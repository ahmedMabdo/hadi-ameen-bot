#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for the evidence-based issue identity/dedup engine.
Covers the brief's required dedup cases + LLM de-escalation + audit persistence.
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import issue_identity  # noqa: E402
import workitems       # noqa: E402


def test_exact_duplicate():
    new = {"title": "checkout crash null pointer", "description": "crash when paying",
           "signature": "NullPointerException", "platform": "Android", "app_version": "8.4.0"}
    existing = [{"id": 111, "title": "checkout crash null pointer", "description": "crash on pay",
                 "signature": "NullPointerException", "platform": "Android", "app_version": "8.4.0"}]
    r = issue_identity.decide(new, existing)
    assert r["decision"] == "DUPLICATE", r
    assert r["matched_existing_issue_id"] == 111


def test_update_existing_when_new_evidence():
    new = {"title": "checkout crash null pointer", "signature": "NullPointerException",
           "platform": "Android", "app_version": "8.4.0", "has_new_evidence": True}
    existing = [{"id": 111, "title": "checkout crash null pointer",
                 "signature": "NullPointerException", "platform": "Android", "app_version": "8.4.0"}]
    assert issue_identity.decide(new, existing)["decision"] == "UPDATE_EXISTING"


def test_semantic_duplicate_two_identity_signals():
    new = {"title": "payment fails at last step", "order_ids": ["A123"],
           "endpoint": "/api/pay", "platform": "iOS"}
    existing = [{"id": 222, "title": "cannot complete order checkout", "order_ids": ["A123"],
                 "endpoint": "/api/pay", "platform": "iOS"}]
    assert issue_identity.decide(new, existing)["decision"] == "DUPLICATE"


def test_unrelated_similar_titles_not_merged():
    new = {"title": "login button not working on profile", "platform": "Android"}
    existing = [{"id": 333, "title": "login button not working on profile", "platform": "iOS"}]
    r = issue_identity.decide(new, existing)
    assert r["decision"] not in ("DUPLICATE", "UPDATE_EXISTING", "SAME"), r
    assert "platform_mismatch" in r["contradicting_evidence"]


def test_same_feature_different_root_cause_needs_review():
    new = {"title": "orders list empty", "release": "8.4.0", "component": "Riders APP",
           "signature": "TimeoutError", "platform": "Android"}
    existing = [{"id": 444, "title": "orders list empty sometimes", "release": "8.4.0",
                 "component": "Riders APP", "signature": "NullPointerException", "platform": "Android"}]
    r = issue_identity.decide(new, existing)
    assert r["decision"] == "NEEDS_REVIEW", r
    assert "signature_mismatch" in r["contradicting_evidence"]


def test_same_crash_signature_merges():
    new = {"title": "cart screen crash on checkout", "signature": "CartException",
           "platform": "Android", "app_version": "8.4.0"}
    existing = [{"id": 555, "title": "cart screen crash on checkout", "signature": "CartException",
                 "platform": "Android", "app_version": "8.4.0"}]
    assert issue_identity.decide(new, existing)["decision"] in ("DUPLICATE", "UPDATE_EXISTING")


def test_different_crash_signature_is_new():
    new = {"title": "random glitch here", "signature": "FooException", "platform": "Android"}
    existing = [{"id": 666, "title": "other unrelated thing", "signature": "BarException",
                 "platform": "Android"}]
    assert issue_identity.decide(new, existing)["decision"] == "NEW"


def test_text_only_similarity_goes_to_review():
    new = {"title": "slow loading on menu page", "platform": "Android"}
    existing = [{"id": 777, "title": "slow loading on menu page", "platform": "Android"}]
    assert issue_identity.decide(new, existing)["decision"] == "NEEDS_REVIEW"


def test_no_candidates_is_new():
    new = {"title": "unique zzzqqq problem"}
    existing = [{"id": 888, "title": "completely different aaa bbb"}]
    assert issue_identity.decide(new, existing)["decision"] == "NEW"


def test_insufficient_info():
    assert issue_identity.decide({}, [])["decision"] == "INSUFFICIENT"


def test_llm_can_only_deescalate():
    new = {"title": "slow loading on menu page", "platform": "Android"}
    existing = [{"id": 777, "title": "slow loading on menu page", "platform": "Android"}]
    fake = lambda prompt: '{"verdict":"NEW","reason":"different screens"}'  # noqa: E731
    assert issue_identity.decide(new, existing, llm=fake)["decision"] == "NEW"
    # an LLM trying to force a merge is ignored (never upgrades)
    merge_llm = lambda prompt: '{"verdict":"DUPLICATE","reason":"looks same"}'  # noqa: E731
    assert issue_identity.decide(new, existing, llm=merge_llm)["decision"] == "NEEDS_REVIEW"


def test_evaluation_is_audited():
    d = tempfile.mkdtemp()
    con = workitems.connect(os.path.join(d, "wi.db"))
    new = {"id": 1, "title": "cart screen crash on checkout", "signature": "CartException"}
    existing = [{"id": 2, "title": "cart screen crash on checkout", "signature": "CartException"}]
    issue_identity.decide(new, existing, persist=True, con=con)
    n = con.execute("SELECT COUNT(*) FROM issue_evaluations").fetchone()[0]
    assert n == 1


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"PASS {fn.__name__}")
    print(f"\n{len(fns)}/{len(fns)} tests passed")


if __name__ == "__main__":
    _run_all()
