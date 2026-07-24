#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""أداة PostHog التفاعلية لهادي (بند 9.2) — أرقام لايف بدل انتظار تقرير الصبح.

النمط: زي `ado_cli.py` بالظبط — **قراءة فقط**، بترد نص جاهز هادي ينقله.

## الحارس (أهم حاجة في الملف ده)

PostHog بيرمي الأحداث **بصمت** لما الكوتا تتعدى: بيرد 200 OK وكأن كل حاجة تمام،
والاستعلام بيرجع أصفار. من غير حارس، سؤال «كام أوردر النهاردة؟» هيرجع «صفر»
بثقة — ورقم غلط من مصدر «موثوق» أسوأ بكتير من «مش عارف».

عشان كده **كل أمر بيطبع حالة البيانات قبل أي رقم**:
    LIVE     آخر حدث من أقل من ساعتين → الأرقام موثوقة
    STALE    آخر حدث من 2-24 ساعة → الأرقام ناقصة غالبًا
    DOWN     مفيش أحداث من أكتر من 24 ساعة → **الأرقام مش حقيقية**، فيه انقطاع تتبع

## مصدر التعريفات

الأرقام بتتحسب بنفس دوال التقرير اليومي (`intel/8orders_report_generator.py`):
نفس `hogql` ونفس خريطة الأحداث `EV` ونفس نافذة يوم العمل `D()` (القاهرة 08:00 →
04:00 اليوم اللي بعده — **مش يوم تقويمي**). يعني الرقم اللايف والرقم اللي في
تقرير الصبح **بيتحسبوا بنفس الطريقة** — مفيش تعريفين متعارضين.

## المفتاح

محتاج `POSTHOG_API_KEY` (Personal API key بصلاحية قراءة) في `.env` في جذر الريبو.
الأداة **مابتكتبش ولا بتعدّل** أي حاجة في PostHog.

## الاستخدام

    posthog_cli.py health                 # حالة البيانات + آخر 7 أيام (ابدأ بيها)
    posthog_cli.py today [--date Y-M-D]   # ملخص يوم العمل: أوردرات، إيراد، تحويل، DAU، أخطاء
    posthog_cli.py orders  [--date ...]
    posthog_cli.py errors  [--date ...] [--limit 5]
    posthog_cli.py since --hours 2        # آخر N ساعة (لأسئلة «في آخر ساعة»)
    posthog_cli.py sql --query "SELECT ..."   # SELECT فقط
    posthog_cli.py selftest               # من غير شبكة
