#!/usr/bin/env python3
"""روتين هادي أمين لقناة 8order-po — كل يومين: أفكار → CRs على Azure DevOps + متابعة.

بيعتمد على الدوال المشتركة في discord_followup.py (نفس التوكن ونفس أسلوب الأخطاء).

الأوامر:
  python3 discord_orderpo.py fetch [--hours 48]
      -> يطبع JSON فيه رسائل آخر N ساعة من قناة 8order-po (افتراضي 48).
         كل رسالة فيها: id / author / author_id / is_bot / content / timestamp /
         reply_to (لو الرسالة رد على رسالة تانية) / mentions.

  python3 discord_orderpo.py reply <message_id> "<نص>"
      -> يرد على رسالة محددة في القناة (Reply حقيقي). المنشنات بصيغة <@user_id>.

  python3 discord_orderpo.py post "<نص>"
      -> رسالة عادية في القناة (للملخصات).

  python3 discord_orderpo.py search-cr "<كلمة>" ["<كلمة تانية>" ...]
      -> يدوّر في CRs الموجودة على بورد Change Requests (منع التكرار قبل أي إنشاء).

  python3 discord_orderpo.py create-cr --title "<عنوان>" --description "<وصف HTML>" [--tags "<تاجات إضافية>"]
      -> ينشئ Change Request على Area Path بتاع البورد ويرجّع {id, url}.

وضع التجربة (dry-run): زي discord_followup بالظبط — env `FOLLOWUP_DRY_RUN` أو فلاج `--dry-run`.
في الوضع ده: reply/post/create-cr ما بينفذوش أي كتابة حقيقية (طباعة فقط + نسخة DM لو
`FOLLOWUP_DM_USER_ID` محدد). fetch و search-cr قراءة بس فبيشتغلوا عادي.

كل خطأ بيتطبع بصيغة "ORDERPO: ..." على stderr وبيرجع exit code != 0.
"""

import base64
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from urllib.parse import quote

import requests

from discord_followup import (
    api_get,
    api_post,
    is_dry_run,
    load_env_file,
    send_dm,
)

# F5: توقيت القاهرة الحقيقي (بيتنقل EET/EEST لوحده) بدل UTC+3 الثابت اللي كان
# هيغلط ساعة كاملة بعد رجوع الساعة الشتوي 2026-10-29.
CAIRO_TZ = ZoneInfo("Africa/Cairo")

# قناة 8order-po — ثابتة، وممكن تتغير بـ env لو القناة اتنقلت
DEFAULT_ORDERPO_CHANNEL_ID = "1358833733699899704"

# إعدادات Azure DevOps — نفس قيم .env.example
DEFAULT_ADO_ORG_URL = "https://hadafsolutions.visualstudio.com"
DEFAULT_ADO_PROJECT = "0_Projects_Team"
CR_AREA_PATH = "0_Projects_Team\\Change Requests"
CR_WORK_ITEM_TYPE = "Change Request"
CR_DEFAULT_TAGS = "from-discord; 8order-po; CR-Auto"
ADO_API_VERSION = "7.1"


def log(msg: str) -> None:
    print(f"ORDERPO: {msg}", file=sys.stderr)


def orderpo_channel_id() -> str:
    return os.environ.get("ORDERPO_CHANNEL_ID", "").strip() or DEFAULT_ORDERPO_CHANNEL_ID


# ---------------------------------------------------------------------------
# Discord — قراءة القناة والرد
# ---------------------------------------------------------------------------

def fetch_window_messages(hours: int) -> dict:
    """يجيب رسائل آخر `hours` ساعة من قناة 8order-po (ترتيب زمني تصاعدي)."""
    channel_id = orderpo_channel_id()
    window_end = datetime.now(CAIRO_TZ)
    window_start = window_end - timedelta(hours=hours)

    messages = []
    before = None
    for _ in range(20):  # حد أقصى ~2000 رسالة
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

            if ts < window_start:
                stop = True
                continue

            author = msg.get("author", {})
            display_name = (
                author.get("global_name")
                or author.get("username")
                or "unknown"
            )
            reference = msg.get("message_reference") or {}
            messages.append(
                {
                    "id": msg.get("id"),
                    "author": display_name,
                    "author_id": author.get("id"),
                    "is_bot": bool(author.get("bot")),
                    "content": msg.get("content", ""),
                    "timestamp": ts.isoformat(),
                    "reply_to": reference.get("message_id"),
                    "mentions": [
                        {
                            "id": u.get("id"),
                            "name": u.get("global_name") or u.get("username"),
                        }
                        for u in msg.get("mentions", [])
                    ],
                }
            )

        before = batch[-1]["id"]
        if stop or len(batch) < 100:
            break

    messages.reverse()
    return {
        "channel_id": channel_id,
        "window_start": window_start.isoformat(),
        "window_end": window_end.isoformat(),
        "count": len(messages),
        "messages": messages,
    }


