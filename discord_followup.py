#!/usr/bin/env python3
"""متابعة يومية لهادي أمين على ديسكورد — Discord REST API v10 مباشرة.

الأوامر:
  python3 discord_followup.py fetch                -> يطبع رسائل آخر 24 ساعة (قناة الدعم) كـ JSON على stdout
  python3 discord_followup.py post "<نص>"          -> يبعت النص كرسالة في قناة الدعم
  python3 discord_followup.py post --dry-run "<نص>" -> وضع تجربة: ما يبعتش في القناة العامة

  python3 discord_followup.py pending list         -> يطبع نقاط "لسه من غير رد" المتتبَّعة من أيام سابقة
  python3 discord_followup.py pending add --content "..." --author "..." --author-id "..."
      --timestamp "..." [--message-id "..."] [--note "..."]  -> يضيف نقطة متتبَّعة جديدة
  python3 discord_followup.py pending resolve --id <id>       -> يشيل نقطة اترد عليها (خلصت متابعتها)

وضع التجربة (dry-run) بيتفعّل لو env `FOLLOWUP_DRY_RUN` قيمته true/1/yes، أو بفلاج
`--dry-run` في الأمر. في وضع التجربة الملخص بيتطبع في stdout بس، وبيتبعت DM خاص
لو `FOLLOWUP_DM_USER_ID` محدد — من غير أي نشر في القناة العامة.

كل خطأ بيتطبع بصيغة "FOLLOWUP: ..." على stderr وبيرجع exit code != 0 من غير ما يكسر باقي الروتين.

نقاط "لسه من غير رد" بتتخزّن في followup_pending.json (متتبَّع في git) عشان تعيش لعدَّة
تشغيلات للروتين — كل تشغيلة (fetch) بترجع بس آخر 24 ساعة، فالنقط الأقدم من كده مش هتظهر
تاني إلا لو محفوظة هنا. الأداة نفسها ما بتحكمش إيه اللي "لسه من غير رد" — ده قرار هادي وقت
التلخيص (`HADI_FOLLOWUP_INSTRUCTIONS.md`)، الأداة بس بتخزّن وتسترجع.
"""

import json
import os
import subprocess
import sys
import uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from pathlib import Path

import requests

# بند 8.2: الكود ده كان متكرر في الروتينات التلاتة — مصدر واحد دلوقتي
import routines_common
from routines_common import log, api_get, api_post, auth_headers, get_token, is_truthy, load_env_file, open_dm_channel, resolve_guild_id, resolve_user_id, send_dm

routines_common.set_prefix("FOLLOWUP")  # اللوج يفضل زي ما هو

API_BASE = "https://discord.com/api/v10"
# F5: توقيت القاهرة الحقيقي (بيتنقل EET/EEST لوحده) بدل UTC+3 الثابت اللي كان
# هيغلط ساعة كاملة بعد رجوع الساعة الشتوي 2026-10-29.
CAIRO_TZ = ZoneInfo("Africa/Cairo")
BASE = Path(__file__).resolve().parent
PENDING_STORE = BASE / "followup_pending.json"








def is_dry_run(cli_flag: bool = False) -> bool:
    return cli_flag or is_truthy(os.environ.get("FOLLOWUP_DRY_RUN"))












def resolve_channel_id() -> str | None:
    """قناة الدعم بالـ ID دايمًا — مش بالبحث بالاسم.

    اسم القناة الحقيقي «8orders-issues» مفهوش كلمة support/دعم/سابورت، فالبحث بالاسم
    القديم كان بيفشل ويرجّع None. بنعتمد على الـ ID الرسمي (قابل للتعديل من .env)."""
    return (os.environ.get("SUPPORT_CHANNEL_ID")
            or os.environ.get("ISSUES_CHANNEL_ID")
            or "1179369466279235584")


def fetch_today_messages() -> list[dict]:
    """يجيب رسائل آخر 24 ساعة من لحظة التشغيل (توقيت القاهرة) من قناة الدعم."""
    channel_id = resolve_channel_id()
    if not channel_id:
        return []

    # نافذة متحركة: آخر 24 ساعة من لحظة التشغيل — نفس podaily/marsteam بالظبط
    # (قرار آسر 2026-07-26). قبل كده كانت مربوطة بمرساة ثابتة 19:00، فأي تشغيل
    # يدوي خارج الميعاد كان بيقرا نافذة مختلفة عن التايمر.
    window_end = datetime.now(CAIRO_TZ)
    window_start = window_end - timedelta(hours=24)

    messages = []
    before = None
    for _ in range(10):  # حد أقصى ~1000 رسالة، كفاية ليوم واحد
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
                    "id": msg.get("id"),
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

    messages.reverse()  # ترتيب زمني تصاعدي
    return messages








