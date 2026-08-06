#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
hadi_config.py — central, env-driven configuration for the work-item lifecycle,
issue-evaluation engine and new reports (Phase 2/3).

Design goals:
  * All thresholds / flags / paths live HERE, never buried in random modules.
  * Every new behaviour is OFF by default (feature flags) so nothing changes in
    production until explicitly enabled.
  * The ADO state -> lifecycle-stage map is CONFIG-DRIVEN (never hardcoded in
    logic). Populate it from the real board with:
        python ado_cli.py get-work-item-type Issue
    then override via env HADI_STATE_CATEGORIES (JSON) or a state_categories.json
    file next to this module.

No side effects on import beyond reading .env (same loader ado_client uses).
"""
import os
import json

try:  # read .env like the rest of the codebase (env_loader.load_for)
    import env_loader
    env_loader.load_for(__file__)
except Exception:  # config must never hard-fail on import
    pass

_HERE = os.path.dirname(os.path.abspath(__file__))


# --------------------------------------------------------------------------
# small typed env helpers
# --------------------------------------------------------------------------
def _bool(name, default=False):
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on", "y")


def _float(name, default):
    try:
        return float(os.getenv(name, ""))
    except (TypeError, ValueError):
        return float(default)


def _int(name, default):
    try:
        return int(float(os.getenv(name, "")))
    except (TypeError, ValueError):
        return int(default)


def _hours(name, default):
    """Accepts '24' or '24h' -> 24 (int hours)."""
    raw = (os.getenv(name) or "").strip().lower().rstrip("h")
    try:
        return int(float(raw))
    except (TypeError, ValueError):
        return int(default)


# --------------------------------------------------------------------------
# feature flags (all OFF by default — nothing changes in prod until enabled)
# --------------------------------------------------------------------------
ISSUE_ENGINE_ENABLED = _bool("HADI_ISSUE_ENGINE", False)
LIFECYCLE_TRACKING_ENABLED = _bool("HADI_LIFECYCLE_TRACKING", True)  # passive read-only event log; safe on
BOARD_REPORT_ENABLED = _bool("HADI_BOARD_REPORT", False)
SMOKE_BC_REPORT_ENABLED = _bool("HADI_SMOKE_BC_REPORT", False)
RELEASE_REPORT_ENABLED = _bool("HADI_RELEASE_REPORT", False)
SEQ_MONITOR_ENABLED = _bool("HADI_SEQ_MONITOR", False)
CRASHLYTICS_MONITOR_ENABLED = _bool("HADI_CRASHLYTICS_MONITOR", False)


# --------------------------------------------------------------------------
# thresholds / windows (all overridable)
# --------------------------------------------------------------------------
ISSUE_MERGE_THRESHOLD = _float("ISSUE_MERGE_THRESHOLD", 0.85)
ISSUE_DUPLICATE_THRESHOLD = _float("ISSUE_DUPLICATE_THRESHOLD", 0.90)
ISSUE_REVIEW_THRESHOLD = _float("ISSUE_REVIEW_THRESHOLD", 0.60)
ISSUE_MIN_SIGNALS_FOR_AUTOMERGE = _int("ISSUE_MIN_SIGNALS_FOR_AUTOMERGE", 2)
STALE_WORK_ITEM_HOURS = _int("STALE_WORK_ITEM_HOURS", 48)
ADO_REVISIONS_POLL_MIN = _int("ADO_REVISIONS_POLL_MIN", 5)
POST_RELEASE_MONITORING_WINDOW_HOURS = _hours("POST_RELEASE_MONITORING_WINDOW", 24)
CRASH_REGRESSION_THRESHOLD = _float("CRASH_REGRESSION_THRESHOLD", 0.2)   # pp drop in crash-free
SEQ_ERROR_REGRESSION_THRESHOLD = _float("SEQ_ERROR_REGRESSION_THRESHOLD", 0.5)  # pp rise in error rate
EVALUATION_VERSION = os.getenv("HADI_EVAL_VERSION", "2.0")

WEEKLY_REPORT_DAY = os.getenv("WEEKLY_REPORT_DAY", "Thu")
SMOKE_BC_REPORT_DAY = os.getenv("SMOKE_BC_REPORT_DAY", "Wed")


# --------------------------------------------------------------------------
# storage
# --------------------------------------------------------------------------
WORKITEMS_DB = os.getenv("WORKITEMS_DB", os.path.join(_HERE, "workitems.db"))


# --------------------------------------------------------------------------
# ADO state -> canonical lifecycle stage (CONFIG-DRIVEN, override before prod)
# --------------------------------------------------------------------------
# Canonical stages, in lifecycle order:
CATEGORY_ORDER = [
    "new", "triage", "active", "dev_done", "qa",
    "ready_release", "released", "closed", "rejected", "unknown",
]

# Default map from states OBSERVED in the repo + the Discord screenshot.
# NOT authoritative — confirm with `ado_cli.py get-work-item-type Issue` and
# override via HADI_STATE_CATEGORIES / state_categories.json.
DEFAULT_STATE_CATEGORIES = {
    "new": "new", "proposed": "new",
    "acknowledged": "triage", "approved": "triage", "feedback": "triage",
    "reviewed": "qa",  # post-dev review (unconfirmed — verify with get-work-item-type)
    "active": "active", "in progress": "active", "committed": "active", "doing": "active",
    "resolved": "dev_done",
    "testing": "qa", "in test": "qa", "qa": "qa", "bc": "qa", "smoke": "qa",
    "ready for qa": "qa",
    "pending deployment": "ready_release", "ready for release": "ready_release",
    "ready to deploy": "ready_release",
    "deployed": "released", "released": "released", "done": "released",
    "closed": "closed", "solved": "closed", "completed": "closed", "accepted": "closed",
    "rejected": "rejected", "removed": "rejected",
}


def _load_state_categories():
    raw = os.getenv("HADI_STATE_CATEGORIES")
    if raw:
        try:
            return {str(k).strip().lower(): v for k, v in json.loads(raw).items()}
        except Exception:
            pass
    p = os.path.join(_HERE, "state_categories.json")
    if os.path.exists(p):
        try:
            with open(p, encoding="utf-8") as f:
                return {str(k).strip().lower(): v for k, v in json.load(f).items()}
        except Exception:
            pass
    return dict(DEFAULT_STATE_CATEGORIES)


STATE_CATEGORIES = _load_state_categories()


def state_category(state):
    """Map a raw ADO state name to a canonical stage. 'unknown' if unmapped
    (never invents a stage — unknown states are surfaced, not guessed)."""
    if not state:
        return "unknown"
    return STATE_CATEGORIES.get(str(state).strip().lower(), "unknown")


def category_rank(category):
    try:
        return CATEGORY_ORDER.index(category)
    except ValueError:
        return CATEGORY_ORDER.index("unknown")


def is_backward(old_category, new_category):
    """True ONLY for a genuine reopen / rollback: from a LATE stage
    (ready_release / released / closed) back to an earlier progress stage.
    Deliberately conservative so ambiguous mid-stages (e.g. an unconfirmed
    'Reviewed' mapping) are never mislabelled as regressions."""
    late = {"ready_release", "released", "closed"}
    prog = {"new", "triage", "active", "dev_done", "qa", "ready_release", "released", "closed"}
    if old_category not in late or new_category not in prog:
        return False
    return category_rank(new_category) < category_rank(old_category)


# --------------------------------------------------------------------------
# Discord channel routing (IDs from env; fall back to existing channels)
# --------------------------------------------------------------------------
def channel(kind):
    routing = {
        "board": os.getenv("BOARD_CHANNEL_ID") or os.getenv("PO_CHANNEL_ID"),
        "smoke_bc": os.getenv("SMOKE_BC_CHANNEL_ID") or os.getenv("MARS_CHANNEL_ID"),
        "release": os.getenv("RELEASE_CHANNEL_ID") or os.getenv("PO_CHANNEL_ID"),
        "weekly": os.getenv("WEEKLY_REPORT_CHANNEL_ID") or os.getenv("PO_CHANNEL_ID"),
        "review": (os.getenv("ISSUE_REVIEW_CHANNEL_ID") or os.getenv("ISSUES_CHANNEL_ID")
                   or os.getenv("SUPPORT_CHANNEL_ID")),
    }
    return routing.get(kind)


if __name__ == "__main__":
    # quick introspection: `python hadi_config.py`
    print(json.dumps({
        "flags": {
            "ISSUE_ENGINE_ENABLED": ISSUE_ENGINE_ENABLED,
            "LIFECYCLE_TRACKING_ENABLED": LIFECYCLE_TRACKING_ENABLED,
        },
        "thresholds": {
            "ISSUE_MERGE_THRESHOLD": ISSUE_MERGE_THRESHOLD,
            "ISSUE_DUPLICATE_THRESHOLD": ISSUE_DUPLICATE_THRESHOLD,
            "ISSUE_REVIEW_THRESHOLD": ISSUE_REVIEW_THRESHOLD,
        },
        "workitems_db": WORKITEMS_DB,
        "state_categories_loaded": len(STATE_CATEGORIES),
    }, ensure_ascii=False, indent=2))
