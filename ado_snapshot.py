#!/usr/bin/env python3
"""
ado_snapshot.py - ADO read-model for Hadi (module C1)

Keeps a FRESH LOCAL snapshot of the current sprint (work items + capacity) in
SQLite, so Hadi answers board-state questions INSTANTLY from cache, with a
data-freshness guard - instead of hitting ADO live on every message.

Design mirrors posthog_guard.py: reads always carry a freshness banner
(GREEN < 20m, YELLOW 20-60m, RED > 60m or refresh failed) so Hadi never
reports stale board state as if it were live.

Read-only mirror. THIS FILE NEVER WRITES TO ADO. Ticket/CR creation stays on
the live path (ado_cli.py). No update/delete here, by design.

Subcommands:
  refresh              pull current iteration + work items + capacity -> SQLite
                       (run by systemd timer / cron every ~15 min)
  status               freshness banner + one-line sprint summary
  sprint               current sprint dates + state counts (JSON)
  stories [--tag T]    list stories; T in: master | FM | up | Blocked
  blocked [--days N]   items tagged Blocked (optionally stuck >= N calendar days)
  capacity             team days-off (scheduled leave) from the Capacity screen

Env (all optional except the PAT):
  AZURE_DEVOPS_PAT        (required) PAT with Work Items (Read)
  ADO_ORG_URL             default https://hadafsolutions.visualstudio.com
  ADO_PROJECT             default 0_Projects_Team
  ADO_TEAM                default Mars Team
  ADO_SNAPSHOT_DB         default <script dir>/ado_snapshot.db
  ADO_FRESH_GREEN_MIN     default 20
  ADO_FRESH_YELLOW_MIN    default 60
"""

import os
import sys
import json
import base64
import sqlite3
import argparse
import datetime
import urllib.parse
import urllib.request
import urllib.error

API = "7.0"
ORG_URL = os.environ.get("ADO_ORG_URL", "https://hadafsolutions.visualstudio.com").rstrip("/")
PROJECT = os.environ.get("ADO_PROJECT", "0_Projects_Team")
TEAM = os.environ.get("ADO_TEAM", "Mars Team")
PAT = os.environ.get("AZURE_DEVOPS_PAT") or os.environ.get("ADO_PAT", "")
DB_PATH = os.environ.get(
    "ADO_SNAPSHOT_DB",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "ado_snapshot.db"),
)
GREEN_MIN = int(os.environ.get("ADO_FRESH_GREEN_MIN", "20"))
YELLOW_MIN = int(os.environ.get("ADO_FRESH_YELLOW_MIN", "60"))

WORK_DAYS = {6, 0, 1, 2, 3}  # Sun..Thu (Python weekday: Mon=0..Sun=6) -> Egypt week

FIELDS = [
    "System.Id", "System.WorkItemType", "System.Title", "System.State",
    "System.Tags", "System.BoardColumn", "System.BoardLane", "System.AssignedTo",
    "System.IterationPath", "System.Parent", "System.CreatedDate",
    "System.ChangedDate", "Microsoft.VSTS.Scheduling.RemainingWork",
]


# ----------------------------- ADO REST -----------------------------
def _auth_header():
    if not PAT:
        raise SystemExit("ERROR: AZURE_DEVOPS_PAT is not set.")
    token = base64.b64encode(f":{PAT}".encode()).decode()
    return {"Authorization": f"Basic {token}", "Accept": "application/json"}


def _req(method, url, body=None):
    data = json.dumps(body).encode() if body is not None else None
    headers = _auth_header()
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def _team_base():
    return f"{ORG_URL}/{urllib.parse.quote(PROJECT)}/{urllib.parse.quote(TEAM)}/_apis/work/teamsettings"


def fetch_current_iteration():
    url = f"{_team_base()}/iterations?$timeframe=current&api-version={API}"
    vals = _req("GET", url).get("value", [])
    return vals[0] if vals else None


def fetch_iteration_workitem_ids(iteration_id):
    url = f"{_team_base()}/iterations/{iteration_id}/workitems?api-version={API}"
    rels = _req("GET", url).get("workItemRelations", [])
    ids, top = [], set()
    for rel in rels:
        tgt = rel.get("target") or {}
        if tgt.get("id"):
            ids.append(tgt["id"])
        if rel.get("rel") is None and tgt.get("id"):
            top.add(tgt["id"])
    return sorted(set(ids)), top


def fetch_fields(ids):
    out = []
    url = f"{ORG_URL}/{urllib.parse.quote(PROJECT)}/_apis/wit/workitemsbatch?api-version={API}"
    for i in range(0, len(ids), 200):
        chunk = ids[i:i + 200]
        res = _req("POST", url, {"ids": chunk, "fields": FIELDS})
        out.extend(res.get("value", []))
    return out


