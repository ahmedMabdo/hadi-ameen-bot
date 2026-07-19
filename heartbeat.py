#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""نبضة هادي — الاستباقية (بند 8.1 و8.3).

النقلة اللي التقرير بيسميها «الفرق النوعي»: هادي يمسك المشكلة قبل ما حد يسأل،
بدل ما يستنى النداء.

الفلسفة (مهمة): **نفس فلسفة NO_REPLY** — النبضة بتشتغل كل ساعة، ولو مفيش حاجة
تستاهل بتسكت تمامًا. تنبيه من غير داعي أسوأ من مفيش تنبيه، لأنه بيخلي الفريق
يتجاهل التنبيهات كلها.

الفحوصات (8.1):
  stale_p1        تذكرة P1/P0 مفتوحة وواقفة من غير حركة > HADI_HB_STALE_DAYS
  sprint_tomorrow سيكون بكرة من knowledge/sprints.md
  support_48h     نقطة سابورت متتبعة في followup_pending.json عدت 48 ساعة من غير رد

الأحداث (8.3):
  release_day     يوم الريليز (من sprints.md) → يقترح تقرير regression الصبح
  new_sprint      iteration جديد ظهر على ADO → تحديث الذاكرة + سؤال عن الناقص

ضوابط ضد الإزعاج:
  - **كل تنبيه بيتبعت مرة واحدة بس** لكل عنصر خلال HADI_HB_COOLDOWN_HOURS (افتراضي 24).
  - ساعات الشغل بس (HADI_HB_QUIET_START/END بتوقيت القاهرة) — مفيش نبضة بالليل.
  - الحالة في logs/heartbeat_state.json (حالة تشغيل محلية، مش في git).
  - HADI_HEARTBEAT=off بيوقفها بالكامل من .env من غير تعديل كود.

CLI (للتجربة من غير إرسال):
    heartbeat.py check            # يطبع اللي كان هيتبعت — مفيش إرسال
    heartbeat.py state            # آخر التنبيهات المتبعتة
    heartbeat.py selftest
