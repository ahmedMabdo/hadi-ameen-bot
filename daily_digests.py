#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""daily_digests.py — التقارير والملخصات اليومية من الكود مباشرة (نقطة 5).

بيستبدل روتينز كلود الحرة بمسار مقيد وقابل للقياس:
  fetch (أدوات REST الموجودة) → نداء موديل واحد ببرومبت ثابت hardened → post
مع حراس حتمية في الكود نفسه:
  - حد أدنى لعدد رسايل البشر قبل التلخيص (يوم فاضي = مفيش سبام).
  - تقرير PostHog عمره ما يتبعت من غير فحص LIVE/STALE/DOWN الأول —
    لو DOWN بيتلغى التقرير وبيوصل تنبيه لآسر بدل أرقام مضللة. والتنبيه نفسه
    له مسارين (DM ← قناة احتياطية) ونتيجته بتتسجّل في alert_via؛ لو محدش
    اتبلّغ بيبقى ok=false وexit 1 — حارس بيمنع بصمت أخطر من مفيش حارس.
  - الموديل ممنوع يألّف: أي رقم/اسم لازم يكون من الرسايل المدخلة، وSKIP_EMPTY
    لو مفيش محتوى شغل حقيقي.
  - retry واحدة على فشل الموديل، وexit code غير صفري على أي فشل (يبان في systemd).
  - سطر JSONL لكل تشغيلة في logs/digests.jsonl (غذاء الـ evals — نقطة 7).

الاستخدام (systemd timers — الملفات في setup/systemd/):
  python3 daily_digests.py marsteam [--dry-run]     # 19:00 القاهرة
  python3 daily_digests.py podaily  [--dry-run]     # 19:10 القاهرة
  python3 daily_digests.py followup [--dry-run]     # 19:20 القاهرة
  python3 daily_digests.py posthog  [--dry-run]     # 09:00 القاهرة

