#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
monitoring.py — post-release health/regression layer (Phase 4).

`assess()` and `baseline()` are PURE and unit-tested — the before/after
comparison that decides IMPROVED / STABLE / REGRESSED / CRITICAL_REGRESSION /
INSUFFICIENT_DATA, never claiming improvement without data.

Seq / Crashlytics fetchers are network skeletons, gated behind config + flags.
They return {"configured": False} until creds are supplied, so nothing runs (or
fabricates) without them. NOT VERIFIED without live Seq/Crashlytics access.
"""
import os

import hadi_config

IMPROVED = "IMPROVED"
STABLE = "STABLE"
REGRESSED = "REGRESSED"
CRITICAL = "CRITICAL_REGRESSION"
INSUFFICIENT = "INSUFFICIENT_DATA"


def baseline(series):
    """Median of the top-7 of the most recent 30 daily values (mirrors the
    existing PostHog baseline idea). Pure. None if empty."""
    vals = [v for v in (series or []) if v is not None]
    if not vals:
        return None
    recent = vals[-30:]
    top = sorted(recent, reverse=True)[:7]
    top.sort()
    n = len(top)
    return top[n // 2] if n % 2 else (top[n // 2 - 1] + top[n // 2]) / 2.0


def assess(before, after, higher_better=True, regress_threshold=0.5, improve_threshold=None):
    """Compare a metric before vs after a release. `regress_threshold` and
    `improve_threshold` are in the metric's own units (e.g. percentage points).
    Returns {status, delta, before, after}."""
    if before is None or after is None:
        return {"status": INSUFFICIENT, "delta": None, "before": before, "after": after}
    improve_threshold = regress_threshold if improve_threshold is None else improve_threshold
    delta = after - before
    signed = delta if higher_better else -delta   # >0 => better
    if signed >= improve_threshold:
        status = IMPROVED
    elif signed <= -2 * regress_threshold:
        status = CRITICAL
    elif signed <= -regress_threshold:
        status = REGRESSED
    else:
        status = STABLE
    return {"status": status, "delta": round(delta, 4), "before": before, "after": after}


def release_compare(before, after):
    """Compare a dict of {metric: value} before vs after with per-metric
    direction/threshold config. Returns {metric: assess(...)}."""
    specs = {
        "crash_free_users": (True, hadi_config.CRASH_REGRESSION_THRESHOLD),
        "crash_free_sessions": (True, hadi_config.CRASH_REGRESSION_THRESHOLD),
        "seq_error_rate": (False, hadi_config.SEQ_ERROR_REGRESSION_THRESHOLD),
        "error_rate": (False, hadi_config.SEQ_ERROR_REGRESSION_THRESHOLD),
    }
    out = {}
    for metric, (higher_better, thr) in specs.items():
        if metric in before or metric in after:
            out[metric] = assess(before.get(metric), after.get(metric),
                                  higher_better=higher_better, regress_threshold=thr)
    return out


# --------------------------------------------------------------------------
# Seq — network skeleton (NOT VERIFIED without SEQ_URL/SEQ_API_KEY)
# --------------------------------------------------------------------------
def seq_configured():
    return bool(os.getenv("SEQ_URL") and os.getenv("SEQ_API_KEY"))


def fetch_seq_signal(signal_filter, window_minutes=60):
    """Count Seq events matching `signal_filter` over the window. Returns
    {"configured": bool, "count": int|None}. NOT VERIFIED."""
    if not seq_configured():
        return {"configured": False, "count": None, "reason": "SEQ_URL/SEQ_API_KEY not set"}
    import requests
    base = os.getenv("SEQ_URL").rstrip("/")
    headers = {"X-Seq-ApiKey": os.getenv("SEQ_API_KEY")}
    try:
        r = requests.get(f"{base}/api/events/signal",
                         params={"filter": signal_filter, "count": 1000,
                                 "range": f"{window_minutes}m"},
                         headers=headers, timeout=30)
        r.raise_for_status()
        events = r.json().get("Events", r.json()) if isinstance(r.json(), dict) else r.json()
        return {"configured": True, "count": len(events) if isinstance(events, list) else None}
    except Exception as e:  # noqa
        return {"configured": True, "count": None, "error": str(e)}


# --------------------------------------------------------------------------
# Crashlytics — no official REST API; via Firebase/BigQuery export
# --------------------------------------------------------------------------
def crashlytics_configured():
    return bool(os.getenv("CRASHLYTICS_PROJECT"))


def fetch_crashlytics_metrics(release=None):
    """Crash-free users/sessions, crash count, affected users, new/regressed
    signatures — sourced from the Firebase Crashlytics BigQuery export. Skeleton:
    returns {"configured": False} until the export + creds are wired. NOT VERIFIED."""
    if not crashlytics_configured():
        return {"configured": False, "reason": "CRASHLYTICS_PROJECT not set (needs BigQuery export)"}
    # Intentionally not fabricating numbers without a real data source.
    return {"configured": True, "metrics": None,
            "reason": "BigQuery export client not wired in this build"}
