#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""المراجعة الأسبوعية — قافلة حلقة التحسين (بند 5.3).

الحلقة: أسوأ التفاعلات تقييمًا ← حالات جديدة في الـ suite ← أي تعديل تعليمات
يتقاس قبل/بعد. السكربت ده بيعمل الخطوة الأولى والتانية:

  1) بيرتّب أسوأ التفاعلات من eval_store (سلبي بالرياكشن → أخطاء/مهل → الأبطأ).
  2) بيطلع لكل واحدة **حالة جاهزة** بصيغة evals/cases.json عشان المراجع ينسخها
     (بشرط بشري — مفيش حالة بتتضاف آليًا: الحالة بتحدد السلوك الصح، والصح ده
     قرار بشري مش استنتاج).
  3) بيقارن آخر تشغيل للـ suite بخط الأساس لو موجودين.

الاستخدام:
    weekly_review.py [--days 7] [--limit 8] [--write-report]
"""
import argparse
import datetime as dt
import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent
RUNS_DIR = BASE / "evals" / "runs"
BASELINE = BASE / "evals" / "baseline.json"

try:
    import eval_store
except Exception as error:  # pragma: no cover
    raise SystemExit(f"weekly_review محتاج eval_store.py جنبه: {error}")


def _slug(text: str, fallback: str) -> str:
    words = re.findall(r"[A-Za-z0-9]+", text.lower())[:3]
    return "_".join(words) if words else fallback


def propose_case(row: dict) -> dict:
    """يحوّل تفاعل سيئ لحالة مقترحة — الشروط فاضية عمدًا عشان المراجع يحددها."""
    outcome = row["outcome"]
    if outcome in ("error", "timeout"):
        why = f"التفاعل ده انتهى بـ {outcome}" + (f" ({row['error_type']})" if row["error_type"] else "")
        expect = [{"type": "replies"}]
    elif row.get("score", 0) < 0:
        why = "الفريق قيّم الرد بالسالب — حدد السلوك الصح هنا"
        expect = [{"type": "contains_any", "values": ["<<< املا الصح المتوقع >>>"]}]
    else:
        why = f"بطيء ({row['latency_ms']/1000:.0f} ثانية) — تأكد إن الرد نفسه سليم"
        expect = [{"type": "replies"}]
    return {
        "id": f"from_review_{dt.date.today():%m%d}_{_slug(row['prompt_excerpt'], str(row['id']))}",
        "category": "from_review",
        "why": why,
        "input": {
            "message": row["prompt_excerpt"],
            "author": row["author"] or "آسر",
            "channel": row["channel"] or "#team-mars-po",
        },
        "expect": expect,
    }


def suite_section() -> list:
    lines = ["## 3) الـ suite — قبل/بعد", ""]
    runs = sorted(RUNS_DIR.glob("run_*.json")) if RUNS_DIR.exists() else []
    if not runs:
        lines += ["- مفيش تشغيلات للـ suite لسه. شغّل: `python3 eval_runner.py run` ثم `baseline`.", ""]
        return lines
    latest = json.loads(runs[-1].read_text(encoding="utf-8"))
    lines.append(f"- آخر تشغيل: **{latest['pass_rate']}%** ({latest['passed']}/{latest['total']}) — {latest['ts']}")
    if BASELINE.exists():
        base = json.loads(BASELINE.read_text(encoding="utf-8"))
        delta = latest["pass_rate"] - base["pass_rate"]
        arrow = "▲" if delta > 0 else ("▼" if delta < 0 else "=")
        lines.append(f"- خط الأساس: {base['pass_rate']}% ({base['ts']}) — الفرق: {arrow} {abs(delta):.1f} نقطة")
        bmap = {r["id"]: r for r in base["results"]}
        broke = [r["id"] for r in latest["results"] if bmap.get(r["id"], {}).get("passed") and not r["passed"]]
        if broke:
            lines.append(f"- ⚠ **اتكسر:** {', '.join(broke)}")
    else:
        lines.append("- مفيش خط أساس — `python3 eval_runner.py baseline`")
    failing = [r["id"] for r in latest["results"] if not r["passed"]]
    if failing:
        lines.append(f"- حالات راسبة دلوقتي: {', '.join(failing)}")
    lines.append("")
    return lines


def build_report(days: float, limit: int) -> str:
    st = eval_store.stats(days)
    rows = eval_store.worst(days, limit)
    today = dt.date.today().isoformat()

    lines = [
        f"# المراجعة الأسبوعية لهادي — {today}",
        "",
        f"> آخر {days:g} يوم. مولَّد بـ `weekly_review.py` (بند 5.3). "
        "القرارات هنا بشرية — السكربت بيرتّب ويقترح بس.",
        "",
        "## 1) الأرقام",
        "",
        "| المؤشر | القيمة |",
        "|--------|--------|",
        f"| تفاعلات | {st['interactions']} (رد {st['replies']} / صمت {st['no_reply']}) |",
        f"| أخطاء / مهل | {st['errors']} / {st['timeouts']} |",
        f"| زمن الرد P50 / P90 | {st['p50_ms']/1000:.0f}ث / {st['p90_ms']/1000:.0f}ث |",
        f"| تكلفة الفترة | ${st['cost_usd']} |",
        f"| تكلفة/1000 تفاعل | ${st['cost_per_1000']} |",
        f"| تقييمات (👍/👎) | {st['feedback_pos']} / {st['feedback_neg']} |",
        "",
    ]
    if st["interactions"] == 0:
        lines += ["> مفيش تفاعلات مسجلة في الفترة دي — الجدولة أسبوعية والتسجيل بيبدأ مع أول رسالة.", ""]

    lines += ["## 2) أسوأ التفاعلات", ""]
    if not rows:
        lines.append("- مفيش. أسبوع نضيف.")
    for row in rows:
        tag = row["outcome"] + (f"/{row['error_type']}" if row["error_type"] else "")
        lines += [
            f"### #{row['id']} — {tag} | تقييم {row['score']} | {row['latency_ms']/1000:.0f}ث",
            f"- **القناة:** {row['channel'] or '-'} | **صاحب الطلب:** {row['author'] or '-'}",
            f"- **الطلب:** {row['prompt_excerpt'][:200]}",
        ]
        if row["reply_excerpt"]:
            lines.append(f"- **الرد:** {row['reply_excerpt'][:200]}")
        lines += ["", "```json", json.dumps(propose_case(row), ensure_ascii=False, indent=2), "```", ""]

    lines += suite_section()
    lines += [
        "## 4) الخطوات",
        "",
        "1. راجع الحالات المقترحة فوق، املا الشرط المتوقع، وضيفها في `evals/cases.json`.",
        "2. عدّل التعليمات (CLAUDE.md / HADI_*.md) للي محتاج تعديل.",
        "3. `python3 eval_runner.py run` ثم `python3 eval_runner.py diff` — التعديل يتقاس مش يتحس.",
        "4. لو مفيش انحدار: انشر. لو في: صلّح الأول.",
        "",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="المراجعة الأسبوعية (بند 5.3)")
    parser.add_argument("--days", type=float, default=7)
    parser.add_argument("--limit", type=int, default=8)
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args()

    report = build_report(args.days, args.limit)
    print(report)
    if args.write_report:
        out = BASE / "evals" / f"review_{dt.date.today():%Y_%m_%d}.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report, encoding="utf-8")
        print(f"\nREPORT: {out}")


if __name__ == "__main__":
    main()
