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
    # ado_cli.py wiql بياخد الاستعلام positional مش --query (كان بيرجّع exit 2)
    ok, out = _ado("wiql", wiql)
    if not ok:
        return []
    # ado_cli.py wiql بيطبع list من dicts فيها "id" — مش {"workItems": [...]}.
    # الشكل القديم كان بيرمي AttributeError وبيتبلع، فالفحص ده عمره ما اشتغل.
    try:
        rows = json.loads(out)
    except json.JSONDecodeError:
        return []
    if isinstance(rows, dict):  # توافق لو الشكل اتغير
        rows = rows.get("workItems", [])
    if not isinstance(rows, list):
        return []
    ids = [str(r.get("id")) for r in rows if isinstance(r, dict) and r.get("id")]
    ids = ids[:MAX_ALERTS]
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
    """نقطة مفتوحة عدّى عليها الحد من غير رد — من مخزن المتابعة الموحّد.

    قبل كده كان بيقرا followup_pending.json مباشرة، والملف فضل [] لأن الروتين
    اللي بيشتغل (daily_digests) ماكانش موصول بأداة الـ pending أصلًا — فالفحص
    ده عمره ما اشتغل على داتا حقيقية. دلوقتي بيقرا نفس المخزن اللي الملخصات
    بتكتب فيه، وبيغطي التلات قنوات مش الدعم بس.
    """
    try:
        import followup_store
        rows = followup_store.all_open()
    except Exception as error:
        print(f"HEARTBEAT WARN: مخزن المتابعة مش متاح ({type(error).__name__}: {error})")
        return []

    today = dt.datetime.now(TZ).date()
    min_days = max(1, SUPPORT_HOURS // 24)
    alerts = []
    for item in rows:
        try:
            days = followup_store.age_days(item, today)
        except Exception:
            continue
        if days < min_days:
            continue
        key = f"support:{item.get('digest', '?')}:{item.get('id', '')}"
        if recently_sent(state, key):
            continue
        who = item.get("owner") or "مش محدد"
        alerts.append({
            "key": key,
            "text": (f"🕒 نقطة مفتوحة من {days} يوم في {item.get('digest', '?')} "
                     f"(المسؤول: {who}): {str(item.get('content', ''))[:140]}"),
        })
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


# --- فحوصات صحة النظام نفسه (2026-07-26) --------------------------------
# heartbeat كان بيراقب الشغل (تذاكر/سبرنت) ومش بيراقب **نفسه**. النتيجة: حادثة
# 2026-07-23 (رصيد Claude خلص + CLI مسجّل خارج) عدّت من غير أي تنبيه.
def check_error_rate(state):
    """معدل فشل التفاعلات فوق الحد → تنبيه بنص أكتر خطأ متكرر."""
    try:
        import eval_store
        st = eval_store.error_rate(days=7)
    except Exception as error:
        print(f"HEARTBEAT WARN: eval_store مش متاح ({type(error).__name__}: {error})")
        return []
    limit = float(os.environ.get("HADI_HB_ERROR_PCT", "5") or "5")
    if st["total"] < 10 or st["pct"] < limit:
        return []
    key = f"errrate:{int(st['pct'])}"
    if recently_sent(state, key):
        return []
    top = st["top"][0] if st["top"] else {}
    return [{"key": key,
             "text": (f"⚠️ معدل فشل هادي آخر ٧ أيام **{st['pct']}%** "
                      f"({st['failures']} من {st['total']}).\n"
                      f"  أكتر خطأ: `{top.get('type','?')}` ×{top.get('count',0)} — "
                      f"{top.get('msg','')[:140]}")}]


def check_disk(state):
    """القرص قرب يملا → SQLite بيفشل والبوت بيقع بطرق غريبة."""
    try:
        import shutil
        usage = shutil.disk_usage(str(BASE))
    except Exception:
        return []
    pct = 100.0 * usage.used / usage.total
    limit = float(os.environ.get("HADI_HB_DISK_PCT", "90") or "90")
    if pct < limit:
        return []
    key = f"disk:{int(pct)}"
    if recently_sent(state, key):
        return []
    return [{"key": key,
             "text": (f"💾 القرص على **{pct:.0f}%** "
                      f"(فاضل {usage.free // (1024*1024)}MB). "
                      "SQLite بيفشل لما يملا.")}]


def check_memory_index(state):
    """الفهرس اتفرّق عن memory.md، أو قواعد سلوك بتتقص من الحقن."""
    try:
        import memory_store
        st = memory_store.status()
    except Exception:
        return []
    out = []
    if not st.get("in_sync"):
        # قرار آسر: ماتطلبش منه يشغّل rebuild يدوي — دي صيانة داخلية مش شغلته.
        # هادي بيصلّحها بنفسه (rebuild آمن وidempotent)، ويتنبّه **بس** لو فشلت
        # أو فضلت مش متزامنة بعد المحاولة (وقتها بقت مشكلة حقيقية تستاهل نظرة).
        try:
            memory_store.rebuild()
            st = memory_store.status()
        except Exception as _e:
            if not recently_sent(state, "memidx"):
                out.append({"key": "memidx",
                            "text": ("🧠 فهرس الذاكرة مش متزامن وفشلت أصلّحه تلقائيًا "
                                     f"({type(_e).__name__}) — محتاج تدخل: `python3 memory_store.py rebuild`")})
        else:
            if not st.get("in_sync") and not recently_sent(state, "memidx"):
                out.append({"key": "memidx",
                            "text": (f"🧠 فهرس الذاكرة لسه مش متزامن بعد إعادة بناء تلقائية "
                                     f"(md={st.get('md_notes')} db={st.get('db_notes')}) — محتاج فحص.")})
    tot, inj = st.get("procedural_total", 0), st.get("procedural_injected", 0)
    if tot > inj and not recently_sent(state, "proccut"):
        out.append({"key": "proccut",
                    "text": (f"📋 {tot - inj} قاعدة سلوك مش بتتحقن في البرومبت "
                             f"(الحقن {inj} من {tot}) — راجعها أو اسحب القديم.")})
    return out


CHECKS = [
    ("error_rate", check_error_rate),
    ("disk", check_disk),
    ("memory_index", check_memory_index),
    ("stale_p1", check_stale_p1),
    ("sprint_tomorrow", check_sprint_tomorrow),
    ("support_48h", check_support_48h),
    ("release_day", check_release_day),
    ("new_sprint", check_new_sprint),
]


def touch_alive() -> None:
    """طابع زمني للـ watchdog. لو الملف ده قديم = البوت متعلّق أو ميت.

    2026-07-26: `!ping` كان الفحص الوحيد وهو **يدوي** — لو البوت اتعلّق
    (قفل معلّق أو الـ Gateway فقد الاتصال من غير crash) محدش يعرف غير لما
    حد يكلّمه ويستنى.
    """
    try:
        (BASE / "logs").mkdir(exist_ok=True)
        (BASE / "logs" / "alive").write_text(
            f"{int(time.time())} {dt.datetime.now(TZ).isoformat(timespec='seconds')}\n",
            encoding="utf-8")
    except OSError:
        pass


def run_checks(state=None, dry_run=True):
    """بيرجّع (تنبيهات, الحالة). الصمت لو مفيش حاجة — نفس فلسفة NO_REPLY."""
    state = load_state() if state is None else state
    if not dry_run:
        touch_alive()
    alerts = []
    # نقطة 3 (كانبان): وقّف فحوصات السبرنت طالما الاسبرنت متوقف — دي اللي كانت
    # بتبعت «نبضة هادي» بتفكّر آسر بإيفنتات سبرنت احنا وقفناه.
    _skip = set()
    try:
        import process_state
        if not process_state.sprint_watch_enabled():
            _skip = {"sprint_tomorrow", "new_sprint", "release_day"}
    except Exception:
        pass
    for name, func in CHECKS:
        if name in _skip:
            continue
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
        import followup_store
        followup_store.STORE = tmp / "pending.json"
        old_day = (dt.datetime.now(TZ).date() - dt.timedelta(days=3)).isoformat()
        new_day = dt.datetime.now(TZ).date().isoformat()
        followup_store._save_all({"followup": [
            {"id": "p1", "content": "شكوى تاجر مستنية رد", "owner": "غادة",
             "owner_id": "1093636555362533498", "first_seen": old_day},
            {"id": "p2", "content": "نقطة جديدة", "owner": "آسر",
             "owner_id": "", "first_seen": new_day},
        ]})

        state = {"sent": {}, "seen_iterations": []}
        assert len(check_sprint_tomorrow(state, today)) == 1, "حدث بكرة مااتمسكش"
        assert len(check_release_day(state, today)) == 1, "يوم الريليز مااتمسكش"
        sup = check_support_48h(state)
        assert len(sup) == 1 and "شكوى" in sup[0]["text"], f"فحص الـ 48 ساعة: {sup}"
        assert "3 يوم" in sup[0]["text"], f"العمر مش ظاهر: {sup}"

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
