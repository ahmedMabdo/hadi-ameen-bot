#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
board_report.py — engineering reports built from the durable lifecycle store
(workitems.db) + the ado_snapshot board cache. Phase 3.

Reports:
  daily_board(date)      -> #5 end-of-day board summary
  weekly_engineering()   -> #7 weekly report + engineering health status
  smoke_bc(date)         -> #6 Wednesday Smoke/BC (flags DATA MISSING, never fabricates)
  release_digest()       -> #8 release content/stats/risk

Aggregation is pure (reads a connection); formatting returns Discord-ready text.
Counts come from SQL — the LLM is never asked to count. Delivery is a thin wrapper
around routines_common (see reports_cli.py).
"""
import datetime
from collections import Counter

import hadi_config
import workitems

try:
    import issue_matrix
except Exception:  # pragma: no cover
    issue_matrix = None

HIGH_SEV = {"Urgent", "High"}
OPEN_EXCLUDE = {"closed", "rejected"}


def _sev(v):
    if issue_matrix is None:
        return None
    return issue_matrix.normalize_severity(v)


_SEV_ORDER = {"Urgent": 0, "High": 1, "Medium": 2, "Low": 3}


def _sev_rank(v):
    """ترتيب الخطورة للفرز (الأعلى الأول)؛ غير المعروف في الآخر."""
    return _SEV_ORDER.get(_sev(v), 9)


def _day_bounds(date):
    return f"{date}T00:00:00", f"{date}T23:59:59.999999Z"


def _open(items):
    return [w for w in items if hadi_config.state_category(w["state"]) not in OPEN_EXCLUDE]


def _stale(w, hours):
    cd = w.get("changed_date")
    if not cd:
        return False
    try:
        dt = datetime.datetime.fromisoformat(cd.replace("Z", "+00:00"))
    except ValueError:
        return False
    age_h = (datetime.datetime.now(datetime.timezone.utc) - dt).total_seconds() / 3600.0
    return age_h >= hours


# --------------------------------------------------------------------------
# #5 daily board summary
# --------------------------------------------------------------------------
def daily_board(date, con=None):
    con = workitems._con(con)
    lo, hi = _day_bounds(date)
    evs = workitems.events(since=lo, until=hi, meaningful_only=True, con=con)
    items = workitems.all_work_items(con=con)
    open_items = _open(items)

    status_evs = [e for e in evs if e["field"] == "System.State"]
    moves = Counter(f"{e['previous_category'] or '?'}→{e['new_category'] or '?'}" for e in status_evs)
    assignments = [e for e in evs if e["event_type"] == "ASSIGNMENT_CHANGE"]
    completed = [e for e in status_evs if e["new_category"] == "closed"]
    qa_entered = [e for e in evs if e["event_type"] == "QA_UPDATE"]
    qa_failed_back = [e for e in status_evs if e["previous_category"] == "qa"
                      and e["new_category"] in ("active", "dev_done")]
    releases = [e for e in evs if e["event_type"] == "RELEASE"]
    regressions = [e for e in evs if e["event_type"] == "REGRESSION"]
    blockers = [e for e in evs if e["event_type"] == "BLOCKER"]

    created = [w for w in items if (w.get("created_date") or "")[:10] == date]
    by_priority = Counter(str(w["priority"]) for w in open_items if w["priority"] is not None)
    by_severity = Counter(_sev(w["severity"]) or "—" for w in open_items)

    risks = _risks(len(regressions))
    return {
        "date": date,
        "created": len(created),
        "meaningful_updates": len(evs),
        "status_movements": dict(moves),
        "assignments": len(assignments),
        "by_priority": dict(by_priority),
        "by_severity": dict(by_severity),
        "completed": len(completed),
        "blocked_new": len(blockers),
        "qa_entered": len(qa_entered),
        "qa_failed_back": len(qa_failed_back),
        "releases": len(releases),
        "regressions": len(regressions),
        "risks": risks,
    }


def _risks(regressions_count=0):
    import sqlite3 as _sq3, os as _os
    db = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "data", "ado_snapshot.db")
    if not _os.path.exists(db):
        return {"high_sev_or_pri": 0, "stale": 0, "blocked": 0,
                "regressions_today": regressions_count, "top": []}
    _con = _sq3.connect(db)
    try:
        rows = _con.execute(
            "SELECT id, title, state, tags, priority, severity, changed_date "
            "FROM board_items WHERE board='support' AND state IS NOT NULL AND state != 'Closed'"
        ).fetchall()
    finally:
        _con.close()
    items = [{"id": r[0], "title": r[1], "state": r[2], "tags": r[3],
              "priority": r[4], "severity": r[5], "changed_date": r[6]} for r in rows]
    high = [w for w in items if (_sev(w.get("severity")) in HIGH_SEV) or (w.get("priority") in (0, 1))]
    stale = [w for w in items if _stale(w, hadi_config.STALE_WORK_ITEM_HOURS)]
    blocked = [w for w in items if "blocked" in (w.get("tags") or "").lower()]
    return {
        "high_sev_or_pri": len(high),
        "stale": len(stale),
        "blocked": len(blocked),
        "regressions_today": regressions_count,
        "top": [{"id": w["id"], "title": (w["title"] or "")[:60],
                 "state": w["state"], "severity": w.get("severity")} for w in sorted(high, key=lambda w: (w["priority"] if w["priority"] is not None else 99, _sev_rank(w.get("severity"))))[:8]],
    }


def board_snapshot():
    """Current board-item state from ado_snapshot.db."""
    import sqlite3 as _sq3, os as _os
    db = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "data", "ado_snapshot.db")
    if not _os.path.exists(db):
        return {}
    con = _sq3.connect(db)
    try:
        rows = con.execute("SELECT state FROM board_items WHERE board='support' AND state IS NOT NULL AND state != 'Closed'").fetchall()
    except Exception:
        return {}
    finally:
        con.close()

    # Exact column order from the Support Team board
    BOARD_ORDER = [
        "New",
        "Reviewed/Valid/Prioritized",
        "PO Review",
        "Active",
        "Blocked",
        "Feedback",
        "Resolved",
        "Pending Deployment",
        "Rejected",
        "Deployed",
    ]
    counts = {}
    for (st,) in rows:
        counts[st or "Unknown"] = counts.get(st or "Unknown", 0) + 1

    by_state = {s: counts[s] for s in BOARD_ORDER if counts.get(s, 0) > 0}
    for s, c in counts.items():
        if s not in by_state and c > 0:
            by_state[s] = c

    return {
        "by_state": by_state,
        "total": len(rows),
        "blocked": counts.get("Blocked", 0),
        "pending_deploy": counts.get("Pending Deployment", 0),
        "active": counts.get("Active", 0),
        "new_items": counts.get("New", 0),
        "resolved": counts.get("Resolved", 0),
        "deployed": counts.get("Deployed", 0),
        "rejected": counts.get("Rejected", 0),
        "feedback": counts.get("Feedback", 0),
    }

def _weekly_board_stats(start_iso, end_iso):
    """Weekly activity derived from board_items changed_date/created_date."""
    import sqlite3 as _sq3, os as _os
    db = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "data", "ado_snapshot.db")
    if not _os.path.exists(db):
        return {}
    con = _sq3.connect(db)
    try:
        def _q(sql, p): return con.execute(sql, p).fetchone()[0]
        s, e = start_iso, end_iso
        resolved = _q(
            "SELECT COUNT(*) FROM board_items WHERE state IN ('Resolved','Deployed') AND board='support' "
            "AND substr(changed_date,1,10)>=? AND substr(changed_date,1,10)<=?", (s, e))
        created = _q(
            "SELECT COUNT(*) FROM board_items "
            "WHERE board='support' AND substr(created_date,1,10)>=? AND substr(created_date,1,10)<=?", (s, e))
        newly_blocked = _q(
            "SELECT COUNT(*) FROM board_items WHERE state='Blocked' AND board='support' "
            "AND substr(changed_date,1,10)>=? AND substr(changed_date,1,10)<=?", (s, e))
        pending = _q(
            "SELECT COUNT(*) FROM board_items WHERE state='Pending Deployment' AND board='support' "
            "AND substr(changed_date,1,10)>=? AND substr(changed_date,1,10)<=?", (s, e))
        ci = con.execute(
            "SELECT id, title, state, priority FROM board_items "
            "WHERE state IN ('Resolved','Deployed') AND board='support' "
            "AND substr(changed_date,1,10)>=? AND substr(changed_date,1,10)<=? "
            "ORDER BY changed_date DESC", (s, e)).fetchall()
    except Exception:
        return {}
    finally:
        con.close()
    return {
        "resolved": resolved, "created": created,
        "newly_blocked": newly_blocked, "pending": pending,
        "resolved_items": [{"id": r[0], "title": r[1], "state": r[2], "priority": r[3]} for r in ci],
    }

def format_daily(s):
    snap = board_snapshot()
    L = [f"📋 **ملخص البورد — {s['date']}**", ""]

    if snap and snap.get("total", 0) > 0:
        by_state = snap.get("by_state", {})
        EMOJIS = {
            "New": "📥",
            "Reviewed/Valid/Prioritized": "✅",
            "PO Review": "👀",
            "Active": "🔨",
            "Blocked": "🔴",
            "Feedback": "💬",
            "Resolved": "✔️",
            "Pending Deployment": "🚦",
            "Rejected": "❌",
            "Deployed": "🚀",
        }
        L.append("**📊 حالة البورد الآن**")
        for state, count in by_state.items():
            emoji = EMOJIS.get(state, "•")
            L.append(f"{emoji} {state}: **{count}**")
        L.append(f"_إجمالي: {snap['total']}_")
        L.append("")

    created   = s.get("created", 0)
    updates   = s.get("meaningful_updates", 0)
    completed = s.get("completed", 0)
    qa_in     = s.get("qa_entered", 0)
    if created or updates or completed or qa_in:
        L.append("**📈 نشاط اليوم**")
        parts = []
        if created:   parts.append(f"➕ New: {created}")
        if updates:   parts.append(f"🔄 تحديثات: {updates}")
        if completed: parts.append(f"✔️ Resolved: {completed}")
        if qa_in:     parts.append(f"🚦 Pending Deployment: {qa_in}")
        L.append("  ".join(parts))
        L.append("")

    if s.get("status_movements"):
        moves = " · ".join(f"{k}: {v}" for k, v in s["status_movements"].items())
        L.append(f"🔀 تغيير الحالات: {moves}")
        L.append("")

    if s.get("releases"):
        L.append(f"🚀 Deployed النهارده: {s['releases']}")
        L.append("")

    r = s.get("risks") or {}
    high        = r.get("high_sev_pri", 0)
    stale       = r.get("stale", 0)
    regressions = r.get("regressions_today", 0)
    blocked_r   = snap.get("blocked", 0) if snap else r.get("blocked", 0)
    risk_parts  = []
    if high:        risk_parts.append(f"🔥 عالي الخطورة: {high}")
    if blocked_r:   risk_parts.append(f"🔴 Blocked: {blocked_r}")
    if stale:       risk_parts.append(f"😴 Stale: {stale}")
    if regressions: risk_parts.append(f"⚠️ Regression: {regressions}")
    if risk_parts:
        L.append("**⚠️ مخاطر**")
        L.append("  ".join(risk_parts))
        for t in (r.get("top") or [])[:5]:
            L.append(f"  › #{t['id']} [{t['state']}] {t['title'][:60]}")

    return "\n".join(L)

def format_smoke_bc(s):
    L = ["🧪 **تقرير Smoke + BC**"]
    if not s["candidates"]:
        L.append("مفيش عناصر Smoke/BC ظاهرة دلوقتي (اتأكد من إشارة التسجيل).")
    for c in s["candidates"][:30]:
        L.append(f"• #{c['id']} [{c['state']}] {c['title']} — tester: {c['assignee']}")
    for w in s["warnings"]:
        L.append(f"⚠️ {w}")
    L.append(f"_({s['note']})_")
    return "\n".join(L)


# --------------------------------------------------------------------------
# #7 weekly engineering report + health status
# --------------------------------------------------------------------------
def weekly_engineering(end_date=None, con=None):
    con = workitems._con(con)
    end = end_date or datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    start = (datetime.date.fromisoformat(end) - datetime.timedelta(days=7)).isoformat()
    evs = workitems.events(since=f"{start}T00:00:00", until=f"{end}T23:59:59.999999Z",
                           meaningful_only=True, con=con)
    items = workitems.all_work_items(con=con)
    open_items = _open(items)
    status_evs = [e for e in evs if e["field"] == "System.State"]

    completed = len({e["work_item_id"] for e in status_evs if e["new_category"] == "closed"})
    reopened = len([e for e in evs if e["event_type"] == "REGRESSION"])
    new_items = len([w for w in items if start <= (w.get("created_date") or "")[:10] <= end])
    blocked = len([w for w in open_items if "blocked" in (w.get("tags") or "").lower()])
    high = len([w for w in open_items if _sev(w["severity"]) in HIGH_SEV or w["priority"] in (0, 1)])
    releases = len([e for e in evs if e["event_type"] == "RELEASE"])

    # #7: سرد الشغل اللي اتقفل الأسبوع بالتفاصيل (title/assignee/priority/severity)
    # — طلب آسر: التقرير يسرد الـ work items مش أرقام مجمّعة بس.
    items_by_id = {w["id"]: w for w in items}
    completed_items, seen = [], set()
    for e in status_evs:
        wid = e["work_item_id"]
        if e["new_category"] != "closed" or wid in seen:
            continue
        seen.add(wid)
        w = items_by_id.get(wid)
        if w:
            completed_items.append({"id": w["id"], "title": (w["title"] or "")[:70],
                                    "assignee": w.get("assignee") or "—",
                                    "priority": w["priority"], "severity": w["severity"],
                                    "type": w.get("type")})
        else:  # اتقفل بس مش في المير الحالي — نبيّنه من غير ما نخترع تفاصيل
            completed_items.append({"id": wid, "title": "(اتقفل — مش في المير الحالي)",
                                    "assignee": "—", "priority": None,
                                    "severity": None, "type": None})
    completed_items.sort(key=lambda w: (w["priority"] if w["priority"] is not None else 99,
                                        _sev_rank(w["severity"])))

    health = _health(open_items, evs, con)
    return {"start": start, "end": end, "completed": completed, "new": new_items,
            "reopened": reopened, "blocked": blocked, "high_sev_pri": high,
            "releases": releases, "in_progress": len([w for w in open_items
                                                      if hadi_config.state_category(w["state"]) == "active"]),
            "completed_items": completed_items, "health": health}


def _status(color, evidence):
    return {"status": color, "evidence": evidence}


def _health(open_items, evs, con):
    regr = len([e for e in evs if e["event_type"] == "REGRESSION"])
    high = len([w for w in open_items if _sev(w["severity"]) in HIGH_SEV or w["priority"] in (0, 1)])
    blocked = len([w for w in open_items if "blocked" in (w.get("tags") or "").lower()])
    stale = len([w for w in open_items if _stale(w, hadi_config.STALE_WORK_ITEM_HOURS)])
    qa = len([e for e in evs if e["event_type"] == "QA_UPDATE"])
    rel = len([e for e in evs if e["event_type"] == "RELEASE"])
    has_mon = con.execute("SELECT COUNT(*) FROM monitoring_snapshots").fetchone()[0] > 0

    def band(n, warn, bad):
        return "GREEN" if n < warn else ("YELLOW" if n < bad else "RED")

    return {
        "WorkItems": _status(band(stale, 3, 8), f"{stale} راكد"),
        "QA": _status("GREEN" if qa else "UNKNOWN", f"{qa} حدث QA الأسبوع"),
        "Releases": _status("GREEN" if rel else "UNKNOWN", f"{rel} إصدار"),
        "Regressions": _status("GREEN" if regr == 0 else "RED", f"{regr} ريجريشن"),
        "HighSeverity": _status("GREEN" if high == 0 else ("YELLOW" if high < 3 else "RED"), f"{high} عالي"),
        "Blocked": _status(band(blocked, 2, 5), f"{blocked} blocked"),
        "Crashlytics": _status("GREEN" if has_mon else "UNKNOWN", "متصل" if has_mon else "مفيش بيانات"),
        "Seq": _status("GREEN" if has_mon else "UNKNOWN", "متصل" if has_mon else "مفيش بيانات"),
    }


def format_weekly(s):
    snap   = board_snapshot()
    weekly = _weekly_board_stats(s["start"], s["end"])
    L = [f"📅 **التقرير الأسبوعي — {s['start']} → {s['end']}**", ""]

    if snap and snap.get("total", 0) > 0:
        by_state = snap.get("by_state", {})
        EMOJIS = {
            "New": "📥",
            "Reviewed/Valid/Prioritized": "✅",
            "PO Review": "👀",
            "Active": "🔨",
            "Blocked": "🔴",
            "Feedback": "💬",
            "Resolved": "✔️",
            "Pending Deployment": "🚦",
            "Rejected": "❌",
            "Deployed": "🚀",
        }
        L.append("**📊 حالة البورد الآن**")
        for state, count in by_state.items():
            emoji = EMOJIS.get(state, "•")
            L.append(f"{emoji} {state}: **{count}**")
        L.append(f"_إجمالي: {snap['total']}_")
        L.append("")

    resolved    = weekly.get("resolved", 0) or s.get("completed", 0)
    created     = weekly.get("created", 0)  or s.get("new", 0)
    pending_new = weekly.get("pending", 0)
    blocked_new = weekly.get("newly_blocked", 0)
    releases    = s.get("releases", 0)
    reopened    = s.get("reopened", 0)
    L.append("**📈 نشاط الأسبوع**")
    L.append(f"✔️ Resolved: **{resolved}**  |  ➕ New: **{created}**  |  🚀 Deployed: **{releases}**")
    if pending_new:
        L.append(f"🚦 وصل Pending Deployment: **{pending_new}**")
    if blocked_new:
        L.append(f"🔴 Blocked جديد: **{blocked_new}**")
    if reopened:
        L.append(f"🔁 Reopened: {reopened}")
    L.append("")

    ci = weekly.get("resolved_items") or s.get("completed_items") or []
    if ci:
        L.append(f"**✔️ Resolved الأسبوع ({len(ci)})**")
        for w in ci[:40]:
            pri = "-" if w.get("priority") is None else f"P{w['priority']}"
            L.append(f"  · #{w['id']} [{pri}] {str(w.get('title',''))[:60]}")
        if len(ci) > 40:
            L.append(f"  _+{len(ci) - 40} more_")
        L.append("")

    health = s.get("health") or {}
    if health:
        L.append("**🩺 Engineering Health**")
        for k, v in health.items():
            dot = {"GREEN": "🟢", "YELLOW": "🟡", "RED": "🔴"}.get(v["status"], "🔵")
            L.append(f"  {dot} {k}: {v['status']} — {v['evidence']}")

    return "\n".join(L)

def release_digest(days=1, end_date=None, con=None):
    con = workitems._con(con)
    end = end_date or datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    start = (datetime.date.fromisoformat(end) - datetime.timedelta(days=days)).isoformat()
    rel_evs = workitems.events(since=f"{start}T00:00:00", until=f"{end}T23:59:59.999999Z",
                               types=["RELEASE"], con=con)
    items = {w["id"]: w for w in workitems.all_work_items(con=con)}
    released = [items.get(e["work_item_id"], {"id": e["work_item_id"]}) for e in rel_evs]
    by_type = Counter((w.get("type") or "?") for w in released)
    high = [w for w in released if _sev(w.get("severity")) in HIGH_SEV]
    return {"start": start, "end": end, "count": len(released), "by_type": dict(by_type),
            "high_risk": len(high),
            "items": [{"id": w.get("id"), "title": (w.get("title") or "")[:60],
                       "type": w.get("type")} for w in released[:40]],
            "note": "التجميع حسب النوع؛ تجميع بالإصدار/النسخة محتاج field الإصدار (لسه غير مؤكد)."}


def format_release(s):
    if not s["count"]:
        return "🚀 **تقرير الإصدار**\nمفيش عناصر اترحّلت (Released) في الفترة."
    L = [f"🚀 **تقرير الإصدار — {s['start']} → {s['end']}**",
         f"• إجمالي المُصدَر: {s['count']} · عالي الخطورة: {s['high_risk']}",
         "• حسب النوع: " + " · ".join(f"{k}: {v}" for k, v in s["by_type"].items())]
    for it in s["items"][:20]:
        L.append(f"   - #{it['id']} [{it['type']}] {it['title']}")
    L.append(f"_({s['note']})_")
    return "\n".join(L)
