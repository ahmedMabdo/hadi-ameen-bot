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

# --- point 2: multi-board read-model (Support + CR + 8Orders project tree) ---
AREA_SUPPORT = os.environ.get("ADO_AREA_SUPPORT", "0_Projects_Team\\Support Team")
AREA_CR = os.environ.get("ADO_AREA_CR", "0_Projects_Team\\Change Requests")
BOARDS = {"support": AREA_SUPPORT, "cr": AREA_CR}
PROJECT_ITEM_ID = int(os.environ.get("ADO_PROJECT_ITEM", "53585") or "53585")
BOARD_TOP = int(os.environ.get("ADO_BOARD_TOP", "500"))
CLOSED_WINDOW_DAYS = int(os.environ.get("ADO_CLOSED_WINDOW_DAYS", "14"))
DONE_STATES = ("Closed", "Rejected", "Removed")

WORK_DAYS = {6, 0, 1, 2, 3}  # Sun..Thu (Python weekday: Mon=0..Sun=6) -> Egypt week

FIELDS = [
    "System.Id", "System.WorkItemType", "System.Title", "System.State",
    "System.Tags", "System.BoardColumn", "System.BoardLane", "System.AssignedTo",
    "System.IterationPath", "System.Parent", "System.CreatedDate",
    "System.ChangedDate", "Microsoft.VSTS.Scheduling.RemainingWork",
    "Microsoft.VSTS.Common.Priority",
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


def wiql_ids(query, top=None):
    """IDs من WIQL flat query (workItems[].id)."""
    url = (f"{ORG_URL}/{urllib.parse.quote(PROJECT)}/_apis/wit/wiql"
           f"?api-version={API}&$top={top or BOARD_TOP}")
    res = _req("POST", url, {"query": query})
    return [w["id"] for w in res.get("workItems", [])]


def wiql_link_ids(query, top=None):
    """IDs من WIQL link query (workItemRelations[].target.id) — لشجرة الـ hierarchy."""
    url = (f"{ORG_URL}/{urllib.parse.quote(PROJECT)}/_apis/wit/wiql"
           f"?api-version={API}&$top={top or BOARD_TOP}")
    res = _req("POST", url, {"query": query})
    ids = set()
    for rel in res.get("workItemRelations", []):
        tgt = rel.get("target") or {}
        if tgt.get("id"):
            ids.add(tgt["id"])
    return sorted(ids)


def fetch_capacity(iteration_id):
    b=_team_base()
    for ver in ('7.1','7.0','6.0'):
        for ep in ('capacities','capacity'):
            try:
                d=_req('GET', f'{b}/iterations/{iteration_id}/{ep}?api-version={ver}')
            except Exception:
                continue
            v=d.get('value') or d.get('teamMembers') or []
            if v: return v
    return []


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
        CREATE TABLE IF NOT EXISTS board_items (
            board TEXT, id INTEGER, type TEXT, title TEXT, state TEXT,
            tags TEXT, assigned_to TEXT, priority INTEGER, parent INTEGER,
            created_date TEXT, changed_date TEXT,
            PRIMARY KEY (board, id)
        );
        CREATE TABLE IF NOT EXISTS project_items (
            id INTEGER PRIMARY KEY, type TEXT, title TEXT, state TEXT,
            parent INTEGER, changed_date TEXT
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


def _refresh_sprint(con, now):
    it = fetch_current_iteration()
    if not it:
        raise RuntimeError("no current iteration found for team " + TEAM)
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
    return len(items)


def _refresh_board(con, board, now):
    """بورد Support أو CR: كل المفتوح + المقفول خلال آخر CLOSED_WINDOW_DAYS يوم."""
    area = BOARDS[board]
    states = " AND ".join(f"[System.State] <> '{s}'" for s in DONE_STATES)
    q = (
        "SELECT [System.Id] FROM WorkItems "
        f"WHERE [System.TeamProject] = '{PROJECT}' "
        f"AND [System.AreaPath] UNDER '{area}' "
        f"AND (({states}) OR [System.ChangedDate] >= @Today - {CLOSED_WINDOW_DAYS}) "
        "ORDER BY [System.ChangedDate] DESC"
    )
    ids = wiql_ids(q)
    items = fetch_fields(ids) if ids else []
    con.execute("DELETE FROM board_items WHERE board=?", (board,))
    for w in items:
        f = w.get("fields", {})
        con.execute(
            """INSERT OR REPLACE INTO board_items
               (board,id,type,title,state,tags,assigned_to,priority,parent,
                created_date,changed_date) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (board, f.get("System.Id"), f.get("System.WorkItemType"),
             f.get("System.Title"), f.get("System.State"), f.get("System.Tags", ""),
             _assigned(f.get("System.AssignedTo")),
             f.get("Microsoft.VSTS.Common.Priority"), f.get("System.Parent"),
             f.get("System.CreatedDate"), f.get("System.ChangedDate")),
        )
    _set_meta(con, {f"{board}_last_refresh": now.isoformat(), f"{board}_error": "",
                    f"{board}_count": str(len(items))})
    return len(items)


def _refresh_project(con, now):
    """شجرة مشروع 8Orders (الـ work item رقم PROJECT_ITEM_ID + كل أولاده recursive)."""
    q = (
        "SELECT [System.Id] FROM WorkItemLinks "
        f"WHERE [Source].[System.Id] = {PROJECT_ITEM_ID} "
        "AND [System.Links.LinkType] = 'System.LinkTypes.Hierarchy-Forward' "
        "MODE (Recursive)"
    )
    ids = set(wiql_link_ids(q))
    ids.add(PROJECT_ITEM_ID)
    items = fetch_fields(sorted(ids))
    con.execute("DELETE FROM project_items")
    for w in items:
        f = w.get("fields", {})
        con.execute(
            "INSERT OR REPLACE INTO project_items (id,type,title,state,parent,changed_date)"
            " VALUES (?,?,?,?,?,?)",
            (f.get("System.Id"), f.get("System.WorkItemType"), f.get("System.Title"),
             f.get("System.State"), f.get("System.Parent"), f.get("System.ChangedDate")),
        )
    _set_meta(con, {"project_last_refresh": now.isoformat(), "project_error": "",
                    "project_count": str(len(items))})
    return len(items)


def refresh():
    """يحدّث كل المصادر — كل مصدر معزول: فشل بورد ميوقعش الباقي (نضارة لكل مصدر)."""
    now = datetime.datetime.now(datetime.timezone.utc)
    con = _db()
    _init(con)
    results, failures = [], []
    parts = [
        ("sprint", lambda: _refresh_sprint(con, now)),
        ("support", lambda: _refresh_board(con, "support", now)),
        ("cr", lambda: _refresh_board(con, "cr", now)),
        ("project", lambda: _refresh_project(con, now)),
    ]
    try:
        for name, fn in parts:
            try:
                n = fn()
                con.commit()
                results.append(f"{name}={n}")
            except Exception as e:  # noqa — عزل الفشل لكل مصدر
                err_key = "last_error" if name == "sprint" else f"{name}_error"
                at_key = "last_error_at" if name == "sprint" else f"{name}_error_at"
                _set_meta(con, {err_key: str(e), at_key: now.isoformat()})
                con.commit()
                failures.append(f"{name}: {e}")
        # توليد knowledge/sprints.md من الـ snapshot (F8: الملف generated دايمًا)
        try:
            import sprints_sync
            sprints_sync.write_default()
        except Exception as e:  # noqa — best-effort
            print("WARN: sprints_sync failed:", e)
    finally:
        con.close()
    print(("OK" if not failures else "PARTIAL") + ": refreshed "
          + ", ".join(results) + (f" | failures: {'; '.join(failures)}" if failures else "")
          + f" at {now.isoformat()}")
    return 0 if not failures else 1


def _set_meta(con, d):
    for k, v in d.items():
        con.execute("INSERT OR REPLACE INTO meta (key,value) VALUES (?,?)", (k, "" if v is None else str(v)))


# ----------------------------- freshness -----------------------------
def _meta(con):
    return {r["key"]: r["value"] for r in con.execute("SELECT key,value FROM meta")}


def freshness(con, source=None):
    """نضارة مصدر معين: sprint (الافتراضي) أو support/cr/project."""
    m = _meta(con)
    if source in (None, "sprint"):
        last, err = m.get("last_refresh"), m.get("last_error")
    else:
        last, err = m.get(f"{source}_last_refresh"), m.get(f"{source}_error")
    if not last:
        return {"emoji": "🔴", "label": "DOWN", "age_min": None, "note": "no snapshot yet"}
    age = (datetime.datetime.now(datetime.timezone.utc)
           - datetime.datetime.fromisoformat(last)).total_seconds() / 60.0
    if err:
        return {"emoji": "🔴", "label": "DOWN", "age_min": round(age), "note": err}
    if age < GREEN_MIN:
        emoji, label = "🟢", "LIVE"
    elif age < YELLOW_MIN:
        emoji, label = "🟡", "STALE"
    else:
        emoji, label = "🔴", "DOWN"
    return {"emoji": emoji, "label": label, "age_min": round(age), "note": ""}


def banner(con, source=None):
    fr = freshness(con, source)
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


# ------------------- multi-board reads (point 2) -------------------
def _board_rows(con, board=None, state=None):
    q, args = "SELECT * FROM board_items", []
    conds = []
    if board:
        conds.append("board=?"); args.append(board)
    if state:
        conds.append("state=?"); args.append(state)
    if conds:
        q += " WHERE " + " AND ".join(conds)
    q += " ORDER BY changed_date DESC"
    return [dict(r) for r in con.execute(q, args)]


def _iso_age_hours(iso):
    try:
        dt = datetime.datetime.fromisoformat((iso or "").replace("Z", "+00:00"))
        return (datetime.datetime.now(datetime.timezone.utc) - dt).total_seconds() / 3600.0
    except Exception:
        return 1e9


def cmd_boards(con, board, state):
    rows = _board_rows(con, board, state)
    out = [{"board": r["board"], "id": r["id"], "type": r["type"], "title": r["title"],
            "state": r["state"], "assigned_to": r["assigned_to"],
            "priority": r["priority"], "tags": _tags_list(r["tags"]),
            "changed": (r["changed_date"] or "")[:16]} for r in rows]
    for b in ([board] if board else sorted(BOARDS)):
        print(f"[{b}] {banner(con, b)}")
    print(json.dumps(out, ensure_ascii=False, indent=2))


def _board_summary(con, board):
    rows = _board_rows(con, board)
    open_rows = [r for r in rows if r["state"] not in DONE_STATES]
    by_state, by_type = {}, {}
    for r in open_rows:
        by_state[r["state"]] = by_state.get(r["state"], 0) + 1
        by_type[r["type"]] = by_type.get(r["type"], 0) + 1
    new_24h = sum(1 for r in rows if _iso_age_hours(r["created_date"]) <= 24)
    closed_14d = sum(1 for r in rows if r["state"] in DONE_STATES)
    return {"open": len(open_rows), "by_state": by_state, "by_type": by_type,
            "new_24h": new_24h, f"closed_{CLOSED_WINDOW_DAYS}d": closed_14d}


def cmd_board_summary(con):
    out = {}
    for b in sorted(BOARDS):
        out[b] = {"freshness": freshness(con, b), **_board_summary(con, b)}
    print(json.dumps(out, ensure_ascii=False, indent=2))


def cmd_project(con):
    rows = {r["id"]: dict(r) for r in con.execute("SELECT * FROM project_items")}
    print(f"[project 8Orders #{PROJECT_ITEM_ID}] {banner(con, 'project')}")
    kids = {}
    for r in rows.values():
        kids.setdefault(r["parent"], []).append(r)

    def _walk(pid, depth, seen=None):
        # حد عمق + كشف الحلقات: parent link دايري في ADO كان هيرمي RecursionError
        seen = seen or set()
        if depth > 12 or pid in seen:
            return
        seen = seen | {pid}
        for r in sorted(kids.get(pid, []), key=lambda x: x["id"]):
            print("  " * depth + f"- #{r['id']} [{r['type']}] {r['title']} ({r['state']})")
            _walk(r["id"], depth + 1, seen)

    root = rows.get(PROJECT_ITEM_ID)
    if root:
        print(f"#{root['id']} [{root['type']}] {root['title']} ({root['state']})")
        _walk(PROJECT_ITEM_ID, 1)
    else:
        print("(no project snapshot yet — run refresh)")


def cmd_whatsnew(con, hours):
    """الجديد/المتغير خلال آخر N ساعة عبر البوردات والسبرنت — غذاء «إيه الجديد؟»."""
    out = {"window_hours": hours, "boards": {}, "sprint_changed": []}
    for b in sorted(BOARDS):
        rows = _board_rows(con, b)
        created = [r for r in rows if _iso_age_hours(r["created_date"]) <= hours]
        changed = [r for r in rows if _iso_age_hours(r["changed_date"]) <= hours
                   and r not in created]
        out["boards"][b] = {
            "freshness": freshness(con, b),
            "created": [{"id": r["id"], "type": r["type"], "title": r["title"],
                         "state": r["state"]} for r in created],
            "changed": [{"id": r["id"], "type": r["type"], "title": r["title"],
                         "state": r["state"]} for r in changed[:20]],
        }
    for r in _rows(con):
        if _iso_age_hours(r["changed_date"]) <= hours:
            out["sprint_changed"].append({"id": r["id"], "title": r["title"],
                                          "state": r["state"]})
    out["sprint_changed"] = out["sprint_changed"][:20]
    print(json.dumps(out, ensure_ascii=False, indent=2))


def _next_ceremony(m):
    """أقرب إيفنت جاي من sprint_ceremonies.json (المؤكد من آسر) أو الديفولت المحسوب."""
    try:
        import sprint_intake
        return sprint_intake.next_event(m.get("sprint_name"),
                                        (m.get("sprint_start") or "")[:10],
                                        (m.get("sprint_finish") or "")[:10])
    except Exception:
        return None


def _days_left(finish_iso):
    try:
        finish = datetime.datetime.fromisoformat(
            (finish_iso or "").replace("Z", "+00:00")).date()
    except Exception:
        return None
    d, days = datetime.date.today(), 0
    while d < finish:
        if d.weekday() in WORK_DAYS:
            days += 1
        d += datetime.timedelta(days=1)
    return days


def cmd_brief(con):
    """الخلاصة الشاملة بأمر واحد — دي «فتحة الدرج» الرسمية: سبرنت + بوردات + مشروع."""
    m = _meta(con)
    states = {}
    for r in _rows(con, "is_top=1"):
        states[r["state"]] = states.get(r["state"], 0) + 1
    blocked = sum(1 for _ in con.execute("SELECT id FROM blocked_state"))
    tags = {t: 0 for t in ("master", "FM", "up")}
    for r in _rows(con, "is_top=1"):
        for t in _tags_list(r["tags"]):
            if t in tags:
                tags[t] += 1
    dl = _days_left(m.get("sprint_finish"))
    print(f"📋 SNAPSHOT BRIEF — {datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='minutes')}")
    print(f"[sprint] {banner(con)}")
    print(f"  {m.get('sprint_name','?')}: {(m.get('sprint_start') or '')[:10]} → "
          f"{(m.get('sprint_finish') or '')[:10]}"
          + (f" — فاضل {dl} يوم شغل" if dl is not None else ""))
    print(f"  states: {json.dumps(states, ensure_ascii=False)} | blocked: {blocked}"
          f" | master: {tags['master']} | FM: {tags['FM']} | unplanned: {tags['up']}")
    nxt = _next_ceremony(m)
    if nxt:
        src = "مؤكد من آسر" if nxt.get("confirmed") else "متوقع — لسه متأكدناش من آسر"
        print(f"  أقرب إيفنت: {nxt['label']} — {nxt['date']} ({src})")
    for b in sorted(BOARDS):
        s = _board_summary(con, b)
        print(f"[{b}] {banner(con, b)}")
        print(f"  open: {s['open']} (new 24h: {s['new_24h']}) | by_type: "
              f"{json.dumps(s['by_type'], ensure_ascii=False)} | by_state: "
              f"{json.dumps(s['by_state'], ensure_ascii=False)}")
    print(f"[project] {banner(con, 'project')} — items: {m.get('project_count', '0')}")


def pointer_line():
    """سطر واحد مكثف للحقن في برومبت البوت — تذكير إن الدرج موجود وطازة (مش الخلاصة كاملة).

    بيتنادى من discord_bot مع كل رسالة: قراءة SQLite محلية بالميلي ثانية، ولو أي
    مشكلة بيرجع '' — عمره ما يوقف رد."""
    try:
        con = _db()
        _init(con)
        try:
            m = _meta(con)
            fr = freshness(con)
            sup = _board_summary(con, "support")
            cr = _board_summary(con, "cr")
        finally:
            con.close()
        name = m.get("sprint_name")
        if not name:
            return ""
        dl = _days_left(m.get("sprint_finish"))
        return (f"{fr['emoji']} snapshot محلي (اتحدث من {fr['age_min']}د): {name}"
                + (f" فاضل {dl} يوم شغل" if dl is not None else "")
                + f" | سابورت {sup['open']} مفتوح | CR {cr['open']} مفتوح")
    except Exception:
        return ""


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
    bo = sub.add_parser("boards")
    bo.add_argument("--board", choices=sorted(BOARDS), default=None)
    bo.add_argument("--state", default=None)
    sub.add_parser("board-summary")
    sub.add_parser("project")
    wn = sub.add_parser("whatsnew"); wn.add_argument("--hours", type=int, default=24)
    sub.add_parser("brief")
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
        elif a.cmd == "boards":
            cmd_boards(con, a.board, a.state)
        elif a.cmd == "board-summary":
            cmd_board_summary(con)
        elif a.cmd == "project":
            cmd_project(con)
        elif a.cmd == "whatsnew":
            cmd_whatsnew(con, a.hours)
        elif a.cmd == "brief":
            cmd_brief(con)
    finally:
        con.close()


if __name__ == "__main__":
    main()
