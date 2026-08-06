#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
issue_engine.py — glue that puts the evidence-based identity/dedup engine
(issue_identity.py) in front of the create-only triage path (channel_triage.py).

Behind HADI_ISSUE_ENGINE (default OFF). When on, each candidate issue is checked
against existing open board tickets and routed:
    NEW / RELATED / INSUFFICIENT -> create (as before)
    DUPLICATE                     -> skip (don't file a second ticket)
    UPDATE_EXISTING               -> add a comment to the matched ticket
    NEEDS_REVIEW                  -> surface to a human, don't auto-file

Existing-ticket candidates come from the local ado_snapshot.db board cache (the
"what's already filed" read-model) — no extra ADO calls on the hot path. The
routing is pure given an injected `existing` list, so it is unit-tested offline.
"""
import os
import re
import sys
import asyncio

import hadi_config
import issue_identity

try:
    import issue_matrix
except Exception:  # pragma: no cover
    issue_matrix = None

_ORDER_RX = re.compile(r"(?:order|order\s*no|اوردر|أوردر|طلب|رقم)\s*#?\s*(\d{3,})", re.IGNORECASE)


def enabled():
    return hadi_config.ISSUE_ENGINE_ENABLED


def _enrich(issue):
    """Map a triage issue dict -> issue_identity input, extracting weak identity
    signals (platform / order numbers) from the free text. Signature is derived
    inside issue_identity from the same text."""
    text = f"{issue.get('title','')} {issue.get('description','')}"
    platform = issue_matrix.normalize_platform(text) if issue_matrix else None
    orders = _ORDER_RX.findall(text)
    return {
        "title": issue.get("title", ""),
        "description": issue.get("description", ""),
        "platform": platform,
        "order_ids": orders,
    }


def _default_existing(channel_id):
    """Open board tickets from the local ado_snapshot cache -> candidate pool."""
    try:
        import sqlite3
        import ado_snapshot
        done = set(ado_snapshot.DONE_STATES)
        con = sqlite3.connect(ado_snapshot.DB_PATH)
        con.row_factory = sqlite3.Row
        rows = con.execute("SELECT id,title,state,tags FROM board_items").fetchall()
        con.close()
        out = []
        for r in rows:
            if r["state"] in done:
                continue
            out.append({"id": r["id"], "title": r["title"] or "",
                        "description": "", "tags": r["tags"] or ""})
        return out
    except Exception as e:  # noqa — no cache yet / read error -> empty pool (safe: all NEW)
        print(f"issue_engine: existing pool unavailable ({e})")
        return []


def route_issues(channel_id, issues, existing=None):
    """Bucket candidate issues by the engine's decision. Pure given `existing`."""
    if existing is None:
        existing = _default_existing(channel_id)
    out = {"create": [], "update": [], "duplicate": [], "review": []}
    for it in issues:
        decision = issue_identity.decide(_enrich(it), existing, persist=True)
        d = decision["decision"]
        it = dict(it)
        it["_decision"] = decision
        if d in ("DUPLICATE",):
            out["duplicate"].append((it, decision))
        elif d == "UPDATE_EXISTING":
            out["update"].append((it, decision))
        elif d == "NEEDS_REVIEW":
            out["review"].append((it, decision))
        else:  # NEW / RELATED / INSUFFICIENT -> file it
            out["create"].append(it)
    return out


async def apply_updates(updates, cwd, dry_run=False):
    """For UPDATE_EXISTING decisions, add a comment to the matched ticket via
    ado_cli.py add-comment (create-only-safe: a comment, never a field update)."""
    for it, decision in updates or []:
        mid = decision.get("matched_existing_issue_id")
        if not mid:
            continue
        note = (f"[هادي] بلاغ مشابه اترصد وربطته بالتذكرة دي بدل ما أفتح تذكرة جديدة "
                f"(ثقة {decision.get('confidence')}, دليل: {', '.join(decision.get('evidence', []))}). "
                f"العنوان الجديد: {it.get('title','')}")
        cmd = [sys.executable, os.path.join(cwd, "ado_cli.py"), "add-comment", str(mid), note]
        if dry_run:
            cmd.append("--dry-run")
        try:
            p = await asyncio.create_subprocess_exec(
                *cmd, cwd=cwd,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            await asyncio.wait_for(p.communicate(), timeout=90)
        except Exception as e:  # noqa — a failed comment must not break triage
            print(f"issue_engine: add-comment on #{mid} failed: {e}")