"""
import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from zoneinfo import ZoneInfo

BASE = Path(__file__).resolve().parent
STATE_FILE = BASE / "logs" / "heartbeat_state.json"
SPRINTS = BASE / "knowledge" / "sprints.md"
FOLLOWUP = BASE / "followup_pending.json"
TZ = ZoneInfo("Africa/Cairo")

ENABLED = (os.environ.get("HADI_HEARTBEAT", "on").strip().lower() != "off")
STALE_DAYS = int(os.environ.get("HADI_HB_STALE_DAYS", "3") or "3")
SUPPORT_HOURS = int(os.environ.get("HADI_HB_SUPPORT_HOURS", "48") or "48")
COOLDOWN_H = float(os.environ.get("HADI_HB_COOLDOWN_HOURS", "24") or "24")
QUIET_START = int(os.environ.get("HADI_HB_QUIET_START", "22") or "22")  # 10 مساءً
QUIET_END = int(os.environ.get("HADI_HB_QUIET_END", "9") or "9")        # 9 صباحًا
MAX_ALERTS = int(os.environ.get("HADI_HB_MAX_ALERTS", "3") or "3")      # لكل نبضة


# --- الحالة ----------------------------------------------------------------
def load_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"sent": {}, "seen_iterations": []}


def save_state(state: dict) -> None:
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = STATE_FILE.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(STATE_FILE)
    except Exception as error:
        print(f"HEARTBEAT WARN: حفظ الحالة فشل ({type(error).__name__})")


def recently_sent(state: dict, key: str) -> bool:
    ts = state.get("sent", {}).get(key)
    return bool(ts) and (time.time() - float(ts)) < COOLDOWN_H * 3600


def mark_sent(state: dict, key: str) -> None:
    state.setdefault("sent", {})[key] = time.time()
    cutoff = time.time() - max(COOLDOWN_H, 168) * 3600
    state["sent"] = {k: v for k, v in state["sent"].items() if float(v) > cutoff}


def in_quiet_hours(now=None) -> bool:
    hour = (now or dt.datetime.now(TZ)).hour
    if QUIET_START == QUIET_END:
        return False
    if QUIET_START > QUIET_END:  # يعدّي منتصف الليل
        return hour >= QUIET_START or hour < QUIET_END
    return QUIET_START <= hour < QUIET_END


# --- أدوات -----------------------------------------------------------------
def _ado(*args, timeout=60):
    """نداء ado_cli.py — بيرجّع (نجح؟, stdout)."""
    try:
        result = subprocess.run(
            [sys.executable, str(BASE / "ado_cli.py"), *args],
            capture_output=True, text=True, timeout=timeout, cwd=str(BASE))
        return result.returncode == 0, (result.stdout or result.stderr)
    except Exception as error:
        return False, f"{type(error).__name__}: {error}"


def _parse_iso(value: str):
    try:
        return dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


# --- فحوصات 8.1 ------------------------------------------------------------
def check_stale_p1(state):
    """تذكرة P1/P0 مفتوحة وواقفة من غير حركة — أخطر إشارة إهمال."""
    cutoff = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=STALE_DAYS)).strftime("%Y-%m-%d")
    wiql = (
        "SELECT [System.Id] FROM WorkItems WHERE [System.State] NOT IN ('Closed','Resolved','Removed')"
        " AND [Microsoft.VSTS.Common.Priority] <= 1"
        f" AND [System.ChangedDate] < '{cutoff}'"
    )
    ok, out = _ado("wiql", "--query", wiql)
    if not ok:
        return []
    ids = re.findall(r"\b(\d{4,7})\b", out)[:MAX_ALERTS]
    alerts = []
    for wid in ids:
        key = f"stale_p1:{wid}"
        if recently_sent(state, key):
            continue
        alerts.append({
            "key": key,
            "text": f"⚠️ تذكرة **#{wid}** (P0/P1) مفتوحة وواقفة من غير أي حركة أكتر من {STALE_DAYS} أيام.",
        })
    return alerts


def _sprint_events(today=None):
    """(اسم الحدث، تاريخه) من knowledge/sprints.md — بيقرا أي سطر فيه تاريخ ISO."""
    if not SPRINTS.exists():
        return []
    events = []
    for line in SPRINTS.read_text(encoding="utf-8").splitlines():
        match = re.search(r"(\d{4}-\d{2}-\d{2})", line)
        if not match:
            continue
        date = dt.date.fromisoformat(match.group(1))
        label = re.sub(r"[-*|#>]+", " ", line.replace(match.group(1), "")).strip()
        events.append((label[:120] or "حدث سبرنت", date))
    return events


def check_sprint_tomorrow(state, today=None):
    today = today or dt.datetime.now(TZ).date()
    tomorrow = today + dt.timedelta(days=1)
    alerts = []
    for label, date in _sprint_events():
        if date != tomorrow:
            continue
        key = f"sprint:{date}:{label[:40]}"
        if recently_sent(state, key):
            continue
        alerts.append({"key": key, "text": f"📅 بكرة ({date}): {label} — التجهيز تمام؟"})
    return alerts[:MAX_ALERTS]


def check_support_48h(state, now=None):
    """نقطة سابورت متتبعة عدت الحد من غير رد (من ملف متابعة الروتين اليومي)."""
    if not FOLLOWUP.exists():
        return []
    try:
        data = json.loads(FOLLOWUP.read_text(encoding="utf-8"))
    except Exception:
        return []
    items = data.get("points", data) if isinstance(data, dict) else data
    if not isinstance(items, list):
        return []
    now = now or dt.datetime.now(dt.timezone.utc)
    alerts = []
    for item in items:
        if not isinstance(item, dict) or item.get("resolved") or item.get("answered"):
            continue
        first_seen = _parse_iso(item.get("first_seen") or item.get("date") or item.get("ts") or "")
        if not first_seen:
            continue
        if first_seen.tzinfo is None:
            first_seen = first_seen.replace(tzinfo=dt.timezone.utc)
        hours = (now - first_seen).total_seconds() / 3600
        if hours < SUPPORT_HOURS:
            continue
        ident = str(item.get("id") or item.get("message_id") or item.get("summary", ""))[:40]
        key = f"support:{ident}"
        if recently_sent(state, key):
            continue
        summary = str(item.get("summary") or item.get("text") or "نقطة سابورت")[:140]
        alerts.append({"key": key, "text": f"🕒 نقطة سابورت عدّى عليها {hours:.0f} ساعة من غير رد: {summary}"})
    return alerts[:MAX_ALERTS]


# --- أحداث 8.3 -------------------------------------------------------------
def check_release_day(state, today=None):
    """يوم الريليز → تقرير regression الصبح."""
    today = today or dt.datetime.now(TZ).date()
    for label, date in _sprint_events():
        if date == today and re.search(r"release|ريليز|إصدار|اصدار", label, re.IGNORECASE):
            key = f"release:{date}"
            if recently_sent(state, key):
                return []
            return [{
                "key": key,
                "text": f"🚀 النهاردة يوم الريليز ({label}) — أجهّز تقرير regression؟ رد بـ «اعمل التقرير» وهبدأ.",
            }]
    return []


def check_new_sprint(state):
    """iteration جديد على ADO → تحديث الذاكرة وسؤال عن الناقص (القاعدة مكتوبة أصلًا)."""
    ok, out = _ado("list-iterations")
    if not ok:
        return []
    names = set(re.findall(r"(MS-\d+|Sprint\s*\d+)", out, re.IGNORECASE))
    if not names:
        return []
    seen = set(state.get("seen_iterations") or [])
    fresh = sorted(names - seen)
    state["seen_iterations"] = sorted(seen | names)
    if not seen:  # أول تشغيل: بنسجّل الموجود من غير ما نزعج حد
        return []
    alerts = []
    for name in fresh[:MAX_ALERTS]:
        key = f"sprint_new:{name}"
        if recently_sent(state, key):
            continue
        alerts.append({
            "key": key,
            "text": f"🆕 سبرنت جديد على ADO: **{name}** — محتاج مواعيد السيكونات عشان أحدّث `sprints.md`. تبعتهالي؟",
        })
    return alerts


CHECKS = [
    ("stale_p1", check_stale_p1),
    ("sprint_tomorrow", check_sprint_tomorrow),
    ("support_48h", check_support_48h),
    ("release_day", check_release_day),
    ("new_sprint", check_new_sprint),
]


def run_checks(state=None, dry_run=True):
    """بيرجّع (تنبيهات, الحالة). الصمت لو مفيش حاجة — نفس فلسفة NO_REPLY."""
    state = load_state() if state is None else state
    alerts = []
    for name, func in CHECKS:
        try:
            alerts.extend(func(state))
        except Exception as error:
            print(f"HEARTBEAT WARN: فحص {name} فشل ({type(error).__name__}: {error})")
    alerts = alerts[:MAX_ALERTS]
    if not dry_run:
        for alert in alerts:
            mark_sent(state, alert["key"])
        save_state(state)
    return alerts, state


def format_message(alerts) -> str:
    if not alerts:
        return ""
    head = "نبضة هادي — حاجات محتاجة نظرة:" if len(alerts) > 1 else "نبضة هادي:"
    body = "\n".join(f"• {a['text']}" for a in alerts)
    return f"{head}\n{body}"


# --- اختبار ذاتي ------------------------------------------------------------
def selftest():
    global STATE_FILE, SPRINTS, FOLLOWUP
    import tempfile
    orig = (STATE_FILE, SPRINTS, FOLLOWUP)
    tmp = Path(tempfile.mkdtemp(prefix="hadi_hb_test_"))
    try:
        STATE_FILE = tmp / "state.json"
        SPRINTS = tmp / "sprints.md"
        FOLLOWUP = tmp / "followup.json"
        today = dt.date(2026, 7, 19)
        tomorrow = today + dt.timedelta(days=1)
        SPRINTS.write_text(
            f"# سبرنتات\n- كود فريز {tomorrow}\n- Release MS-92 {today}\n- حاجة قديمة 2026-01-01\n",
            encoding="utf-8")
        old = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=72)).isoformat()
        recent = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=5)).isoformat()
        FOLLOWUP.write_text(json.dumps([
            {"id": "p1", "summary": "شكوى تاجر مستنية رد", "first_seen": old},
            {"id": "p2", "summary": "نقطة جديدة", "first_seen": recent},
            {"id": "p3", "summary": "اتحلت", "first_seen": old, "resolved": True},
        ], ensure_ascii=False), encoding="utf-8")

        state = {"sent": {}, "seen_iterations": []}
        assert len(check_sprint_tomorrow(state, today)) == 1, "حدث بكرة مااتمسكش"
        assert len(check_release_day(state, today)) == 1, "يوم الريليز مااتمسكش"
        sup = check_support_48h(state)
        assert len(sup) == 1 and "شكوى" in sup[0]["text"], f"فحص الـ 48 ساعة: {sup}"

        mark_sent(state, sup[0]["key"])
        assert check_support_48h(state) == [], "التكرار مااتمنعش (cooldown)"

        assert in_quiet_hours(dt.datetime(2026, 7, 19, 3, tzinfo=TZ)) is True, "الليل مش هادي"
        assert in_quiet_hours(dt.datetime(2026, 7, 19, 14, tzinfo=TZ)) is False, "الضهر اتحسب هادي"

        assert format_message([]) == "", "الصمت لازم يبقى فاضي"
        assert "•" in format_message(sup), "التنسيق"
        print("SELFTEST PASS — الفحوصات والـ cooldown وساعات الهدوء والصمت كلهم سليمين")
    finally:
        STATE_FILE, SPRINTS, FOLLOWUP = orig


def main():
    parser = argparse.ArgumentParser(description="نبضة هادي الاستباقية (بند 8.1/8.3)")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check", help="يطبع اللي كان هيتبعت — من غير إرسال ولا تعديل حالة")
    sub.add_parser("state")
    sub.add_parser("selftest")
    args = parser.parse_args()

    if args.cmd == "check":
        alerts, _ = run_checks(dry_run=True)
        print(format_message(alerts) or "(صمت — مفيش حاجة تستاهل تنبيه)")
    elif args.cmd == "state":
        state = load_state()
        sent = state.get("sent", {})
        print(f"تنبيهات متبعتة: {len(sent)} | سبرنتات معروفة: {len(state.get('seen_iterations', []))}")
        for key, ts in sorted(sent.items(), key=lambda kv: -kv[1])[:15]:
            ago = (time.time() - float(ts)) / 3600
            print(f"  {key:44} من {ago:.1f} ساعة")
    elif args.cmd == "selftest":
        selftest()


if __name__ == "__main__":
    main()
