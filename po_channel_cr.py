#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Discord channel -> ADO boards bridge, built as a CLI for Hadi (the
interactive Discord agent on AWS) to call as a tool. Hadi does the judgment
(summarize the discussion, decide what counts as a NEW idea); this script
does the deterministic I/O:

  fetch    read the latest messages from a Discord channel
           (default: the PO channel 1358833733699899704) over the Discord
           REST API using the same bot token as discord_delivery.py.
  file-cr  create one Change Request work item on the ADO
           "Change Requests" board (Project 0_Projects_Team, Area Path
           `0_Projects_Team\\Change Requests`, Stories board), deduped by a
           `po-msg-<message_id>` tag so the same idea is never filed twice.
           Prints the work item's browser URL on success.
  post     send a message into a channel (the summary + CR links).

Channels: aliases po (default) / mars / issues, or any raw channel id.

The intended workflow (full text in HADI_PO_CHANNEL_INSTRUCTIONS.md):
  1. fetch --json           -> Hadi reads and summarizes the discussion
  2. file-cr ... per idea   -> one CR per genuinely new idea, link printed
  3. post --text "..."      -> summary + CR links back into the channel

Env (read from a `.env` file alongside this script if present, else the
process environment):
  DISCORD_BOT_TOKEN   bot token — same one discord_delivery.py uses. The bot
                      needs View Channel + Read Message History on the
                      channel (and Send Messages for `post`).
  PO_CHANNEL_ID       PO channel id; defaults to 1358833733699899704.
  MARS_CHANNEL_ID     Mars channel id; defaults to 1136668686044909761.
  ISSUES_CHANNEL_ID   8orders-issues channel id; defaults to
                      1179369466279235584.
  AZURE_DEVOPS_PAT    ADO personal access token, Work Items Read & Write
                      (same one ado_client.py uses) — needed for `file-cr`.
  ADO_CR_AREA_PATH    default `0_Projects_Team\\Change Requests`.
  ADO_CR_TYPE         work item type to create; default "Change Request"
                      (confirmed: the Change Requests board uses this type —
                      NOT "Issue", that's the Support board's type). On a
                      type error the script prints the valid type names for
                      the project to pick from.

Like discord_delivery.py, per-call failures print a clear error and exit
non-zero instead of raising tracebacks, so Hadi can read what went wrong
and relay it.
"""
import argparse
import datetime as dt
import json
import os
import sys

import requests

# reuse the proven ADO plumbing (env parsing, org/project/base URL, auth,
# mandatory Customer/Application field values) from the existing client
import ado_client
import cr_media
from ado_client import ADO_BASE, ADO_API_VERSION, ADO_CUSTOMER, ADO_APPLICATION

API_BASE = "https://discord.com/api/v10"
DEFAULT_PO_CHANNEL_ID = "1358833733699899704"
DEFAULT_MARS_CHANNEL_ID = "1136668686044909761"
DEFAULT_ISSUES_CHANNEL_ID = "1179369466279235584"

ADO_CR_AREA_PATH = os.environ.get("ADO_CR_AREA_PATH", r"0_Projects_Team\Change Requests")
ADO_CR_TYPE = os.environ.get("ADO_CR_TYPE", "Change Request")


def _bot_token():
    token = os.environ.get("DISCORD_BOT_TOKEN")
    if not token:
        sys.exit("ERROR: DISCORD_BOT_TOKEN not set")
    return token


def _discord_headers():
    return {"Authorization": f"Bot {_bot_token()}"}


def _channel_id(args):
    """Resolve --channel: the aliases 'po' / 'mars' / 'issues', a raw channel
    id, or the PO channel by default — so Hadi can relay a request like 'send
    this to the Mars group' without knowing snowflake ids."""
    raw = (args.channel or "po").strip().lower()
    if raw == "po":
        return os.environ.get("PO_CHANNEL_ID", DEFAULT_PO_CHANNEL_ID)
    if raw == "mars":
        return os.environ.get("MARS_CHANNEL_ID", DEFAULT_MARS_CHANNEL_ID)
    if raw == "issues":
        return os.environ.get("ISSUES_CHANNEL_ID", DEFAULT_ISSUES_CHANNEL_ID)
    return args.channel.strip()


def _channel_label(channel_id):
    """Human label for the source channel, used in CR descriptions so the
    ticket never claims a wrong origin."""
    if channel_id == os.environ.get("PO_CHANNEL_ID", DEFAULT_PO_CHANNEL_ID):
        return "قناة الـ PO"
    if channel_id == os.environ.get("MARS_CHANNEL_ID", DEFAULT_MARS_CHANNEL_ID):
        return "قناة مارس"
    if channel_id == os.environ.get("ISSUES_CHANNEL_ID", DEFAULT_ISSUES_CHANNEL_ID):
        return "قناة 8orders-issues"
    return f"قناة Discord ({channel_id})"


