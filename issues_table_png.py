#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""issues_table_png.py — جدول الإيشوز المفتوحة كصورة PNG في Discord.

المشكلة اللي بيحلها: `code block` فيه نص عربي+إنجليزي مختلط = محاذاة مكسورة
على Discord. الحل: HTML جدول → WeasyPrint → PNG → Discord DM أو قناة.

WeasyPrint مثبّت أصلًا (للتقرير اليومي) — مفيش dependency جديدة.

الاستخدام:
    python3 issues_table_png.py --channel CHANNEL_ID
    python3 issues_table_png.py --channel CHANNEL_ID --states "New,Active"
    python3 issues_table_png.py --channel CHANNEL_ID --area-path "Support" --top 50
    python3 issues_table_png.py --out /tmp/table.png           # يحفظ بدل ما يبعت
    python3 issues_table_png.py selftest                        # من غير شبكة/Discord
"""
import argparse
import io
import json
import os
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent

try:
    from dotenv import load_dotenv
    load_dotenv(BASE / ".env")
except Exception:
    pass

DISCORD_API = "https://discord.com/api/v10"

# ألوان الحالات — نفس palette التقرير اليومي
_STATE_STYLE = {
    "new":      ("#DBEAFE", "#1D4ED8"),   # أزرق فاتح
    "reviewed": ("#FEF3C7", "#92400E"),   # أصفر فاتح
    "active":   ("#D1FAE5", "#065F46"),   # أخضر فاتح
}


# ─────────────────────────── جلب البيانات ───────────────────────────
def fetch_issues(states, area_path, top, project):
    """يشغّل ado_cli.py issues-table --json ويرجّع list من dicts."""
    cmd = [
        sys.executable, str(BASE / "ado_cli.py"),
        "issues-table",
        "--json",
        "--states", states,
        "--top", str(top),
    ]
    if area_path:
        cmd += ["--area-path", area_path]
    if project:
        cmd += ["--project", project]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, cwd=str(BASE))
    if result.returncode != 0:
        raise RuntimeError(f"ado_cli.py failed: {result.stderr.strip()[:300]}")
    return json.loads(result.stdout)


# ───────────────────────── بناء الـ HTML ─────────────────────────────
def _state_span(state: str) -> str:
    key = (state or "").lower()
    bg, fg = _STATE_STYLE.get(key, ("#E2E8F0", "#1E293B"))
    return (f'<span style="background:{bg};color:{fg};padding:2px 10px;'
            f'border-radius:20px;font-size:11px;white-space:nowrap;'
            f'font-weight:600">{state or "—"}</span>')


def _sev(raw) -> str:
    s = str(raw or "—")
    # "2 - High" → يفضل كما هو؛ "—" → كما هو
    return s


def build_html(rows, caption="") -> str:
    rows_html = ""
    for i, r in enumerate(rows):
        bg = "#F8FAFC" if i % 2 == 0 else "#FFFFFF"
        rows_html += f"""
<tr style="background:{bg}">
  <td style="color:#64748B;font-family:monospace;white-space:nowrap">#{r['id']}</td>
  <td>{_state_span(r['state'])}</td>
  <td style="white-space:nowrap;font-size:11px">{_sev(r['severity'])}</td>
  <td style="text-align:center">{r['priority']}</td>
  <td style="color:#475569;white-space:nowrap">{(r['owner'] or '—')[:28]}</td>
  <td style="color:#94A3B8;font-size:11px;white-space:nowrap">{r['created']}</td>
  <td style="max-width:340px">{(r['title'] or '')[:90]}</td>
</tr>"""

    caption_html = f'<p style="margin:10px 20px 0;color:#94A3B8;font-size:12px">{caption}</p>' if caption else ""

    return f"""<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
