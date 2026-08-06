#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the authoritative revisions path (pure, no network)."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ado_updates   # noqa: E402
import workitems     # noqa: E402


def _rev(wid, rev, state, assignee="Ali", changed=None):
    return {"id": wid, "rev": rev, "fields": {
        "System.Id": wid, "System.State": state,
        "System.AssignedTo": {"displayName": assignee},
        "System.ChangedDate": changed or f"2026-08-06T1{rev}:00:00Z",
        "System.ChangedBy": {"displayName": "Dev"}, "System.Rev": rev,
    }}


def _fresh():
    d = tempfile.mkdtemp()
    return workitems.connect(os.path.join(d, "wi.db"))


def test_revisions_to_events_diffs_consecutive():
    revs = [_rev(1, 1, "New"), _rev(1, 2, "Active"), _rev(1, 3, "Resolved")]
    rows = ado_updates.revisions_to_events(revs)
    state_rows = [r for r in rows if r["field"] == "System.State"]
    assert len(state_rows) == 2                              # New->Active, Active->Resolved
    assert (state_rows[0]["old"], state_rows[0]["new"]) == ("New", "Active")
    assert (state_rows[1]["old"], state_rows[1]["new"]) == ("Active", "Resolved")


def test_revisions_capture_intra_interval_transitions():
    # snapshot-diff would only see New->Resolved; revisions keep the Active step
    revs = [_rev(1, 1, "New"), _rev(1, 2, "Active"), _rev(1, 3, "Resolved")]
    con = _fresh()
    workitems.ingest_revisions("ado", ado_updates.revisions_to_events(revs), con=con)
    states = [(e["previous_value"], e["new_value"])
              for e in workitems.status_transitions(con=con)]
    assert ("New", "Active") in states and ("Active", "Resolved") in states


def test_ingest_revisions_idempotent():
    revs = [_rev(1, 1, "New"), _rev(1, 2, "Active")]
    rows = ado_updates.revisions_to_events(revs)
    con = _fresh()
    workitems.ingest_revisions("ado", rows, con=con)
    res2 = workitems.ingest_revisions("ado", rows, con=con)
    assert res2["events"] == 0                               # already ingested


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"PASS {fn.__name__}")
    print(f"\n{len(fns)}/{len(fns)} tests passed")


if __name__ == "__main__":
    _run_all()