def _safe_mentions() -> dict:
    """منشنات المستخدمين بس — @everyone/@here والرولز متعطلين نهائيًا."""
    return {"parse": ["users"], "replied_user": True}


def send_channel_message(content: str, reply_to: str | None = None, dry_run: bool = False) -> bool:
    channel_id = orderpo_channel_id()

    if dry_run:
        banner = "ORDERPO: DRY RUN — لم يُنشر في القناة"
        if reply_to:
            banner += f" (كان هيبقى رد على الرسالة {reply_to})"
        print(banner)
        print(content)

        dm_user_id = os.environ.get("FOLLOWUP_DM_USER_ID")
        if dm_user_id:
            prefix = f"[تجربة 8order-po{' — رد على ' + reply_to if reply_to else ''}]\n"
            if send_dm(dm_user_id, prefix + content):
                log(f"تم إرسال نسخة تجريبية DM للمستخدم {dm_user_id}")
            else:
                log(f"فشل إرسال DM التجريبي للمستخدم {dm_user_id}")
        return True

    payload = {"content": content, "allowed_mentions": _safe_mentions()}
    if reply_to:
        payload["message_reference"] = {
            "message_id": reply_to,
            "fail_if_not_exists": False,
        }

    result = api_post(f"/channels/{channel_id}/messages", payload)
    if result is None:
        return False

    log(f"تم الإرسال لقناة {channel_id}" + (f" كرد على {reply_to}" if reply_to else ""))
    return True


# ---------------------------------------------------------------------------
# Azure DevOps — البحث وإنشاء الـ CR
# ---------------------------------------------------------------------------

def ado_config() -> tuple[str, str, str] | None:
    pat = (
        os.environ.get("AZURE_DEVOPS_PAT")
        or os.environ.get("ADO_MCP_AUTH_TOKEN")
        or ""
    ).strip()
    if not pat:
        log("AZURE_DEVOPS_PAT مش موجود في الـ environment ولا في .env")
        return None

    org_url = (os.environ.get("AZURE_DEVOPS_ORG_URL", "").strip() or DEFAULT_ADO_ORG_URL).rstrip("/")
    project = os.environ.get("AZURE_DEVOPS_DEFAULT_PROJECT", "").strip() or DEFAULT_ADO_PROJECT
    return org_url, project, pat


def ado_headers(pat: str, patch: bool = False) -> dict:
    token = base64.b64encode(f":{pat}".encode()).decode()
    return {
        "Authorization": f"Basic {token}",
        "Content-Type": "application/json-patch+json" if patch else "application/json",
    }


def _wiql_escape(term: str) -> str:
    return term.replace("'", "''")


def search_existing_crs(terms: list[str]) -> list[dict] | None:
    """WIQL على بورد Change Requests — بيرجع CRs عناوينها فيها أي من الكلمات."""
    cfg = ado_config()
    if not cfg:
        return None
    org_url, project, pat = cfg

    conditions = " OR ".join(
        f"[System.Title] CONTAINS '{_wiql_escape(t)}'" for t in terms if t.strip()
    )
    if not conditions:
        log("محتاج كلمة واحدة على الأقل للبحث")
        return None

    wiql = (
        "SELECT [System.Id] FROM WorkItems "
        f"WHERE [System.TeamProject] = '{project}' "
        f"AND [System.AreaPath] = '{CR_AREA_PATH}' "
        f"AND ({conditions}) "
        "ORDER BY [System.ChangedDate] DESC"
    )

    url = f"{org_url}/{quote(project)}/_apis/wit/wiql?api-version={ADO_API_VERSION}&$top=20"
    resp = requests.post(url, headers=ado_headers(pat), json={"query": wiql}, timeout=30)
    if resp.status_code != 200:
        log(f"WIQL فشل — status {resp.status_code}: {resp.text[:300]}")
        return None

    ids = [str(item["id"]) for item in resp.json().get("workItems", [])]
    if not ids:
        return []

    fields = "System.Id,System.Title,System.State"
    url = (
        f"{org_url}/{quote(project)}/_apis/wit/workitems"
        f"?ids={','.join(ids[:20])}&fields={fields}&api-version={ADO_API_VERSION}"
    )
    resp = requests.get(url, headers=ado_headers(pat), timeout=30)
    if resp.status_code != 200:
        log(f"جلب تفاصيل الـ work items فشل — status {resp.status_code}: {resp.text[:300]}")
        return None

    results = []
    for item in resp.json().get("value", []):
        item_id = item.get("id")
        f = item.get("fields", {})
        results.append(
            {
                "id": item_id,
                "title": f.get("System.Title"),
                "state": f.get("System.State"),
                "url": f"{org_url}/{quote(project)}/_workitems/edit/{item_id}",
            }
        )
    return results