def _cairo(ts_iso):
    """Discord ISO timestamp -> readable Cairo local time."""
    try:
        from zoneinfo import ZoneInfo
        t = dt.datetime.fromisoformat(ts_iso.replace("Z", "+00:00"))
        return t.astimezone(ZoneInfo("Africa/Cairo")).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return ts_iso


def _get_channel(channel_id):
    r = requests.get(f"{API_BASE}/channels/{channel_id}",
                     headers=_discord_headers(), timeout=15)
    if r.status_code == 403:
        sys.exit(f"ERROR: bot has no access to channel {channel_id} — grant it "
                 "View Channel + Read Message History there")
    r.raise_for_status()
    return r.json()


def _jump_link(guild_id, channel_id, message_id):
    return f"https://discord.com/channels/{guild_id or '@me'}/{channel_id}/{message_id}"


def _message_row(m, guild_id, channel_id):
    author = m.get("author") or {}
    content = m.get("content") or ""
    extras = [a.get("filename", "attachment") for a in m.get("attachments") or []]
    extras += [e.get("title") for e in m.get("embeds") or [] if e.get("title")]
    if extras:
        content = (content + " " if content else "") + "[" + ", ".join(extras) + "]"
    return {
        "id": m["id"],
        "time_cairo": _cairo(m.get("timestamp", "")),
        "author": author.get("global_name") or author.get("username") or "?",
        "bot": bool(author.get("bot")),
        "content": content,
        "media": cr_media.media_from_message(m),
        "jump_link": _jump_link(guild_id, channel_id, m["id"]),
    }


def cmd_fetch(args):
    channel_id = _channel_id(args)
    channel = _get_channel(channel_id)
    guild_id = channel.get("guild_id")

    params = {"limit": max(1, min(args.limit, 100))}
    if args.after_msg:
        params["after"] = args.after_msg
    r = requests.get(f"{API_BASE}/channels/{channel_id}/messages",
                     headers=_discord_headers(), params=params, timeout=30)
    r.raise_for_status()
    rows = [_message_row(m, guild_id, channel_id) for m in r.json()]
    rows.reverse()  # Discord returns newest first; read chronologically

    if args.json:
        print(json.dumps({"channel": channel.get("name"), "channel_id": channel_id,
                          "messages": rows}, ensure_ascii=False, indent=2))
        return
    print(f"# آخر {len(rows)} رسالة في #{channel.get('name', channel_id)}\n")
    for m in rows:
        bot_mark = " [bot]" if m["bot"] else ""
        print(f"[{m['time_cairo']}] {m['author']}{bot_mark} (msg {m['id']}):")
        print(f"  {m['content']}\n")


def _cr_already_filed(dedup_tag, headers):
    wiql = {"query": ("SELECT [System.Id] FROM WorkItems "
                      f"WHERE [System.TeamProject] = '{ado_client.ADO_PROJECT}' "
                      f"AND [System.Tags] CONTAINS '{dedup_tag.replace(chr(39), chr(39) * 2)}'")}
    r = requests.post(f"{ADO_BASE}/wit/wiql?api-version={ADO_API_VERSION}",
                      headers={**headers, "Content-Type": "application/json"},
                      json=wiql, timeout=30)
    r.raise_for_status()
    items = r.json().get("workItems") or []
    return items[0]["id"] if items else None


def _list_work_item_types(headers):
    r = requests.get(f"{ADO_BASE}/wit/workitemtypes?api-version={ADO_API_VERSION}",
                     headers=headers, timeout=30)
    r.raise_for_status()
    return [t["name"] for t in r.json().get("value", [])]


