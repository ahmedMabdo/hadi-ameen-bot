#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""مخزن النقاط المعلقة للملخصات اليومية — المتابعة عبر الأيام لحد ما النقطة تتقفل.

المشكلة اللي بيحلها:
  daily_digests.py استبدل روتينز كلود الحرة بمسار مقيد — والاستبدال ده شال قدرة
  المتابعة بالكامل. الأدوات فضلت موجودة (discord_followup.py pending) بس اتفصلت
  عن الروتين اللي بيشتغل فعلًا، وfollowup_pending.json فضل [] من يوم ما اتعمل.

الوحدة دي بترجّع القدرة دي وبتعمّمها على التلات قنوات:
  - نقطة مفتوحة بتتسجل بصاحبها (owner_id) وأول يوم اتشافت فيه.
  - كل ملخص بيفكّر بيها بمنشن حقيقي، والتذكير بيتصعّد مع العمر.
  - الموديل هو اللي بيقرر إنها اتقفلت (شاف رد فعلي عليها) — والكود بيتأكد إن
    الـ id اللي بيقفله موجود فعلًا (منع هلوسة ids).

التخزين: pending_points.json — dict مفاتيحه أسماء الملخصات:
  {"followup": [ {...} ], "podaily": [ ... ], "marsteam": [ ... ]}

كل عنصر:
  id          8 حروف hex
  content     نص النقطة
  owner       اسم صاحبها زي ما ظهر
  owner_id    Discord user id (من الروستر — مش من كلام الموديل الحر)
  first_seen  تاريخ ISO (القاهرة) لأول ما اتسجلت
  source_msg  id الرسالة الأصلية لو متاح
  reminders   كام مرة اتفكّرنا بيها

CLI:
    followup_store.py list [--digest followup]
    followup_store.py resolve --digest followup --id <id>
    followup_store.py selftest
