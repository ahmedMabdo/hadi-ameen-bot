#!/usr/bin/env python3
"""
ado_alerts.py - proactive alerts for Hadi (modules C3-C8). READ-ONLY.

Reads the local snapshot (ado_snapshot.db, produced by ado_snapshot.py) and
computes proactive notifications. NEVER writes to ADO. Notifications only.

Alerts:
  blocked    items tagged `Blocked` stuck >= N working days (default 2)     [C3]
  master     `master` stories not started near sprint end                    [C4]
  fm         `FM` (Feature Management) stories - shipped-closed tracking      [C5]
  unplanned  `up` stories that entered the sprint                            [C6]
  risk       sprint-risk signal (open ratio vs remaining time)              [C7]
  leave      capacity days-off + conflicts with owners of master/blocked     [C8]
  all        run everything (default)

Every output carries the snapshot freshness banner. If the snapshot is RED
(stale/failed), alerts are SUPPRESSED with a warning - never alert on stale data.

Optional: set DISCORD_WEBHOOK_URL to POST a compact summary to a channel.
Thresholds via env: ADO_BLOCKED_DAYS=2, ADO_NEAR_END_DAYS=3,
                    ADO_RISK_OPEN_PCT=40, ADO_RISK_TIME_PCT=30.
"""
import os
import sys
import json
import argparse
import datetime
import urllib.request

import ado_snapshot as snap

BLOCKED_DAYS = int(os.environ.get("ADO_BLOCKED_DAYS", "2"))
NEAR_END_DAYS = int(os.environ.get("ADO_NEAR_END_DAYS", "3"))
RISK_OPEN_PCT = float(os.environ.get("ADO_RISK_OPEN_PCT", "40"))
RISK_TIME_PCT = float(os.environ.get("ADO_RISK_TIME_PCT", "30"))
WEBHOOK = os.environ.get("DISCORD_WEBHOOK_URL", "")

DONE_STATES = {"closed", "done", "completed", "resolved", "removed", "accepted"}
NOT_STARTED = {"new", "acknowledged", "approved", "to do", "proposed"}


def _now():
    return datetime.datetime.now(datetime.timezone.utc)


def _parse(dtiso):
    if not dtiso:
        return None
    try:
        return datetime.datetime.fromisoformat(str(dtiso).replace("Z", "+00:00"))
    except ValueError:
        return None


def _working_days_between(a, b):
    if not a or not b or b <= a:
        return 0
    d, n = a, 0
    while d.date() < b.date():
        if d.weekday() in snap.WORK_DAYS:
            n += 1
        d += datetime.timedelta(days=1)
    return n


def _has_tag(row, tag):
    return any(t.lower() == tag.lower() for t in snap._tags_list(row["tags"]))


# ----------------------------- alerts -----------------------------
def a_blocked(con):
    since = {r["id"]: r["blocked_since"] for r in con.execute("SELECT id,blocked_since FROM blocked_state")}
    out = []
    for r in snap._rows(con):
        if r["id"] in since:
            wd = snap._working_days(since[r["id"]])
            if wd >= BLOCKED_DAYS:
                out.append({"id": r["id"], "title": r["title"], "state": r["state"],
                            "assigned_to": r["assigned_to"], "blocked_working_days": wd})
    return sorted(out, key=lambda x: -x["blocked_working_days"])


def a_master(con, meta):
    finish = _parse(meta.get("sprint_finish"))
    left = _working_days_between(_now(), finish) if finish else 999
    out = []
    for r in snap._rows(con, "is_top=1"):
        if _has_tag(r, "master") and (r["state"] or "").lower() in NOT_STARTED and left <= NEAR_END_DAYS:
            out.append({"id": r["id"], "title": r["title"], "state": r["state"],
                        "assigned_to": r["assigned_to"], "working_days_left": left})
    return out


def a_fm(con):
    out = []
    for r in snap._rows(con, "is_top=1"):
        if _has_tag(r, "FM"):
            done = (r["state"] or "").lower() in DONE_STATES
            out.append({"id": r["id"], "title": r["title"], "state": r["state"],
                        "assigned_to": r["assigned_to"],
                        "ready_to_open_after_release": done})
    return out


def a_unplanned(con):
    out = []
    for r in snap._rows(con, "is_top=1"):
        if _has_tag(r, "up"):
            out.append({"id": r["id"], "title": r["title"], "state": r["state"],
                        "assigned_to": r["assigned_to"]})
    return out