def cmd_file_cr(args):
    headers = ado_client._auth_headers()
    channel_id = _channel_id(args)
    channel_label = _channel_label(channel_id)

    dedup_tag = f"po-msg-{args.source_msg}" if args.source_msg else None
    if dedup_tag:
        existing = _cr_already_filed(dedup_tag, headers)
        if existing:
            url = f"{ado_client.ADO_ORG_BASE}/{ado_client.ADO_PROJECT}/_workitems/edit/{existing}"
            print(f"SKIP: already filed as #{existing} -> {url}")
            return

    source_note = ""
    if args.source_msg:
        link = _jump_link(args.guild, channel_id, args.source_msg)
        source_note = (f"<div>المصدر: رسالة في {channel_label} — "
                       f"<a href=\"{link}\">{link}</a></div>")
    desc = (f"<div><strong>فكرة من {channel_label} (رفعها هادي)</strong></div>"
            f"<div>{args.brief}</div>{source_note}")

    tags = "po-channel; change-request" + (f"; {dedup_tag}" if dedup_tag else "")
    payload = [
        {"op": "add", "path": "/fields/System.Title", "value": args.title},
        {"op": "add", "path": "/fields/System.Description", "value": desc},
        {"op": "add", "path": "/fields/System.Tags", "value": tags},
        {"op": "add", "path": "/fields/System.AreaPath", "value": ADO_CR_AREA_PATH},
        {"op": "add", "path": "/fields/myagile.Customer", "value": ADO_CUSTOMER},
        # نقطة 4 (F13): Custom.Application اتشال — مش من حقول نوع Change Request
        # (متحقق من تعريف النوع في ADO الحي 2026-07-24).
        {"op": "add", "path": "/fields/System.State", "value": "New"},
    ]
    for _extra in (args.field or []):
        if "=" in _extra:
            _p, _v = _extra.split("=", 1)
            payload.append({"op": "add", "path": f"/fields/{_p.strip()}", "value": _v})
    _provided = {op["path"].split("/fields/", 1)[-1] for op in payload if "/fields/" in op.get("path", "")}
    # F12: منصة/تصنيف الـ CR بيتستنتجوا من عنوان الفكرة ووصفها بدل defaults ثابتة
    payload += cr_media.required_field_ops(
        ADO_CR_TYPE, _provided, context_text=f"{args.title or ''} {args.brief or ''}"
    )

    if args.dry_run:
        print(f"DRY-RUN would create {ADO_CR_TYPE} in '{ADO_CR_AREA_PATH}': {args.title}")
        return

    r = requests.post(
        f"{ADO_BASE}/wit/workitems/${ADO_CR_TYPE}?api-version={ADO_API_VERSION}",
        headers={**headers, "Content-Type": "application/json-patch+json"},
        json=payload, timeout=30)
    if r.status_code not in (200, 201):
        msg = r.text[:400]
        if "work item type" in msg.lower() or r.status_code == 404:
            try:
                types = _list_work_item_types(headers)
                msg += (f"\nValid work item types in this project: {', '.join(types)}"
                        f"\nSet ADO_CR_TYPE to the right one.")
            except Exception:
                pass
        sys.exit(f"FAILED to create CR: HTTP {r.status_code} {msg}")

    wi = r.json()
    url = wi.get("_links", {}).get("html", {}).get("href", "")
    print(f"CREATED CR #{wi['id']} -> {url}")
    cr_media.maybe_attach_media(args, wi, channel_id, headers)


def cmd_post(args):
    channel_id = _channel_id(args)
    text = args.text if args.text is not None else sys.stdin.read()
    text = text.strip()
    if not text:
        sys.exit("ERROR: nothing to post — pass --text or pipe the message on stdin")
    # Discord hard limit is 2000 chars per message. المصدر الواحد للتقسيم —
    # النسخة القديمة هنا كانت بتبعت سطر أطول من 2000 كما هو وتاخد HTTP 400.
    import routines_common
    chunks = routines_common.split_for_discord(text)
    for chunk in chunks:
        r = requests.post(f"{API_BASE}/channels/{channel_id}/messages",
                          headers={**_discord_headers(),
                                   "Content-Type": "application/json"},
                          json={"content": chunk}, timeout=30)
        if r.status_code == 403:
            sys.exit(f"ERROR: bot can't post in channel {channel_id} — grant it "
                     "Send Messages there")
        r.raise_for_status()
    print(f"POSTED {len(chunks)} message(s) to channel {channel_id}")


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_channel_arg(sp):
        sp.add_argument("--channel",
                        help="'po' (default), 'mars', 'issues', or a raw "
                             f"channel id (po={DEFAULT_PO_CHANNEL_ID}, "
                             f"mars={DEFAULT_MARS_CHANNEL_ID}, "
                             f"issues={DEFAULT_ISSUES_CHANNEL_ID}; override "
                             "via env PO_CHANNEL_ID / MARS_CHANNEL_ID / "
                             "ISSUES_CHANNEL_ID)")

    f = sub.add_parser("fetch", help="read the latest channel messages")
    add_channel_arg(f)
    f.add_argument("--limit", type=int, default=50, help="how many (max 100)")
    f.add_argument("--after-msg", help="only messages after this message id")
    f.add_argument("--json", action="store_true", help="machine-readable output")
    f.set_defaults(func=cmd_fetch)

    c = sub.add_parser("file-cr", help="create one CR on the Change Requests board")
    add_channel_arg(c)
    c.add_argument("--title", required=True, help="CR title (Arabic, describes the idea)")
    c.add_argument("--brief", required=True, help="2-4 line description of the idea")
    c.add_argument("--source-msg", help="Discord message id the idea came from "
                                        "(enables dedup + jump link)")
    c.add_argument("--guild", help="guild id for the jump link (default env "
                                   "DISCORD_GUILD_ID)",
                   default=os.environ.get("DISCORD_GUILD_ID"))
    c.add_argument("--attach-url", action="append", default=[],
                   help="image/video URLs from the conversation to attach (repeatable)")
    c.add_argument("--no-media", action="store_true", help="skip auto-attaching media")
    c.add_argument("--dry-run", action="store_true")
    c.add_argument("--field", action="append", default=[],
                   help="set any field: Ref=Value (repeatable), e.g. Custom.WorkType=Mobile")
    c.set_defaults(func=cmd_file_cr)

    o = sub.add_parser("post", help="post a message into a channel")
    add_channel_arg(o)
    o.add_argument("--text", help="message text (or pipe on stdin)")
    o.set_defaults(func=cmd_post)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
