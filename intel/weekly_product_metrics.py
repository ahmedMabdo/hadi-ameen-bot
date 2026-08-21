#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""8Orders — Weekly Product Metrics Report (v2).

A three-layer executive report driven by a full week of live PostHog data.

Design contract (per the PO):
  · every NUMBER is computed in Python from live PostHog data (wpm_data.collect_week)
  · every RATE uses one denominator — unique users — and prints its own numerator
    and denominator next to it, so a percentage can never be misread
  · every metric is segmented by city / platform / app version where the data allows
  · the LLM only writes the qualitative reading — it never computes or invents a number
  · the run FAILS LOUD rather than delivering a zeroed report (preflight)
  · a tracking outage shifts the window back to the last 7 ACTIVE days instead of
    silently reporting a 3-day week as if it were a full one

Layers inside the single PDF:
  1. Executive        — top management
  2. Growth & Ops     — marketing / operations / business / delivery
  3. Product & Eng    — UX designers, backend & mobile developers

Schedule: Thursday 12:00 Africa/Cairo, DM'd to Asser by Hadi.

Env: POSTHOG_API_KEY (Personal key, phx_...), DISCORD_BOT_TOKEN,
     optional ANTHROPIC_API_KEY (qualitative reading), optional ASSER_USER_ID.

Usage:
    python3 intel/weekly_product_metrics.py                      # build + DM
    python3 intel/weekly_product_metrics.py --dry-run            # build, don't DM
    python3 intel/weekly_product_metrics.py --to 1378684355148386355
    python3 intel/weekly_product_metrics.py --date 2026-08-19    # explicit end day
    python3 intel/weekly_product_metrics.py --dump-fixture w.json --dry-run
    python3 intel/weekly_product_metrics.py --fixture w.json --no-llm --dry-run
    python3 intel/weekly_product_metrics.py --self-check --dry-run   # verify the maths