def fetch_capacity(iteration_id):
    url = f"{_team_base()}/iterations/{iteration_id}/capacities?api-version={API}"
    try:
        return _req("GET", url).get("value", [])
    except urllib.error.HTTPError:
        # older API shape
        url2 = f"{_team_base()}/iterations/{iteration_id}/capacities?api-version=6.0"
        return _req("GET", url2).get("value", [])


# ----------------------------- storage -----------------------------
def _db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def _init(con):
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
        CREATE TABLE IF NOT EXISTS work_items (
            id INTEGER PRIMARY KEY, type TEXT, title TEXT, state TEXT,
            tags TEXT, board_column TEXT, board_lane TEXT, assigned_to TEXT,
            iteration_path TEXT, parent INTEGER, remaining_work REAL,
            created_date TEXT, changed_date TEXT, is_top INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS capacity (
            member TEXT, email TEXT, activity TEXT,
            capacity_per_day REAL, days_off TEXT
        );
        CREATE TABLE IF NOT EXISTS blocked_state (
            id INTEGER PRIMARY KEY, blocked_since TEXT
        );
        """
    )
    con.commit()


def _tags_list(raw):
    return [t.strip() for t in (raw or "").split(";") if t.strip()]


def _assigned(v):
    if isinstance(v, dict):
        return v.get("displayName") or v.get("uniqueName") or ""
    return v or ""


def refresh():
    now = datetime.datetime.now(datetime.timezone.utc)
    con = _db()
    _init(con)
    try:
        it = fetch_current_iteration()
        if not it:
            _set_meta(con, {"last_error": "no current iteration", "last_error_at": now.isoformat()})
            con.commit()
            print("ERROR: no current iteration found for team", TEAM)
            return 1
        attrs = it.get("attributes", {}) or {}
        ids, top = fetch_iteration_workitem_ids(it["id"])
        items = fetch_fields(ids) if ids else []
        caps = fetch_capacity(it["id"])

        con.execute("DELETE FROM work_items")
        con.execute("DELETE FROM capacity")
        blocked_now = set()
        for w in items:
            f = w.get("fields", {})
            tags = f.get("System.Tags", "")
            wid = f.get("System.Id")
            con.execute(
                """INSERT OR REPLACE INTO work_items
                   (id,type,title,state,tags,board_column,board_lane,assigned_to,
                    iteration_path,parent,remaining_work,created_date,changed_date,is_top)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (wid, f.get("System.WorkItemType"), f.get("System.Title"),
                 f.get("System.State"), tags, f.get("System.BoardColumn"),
                 f.get("System.BoardLane"), _assigned(f.get("System.AssignedTo")),
                 f.get("System.IterationPath"), f.get("System.Parent"),
                 f.get("Microsoft.VSTS.Scheduling.RemainingWork"),
                 f.get("System.CreatedDate"), f.get("System.ChangedDate"),
                 1 if wid in top else 0),
            )
            if any(t.lower() == "blocked" for t in _tags_list(tags)):
                blocked_now.add(wid)

        # stateful blocked-since tracking (for "stuck >= N days")
        existing = {r["id"] for r in con.execute("SELECT id FROM blocked_state")}
        for wid in blocked_now - existing:
            con.execute("INSERT OR REPLACE INTO blocked_state (id,blocked_since) VALUES (?,?)",
                        (wid, now.isoformat()))
        for wid in existing - blocked_now:
            con.execute("DELETE FROM blocked_state WHERE id=?", (wid,))

        for c in caps:
            tm = c.get("teamMember", {}) or {}
            acts = c.get("activities") or [{}]
            con.execute(
                "INSERT INTO capacity (member,email,activity,capacity_per_day,days_off) VALUES (?,?,?,?,?)",
                (tm.get("displayName"), tm.get("uniqueName"),
                 acts[0].get("name"), acts[0].get("capacityPerDay"),
                 json.dumps(c.get("daysOff") or [])),
            )

        _set_meta(con, {
            "last_refresh": now.isoformat(),
            "last_error": "",
            "sprint_id": it["id"],
            "sprint_name": it.get("name"),
            "sprint_path": it.get("path"),
            "sprint_start": attrs.get("startDate"),
            "sprint_finish": attrs.get("finishDate"),
            "item_count": str(len(items)),
        })
        con.commit()
        print(f"OK: refreshed {len(items)} items for {it.get('name')} at {now.isoformat()}")
        return 0
    except Exception as e:  # noqa
        _set_meta(con, {"last_error": str(e), "last_error_at": now.isoformat()})
        con.commit()
        print("ERROR during refresh:", e)
        return 1
    finally:
        con.close()


def _set_meta(con, d):
    for k, v in d.items():
        con.execute("INSERT OR REPLACE INTO meta (key,value) VALUES (?,?)", (k, "" if v is None else str(v)))


# ----------------------------- freshness -----------------------------
def _meta(con):
    return {r["key"]: r["value"] for r in con.execute("SELECT key,value FROM meta")}


