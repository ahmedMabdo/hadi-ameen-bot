#!/usr/bin/env python3
"""Hadi Ameen - Mars automation TEST RESULTS report (Azure DevOps -> Discord).

Fetches the latest Develop (def 604) and Master (def 603) TalabatkAPI.Test
pipeline runs from Azure DevOps and posts a summary (embed + emoji bar + PNG
card) to the mars channel. When there are failures it also lists the failed
test cases (names + error) - a short preview inline and the full list in an
attached text file.

Commands:
    python3 discord_mars_results.py run             -> full report to mars channel
    python3 discord_mars_results.py run --dry-run   -> print only, do NOT post
    python3 discord_mars_results.py failed [develop|master|all]
                                                    -> failed-tests list to channel
    python3 discord_mars_results.py fetch           -> JSON summary to stdout

Dry-run: env MARSRESULTS_DRY_RUN=true/1/yes or the --dry-run flag.
Errors print as "MARSRESULTS: ..." to stderr, non-zero exit, no crash.

Env (read from .env next to this script if present, else process env):
    AZURE_DEVOPS_ORG_URL       default https://hadafsolutions.visualstudio.com
    AZURE_DEVOPS_PAT           PAT: Build (Read) + Test Management (Read)
    AZURE_DEVOPS_DEFAULT_PROJECT  default 0_Projects_Team
    DISCORD_BOT_TOKEN          Hadi bot token (routines_common.get_token)
    MARS_CHANNEL_ID            default 1136668686044909761
    MARS_DEVELOP_DEF_ID        default 604
    MARS_MASTER_DEF_ID         default 603
"""

import base64
import json
import os
import sys
from datetime import datetime
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
    CAIRO_TZ = ZoneInfo("Africa/Cairo")
except Exception:  # pragma: no cover
    from datetime import timezone, timedelta
    CAIRO_TZ = timezone(timedelta(hours=3))

import requests

import routines_common
from routines_common import log, get_token, is_truthy, load_env_file

routines_common.set_prefix("MARSRESULTS")

BASE = Path(__file__).resolve().parent
DISCORD_API = "https://discord.com/api/v10"

ADO_ORG_URL = os.environ.get("AZURE_DEVOPS_ORG_URL", "https://hadafsolutions.visualstudio.com").rstrip("/")
ADO_PROJECT = os.environ.get("AZURE_DEVOPS_DEFAULT_PROJECT", "0_Projects_Team")
ADO_API_VERSION = "7.1"

DEVELOP_DEF_ID = int(os.environ.get("MARS_DEVELOP_DEF_ID", "604"))
MASTER_DEF_ID = int(os.environ.get("MARS_MASTER_DEF_ID", "603"))

MARS_CHANNEL_ID = os.environ.get("MARS_CHANNEL_ID", "1136668686044909761")

# مسؤول كل بايبلاين — بيتعمله tag في التقرير اليومي طول ما فيه مشاكل (طلب غادة).
# develop: عصام غادر (layoff 30 يوليو 2026) — فاضي لحد ما يتعيّن مسؤول جديد بـ
#          MARS_DEVELOP_OWNER_ID. master: مصطفى سلامة.
# الكود بيتخطّى المسؤول الفاضي (tag = "" ومفيش mention) فمفيش tag مكسور.
PIPELINE_OWNERS = {
    "develop": os.environ.get("MARS_DEVELOP_OWNER_ID", ""),                      # فاضي بعد رحيل عصام — عيّن الجديد
    "master": os.environ.get("MARS_MASTER_OWNER_ID", "1017367801033400380"),    # مصطفى سلامة
}

BUILD_RESULT = {"succeeded": "SUCCEEDED", "partiallysucceeded": "PARTIAL",
                "failed": "FAILED", "canceled": "CANCELED"}

COLOR_GREEN = 0x57F287
COLOR_RED = 0xED4245

INLINE_PREVIEW = 5      # failed test names shown inline in the daily report
INLINE_FAILED_CMD = 12  # failed test names shown inline for the `failed` command

PIPELINES = [
    ("Develop — TalabatkAPI.Test", DEVELOP_DEF_ID, "develop"),
    ("Master — TalabatkAPI.Test", MASTER_DEF_ID, "master"),
]


# --------------------------------------------------------------------------- #
# Azure DevOps
# --------------------------------------------------------------------------- #

def _ado_auth() -> dict:
    pat = os.environ.get("AZURE_DEVOPS_PAT")
    if not pat:
        log("AZURE_DEVOPS_PAT مش موجود في الـ environment ولا في .env")
        sys.exit(1)
    token = base64.b64encode(f":{pat}".encode()).decode()
    return {"Authorization": f"Basic {token}", "Accept": "application/json"}