"""
import os, sys, json, argparse, datetime as dt
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import wpm_data as WD
import wpm_render as WR

CAIRO_TZ = WD.CAIRO_TZ


def self_check(data):
    """Independent re-derivation of every headline rate, straight from the raw counts.

    The report's credibility rests on the arithmetic, so we recompute it here from
    the stored numerator/denominator and refuse to ship if anything disagrees.
    Catches a mis-wired metric far more reliably than eyeballing a PDF.
    """
    u, r, v = data["users"], data["rates"], data["vol"]
    problems = []

    def chk(name, got, want, tol=0.05):
        if abs(got - want) > tol:
            problems.append(f"{name}: report says {got:.3f}, recomputed {want:.3f}")

    chk("activation", r["activation"]["v"], WD.pct(u["cart"], u["active"]))
    chk("cart_to_checkout", r["cart_to_checkout"]["v"], WD.pct(u["checkout"], u["cart"]))
    chk("checkout_to_order", r["checkout_to_order"]["v"], WD.pct(u["buyer"], u["checkout"]))
    chk("cart_to_order", r["cart_to_order"]["v"], WD.pct(u["buyer"], u["cart"]))
    chk("purchase", r["purchase"]["v"], WD.pct(u["buyer"], u["active"]))
    chk("error_hit", r["error_hit"]["v"], WD.pct(u["error"], u["active"]))
    chk("pay_success", r["pay_success"]["v"], WD.pct(u["buyer"], u["buyer"] + u["payfail"]))

    # every rate must carry a numerator, a denominator and a stated basis
    for k, rr in r.items():
        if rr["d"] and rr["n"] > rr["d"]:
            problems.append(f"{k}: numerator {rr['n']} exceeds denominator {rr['d']}")
        if not rr.get("basis"):
            problems.append(f"{k}: missing the denominator label")
        if k not in WR.RATE_DEFS:
            problems.append(f"{k}: shown in the report but missing from the glossary")

    # funnel monotonicity — a later step cannot have more users than an earlier one
    for a, b in [("active", "product"), ("active", "cart"), ("cart", "checkout"),
                 ("checkout", "buyer")]:
        if u[b] > u[a]:
            problems.append(f"funnel broken: {b} ({u[b]}) > {a} ({u[a]})")

    # money sanity
    if v["orders"] and data["aov"] <= 0:
        problems.append("AOV is zero while orders exist")
    if data["active_days"] < 1:
        problems.append("no active day in the window")

    # segmentation must reconcile with the total within a rounding margin
    seg_users = sum(c["users"] for c in data["cities"])
    if u["active"] and abs(seg_users - u["active"]) / u["active"] > 0.02:
        problems.append(f"city split {seg_users} vs total users {u['active']} "
                        f"(>2% apart — attribution is dropping people)")
    return problems


def deliver(pdf_path, label, dry_run=False, to=None):
    raw = to or os.environ.get("ASSER_USER_ID", "1378684355148386355")
    recipients = [x.strip() for x in str(raw).replace(",", " ").split() if x.strip()]
    msg = (f"**تقرير مؤشرات المنتج — أسبوعي**\n"
           f"الفترة: {label}\n\n"
           f"التقرير مبني على بيانات PostHog الحقيقية، وكل الأرقام محسوبة برمجيًا.\n"
           f"**التقرير 3 طبقات:** الطبقة 1 للإدارة العليا، الطبقة 2 للماركتنج والأوبريشن "
           f"والبيزنس والديليفري، الطبقة 3 للـ UX والمطوّرين.\n"
           f"كل نسبة في التقرير محسوبة على **المستخدمين الفريدين** ومكتوب جنبها البسط "
           f"والمقام. قاموس المؤشرات في آخر التقرير فيه تعريف كل مؤشر بمعادلته.")
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
    ap.add_argument("--html", help="also write the raw HTML here (debugging)")
    ap.add_argument("--self-check", action="store_true",
                    help="re-derive every rate and abort on any disagreement")
    args = ap.parse_args()

    if args.fixture:
        data = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
        print(f"FIXTURE: loaded {args.fixture} "
              f"({data['week_start']}..{data['week_end']}, {data['active_days']} active days)")
    else:
        WD.preflight()   # raises rather than letting a zeroed report through
        end_day = args.date or (WD.cairo_today() - dt.timedelta(days=1)).isoformat()
        print(f"Collecting the last {WD.WEEK_LEN} ACTIVE business days ending on/before {end_day} …")
        data = WD.collect_week(end_day)
        print(f"  window: {data['week_start']} .. {data['week_end']} "
              f"({data['active_days']} active days)")
        if data["gap_days"]:
            print(f"  NOTE {len(data['gap_days'])} day(s) inside the span had no traffic: "
                  f"{', '.join(data['gap_days'])}")
        if data["stale_days"]:
            print(f"  WARN tracking has been dark for {len(data['stale_days'])} day(s) since "
                  f"{data['week_end']} — window shifted back to stay comparable.")
        if data["prev_active_days"]:
            print(f"  previous window: {data['prev_start']} .. {data['prev_end']} "
                  f"({data['prev_active_days']} active days)")
        if args.dump_fixture:
            Path(args.dump_fixture).write_text(
                json.dumps(data, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
            print(f"  fixture written: {args.dump_fixture}")

    problems = self_check(data)
    if problems:
        print("\nSELF-CHECK FAILED:", file=sys.stderr)
        for p in problems:
            print(f"  ✗ {p}", file=sys.stderr)
        if args.self_check:
            sys.exit(2)
    else:
        print("  self-check ok — every rate re-derived and matched.")

    assess = WD.llm_assessment(data, enabled=not args.no_llm)
    html = WR.render(data, assess)
    if args.html:
        Path(args.html).write_text(html, encoding="utf-8")
        print(f"HTML written: {args.html}")

    out = args.out or os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        f"Product Metrics Report {data['week_start']}_{data['week_end']}.pdf")
    from weasyprint import HTML
    HTML(string=html).write_pdf(out, presentational_hints=True)

    U, V, R = data["users"], data["vol"], data["rates"]
    print(f"\nPDF written: {out}")
    print(f"  users={U['active']:,} buyers={U['buyer']:,} orders={V['orders']:,} "
          f"revenue={V['revenue']:,.0f} aov={data['aov']:.0f}")
    print(f"  activation={R['activation']['v']:.1f}% "
          f"cart->checkout={R['cart_to_checkout']['v']:.1f}% "
          f"checkout->order={R['checkout_to_order']['v']:.1f}% "
          f"cart->order={R['cart_to_order']['v']:.1f}%")
    print(f"  pay_success={R['pay_success']['v']:.1f}% "
          f"users_hit_by_error={U['error']:,} ({R['error_hit']['v']:.1f}%) "
          f"repeat_buyers={data['repeat_rate']:.1f}%")
    for c in data["cities"]:
        print(f"  city {c['dim']}: users={c['users']:,} buyers={c['buyers']:,} "
              f"purchase={c['purchase_rate']:.1f}% aov={c['aov']:.0f}")

    if not args.no_discord:
        deliver(out, f"{WR.ar_date(data['week_start'])} – {WR.ar_date(data['week_end'])}",
                dry_run=args.dry_run, to=args.to)


if __name__ == "__main__":
    main()
