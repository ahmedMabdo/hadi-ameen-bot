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

    risks = _risks(open_items, regressions, con)
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


def _risks(open_items, regressions, con):
    high = [w for w in open_items if (_sev(w["severity"]) in HIGH_SEV) or (w["priority"] in (0, 1))]
    stale = [w for w in open_items if _stale(w, hadi_config.STALE_WORK_ITEM_HOURS)]
    blocked = [w for w in open_items if "blocked" in (w.get("tags") or "").lower()]
    return {
        "high_sev_or_pri": len(high),
        "stale": len(stale),
        "blocked": len(blocked),
        "regressions_today": len(regressions),
        "top": [{"id": w["id"], "title": (w["title"] or "")[:60],
                 "state": w["state"], "severity": w["severity"]} for w in high[:8]],
    }


def board_snapshot():
    """Current board-item state from ado_snapshot.db."""
    import sqlite3 as _sq3, os as _os
    db = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "data", "ado_snapshot.db")
    if not _os.path.exists(db):
        return {}
    con = _sq3.connect(db)
    try:
        rows = con.execute("SELECT state FROM board_items").fetchall()
    except Exception:
        return {}
    finally:
        con.close()
    counts = {}
    for (st,) in rows:
        counts[st or "Unknown"] = counts.get(st or "Unknown", 0) + 1
    active    = sum(counts.get(s, 0) for s in ["In Development", "In Progress", "Active", "Confirmed"])
    qa        = sum(counts.get(s, 0) for s in ["Test case ready", "Reviewed"])
    blocked   = counts.get("Blocked", 0)
    pending   = sum(counts.get(s, 0) for s in ["Pending Deployment", "Pending For Release"])
    new_items = sum(counts.get(s, 0) for s in ["New", "Planned", "Design"])
    done      = sum(counts.get(s, 0) for s in ["Closed", "Solved"])
    return {
        "active": active, "qa": qa, "blocked": blocked,
        "pending_deploy": pending, "new_planned": new_items,
        "done_total": done, "total": len(rows), "raw": counts,
    }


def format_daily(s):
    snap = board_snapshot()
    L = [f"📋 **ملخص البورد — {s['date']}**", ""]

    if snap and snap.get("total", 0) > 0:
        L.append("**📊 حالة البورد الآن**")
        L.append(
            f"🔨 شغل نشط: **{snap['active']}**  |  "
            f"🧪 QA: **{snap['qa']}**  |  "
            f"🚦 Pending Deploy: **{snap['pending_deploy']}**"
        )
        if snap["blocked"]:
            L.append(f"🔴 Blocked: **{snap['blocked']}**")
        L.append(f"📌 New/Planned: {snap['new_planned']}  |  ✅ مكتمل اليوم: {s.get('completed', 0)}")
        L.append("")

    created   = s.get("created", 0)
    updates   = s.get("meaningful_updates", 0)
    completed = s.get("completed", 0)
    qa_in     = s.get("qa_entered", 0)
    if created or updates or completed or qa_in:
        L.append("**📈 نشاط اليوم**")
        parts = []
        if created:   parts.append(f"➕ جديد: {created}")
        if updates:   parts.append(f"🔄 تحديثات: {updates}")
        if completed: parts.append(f"✅ مكتمل: {completed}")
        if qa_in:     parts.append(f"🧪 دخل QA: {qa_in}")
        L.append("  ".join(parts))
        L.append("")

    if s.get("status_movements"):
        moves = " · ".join(f"{k}: {v}" for k, v in s["status_movements"].items())
        L.append(f"🔀 حركة الحالات: {moves}")
        L.append("")

    if s.get("releases"):
        L.append(f"🚀 إصدارات النهارده: {s['releases']}")
        L.append("")

    r = s.get("risks") or {}
    high        = r.get("high_sev_pri", 0)
    stale       = r.get("stale", 0)
    regressions = r.get("regressions_today", 0)
    blocked_r   = snap.get("blocked", 0) if snap else r.get("blocked", 0)
    risk_parts  = []
    if high:        risk_parts.append(f"🔥 عالي الخطورة: {high}")
    if blocked_r:   risk_parts.append(f"🚧 Blocked: {blocked_r}")
    if stale:       risk_parts.append(f"😴 راكد: {stale}")
    if regressions: risk_parts.append(f"⚠️ ريجريشن: {regressions}")
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
    snap = board_snapshot()
    L = [f"📅 **التقرير الأسبوعي — {s['start']} → {s['end']}**", ""]

    if snap and snap.get("total", 0) > 0:
        L.append("**📊 حالة البورد**")
        L.append(
            f"🔨 نشط: **{snap['active']}**  |  "
            f"🧪 QA: **{snap['qa']}**  |  "
            f"🚦 Pending Deploy: **{snap['pending_deploy']}**"
        )
        if snap["blocked"]:
            L.append(f"🔴 Blocked: **{snap['blocked']}**")
        L.append("")

    L.append("**📈 إحصائيات الأسبوع**")
    completed = s.get("completed", 0)
    in_prog   = s.get("in_progress", 0)
    new_items = s.get("new", 0)
    reopened  = s.get("reopened", 0)
    releases  = s.get("releases", 0)
    blocked_w = s.get("blocked", 0)
    L.append(
        f"✅ مكتمل: **{completed}**  |  "
        f"🔨 In Progress: **{in_prog}**  |  "
        f"➕ جديد: **{new_items}**"
    )
    if releases:
        L.append(f"🚀 إصدارات: **{releases}**")
    if reopened:
        L.append(f"🔁 فُتحت تاني: {reopened}")
    if blocked_w:
        L.append(f"🚧 Blocked: {blocked_w}")
    L.append("")

    ci = s.get("completed_items") or []
    if ci:
        L.append(f"**✅ المُغلق الأسبوع ({len(ci)})**")
        for w in ci[:40]:
            pri = "-" if w["priority"] is None else f"P{w['priority']}"
            sev = w.get("severity") or "-"
            L.append(f"  · #{w['id']} [{pri}·{sev}] {w['title'][:60]}")
        if len(ci) > 40:
            L.append(f"  _+{len(ci) - 40} عنصر تاني_")
        L.append("")

    health = s.get("health") or {}
    if health:
        L.append("**🩺 صحة الهندسة**")
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
