#!/usr/bin/env python3
"""Hadi Ameen - Mars automation TEST RESULTS daily report (Azure DevOps -> Discord).

Fetches the latest Develop (def 604) and Master (def 603) TalabatkAPI.Test
pipeline runs from Azure DevOps, builds a summary embed (with an emoji pass/
fail bar, always works) plus an optional PNG card (only if Pillow is present),
and posts it to the mars channel via Discord REST API v10.

Commands:
    python3 discord_mars_results.py run            -> fetch + post to mars channel
    python3 discord_mars_results.py run --dry-run  -> print only, do NOT post
    python3 discord_mars_results.py fetch          -> print JSON summary to stdout

Dry-run is enabled via env MARSRESULTS_DRY_RUN=true/1/yes or the --dry-run flag.
Every error is printed as "MARSRESULTS: ..." to stderr and returns a non-zero
exit code without crashing the rest of the routine.

Env (read from .env next to this script if present, else the process env):
    AZURE_DEVOPS_ORG_URL       default https://hadafsolutions.visualstudio.com
    AZURE_DEVOPS_PAT           PAT, scopes: Build (Read) + Test Management (Read)
    AZURE_DEVOPS_DEFAULT_PROJECT  default 0_Projects_Team
    DISCORD_BOT_TOKEN          Hadi bot token (via routines_common.get_token)
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

# Azure DevOps build result codes
BUILD_RESULT = {"succeeded": "SUCCEEDED", "partiallysucceeded": "PARTIAL", "failed": "FAILED", "canceled": "CANCELED"}

# Discord embed colors
COLOR_GREEN = 0x57F287
COLOR_RED = 0xED4245


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
        "definitions": def_id,
        "statusFilter": "completed",
        "queryOrder": "finishTimeDescending",
        "$top": 1,
        "api-version": ADO_API_VERSION,
    })
    if not data:
        return None
    values = data.get("value") or []
    return values[0] if values else None


def get_test_summary(build_id: int):
    """Aggregated pass/fail counts for a build via its test runs. None on failure.

    Azure DevOps exposes per-build test runs at test/runs?buildUri=... ; each run
    reports totalTests / passedTests / notApplicableTests / unanalyzedTests, and
    totalTests == passed + notApplicable + unanalyzed (verified live). Failed maps
    to unanalyzedTests, not-executed to notApplicableTests.
    """
    data = _ado_get("test/runs", {
        "buildUri": f"vstfs:///Build/Build/{build_id}",
        "api-version": ADO_API_VERSION,
    })
    if not data:
        return None
    passed = failed = not_exec = total = 0
    for run in data.get("value") or []:
        total += run.get("totalTests", 0)
        passed += run.get("passedTests", 0)
        not_exec += run.get("notApplicableTests", 0)
        failed += run.get("unanalyzedTests", 0)
    return {"passed": passed, "failed": failed, "not_executed": not_exec, "total": total}


def build_web_url(build_id: int) -> str:
    return (f"{ADO_ORG_URL}/{ADO_PROJECT}/_build/results"
            f"?buildId={build_id}&view=ms.vss-test-web.build-test-results-tab")


def collect_pipeline(name: str, def_id: int) -> dict:
    try:
        build = get_latest_build(def_id)
        if not build:
            return {"name": name, "error": "مفيش رن مكتمل"}
        summary = get_test_summary(build["id"])
        if summary is None:
            return {"name": name, "error": "تعذّر جلب نتائج الاختبارات"}
        return {
            "name": name,
            "build_id": build["id"],
            "build_number": build.get("buildNumber", str(build["id"])),
            "result_label": BUILD_RESULT.get(str(build.get("result", "")).lower(), "UNKNOWN"),
            "url": build_web_url(build["id"]),
            **summary,
        }
    except Exception as exc:  # noqa: BLE001
        return {"name": name, "error": f"{type(exc).__name__}: {exc}"}


# --------------------------------------------------------------------------- #
# Formatting
# --------------------------------------------------------------------------- #

def pass_rate(p: dict) -> float:
    executed = p["total"] - p.get("not_executed", 0)
    return (p["passed"] / executed * 100) if executed > 0 else 0.0


def emoji_bar(p: dict, width: int = 20) -> str:
    total = max(p["total"], 1)
    g = round(p["passed"] / total * width)
    r = round(p["failed"] / total * width)
    g = min(g, width)
    r = min(r, width - g)
    w = width - g - r
    return "🟩" * g + "🟥" * r + "⬜" * w


def now_label() -> str:
    return datetime.now(CAIRO_TZ).strftime("%A, %d %b %Y — %H:%M") + " القاهرة"


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
                f"\u26a0\ufe0f **{p['result_label']}** \u2014 \u0645\u0641\u064a\u0634 \u0646\u062a\u0627\u0626\u062c "
                f"\u0627\u062e\u062a\u0628\u0627\u0631\u0627\u062a \u0644\u0644\u0631\u0646 \u062f\u0647 "
                f"(\u0627\u0644\u0631\u0646 \u0641\u0634\u0644 \u0642\u0628\u0644 \u062a\u0646\u0641\u064a\u0630 \u0627\u0644\u0627\u062e\u062a\u0628\u0627\u0631\u0627\u062a \u063a\u0627\u0644\u0628\u064b\u0627)\n"
                f"[Build {p['build_number']} \u2014 details]({p['url']})"), "inline": False})
            continue
        dot = "\U0001F7E2" if (p["failed"] == 0 and p["result_label"] == "SUCCEEDED") else "\U0001F534"
        value = (
            f"{emoji_bar(p)}\n"
            f"{dot} **{p['result_label']}** \u00b7 \u0646\u0633\u0628\u0629 \u0627\u0644\u0646\u062c\u0627\u062d **{pass_rate(p):.1f}%**\n"
            f"\u2705 \u0646\u062c\u062d: **{p['passed']}**  \u274c \u0641\u0634\u0644: **{p['failed']}**  "
            f"\u26aa \u0645\u0634 \u0645\u062a\u0646\u0641\u0630: **{p.get('not_executed', 0)}**  (\u0627\u0644\u0643\u0644\u064a {p['total']})\n"
            f"[Build {p['build_number']} \u2014 test results]({p['url']})"
        )
        fields.append({"name": p["name"], "value": value, "inline": False})

    embed = {
        "title": ("\U0001F534 Mars Automation \u2014 \u0646\u062a\u0627\u0626\u062c \u0627\u0644\u0623\u0648\u062a\u0648\u0645\u064a\u0634\u0646 \u0627\u0644\u064a\u0648\u0645\u064a\u0629"
                  if any_fail else
                  "\U0001F7E2 Mars Automation \u2014 \u0646\u062a\u0627\u0626\u062c \u0627\u0644\u0623\u0648\u062a\u0648\u0645\u064a\u0634\u0646 \u0627\u0644\u064a\u0648\u0645\u064a\u0629"),
        "description": date_label,
        "color": COLOR_RED if any_fail else COLOR_GREEN,
        "fields": fields,
        "footer": {"text": "Source: Azure DevOps \u00b7 TalabatkAPI.Test"},
        "timestamp": datetime.now(CAIRO_TZ).isoformat(),
    }
    if has_image:
        embed["image"] = {"url": "attachment://mars_results.png"}
    return embed


# --------------------------------------------------------------------------- #
# Optional PNG card (only if Pillow is available)
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
    """Render a card PNG. Returns path, or None if Pillow is unavailable."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        log("Pillow مش متثبت — هيتبعت embed من غير صورة")
        return None

    W = 1000
    row_h = 150
    top = 130
    H = top + row_h * len(pipelines) + 50
    BG = (35, 39, 42)
    GREEN = (87, 242, 135)
    RED = (237, 66, 69)
    GREY = (148, 155, 164)
    TRACK = (30, 31, 34)
    WHITE = (255, 255, 255)
    SUB = (181, 186, 193)

    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    f_title = _load_font(34, bold=True)
    f_date = _load_font(18)
    f_name = _load_font(24, bold=True)
    f_stat = _load_font(19)
    f_badge = _load_font(21, bold=True)

    d.text((40, 34), "Mars Automation — Daily Results", font=f_title, fill=WHITE)
    d.text((42, 82), date_label, font=f_date, fill=SUB)

    for i, p in enumerate(pipelines):
        y = top + i * row_h
        d.text((40, y), p["name"], font=f_name, fill=WHITE)
        if p.get("error"):
            d.text((40, y + 48), f"! {p['error']}", font=f_stat, fill=RED)
            continue

        if p["total"] == 0:
            bbox0 = d.textbbox((0, 0), p["result_label"], font=f_badge)
            d.text((W - 40 - (bbox0[2] - bbox0[0]), y + 2), p["result_label"], font=f_badge, fill=RED)
            d.text((40, y + 55), "No test results for this build (run likely failed before tests ran)",
                   font=f_stat, fill=RED)
            continue

        label = p["result_label"]
        badge_color = GREEN if (p["failed"] == 0 and label == "SUCCEEDED") else RED
        bbox = d.textbbox((0, 0), label, font=f_badge)
        d.text((W - 40 - (bbox[2] - bbox[0]), y + 2), label, font=f_badge, fill=badge_color)

        total = max(p["total"], 1)
        bx, by, bw, bh = 40, y + 50, W - 80, 26
        d.rounded_rectangle([bx, by, bx + bw, by + bh], radius=6, fill=TRACK)
        gp = int(bw * p["passed"] / total)
        fp = int(bw * p["failed"] / total)
        d.rectangle([bx, by, bx + gp, by + bh], fill=GREEN)
        d.rectangle([bx + gp, by, bx + gp + fp, by + bh], fill=RED)
        rem = bw - gp - fp
        if rem > 0:
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