"""
import argparse
import datetime as dt
import json
import os
import re
import sys
import uuid
from pathlib import Path
from zoneinfo import ZoneInfo

BASE = Path(__file__).resolve().parent
STORE = Path(os.environ.get("HADI_PENDING_STORE", BASE / "pending_points.json"))
LEGACY_SUPPORT = BASE / "followup_pending.json"   # المخزن القديم لقناة الدعم
CAIRO = ZoneInfo("Africa/Cairo")

DIGESTS = ("followup", "podaily", "marsteam")

# سقف المنشنات في الملخص الواحد — منشن حقيقي بينبّه فعلًا، والإفراط بيخلي
# التيم يتجاهل الملخص كله (نفس فلسفة NO_REPLY).
MAX_MENTIONS = max(1, int(os.environ.get("HADI_DIGEST_MAX_MENTIONS", "6") or "6"))
# بعد كام يوم النقطة تتصعّد لتنبيه واضح
ESCALATE_DAYS = max(1, int(os.environ.get("HADI_DIGEST_ESCALATE_DAYS", "2") or "2"))
# بعد كام يوم نبطّل نفكّر ونعتبرها محتاجة قرار بشري (منع تذكير أبدي)
STALE_DAYS = max(2, int(os.environ.get("HADI_DIGEST_STALE_DAYS", "14") or "14"))

_WS_RX = re.compile(r"\s+")


def _today():
    return dt.datetime.now(CAIRO).date()


def _norm(text: str) -> str:
    """تطبيع للمقارنة — عشان نفس النقطة ماتتسجلش كل يوم من تاني."""
    return _WS_RX.sub(" ", (text or "").strip().lower())[:160]


# ------------------------------------------------------------------ التخزين
def _load_all() -> dict:
    try:
        data = json.loads(STORE.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return {k: (v if isinstance(v, list) else []) for k, v in data.items()}
    except (OSError, json.JSONDecodeError):
        pass
    # هجرة لمرة واحدة من المخزن القديم بتاع الدعم
    try:
        legacy = json.loads(LEGACY_SUPPORT.read_text(encoding="utf-8"))
        if isinstance(legacy, list) and legacy:
            return {"followup": legacy}
    except (OSError, json.JSONDecodeError):
        pass
    return {}


def _save_all(data: dict) -> None:
    tmp = STORE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(STORE)


def load(digest: str) -> list:
    return _load_all().get(digest, [])


def save(digest: str, items: list) -> None:
    data = _load_all()
    data[digest] = items
    _save_all(data)


def all_open() -> list:
    """كل النقاط المفتوحة عبر الملخصات التلاتة — بيستخدمها heartbeat."""
    out = []
    for digest, items in _load_all().items():
        for it in items:
            out.append({**it, "digest": digest})
    return out


# ------------------------------------------------------------------ العمليات
def add(digest: str, content: str, owner: str = "", owner_id: str = "",
        source_msg: str = "", channel_id: str = "", message_id: str = "") -> dict | None:
    """يسجّل نقطة جديدة. بيرجّع None لو نفس النقطة متسجلة أصلًا (dedup في الكود
    مش بالاعتماد على الموديل).

    channel_id + message_id بيتخزّنوا عشان النبض يقدر يرجع يبص على المحادثة
    ويعرف لو النقطة اتردّ عليها (رد مباشر أو منشن المسؤول) — نقطة آسر.
    """
    content = (content or "").strip()
    if len(content) < 8:
        return None
    items = load(digest)
    key = _norm(content)
    if any(_norm(i.get("content", "")) == key for i in items):
        return None
    msg_id = str(message_id or source_msg or "").strip()
    item = {
        "id": uuid.uuid4().hex[:8],
        "content": content[:500],
        "owner": (owner or "").strip()[:60],
        "owner_id": str(owner_id or "").strip(),
        "first_seen": _today().isoformat(),
        "source_msg": msg_id,          # توافق قديم
        "message_id": msg_id,          # رسالة النقطة الأصلية (مرساة كشف الرد)
        "channel_id": str(channel_id or "").strip(),
        "reminders": 0,
    }
    items.append(item)
    save(digest, items)
    return item


def resolve(digest: str, ids) -> list:
    """يقفل نقاط بالـ id. بيتجاهل أي id مش موجود (منع هلوسة الموديل).
    بيرجّع النقاط اللي اتقفلت فعلًا."""
    wanted = {str(i).strip() for i in (ids or []) if str(i).strip()}
    if not wanted:
        return []
    items = load(digest)
    closed = [i for i in items if i.get("id") in wanted]
    if closed:
        save(digest, [i for i in items if i.get("id") not in wanted])
    return closed


def age_days(item, today=None) -> int:
    try:
        seen = dt.date.fromisoformat(str(item.get("first_seen", ""))[:10])
    except ValueError:
        return 0
    return max(0, ((today or _today()) - seen).days)


def bump_reminders(digest: str, items) -> None:
    seen = {i.get("id") for i in items}
    rows = load(digest)
    for r in rows:
        if r.get("id") in seen:
            r["reminders"] = int(r.get("reminders", 0)) + 1
    save(digest, rows)


# ------------------------------------------------------------------ العرض
def _mention(item) -> str:
    """منشن حقيقي لو عندنا id، وإلا الاسم bold (مفيش إشعار كاذب)."""
    oid = str(item.get("owner_id") or "").strip()
    if oid.isdigit():
        return f"<@{oid}>"
    name = item.get("owner") or "مش محدد"
    return f"**{name}**"


def render_open_section(digest: str, today=None) -> tuple:
    """(نص القسم, قائمة ids للمنشن). بيرجّع ("", []) لو مفيش نقاط مستحقة تذكير.

    القاعدة: النقطة اللي اتسجلت النهاردة بس (عمر 0) بتظهر في الملخص العادي
    كـ action item — القسم ده للنقط اللي **عدّى عليها يوم أو أكتر** وهي مفتوحة،
    زي ما آسر طلب.
    """
    today = today or _today()
    items = load(digest)
    aged = [i for i in items if 1 <= age_days(i, today) <= STALE_DAYS]
    if not aged:
        return "", []

    aged.sort(key=lambda i: -age_days(i, today))
    lines, mention_ids = [], []
    hot = [i for i in aged if age_days(i, today) >= ESCALATE_DAYS]
    lines.append("**نقاط لسه مفتوحة من قبل النهاردة:**"
                 if not hot else "⚠️ **نقاط مفتوحة ومحتاجة قفل:**")

    for item in aged:
        days = age_days(item, today)
        oid = str(item.get("owner_id") or "").strip()
        if oid.isdigit() and len(mention_ids) < MAX_MENTIONS and oid not in mention_ids:
            mention_ids.append(oid)
            who = f"<@{oid}>"
        else:
            who = f"**{item.get('owner') or 'مش محدد'}**"
        when = "من امبارح" if days == 1 else f"من {days} يوم"
        mark = "⚠️ " if days >= ESCALATE_DAYS else ""
        lines.append(f"- {mark}{who}: {item.get('content', '')[:180]} — {when}")

    dropped = len(items) - len(aged)
    stale = [i for i in items if age_days(i, today) > STALE_DAYS]
    if stale:
        lines.append(f"  _({len(stale)} نقطة عدّى عليها أكتر من {STALE_DAYS} يوم — "
                     "محتاجة قرار: تتقفل ولا تتحوّل تذكرة؟)_")
    return "\n".join(lines), mention_ids


def pending_brief(digest: str, today=None) -> list:
    """قائمة مختصرة للبرومبت — الموديل بيقارنها برسايل اليوم ويقرر إيه اللي اتقفل."""
    today = today or _today()
    return [{"id": i["id"], "content": i.get("content", "")[:200],
             "owner": i.get("owner", ""), "days_open": age_days(i, today)}
            for i in load(digest)]


# ------------------------------------------------------------------ selftest
def selftest() -> int:
    global STORE
    import tempfile
    ok = True

    def check(label, cond):
        nonlocal ok
        print(("PASS  " if cond else "FAIL  ") + label)
        ok = ok and bool(cond)

    orig = STORE
    tmp = Path(tempfile.mkdtemp(prefix="hadi_pending_"))
    try:
        STORE = tmp / "pending.json"
        today = dt.date(2026, 7, 26)

        a = add("followup", "ياسمين محتاجة تأكيد على سيناريو الريفاند", "ياسمين",
                "1018813098745937990", "999")
        check("إضافة نقطة", a is not None and a["owner_id"] == "1018813098745937990")
        check("dedup: نفس النقطة مش بتتسجل تاني",
              add("followup", "ياسمين محتاجة تأكيد على سيناريو الريفاند", "ياسمين") is None)
        check("dedup بيتجاهل فروق المسافات",
              add("followup", "  ياسمين محتاجة   تأكيد على سيناريو الريفاند ") is None)
        check("النص القصير بيترفض", add("followup", "تمام") is None)

        rows = load("followup")
        check("المخزن فيه عنصر واحد", len(rows) == 1)

        # النقطة اتسجلت النهاردة → مش المفروض تظهر في قسم «مفتوحة من قبل»
        text, ids = render_open_section("followup", today=_today())
        check("نقطة عمرها 0 مابتظهرش في قسم القديم", text == "" and ids == [])

        # نخلّيها من امبارح
        rows[0]["first_seen"] = (dt.date(2026, 7, 25)).isoformat()
        save("followup", rows)
        text, ids = render_open_section("followup", today=today)
        check("عمر يوم → بتظهر", "من امبارح" in text)
        check("منشن حقيقي بالـ id", "<@1018813098745937990>" in text)
        check("الـ id اترجّع للـ allowed_mentions", ids == ["1018813098745937990"])
        check("مفيش تصعيد عند يوم واحد", "⚠️" not in text)

        # نخلّيها من 3 أيام → تصعيد
        rows = load("followup")
        rows[0]["first_seen"] = dt.date(2026, 7, 23).isoformat()
        save("followup", rows)
        text, _ = render_open_section("followup", today=today)
        check("عمر 3 أيام → تصعيد", "⚠️" in text and "من 3 يوم" in text)

        # نقطة من غير owner_id → اسم bold مش منشن كاذب
        add("followup", "حد يراجع تقرير الأوتوميشن بتاع امبارح", "مش معروف", "")
        rows = load("followup")
        for r in rows:
            r["first_seen"] = dt.date(2026, 7, 24).isoformat()
        save("followup", rows)
        text, ids = render_open_section("followup", today=today)
        check("من غير id → bold مش منشن", "**مش معروف**" in text)
        check("الـ ids فيها الحقيقي بس", ids == ["1018813098745937990"])

        # قفل بالـ id
        target = load("followup")[0]["id"]
        closed = resolve("followup", [target, "id-متخيّل"])
        check("القفل بيشتغل على الموجود بس", len(closed) == 1)
        check("الـ id المتخيّل اتتجاهل", len(load("followup")) == 1)

        # سقف المنشنات
        for n in range(10):
            add("followup", f"نقطة رقم {n} محتاجة متابعة من التيم", f"شخص{n}",
                str(1000000000000000000 + n))
        rows = load("followup")
        for r in rows:
            r["first_seen"] = dt.date(2026, 7, 25).isoformat()
        save("followup", rows)
        _, ids = render_open_section("followup", today=today)
        check(f"سقف المنشنات محترم ({len(ids)} <= {MAX_MENTIONS})", len(ids) <= MAX_MENTIONS)

        # العزل بين الملخصات
        add("marsteam", "نقطة مارس مختلفة تمامًا عن الدعم", "أحمد", "1017103979760582706")
        check("عزل المخازن", len(load("marsteam")) == 1 and len(load("followup")) > 1)
        check("all_open بيجمّع الاتنين",
              {r["digest"] for r in all_open()} == {"followup", "marsteam"})

        # ملف تالف → مايكسرش
        STORE.write_text("{ تالف", encoding="utf-8")
        check("ملف تالف بيرجّع فاضي بهدوء", load("followup") == [])

        print("\n" + ("ALL PASS" if ok else "THERE ARE FAILURES"))
        return 0 if ok else 1
    finally:
        STORE = orig


def main():
    p = argparse.ArgumentParser(description="مخزن النقاط المعلقة للملخصات اليومية")
    sub = p.add_subparsers(dest="cmd", required=True)
    l = sub.add_parser("list"); l.add_argument("--digest", choices=DIGESTS, default=None)
    r = sub.add_parser("resolve")
    r.add_argument("--digest", choices=DIGESTS, required=True)
    r.add_argument("--id", required=True)
    sub.add_parser("selftest")
    a = p.parse_args()

    if a.cmd == "selftest":
        sys.exit(selftest())
    if a.cmd == "list":
        rows = load(a.digest) if a.digest else all_open()
        if not rows:
            print("مفيش نقاط مفتوحة.")
            return
        for r in rows:
            print(f"[{r['id']}] ({age_days(r)} يوم) {r.get('owner','?')}: {r.get('content','')[:100]}")
        return
    if a.cmd == "resolve":
        closed = resolve(a.digest, [a.id])
        print(f"RESOLVED {len(closed)}" if closed else f"مفيش نقطة بالـ id ده: {a.id}")


if __name__ == "__main__":
    main()
