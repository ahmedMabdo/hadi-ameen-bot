#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the pure post-release assessment logic."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import monitoring  # noqa: E402


def test_improved():
    r = monitoring.assess(98.7, 99.2, higher_better=True, regress_threshold=0.2)
    assert r["status"] == "IMPROVED" and r["delta"] == 0.5


def test_regressed_error_rate():
    r = monitoring.assess(0.42, 1.13, higher_better=False, regress_threshold=0.5)
    assert r["status"] == "REGRESSED"


def test_critical_regression():
    r = monitoring.assess(99.0, 96.5, higher_better=True, regress_threshold=0.5)
    assert r["status"] == "CRITICAL_REGRESSION"


def test_stable():
    assert monitoring.assess(99.0, 99.05, higher_better=True, regress_threshold=0.2)["status"] == "STABLE"


def test_insufficient():
    assert monitoring.assess(None, 99.0)["status"] == "INSUFFICIENT_DATA"
    assert monitoring.assess(99.0, None)["status"] == "INSUFFICIENT_DATA"


def test_baseline_median_top7():
    assert monitoring.baseline([1, 2, 3, 4, 5, 6, 7, 8, 9]) == 6  # top7=3..9, median 6
    assert monitoring.baseline([]) is None


def test_release_compare():
    before = {"crash_free_users": 99.0, "seq_error_rate": 0.4}
    after = {"crash_free_users": 99.3, "seq_error_rate": 1.5}
    out = monitoring.release_compare(before, after)
    assert out["crash_free_users"]["status"] == "IMPROVED"
    assert out["seq_error_rate"]["status"] in ("REGRESSED", "CRITICAL_REGRESSION")


def test_monitors_unconfigured_by_default():
    assert monitoring.fetch_seq_signal("x")["configured"] is False
    assert monitoring.fetch_crashlytics_metrics()["configured"] is False


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"PASS {fn.__name__}")
    print(f"\n{len(fns)}/{len(fns)} tests passed")


if __name__ == "__main__":
    _run_all()