def post_report(embed: dict, png_path, dry_run: bool) -> bool:
    if dry_run:
        print("MARSRESULTS: DRY RUN — لم يُنشر في القناة العامة")
        print(json.dumps({"embeds": [embed]}, ensure_ascii=False, indent=2))
        return True

    url = f"{DISCORD_API}/channels/{MARS_CHANNEL_ID}/messages"
    token = get_token()
    payload = {"embeds": [embed]}

    if png_path and os.path.isfile(png_path):
        with open(png_path, "rb") as fh:
            files = {"files[0]": ("mars_results.png", fh, "image/png")}
            resp = requests.post(url, headers={"Authorization": f"Bot {token}"},
                                 data={"payload_json": json.dumps(payload)},
                                 files=files, timeout=45)
    else:
        resp = requests.post(url, headers={"Authorization": f"Bot {token}",
                                           "Content-Type": "application/json"},
                             json=payload, timeout=45)

    if resp.status_code not in (200, 201):
        log(f"POST فشل — status {resp.status_code}: {resp.text[:300]}")
        return False
    log(f"تم إرسال تقرير النتائج لقناة {MARS_CHANNEL_ID}")
    return True


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def gather() -> list:
    return [
        collect_pipeline("Develop — TalabatkAPI.Test", DEVELOP_DEF_ID),
        collect_pipeline("Master — TalabatkAPI.Test", MASTER_DEF_ID),
    ]


def main() -> None:
    load_env_file(str(BASE / ".env"))

    args = sys.argv[1:]
    cli_dry_run = "--dry-run" in args
    args = [a for a in args if a != "--dry-run"]
    if not args:
        print("Usage: discord_mars_results.py [--dry-run] run | fetch", file=sys.stderr)
        sys.exit(1)

    command = args[0]
    dry_run = cli_dry_run or is_truthy(os.environ.get("MARSRESULTS_DRY_RUN"))
    pipelines = gather()

    if command == "fetch":
        print(json.dumps(pipelines, ensure_ascii=False, indent=2))
        return

    if command == "run":
        date_label = now_label()
        png = render_card(pipelines, str(BASE / "mars_results.png"), date_label)
        embed = build_embed(pipelines, date_label, has_image=bool(png))
        ok = post_report(embed, png, dry_run=dry_run)
        sys.exit(0 if ok else 1)

    print(f"Unknown command: {command}", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
