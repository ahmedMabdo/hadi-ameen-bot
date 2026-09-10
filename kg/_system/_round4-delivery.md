---
id: 8orders/system/round4-delivery
note_type: system
sources:
  - path: Shared/TalabatkData/Mapping/CustomerCartMaping.cs
    sha1: 3b461ef795ef
  - path: Shared/TalabatkData/Mapping/CustomerMap.cs
    sha1: 5ec0075f81d7
  - path: Talabatk.IDS/Configurations/Identity.cs
    sha1: 9ac57860f5a7
last_updated: 2026-08-23
---
# Round 4 — Delivery Summary

**Closed 2026-08-21.** Plan: `i-need-you-to-expressive-hearth.md`. Branch `KnowledgeGraph`.
Attested at commit `75525122d23b7eb0935cfd1b082c1aff88dac0bf`.

> **Nothing was committed or pushed, and no source file was modified.** This round produced
> documentation and findings only. Appendix A security items are **reported, not remediated**.

---

## Re-prove coverage at any commit, in seconds

```bash
node docs/knowledge-graph/_system/verify-coverage.js
```

Exits non-zero and names the offending files if anything in git is new, removed, or unclassified.
**Run it after every rebase or merge.** This is the safeguard all three previous rounds lacked.

**Drift test, actually performed rather than asserted:** deleting one manifest row makes the script
exit `1` and name that exact file (`NEW  AdminUi/Startup.cs -> in git, absent from manifest`);
restoring it returns exit `0`. A completeness claim that cannot detect its own staleness is precisely
what failed three times before.

---

## The honest coverage claim, in tiers

| Tier | Count | Evidence |
|---|---|---|
| **Enumerated & classified** | **14,076** | `verify-coverage.js` exit 0 against **unfiltered** `git ls-files`; **0 unclassified** |
| In coverage scope | 7,613 | 9 in-scope projects + root-level build/ops files |
| Excluded, each with a stated reason | 6,463 | `_coverage-manifest.tsv` `status` column |
| Machine-analysed by deterministic parsers | ~4,500 | Reproducible; stronger than reading for generated content |
| **Explicit per-file read attestations (Round 4)** | **413** | 8 inbox reports with "Files read" sections |
| Cited anywhere in the graph | 1,879 | `depth` column — a **loose lower bound**, basename matching |

**This is not a claim that all 7,613 in-scope files have been read line by line.** That claim was made
three times and could not be substantiated. What *is* proven is that **nothing is missed**: every
tracked file is accounted for. Read-depth is reported separately and honestly — see **#382**.

`sweep-only` does **not** mean unread: a file read in Round 1 and found clean leaves no citation, so
absence of evidence is not evidence of absence. The graph's inability to distinguish those two cases
*was* the defect, and it is now visible rather than hidden.

---

## What this round changed structurally

1. **Enumeration blind spot closed (#384, critical).** `verify-coverage.js` enumerated only **8,491 of
   14,076** tracked files, against a 13-path whitelist — the remaining 5,585 were not excluded but
   **invisible**. It compared that filtered list against a manifest built from the same filter, so it
   agreed with itself and printed `COVERAGE OK`. **This was Round 2's defect reproduced one level up.**
   Found only because Phase 10 re-derived the file list by **walking the filesystem** instead of asking
   git the same question twice.
   *Generalisable lesson: a coverage checker must never derive both its expectation and its observation
   from the same filter.*
2. **Coverage claims made auditable (#382).** The manifest's `read` status was an *intention* — a file
   was stamped `read` because a phase was scheduled to read it. A `depth` column now sits beside
   `status`, the verifier prints the split on every run, `writeManifest()` carries it across
   regeneration so a rebase cannot silently reset it, and the success message states what it actually
   proves.
3. **Phase 0's "no untracked source files" premise falsified (#385).** 6 untracked files in
   `TalabatkRestaurants/Reports/`; the disk holds **41** report layouts, not the 38 Phase 4 audited.
4. **#4 retracted** after four rounds. `CustomerCart.CustomerId` *does* have a unique DB index — EF
   generates it from the one-to-one declared on the *other* side (`CustomerMap.cs:76`). Every prior
   round read only `CustomerCartMaping.cs` and missed it.

## Findings

**`_conflicts.md` now holds 386 entries, script-verified sequential 1–386, no gaps, no duplicates.**
Round 4 added **#330–386 (57)** and retracted #4. Wikilinks: **555, 0 broken.**

### Highest severity

| # | Finding |
|---|---|
| **331** | Production IDS **token-signing certificate + private key** committed, password hardcoded at `Identity.cs:101` → **token forgery for any user or role across all 5 hosts** |
| **384** | The coverage verifier's own 5,585-file blind spot (above) |
| **362** | `TrackingOrder` — no role gate; **any authenticated caller of any role** gets any customer's **home GPS** plus the driver's live position, name and phone, by walking an integer |
| **374** | **No host defines an authorization fallback policy**, so a controller written without `[Authorize]` is silently public: 13 admin controllers and **128 spec operations** anonymous, worst being `GET api/ElasticSerach/CreateIndecies` — an unauthenticated **GET** that rebuilds the search indices |
| **356** | All five production hosts resolve feature flags in a **test** scope, split across **two different** scopes (`"Tests"` vs `"Testing"`) → flags apply on some hosts and not others |
| **358** | Production Fawry payments routed to the provider's **staging** gateway, with `//change to production url` committed beside it |
| **367** | Data Protection key rings **per-server** on the 2-server farm; IDS has the sharing mechanism and it is **switched off** → random logouts on every load-balancer hop and deploy |
| **340** | Write-once financial ledgers set to `Cascade` with a reachable hard-delete path |
| **386** | Every delivery man's **password hash** returned to any authenticated role |
| **351** | "Remove one device" **empties the entire device list** — a `Where` predicate that never references its own lambda parameter, at 5 sites across customers, drivers and merchants |
| **377** | Merchant payments submittable with a **zero amount**; the sibling delivery-man screen guards exactly that |
| **375** | `[AllowAnonymous]` on a parameterless **insurance-deduction batch job** with no date guard |

Also notable: **#354** (announcement start job gets the *end* cron, end job an empty cron — present in
both Add and Edit), **#352** (order create/update dereference a deliberately-nullable address),
**#353** (tautological `!=`/`==` disabling reorder price-change detection), **#355** (PayMob validator
exempts Apple Pay from needing an id, then dereferences it), **#363–366** (IDOR cluster + shared root
cause), **#371/#378/#379** (validation authored in markup, enforced only where a developer remembered),
**#343/#344** (no effective CI quality gate; failed production deploys report green).

