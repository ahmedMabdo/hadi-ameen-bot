#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""مكتبة الروتينات المشتركة (بند 8.2) — مصدر واحد للكود المتكرر.

مولَّدة بـ unify_routines2.py من السورس الأصلي لسكربتات الروتين. كانت الدوال دي
متكررة حرفيًا في 3 سكربتات (followup / podaily / marsteam) = ~240 سطر صيانة مكررة.

**بادئة اللوج:** كل سكربت بينادي `set_prefix("PODAILY")` وهكذا عند الاستيراد،
فمخرجات stderr بتفضل زي ما كانت بالظبط.

**resolve_guild_id:** النسخة المعتمدة هنا هي بتاعة marsteam/followup (المتطابقين)
اللي فيها حارس «البوت مش عضو في أي guild» — podaily كان ناقصه الحارس ده وبقى عنده.

أي تعديل هنا بيأثر على الروتينات الثلاثة: شغّل `fetch` لكل واحد وقارن قبل/بعد.
"""

import os
import sys
import requests


API_BASE = "https://discord.com/api/v10"


# بادئة اللوج لكل روتين — بتتضبط من السكربت المستورد (بند 8.2)
PREFIX = "ROUTINE"


def set_prefix(name: str) -> None:
    """بيحدد بادئة اللوج (FOLLOWUP / PODAILY / MARSTEAM) — نفس المخرجات القديمة."""
    global PREFIX
    PREFIX = name


def log(msg: str) -> None:
    print(f"{PREFIX}: {msg}", file=sys.stderr)


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


def auth_headers() -> dict:
    return {
        "Authorization": f"Bot {get_token()}",
        "Content-Type": "application/json",
    }


def get_token() -> str:
    token = os.environ.get("DISCORD_BOT_TOKEN")
    if not token:
        log("DISCORD_BOT_TOKEN مش موجود في الـ environment ولا في .env")
        sys.exit(1)
    return token


def is_truthy(value: str | None) -> bool:
    if not value:
        return False
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def load_env_file(path: str = ".env") -> None:
    """يقرا متغيرات من ملف .env لو موجود، من غير ما يكسر لو مش موجود أو فيه سطور غلط."""
    if not os.path.isfile(path):
        return
    try:
        # errors="replace" عشان الملف لو متسجل بترميز مش UTF-8 سليم ما يكسرش الروتين كله
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value
    except (OSError, UnicodeError) as exc:
        log(f"تعذر قراءة {path}: {exc}")


def open_dm_channel(user_id: str) -> str | None:
    result = api_post("/users/@me/channels", {"recipient_id": user_id})
    if not result:
        log(f"مقدرش أفتح DM مع المستخدم {user_id}")
        return None
    return result.get("id")


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


def send_dm(user_id: str, content: str) -> bool:
    dm_channel_id = open_dm_channel(user_id)
    if not dm_channel_id:
        return False

    result = api_post(f"/channels/{dm_channel_id}/messages", {"content": content})
    return result is not None


# ---------------------------------------------------------------------------
# النشر في القناة بمنشن آمن (بند المتابعة اليومية)
# ---------------------------------------------------------------------------
# ليه allowed_mentions إلزامية: نص الملخص جاي من موديل بيقرا رسايل مستخدمين.
# من غير القيد ده، أي "@everyone" في كلام حد في القناة ممكن يعدّي في الملخص
# ويعمل ping للسيرفر كله. parse=[] بيلغي @everyone/@here/الرولز تمامًا،
# وusers بتحدد بالظبط مين ينفع يتنبّه.
DISCORD_MSG_LIMIT = 2000


def split_for_discord(text: str, limit: int = 1900) -> list:
    """تقسيم على حدود الأسطر مع قطع اضطراري للسطر الأطول من الحد."""
    chunks, current = [], ""
    for line in (text or "").split("\n"):
        while len(line) > limit:
            if current:
                chunks.append(current)
                current = ""
            chunks.append(line[:limit])
            line = line[limit:]
        candidate = f"{current}\n{line}" if current else line
        if len(candidate) > limit:
            if current:
                chunks.append(current)
            current = line
        else:
            current = candidate
    if current:
        chunks.append(current)
    return [c for c in chunks if c.strip()] or [(text or "")[:limit]]


def post_to_channel(channel_id: str, content: str, mention_ids=None) -> bool:
    """ينشر الملخص في القناة. المنشن مسموح بس للـ ids المحددة صراحةً.

    بيرجّع True لو كل الأجزاء اتبعتت. أول جزء بس هو اللي بيحمل المنشنات —
    الباقي بـ parse=[] عشان مايتكررش الإشعار.
    """
    ids = [str(i) for i in (mention_ids or []) if str(i).strip().isdigit()]
    chunks = split_for_discord(content)
    for index, chunk in enumerate(chunks):
        payload = {
            "content": chunk,
            "allowed_mentions": {"parse": [], "users": ids if index == 0 else []},
        }
        if api_post(f"/channels/{channel_id}/messages", payload) is None:
            log(f"فشل نشر الجزء {index + 1}/{len(chunks)} في القناة {channel_id}")
            return False
    log(f"تم إرسال الملخص لقناة {channel_id} ({len(chunks)} رسالة، "
        f"{len(ids)} منشن)")
    return True