def _load_pending() -> list[dict]:
    if not PENDING_STORE.exists():
        return []
    try:
        return json.loads(PENDING_STORE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        log(f"تعذر قراءة {PENDING_STORE.name}: {exc}")
        return []


def _save_pending(items: list[dict]) -> None:
    PENDING_STORE.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def _git_persist_pending(message: str) -> None:
    """best-effort: بيتم الـ commit + push عشان النقط المتتبَّعة تعيش لتشغيلة الروتين الجاية
    (كل تشغيلة ممكن تبقى على container جديد تمامًا)."""
    try:
        for cmd in (["add", str(PENDING_STORE)], ["commit", "-m", message]):
            subprocess.run(["git", "-C", str(BASE), *cmd], check=True, capture_output=True, timeout=30)
        subprocess.run(["git", "-C", str(BASE), "push"], check=True, capture_output=True, timeout=60)
    except Exception as exc:
        log(f"محفوظ محليًا بس فشل git persist: {type(exc).__name__} — هيتزامن مع أول push ناجح")


def cmd_pending_list() -> None:
    print(json.dumps(_load_pending(), ensure_ascii=False, indent=2))


def cmd_pending_add(flags: dict) -> None:
    content = (flags.get("content") or "").strip()
    if not content:
        log("محتاج --content (نص النقطة اللي لسه من غير رد)")
        sys.exit(1)

    item = {
        "id": uuid.uuid4().hex[:8],
        "message_id": flags.get("message-id"),
        "author": flags.get("author") or "unknown",
        "author_id": flags.get("author-id"),
        "content": content,
        "timestamp": flags.get("timestamp"),
        "note": flags.get("note", ""),
        "flagged_at": datetime.now(CAIRO_TZ).strftime("%Y-%m-%d %H:%M") + " القاهرة",
    }
    items = _load_pending()
    items.append(item)
    _save_pending(items)
    _git_persist_pending(f"followup: track pending point from {item['author']}")
    print(f"PENDING_ADDED #{item['id']}")


def cmd_pending_resolve(flags: dict) -> None:
    item_id = flags.get("id")
    if not item_id:
        log("محتاج --id بتاع النقطة اللي هتقفلها")
        sys.exit(1)

    items = _load_pending()
    remaining = [i for i in items if i.get("id") != item_id]
    if len(remaining) == len(items):
        log(f"مفيش نقطة متتبَّعة بالـ id ده: {item_id}")
        sys.exit(1)

    _save_pending(remaining)
    _git_persist_pending(f"followup: resolve pending point #{item_id}")
    print(f"PENDING_RESOLVED #{item_id}")


def post_message(content: str, dry_run: bool = False, mention_ids=None) -> bool:
    if dry_run:
        print("FOLLOWUP: DRY RUN — لم يُنشر في القناة العامة")
        print(content)

        dm_user_id = os.environ.get("FOLLOWUP_DM_USER_ID")
        if dm_user_id:
            if send_dm(dm_user_id, content):
                log(f"تم إرسال نسخة تجريبية DM للمستخدم {dm_user_id}")
            else:
                log(f"فشل إرسال DM التجريبي للمستخدم {dm_user_id}")
        else:
            log("FOLLOWUP_DM_USER_ID مش محدد — الملخص اتطبع في stdout بس من غير DM")

        return True

    channel_id = resolve_channel_id()
    if not channel_id:
        return False

    # المنشن بيتحدد صراحةً في allowed_mentions — أي @everyone جاي في نص
    # الموديل مابيتنفذش (parse=[]). التقسيم فوق 2000 حرف متعامل معاه.
    return routines_common.post_to_channel(channel_id, content, mention_ids)


def parse_flags(args: list[str]) -> dict:
    """--key value --key2 "value 2" -> {"key": "value", "key2": "value 2"}"""
    flags = {}
    i = 0
    while i < len(args):
        arg = args[i]
        if arg.startswith("--"):
            key = arg[2:]
            value = args[i + 1] if i + 1 < len(args) else ""
            flags[key] = value
            i += 2
        else:
            i += 1
    return flags


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
        print(
            "Usage: discord_followup.py [--dry-run] fetch | post \"<text>\" | pending list|add|resolve",
            file=sys.stderr,
        )
        sys.exit(1)

    command = args[0]
    dry_run = is_dry_run(cli_dry_run)

    if command == "fetch":
        messages = fetch_today_messages()
        print(json.dumps(messages, ensure_ascii=False, indent=2))
        return

    if command == "post":
        if len(args) < 2:
            log("محتاج تبعت النص اللي عايز تنشره: post \"<text>\"")
            sys.exit(1)
        ok = post_message(args[1], dry_run=dry_run, mention_ids=mention_ids)
        sys.exit(0 if ok else 1)

    if command == "pending":
        if len(args) < 2:
            log("محتاج sub-command: pending list | add | resolve")
            sys.exit(1)
        sub = args[1]
        flags = parse_flags(args[2:])
        if sub == "list":
            cmd_pending_list()
        elif sub == "add":
            cmd_pending_add(flags)
        elif sub == "resolve":
            cmd_pending_resolve(flags)
        else:
            log(f"Unknown pending sub-command: {sub}")
            sys.exit(1)
        return

    print(f"Unknown command: {command}", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
