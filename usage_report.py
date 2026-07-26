#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""تقرير استخدام محرك هادي (بند 3.1/F5) — يقرا logs/usage.jsonl ويطلع KPIs بالأرقام.

الاستخدام:
    python3 usage_report.py            # آخر 7 أيام
    python3 usage_report.py --days 30  # آخر 30 يوم

KPIs:
  - Hit Rate  = cache_read / (cache_read + cache_write + input)  ← المستهدف بعد التفعيل: +70%
  - تكلفة/تفاعل و P50 زمن — نفس مؤشرات تقرير التحسينات (§10).
ملاحظة: على اشتراك Claude التكلفة المطبوعة تقديرية (الاستخدام محسوب على الخطة) —
لكن التوكنز حقيقية، وهي أساس قرار الكاش.
"""
import argparse
import json
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

LOG = Path(__file__).resolve().parent / "logs" / "usage.jsonl"


def load_rows(days: float):
    if not LOG.exists():
        raise SystemExit(f"مفيش لوج لسه: {LOG} — شغّل البوت الأول وسيبه يستقبل رسايل.")
    cutoff = time.time() - days * 86400
    rows = []
    for line in LOG.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
            # fromisoformat بيفهم الـ +0300 اللي %z بيكتبه — mktime على نص مقصوص
            # كان بيتعامل معاه كتوقيت محلي (2026-07-26)
            ts = datetime.fromisoformat(r["ts"]).timestamp()
            if ts >= cutoff:
                r["_day"] = r["ts"][:10]
                rows.append(r)
        except (ValueError, KeyError):
            continue
    return rows


def pct(n, d):
    return f"{100.0 * n / d:5.1f}%" if d else "  n/a "


def p50(values):
    vals = sorted(v for v in values if v is not None)
    return vals[len(vals) // 2] if vals else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=float, default=7.0)
    args = ap.parse_args()
    rows = load_rows(args.days)
    if not rows:
        raise SystemExit("مفيش تفاعلات في المدة دي.")

    days = defaultdict(list)
    for r in rows:
        days[r["_day"]].append(r)

    print(f"تقرير استخدام هادي — آخر {args.days:g} يوم — {len(rows)} تفاعل")
    print(f"{'اليوم':12} {'تفاعل':>6} {'hit rate':>8} {'cache_read':>11} "
          f"{'cache_write':>11} {'input':>8} {'P50 ms':>8} {'تكلفة$':>8}")
    for day in sorted(days):
        rs = days[day]
        cr = sum(r.get("cache_read", 0) for r in rs)
        cw = sum(r.get("cache_write", 0) for r in rs)
        inp = sum(r.get("input_tokens", 0) for r in rs)
        cost = sum(r.get("cost_usd") or 0 for r in rs)
        print(f"{day:12} {len(rs):>6} {pct(cr, cr + cw + inp):>8} {cr:>11,} "
              f"{cw:>11,} {inp:>8,} {p50([r.get('duration_ms') for r in rs]):>8,} {cost:>8.3f}")

    cr = sum(r.get("cache_read", 0) for r in rows)
    cw = sum(r.get("cache_write", 0) for r in rows)
    inp = sum(r.get("input_tokens", 0) for r in rows)
    cost = sum(r.get("cost_usd") or 0 for r in rows)
    print("-" * 78)
    print(f"{'الإجمالي':12} {len(rows):>6} {pct(cr, cr + cw + inp):>8} {cr:>11,} "
          f"{cw:>11,} {inp:>8,} {p50([r.get('duration_ms') for r in rows]):>8,} {cost:>8.3f}")
    print(f"تكلفة/1000 تفاعل: ${1000.0 * cost / len(rows):.2f} — "
          f"resume: {sum(1 for r in rows if r.get('resumed'))}/{len(rows)}")

    by_key = defaultdict(list)
    for r in rows:
        by_key[r.get("conv_key", "-")].append(r)
    print("\nحسب المحادثة (أعلى 8):")
    ranked = sorted(by_key.items(), key=lambda kv: -len(kv[1]))[:8]
    for key, rs in ranked:
        cr = sum(r.get("cache_read", 0) for r in rs)
        cw = sum(r.get("cache_write", 0) for r in rs)
        inp = sum(r.get("input_tokens", 0) for r in rs)
        print(f"  {key:24} {len(rs):>5} تفاعل  hit={pct(cr, cr + cw + inp)}")


if __name__ == "__main__":
    main()
