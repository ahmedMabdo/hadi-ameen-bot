#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""notify.py — أداة هادي يبعت بيها DM لآسر (أو لعضو في الفريق) عبر Discord REST.

ليه الأداة دي موجودة (2026-07-26):
    هادي كان عنده طريقة يبعت في **القنوات** (po_channel_cr.py post) ومفيش
    طريقة يبعت **DM** خالص — الحل الوحيد كان يجدول تذكير بعد دقيقة
    (schedule.py) وده التواء مش أداة. ومع قرار «القواعد السلوكية تتشاور مع
    آسر في الخاص» بقت لازمة.

الحدود بالنية:
    - المستقبِل لازم يكون **من جدول الفريق** (posthog_guard.ADMIN_IDS/TEAM_IDS)
      أو الـ alias `asser`. أي id تاني بيترفض — عشان مايبقاش وسيلة لإرسال
      رسايل لأي حد على ديسكورد.
    - إرسال نص بس. مفيش مرفقات ولا embeds ولا منشنات جماعية.
    - allowed_mentions معطلة تمامًا (parse=[]) — @everyone في نص الموديل
      مابيتنفذش.

الاستخدام:
    python3 notify.py asser --text "..."
    python3 notify.py --to 1378684355148386355 --text "..."
    python3 notify.py list          # مين ينفع أبعتله
"""
import argparse
import os
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

try:
    from dotenv import load_dotenv
    load_dotenv(BASE / ".env")
except Exception:
    pass

ASSER_ID = os.environ.get("ASSER_USER_ID", "1378684355148386355").strip()
MAX_CHARS = 1900


def roster() -> dict:
    """{id: الاسم} — نفس مصدر daily_digests.team_roster عشان مايبقاش جدول تاني."""
    try:
        import posthog_guard
        return {**posthog_guard.ADMIN_IDS, **posthog_guard.TEAM_IDS}
    except Exception as error:
        print(f"NOTIFY WARN: الروستر مش متاح ({type(error).__name__}) — آسر فقط",
              file=sys.stderr)
        return {ASSER_ID: "آسر جميل"}


def resolve(target: str) -> str:
    t = (target or "").strip().lower()
    if t in ("asser", "آسر", "asser_gameel"):
        return ASSER_ID
    people = roster()
    if target in people:
        return target
    # بالاسم من الجدول
    for uid, name in people.items():
        if t and t in name.lower():
            return uid
    sys.exit(f"ERROR: '{target}' مش في جدول الفريق. شوف: python3 notify.py list")


def send(user_id: str, text: str) -> bool:
    import routines_common
    routines_common.set_prefix("NOTIFY")
    channel_id = routines_common.open_dm_channel(user_id)
    if not channel_id:
        return False
    ok = routines_common.api_post(
        f"/channels/{channel_id}/messages",
        {"content": text[:MAX_CHARS], "allowed_mentions": {"parse": []}},
    )
    return ok is not None


def main():
    p = argparse.ArgumentParser(description="ابعت DM لآسر أو لعضو في الفريق")
    p.add_argument("target", nargs="?", default="asser",
                   help="asser (الافتراضي) أو اسم من الجدول أو 'list'")
    p.add_argument("--to", help="user id مباشر (لازم يكون في جدول الفريق)")
    p.add_argument("--text", help="نص الرسالة (أو من stdin)")
    a = p.parse_args()

    if a.target == "list":
        for uid, name in sorted(roster().items(), key=lambda kv: kv[1]):
            print(f"  {uid:22} {name}")
        return

    text = (a.text if a.text is not None else sys.stdin.read()).strip()
    if not text:
        sys.exit("ERROR: مفيش نص — استخدم --text أو مرّره على stdin")

    uid = resolve(a.to or a.target)
    if send(uid, text):
        print(f"DM SENT to {roster().get(uid, uid)} ({len(text)} حرف)")
    else:
        sys.exit(f"FAILED: مقدرتش أبعت DM لـ {uid}")


if __name__ == "__main__":
    main()