def create_cr(title: str, description_html: str, extra_tags: str = "", dry_run: bool = False) -> dict | None:
    cfg = ado_config()
    if not cfg:
        return None
    org_url, project, pat = cfg

    tags = CR_DEFAULT_TAGS + (f"; {extra_tags.strip()}" if extra_tags.strip() else "")
    ops = [
        {"op": "add", "path": "/fields/System.Title", "value": title},
        {"op": "add", "path": "/fields/System.Description", "value": description_html},
        {"op": "add", "path": "/fields/System.AreaPath", "value": CR_AREA_PATH},
        {"op": "add", "path": "/fields/System.Tags", "value": tags},
    ]

    if dry_run:
        print("ORDERPO: DRY RUN — لم يُنشأ CR حقيقي. البيانات اللي كانت هتتبعت:")
        print(json.dumps({"type": CR_WORK_ITEM_TYPE, "ops": ops}, ensure_ascii=False, indent=2))
        return {"id": 0, "url": "(dry-run)", "title": title, "dry_run": True}

    url = (
        f"{org_url}/{quote(project)}/_apis/wit/workitems/"
        f"${quote(CR_WORK_ITEM_TYPE)}?api-version={ADO_API_VERSION}"
    )
    resp = requests.post(url, headers=ado_headers(pat, patch=True), json=ops, timeout=30)
    if resp.status_code not in (200, 201):
        log(f"إنشاء الـ CR فشل — status {resp.status_code}: {resp.text[:300]}")
        return None

    item = resp.json()
    item_id = item.get("id")
    result = {
        "id": item_id,
        "title": title,
        "url": f"{org_url}/{quote(project)}/_workitems/edit/{item_id}",
    }
    log(f"تم إنشاء CR رقم {item_id}")
    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_option(args: list[str], name: str) -> tuple[list[str], str]:
    """يسحب قيمة أوبشن زي --title من قائمة الأرجيومنتس."""
    if name not in args:
        return args, ""
    idx = args.index(name)
    if idx + 1 >= len(args):
        log(f"الأوبشن {name} محتاج قيمة بعده")
        sys.exit(1)
    value = args[idx + 1]
    return args[:idx] + args[idx + 2:], value


def main() -> None:
    load_env_file()

    args = sys.argv[1:]
    cli_dry_run = "--dry-run" in args
    if cli_dry_run:
        args = [a for a in args if a != "--dry-run"]
    dry_run = is_dry_run(cli_dry_run)

    if not args:
        print(__doc__, file=sys.stderr)
        sys.exit(1)

    command = args[0]
    rest = args[1:]

    if command == "fetch":
        rest, hours_raw = _parse_option(rest, "--hours")
        try:
            hours = int(hours_raw) if hours_raw else int(os.environ.get("ORDERPO_WINDOW_HOURS", "48"))
        except ValueError:
            log("--hours لازم يكون رقم صحيح")
            sys.exit(1)
        result = fetch_window_messages(hours)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    if command == "reply":
        if len(rest) < 2:
            log('الاستخدام: reply <message_id> "<نص>"')
            sys.exit(1)
        ok = send_channel_message(rest[1], reply_to=rest[0], dry_run=dry_run)
        sys.exit(0 if ok else 1)

    if command == "post":
        if len(rest) < 1:
            log('الاستخدام: post "<نص>"')
            sys.exit(1)
        ok = send_channel_message(rest[0], dry_run=dry_run)
        sys.exit(0 if ok else 1)

    if command == "search-cr":
        if not rest:
            log('الاستخدام: search-cr "<كلمة>" ["<كلمة تانية>" ...]')
            sys.exit(1)
        results = search_existing_crs(rest)
        if results is None:
            sys.exit(1)
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return

    if command == "create-cr":
        rest, title = _parse_option(rest, "--title")
        rest, description = _parse_option(rest, "--description")
        rest, extra_tags = _parse_option(rest, "--tags")
        if not title or not description:
            log('الاستخدام: create-cr --title "<عنوان>" --description "<وصف HTML>" [--tags "..."]')
            sys.exit(1)
        result = create_cr(title, description, extra_tags, dry_run=dry_run)
        if result is None:
            sys.exit(1)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    print(f"Unknown command: {command}", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
