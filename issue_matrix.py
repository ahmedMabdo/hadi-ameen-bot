#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
issue_matrix.py — the Issue Management Priority Matrix from the team's Google
Sheet, encoded as machine-readable classification config.

Sheet (gid=205142931): Platform x Severity -> SLA + Priority.
  Urgent  -> immediately / same day (top priority)
  High    -> 1 working day  -> Priority 1
  Medium  -> 3 working days -> Priority 3
  Low     -> 5 working days -> Priority 5

This is the CLASSIFICATION half of the evaluation engine (severity/priority/SLA).
The identity/dedup half lives in issue_identity.py.
"""

PLATFORMS = [
    "Platform Admin Panel",
    "Admin Panel",
    "Customer APP",
    "Riders APP",
    "Merchant OPS Web",
    "Merchants OPS APP",
]

# canonical severity -> SLA + ADO priority
SEVERITY_SLA = {
    "Urgent": {"sla_days": 0, "priority": 1, "sla_label": "immediately / same day"},
    "High":   {"sla_days": 1, "priority": 1, "sla_label": "1 working day"},
    "Medium": {"sla_days": 3, "priority": 3, "sla_label": "3 working days"},
    "Low":    {"sla_days": 5, "priority": 5, "sla_label": "5 working days"},
}

# raw ADO / free-text severity -> canonical. ADO Severity fields look like
# "1 - Critical" / "2 - High" / "3 - Medium" / "4 - Low".
_SEVERITY_ALIASES = {
    "1 - critical": "Urgent", "critical": "Urgent", "urgent": "Urgent", "blocker": "Urgent",
    "1": "Urgent", "sev1": "Urgent", "p0": "Urgent",
    "2 - high": "High", "high": "High", "2": "High", "sev2": "High", "p1": "High",
    "3 - medium": "Medium", "medium": "Medium", "moderate": "Medium", "3": "Medium",
    "sev3": "Medium", "p2": "Medium",
    "4 - low": "Low", "low": "Low", "minor": "Low", "4": "Low", "sev4": "Low", "p3": "Low",
    # Arabic
    "حرج": "Urgent", "عاجل": "Urgent", "عالي": "High", "مرتفع": "High",
    "متوسط": "Medium", "منخفض": "Low", "بسيط": "Low",
}

_PLATFORM_ALIASES = {
    "platform admin": "Platform Admin Panel", "super admin": "Platform Admin Panel",
    "admin panel": "Admin Panel", "admin": "Admin Panel", "dashboard": "Admin Panel",
    "customer app": "Customer APP", "customer": "Customer APP", "cst": "Customer APP",
    "rider": "Riders APP", "riders": "Riders APP", "captain": "Riders APP",
    "delivery": "Riders APP", "driver": "Riders APP",
    "merchant ops web": "Merchant OPS Web", "merchant web": "Merchant OPS Web",
    "merchant ops app": "Merchants OPS APP", "merchant app": "Merchants OPS APP",
    "merchant": "Merchant OPS Web",
}


def normalize_severity(raw):
    """Map a raw severity/priority string to canonical Urgent/High/Medium/Low.
    Returns None if it can't be confidently mapped (never guesses)."""
    if raw is None:
        return None
    key = str(raw).strip().lower()
    if key in _SEVERITY_ALIASES:
        return _SEVERITY_ALIASES[key]
    # try the leading token, e.g. "2 - High" -> "high"
    for part in (key.replace("-", " ").split()):
        if part in _SEVERITY_ALIASES:
            return _SEVERITY_ALIASES[part]
    return None


def normalize_platform(text):
    """Best-effort platform inference from free text. None if not found."""
    if not text:
        return None
    t = str(text).lower()
    for alias, canonical in _PLATFORM_ALIASES.items():
        if alias in t:
            return canonical
    return None


def classify(severity_raw, platform=None):
    """Return {severity, platform, sla_days, priority, sla_label} or a partial
    result with missing=True when severity can't be determined."""
    sev = normalize_severity(severity_raw)
    if sev is None:
        return {"severity": None, "platform": platform, "missing": True,
                "reason": f"unmapped severity: {severity_raw!r}"}
    sla = SEVERITY_SLA[sev]
    return {
        "severity": sev,
        "platform": platform,
        "sla_days": sla["sla_days"],
        "priority": sla["priority"],
        "sla_label": sla["sla_label"],
        "missing": False,
    }


if __name__ == "__main__":
    import json
    demo = [("2 - High", "customer app crash"), ("عاجل", None), ("weird", "admin")]
    print(json.dumps([classify(s, normalize_platform(p)) for s, p in demo],
                     ensure_ascii=False, indent=2))