"""
import argparse
import datetime as dt
import importlib.util
import os
import re
import sys
from pathlib import Path

import posthog_guard  # طبقة صلاحيات PostHog

BASE = Path(__file__).resolve().parent
GENERATOR = BASE / "intel" / "8orders_report_generator.py"
TZ_NAME = "Africa/Cairo"

try:
    from dotenv import load_dotenv
    load_dotenv(BASE / ".env")
except Exception:
    pass

STALE_HOURS = float(os.environ.get("HADI_PH_STALE_HOURS", "2") or "2")
DOWN_HOURS = float(os.environ.get("HADI_PH_DOWN_HOURS", "24") or "24")
# نسبة حجم آخر 24 ساعة للمعتاد اللي تحتها نعتبر الأنبوب مقطوع (افتراضي 5%)
DOWN_RATIO = float(os.environ.get("HADI_PH_DOWN_RATIO", "0.05") or "0.05")

_gen = None


def gen():
    """بيحمّل مولّد التقرير اليومي كموديول (اسمه بيبدأ برقم فمينفعش import عادي).

    الملف متغلّف بـ __main__ فالاستيراد مابيشغّلش التقرير."""
    global _gen
    if _gen is None:
        if not os.environ.get("POSTHOG_API_KEY", "").strip():
            sys.exit(
                "مفيش POSTHOG_API_KEY في البيئة.\n"
                "ضيفه في ملف .env في جذر الريبو (سطر واحد: POSTHOG_API_KEY=...)\n"
                "المفتاح لازم يكون Personal API key بصلاحية قراءة على مشروع 8orders.")
        if not GENERATOR.exists():
            sys.exit(f"مش لاقي {GENERATOR} — الأداة بتعتمد على تعريفاته.")
        spec = importlib.util.spec_from_file_location("hadi_ph_generator", GENERATOR)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _gen = posthog_guard.GuardedGen(module)
    return _gen


def now_cairo():
    try:
        from zoneinfo import ZoneInfo
        return dt.datetime.now(ZoneInfo(TZ_NAME))
    except Exception:
        return dt.datetime.now()


# لازم يفضل متطابق مع BIZ_END_HOUR في intel/8orders_report_generator.py.
# 8Orders زودوا ساعات العمل (2026-07-24): اليوم بيقفل 04:00 بدل 02:00.
BIZ_END_HOUR = 4


def business_day(at=None) -> str:
    """يوم العمل الحالي: قبل 04:00 القاهرة إحنا لسه في يوم إمبارح."""
    at = at or now_cairo()
    return ((at.date() - dt.timedelta(days=1)).isoformat()
            if at.hour < BIZ_END_HOUR else at.date().isoformat())


# ───────────────────────── الحارس ─────────────────────────
def classify(hours_since, last24=None, baseline=None):
    """التصنيف بالحجم مش بآخر حدث بس.

    الدرس اللي اتعلمناه من أول تشغيل حقيقي: أنبوب البيانات كان **مقطوع من 10 أيام**،
    ومع ذلك حدثين يتامى إمبارح خلّوا التصنيف يطلع STALE («متأخرة شوية») بدل DOWN.
    حدث واحد ≠ أنبوب شغال. فلو حجم آخر 24 ساعة أقل من DOWN_RATIO من المعتاد،
    الحالة DOWN مهما كان آخر حدث قريب.
    """
    if hours_since is None:
        return "DOWN", "مفيش ولا حدث مسجّل خالص"
    if baseline and baseline > 0 and last24 is not None:
        ratio = last24 / baseline
        if ratio < DOWN_RATIO:
            return "DOWN", (f"{last24:,} حدث في 24 ساعة مقابل {baseline:,.0f} المعتاد "
                            f"({ratio*100:.1f}%) — الأنبوب مقطوع فعليًا")
    if hours_since >= DOWN_HOURS:
        return "DOWN", f"آخر حدث من {hours_since:.0f} ساعة — التتبع واقف"
    if hours_since >= STALE_HOURS:
        return "STALE", f"آخر حدث من {hours_since:.1f} ساعة — البيانات متأخرة"
    return "LIVE", f"آخر حدث من {hours_since*60:.0f} دقيقة"


def baseline_daily():
    """المعتاد اليومي = وسيط أعلى 7 أيام في آخر 30 — بيتجاهل أيام الانقطاع نفسها."""
    rows = gen().hogql(
        "SELECT count() AS c FROM events WHERE timestamp >= now() - INTERVAL 30 DAY "
        "GROUP BY toDate(timestamp) ORDER BY c DESC LIMIT 7")
    counts = sorted(int(r[0]) for r in rows if r and r[0])
    return counts[len(counts) // 2] if counts else 0


def freshness():
    """(الحالة, الشرح, آخر توقيت, عدد أحداث آخر 24 ساعة)."""
    rows = gen().hogql(
        "SELECT max(timestamp), countIf(timestamp >= now() - INTERVAL 24 HOUR) FROM events")
    last, last24 = (rows[0][0], rows[0][1]) if rows and rows[0] else (None, 0)
    hours = None
    if last:
        stamp = str(last).replace("Z", "+00:00")
        try:
            parsed = dt.datetime.fromisoformat(stamp)
            if parsed.tzinfo is None:
                from zoneinfo import ZoneInfo
                parsed = parsed.replace(tzinfo=ZoneInfo(TZ_NAME))
            hours = (now_cairo() - parsed).total_seconds() / 3600
        except Exception:
            hours = None
    state, why = classify(hours, int(last24 or 0), baseline_daily())
    return state, why, last, int(last24 or 0)


def guard_banner():
    """السطر اللي لازم يسبق أي رقم — وبيرجّع الحالة عشان النداء يقرر."""
    state, why, last, last24 = freshness()
    icon = {"LIVE": "🟢", "STALE": "🟡", "DOWN": "🔴"}[state]
    lines = [f"{icon} حالة البيانات: {state} — {why}",
             f"   آخر حدث: {last or 'مفيش'} | أحداث آخر 24 ساعة: {last24:,}"]
    if state == "DOWN":
        lines += [
            "   ⚠️ الأرقام تحت **مش حقيقية**: PostHog بيرمي الأحداث بصمت لما الكوتا تتعدى",
            "      (بيرد 200 OK من غير ما يسجّل). بلّغ ده قبل أي رقم، وشوف knowledge/memory.md",
            "      لو الانقطاع ده متوقع ومعروف السبب.",
        ]
    elif state == "STALE":
        lines.append("   ⚠️ الأرقام ناقصة غالبًا — البيانات لسه بتتأخر في الوصول.")
    return "\n".join(lines), state


# ───────────────────────── الاستعلامات ─────────────────────────
def q_scalar(query, default=0):
    rows = gen().hogql(query)
    return rows[0][0] if rows and rows[0] and rows[0][0] is not None else default


def cmd_health(args):
    banner, state = guard_banner()
    print(banner)
    print("\nأحداث آخر 10 أيام (تقويمي):")
    rows = gen().hogql(
        "SELECT toDate(timestamp) AS d, count() FROM events "
        "WHERE timestamp >= now() - INTERVAL 10 DAY GROUP BY d ORDER BY d DESC")
    if not rows:
        print("  مفيش بيانات خالص.")
    for day, count in rows:
        bar = "█" * min(40, int(int(count) / 3000)) if count else ""
        print(f"  {day}  {int(count):>9,}  {bar}")
    if state != "LIVE":
        print("\nالتشخيص: هبوط مفاجئ لأصفار مع استمرار عمل التطبيق = تعدّي كوتا غالبًا،")
        print("مش عطل في التطبيق. الأحداث اللي اتضربت في فترة الانقطاع **مش بترجع**.")


def _revenue_baseline(module):
    """وسيط الإيراد اليومي في آخر 30 يوم — أساس المقارنة للتيم."""
    rows = gen().hogql(
        "SELECT round(sum(toFloat(properties.total_amount)),0) AS v FROM events "
        f"WHERE event='{module.EV['order']}' AND timestamp >= now() - INTERVAL 30 DAY "
        "GROUP BY toDate(timestamp) ORDER BY v DESC LIMIT 7")
    values = sorted(float(r[0]) for r in rows if r and r[0])
    return values[len(values) // 2] if values else 0


def _money(value, baseline_fn):
    """مبلغ: رقم كامل للأدمن، مؤشر نسبي للتيم."""
    if posthog_guard.is_admin():
        return f"{float(value or 0):,.0f} ج.م"
    return posthog_guard.as_index(float(value or 0), baseline_fn())


def _amount_cell(amount, revenue_total):
    """خانة المبلغ في جدول الأوردرات: مبلغ للأدمن، نصيب من الإيراد للتيم."""
    if posthog_guard.is_admin():
        return f"{float(amount or 0):>12,.0f} ج.م"
    return f"{posthog_guard.as_share(float(amount or 0), revenue_total):>8} من الإيراد"


def cmd_today(args):
    day = args.date or business_day()
    banner, state = guard_banner()
    print(banner)
    module = gen()
    D, EV = module.D, module.EV
    print(f"\n📊 يوم العمل {day} (القاهرة 08:00 → 04:00 اليوم اللي بعده)")

    orders = q_scalar(f"SELECT count() FROM events WHERE event='{EV['order']}' AND {D(day)}")
    revenue = q_scalar(
        f"SELECT round(sum(toFloat(properties.total_amount)),0) FROM events "
        f"WHERE event='{EV['order']}' AND {D(day)}")
    carts = q_scalar(f"SELECT count() FROM events WHERE event='{EV['cart']}' AND {D(day)}")
    views = q_scalar(f"SELECT count() FROM events WHERE event='{EV['product']}' AND {D(day)}")
    errors = q_scalar(f"SELECT count() FROM events WHERE event='{EV['error']}' AND {D(day)}")
    rage = q_scalar(f"SELECT count() FROM events WHERE event='{EV['rage']}' AND {D(day)}")
    users = q_scalar(f"SELECT uniq(person_id) FROM events WHERE {D(day)}")

    conv = f"{100.0 * orders / carts:.1f}%" if carts else "—"
    print(f"  أوردرات      : {int(orders):,}")
    print(f"  إيراد        : {_money(revenue, lambda: _revenue_baseline(module))}")
    print(f"  سلات         : {int(carts):,}  (سلة→أوردر: {conv})")
    print(f"  مشاهدات منتج : {int(views):,}")
    print(f"  مستخدمين     : {int(users):,}")
    print(f"  أخطاء        : {int(errors):,}   نقرات غاضبة: {int(rage):,}")
    if state == "DOWN":
        print("\n⚠️ كرر: الأرقام دي مش حقيقية — التتبع واقف.")


def cmd_orders(args):
    day = args.date or business_day()
    banner, _ = guard_banner()
    print(banner)
    module = gen()
    D, EV = module.D, module.EV
    print(f"\n🧾 أوردرات يوم {day}")
    rows = gen().hogql(
        f"SELECT properties.payment_method, count(), round(sum(toFloat(properties.total_amount)),0) "
        f"FROM events WHERE event='{EV['order']}' AND {D(day)} GROUP BY 1 ORDER BY 2 DESC")
    if not rows:
        print("  مفيش أوردرات مسجّلة في النافذة دي.")
        return
    total = sum(int(r[1]) for r in rows)
    revenue_total = sum(float(r[2] or 0) for r in rows)
    for method, count, amount in rows:
        share = 100.0 * int(count) / total if total else 0
        print(f"  {str(method or 'غير محدد'):22} {int(count):>6,} ({share:4.1f}%)  {_amount_cell(amount, revenue_total)}")
    print(f"  {'الإجمالي':22} {total:>6,}")


def cmd_errors(args):
    day = args.date or business_day()
    banner, _ = guard_banner()
    print(banner)
    module = gen()
    D, EV = module.D, module.EV
    print(f"\n🐞 أخطاء يوم {day} (أعلى {args.limit})")
    rows = gen().hogql(
        f"SELECT properties.$screen_name, count() FROM events "
        f"WHERE event='{EV['error']}' AND {D(day)} GROUP BY 1 ORDER BY 2 DESC LIMIT {args.limit}")
    if not rows:
        print("  مفيش أخطاء مسجّلة.")
    for screen, count in rows:
        print(f"  {str(screen or 'غير محدد'):32} {int(count):>6,}")


def cmd_since(args):
    banner, state = guard_banner()
    print(banner)
    module = gen()
    EV = module.EV
    hours = args.hours
    window = f"timestamp >= now() - INTERVAL {int(hours)} HOUR"
    print(f"\n⏱️ آخر {int(hours)} ساعة")
    for label, event in (("أوردرات", EV["order"]), ("سلات", EV["cart"]),
                         ("أخطاء", EV["error"]), ("نقرات غاضبة", EV["rage"]),
                         ("طلبات دعم", EV["support"])):
        count = q_scalar(f"SELECT count() FROM events WHERE event='{event}' AND {window}")
        print(f"  {label:14} {int(count):>6,}")
    rows = gen().hogql(
        f"SELECT event, count() FROM events WHERE {window} GROUP BY event ORDER BY 2 DESC LIMIT 5")
    if rows:
        print("  أكتر الأحداث:")
        for event, count in rows:
            print(f"    {str(event):30} {int(count):>6,}")


_SQL_OK = re.compile(r"^\s*select\b", re.IGNORECASE)
_SQL_BAD = re.compile(r"\b(insert|update|delete|drop|alter|create|truncate|grant)\b", re.IGNORECASE)


def cmd_sql(args):
    query = args.query.strip().rstrip(";")
    posthog_guard.guard_free_sql(query)
    if not _SQL_OK.match(query) or _SQL_BAD.search(query):
        sys.exit("مسموح SELECT بس — الأداة قراءة فقط.")
    banner, _ = guard_banner()
    print(banner)
    rows = gen().hogql(query)
    print()
    for row in rows[: args.limit]:
        print("  " + " | ".join(str(value) for value in row))
    print(f"\n({len(rows)} صف)")


def selftest():
    """اختبار منطق الحارس من غير شبكة — الجزء اللي بيمنع الأرقام الكاذبة."""
    assert classify(0.5)[0] == "LIVE", classify(0.5)
    assert classify(5)[0] == "STALE", classify(5)
    assert classify(50)[0] == "DOWN", classify(50)
    assert classify(None)[0] == "DOWN", "مفيش بيانات = DOWN"

    # الحالة الحقيقية اللي كشفها أول تشغيل: أنبوب ميت + حدثين يتامى إمبارح.
    # بالعمر بس دي كانت بتطلع STALE — والصح DOWN.
    assert classify(22.9, last24=2, baseline=100_000)[0] == "DOWN", "حجم شبه صفري لازم DOWN"
    assert classify(0.2, last24=3, baseline=100_000)[0] == "DOWN", "حدث لسه جاي مايخفيش أنبوب ميت"
    assert classify(0.5, last24=95_000, baseline=100_000)[0] == "LIVE", "حجم طبيعي = LIVE"
    assert classify(0.5, last24=50, baseline=0)[0] == "LIVE", "من غير خط أساس نرجع للعمر"

    from zoneinfo import ZoneInfo
    at = dt.datetime(2026, 7, 19, 1, 30, tzinfo=ZoneInfo(TZ_NAME))
    assert business_day(at) == "2026-07-18", "قبل 4 الفجر = يوم العمل السابق"
    # الحدود الجديدة بعد ما 8Orders زودوا ساعات العمل (02:00 -> 04:00):
    at = dt.datetime(2026, 7, 19, 3, 0, tzinfo=ZoneInfo(TZ_NAME))
    assert business_day(at) == "2026-07-18", "3 الفجر لسه يوم إمبارح (كانت بتطلع غلط قبل التوسعة)"
    at = dt.datetime(2026, 7, 19, 3, 59, tzinfo=ZoneInfo(TZ_NAME))
    assert business_day(at) == "2026-07-18", "3:59 آخر لحظة في يوم إمبارح"
    at = dt.datetime(2026, 7, 19, 4, 0, tzinfo=ZoneInfo(TZ_NAME))
    assert business_day(at) == "2026-07-19", "4:00 بالظبط = يوم جديد"
    at = dt.datetime(2026, 7, 19, 14, 0, tzinfo=ZoneInfo(TZ_NAME))
    assert business_day(at) == "2026-07-19", "بعد الفجر = اليوم"

    for bad in ("DELETE FROM events", "select 1; drop table x", "update events set a=1"):
        assert not (_SQL_OK.match(bad) and not _SQL_BAD.search(bad)), f"مر استعلام خطر: {bad}"
    assert _SQL_OK.match("SELECT count() FROM events") and not _SQL_BAD.search("SELECT count() FROM events")
    print("SELFTEST PASS — الحارس ونافذة يوم العمل وقفل الكتابة كلهم سليمين")


def main():
    parser = argparse.ArgumentParser(description="PostHog تفاعلي لهادي (بند 9.2) — قراءة فقط")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("health").set_defaults(func=cmd_health)
    for name, func in (("today", cmd_today), ("orders", cmd_orders)):
        p = sub.add_parser(name)
        p.add_argument("--date")
        p.set_defaults(func=func)
    p = sub.add_parser("errors")
    p.add_argument("--date")
    p.add_argument("--limit", type=int, default=5)
    p.set_defaults(func=cmd_errors)
    p = sub.add_parser("since")
    p.add_argument("--hours", type=float, default=1)
    p.set_defaults(func=cmd_since)
    p = sub.add_parser("sql")
    p.add_argument("--query", required=True)
    p.add_argument("--limit", type=int, default=30)
    p.set_defaults(func=cmd_sql)
    sub.add_parser("selftest").set_defaults(func=lambda a: selftest())

    args = parser.parse_args()
    try:
        args.func(args)
    except posthog_guard.GuardDenied as exc:
        sys.exit(f"\u26d4 {exc}")


if __name__ == "__main__":
    main()
