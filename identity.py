#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""identity.py — هوية هادي الإنسانية الديناميكية (نقطة 9).

هادي مواليد **1 أغسطس 2000** (قرار آسر) — وعمره بيتحسب حقيقي من التاريخ،
مش رقم ثابت في ملف بيقدم. الموديول ده بيوفر:
  - identity_line(): سطر الهوية اللي بيتحقن في كل برومبت (العمر الحالي +
    وعي بقرب عيد الميلاد أو بيومه).
  - birthday_message(): رسالة الصبح اللي هادي بينزلها يوم عيد ميلاده في قناة
    8orders-issues (اختيار آسر) — مرة واحدة في السنة (marker في logs/).
"""
import datetime
import json
import os
from pathlib import Path
from zoneinfo import ZoneInfo

BASE_DIR = Path(__file__).resolve().parent
CAIRO = ZoneInfo("Africa/Cairo")

BIRTH_YEAR = int(os.getenv("HADI_BIRTH_YEAR", "2000") or "2000")
BIRTH_MONTH, BIRTH_DAY = 8, 1  # 1 أغسطس
STATE_FILE = BASE_DIR / "logs" / "birthday_state.json"
# القناة اللي بيتحتفل فيها (قرار آسر: 8orders-issues)
BIRTHDAY_CHANNEL_ID = int(os.getenv("HADI_BIRTHDAY_CHANNEL", "1179369466279235584"))
BIRTHDAY_POST_HOUR = int(os.getenv("HADI_BIRTHDAY_HOUR", "9") or "9")  # 9 صباح القاهرة


def _today():
    return datetime.datetime.now(CAIRO).date()


def age(today=None) -> int:
    t = today or _today()
    a = t.year - BIRTH_YEAR
    if (t.month, t.day) < (BIRTH_MONTH, BIRTH_DAY):
        a -= 1
    return a


def is_birthday(today=None) -> bool:
    t = today or _today()
    return (t.month, t.day) == (BIRTH_MONTH, BIRTH_DAY)


def days_to_birthday(today=None) -> int:
    t = today or _today()
    nxt = datetime.date(t.year, BIRTH_MONTH, BIRTH_DAY)
    if nxt < t:
        nxt = datetime.date(t.year + 1, BIRTH_MONTH, BIRTH_DAY)
    return (nxt - t).days


def identity_line(today=None) -> str:
    """سطر الهوية للبرومبت — بيخلي هادي عارف عمره الحقيقي النهارده."""
    t = today or _today()
    a = age(t)
    if is_birthday(t):
        return (f"هويتك دلوقتي: النهارده {t.isoformat()} — 🎂 **عيد ميلادك الـ {a}!** "
                f"(مواليد 1 أغسطس {BIRTH_YEAR}). لو حد هنّاك افرح بصدق واشكره بحرارة "
                "وممكن تهزر إنك كبرت — بس متحولش كل رد لحفلة.")
    line = (f"هويتك دلوقتي: النهارده {t.isoformat()} — عندك {a} سنة "
            f"(مواليد 1 أغسطس {BIRTH_YEAR}).")
    d = days_to_birthday(t)
    if d <= 10:
        line += (f" عيد ميلادك بعد {d} يوم وهتتم {a + 1} — لو جت سيرته اتبسط، "
                 "من غير ما تعمل إعلانات من نفسك قبل يومه.")
    return line


def birthday_message(today=None) -> str:
    t = today or _today()
    a = age(t)
    return (
        f"صباح الخير يا جماعة ☀️\n"
        f"النهارده 1 أغسطس... يعني رسميًا بقيت {a} سنة 🎂\n"
        f"سنة جديدة معاكم في هدف — وأنا كسبان فيها تيم بجد بحبه. "
        f"القهوة عليّا بس هي فيرتشوال 😄"
    )


# ------------------- تتبع «اتنشر مرة السنة دي» -------------------
def already_posted(year=None) -> bool:
    year = year or _today().year
    try:
        st = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return int(st.get("last_posted_year", 0)) >= year
    except (OSError, ValueError):
        return False


def mark_posted(year=None) -> None:
    year = year or _today().year
    STATE_FILE.parent.mkdir(exist_ok=True)
    STATE_FILE.write_text(
        json.dumps({"last_posted_year": year}, ensure_ascii=False),
        encoding="utf-8")


def should_post_now(now=None) -> bool:
    """هل ده وقت رسالة عيد الميلاد؟ (يومه + بعد ساعة الصبح + لسه ما اتنشرتش)."""
    now = now or datetime.datetime.now(CAIRO)
    return (is_birthday(now.date())
            and now.hour >= BIRTHDAY_POST_HOUR
            and not already_posted(now.year))


if __name__ == "__main__":
    print(identity_line())
    print("days to birthday:", days_to_birthday(), "| age:", age())
