#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ado_updates.py — AUTHORITATIVE work-item history via ADO's reporting feed
`_apis/wit/reporting/workItemRevisions`, with a persisted watermark
(continuationToken / startDateTime) so we pull only what changed — never the
whole board.

This is the OPT-IN history path. The DEFAULT lifecycle path is the snapshot-diff
in workitems.record_transitions (wired into ado_snapshot.refresh). Run ONE of the
two in production to avoid attributing the same arrival twice — though the shared
event_id (keyed on old|new|changed_date) makes overlap safe/idempotent anyway.

`revisions_to_events()` is pure and unit-tested. `fetch_revisions()`/`sync()` hit
the network and are NOT verified without live ADO (no PAT in the dev sandbox).
"""
import urllib.parse

import ado_client
import workitems

REV_FIELDS = [
    "System.Id", "System.State", "System.AssignedTo",
    "Microsoft.VSTS.Common.Priority", "Microsoft.VSTS.Common.Severity",
    "System.Title", "System.IterationPath", "System.Tags",
    "System.ChangedDate", "System.ChangedBy",
]

# ADO field reference names we diff between consecutive revisions
TRACKED = (
    "System.State", "System.AssignedTo", "Microsoft.VSTS.Common.Priority",
    "Microsoft.VSTS.Common.Severity", "System.Tags", "System.IterationPath",
    "System.Title",
)

_WATERMARK_KEY = "ado_revisions_watermark"


def _s(v):
    return None if v is None else str(v)


def _assigned(v):
    if isinstance(v, dict):
        return v.get("displayName") or v.get("uniqueName") or ""
    return v or ""


def _base():
    return f"{ado_client.ADO_ORG_BASE}/{urllib.parse.quote(ado_client.ADO_PROJECT)}/_apis"


def fetch_revisions(since_iso=None, max_pages=200):
    """NETWORK. Pull revisions since `since_iso` (UTC ISO) via the reporting
    feed's continuationToken. Returns (revisions, watermark_token)."""
    import requests
    revs, token = [], None
    base = _base()
    headers = ado_client._auth_headers()
    for _ in range(max_pages):
        params = {"api-version": ado_client.ADO_API_VERSION, "fields": ",".join(REV_FIELDS)}
        if since_iso:
            params["startDateTime"] = since_iso
        if token:
            params["continuationToken"] = token
        url = f"{base}/wit/reporting/workItemRevisions?{urllib.parse.urlencode(params)}"
        r = requests.get(url, headers=headers, timeout=60)
        if r.status_code == 401:
            raise RuntimeError("ADO auth failed (401) — check AZURE_DEVOPS_PAT")
        if r.status_code >= 400:
            raise RuntimeError(f"ADO reporting revisions HTTP {r.status_code}: {r.text[:300]}")
        data = r.json()
        revs.extend(data.get("values", []))
        token = data.get("continuationToken")
        if data.get("isLastBatch", True):
            break
    return revs, token


def revisions_to_events(revisions):
    """PURE. Group full-snapshot revisions by id, sort by rev, diff consecutive
    revisions, and yield normalized rows for workitems.ingest_revisions().

    The first in-window revision of an id has no in-window predecessor, so it is
    not diffed — the snapshot-diff path (and a small watermark overlap) covers
    that boundary. Overlaps are idempotent via the shared event_id.
    """
    by_id = {}
    for rv in revisions:
        wid = rv.get("id") or (rv.get("fields", {}) or {}).get("System.Id")
        by_id.setdefault(wid, []).append(rv)

    rows = []
    for wid, items in by_id.items():
        items.sort(key=lambda x: x.get("rev", 0))
        prev = None
        for rv in items:
            f = rv.get("fields", {}) or {}
            if prev is not None:
                pf = prev.get("fields", {}) or {}
                for field in TRACKED:
                    o, n = pf.get(field), f.get(field)
                    if field == "System.AssignedTo":
                        o, n = _assigned(o), _assigned(n)
                    if _s(o) != _s(n):
                        rows.append({
                            "id": wid, "field": field, "old": o, "new": n,
                            "changed_date": f.get("System.ChangedDate"),
                            "changed_by": _assigned(f.get("System.ChangedBy")),
                            "rev": rv.get("rev"), "item": rv,
                        })
            prev = rv
    return rows


def _watermark(con):
    r = con.execute("SELECT value FROM meta WHERE key=?", (_WATERMARK_KEY,)).fetchone()
    return r["value"] if r else None


def _set_watermark(con, value):
    if value:
        con.execute("INSERT OR REPLACE INTO meta(key,value) VALUES (?,?)", (_WATERMARK_KEY, value))
        con.commit()


def _max_changed(revisions):
    dates = [(rv.get("fields", {}) or {}).get("System.ChangedDate") for rv in revisions]
    dates = [d for d in dates if d]
    return max(dates) if dates else None


def sync(since_iso=None, con=None):
    """NETWORK. Pull → convert → ingest idempotently → advance watermark.
    NOT VERIFIED without live ADO."""
    c = workitems._con(con)
    wm = since_iso or _watermark(c)
    revisions, _token = fetch_revisions(wm)
    rows = revisions_to_events(revisions)
    res = workitems.ingest_revisions("ado", rows, con=c)
    _set_watermark(c, _max_changed(revisions) or wm)
    return {"revisions": len(revisions), **res}


if __name__ == "__main__":
    import json
    print(json.dumps(sync(), ensure_ascii=False, indent=2))
