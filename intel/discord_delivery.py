#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Send the day's PostHog PDF report as a Discord DM to one or more recipients.

Runs as the last step of the daily routine (see ROUTINE_INSTRUCTIONS.md step 4)
so the report reaches them even if no one is watching the routine's chat
transcript that day. Uses the Discord REST API directly (bot token), not the
gateway — opening a DM channel + posting a message with attachments is a
one-shot REST call, no persistent connection needed.

Env (read from a `.env` file alongside this script if present, else the
process environment):
  DISCORD_BOT_TOKEN     bot token (the same bot used for interactive access)
  REPORT_DM_USER_IDS    recipient Discord user id(s) — overrides the default
                        list. Accepts ONE id, or several separated by commas
                        and/or whitespace, e.g. "111,222". Each id gets its
                        own independent DM.
                        Backward compat: MAHMOUD_DISCORD_USER_ID still works
                        when REPORT_DM_USER_IDS is not set.
  DISCORD_GUILD_ID      optional fallback — if neither env var is set, resolve
                        a single recipient by searching the guild for
                        RECIPIENT_NAME (legacy behaviour).

Default recipients (used when no env var is set):
  باشمهندس محمود عبده (1016738618267664485) + آسر جميل (1378684355148386355)

Delivery failure here must never break the routine: every public function
catches its own errors, logs them, and returns False rather than raising.
A failure for one recipient never blocks delivery to the others.
"""
import os, re, sys, requests

# .env بيتقرا بنفس دلالات `source` — شوف env_loader.py.
# load_for بيدوّر في intel/.env وبعدين في .env بتاع الريبو. النسخة القديمة كانت
# بتدوّر على intel/.env بس، وده ملف مش موجود عادةً — يعني الوحدة دي كانت
# بتعتمد على بيئة العملية وحدها وبتفشل لو اتنادت لوحدها من الشِل.
try:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import env_loader
    env_loader.load_for(__file__)
except Exception:  # قراءة الإعدادات مالهاش لازمة توقف الوحدة
    pass

API_BASE = "https://discord.com/api/v10"
RECIPIENT_NAME = "Mahmoud Abdou"

# المستقبلون الافتراضيون لتقرير PostHog اليومي — بيتجاوَز بـ REPORT_DM_USER_IDS.
# آسر جميل + باشمهندس محمود عبده (من posthog_guard.ADMIN_IDS).
DEFAULT_REPORT_RECIPIENTS = [
    "1016738618267664485",  # باشمهندس محمود عبده
    "1378684355148386355",  # آسر جميل
]


def _headers(token):
    return {"Authorization": f"Bot {token}"}


def parse_user_ids(raw):
    """Split a comma/whitespace separated id list into a deduped, ordered list."""
    if not raw:
        return []
    ids = re.split(r"[,\s]+", raw.strip())
    seen, out = set(), []
    for uid in ids:
        if uid and uid not in seen:
            seen.add(uid)
            out.append(uid)
    return out


def resolve_user_id_by_name(token, guild_id, name=RECIPIENT_NAME):
    """Best-effort lookup of a member's user id by display/username via the
    guild member search endpoint. Requires the bot to share a guild with them
    and have the Server Members Intent enabled."""
    r = requests.get(f"{API_BASE}/guilds/{guild_id}/members/search",
                      headers=_headers(token), params={"query": name, "limit": 5},
                      timeout=15)
    r.raise_for_status()
    members = r.json()
    return members[0]["user"]["id"] if members else None


def _dm_channel_id(token, user_id):
    r = requests.post(f"{API_BASE}/users/@me/channels",
                       headers={**_headers(token), "Content-Type": "application/json"},
                       json={"recipient_id": user_id}, timeout=15)
    r.raise_for_status()
    return r.json()["id"]


def _send_to_one(token, user_id, pdf_paths, message):
    """Open a DM with one user and post the PDF(s). Raises on failure — caller
    is responsible for catching per-recipient so one bad id doesn't block the rest."""
    channel_id = _dm_channel_id(token, user_id)
    files, handles = {}, []
    for i, path in enumerate(pdf_paths):
        fh = open(path, "rb")
        handles.append(fh)
        files[f"files[{i}]"] = (os.path.basename(path), fh, "application/pdf")
    data = {"content": message or "تقرير PostHog اليومي 📊"}
    try:
        r = requests.post(f"{API_BASE}/channels/{channel_id}/messages",
                           headers=_headers(token), data=data, files=files, timeout=60)
    finally:
        for fh in handles:
            fh.close()
    r.raise_for_status()


def send_report(pdf_paths, message=None, token=None, user_ids=None, guild_id=None):
    """Send one or more PDFs as separate DMs to one or more recipients.
    `user_ids` may be a list, or a single comma/whitespace-separated string
    (defaults to env MAHMOUD_DISCORD_USER_ID). Each recipient is attempted
    independently — one failure is logged and does not stop the others.
    Returns True if at least one recipient received it, False otherwise —
    never raises, so the daily routine can call this after writing the PDFs
    without risking the run."""
    token = token or os.environ.get("DISCORD_BOT_TOKEN")
    guild_id = guild_id or os.environ.get("DISCORD_GUILD_ID")
    pdf_paths = [p for p in pdf_paths if p and os.path.isfile(p)]

    if user_ids is None:
        # الأولوية: REPORT_DM_USER_IDS → MAHMOUD_DISCORD_USER_ID (backward compat) → defaults
        raw = (os.environ.get("REPORT_DM_USER_IDS", "").strip()
               or os.environ.get("MAHMOUD_DISCORD_USER_ID", "").strip())
        ids = parse_user_ids(raw) if raw else list(DEFAULT_REPORT_RECIPIENTS)
    elif isinstance(user_ids, str):
        ids = parse_user_ids(user_ids)
    else:
        ids = list(user_ids)

    if not token:
        print("DISCORD: skipped — DISCORD_BOT_TOKEN not set")
        return False
    if not pdf_paths:
        print("DISCORD: skipped — no PDF files to send")
        return False

    if not ids:
        if not guild_id:
            print("DISCORD: skipped — set REPORT_DM_USER_IDS "
                  "(one id, or several comma/space-separated) "
                  "or DISCORD_GUILD_ID to resolve one by name")
            return False
        try:
            resolved = resolve_user_id_by_name(token, guild_id)
        except Exception as e:
            print(f"DISCORD: failed to resolve user id by name: {e}")
            return False
        if not resolved:
            print(f"DISCORD: skipped — could not find '{RECIPIENT_NAME}' in guild {guild_id}")
            return False
        ids = [resolved]

    sent = 0
    for user_id in ids:
        try:
            _send_to_one(token, user_id, pdf_paths, message)
            print(f"DISCORD: sent {len(pdf_paths)} file(s) to user {user_id}")
            sent += 1
        except Exception as e:
            print(f"DISCORD: send to user {user_id} failed: {e}")

    return sent > 0


if __name__ == "__main__":
    # manual test: python3 discord_delivery.py path/to/report.pdf [more.pdf ...]
    paths = sys.argv[1:]
    if not paths:
        sys.exit("Usage: python3 discord_delivery.py <pdf> [pdf2 ...]")
    ok = send_report(paths)
    sys.exit(0 if ok else 1)