def _ado_get(path: str, params: dict):
    url = f"{ADO_ORG_URL}/{ADO_PROJECT}/_apis/{path}"
    resp = requests.get(url, headers=_ado_auth(), params=params, timeout=45)
    if resp.status_code != 200:
        log(f"ADO GET {path} فشل — status {resp.status_code}: {resp.text[:200]}")
        return None
    return resp.json()


def get_latest_build(def_id: int):
    data = _ado_get("build/builds", {
        "definitions": def_id, "statusFilter": "completed",
        "queryOrder": "finishTimeDescending", "$top": 1, "api-version": ADO_API_VERSION,
    })
    if not data:
        return None
    values = data.get("value") or []
    return values[0] if values else None


def _build_runs(build_id: int):
    data = _ado_get("test/runs", {
        "buildUri": f"vstfs:///Build/Build/{build_id}", "api-version": ADO_API_VERSION,
    })
    return (data.get("value") or []) if data else []


def get_test_summary(build_id: int):
    """Aggregated counts via the build's test runs. None on failure.

    Each run reports totalTests / passedTests / notApplicableTests /
    unanalyzedTests, and totalTests == passed + notApplicable + unanalyzed
    (verified live). Failed maps to unanalyzedTests, not-executed to
    notApplicableTests.
    """
    runs = _build_runs(build_id)
    if runs is None:
        return None
    passed = failed = not_exec = total = 0
    for run in runs:
        total += run.get("totalTests", 0)
        passed += run.get("passedTests", 0)
        not_exec += run.get("notApplicableTests", 0)
        failed += run.get("unanalyzedTests", 0)
    return {"passed": passed, "failed": failed, "not_executed": not_exec, "total": total}


def get_failed_tests(build_id: int):
    """List of {title, error} for every failed test result in the build."""
    out = []
    for run in _build_runs(build_id):
        if run.get("unanalyzedTests", 0) == 0:
            continue
        rid = run["id"]
        skip = 0
        while True:
            data = _ado_get(f"test/Runs/{rid}/results", {
                "outcomes": "Failed", "$top": 200, "$skip": skip,
                "api-version": ADO_API_VERSION,
            })
            batch = (data.get("value") or []) if data else []
            for t in batch:
                title = t.get("testCaseTitle") or t.get("automatedTestName") or "(بدون اسم)"
                error = " ".join((t.get("errorMessage") or "").split())
                out.append({"title": title, "error": error})
            if len(batch) < 200:
                break
            skip += 200
    return out


def build_web_url(build_id: int) -> str:
    return (f"{ADO_ORG_URL}/{ADO_PROJECT}/_build/results"
            f"?buildId={build_id}&view=ms.vss-test-web.build-test-results-tab")


def collect_pipeline(name: str, def_id: int, with_failures: bool = True) -> dict:
    try:
        build = get_latest_build(def_id)
        if not build:
            return {"name": name, "error": "مفيش رن مكتمل"}
        summary = get_test_summary(build["id"])
        if summary is None:
            return {"name": name, "error": "تعذّر جلب نتائج الاختبارات"}
        p = {
            "name": name,
            "build_id": build["id"],
            "build_number": build.get("buildNumber", str(build["id"])),
            "result_label": BUILD_RESULT.get(str(build.get("result", "")).lower(), "UNKNOWN"),
            "url": build_web_url(build["id"]),
            **summary,
        }
        if with_failures and p.get("failed", 0) > 0:
            p["failed_tests"] = get_failed_tests(build["id"])
        return p
    except Exception as exc:  # noqa: BLE001
        return {"name": name, "error": f"{type(exc).__name__}: {exc}"}


# --------------------------------------------------------------------------- #
# Formatting helpers
# --------------------------------------------------------------------------- #

def pass_rate(p: dict) -> float:
    executed = p["total"] - p.get("not_executed", 0)
    return (p["passed"] / executed * 100) if executed > 0 else 0.0


def emoji_bar(p: dict, width: int = 20) -> str:
    total = max(p["total"], 1)
    g = min(round(p["passed"] / total * width), width)
    r = min(round(p["failed"] / total * width), width - g)
    w = width - g - r
    return "\U0001F7E9" * g + "\U0001F7E5" * r + "⬜" * w


def now_label() -> str:
    return datetime.now(CAIRO_TZ).strftime("%A, %d %b %Y — %H:%M") + " القاهرة"


