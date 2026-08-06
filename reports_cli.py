#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
reports_cli.py — generate + deliver the Phase 3 engineering reports.

    python reports_cli.py board-daily [--date YYYY-MM-DD] [--dry-run] [--force]
    python reports_cli.py smoke-bc    [--dry-run] [--force]
    python reports_cli.py weekly      [--dry-run] [--force]
    python reports_cli.py release     [--dry-run] [--force]

Each report is gated by its flag in hadi_config (default OFF); --force runs it
manually. Reads the durable workitems.db (filled by the ado_snapshot hook), so
numbers come from SQL — never fabricated. Delivery reuses routines_common.
"""
import sys
import argparse
import datetime

try:
    import env_loader
    env_loader.load_for(__file__)
except Exception:
    pass

import hadi_config
import board_report


def _deliver(channel_kind, text, dry_run):
    ch = hadi_config.channel(channel_kind)
    if dry_run or not ch:
        print(f"[dry-run kind={channel_kind} channel={ch}]\n{text}")
        return 0
    try:
        import routines_common
        ok = routines_common.post_to_channel(ch, text)
        print("posted" if ok else "post failed")
        return 0 if ok else 1
    except Exception as e:  # noqa
        print(f"delivery error: {e}")
        return 1


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    p.add_argument("report", choices=["board-daily", "smoke-bc", "weekly", "release"])
    p.add_argument("--date")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--force", action="store_true", help="run even if the report's flag is off")
    a = p.parse_args()
    date = a.date or datetime.date.today().isoformat()

    if a.report == "board-daily":
        if not (hadi_config.BOARD_REPORT_ENABLED or a.force):
            print("BOARD_REPORT disabled (HADI_BOARD_REPORT=1 or --force)")
            return 0
        s = board_report.daily_board(date)
        return _deliver("board", board_report.format_daily(s), a.dry_run)

    if a.report == "smoke-bc":
        if not (hadi_config.SMOKE_BC_REPORT_ENABLED or a.force):
            print("SMOKE_BC disabled (HADI_SMOKE_BC_REPORT=1 or --force)")
            return 0
        s = board_report.smoke_bc(date)
        return _deliver("smoke_bc", board_report.format_smoke_bc(s), a.dry_run)

    if a.report == "weekly":
        if not (hadi_config.BOARD_REPORT_ENABLED or a.force):
            print("weekly gated by HADI_BOARD_REPORT (or --force)")
            return 0
        s = board_report.weekly_engineering(end_date=date)
        return _deliver("weekly", board_report.format_weekly(s), a.dry_run)

    if a.report == "release":
        if not (hadi_config.RELEASE_REPORT_ENABLED or a.force):
            print("RELEASE_REPORT disabled (HADI_RELEASE_REPORT=1 or --force)")
            return 0
        s = board_report.release_digest(end_date=date)
        return _deliver("release", board_report.format_release(s), a.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
