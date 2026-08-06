#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the P3 report generators (pure aggregation from workitems.db)."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import workitems      # noqa: E402
import board_report   # noqa: E402


def _item(wid, state="New", assignee="Ali", pri=2, sev="3 - Medium",
          changed="2026-08-01T10:00:00Z", created="2026-08-01T09:00:00Z"):
    return {"id": wid, "fields": {
        "System.Id": wid, "System.State": state, "System.Title": f"item {wid}",
        "System.WorkItemType": "Bug", "System.AssignedTo": {"displayName": assignee} if assignee else None,
        "Microsoft.VSTS.Common.Priority": pri, "Microsoft.VSTS.Common.Severity": sev,
        "System.ChangedDate": changed, "System.CreatedDate": created,
    }}


def _fresh():
    d = tempfile.mkdtemp()
    return workitems.connect(os.path.join(d, "wi.db"))


def test_daily_board_counts():
    con = _fresh()
    workitems.record_transitions("sprint", [
        _item(1, "New"), _item(2, "Active"), _item(3, "Resolved"),
        _item(4, "Resolved"), _item(5, "Resolved"), _item(6, "Closed"), _item(7, "Active")], con=con)
    D = "2026-08-06"
    workitems.record_transitions("sprint", [
        _item(1, "Active", changed=D + "T09:00:00Z"),
        _item(2, "Resolved", changed=D + "T09:05:00Z"),
        _item(3, "Closed", changed=D + "T09:10:00Z"),           # completed
        _item(4, "Reviewed", changed=D + "T09:15:00Z"),         # QA
        _item(5, "Pending Deployment", changed=D + "T09:20:00Z"),
        _item(6, "Active", changed=D + "T09:25:00Z"),           # regression (Closed->Active)
        _item(7, "Active", assignee="Sara", changed=D + "T09:30:00Z")], con=con)  # assignment
    s = board_report.daily_board(D, con=con)
    assert s["completed"] == 1
    assert s["qa_entered"] == 1
    assert s["regressions"] == 1
    assert s["assignments"] == 1
    assert s["meaningful_updates"] >= 6
    assert "ملخص البورد" in board_report.format_daily(s)


def test_smoke_bc_flags_missing_tester():
    con = _fresh()
    workitems.record_transitions("support", [_item(10, "Reviewed", assignee="")], con=con)
    s = board_report.smoke_bc(con=con)
    assert any("DATA MISSING" in w for w in s["warnings"])
    assert "Smoke + BC" in board_report.format_smoke_bc(s)


def test_weekly_has_health_and_counts():
    con = _fresh()
    workitems.record_transitions("sprint", [_item(1, "Active"), _item(2, "Active")], con=con)
    D = "2026-08-06"
    workitems.record_transitions("sprint", [
        _item(1, "Closed", changed=D + "T09:00:00Z"),
        _item(2, "Resolved", changed=D + "T09:05:00Z")], con=con)
    s = board_report.weekly_engineering(end_date=D, con=con)
    assert s["completed"] == 1
    assert "WorkItems" in s["health"] and "Regressions" in s["health"]
    assert "التقرير الأسبوعي" in board_report.format_weekly(s)


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"PASS {fn.__name__}")
    print(f"\n{len(fns)}/{len(fns)} tests passed")


if __name__ == "__main__":
    _run_all()