(تقرير الأوتوميشن 10:00 خارج النطاق ده — discord_mars_results.py قايم بالفعل.)
"""
import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except Exception:
    pass

CLAUDE_BIN = os.getenv("CLAUDE_BIN", "/home/ubuntu/.local/bin/claude").strip()
DIGEST_MODEL = os.getenv("HADI_DIGEST_MODEL", "sonnet").strip() or "sonnet"
MIN_HUMAN_MSGS = int(os.getenv("HADI_DIGEST_MIN_MSGS", "5") or "5")
MAX_CHARS = int(os.getenv("HADI_DIGEST_MAX_CHARS", "1800") or "1800")
LOG_FILE = BASE_DIR / "logs" / "digests.jsonl"
ASSER_USER_ID = os.getenv("ASSER_USER_ID", "1378684355148386355").strip()

# Discord بيرفض User-Agent الافتراضي بتاع urllib على مستوى Cloudflare (كود 1010)
# قبل ما الطلب يوصله أصلًا. باقي ملفات المشروع بتستخدم requests فمابتتأثرش.
DISCORD_UA = "DiscordBot (hadi-ameen-bot, 1.0)"

# قناة احتياطية للتنبيه لو الـ DM فشل. تنبيه حارس مايوصلش = حارس أعمى.
ALERT_CHANNEL_ID = (os.getenv("HADI_ALERT_CHANNEL_ID", "").strip()
                    or os.getenv("MARS_CHANNEL_ID", "").strip())


def alert_recipients():
    """آسر + نفس مستقبلي التقرير (MAHMOUD_DISCORD_USER_ID).

    اللي مستني التقرير لازم يعرف ليه ماجاش — قبل كده كان بيوصله سكوت.
    """
    raw = f"{ASSER_USER_ID},{os.getenv('MAHMOUD_DISCORD_USER_ID', '')}"
    out, seen = [], set()
    for part in raw.replace(" ", ",").replace(";", ",").split(","):
        part = part.strip()
        if part and part not in seen:
            seen.add(part)
            out.append(part)
    return out


def _log(row):
    try:
        LOG_FILE.parent.mkdir(exist_ok=True)
        row.setdefault("ts", time.strftime("%Y-%m-%dT%H:%M:%S%z"))
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _run(cmd, timeout=120, check=True):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=BASE_DIR)
    if check and r.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd[:3])}... rc={r.returncode}: "
                           f"{(r.stderr or r.stdout)[-400:]}")
    return r.stdout


def call_model(prompt, timeout=240):
    """نداء موديل واحد نظيف (cwd=/tmp — من غير شخصية المشروع) مع retry واحدة."""
    last = None
    for attempt in (1, 2):
        try:
            r = subprocess.run(
                [CLAUDE_BIN, "-p", prompt, "--model", DIGEST_MODEL],
                capture_output=True, text=True, timeout=timeout, cwd="/tmp",
            )
            out = (r.stdout or "").strip()
            if r.returncode == 0 and out:
                return out
            last = f"rc={r.returncode}: {(r.stderr or out)[-300:]}"
        except subprocess.TimeoutExpired:
            last = f"timeout {timeout}s"
        if attempt == 1:
            time.sleep(10)
    raise RuntimeError(f"model failed twice: {last}")


def _discord_post(path, payload, token):
    req = urllib.request.Request(
        f"https://discord.com/api/v10{path}",
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bot {token}",
                 "Content-Type": "application/json",
                 # من غير السطر ده Cloudflare بيرد 1010 قبل ما Discord يشوف الطلب
                 "User-Agent": DISCORD_UA},
        method="POST")
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode())


def _reason(error):
    """سبب مقروء — بيقرا جسم رد Discord بدل ما يرميه زي الأول."""
    if isinstance(error, urllib.error.HTTPError):
        try:
            body = error.read().decode("utf-8", "replace").strip()[:200]
        except Exception:
            body = ""
        return f"HTTP {error.code} {body}".strip()
    return f"{type(error).__name__}: {error}"[:200]


def alert_owners(text):
    """تنبيه لكل المعنيين: DM لكل واحد، وقناة احتياطية لو كلهم فشلوا.

    بيرجع (via, error) — via = "dm" لو حد واحد على الأقل استلم، أو "channel"،
    أو None لو محدش اتبلّغ. لازم المُنادي يسجّل النتيجة: تنبيه فاشل
    مايتخبّاش تحت ok=true تاني.
    """
    token = os.getenv("DISCORD_BOT_TOKEN", "").strip()
    if not token:
        return None, "DISCORD_BOT_TOKEN مش موجود"

    people = alert_recipients()
    if not people:
        dm_error = "مفيش مستقبِلين (ASSER_USER_ID / MAHMOUD_DISCORD_USER_ID)"
    else:
        sent, failures = 0, []
        for user_id in people:
            try:
                ch = _discord_post("/users/@me/channels",
                                   {"recipient_id": user_id}, token)
                _discord_post(f"/channels/{ch['id']}/messages",
                              {"content": text[:1900]}, token)
                sent += 1
            except Exception as error:
                failures.append(f"{user_id}[{_reason(error)}]")
                print(f"DM FAIL {user_id}: {_reason(error)}", file=sys.stderr)
        if sent:
            # وصل لواحد على الأقل — بس الفشل الجزئي بيتسجّل برضه
            return "dm", ("لم يصل لـ " + ", ".join(failures)) if failures else None
        dm_error = "; ".join(failures)

    if not ALERT_CHANNEL_ID:
        return None, f"dm[{dm_error}] + مفيش قناة احتياطية (HADI_ALERT_CHANNEL_ID)"

    try:
        mention = " ".join(f"<@{uid}>" for uid in alert_recipients())
        body = (mention + "\n" + text) if mention else text
        _discord_post(f"/channels/{ALERT_CHANNEL_ID}/messages",
                      {"content": body[:1900]}, token)
        print(f"ALERT عبر القناة الاحتياطية (الـ DM فشل: {dm_error})", file=sys.stderr)
        return "channel", f"dm[{dm_error}]"
    except Exception as error:
        both = f"dm[{dm_error}] channel[{_reason(error)}]"
        print(f"ALERT FAIL: {both}", file=sys.stderr)
        return None, both


# ----------------------------- الملخصات -----------------------------
DIGESTS = {
    "marsteam": {
        "fetch": ["discord_marsteam.py", "fetch"],
        "post": ["discord_marsteam.py", "post"],
        "label": "قناة مارس (mars-team)",
        "focus": ("قرارات التيم، تحديثات السبرنت والريليز، المشاكل التقنية المفتوحة، "
                  "والـ action items (مين → إيه)"),
    },
    "podaily": {
        "fetch": ["discord_podaily.py", "fetch"],
        "post": ["discord_podaily.py", "post"],
        "label": "قناة الـ PO (8orders-po)",
        "focus": ("الأفكار والمطالب الجديدة، القرارات البيزنس، والنقاط اللي محتاجة "
                  "متابعة من الـ Product"),
    },
    "followup": {
        "fetch": ["discord_followup.py", "fetch"],
        "post": ["discord_followup.py", "post"],
        "label": "قناة السابورت (8orders-issues)",
        "focus": ("مشاكل العملا اللي اتفتحت، اللي اتحل واللي لسه، والأهم: "
                  "الأسئلة والبلاغات اللي **من غير رد لحد دلوقتي** (متابعة)"),
    },
}

def _persona_core() -> str:
    """نواة الشخصية المشتركة (نقطة 8) — نفس صوت هادي في الملخصات زي القنوات."""
    try:
        return (BASE_DIR / "PERSONA_CORE.md").read_text(encoding="utf-8").strip()
    except OSError:
        return "انت هادي أمين، عضو تيم مارس في فريق هدف — مصري، مختصر، evidence-based."


PROMPT_TEMPLATE = """{persona}

