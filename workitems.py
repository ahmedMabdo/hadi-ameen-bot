#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
workitems.py — durable work-item lifecycle store for Hadi (Phase 2/3, module W1).

Owns `workitems.db` (SEPARATE from the read-only ado_snapshot.db, whose contract
is refresh-and-overwrite). Here we keep:

  * a current mirror of each work item (upsert by ADO id), and
  * an APPEND-ONLY, IDEMPOTENT event log of every meaningful change — the thing
    the bot lacked when it couldn't answer "how many items moved Resolved ->
    Pending Deployment / Closed today?".

Idempotency: every event has a deterministic `event_id`
    sha1(source | work_item_id | field | old | new | changed_date)
with `UNIQUE(event_id)` + `INSERT OR IGNORE`. The same change observed 5x
(re-poll, restart, retry) inserts exactly once and survives restarts.

Two ingestion paths (run ONE in prod — see record_transitions vs ingest_revisions):
  * record_transitions(source, ado_items)  — diff the fresh 15-min snapshot batch
    against the stored mirror. Self-contained, no extra API. Captures net change
    per interval. THIS is the default (wired into ado_snapshot.refresh()).
  * ingest_revisions(source, rows)          — authoritative intra-interval history
    from ADO reporting/workItemRevisions (ado_updates.py). Enable when you want
    every transition, not just the per-interval net.