def _clip(text: str, n: int) -> str:
    text = text or ""
    return text if len(text) <= n else text[: n - 1] + "…"


# --------------------------------------------------------------------------- #
# Report embed (run)
# --------------------------------------------------------------------------- #

def build_embed(pipelines: list, date_label: str, has_image: bool) -> dict:
    def is_bad(p):
        return bool(p.get("error")) or p.get("failed", 0) > 0 or (not p.get("error") and p.get("total", 0) == 0)

    any_fail = any(is_bad(p) for p in pipelines)
    fields = []
    for p in pipelines:
        if p.get("error"):
            fields.append({"name": p["name"], "value": f":warning: {p['error']}", "inline": False})
            continue
        if p.get("total", 0) == 0:
            fields.append({"name": p["name"], "value": (
                f"⚠️ **{p['result_label']}** — مفيش نتائج "
                f"اختبارات للرن ده "
                f"(الرن فشل قبل تنفيذ الاختبارات غالبًا)\n"
                f"[Build {p['build_number']} — details]({p['url']})"), "inline": False})
            continue
        dot = "\U0001F7E2" if (p["failed"] == 0 and p["result_label"] == "SUCCEEDED") else "\U0001F534"
        value = (
            f"{emoji_bar(p)}\n"
            f"{dot} **{p['result_label']}** · نسبة النجاح **{pass_rate(p):.1f}%**\n"
            f"✅ نجح: **{p['passed']}**  ❌ فشل: **{p['failed']}**  "
            f"⚪ مش متنفذ: **{p.get('not_executed', 0)}**  (الكلي {p['total']})\n"
        )
        fails = p.get("failed_tests") or []
        if fails:
            preview = fails[:INLINE_PREVIEW]
            lines = "\n".join(f"• {_clip(f['title'], 70)}" for f in preview)
            value += f"أمثلة من الفاشل:\n{lines}\n"
            if len(fails) > INLINE_PREVIEW:
                value += (f"… و **{len(fails) - INLINE_PREVIEW}** كمان في الملف المرفق\n")
        value += f"[Build {p['build_number']} — test results]({p['url']})"
        fields.append({"name": p["name"], "value": _clip(value, 1024), "inline": False})

    title = ("\U0001F534 Mars Automation — نتائج الأوتوميشن اليومية"
             if any_fail else
             "\U0001F7E2 Mars Automation — نتائج الأوتوميشن اليومية")
    embed = {
        "title": title,
        "description": date_label,
        "color": COLOR_RED if any_fail else COLOR_GREEN,
        "fields": fields,
        "footer": {"text": "Source: Azure DevOps · TalabatkAPI.Test"},
        "timestamp": datetime.now(CAIRO_TZ).isoformat(),
    }
    if has_image:
        embed["image"] = {"url": "attachment://mars_results.png"}
    return embed


# --------------------------------------------------------------------------- #
# Failed-tests embed (failed command) + text file
# --------------------------------------------------------------------------- #

def build_failed_embed(pipelines: list, date_label: str) -> dict:
    fields = []
    total_failed = 0
    for p in pipelines:
        if p.get("error"):
            fields.append({"name": p["name"], "value": f":warning: {p['error']}", "inline": False})
            continue
        fails = p.get("failed_tests") or []
        total_failed += len(fails)
        if not fails:
            note = ("✅ مفيش فشل" if p.get("total", 0) > 0
                    else "⚠️ مفيش نتائج للرن ده")
            fields.append({"name": p["name"], "value": f"{note}\n[Build {p['build_number']}]({p['url']})", "inline": False})
            continue
        lines = "\n".join(f"{i}. {_clip(f['title'], 75)}" for i, f in enumerate(fails[:INLINE_FAILED_CMD], 1))
        val = f"عدد الفاشل: **{len(fails)}**\n{lines}\n"
        if len(fails) > INLINE_FAILED_CMD:
            val += f"… و **{len(fails) - INLINE_FAILED_CMD}** كمان في الملف المرفق\n"
        val += f"[Build {p['build_number']} — test results]({p['url']})"
        fields.append({"name": p["name"], "value": _clip(val, 1024), "inline": False})

    return {
        "title": "\U0001F534 Mars Automation — الاختبارات الفاشلة",
        "description": date_label,
        "color": COLOR_RED if total_failed else COLOR_GREEN,
        "fields": fields,
        "footer": {"text": "Source: Azure DevOps · TalabatkAPI.Test"},
        "timestamp": datetime.now(CAIRO_TZ).isoformat(),
    }