def freshness(con):
    m = _meta(con)
    last = m.get("last_refresh")
    if not last:
        return {"emoji": "🔴", "label": "DOWN", "age_min": None, "note": "no snapshot yet"}
    age = (datetime.datetime.now(datetime.timezone.utc)
           - datetime.datetime.fromisoformat(last)).total_seconds() / 60.0
    if m.get("last_error"):
        return {"emoji": "🔴", "label": "DOWN", "age_min": round(age), "note": m["last_error"]}
    if age < GREEN_MIN:
        emoji, label = "🟢", "LIVE"
    elif age < YELLOW_MIN:
        emoji, label = "🟡", "STALE"
    else:
        emoji, label = "🔴", "DOWN"
    return {"emoji": emoji, "label": label, "age_min": round(age), "note": ""}


def banner(con):
    fr = freshness(con)
    age = "?" if fr["age_min"] is None else f"{fr['age_min']}m"
    extra = f" - {fr['note']}" if fr["note"] else ""
    return f"{fr['emoji']} {fr['label']} (snapshot age {age}){extra}"


# ----------------------------- reads -----------------------------
def _rows(con, where="", args=()):
    q = "SELECT * FROM work_items"
    if where:
        q += " WHERE " + where
    return [dict(r) for r in con.execute(q, args)]


def _working_days(since_iso):
    start = datetime.datetime.fromisoformat(since_iso)
    now = datetime.datetime.now(datetime.timezone.utc)
    d, days = start, 0
    while d.date() < now.date():
        if d.weekday() in WORK_DAYS:
            days += 1
        d += datetime.timedelta(days=1)
    return days


def cmd_status(con):
    m = _meta(con)
    print(banner(con))
    if m.get("sprint_name"):
        print(f"Sprint: {m['sprint_name']}  ({(m.get('sprint_start') or '')[:10]} -> {(m.get('sprint_finish') or '')[:10]})")
        print(f"Work items in snapshot: {m.get('item_count','0')}")


def cmd_sprint(con):
    m = _meta(con)
    states = {}
    for r in _rows(con, "is_top=1"):
        states[r["state"]] = states.get(r["state"], 0) + 1
    print(json.dumps({
        "freshness": freshness(con),
        "sprint": {"name": m.get("sprint_name"), "start": m.get("sprint_start"),
                   "finish": m.get("sprint_finish")},
        "top_level_state_counts": states,
    }, ensure_ascii=False, indent=2))


def cmd_stories(con, tag):
    rows = _rows(con, "is_top=1")
    if tag:
        tl = tag.lower()
        rows = [r for r in rows if any(t.lower() == tl for t in _tags_list(r["tags"]))]
    out = [{"id": r["id"], "title": r["title"], "state": r["state"],
            "column": r["board_column"], "assigned_to": r["assigned_to"],
            "tags": _tags_list(r["tags"])} for r in rows]
    print(banner(con))
    print(json.dumps(out, ensure_ascii=False, indent=2))


def cmd_blocked(con, days):
    since = {r["id"]: r["blocked_since"] for r in con.execute("SELECT id,blocked_since FROM blocked_state")}
    out = []
    for r in _rows(con):
        if r["id"] in since:
            wd = _working_days(since[r["id"]])
            if wd >= days:
                out.append({"id": r["id"], "title": r["title"], "state": r["state"],
                            "assigned_to": r["assigned_to"], "blocked_working_days": wd,
                            "blocked_since": since[r["id"]][:10]})
    print(banner(con))
    print(json.dumps(sorted(out, key=lambda x: -x["blocked_working_days"]), ensure_ascii=False, indent=2))


def cmd_capacity(con):
    out = []
    for r in con.execute("SELECT * FROM capacity"):
        out.append({"member": r["member"], "email": r["email"],
                    "activity": r["activity"], "capacity_per_day": r["capacity_per_day"],
                    "days_off": json.loads(r["days_off"] or "[]")})
    print(banner(con))
    print(json.dumps(out, ensure_ascii=False, indent=2))


# ----------------------------- cli -----------------------------
def main():
    p = argparse.ArgumentParser(description="Hadi ADO read-model (read-only snapshot).")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("refresh")
    sub.add_parser("status")
    sub.add_parser("sprint")
    sp = sub.add_parser("stories"); sp.add_argument("--tag", default=None)
    bp = sub.add_parser("blocked"); bp.add_argument("--days", type=int, default=0)
    sub.add_parser("capacity")
    a = p.parse_args()

    if a.cmd == "refresh":
        sys.exit(refresh())

    con = _db(); _init(con)
    try:
        if a.cmd == "status":
            cmd_status(con)
        elif a.cmd == "sprint":
            cmd_sprint(con)
        elif a.cmd == "stories":
            cmd_stories(con, a.tag)
        elif a.cmd == "blocked":
            cmd_blocked(con, a.days)
        elif a.cmd == "capacity":
            cmd_capacity(con)
    finally:
        con.close()


if __name__ == "__main__":
    main()