This module NEVER writes to ADO.
"""
import os
import sqlite3
import hashlib
import datetime

import hadi_config
import change_classifier

DB_PATH = hadi_config.WORKITEMS_DB

_SCHEMA = """
CREATE TABLE IF NOT EXISTS work_items (
    id INTEGER PRIMARY KEY,
    source TEXT, type TEXT, title TEXT, state TEXT, state_category TEXT,
    severity TEXT, priority INTEGER, assignee TEXT,
    area_path TEXT, iteration_path TEXT, release TEXT, tags TEXT,
    parent INTEGER, rev INTEGER,
    created_date TEXT, changed_date TEXT, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS work_item_events (
    event_id TEXT PRIMARY KEY,
    work_item_id INTEGER, source TEXT, event_type TEXT, field TEXT,
    previous_value TEXT, new_value TEXT,
    previous_category TEXT, new_category TEXT,
    source_rev INTEGER, changed_by TEXT, changed_date TEXT,
    meaningful INTEGER, processed_at TEXT
);
CREATE INDEX IF NOT EXISTS ix_events_changed ON work_item_events(changed_date);
CREATE INDEX IF NOT EXISTS ix_events_type ON work_item_events(event_type);
CREATE INDEX IF NOT EXISTS ix_events_wi ON work_item_events(work_item_id);
CREATE TABLE IF NOT EXISTS issue_evaluations (
    evaluation_id TEXT PRIMARY KEY, work_item_id INTEGER, decision TEXT,
    confidence REAL, matched_issue_id INTEGER, evidence TEXT,
    contradicting TEXT, reason TEXT, evaluation_version TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS releases (
    release_id TEXT PRIMARY KEY, version TEXT, platform TEXT, release_time TEXT,
    work_items TEXT, status TEXT, baseline_captured INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS monitoring_snapshots (
    source TEXT, release_id TEXT, ts TEXT, metric TEXT,
    value REAL, baseline REAL, delta REAL, status TEXT,
    PRIMARY KEY (source, release_id, ts, metric)
);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
"""

_default = None


def connect(path=None):
    """Open (and initialise) a connection. Pass path for tests/temp DBs."""
    con = sqlite3.connect(path or DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.executescript(_SCHEMA)
    _migrate(con)
    con.commit()
    return con


def _migrate(con):
    """eval_store.py-style additive migration: add columns if missing."""
    cols = {r[1] for r in con.execute("PRAGMA table_info(work_items)")}
    for name, ddl in (("release", "ALTER TABLE work_items ADD COLUMN release TEXT"),
                      ("rev", "ALTER TABLE work_items ADD COLUMN rev INTEGER")):
        if name not in cols:
            con.execute(ddl)


def _con(con):
    global _default
    if con is not None:
        return con
    if _default is None:
        _default = connect()
    return _default


def _now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _event_id(source, wid, field, old, new, changed_date):
    raw = f"{source}|{wid}|{field}|{old}|{new}|{changed_date}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def _assigned(v):
    if isinstance(v, dict):
        return v.get("displayName") or v.get("uniqueName") or ""
    return v or ""


def normalize_ado_item(item, source):
    """ADO batch item ({'id','fields':{...}}) -> flat normalized dict."""
    f = item.get("fields", item) or {}
    wid = item.get("id") or f.get("System.Id")
    return {
        "id": wid,
        "source": source,
        "type": f.get("System.WorkItemType"),
        "title": f.get("System.Title"),
        "state": f.get("System.State"),
        "state_category": hadi_config.state_category(f.get("System.State")),
        "severity": _sev_str(f.get("Microsoft.VSTS.Common.Severity")),
        "priority": f.get("Microsoft.VSTS.Common.Priority"),
        "assignee": _assigned(f.get("System.AssignedTo")),
        "area_path": f.get("System.AreaPath"),
        "iteration_path": f.get("System.IterationPath"),
        "tags": f.get("System.Tags") or "",
        "parent": f.get("System.Parent"),
        "rev": f.get("System.Rev") or item.get("rev"),
        "created_date": f.get("System.CreatedDate"),
        "changed_date": f.get("System.ChangedDate"),
        "changed_by": _assigned(f.get("System.ChangedBy")),
    }


def _sev_str(v):
    return None if v is None else str(v)


# map normalized-dict keys -> ADO field reference names (for event `field`)
_FIELD_OF = {
    "state": "System.State",
    "assignee": "System.AssignedTo",
    "priority": "Microsoft.VSTS.Common.Priority",
    "severity": "Microsoft.VSTS.Common.Severity",
    "tags": "System.Tags",
    "iteration_path": "System.IterationPath",
    "title": "System.Title",
}
_DIFF_KEYS = ("state", "assignee", "priority", "severity", "tags", "iteration_path", "title")


def _upsert(con, n, now):
    con.execute(
        """INSERT INTO work_items
           (id,source,type,title,state,state_category,severity,priority,assignee,
            area_path,iteration_path,release,tags,parent,rev,created_date,changed_date,updated_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
           ON CONFLICT(id) DO UPDATE SET
             source=excluded.source, type=excluded.type, title=excluded.title,
             state=excluded.state, state_category=excluded.state_category,
             severity=excluded.severity, priority=excluded.priority,
             assignee=excluded.assignee, area_path=excluded.area_path,
             iteration_path=excluded.iteration_path, tags=excluded.tags,
             parent=excluded.parent, rev=excluded.rev,
             changed_date=excluded.changed_date, updated_at=excluded.updated_at""",
        (n["id"], n["source"], n["type"], n["title"], n["state"], n["state_category"],
         n["severity"], n["priority"], n["assignee"], n["area_path"], n["iteration_path"],
         n.get("release"), n["tags"], n["parent"], n["rev"], n["created_date"],
         n["changed_date"], now),
    )


def _emit(con, source, wid, field, old, new, changed_date, changed_by, rev, now, extra):
    et, meaningful, ex = change_classifier.classify(field, old, new)
    eid = _event_id(source, wid, field, old, new, changed_date)
    cur = con.execute(
        """INSERT OR IGNORE INTO work_item_events
           (event_id,work_item_id,source,event_type,field,previous_value,new_value,
            previous_category,new_category,source_rev,changed_by,changed_date,
            meaningful,processed_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (eid, wid, source, et, field, _s(old), _s(new),
         ex.get("old_cat"), ex.get("new_cat"), rev, changed_by, changed_date,
         1 if meaningful else 0, now),
    )
    return (et, cur.rowcount == 1)  # rowcount 0 => already existed (idempotent no-op)


def _s(v):
    return None if v is None else str(v)


def _apply(con, n, now, emit_events=True):
    """Compare normalized item `n` against the stored mirror; emit events for
    changed tracked fields; upsert. Returns list of emitted (type) for NEW rows."""
    wid = n["id"]
    if wid is None:
        return []
    row = con.execute("SELECT * FROM work_items WHERE id=?", (wid,)).fetchone()
    emitted = []
    if row is None:
        # first time we ever see this id in this store -> seed, no change events
        _upsert(con, n, now)
        return emitted
    if emit_events:
        old = dict(row)
        mapping = {
            "state": old["state"], "assignee": old["assignee"],
            "priority": old["priority"], "severity": old["severity"],
            "tags": old["tags"], "iteration_path": old["iteration_path"],
            "title": old["title"],
        }
        for key in _DIFF_KEYS:
            new_val = n.get(key)
            old_val = mapping.get(key)
            if _s(old_val) != _s(new_val):
                et, inserted = _emit(
                    con, n["source"], wid, _FIELD_OF[key], old_val, new_val,
                    n.get("changed_date"), n.get("changed_by", ""), n.get("rev"), now, {})
                if inserted:
                    emitted.append(et)
    _upsert(con, n, now)
    return emitted


def _seeded(con, source):
    r = con.execute("SELECT value FROM meta WHERE key=?", (f"seeded_{source}",)).fetchone()
    return bool(r and r["value"] == "1")


def _mark_seeded(con, source):
    con.execute("INSERT OR REPLACE INTO meta(key,value) VALUES (?,?)",
                (f"seeded_{source}", "1"))


def record_transitions(source, ado_items, now=None, con=None):
    """DIFF PATH (default). Compare a fresh ADO batch (list of {'id','fields'})
    against the mirror; log transition events; upsert mirror.

    On the very first run for a `source` (empty mirror) we SEED silently — no
    flood of bogus 'created' events for pre-existing board items.
    """
    con = _con(con)
    now = now or _now_iso()
    cold = not _seeded(con, source)
    summary = {"seeded": cold, "events": 0, "by_type": {}, "items": 0}
    for item in ado_items or []:
        n = normalize_ado_item(item, source)
        emitted = _apply(con, n, now, emit_events=not cold)
        summary["items"] += 1
        for et in emitted:
            summary["events"] += 1
            summary["by_type"][et] = summary["by_type"].get(et, 0) + 1
    if cold:
        _mark_seeded(con, source)
    con.commit()
    return summary


def ingest_revisions(source, rows, now=None, con=None):
    """AUTHORITATIVE PATH (opt-in). `rows` are normalized revision dicts from
    ado_updates (reporting/workItemRevisions), each already carrying explicit
    field/old/new/changed_date/rev. Idempotent via the same event_id."""
    con = _con(con)
    now = now or _now_iso()
    count = 0
    for r in rows or []:
        _, inserted = _emit(
            con, source, r["id"], r["field"], r.get("old"), r.get("new"),
            r.get("changed_date"), r.get("changed_by", ""), r.get("rev"), now, {})
        if inserted:
            count += 1
        # keep the mirror current with the latest revision snapshot if provided
        if r.get("item"):
            _apply(con, normalize_ado_item(r["item"], source), now, emit_events=False)
    con.commit()
    return {"events": count}


# --------------------------------------------------------------------------
# reads (this is what answers Ghada's question)
# --------------------------------------------------------------------------
def _date(iso):
    return (iso or "")[:10]


def status_transitions(on_date=None, from_state=None, to_states=None, con=None):
    """Return STATUS/QA/RELEASE/REGRESSION events (state field) filtered by
    optional date (YYYY-MM-DD, matched on changed_date), from_state, to_states."""
    con = _con(con)
    q = ("SELECT * FROM work_item_events WHERE field='System.State'")
    rows = [dict(r) for r in con.execute(q)]
    out = []
    to_set = {s.lower() for s in to_states} if to_states else None
    for r in rows:
        if on_date and _date(r["changed_date"]) != on_date:
            continue
        if from_state and (r["previous_value"] or "").lower() != from_state.lower():
            continue
        if to_set and (r["new_value"] or "").lower() not in to_set:
            continue
        out.append(r)
    return out


def count_status_transitions(on_date=None, from_state=None, to_states=None, con=None):
    return len(status_transitions(on_date, from_state, to_states, con))


def events(since=None, until=None, types=None, meaningful_only=False, con=None):
    con = _con(con)
    rows = [dict(r) for r in con.execute(
        "SELECT * FROM work_item_events ORDER BY changed_date")]
    tset = set(types) if types else None
    out = []
    for r in rows:
        cd = r["changed_date"] or ""
        if since and cd < since:
            continue
        if until and cd > until:
            continue
        if tset and r["event_type"] not in tset:
            continue
        if meaningful_only and not r["meaningful"]:
            continue
        out.append(r)
    return out


def get_work_item(wid, con=None):
    con = _con(con)
    r = con.execute("SELECT * FROM work_items WHERE id=?", (wid,)).fetchone()
    return dict(r) if r else None


def all_work_items(source=None, con=None):
    con = _con(con)
    if source:
        rows = con.execute("SELECT * FROM work_items WHERE source=?", (source,))
    else:
        rows = con.execute("SELECT * FROM work_items")
    return [dict(r) for r in rows]


# --------------------------------------------------------------------------
# evaluations / releases / monitoring (used by later phases; stored here)
# --------------------------------------------------------------------------
def record_evaluation(ev, con=None):
    con = _con(con)
    import json
    con.execute(
        """INSERT OR REPLACE INTO issue_evaluations
           (evaluation_id,work_item_id,decision,confidence,matched_issue_id,
            evidence,contradicting,reason,evaluation_version,created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (ev["evaluation_id"], ev.get("work_item_id"), ev["decision"],
         ev.get("confidence"), ev.get("matched_issue_id"),
         json.dumps(ev.get("evidence", []), ensure_ascii=False),
         json.dumps(ev.get("contradicting", []), ensure_ascii=False),
         ev.get("reason", ""), ev.get("evaluation_version", hadi_config.EVALUATION_VERSION),
         _now_iso()))
    con.commit()


def upsert_release(rel, con=None):
    con = _con(con)
    import json
    con.execute(
        """INSERT OR REPLACE INTO releases
           (release_id,version,platform,release_time,work_items,status,baseline_captured)
           VALUES (?,?,?,?,?,?,?)""",
        (rel["release_id"], rel.get("version"), rel.get("platform"),
         rel.get("release_time"), json.dumps(rel.get("work_items", []), ensure_ascii=False),
         rel.get("status", "detected"), 1 if rel.get("baseline_captured") else 0))
    con.commit()


def record_metric(m, con=None):
    con = _con(con)
    con.execute(
        """INSERT OR REPLACE INTO monitoring_snapshots
           (source,release_id,ts,metric,value,baseline,delta,status)
           VALUES (?,?,?,?,?,?,?,?)""",
        (m["source"], m.get("release_id", ""), m.get("ts", _now_iso()), m["metric"],
         m.get("value"), m.get("baseline"), m.get("delta"), m.get("status")))
    con.commit()


if __name__ == "__main__":
    import json
    con = connect()
    print(json.dumps({
        "db": DB_PATH,
        "work_items": con.execute("SELECT COUNT(*) FROM work_items").fetchone()[0],
        "events": con.execute("SELECT COUNT(*) FROM work_item_events").fetchone()[0],
    }, ensure_ascii=False, indent=2))
