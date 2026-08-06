#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for the work-item lifecycle store (Phase 2/3 — P0+P1).

Covers: cold-start seeding, state-transition detection, the exact "Resolved ->
Pending Deployment / Closed / Reviewed today" question from the Discord thread,
idempotency (same event Nx -> once), restart recovery, and assignment/priority/
severity change events. Runnable directly (`python tests/test_workitems.py`) or
via pytest.
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import workitems          # noqa: E402
import change_classifier  # noqa: E402
import issue_matrix       # noqa: E402
import hadi_config        # noqa: E402


def _item(wid, state="New", assignee="Ali", pri=2, sev="3 - Medium",
          changed="2026-08-06T10:00:00Z", title="issue title"):
    return {"id": wid, "fields": {
        "System.Id": wid, "System.State": state, "System.Title": title,
        "System.WorkItemType": "Bug",
        "System.AssignedTo": {"displayName": assignee},
        "Microsoft.VSTS.Common.Priority": pri,
        "Microsoft.VSTS.Common.Severity": sev,
        "System.ChangedDate": changed, "System.CreatedDate": "2026-08-01T09:00:00Z",
    }}


def _fresh():
    d = tempfile.mkdtemp()
    path = os.path.join(d, "wi.db")
    return workitems.connect(path), path


def test_cold_start_seeds_silently():
    con, _ = _fresh()
    s = workitems.record_transitions("sprint", [_item(1, "New"), _item(2, "Resolved")], con=con)
    assert s["seeded"] is True
    assert s["events"] == 0, "cold start must not emit change events for pre-existing items"
    assert len(workitems.all_work_items(con=con)) == 2


def test_status_transition_detected():
    con, _ = _fresh()
    workitems.record_transitions("sprint", [_item(1, "New")], con=con)          # seed
    s = workitems.record_transitions("sprint", [_item(1, "Active", changed="2026-08-06T11:00:00Z")], con=con)
    assert s["events"] == 1
    evs = workitems.status_transitions(con=con)
    assert len(evs) == 1
    assert evs[0]["previous_value"] == "New" and evs[0]["new_value"] == "Active"


def test_ghada_question_resolved_to_pending_closed_reviewed():
    con, _ = _fresh()
    # seed: four items currently Resolved / New
    workitems.record_transitions("support", [
        _item(1, "Resolved"), _item(2, "Resolved"), _item(3, "Resolved"), _item(4, "New")], con=con)
    # today they move
    workitems.record_transitions("support", [
        _item(1, "Pending Deployment", changed="2026-08-06T12:00:00Z"),
        _item(2, "Closed", changed="2026-08-06T12:05:00Z"),
        _item(3, "Reviewed", changed="2026-08-06T12:10:00Z"),
        _item(4, "Active", changed="2026-08-06T12:15:00Z"),
    ], con=con)
    pend_closed = workitems.count_status_transitions(
        on_date="2026-08-06", from_state="Resolved",
        to_states=["Pending Deployment", "Closed"], con=con)
    reviewed = workitems.count_status_transitions(
        on_date="2026-08-06", from_state="Resolved", to_states=["Reviewed"], con=con)
    assert pend_closed == 2, f"expected 2 Resolved->Pending/Closed, got {pend_closed}"
    assert reviewed == 1, f"expected 1 Resolved->Reviewed, got {reviewed}"


def test_idempotent_same_batch_5x():
    con, _ = _fresh()
    workitems.record_transitions("sprint", [_item(1, "New")], con=con)
    batch = [_item(1, "Active", changed="2026-08-06T11:00:00Z")]
    for _ in range(5):
        workitems.record_transitions("sprint", batch, con=con)
    assert len(workitems.status_transitions(con=con)) == 1, "same change 5x must produce ONE event"


def test_restart_recovery():
    con, path = _fresh()
    workitems.record_transitions("sprint", [_item(1, "New")], con=con)
    workitems.record_transitions("sprint", [_item(1, "Active", changed="2026-08-06T11:00:00Z")], con=con)
    con.close()
    con2 = workitems.connect(path)                       # simulate restart
    workitems.record_transitions("sprint", [_item(1, "Active", changed="2026-08-06T11:00:00Z")], con=con2)
    assert len(workitems.status_transitions(con=con2)) == 1, "no duplicate after restart"


def test_assignment_priority_severity_events():
    con, _ = _fresh()
    workitems.record_transitions("sprint", [_item(1, "Active", assignee="Ali", pri=2, sev="3 - Medium")], con=con)
    workitems.record_transitions("sprint", [_item(1, "Active", assignee="Sara", pri=1, sev="2 - High",
                                                   changed="2026-08-06T13:00:00Z")], con=con)
    types = {e["event_type"] for e in workitems.events(con=con)}
    assert {"ASSIGNMENT_CHANGE", "PRIORITY_CHANGE", "SEVERITY_CHANGE"} <= types, types


def test_change_classifier_labels():
    assert change_classifier.classify("System.State", "Closed", "Active")[0] == "REGRESSION"
    assert change_classifier.classify("System.State", "New", "Active")[0] == "STATUS_CHANGE"
    assert change_classifier.classify("System.State", "Resolved", "Pending Deployment")[0] == "RELEASE_UPDATE"
    assert change_classifier.classify("System.State", "Resolved", "Reviewed")[0] == "QA_UPDATE"
    assert change_classifier.classify("System.Description", "a", "b")[0] == "NOISE"
    assert hadi_config.state_category("Pending Deployment") == "ready_release"


def test_issue_matrix():
    r = issue_matrix.classify("2 - High")
    assert r["priority"] == 1 and r["sla_days"] == 1 and r["severity"] == "High"
    assert issue_matrix.classify("totally unknown")["missing"] is True
    assert issue_matrix.normalize_severity("عاجل") == "Urgent"


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        fn()
        print(f"PASS {fn.__name__}")
        passed += 1
    print(f"\n{passed}/{len(fns)} tests passed")


if __name__ == "__main__":
    _run_all()
