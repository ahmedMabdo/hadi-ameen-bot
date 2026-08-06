#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
change_classifier.py — turn a single ADO field change into a typed, meaningful
lifecycle event.

Pure functions, no I/O. Used by workitems.record_transitions() to label each
detected diff. The state->category mapping comes from hadi_config (config-driven).

event_type ∈ {
  STATUS_CHANGE, ASSIGNMENT_CHANGE, PRIORITY_CHANGE, SEVERITY_CHANGE,
  QA_UPDATE, RELEASE_UPDATE, RELEASE, BLOCKER, REGRESSION,
  MEANINGFUL_UPDATE, NOISE
}
`meaningful` is False for NOISE-class changes so downstream reporting can filter
API churn (e.g. a bare Description tweak) without dropping real signal.
"""
import hadi_config


def _tags(raw):
    return {t.strip().lower() for t in (raw or "").split(";") if t.strip()}


def _tag_newly_contains(old, new, needle):
    return needle in _tags(new) and needle not in _tags(old)


def classify(field, old_value, new_value):
    """Return (event_type, meaningful, extra_dict) for one field change.

    `extra_dict` may carry {'old_cat','new_cat','regression'} for state changes.
    """
    field = field or ""

    if field == "System.State":
        oc = hadi_config.state_category(old_value)
        nc = hadi_config.state_category(new_value)
        regression = hadi_config.is_backward(oc, nc)
        if regression:
            et = "REGRESSION"          # reopened / moved backwards
        elif nc == "qa":
            et = "QA_UPDATE"
        elif nc == "ready_release":
            et = "RELEASE_UPDATE"
        elif nc == "released":
            et = "RELEASE"
        else:
            et = "STATUS_CHANGE"
        return et, True, {"old_cat": oc, "new_cat": nc, "regression": regression}

    if field == "System.AssignedTo":
        return "ASSIGNMENT_CHANGE", True, {}

    if field == "Microsoft.VSTS.Common.Priority":
        return "PRIORITY_CHANGE", True, {}

    if field == "Microsoft.VSTS.Common.Severity":
        return "SEVERITY_CHANGE", True, {}

    if field == "System.Tags":
        if _tag_newly_contains(old_value, new_value, "blocked"):
            return "BLOCKER", True, {}
        return "MEANINGFUL_UPDATE", False, {}   # other tag churn = low signal

    if field in ("System.Title", "System.IterationPath"):
        return "MEANINGFUL_UPDATE", True, {}

    # Description / board column / everything else = noise for reporting
    return "NOISE", False, {}


# Fields we diff for transitions (order defines event emission priority).
TRACKED_FIELDS = (
    "System.State",
    "System.AssignedTo",
    "Microsoft.VSTS.Common.Priority",
    "Microsoft.VSTS.Common.Severity",
    "System.Tags",
    "System.IterationPath",
    "System.Title",
)