def build_failed_txt(pipelines: list, date_label: str):
    """Return path to a written failed-tests txt file, or None if no failures."""
    chunks = [f"Mars Automation - Failed Tests - {date_label}", ""]
    any_fail = False
    for p in pipelines:
        if p.get("error"):
            continue
        fails = p.get("failed_tests") or []
        if not fails:
            continue
        any_fail = True
        chunks.append(f"== {p['name']} ({len(fails)} failed) - Build {p['build_number']} ==")
        for i, f in enumerate(fails, 1):
            chunks.append(f"{i}. {f['title']}")
            if f.get("error"):
                chunks.append(f"   error: {f['error']}")
        chunks.append("")
    if not any_fail:
        return None
    path = str(BASE / "mars_failed_tests.txt")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(chunks))
    return path


# --------------------------------------------------------------------------- #
# Rendering (PNG card, optional - Pillow only)
# --------------------------------------------------------------------------- #

def _load_font(size: int, bold: bool = False):
    from PIL import ImageFont
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for path in candidates:
        if os.path.isfile(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()


def render_card(pipelines: list, out_path: str, date_label: str):
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        log("Pillow مش متثبت — هيتبعت embed من غير صورة")
        return None

    W, row_h, top = 1000, 150, 130
    H = top + row_h * len(pipelines) + 50
    BG, GREEN, RED, GREY, TRACK = (35, 39, 42), (87, 242, 135), (237, 66, 69), (148, 155, 164), (30, 31, 34)
    WHITE, SUB = (255, 255, 255), (181, 186, 193)

    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    f_title, f_date = _load_font(34, True), _load_font(18)
    f_name, f_stat, f_badge = _load_font(24, True), _load_font(19), _load_font(21, True)

    d.text((40, 34), "Mars Automation — Daily Results", font=f_title, fill=WHITE)
    d.text((42, 82), date_label, font=f_date, fill=SUB)

    for i, p in enumerate(pipelines):
        y = top + i * row_h
        d.text((40, y), p["name"], font=f_name, fill=WHITE)
        if p.get("error"):
            d.text((40, y + 48), f"! {p['error']}", font=f_stat, fill=RED)
            continue
        if p["total"] == 0:
            bb = d.textbbox((0, 0), p["result_label"], font=f_badge)
            d.text((W - 40 - (bb[2] - bb[0]), y + 2), p["result_label"], font=f_badge, fill=RED)
            d.text((40, y + 55), "No test results for this build (run likely failed before tests ran)",
                   font=f_stat, fill=RED)
            continue
        label = p["result_label"]
        badge_color = GREEN if (p["failed"] == 0 and label == "SUCCEEDED") else RED
        bb = d.textbbox((0, 0), label, font=f_badge)
        d.text((W - 40 - (bb[2] - bb[0]), y + 2), label, font=f_badge, fill=badge_color)

        total = max(p["total"], 1)
        bx, by, bw, bh = 40, y + 50, W - 80, 26
        d.rounded_rectangle([bx, by, bx + bw, by + bh], radius=6, fill=TRACK)
        gp = int(bw * p["passed"] / total)
        fp = int(bw * p["failed"] / total)
        d.rectangle([bx, by, bx + gp, by + bh], fill=GREEN)
        d.rectangle([bx + gp, by, bx + gp + fp, by + bh], fill=RED)
        if bw - gp - fp > 0:
            d.rectangle([bx + gp + fp, by, bx + bw, by + bh], fill=GREY)

        stats = (f"Passed {p['passed']}    Failed {p['failed']}    "
                 f"Not-exec {p.get('not_executed', 0)}    |    Total {p['total']}    |    "
                 f"Pass {pass_rate(p):.1f}%    |    Build {p['build_number']}")
        d.text((40, y + 90), stats, font=f_stat, fill=SUB)

    img.save(out_path)
    return out_path


# --------------------------------------------------------------------------- #
# Discord posting
# --------------------------------------------------------------------------- #

def post_report(embed: dict, files: list, dry_run: bool, content: str = None, mention_ids: list = None) -> bool:
    files = [f for f in (files or []) if f and os.path.isfile(f)]
    payload = {"embeds": [embed], "allowed_mentions": {"parse": [], "users": mention_ids or []}}
    if content:
        payload["content"] = content
    if dry_run:
        print("MARSRESULTS: DRY RUN — لم يُنشر في القناة العامة")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        for f in files:
            print("attach:", f)
        return True

    url = f"{DISCORD_API}/channels/{MARS_CHANNEL_ID}/messages"
    token = get_token()
    data = {"payload_json": json.dumps(payload)}
    opened, multipart = [], {}
    try:
        for i, path in enumerate(files):
            fh = open(path, "rb")
            opened.append(fh)
            name = os.path.basename(path)
            mime = "image/png" if name.endswith(".png") else "text/plain"
            multipart[f"files[{i}]"] = (name, fh, mime)
        if multipart:
            resp = requests.post(url, headers={"Authorization": f"Bot {token}"},
                                 data=data, files=multipart, timeout=45)
        else:
            resp = requests.post(url, headers={"Authorization": f"Bot {token}",
                                               "Content-Type": "application/json"},
                                 json=payload, timeout=45)
    finally:
        for fh in opened:
            fh.close()

    if resp.status_code not in (200, 201):
        log(f"POST فشل — status {resp.status_code}: {resp.text[:300]}")
        return False
    log(f"تم الإرسال لقناة {MARS_CHANNEL_ID}")
    return True


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def gather(which: str = "all", with_failures: bool = True) -> list:
    out = []
    for name, def_id, key in PIPELINES:
        if which not in ("all", key):
            continue
        p = collect_pipeline(name, def_id, with_failures)
        p["key"] = key
        out.append(p)
    return out


def _is_bad(p: dict) -> bool:
    return bool(p.get("error")) or p.get("failed", 0) > 0 or (not p.get("error") and p.get("total", 0) == 0)


def build_run_content(pipelines: list):
    """Message content for the daily report. Pings the owner of each failing
    pipeline (Essam=develop, Salama=master) so it acts as a daily reminder
    until fixed. Returns (content, mention_ids)."""
    bad = [p for p in pipelines if _is_bad(p)]
    if not bad:
        return "✅ الأوتوميشن كله عدّى النهاردة — مفيش مشاكل، تسلم إيديكم.", []
    lines = ["⏰ **تذكير يومي — لسه فيه مشاكل في الأوتوميشن محتاجة تتحل:**"]
    mention_ids = []
    for p in bad:
        owner = PIPELINE_OWNERS.get(p.get("key"))
        tag = f"<@{owner}>" if owner else ""
        if p.get("key") == "develop":
            lines.append(f"🔴 Develop: {tag} — شوف مشاكل الـ develop")
        elif p.get("key") == "master":
            lines.append(f"🔴 Master: {tag} — حل مشاكل الـ master")
        else:
            lines.append(f"🔴 {p.get('name','')}: {tag}")
        if owner:
            mention_ids.append(owner)
    lines.append("(التذكير هيتكرر كل يوم لحد ما المشاكل تتحل ✅)")
    return "\n".join(lines), mention_ids


def main() -> None:
    load_env_file(str(BASE / ".env"))

    args = sys.argv[1:]
    cli_dry_run = "--dry-run" in args
    args = [a for a in args if a != "--dry-run"]
    if not args:
        print("Usage: discord_mars_results.py [--dry-run] run | failed [develop|master|all] | fetch",
              file=sys.stderr)
        sys.exit(1)

    command = args[0]
    dry_run = cli_dry_run or is_truthy(os.environ.get("MARSRESULTS_DRY_RUN"))
    date_label = now_label()

    if command == "fetch":
        pipes = gather("all", with_failures=False)
        compact = [{k: p.get(k) for k in ("name", "result_label", "passed", "failed",
                                          "not_executed", "total", "build_number", "error")}
                   for p in pipes]
        print(json.dumps(compact, ensure_ascii=False, indent=2))
        return

    if command == "run":
        pipelines = gather("all", with_failures=True)
        png = render_card(pipelines, str(BASE / "mars_results.png"), date_label)
        txt = build_failed_txt(pipelines, date_label)
        embed = build_embed(pipelines, date_label, has_image=bool(png))
        files = [f for f in (png, txt) if f]
        content, mention_ids = build_run_content(pipelines)
        ok = post_report(embed, files, dry_run=dry_run, content=content, mention_ids=mention_ids)
        sys.exit(0 if ok else 1)

    if command == "failed":
        which = args[1].lower() if len(args) > 1 else "all"
        if which not in ("all", "develop", "master"):
            which = "all"
        pipelines = gather(which, with_failures=True)
        txt = build_failed_txt(pipelines, date_label)
        embed = build_failed_embed(pipelines, date_label)
        ok = post_report(embed, [txt] if txt else [], dry_run=dry_run)
        sys.exit(0 if ok else 1)

    print(f"Unknown command: {command}", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
