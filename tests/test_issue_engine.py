#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the triage<->identity glue (routing buckets). No network."""
import os
import sys
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import issue_engine  # noqa: E402


def test_route_buckets_duplicate_and_new():
    issues = [
        {"title": "cart screen crash on checkout", "description": "CartException",
         "confidence": 0.9, "mids": []},
        {"title": "brand new unrelated zzzqqq request", "description": "", "confidence": 0.9, "mids": []},
    ]
    existing = [{"id": 555, "title": "cart screen crash on checkout", "description": "CartException"}]
    routed = issue_engine.route_issues("chan", issues, existing=existing)
    assert len(routed["create"]) == 1
    assert routed["create"][0]["title"].startswith("brand new")
    assert len(routed["duplicate"]) == 1
    assert routed["duplicate"][0][1]["matched_existing_issue_id"] == 555


def test_route_needs_review_when_text_only():
    issues = [{"title": "slow loading on menu page", "description": "", "confidence": 0.9, "mids": []}]
    existing = [{"id": 777, "title": "slow loading on menu page", "description": ""}]
    routed = issue_engine.route_issues("chan", issues, existing=existing)
    assert len(routed["review"]) == 1
    assert not routed["create"]


def test_empty_existing_all_created():
    issues = [{"title": "anything at all", "description": "x", "confidence": 0.9, "mids": []}]
    routed = issue_engine.route_issues("chan", issues, existing=[])
    assert len(routed["create"]) == 1


def test_apply_updates_dry_run_no_crash():
    upd = [({"title": "dup"}, {"matched_existing_issue_id": 999, "confidence": 0.9, "evidence": ["text"]})]
    asyncio.run(issue_engine.apply_updates(upd, os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                           dry_run=True))


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"PASS {fn.__name__}")
    print(f"\n{len(fns)}/{len(fns)} tests passed")


if __name__ == "__main__":
    _run_all()
