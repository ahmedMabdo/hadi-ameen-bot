#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
issue_identity.py — evidence-based issue identity / deduplication engine
(Phase 2, module P2). The correctness core: decide whether an incoming issue is
a DUPLICATE / UPDATE to an existing one, a NEW issue, RELATED, or needs a human
(NEEDS_REVIEW) — WITHOUT the old failure mode of merging on wording alone.

Hard rules (from the brief §5):
  * Never auto-merge on a single weak signal (e.g. similar title / same screen).
  * Auto-merge requires an IDENTITY-grade signal (crash signature / order # /
    endpoint / explicit link) plus corroboration, OR >=2 independent signals.
  * A hard contradiction (different crash signature, or different platform+version)
    blocks the merge and routes to NEEDS_REVIEW / NEW — similar words are never
    treated as proof of the same root cause.
  * Uncertain -> NEEDS_REVIEW (a human), never a silent merge.

The pipeline is deterministic first; an optional LLM is advisory and may only
DE-ESCALATE (turn a NEEDS_REVIEW into NEW/RELATED) — it can never silently
upgrade to an auto-merge.

Decision object:
  {decision, confidence, matched_existing_issue_id, evidence[],
   contradicting_evidence[], reason, evaluation_version}
"""
import re
import uuid
import json

import hadi_config

try:
    import workitems  # for audit persistence (optional)
except Exception:  # pragma: no cover
    workitems = None

# thresholds (config-driven)
MERGE = hadi_config.ISSUE_MERGE_THRESHOLD
DUP = hadi_config.ISSUE_DUPLICATE_THRESHOLD
REVIEW = hadi_config.ISSUE_REVIEW_THRESHOLD
MIN_SIGNALS = hadi_config.ISSUE_MIN_SIGNALS_FOR_AUTOMERGE
TEXT_SIM_SIGNAL = 0.5  # Jaccard above which text similarity counts as *a* (weak) signal

IDENTITY_SIGNALS = {"crash_signature", "order", "endpoint", "link"}

_AR_DIAC = re.compile(r"[ً-ْـ]")
_STOP = {
    "the", "a", "an", "of", "to", "in", "on", "and", "or", "for", "is", "was",
    "with", "when", "then", "app", "issue", "error", "bug", "problem", "page",
    "screen", "في", "من", "على", "الى", "إلى", "مش", "لا", "و", "او", "أو",
    "مشكلة", "خطأ", "ايشو", "صفحة", "شاشة",
}


def _norm(s):
    if not s:
        return ""
    s = _AR_DIAC.sub("", str(s))
    s = s.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ة", "ه")
    return s.strip().lower()


def _tokens(text):
    toks = re.split(r"[^0-9A-Za-z؀-ۿ]+", _norm(text))
    return {t for t in toks if len(t) >= 2 and t not in _STOP}


def _text_sim(a, b):
    ta = _tokens(f"{a.get('title','')} {a.get('description','')}")
    tb = _tokens(f"{b.get('title','')} {b.get('description','')}")
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


_SIG_RX = re.compile(r"([A-Za-z_][A-Za-z0-9_.]*(?:Exception|Error|Fault|Crash))")


def _sig(x):
    if x.get("signature"):
        return _norm(x["signature"])
    m = _SIG_RX.search(f"{x.get('title','')} {x.get('description','')}")
    return _norm(m.group(1)) if m else None


def _match(a, b):
    """Compute signals + contradictions + text similarity between two issues."""
    signals, contra = set(), set()

    ids_a = set(a.get("links") or [])
    ids_b = set(b.get("links") or [])
    if (b.get("id") in ids_a) or (a.get("id") in ids_b):
        signals.add("link")

    sa, sb = _sig(a), _sig(b)
    if sa and sb:
        if sa == sb:
            signals.add("crash_signature")
        else:
            contra.add("signature_mismatch")

    if set(a.get("order_ids") or []) & set(b.get("order_ids") or []):
        signals.add("order")

    ea, eb = a.get("endpoint"), b.get("endpoint")
    if ea and eb and _norm(ea) == _norm(eb):
        signals.add("endpoint")

    if (a.get("release") and a.get("release") == b.get("release")
            and a.get("component") and _norm(a["component"]) == _norm(b.get("component"))):
        signals.add("release_component")

    pa, pb = a.get("platform"), b.get("platform")
    if pa and pb and _norm(pa) != _norm(pb):
        contra.add("platform_mismatch")
    va, vb = a.get("app_version"), b.get("app_version")
    if va and vb and str(va) != str(vb):
        contra.add("version_mismatch")

    sim = _text_sim(a, b)
    if sim >= TEXT_SIM_SIGNAL:
        signals.add("text")

    return {
        "signals": signals, "contradictions": contra, "sim": sim,
        "strong": len(signals - {"text"}),
        "identity": len(signals & IDENTITY_SIGNALS),
    }


def _confidence(sim, identity, strong, contra):
    c = 0.45 + 0.16 * identity + 0.09 * (strong - identity) + 0.32 * sim - 0.2 * len(contra)
    return round(max(0.0, min(0.99, c)), 3)


def _result(decision, confidence, matched_id, evidence, contradicting, reason,
            new_issue, persist, con):
    ev = {
        "evaluation_id": uuid.uuid4().hex,
        "work_item_id": new_issue.get("id"),
        "decision": decision,
        "confidence": confidence,
        "matched_issue_id": matched_id,
        "evidence": evidence,
        "contradicting": contradicting,
        "reason": reason,
        "evaluation_version": hadi_config.EVALUATION_VERSION,
    }
    if persist and workitems is not None:
        try:
            workitems.record_evaluation(ev, con=con)
        except Exception:
            pass
    # public shape uses the brief's key names
    return {
        "decision": decision,
        "confidence": confidence,
        "matched_existing_issue_id": matched_id,
        "evidence": evidence,
        "contradicting_evidence": contradicting,
        "reason": reason,
        "evaluation_version": hadi_config.EVALUATION_VERSION,
    }


def decide(new_issue, existing_issues, llm=None, persist=False, con=None):
    """Return a decision object for `new_issue` vs the `existing_issues` pool."""
    if not (new_issue.get("title") or new_issue.get("description") or new_issue.get("signature")):
        return _result("INSUFFICIENT", 0.0, None, [], [],
                       "no title/description/signature to evaluate", new_issue, persist, con)

    scored = []
    for b in existing_issues or []:
        if b.get("id") is not None and b.get("id") == new_issue.get("id"):
            continue
        m = _match(new_issue, b)
        m["cand"] = b
        scored.append(m)

    cands = [m for m in scored if m["signals"] or m["sim"] >= REVIEW]
    if not cands:
        return _result("NEW", 0.8, None, [], [],
                       "no candidate shares an identity signal or sufficient similarity",
                       new_issue, persist, con)

    best = max(cands, key=lambda m: (m["identity"], m["strong"], m["sim"]))
    b = best["cand"]
    sim, strong, identity = best["sim"], best["strong"], best["identity"]
    contra = best["contradictions"]
    hard = "signature_mismatch" in contra
    evidence = sorted(best["signals"])
    contradicting = sorted(contra)
    matched_id = b.get("id")
    conf = _confidence(sim, identity, strong, contra)
    new_ev = bool(new_issue.get("has_new_evidence"))

    auto_merge = (not hard) and (
        (identity >= 1 and sim >= REVIEW)
        or identity >= MIN_SIGNALS
        or (strong >= 1 and sim >= MERGE)
    )

    if hard:
        decision = "NEEDS_REVIEW" if (strong >= 1 or sim >= MERGE) else "NEW"
        reason = ("shares signals but crash/exception signatures DIFFER — likely a "
                  "different root cause; not merging")
    elif auto_merge:
        decision = "UPDATE_EXISTING" if new_ev else "DUPLICATE"
        reason = (f"identity match ({', '.join(sorted(best['signals'] & IDENTITY_SIGNALS)) or 'multi-signal'}"
                  f"), text sim={sim:.2f}")
    elif strong >= 1:
        decision = "RELATED" if contra else "NEEDS_REVIEW"
        reason = ("one shared signal but not enough to auto-merge; "
                  + ("contradiction present -> related, not same" if contra else "needs a human"))
    elif sim >= REVIEW:
        decision = "NEW" if contra else "NEEDS_REVIEW"
        reason = ("similar wording only" + (" but contradicted by platform/version -> new"
                                            if contra else " with no identity signal -> human check"))
    else:
        decision = "NEW"
        reason = "weak/insufficient overlap"

    # optional LLM: advisory, DE-ESCALATION ONLY (never upgrades to a merge)
    if decision == "NEEDS_REVIEW" and llm is not None:
        suggestion = _ask_llm(llm, new_issue, b, evidence, contradicting)
        if suggestion in ("NEW", "RELATED"):
            reason += f" | LLM de-escalated to {suggestion}"
            decision = suggestion

    return _result(decision, conf, matched_id if decision != "NEW" else None,
                   evidence, contradicting, reason, new_issue, persist, con)


def _ask_llm(llm, new_issue, cand, evidence, contradicting):
    """Call the injected LLM for an advisory verdict. Returns one of
    NEW/RELATED/KEEP (KEEP = leave as NEEDS_REVIEW) — merges are never taken
    from the LLM here, by design."""
    prompt = (
        "You are a strict issue-deduplication reviewer. Two issues are below.\n"
        "Answer ONLY compact JSON: {\"verdict\":\"NEW|RELATED|KEEP\",\"reason\":\"...\"}\n"
        "Use NEW only if they are clearly different problems; RELATED if linked but "
        "distinct; KEEP if you are unsure.\n"
        f"Shared evidence: {evidence}\nContradictions: {contradicting}\n"
        f"NEW ISSUE:\n{json.dumps({k: new_issue.get(k) for k in ('title','description','platform','app_version')}, ensure_ascii=False)}\n"
        f"EXISTING #{cand.get('id')}:\n{json.dumps({k: cand.get(k) for k in ('title','description','platform','app_version')}, ensure_ascii=False)}\n"
    )
    try:
        raw = llm(prompt)
        data = json.loads(raw[raw.find("{"):raw.rfind("}") + 1])
        v = str(data.get("verdict", "")).upper()
        return v if v in ("NEW", "RELATED") else "KEEP"
    except Exception:
        return "KEEP"


def default_llm(prompt, model=None):
    """Shell out to the Claude CLI (same mechanism as daily_digests). Not used
    in tests; only when an operator wires it into decide(llm=default_llm)."""
    import subprocess
    import claude_bin
    model = model or __import__("os").environ.get("HADI_MODEL", "")
    cmd = [claude_bin.resolve(), "-p", prompt]
    if model:
        cmd += ["--model", model]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=120, cwd="/tmp")
    return out.stdout


if __name__ == "__main__":
    demo_new = {"title": "checkout crash NullPointerException", "signature": "NullPointerException",
                "platform": "Android", "app_version": "8.4.0"}
    demo_existing = [{"id": 111, "title": "crash at checkout NullPointerException",
                      "signature": "NullPointerException", "platform": "Android", "app_version": "8.4.0"}]
    print(json.dumps(decide(demo_new, demo_existing), ensure_ascii=False, indent=2))