### Review gate — what it *rejected*

The gate is only meaningful if it says no. It did, repeatedly:

- **Payment bypass — refuted.** `PATCH ChangePaymentOnlineStatus` is `[AllowAnonymous]` and takes
  `(orderId, statusId)`, reading exactly like "mark any order paid". Tracing the handler showed the
  caller's status is **not** trusted — it asks the bank gateway or PayMob and derives `isPaid` from the
  provider. Logged as **#376** at medium (amplification + order oracle), with the refutation recorded
  so it is not re-raised.
- **Anonymous announcement management — rejected.** Reframed as **#370**, an admin-tier
  privilege-separation gap, after confirming the controllers are `[Authorize]`-protected.
- **Google Maps key — rejected twice.** Compared by hash without printing either value: the template
  key and the server key **differ**; the browser key is public by design.
- **25 "unmatched" UI permission strings — rejected.** They are seeded in migrations. My `.cs`-only
  grep was the flaw, not the code.
- Plus Round 1's Order money-precision claim (all 337 decimals repo-wide declare precision) and a
  `PromoCodes` missing-`HasKey` claim (it has one).

### My own tooling errors, recorded because they recur

- An N+1 detector using indentation reported 92 hits; the first sampled hit was straight-line code.
  Discarded and rewritten with brace-accurate tracking → 28 real hits.
- The read-evidence audit scanned `.txt` and so ingested **its own output**, counting 4,223 unevidenced
  paths *as evidence* (1,826 → 6,033). **Self-verification contaminates itself** unless the evidence
  corpus excludes the audit's own artifacts.
- My Phase 10 walker skipped `dist/`, producing 90 phantom "stale rows".
- An i18n detector's Unicode range did not survive shell embedding and flagged Arabic text as English.
- 11 wikilinks written with **fabricated** target paths — which became **#383** (7 entity notes missing).

---

## Open items — stated, not omitted

- **#383** — 7 entities (`DeliveryMan`, `Permission`, `Identity`, `CustomerAddress`, `Search`, `Fawry`,
  `PayMob`) have confirmed high-severity findings but **no dedicated note**.
- **`Commands/` A-range** — depth-reading agent stalled twice; covered by deterministic breadth only,
  marked `blocked:agent-stall`. Not absorbed into a "read" count.
- **`_conflicts.md` table formatting** — column counts vary across rows, inherited from Rounds 1–3
  (present from entry #1). Content sound; not bulk-rewritten because a prior `sed` pass over this file
  corrupted wikilinks.
- **Appendix A** — signing certificate, 5 Firebase service accounts, Fawry credentials, 159 populated
  secret-shaped config keys. **Rotation required, not deletion** — they are in git history.
- 🟡 items explicitly marked untraced-by-me in `_conflicts.md` (e.g. #380 c/d, #373's popup-close
  claim) need verification before action.

## Keeping it true

Run `verify-coverage.js` after every rebase or merge. It exits non-zero and names the drifted files.
When adding a phase that reads files, write a "## Files read" section listing them — that is what the
`depth` column counts, and it is the only thing that makes a read claim provable later.