<meta charset="utf-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap');
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  font-family: 'Cairo', 'Segoe UI', Arial, sans-serif;
  background: #F1F5F9;
  padding: 16px;
  direction: rtl;
  min-width: 900px;
}}
.card {{
  background: #fff;
  border-radius: 14px;
  overflow: hidden;
  box-shadow: 0 4px 16px rgba(0,0,0,.1);
}}
.header {{
  background: linear-gradient(135deg, #1E293B 0%, #334155 100%);
  color: #fff;
  padding: 14px 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}}
.header h1 {{ font-size: 15px; font-weight: 700; }}
.header .badge {{
  background: rgba(255,255,255,.15);
  border-radius: 20px;
  padding: 3px 12px;
  font-size: 12px;
  white-space: nowrap;
}}
table {{ width: 100%; border-collapse: collapse; font-size: 12.5px; }}
th {{
  background: #334155;
  color: #CBD5E1;
  padding: 9px 14px;
  text-align: right;
  font-weight: 600;
  font-size: 11px;
  white-space: nowrap;
}}
td {{
  padding: 8px 14px;
  border-bottom: 1px solid #F1F5F9;
  color: #1E293B;
  text-align: right;
  vertical-align: middle;
}}
tr:last-child td {{ border-bottom: none; }}
</style>
</head>
<body>
<div class="card">
  <div class="header">
    <h1>📋 الإيشوز المفتوحة على بورد السابورت</h1>
    <span class="badge">{len(rows)} إيشو</span>
  </div>
  <table>
    <tr>
      <th>ID</th>
      <th>الحالة</th>
      <th>Severity</th>
      <th>P</th>
      <th>المسؤول</th>
      <th>Created</th>
      <th>العنوان</th>
    </tr>
    {rows_html}
  </table>
</div>
{caption_html}
</body>
</html>"""


# ───────────────────────── WeasyPrint ──────────────────────────────
def render_png(html_str: str) -> bytes:
    """يرندر HTML لـ PNG bytes باستخدام WeasyPrint (مثبّت مع التقرير اليومي)."""
    from weasyprint import HTML
    return HTML(string=html_str, base_url=str(BASE)).write_png(resolution=144)


# ───────────────────────── إرسال Discord ────────────────────────────
def post_to_channel(channel_id: str, png_bytes: bytes, caption: str, token: str):
    import requests
    url = f"{DISCORD_API}/channels/{channel_id}/messages"
    resp = requests.post(
        url,
        headers={"Authorization": f"Bot {token}"},
        data={"content": caption or ""},
        files={"files[0]": ("issues_table.png", io.BytesIO(png_bytes), "image/png")},
        timeout=45,
    )
    if resp.status_code not in (200, 201):
        raise RuntimeError(
            f"Discord POST failed — HTTP {resp.status_code}: {resp.text[:300]}")
    return resp.json()


# ─────────────────────────── selftest ───────────────────────────────
def selftest():
    """يتأكد إن WeasyPrint مثبّت ويرندر HTML بسيط — من غير شبكة أو Discord."""
    from weasyprint import HTML
    png = HTML(string="<html><body><p style='color:green'>OK</p></body></html>").write_png()
    assert png and len(png) > 500, f"write_png فاضي ({len(png)} bytes)"
    # اختبار _state_span
    assert "border-radius" in _state_span("New")
    # اختبار build_html بدون crash
    sample = [{"id": 1, "state": "New", "severity": "2 - High", "priority": "1",
               "owner": "غادة فودة", "created": "2026-08-01", "title": "مشكلة اختبار", "url": "#"}]
    html = build_html(sample)
    assert "<table" in html
    print("SELFTEST PASS — WeasyPrint render + HTML builder سليمين")


# ─────────────────────────── main ───────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description="جدول الإيشوز كـ PNG في Discord")
    ap.add_argument("cmd_or_channel", nargs="?",
                    help='"selftest" أو channel id مباشرة (اختصار بدل --channel)')
    ap.add_argument("--channel",
                    help="Discord channel id (أو env ISSUES_CHANNEL_ID/SUPPORT_CHANNEL_ID)")
    ap.add_argument("--states", default="New,Reviewed,Active")
    ap.add_argument("--area-path")
    ap.add_argument("--top", type=int, default=200)
    ap.add_argument("--project")
    ap.add_argument("--caption", default="")
    ap.add_argument("--out", help="احفظ PNG في ملف بدل الإرسال لـ Discord")
    ap.add_argument("--dry-run", action="store_true",
                    help="ولّد PNG واحفظه محليًا من غير إرسال")
    args = ap.parse_args()

    # اختصار: لو الـ positional هو "selftest" أو channel id
    if args.cmd_or_channel == "selftest":
        selftest()
        return
    channel = args.channel or args.cmd_or_channel or \
              os.environ.get("ISSUES_CHANNEL_ID") or \
              os.environ.get("SUPPORT_CHANNEL_ID")

    # ─── جيب البيانات ───
    rows = fetch_issues(
        states=args.states,
        area_path=args.area_path,
        top=args.top,
        project=args.project,
    )
    if not rows:
        print(f"مفيش إيشوز مفتوحة بالحالات: {args.states}")
        return

    # ─── رندر ───
    html = build_html(rows, caption=args.caption)
    png_bytes = render_png(html)

    # ─── إخراج ───
    if args.out:
        Path(args.out).write_bytes(png_bytes)
        print(f"PNG saved: {args.out}  ({len(rows)} rows, {len(png_bytes)//1024}KB)")
        return

    if args.dry_run or not channel:
        out = BASE / "issues_table_preview.png"
        out.write_bytes(png_bytes)
        if args.dry_run:
            print(f"DRY-RUN: PNG saved to {out}  ({len(rows)} rows, {len(png_bytes)//1024}KB) — لم يُرسَل")
        else:
            print(f"DISCORD: مفيش channel id — PNG saved to {out}\n"
                  "مرر --channel CHANNEL_ID أو ضيف ISSUES_CHANNEL_ID في .env")
        return

    token = os.environ.get("DISCORD_BOT_TOKEN")
    if not token:
        sys.exit("ERROR: DISCORD_BOT_TOKEN not set")

    post_to_channel(channel, png_bytes, args.caption, token)
    print(f"SENT: {len(rows)} إيشوز → قناة {channel}  ({len(png_bytes)//1024}KB)")


if __name__ == "__main__":
    main()
