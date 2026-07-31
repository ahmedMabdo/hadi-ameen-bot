#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""8Orders — Weekly Product Metrics Report.

Same 21-section executive layout that went to management, driven by a full week of
live PostHog data instead of a single day.

Design contract (per the PO):
  · every NUMBER is computed in Python from live PostHog data (wpm_data.collect_week)
  · the LLM only writes the qualitative reading — it never computes or invents a number
  · the run FAILS LOUD rather than delivering a zeroed report (preflight)
  · partial weeks are handled honestly: averages and week-over-week use ACTIVE days only

Schedule: Thursday 12:00 Africa/Cairo via systemd, DM'd to Asser by Hadi.

Env: POSTHOG_API_KEY (Personal key, phx_...), DISCORD_BOT_TOKEN,
     optional ANTHROPIC_API_KEY (qualitative reading), optional ASSER_USER_ID.

Usage:
    python3 intel/weekly_product_metrics.py                      # build + DM
    python3 intel/weekly_product_metrics.py --dry-run            # build, don't DM
    python3 intel/weekly_product_metrics.py --to 1378684355148386355
    python3 intel/weekly_product_metrics.py --date 2026-07-29    # explicit end day
    python3 intel/weekly_product_metrics.py --dump-fixture w.json --dry-run
    python3 intel/weekly_product_metrics.py --fixture w.json --no-llm --dry-run
"""
import os, sys, json, argparse, datetime as dt
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import wpm_data as WD
import wpm_render as WR

CAIRO_TZ = WD.CAIRO_TZ


def deliver(pdf_path, label, dry_run=False, to=None):
    raw = to or os.environ.get("ASSER_USER_ID", "1378684355148386355")
    recipients = [x.strip() for x in str(raw).replace(",", " ").split() if x.strip()]
    msg = (f"**تقرير مؤشرات المنتج — أسبوعي**\n"
           f"الفترة: {label}\n\n"
           f"التقرير مبني على بيانات PostHog الحقيقية للأسبوع، وكل الأرقام محسوبة برمجيًا. "
           f"القراءة النوعية مكتوبة على الأرقام دي بدون أي إعادة حساب.\n"
           f"ابدأ من الملخص التنفيذي (صفحة 1) ثم القرارات المقترحة في آخر التقرير.")
    if dry_run:
        print(f"DRY-RUN: would DM {recipients} with {pdf_path}")
        return True
    try:
        import discord_delivery
        discord_delivery.send_report([pdf_path], message=msg, user_ids=recipients)
        print(f"DISCORD: delivered to {recipients}.")
        return True
    except Exception as e:
        print(f"DISCORD: delivery failed (non-fatal): {e}", file=sys.stderr)
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="end business day, YYYY-MM-DD (default: yesterday Cairo)")
    ap.add_argument("--out", help="output PDF path")
    ap.add_argument("--dry-run", action="store_true", help="build but do not DM")
    ap.add_argument("--no-discord", action="store_true", help="skip delivery entirely")
    ap.add_argument("--no-llm", action="store_true", help="rule-based assessment only")
    ap.add_argument("--to", help="Discord user id(s) to DM, comma or space separated")
    ap.add_argument("--fixture", help="render from a saved data JSON instead of querying PostHog")
    ap.add_argument("--dump-fixture", help="write the collected data dict to this JSON file")
    args = ap.parse_args()

    if args.fixture:
        data = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
        print(f"FIXTURE: loaded {args.fixture} "
              f"({data['week_start']}..{data['week_end']}, {data['active_days']} active days)")
    else:
        WD.preflight()   # raises rather than letting a zeroed report through
        end_day = args.date or (WD.cairo_today() - dt.timedelta(days=1)).isoformat()
        print(f"Collecting the 7 business days ending {end_day} …")
        data = WD.collect_week(end_day)
        print(f"  active days: {data['active_days']}/7 -> {', '.join(data['active'])}")
        if data["active_days"] < 7:
            missing = [x for x in data["days"] if x not in data["active"]]
            print(f"  NOTE {len(missing)} day(s) had no real traffic: {', '.join(missing)}; "
                  f"averages use active days only.")
        if args.dump_fixture:
            Path(args.dump_fixture).write_text(
                json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"  fixture written: {args.dump_fixture}")

    assess = WD.llm_assessment(data, enabled=not args.no_llm)
    html = WR.render(data, assess)

    out = args.out or os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        f"Product Metrics Report {data['week_start']}_{data['week_end']}.pdf")
    from weasyprint import HTML
    HTML(string=html).write_pdf(out, presentational_hints=True)

    W_ = data["week"]
    print(f"PDF written: {out}")
    print(f"  orders={W_['orders']:,} revenue={W_['revenue']:,.0f} aov={data['aov']:.0f} "
          f"users={W_['people']:,} sessions={W_['sessions']:,}")
    print(f"  cart->checkout={data['cart_to_checkout']:.1f}% "
          f"checkout->order={data['checkout_to_order']:.1f}% "
          f"pay_success={data['pay_success']:.1f}%")
    print(f"  errors={W_['errors']:,} (non-network {data['e_non']:,}) "
          f"payfail={W_['payfail']:,} (sqf {data['sqf']:,}) "
          f"repeat_buyers={data['repeat_rate']:.1f}%")

    if not args.no_discord:
        deliver(out, f"{WR.ar_date(data['week_start'])} – {WR.ar_date(data['week_end'])}",
                dry_run=args.dry_run, to=args.to)


if __name__ == "__main__":
    main()
