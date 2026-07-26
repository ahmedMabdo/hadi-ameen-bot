#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""notify.py — هادي يبعت DM لآسر. **لآسر بس.**

ليه الأداة دي موجودة (2026-07-26):
    هادي كان عنده طريقة يبعت في **القنوات** (po_channel_cr.py post) ومفيش
    طريقة يبعت **DM** خالص — الحل الوحيد كان يجدول تذكير بعد دقيقة
    (schedule.py) وده التواء مش أداة. ومع SOP القواعد السلوكية (لازم يشاور
    آسر قبل أي تغيير سلوك دائم) بقت لازمة.

سياسة الـ DM في المشروع (قرار آسر) — مثبتة في الكود مش في الإعدادات:
    • الكلام مع هادي في الخاص       → آسر فقط  (discord_bot.ALLOWED_USER_IDS)
    • تنبيهات هادي الاستباقية       → آسر فقط  (discord_bot.dm_allowed_users)
    • تقرير PostHog اليومي          → آسر + باشمهندس محمود
                                      (intel/discord_delivery + MAHMOUD_DISCORD_USER_ID)
    • الأداة دي                     → آسر فقط

    مفيش أي حد تاني. النسخة الأولى من الملف ده كانت بتسمح بأي حد في
    posthog_guard.TEAM_IDS — وده **غلط**: الجدول ده للتسمية في سجل التدقيق
    (مكتوب في docstring بتاعه) ومش قايمة صلاحيات. اتصلح فورًا.

الاستخدام:
    python3 notify.py --text "..."
    echo "..." | python3 notify.py
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

# المستقبِل الوحيد. مثبّت في الكود زي ASSER_USER_ID في discord_bot — مش
# إعداد بيتغير من .env بالغلط.
ASSER_ID = os.environ.get("ASSER_USER_ID", "1378684355148386355").strip()
MAX_CHARS = 1900


def send(text: str) -> bool:
    import routines_common
    routines_common.set_prefix("NOTIFY")
    channel_id = routines_common.open_dm_channel(ASSER_ID)
    if not channel_id:
        return False
    return routines_common.api_post(
        f"/channels/{channel_id}/messages",
        # parse=[] — أي @everyone في نص الموديل مابيتنفذش
        {"content": text[:MAX_CHARS], "allowed_mentions": {"parse": []}},
    ) is not None


def main():
    p = argparse.ArgumentParser(description="ابعت DM لآسر (المستقبِل الوحيد)")
    p.add_argument("--text", help="نص الرسالة (أو مرّره على stdin)")
    a = p.parse_args()

    text = (a.text if a.text is not None else sys.stdin.read()).strip()
    if not text:
        sys.exit("ERROR: مفيش نص — استخدم --text أو مرّره على stdin")
    if len(text) > MAX_CHARS:
        print(f"NOTIFY: النص {len(text)} حرف — هيتقص عند {MAX_CHARS}", file=sys.stderr)

    if send(text):
        print(f"DM SENT to آسر ({min(len(text), MAX_CHARS)} حرف)")
    else:
        sys.exit("FAILED: مقدرتش أبعت الـ DM — شوف اللوج فوق")


if __name__ == "__main__":
    main()
