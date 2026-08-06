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


def format_daily(s):
    L = [f"📋 **ملخص البورد — {s['date']}**",
         f"• جديد: {s['created']} · تحديثات مؤثرة: {s['meaningful_updates']} · "
         f"مكتمل: {s['completed']} · دخل QA: {s['qa_entered']}"]
    if s["status_movements"]:
        moves = " · ".join(f"{k}: {v}" for k, v in s["status_movements"].items())
        L.append(f"• حركة الحالات: {moves}")
    if s["releases"]:
        L.append(f"• 🚀 إصدارات النهاردة: {s['releases']}")
    if s["by_severity"]:
        L.append("• الخطورة (مفتوح): " + " · ".join(f"{k}: {v}" for k, v in s["by_severity"].items()))
    r = s["risks"]
    L.append(f"• ⚠️ مخاطر: عالي الخطورة/الأولوية {r['high_sev_or_pri']} · راكد {r['stale']} · "
             f"blocked {r['blocked']} · ريجريشن {r['regressions_today']}")
    for t in r["top"]:
        L.append(f"   - #{t['id']} [{t['state']}] {t['title']}")
    return "\n".join(L)


# --------------------------------------------------------------------------
# #6 Wednesday Smoke / BC — flags DATA MISSING, never fabricates results
# --------------------------------------------------------------------------
def smoke_bc(date=None, con=None):
    con = workitems._con(con)
    items = workitems.all_work_items(con=con)
    need = [w for w in items
            if any(k in (w.get("tags") or "").lower() for k in ("smoke", "bc"))
            or hadi_config.state_category(w["state"]) == "qa"]
    ready_no_tester = [w for w in items
                       if hadi_config.state_category(w["state"]) == "qa"
                       and not (w.get("assignee"))]
    warnings = []
    if ready_no_tester:
        warnings.append(f"DATA MISSING: {len(ready_no_tester)} عنصر Ready-for-QA من غير tester/تحديث.")
    return {
        "candidates": [{"id": w["id"], "title": (w["title"] or "")[:70], "state": w["state"],
                        "assignee": w.get("assignee") or "—", "severity": w["severity"],
                        "priority": w["priority"]} for w in need],
        "warnings": warnings,
        "note": ("Smoke/BC signal مفترض من tags/state — أكّده بعد ما نعرف إزاي متسجّل فعليًا."),
    }


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

    health = _health(open_items, evs, con)
    return {"start": start, "end": end, "completed": completed, "new": new_items,
            "reopened": reopened, "blocked": blocked, "high_sev_pri": high,
            "releases": releases, "in_progress": len([w for w in open_items
                                                      if hadi_config.state_category(w["state"]) == "active"]),
            "health": health}


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
    L = [f"🗓️ **التقرير الأسبوعي — {s['start']} → {s['end']}**",
         f"• مكتمل: {s['completed']} · شغّال: {s['in_progress']} · جديد: {s['new']} · "
         f"blocked: {s['blocked']} · reopened: {s['reopened']} · إصدارات: {s['releases']}",
         f"• عالي الخطورة/الأولوية مفتوح: {s['high_sev_pri']}",
         "**صحة الهندسة:**"]
    for k, v in s["health"].items():
        dot = {"GREEN": "🟢", "YELLOW": "🟡", "RED": "🔴", "UNKNOWN": "⚪"}.get(v["status"], "⚪")
        L.append(f"   {dot} {k}: {v['status']} — {v['evidence']}")
    return "\n".join(L)


# --------------------------------------------------------------------------
# #8 release digest — released work items grouped by type
# --------------------------------------------------------------------------
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