مطلوب منك: الملخص اليومي لـ{label}.

قواعد صارمة (إلزامية):
1. لخّص من الرسايل المرفقة تحت **فقط**. ممنوع منعًا باتًا ذكر أي رقم أو اسم أو حدث مش موجود فيها نصًا.
2. ركّز على: {focus}.
3. تجاهل رسايل البوتات والتقارير الأوتوماتيكية، والهزار والسلامات اللي مالهاش علاقة بالشغل.
4. الفورمات: سطر عنوان **الملخص اليومي — {label}** وبعده 3 لـ 8 نقاط قصيرة بالعربي المصري، الأسماء زي ما وردت. مفيش مقدمات ولا خواتيم ولا نصايح عامة.
5. أقصى طول {max_chars} حرف.
6. لو مفيش محتوى شغل حقيقي في الرسايل (يوم هادي أو هزار بس): رد بكلمة SKIP_EMPTY بس من غير أي حاجة تانية.

الرسايل (JSON، الأقدم فالأحدث):
{messages}"""


def _human_messages(raw_json):
    try:
        msgs = json.loads(raw_json)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"fetch output is not JSON: {error}")
    if isinstance(msgs, dict):
        msgs = msgs.get("messages") or []
    out = []
    for m in msgs:
        if m.get("is_bot") or m.get("bot"):
            continue
        if not (m.get("content") or "").strip():
            continue
        out.append({"author": m.get("author", "?"), "content": m.get("content", "")[:600],
                    "ts": m.get("timestamp", "")[:16]})
    return out


def run_digest(name, dry_run=False):
    cfg = DIGESTS[name]
    t0 = time.time()
    row = {"digest": name, "ok": False}
    try:
        raw = _run([sys.executable, str(BASE_DIR / cfg["fetch"][0])] + cfg["fetch"][1:],
                   timeout=120)
        humans = _human_messages(raw)
        row["human_msgs"] = len(humans)
        if len(humans) < MIN_HUMAN_MSGS:
            row.update(ok=True, decision="skip_quiet")
            print(f"{name}: {len(humans)} رسايل بشر بس (<{MIN_HUMAN_MSGS}) — مفيش ملخص النهارده")
            return 0
        prompt = PROMPT_TEMPLATE.format(
            persona=_persona_core(),
            label=cfg["label"], focus=cfg["focus"], max_chars=MAX_CHARS,
            messages=json.dumps(humans, ensure_ascii=False))
        summary = call_model(prompt)
        summary = summary.strip().strip("`").strip()
        if "SKIP_EMPTY" in summary[:40]:
            row.update(ok=True, decision="skip_empty")
            print(f"{name}: الموديل قرر مفيش محتوى يستاهل — مفيش ملخص")
            return 0
        if len(summary) > MAX_CHARS + 200:  # حارس طول حتمي فوق تعليمة الموديل
            summary = summary[:MAX_CHARS + 200].rsplit("\n", 1)[0]
        row["chars_out"] = len(summary)
        post_cmd = [sys.executable, str(BASE_DIR / cfg["post"][0])] + cfg["post"][1:]
        if dry_run:
            post_cmd.append("--dry-run")
        _run(post_cmd + [summary], timeout=60)
        row.update(ok=True, decision="posted")
        print(f"{name}: الملخص اتبعت ({len(summary)} حرف من {len(humans)} رسالة)")
        return 0
    except Exception as error:
        row.update(error=f"{type(error).__name__}: {error}"[:300])
        print(f"{name} FAILED: {row['error']}", file=sys.stderr)
        return 1
    finally:
        row["latency_ms"] = int((time.time() - t0) * 1000)
        _log(row)


# ----------------------------- تقرير PostHog -----------------------------
def run_posthog(dry_run=False):
    """التقرير الصباحي — بالحارس الإلزامي: مفيش تقرير بأرقام والتتبع DOWN."""
    t0 = time.time()
    row = {"digest": "posthog", "ok": False}
    try:
        health = _run([sys.executable, str(BASE_DIR / "posthog_cli.py"), "health"],
                      timeout=90, check=False)
        row["health"] = health.strip().splitlines()[0][:120] if health.strip() else "?"
        if "DOWN" in health.upper():
            row.update(ok=True, decision="blocked_down")
            detail = row["health"]
            if "—" in detail:            # نشيل "🔴 حالة البيانات: DOWN —" المكررة
                detail = detail.split("—", 1)[1].strip()
            msg = ("🔴 تقرير PostHog اتوقف — التتبع واقف\n"
                   f"{detail}\n"
                   "هيرجع لوحده أول ما التتبع يرجع.")
            print(msg)
            if not dry_run:
                via, alert_error = alert_owners(msg)
                row["alert_via"] = via
                if alert_error:
                    row["alert_error"] = alert_error
                if not via:
                    # الحارس منع التقرير الغلط بس محدش اتبلّغ — ده مش نجاح.
                    # exit code 1 بيخلي systemd يسجّلها failed = طبقة تنبيه تالتة.
                    row["ok"] = False
                    print("ALERT UNDELIVERED: التقرير اتمنع ومحدش اتبلّغ",
                          file=sys.stderr)
                    return 1
            return 0
        cmd = [sys.executable, str(BASE_DIR / "intel" / "8orders_report_generator.py"),
               "--push-ado"]
        if dry_run:
            cmd += ["--ado-dry-run", "--no-discord"]
        out = _run(cmd, timeout=600)
        row.update(ok=True, decision="posted")
        print(f"posthog: التقرير اتولد واتسلم — آخر سطر: {out.strip().splitlines()[-1][:120] if out.strip() else 'ok'}")
        return 0
    except Exception as error:
        row.update(error=f"{type(error).__name__}: {error}"[:300])
        print(f"posthog FAILED: {row['error']}", file=sys.stderr)
        if not dry_run:
            via, alert_error = alert_owners(
                f"🔴 تقرير PostHog فشل\n{row['error']}")
            row["alert_via"] = via
            if alert_error:
                row["alert_error"] = alert_error
        return 1
    finally:
        row["latency_ms"] = int((time.time() - t0) * 1000)
        _log(row)


def main():
    p = argparse.ArgumentParser(description="Hadi daily digests (code-driven).")
    p.add_argument("digest", choices=[*DIGESTS, "posthog"])
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()
    if a.digest == "posthog":
        sys.exit(run_posthog(a.dry_run))
    sys.exit(run_digest(a.digest, a.dry_run))


if __name__ == "__main__":
    main()