def a_risk(con, meta):
    tops = snap._rows(con, "is_top=1")
    if not tops:
        return {"risk": False, "reason": "no items"}
    open_n = sum(1 for r in tops if (r["state"] or "").lower() not in DONE_STATES)
    open_pct = round(100.0 * open_n / len(tops), 1)
    start, finish, now = _parse(meta.get("sprint_start")), _parse(meta.get("sprint_finish")), _now()
    remaining_pct = None
    if start and finish and finish > start:
        remaining_pct = round(max(0.0, min(100.0, 100.0 * (finish - now).total_seconds() / (finish - start).total_seconds())), 1)
    risk = bool(remaining_pct is not None and open_pct > RISK_OPEN_PCT and remaining_pct < RISK_TIME_PCT)
    return {"risk": risk, "open_pct": open_pct, "open_items": open_n,
            "total_items": len(tops), "remaining_time_pct": remaining_pct}


def a_leave(con):
    today = _now().date()
    on_leave, owners = [], {}
    for r in snap._rows(con, "is_top=1"):
        who = (r["assigned_to"] or "").strip()
        if who and (_has_tag(r, "master") or _has_tag(r, "Blocked")) and (r["state"] or "").lower() not in DONE_STATES:
            owners.setdefault(who.lower(), []).append({"id": r["id"], "title": r["title"]})
    conflicts = []
    for c in con.execute("SELECT * FROM capacity"):
        member = c["member"] or ""
        for off in json.loads(c["days_off"] or "[]"):
            e = _parse(off.get("end"))
            if e and e.date() >= today:
                entry = {"member": member, "start": (off.get("start") or "")[:10],
                         "end": (off.get("end") or "")[:10]}
                on_leave.append(entry)
                hit = owners.get(member.lower())
                if hit:
                    conflicts.append({**entry, "owns": hit})
    return {"upcoming_days_off": on_leave, "conflicts": conflicts}


# ----------------------------- run -----------------------------
def run(which):
    con = snap._db()
    snap._init(con)
    try:
        fr = snap.freshness(con)
        head = snap.banner(con)
        if fr["label"] == "DOWN":
            print(head)
            print("ALERTS SUPPRESSED: snapshot is stale/failed - refusing to alert on stale data.")
            return 2
        meta = snap._meta(con)
        res = {"freshness": fr}
        if which in ("all", "blocked"):
            res["blocked"] = a_blocked(con)
        if which in ("all", "master"):
            res["master_not_started"] = a_master(con, meta)
        if which in ("all", "fm"):
            res["feature_management"] = a_fm(con)
        if which in ("all", "unplanned"):
            res["unplanned"] = a_unplanned(con)
        if which in ("all", "risk"):
            res["sprint_risk"] = a_risk(con, meta)
        if which in ("all", "leave"):
            res["leave"] = a_leave(con)
        print(head)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        if WEBHOOK:
            _post_discord(_summary(res, meta, con))
        return 0
    finally:
        con.close()


def _summary(res, meta, con=None):
    # 2026-07-26: كان snap.banner_from(...) — دالة مش موجودة في ado_snapshot،
    # فالـ hasattr كان دايمًا False والسطر دايمًا "". يعني ملخص الـ webhook كان
    # بيروح من غير بانر النضارة، وهو أهم سطر في فلسفة المشروع.
    fr = res.get("freshness") or {}
    banner = (f"{fr.get('emoji','')} {fr.get('label','?')} "
              f"(snapshot age {fr.get('age_min','?')}m)").strip()
    lines = [f"**تنبيهات هادي — {meta.get('sprint_name','')}**", banner]
    b = res.get("blocked") or []
    if b:
        lines.append(f"🚧 متبلوك ({len(b)}): " + "، ".join(f"#{x['id']} ({x['blocked_working_days']}ي)" for x in b[:5]))
    m = res.get("master_not_started") or []
    if m:
        lines.append(f"🔴 master لسه ماابتدتش ({len(m)}): " + "، ".join(f"#{x['id']}" for x in m[:5]))
    r = res.get("sprint_risk") or {}
    if r.get("risk"):
        lines.append(f"⚠️ خطر سبرنت: مفتوح {r.get('open_pct')}% ووقت متبقّي {r.get('remaining_time_pct')}%")
    lv = (res.get("leave") or {}).get("conflicts") or []
    if lv:
        lines.append(f"🌴 تعارض إجازات ({len(lv)}): " + "، ".join(x["member"] for x in lv[:5]))
    return "\n".join(x for x in lines if x) or "لا يوجد تنبيهات."


def _post_discord(text):
    try:
        data = json.dumps({"content": text[:1900]}).encode()
        req = urllib.request.Request(WEBHOOK, data=data,
                                     headers={"Content-Type": "application/json"}, method="POST")
        urllib.request.urlopen(req, timeout=15)
    except Exception as e:  # noqa
        print("WARN: discord post failed:", e)


def main():
    p = argparse.ArgumentParser(description="Hadi proactive ADO alerts (read-only).")
    p.add_argument("which", nargs="?", default="all",
                   choices=["all", "blocked", "master", "fm", "unplanned", "risk", "leave"])
    a = p.parse_args()
    sys.exit(run(a.which))


if __name__ == "__main__":
    main()
