#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""eval_report.py — تقرير الـ evals الأسبوعي لآسر في الـ DM (نقطة 7).

بيجمّع كل إشارات الجودة في رسالة واحدة:
  1. أرقام التشغيل (eval_store): تفاعلات، رد/صمت/أخطاء، p50/p90، تكلفة.
  2. فيدباك التيم: رياكشنز موجبة/سالبة + أسوأ 3 تفاعلات بنصها (error analysis).
  3. بوابة الحضور (logs/ambient_gate.jsonl): توزيع القرارات ونسبة قطع الـ pre-filter.
  4. الملخصات اليومية (logs/digests.jsonl): نجح/سكت/فشل.
  5. الحكم الأسبوعي (eval_judge): متوسطات الـ rubric + أبرز الـ issues.
  6. الحالات الذهبية: آخر تشغيلة + مقارنة بالـ baseline لو موجودين.

الاستخدام:
  python3 eval_report.py build [--days 7] [--with-judge]   # طباعة بس
  python3 eval_report.py send  [--days 7] [--with-judge]   # DM لآسر
(التايمر الأسبوعي: setup/systemd/hadi-eval-weekly.timer — الخميس 09:30 القاهرة)
"""
import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

AMBIENT_LOG = BASE_DIR / "logs" / "ambient_gate.jsonl"
DIGESTS_LOG = BASE_DIR / "logs" / "digests.jsonl"
RUNS_DIR = BASE_DIR / "evals" / "runs"
BASELINE = BASE_DIR / "evals" / "baseline.json"


def _read_jsonl(path, days):
    if not path.exists():
        return []
    cutoff = time.time() - days * 86400
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        try:
            # 2026-07-26: الطابع مكتوب بـ %z (فيه +0300). القص على 19 حرف كان
            # بيشيل الـ offset وmktime كان بيفسّر الباقي كتوقيت محلي — فأي تشغيل
            # على UTC (CI/container) كان بيفلتر غلط بساعتين/تلاتة.
            ts = datetime.fromisoformat(row.get("ts", "")).timestamp()
            if ts < cutoff:
                continue
        except (ValueError, TypeError):
            pass
        out.append(row)
    return out


def _ambient_section(days):
    rows = _read_jsonl(AMBIENT_LOG, days)
    if not rows:
        return "🚪 بوابة الحضور: مفيش داتا للفترة دي"
    total = len(rows)
    pre = sum(1 for r in rows if r.get("stage") == "prefilter")
    decided = [r for r in rows if r.get("stage") == "gate"]
    reacts = sum(1 for r in decided if r.get("decision") == "react")
    replies = sum(1 for r in decided if r.get("decision") == "reply")
    silents = total - reacts - replies
    return (f"🚪 بوابة الحضور: {total} رسالة ambient — "
            f"صمت {silents} ({100 * silents // max(total, 1)}%) | "
            f"رياكشن {reacts} | رد {replies} | "
            f"الـ pre-filter قطع {pre} ({100 * pre // max(total, 1)}%) ببلاش")


def _digests_section(days):
    rows = _read_jsonl(DIGESTS_LOG, days)
    if not rows:
        return "📰 الملخصات اليومية: مفيش داتا (التايمرات لسه متفعلتش؟)"
    posted = sum(1 for r in rows if r.get("decision") == "posted")
    skipped = sum(1 for r in rows if str(r.get("decision", "")).startswith("skip"))
    blocked = sum(1 for r in rows if r.get("decision") == "blocked_down")
    failed = sum(1 for r in rows if not r.get("ok"))
    return (f"📰 الملخصات اليومية: {posted} اتبعت | {skipped} سكتت (يوم هادي) | "
            f"{blocked} اتحجبت (PostHog DOWN) | {failed} فشلت"
            + (" ⚠️" if failed else ""))


def _golden_section():
    # نفس النمط بتاع eval_runner.latest_run — "*.json" كان بيلقط baseline.json كمان
    latest = sorted(RUNS_DIR.glob("run_*.json")) if RUNS_DIR.exists() else []
    if not latest:
        return "🏅 الحالات الذهبية: مفيش تشغيلة محفوظة — شغّل eval_runner.py run"
    try:
        run = json.loads(latest[-1].read_text(encoding="utf-8"))
    except Exception:
        return "🏅 الحالات الذهبية: آخر تشغيلة مش مقروءة"
    line = (f"🏅 الحالات الذهبية (آخر تشغيلة {run.get('ts', '?')}): "
            f"{run.get('passed', '?')}/{run.get('total', '?')} ناجح")
    if BASELINE.exists():
        try:
            base = json.loads(BASELINE.read_text(encoding="utf-8"))
            diff = (run.get("passed", 0) or 0) - (base.get("passed", 0) or 0)
            line += f" (مقابل الـ baseline: {'+' if diff >= 0 else ''}{diff})"
        except Exception:
            pass
    return line


def _judge_section(days, with_judge):
    import eval_judge
    if with_judge:
        eval_judge.run(days=days)
    s = eval_judge.latest_summary()
    if not s or not s.get("judged"):
        return "⚖️ الحكم الأسبوعي: مفيش نتايج"
    avg = s.get("avg_scores", {})
    lines = [f"⚖️ الحكم الأسبوعي ({s['judged']} رد متقيّم): "
             f"مصادر {avg.get('grounding', '?')}/5 | شخصية {avg.get('persona', '?')}/5 | "
             f"إيجاز {avg.get('brevity', '?')}/5 | سياق {avg.get('context', '?')}/5"
             + (f" | ردود ضعيفة: {s.get('low_scored', 0)}" if s.get("low_scored") else "")]
    for issue in (s.get("top_issues") or [])[:3]:
        lines.append(f"   • {issue}")
    return "\n".join(lines)


def build(days=7.0, with_judge=False):
    import eval_store
    st = eval_store.stats(days)
    lines = [f"📊 **تقرير جودة هادي** — آخر {int(days)} أيام", ""]
    lines.append(
        f"⚙️ التشغيل: {st['interactions']} تفاعل — رد {st['replies']} | "
        f"صمت {st['no_reply']} | خطأ {st['errors']} | timeout {st['timeouts']}")
    lines.append(
        f"⏱️ الاستجابة: p50 {st['p50_ms'] // 1000}ث | p90 {st['p90_ms'] // 1000}ث | "
        f"التكلفة ${st['cost_usd']}")
    fb = f"👍 {st['feedback_pos']} / 👎 {st['feedback_neg']} (من {st['feedback_total']} رياكشن)"
    lines.append(f"🗣️ فيدباك التيم: {fb}")
    bad = [w for w in eval_store.worst(days, 3)
           if w.get("score", 0) < 0 or w.get("outcome") in ("error", "timeout")]
    if bad:
        lines.append("")
        lines.append("🔍 محتاج مراجعة (error analysis):")
        for w in bad:
            lines.append(f"   • [{w.get('outcome')}] {w.get('author', '?')}: "
                         f"{(w.get('prompt_excerpt') or '')[:90]}")
            if w.get("reply_excerpt"):
                lines.append(f"     ردّي: {(w.get('reply_excerpt') or '')[:110]}")
    lines.append("")
    lines.append(_ambient_section(days))
    lines.append(_digests_section(days))
    lines.append(_golden_section())
    lines.append(_judge_section(days, with_judge))
    return "\n".join(lines)


def main():
    p = argparse.ArgumentParser(description="Hadi weekly evals report.")
    p.add_argument("cmd", choices=["build", "send"])
    p.add_argument("--days", type=float, default=7.0)
    p.add_argument("--with-judge", action="store_true")
    a = p.parse_args()
    text = build(a.days, a.with_judge)
    print(text)
    if a.cmd == "send":
        from daily_digests import _dm_asser
        ok = _dm_asser(text)
        print("\n[DM]", "اتبعت لآسر" if ok else "فشل الإرسال")
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
