#!/usr/bin/env python3
"""Hadi Ameen - 8order-po daily digest routine (Discord REST API v10 direct).

Commands:
    python3 discord_podaily.py fetch            -> prints JSON of messages from the
                                                   last rolling 24 hours in the 8order-po channel to stdout
    python3 discord_podaily.py post "<text>"    -> posts text to the 8order-po channel
    python3 discord_podaily.py post --dry-run "<text>" -> dry-run mode: does not
                                                   post publicly

Dry-run mode is enabled via env PODAILY_DRY_RUN=true/1/yes, or the --dry-run
flag. In dry-run mode the summary is only printed to stdout, and optionally
DMed to PODAILY_DM_USER_ID if set - nothing is posted publicly.

Every error is printed as "PODAILY: ..." to stderr and returns a non-zero
exit code without crashing the rest of the routine.
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import requests

# بند 8.2: الكود ده كان متكرر في الروتينات التلاتة — مصدر واحد دلوقتي
import routines_common
from routines_common import log, api_get, api_post, auth_headers, get_token, is_truthy, load_env_file, open_dm_channel, resolve_guild_id, resolve_user_id, send_dm

routines_common.set_prefix("PODAILY")  # اللوج يفضل زي ما هو

API_BASE = "https://discord.com/api/v10"
# F5: توقيت القاهرة الحقيقي (بيتنقل EET/EEST لوحده) بدل UTC+3 الثابت اللي كان
# هيغلط ساعة كاملة بعد رجوع الساعة الشتوي 2026-10-29.
CAIRO_TZ = ZoneInfo("Africa/Cairo")

PO_CHANNEL_ID = "1358833733699899704"








def is_dry_run(cli_flag: bool = False) -> bool:
    return cli_flag or is_truthy(os.environ.get("PODAILY_DRY_RUN"))












def resolve_channel_id() -> str | None:
    """Returns the 8order-po channel id (env override PODAILY_CHANNEL_ID, else the fixed default)."""
    return os.environ.get("PODAILY_CHANNEL_ID", PO_CHANNEL_ID)


def fetch_last_24h_messages() -> list[dict]:
    """Fetch messages from the 8order-po channel in a rolling 24h window ending now (Cairo time)."""
    channel_id = resolve_channel_id()
    if not channel_id:
        return []

    window_end = datetime.now(CAIRO_TZ)
    window_start = window_end - timedelta(hours=24)

    messages = []
    before = None
    for _ in range(10):  # up to ~1000 messages, enough for a 24h window
        params = {"limit": 100}
        if before:
            params["before"] = before

        batch = api_get(f"/channels/{channel_id}/messages", params=params)
        if not batch:
            break

        stop = False
        for msg in batch:
            ts_raw = msg.get("timestamp")
            try:
                ts = datetime.fromisoformat(ts_raw).astimezone(CAIRO_TZ)
            except (TypeError, ValueError):
                continue

            if ts >= window_end:
                continue
            if ts < window_start:
                stop = True
                continue

            author = msg.get("author", {})
            display_name = (
                author.get("global_name")
                or author.get("username")
                or "unknown"
            )
            messages.append(
                {
                    "author": display_name,
                    "author_id": author.get("id"),
                    "bot": bool(author.get("bot")),
                    "content": msg.get("content", ""),
                    "timestamp": ts.isoformat(),
                }
            )

        before = batch[-1]["id"]
        if stop or len(batch) < 100:
            break

    messages.reverse()  # chronological order
    return messages








def post_message(content: str, dry_run: bool = False, mention_ids=None) -> bool:
    if dry_run:
        print("PODAILY: DRY RUN — لم يُنشر في القناة العامة")
        print(content)

        dm_user_id = os.environ.get("PODAILY_DM_USER_ID")
        if dm_user_id:
            if send_dm(dm_user_id, content):
                log(f"تم إرسال نسخة تجريبية DM للمستخدم {dm_user_id}")
            else:
                log(f"فشل إرسال DM التجريبي للمستخدم {dm_user_id}")
        else:
            log("PODAILY_DM_USER_ID مش محدد — الملخص اتطبع في stdout بس من غير DM")

        return True

    channel_id = resolve_channel_id()
    if not channel_id:
        return False

    # المنشن بيتحدد صراحةً في allowed_mentions — أي @everyone جاي في نص
    # الموديل مابيتنفذش (parse=[]). التقسيم فوق 2000 حرف متعامل معاه.
    return routines_common.post_to_channel(channel_id, content, mention_ids)


def main() -> None:
    load_env_file()

    args = sys.argv[1:]
    cli_dry_run = "--dry-run" in args
    if cli_dry_run:
        args = [a for a in args if a != "--dry-run"]

    # --mentions "id1,id2" — الـ ids المسموح تنبيهها في رسالة الملخص
    mention_ids = []
    if "--mentions" in args:
        i = args.index("--mentions")
        if i + 1 < len(args):
            mention_ids = [x.strip() for x in args[i + 1].split(",") if x.strip().isdigit()]
            del args[i:i + 2]
        else:
            del args[i]

    if not args:
        print("Usage: discord_podaily.py [--dry-run] fetch | post \"<text>\" [--mentions id1,id2]", file=sys.stderr)
        sys.exit(1)

    command = args[0]
    dry_run = is_dry_run(cli_dry_run)

    if command == "fetch":
        messages = fetch_last_24h_messages()
        print(json.dumps(messages, ensure_ascii=False, indent=2))
        return

    if command == "post":
        if len(args) < 2:
            log("محتاج تبعت النص اللي عايز تنشره: post \"<text>\"")
            sys.exit(1)
        ok = post_message(args[1], dry_run=dry_run, mention_ids=mention_ids)
        sys.exit(0 if ok else 1)

    print(f"Unknown command: {command}", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
