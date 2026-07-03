#!/usr/bin/env python3
"""متابعة يومية لهادي أمين على ديسكورد — Discord REST API v10 مباشرة.

الأوامر:
  python3 discord_followup.py fetch                -> يطبع رسائل اليوم (قناة الدعم) كـ JSON على stdout
  python3 discord_followup.py post "<نص>"          -> يبعت النص كرسالة في قناة الدعم
  python3 discord_followup.py post --dry-run "<نص>" -> وضع تجربة: ما يبعتش في القناة العامة

وضع التجربة (dry-run) بيتفعّل لو env `FOLLOWUP_DRY_RUN` قيمته true/1/yes، أو بفلاج
`--dry-run` في الأمر. في وضع التجربة الملخص بيتطبع في stdout بس، وبيتبعت DM خاص
لو `FOLLOWUP_DM_USER_ID` محدد — من غير أي نشر في القناة العامة.

كل خطأ بيتطبع بصيغة "FOLLOWUP: ..." على stderr وبيرجع exit code != 0 من غير ما يكسر باقي الروتين.
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone

import requests

API_BASE = "https://discord.com/api/v10"
CAIRO_TZ = timezone(timedelta(hours=3))


def log(msg: str) -> None:
    print(f"FOLLOWUP: {msg}", file=sys.stderr)


def load_env_file(path: str = ".env") -> None:
    """يقرا متغيرات من ملف .env لو موجود، من غير ما يكسر لو مش موجود أو فيه سطور غلط."""
    if not os.path.isfile(path):
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value
    except OSError as exc:
        log(f"تعذر قراءة {path}: {exc}")


def is_truthy(value: str | None) -> bool:
    if not value:
        return False
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def is_dry_run(cli_flag: bool = False) -> bool:
    return cli_flag or is_truthy(os.environ.get("FOLLOWUP_DRY_RUN"))


def get_token() -> str:
    token = os.environ.get("DISCORD_BOT_TOKEN")
    if not token:
        log("DISCORD_BOT_TOKEN مش موجود في الـ environment ولا في .env")
        sys.exit(1)
    return token


def auth_headers() -> dict:
    return {
        "Authorization": f"Bot {get_token()}",
        "Content-Type": "application/json",
    }


def api_get(path: str, params: dict | None = None):
    url = f"{API_BASE}{path}"
    resp = requests.get(url, headers=auth_headers(), params=params, timeout=30)
    if resp.status_code != 200:
        log(f"GET {path} فشل — status {resp.status_code}: {resp.text[:300]}")
        return None
    return resp.json()


def api_post(path: str, payload: dict):
    url = f"{API_BASE}{path}"
    resp = requests.post(url, headers=auth_headers(), json=payload, timeout=30)
    if resp.status_code not in (200, 201):
        log(f"POST {path} فشل — status {resp.status_code}: {resp.text[:300]}")
        return None
    return resp.json()


def resolve_guild_id() -> str | None:
    guild_id = os.environ.get("DISCORD_GUILD_ID")
    if guild_id:
        return guild_id

    guilds = api_get("/users/@me/guilds")
    if not guilds:
        log("مقدرش أجيب guilds بتاعة البوت — تأكد من DISCORD_BOT_TOKEN")
        return None

    if len(guilds) == 1:
        gid = guilds[0]["id"]
        log(f"تم اختيار guild تلقائيًا: {guilds[0].get('name')} ({gid})")
        return gid

    if len(guilds) == 0:
        log("البوت مش عضو في أي guild")
        return None

    log(
        "البوت عضو في أكتر من guild واحدة — حدد DISCORD_GUILD_ID. "
        f"الخيارات: {[(g.get('name'), g.get('id')) for g in guilds]}"
    )
    return None


def resolve_channel_id() -> str | None:
    channel_id = os.environ.get("SUPPORT_CHANNEL_ID")
    if channel_id:
        return channel_id

    guild_id = resolve_guild_id()
    if not guild_id:
        return None

    channels = api_get(f"/guilds/{guild_id}/channels")
    if not channels:
        log("مقدرش أجيب قنوات الـ guild")
        return None

    name_hint = os.environ.get("SUPPORT_CHANNEL_NAME", "").strip().lower()
    hints = [name_hint] if name_hint else ["support", "دعم", "سابورت"]

    for channel in channels:
        cname = (channel.get("name") or "").lower()
        if any(hint and hint in cname for hint in hints):
            log(f"تم إيجاد قناة الدعم تلقائيًا: #{channel.get('name')} ({channel['id']})")
            return channel["id"]

    log(f"مقدرش ألاقي قناة اسمها فيه أي من {hints} — حدد SUPPORT_CHANNEL_ID")
    return None


def fetch_today_messages() -> list[dict]:
    """يجيب رسائل آخر 24 ساعة (من 7م امبارح لـ 7م النهاردة بتوقيت القاهرة) من قناة الدعم."""
    channel_id = resolve_channel_id()
    if not channel_id:
        return []

    now_cairo = datetime.now(CAIRO_TZ)
    window_end = now_cairo.replace(hour=19, minute=0, second=0, microsecond=0)
    if now_cairo < window_end:
        window_end = window_end - timedelta(days=1)
    window_start = window_end - timedelta(days=1)

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
                    "author": display_name,
                    "author_id": author.get("id"),
                    "content": msg.get("content", ""),
                    "timestamp": ts.isoformat(),
                }
            )

        before = batch[-1]["id"]
        if stop or len(batch) < 100:
            break

    messages.reverse()  # ترتيب زمني تصاعدي
    return messages


def resolve_user_id(name: str) -> str | None:
    """يبحث عن عضو بالاسم في الـ guild وبيرجع الـ id بتاعه للمنشن."""
    guild_id = resolve_guild_id()
    if not guild_id:
        return None

    results = api_get(f"/guilds/{guild_id}/members/search", params={"query": name, "limit": 5})
    if not results:
        log(f"مقدرش ألاقي عضو بالاسم '{name}'")
        return None

    first = results[0]
    user = first.get("user", {})
    user_id = user.get("id")
    if not user_id:
        log(f"نتيجة البحث عن '{name}' مالهاش user id واضح")
        return None

    if len(results) > 1:
        matched_name = user.get("global_name") or user.get("username")
        log(f"لقيت أكتر من عضو بالاسم '{name}' — استخدمت أول نتيجة: {matched_name} ({user_id})")

    return user_id


def open_dm_channel(user_id: str) -> str | None:
    result = api_post("/users/@me/channels", {"recipient_id": user_id})
    if not result:
        log(f"مقدرش أفتح DM مع المستخدم {user_id}")
        return None
    return result.get("id")


def send_dm(user_id: str, content: str) -> bool:
    dm_channel_id = open_dm_channel(user_id)
    if not dm_channel_id:
        return False

    result = api_post(f"/channels/{dm_channel_id}/messages", {"content": content})
    return result is not None


def post_message(content: str, dry_run: bool = False) -> bool:
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

    result = api_post(f"/channels/{channel_id}/messages", {"content": content})
    if result is None:
        return False

    log(f"تم إرسال الملخص لقناة {channel_id}")
    return True


def main() -> None:
    load_env_file()

    args = sys.argv[1:]
    cli_dry_run = "--dry-run" in args
    if cli_dry_run:
        args = [a for a in args if a != "--dry-run"]

    if not args:
        print("Usage: discord_followup.py [--dry-run] fetch | post \"<text>\"", file=sys.stderr)
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
        ok = post_message(args[1], dry_run=dry_run)
        sys.exit(0 if ok else 1)

    print(f"Unknown command: {command}", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
