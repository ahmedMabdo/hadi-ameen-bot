---
id: 8orders/system/system-index
note_type: system
sources:
  - path: AdminUi/ClientApp/src/app/auth-guard.guard.ts
    sha1: 692386091bea
  - path: Shared/TalabatkApplication/Services/MartQuantityValidationService.cs
    sha1: 085c128a5b0d
  - path: Shared/TalabatkData/Mapping/CustomerCartMaping.cs
    sha1: 3b461ef795ef
  - path: Shared/TalabatkLogic/TalabatkModels/Order.Partial.cs
    sha1: 0ee58f302d71
  - path: Shared/TalabatkLogic/TalabatkModels/Order.cs
    sha1: a8504688c441
last_updated: 2026-08-23
---
# 8Orders — System Knowledge Graph

## Status, 2026-09-09 — rebased onto `master`, five commands green

`KnowledgeGraph` was rebased onto `origin/master` (98 commits, 281 source files changed) and the vault
re-verified against the new code. What that pass changed, and what it found, is in
`_conflicts.md` **#653-#656**; the short version:

- **71 hard citation failures** were repaired. 51 were pure line drift and renumbered mechanically —
  but only where the cited line's *neighbourhood* was byte-identical, because a unique text match is
  not enough: `Order.cs`'s `this.OrderDeliveries` block still occurred exactly once after master
  extracted it into `CancelActiveOrderDeliveries()` **and widened its status filter**, so a naive
  remap would have produced a citation that passes every check while describing behaviour that no
  longer exists. The remaining 20 were resolved by reading the new code.
- **Of 6,235 citations, 38 sat on code master had actually edited** — the number that matters, where
  `CITATION-STALE`'s 157 only says *the file* changed. All 38 were reviewed; the corrections are in
  the notes. Two claims were rewritten rather than renumbered (the cancellation filter now covers
  `Initialize`; the merchant login gate now covers a third role, `OrdinaryMerchant`).
- **One finding closed by upstream code**: #10's duplicated stock-toggle rule now has a single
  implementation. **One pre-existing citation error corrected**: `Order & Fulfilment/_scenarios.md`
  cited the wallet block for a claim about the online-payment mismatch check.
- **Three checker defects fixed** (#654, #655, #656) — a CRLF parse that made `verify-coverage.js`
  fail unconditionally, a hardcoded absolute path that made `audit-inbox-merge.js` audit a different
  checkout than it reported on, and an unvalidated range end that let 11 corrupted citations through
  every gate.
- **One new confirmed defect in master's own new code** (#653): `MenuItemActivationTrackingController`
  enforces neither a role nor a permission and trusts a caller-supplied `restaurantId`, while the
  permission it should use exists in the database and is wired to nothing.

The counts in the table below are still typed by hand and still drift; script-generating them remains
open on the enhancement backlog.

## Status, 2026-08-23 — the five commands are green

Four rounds of this effort declared completion and four were wrong, each because it verified itself with
the method that produced its gap. This round's answer is different in kind: it is not a claim, it is a
set of commands, and each one prints its own denominator derived from the **code** rather than from the
graph.

```bash
node docs/knowledge-graph/_system/verify-notes.js --self-test      # 39/39 failure classes detectable
node docs/knowledge-graph/_system/verify-notes.js                  # NOTES OK
node docs/knowledge-graph/_system/verify-notes.js --register-check  # REGISTER OK
node docs/knowledge-graph/_system/verify-citations.js               # CITATIONS OK
node docs/knowledge-graph/_system/verify-coverage.js                # COVERAGE OK
```

All five pass today. What each one settles:

| Question | Command | Answer today (2026-09-09, at `master`) |
|---|---|---|
| Is anything in the repository unaccounted for? | `verify-coverage.js` | No — 15,111 tracked files, 0 unclassified |
| Does every entity in the code have a note? | `verify-notes.js` | Yes — **536** candidates (the whole domain layer, widened in finding #639), 245 documented (38 with their own note, 207 folded into a canonical one), 291 excluded each with stated evidence, **0 with no note** |
| Does every entry point belong to a feature? | `verify-notes.js` | Yes — 200 of 200 mapped, 31 of 31 features complete |
| Is any note a stub pretending to be an answer? | `verify-notes.js` | No — 0 stubs; a rule-bearing note without a rule matrix fails |
| Does every citation point at code that exists? | `verify-citations.js` | Yes — 5,223 line citations, **0 hard failures** |
| Is any finding unreachable from the graph? | `verify-notes.js` | No — 692 register rows across `_conflicts.md` (656) and `_idor-instances.md`, **0 linking to nothing** |
| Are the checkers themselves trustworthy? | `--self-test` on both | 40/40 and 7/7 failure classes provably detectable |

**The measured journey: 1,260 problems at the start of this round, 0 now**, across twelve gap classes.
Findings grew 605 → 635 rows while closing them, because closing a gap means reading the code the gap
was hiding.

**What this still is not.** "Every citation is true" means every cited line exists and carries code — it
does not mean a human re-read all 3,291. 664 leads remain in `verify-citations.js`'s two judgement
classes (a symbol named in prose but not within 12 lines of its citation; a bare filename several files
share); those are a triage queue, deliberately not a gate, because neither can be decided mechanically.
The tiered coverage claim below still stands and should still be read before quoting any number.

---

## Coverage status — read this before trusting any completion claim below

**Written 2026-08-21 (Round 4), still accurate and still worth reading. The previous three rounds each
declared "100% complete" and each was wrong. This section states what is actually proven, and by what
evidence, so the claim can be checked rather than believed.**

Verify it yourself — this is the whole point, and it takes seconds:

```bash
node docs/knowledge-graph/_system/verify-coverage.js
```

It exits non-zero and names the offending files if anything in git is new, removed, or unclassified.
Run it after every rebase or merge. **That drift check is the safeguard all three earlier rounds
lacked** — each verified itself with the same method that created its gap, so each was structurally
incapable of noticing what it had missed.

> **And Round 4 nearly repeated the mistake in this very script — see #384.** The verifier originally
> enumerated `git ls-files` against a **13-path whitelist**, so 5,585 tracked files were not
> *excluded* but **invisible**: never enumerated, never classified, never flagged. It compared that
> filtered list against a manifest built from the same filter, so it agreed with itself and printed
> `COVERAGE OK` with `unclassified: 0`. It was caught only because Phase 10 re-derived the file list by
> **walking the filesystem instead of asking git the same question twice**. The generalisable lesson:
> *a coverage checker must never derive both its expectation and its observation from the same filter.*
> That fix also directly produced finding **#386** (delivery-man password hashes exposed to any
> authenticated role) — the trail began in a root-level SQL script that had been invisible until then.

### The claim, in tiers — each with its own evidence

| Tier | Count | What it actually means | Evidence |
|---|---|---|---|
| **Enumerated & classified** | **14,076** | Every tracked file in the repository is accounted for as `read`, `swept` or `excluded:<reason>`. **0 unclassified.** This is what proves *nothing is missed*. | `verify-coverage.js` exits 0 against unfiltered `git ls-files` |
| In coverage scope | 7,613 | The 9 in-scope projects plus root-level build/ops files. The other 6,463 are excluded, each with a stated reason | `_coverage-manifest.tsv` |
| **Machine-analysed** | ~4,500 | Parsed by deterministic scanners — 935 migrations, the 16,651-line model snapshot, 1,850 `Commands`/`Queries`/`Feature`, 380 Angular templates, 107 enums, 130 DTOs, 38 report designers, 24 config files, 4 OpenAPI specs | Reproducible; for generated/regular content this is *stronger* than human reading |
| **Explicitly attested reads** | **413** | Files named individually in a "Files read" attestation during Round 4 | 8 inbox reports under `_system/_inbox/` |
| Cited anywhere in the graph | 1,879 | A **loose lower bound** — basename matching, so treat as indicative only | `depth` column in the manifest |

**What this is not.** It is **not** a claim that every one of the 7,596 files has been read line by
line by a human or a model. That claim was made three times and could not be substantiated. The
manifest's `read` status was originally an *intention* — a file was stamped `read` because a phase was
scheduled to read it — which is why finding **#382** exists and why a `depth` column now sits beside
`status`. Read `#382` before quoting any coverage number from this graph.

**Equally, do not over-read the other direction:** `sweep-only` does **not** mean unread. A file read
in Round 1 and found clean leaves no citation behind, so absence of evidence is not evidence of
absence. The honest position is that the graph cannot distinguish the two for those files — and that
inability, not the reading itself, was the real defect.

### Known open items — stated, not omitted

- **#384** — *critical, fixed:* the verifier's own 5,585-file enumeration blind spot (above).
- **#382** — the coverage-claim integrity finding above. Fixed structurally this round; the tiered
  claim replaces the old assertion.
- ~~**#383**~~ — **closed 2026-08-23.** All 7 entities that had confirmed high-severity findings and no
  dedicated note now have one: `DeliveryMen`, `Permission`, `Identity`, `CustomerAddress`, `Search`,
  `Fawry`, `PayMob`. `verify-notes.js` reports 0 entities with no note, so the class cannot silently
  reopen.
- **#385** — 6 **untracked** source files in `TalabatkRestaurants/Reports/` (3 report classes + 3
  `.vsrepx`), invisible to git and so to every phase. This falsifies Phase 0's explicit "no untracked
  source files exist" premise, which every later phase inherited. The disk holds **41** report layouts,
  not the 38 Phase 4 audited.
- **`Commands/` A-range** — the depth-reading agent stalled twice; covered by deterministic breadth
  scanning only, marked `blocked:agent-stall`. Not silently absorbed into a "read" count.
- **`_conflicts.md` table formatting** — 630 of 632 rows now have 8 cells; 2 have 10. Content is sound.
  The Phase 8 backfill that added a wikilink to every row asserted, before writing, that each edit left
  the cell count unchanged — a row that gains or loses a cell reflows every column after it, and that is
  invisible in a diff of 450 rows. Still not bulk-reformatted, for the original reason: a previous `sed`
  pass over this file corrupted wikilinks, so all edits here go through the Edit tool or a
  cell-aware script.

**Security note:** Appendix A items (committed signing certificate, Firebase private keys, provider
credentials) are **reported, not remediated** — that was the agreed scope. They require rotation, not
just deletion, because they are in git history.

---

> **Scope-qualified completion status, honestly stated (2026-08-20).** This registry covers exactly
> **9 projects, user-confirmed for both audit rounds**: `Shared/SharedWeb`, `Shared/TalabatkApplication`,
> `Shared/TalabatkData`, `Shared/TalabatkLogic`, `AdminUi`, `Talabatk.IDS`, `TalabatkAPIs`,
> `TalabatkDelivery`, `TalabatkRestaurants`. **Explicitly excluded, by direct user instruction, not by
> oversight**: `TalabatkApplication.Test`, `TalabatkData.Test`, `TalabatkLogic.Test` (test projects),
> `Talabatk.VersionAPI`, and the legacy `TalabatkAPI` / `TalabatkAPI.Data` projects — none of these are
> phased in "later"; they are simply out of scope for this knowledge graph.
>
> Within that 9-project scope, two audit rounds have now run:
> - **Round 1** ("True Zero-Gap Closure," plan `gleaming-purring-charm.md`, closed 2026-08-13, Phases
>   1–14): covered every controller + Razor view (Phase 7's "154 controllers" milestone), all 1,847
>   `Shared/TalabatkApplication/Commands`+`Queries`+`Feature` files (Phase 8), all 288
>   `TalabatkLogic/TalabatkModels` files (Phase 9), ~2,162 `TalabatkData` files (Phase 10), the full
>   `Order.cs` handler + `CustomerUserController.cs` (Phase 11), and both Angular frontends' `.ts`
>   files by folder-name enumeration (Phases 12–13) — but that folder-name enumeration silently
>   excluded anything sitting loose at `src/app/` root, and several other folders it claimed as fully
>   covered (`Shared/TalabatkApplication` outside `Commands`/`Queries`/`Feature`, all of
>   `Shared/TalabatkLogic` outside `TalabatkModels`, `Shared/SharedWeb` entirely, per-host
>   non-controller folders like `Helper`/`Reports`, `.resx` files, and Angular build boilerplate) were
>   never actually enumerated by any Round 1 phase at all, despite the "100% done" claim.
> - **Round 2** ("True Zero-Gap Closure, Round 2," plan `shimmering-wiggling-trinket.md`, closed
>   2026-08-20, Phases 1–8): closed every gap Round 1 missed — re-verified via a single consistent
>   manifest pass (`find`, uniform `bin`/`obj`/`node_modules`/`.angular`/`.git` exclusion) against
>   Round 1's own Phase-by-phase claims, then individually read (Pile A) or grep-swept-and-verified
>   (Pile B) roughly 1,400 files across `Shared/TalabatkApplication`'s remaining folders (Phase 1, 530
>   files), all of `Shared/TalabatkLogic` outside `TalabatkModels` (Phase 2, 239 files), all of
>   `Shared/SharedWeb` (Phase 3, 34 files), a `Shared/TalabatkData` reconciliation delta + 2
>   previously-unread `.sql` scripts (Phase 4, 13 files), every host's non-controller `Helper`/
>   `Reports`/root-level `.cs` files plus previously-missed Razor views (Phase 5, ~535 files across
>   AdminUi/TalabatkAPIs/TalabatkDelivery/TalabatkRestaurants), the loose Angular root-level `.ts`
>   files both frontends' Phase 12/13 folder-only counting had silently excluded (Phase 6, 18 files),
>   11 `.resx` localization files + 12 Angular CLI/build boilerplate files (Phase 7), and a final
>   registry re-sync (Phase 8, this update). Every sub-phase's literal file count was independently
>   re-verified against a fresh `find` before being trusted — this caught and corrected several of
>   Round 1's own miscounts along the way (documented in each phase's closing note in the plan file).
>
> - **Round 3** (post-rebase reconciliation, 2026-08-20, same day): the branch was rebased onto
>   `origin/master`, pulling in 11 commits that touched **45 in-scope source files** (10 new, 35
>   modified) — none of which any prior round had seen. Round 3 read all 10 new files, re-verified
>   every modified file that carried an existing finding or citation, and additionally closed the
>   last two *structural* coverage gaps that Rounds 1–2 had left: the **7 loose root-level files in
>   `Shared/TalabatkApplication/Commands/`** (Round 1 read that folder in letter-prefixed *folder*
>   buckets — `Commands/D*`, `Commands/E*` … — so files sitting directly in `Commands/` root belonged
>   to no bucket; all 7 were confirmed present at Round 1's close, and Round 1's own verification
>   count was itself wrong: it claimed 675 files where `git ls-tree` at that commit shows 676), and
>   the **4 files in `Shared/TalabatkLogic/TalabatkModels/POCOs/`** (a subfolder named in *neither*
>   plan, while its sibling `AutoCompensation/` was explicitly read). Coverage was established by
>   diffing the full `git ls-tree` file list at Round 1's closing commit against current `HEAD` —
>   which also proved there is **no other drift**: exactly 12 files were added repo-wide since Round 1
>   closed (10 from this rebase, 2 already handled by Round 2 Phase 4) and **0 removed**.
>
> **Net result after Round 4: `_conflicts.md` holds 383 conflict/gap entries** — script-verified
> sequential from 1 to 383, no gaps, no duplicates. Round 4 contributed **#330-383 (54 entries)**,
> including the two meta-findings **#382** (coverage-claim integrity) and **#383** (7 missing entity
> notes), and **retracted #4** — a four-round-old false claim that `CustomerCart.CustomerId` had no
> unique DB index; it does, generated by EF from the one-to-one declared on the *other* side, which
> every prior round missed by reading only `CustomerCartMaping.cs`. Round 4's highest-severity results:
> **#331** (production IDS token-signing certificate + hardcoded password committed, enabling token
> forgery), **#362** (`TrackingOrder` leaks any customer's home GPS and the driver's live location to
> any authenticated caller of any role), **#374** (no host defines an authorization fallback policy, so
> 13 admin controllers and 128 spec operations are anonymous), **#356** (all five production hosts
> resolve feature flags in a *test* scope, split across two different scopes), **#358** (production
> Fawry payments routed to the provider's **staging** gateway), **#367** (Data Protection key rings
> per-server on a 2-server farm — random logouts on every load-balancer hop and deploy), and **#340**
> (write-once financial ledgers set to `Cascade` with a reachable hard-delete path).
>
> *(Historical counts, for the record: 329 entries at the end of Round 3 — 254 at the end of Round 1, +70
> in Round 2 for #255-324, +5 in Round 3 for #325-329 — script-verified sequential, no gaps or
> duplicates.)*
>
> Round 3 also **narrowed #205** rather than closing it: the rebase's "UnRevised
> Activation" PR fixed the `changeSummary` half (now merged into the row's `Note` via a new
> `AddNotes` helper) but the `barCode` parameter is *still* accepted and never assigned, with a
> confirmed real caller passing the ERP's `MaterialCode`. **Round 3's headline finding is a confirmed
> regression the rebase introduced** (#325): the `out of stock` PR rewrote the `OutOfStock`
> projection in all 3 query paths of `SearchItemsWithFiltersAndSortingOptionsQuery` down to
> `x.CurrentStockQuantity <= 0`, deleting both an `IsStore` guard and the comment explaining why it
> was load-bearing — verified consequence: since every `MaintainStock` call site is a mart/ERP path,
> non-mart restaurant items keep `CurrentStockQuantity` at 0 forever, so **the entire non-mart
> restaurant catalogue now reports as out-of-stock in customer item search**, and the explicit
> persisted `MenuItem.OutOfStock` column is no longer consulted at all. Round 2's highest-severity
> new findings: production stack-trace disclosure to any
> client in `TalabatkDelivery`'s exception middleware (#308); a flipped comparison operator in
> `TalabatkDelivery`'s IDS token-refresh check causing constant needless refresh storms while valid,
> then permanent staleness once truly expired (#306); `AdminUi`'s and `TalabatkRestaurants`' report
> viewers each missing report-class registrations that make specific reports permanently unopenable
> (#300, #311); a copy-paste `StoresHub` bug delivering the wrong SignalR event with no payload for
> two restaurant notification types (#312); `AdminUi`'s production Angular bundle never actually
> running in production mode due to a copy-pasted `environment.prod.ts` (#323); and several more
> confirmed instances of Round 1's already-tracked systemic patterns (unregistered logging
> middleware, hardcoded credentials, stale Angular-CLI scaffold tests) recurring in hosts Round 1
> never actually read. Round 1's own headline findings (`TalabatkContext.Auditing()`'s reversed
> `IsAssignableFrom` check, #207; 2 confirmed IDOR vulnerabilities in `CustomerUserController`,
> #227-228; the identical config-load-hang bug in both Angular frontends, #240/#244; the original
> Phase 7 finding that a controller stacks `[Authorize]` with `[AllowAnonymous]` where the latter
> silently wins, #45) remain valid and unchanged.

## Open this first
- [[system-graph.html|Interactive System Graph]] — bird's-eye map, drill to any entity. Regenerated
  through Round 4 to reflect the current entity/conflict counts (55 entities — **7 more still owed,
  see #383** — and 383 conflicts, the
  `TalabatkContext` hub node, Round 2's 3 new domain concepts, and Round 3's cross-cutting
  Low-Quality Images node) — see that file's own generation note for what it does and doesn't
  visualize.
- [[_entity-index|Entity Registry]] · [[_conflicts|Conflict Register]] · [[_integrations|Integration Register]]
- [[_issues/_index|Issues]] — one file per register finding, each with a `status:` to edit as work
  happens. 605 open of 656. The register stays the source of truth for *what* was found; these carry the
  fix state and the decision.
- [[FIX-650-REVIEW|Review guide — `fix/650-user-privilege-escalation`]] — **read this before merging that
  branch.** 40 findings closed across 36 files, including two criticals (#509 anonymous driver account
  takeover, #650 self-elevation to admin). Lists what to check in risk order, where each fix could have
  broken a legitimate caller, and the two deployment steps no gate can verify.

## Contexts
| Context | Hub | Status |
|---------|-----|--------|
| Customer Ordering | [[Customer Ordering/_context]] | **Fully triaged** — 8 feature groups covering all 37 controller areas (6 full/partial depth, 1 bridged to existing docs, 2 light-tier). **Phase 11 (2026-08-13) additionally read the full 6,235-line `Order.cs` handler body end-to-end** (not just route-mapped) — 10 new confirmed bugs, `_conflicts.md` #217-226, headlined by 3 instances of the same `?? 0 +` operator-precedence bug silently dropping a fee/contribution from a financial calculation |
| Restaurant Portal | [[Restaurant Portal/_context]] | **All 30 controllers read** (Phase 3) — findings include a controller with zero `[Authorize]` on any route (`_conflicts.md` #41), `StoresHub` bug, `UpdateRestaurant` unreachable, duplicate feature-flag endpoints, inconsistent ownership checks. **Phase 13 (2026-08-13) additionally read all 285 `.ts` files in this context's own frontend** (`TalabatkRestaurants/ClientApp`), file-by-file — ~26 new confirmed/likely bugs, `_conflicts.md` #243-254 |
| Admin | [[Admin/_context]] | **All 84 controllers read** (Phase 4, the largest host) — findings include the `[Authorize]`+`[AllowAnonymous]` contradiction (#45), 3 more fully-anonymous financial/write endpoints (#46), a route-parameter-ignored bug (#47), the feature-flag duplicate pattern confirmed across all 4 hosts (#48); shared entities (City, Configuration, StoreTypes, etc.) also done. **Phase 12 (2026-08-13) additionally read all 679 `.ts` files in this context's own frontend** (`AdminUi/ClientApp`), file-by-file — ~14 new confirmed/likely bugs, `_conflicts.md` #229-242, headlined by an `APP_INITIALIZER` config-load failure that hangs the entire app forever with no visible error (#240) |
| Identity & Access | [[Identity & Access/_context]] | **All 19 controllers read** (Phase 1) + **all 21 Razor views read** (Phase 6) — 2 confirmed bugs, one high-severity security gap (`RestaurantMobile` zero status checks), OTP grant flow fully traced; shared entities (Customer, DeliveryMen) also done. **Phase 11 (2026-08-13) additionally read `CustomerUserController.cs`'s full handler bodies** (its own host is `TalabatkAPIs`, but its two IDOR findings are Identity & Access-shaped) — 2 confirmed IDOR vulnerabilities, `_conflicts.md` #227-228 |
| Delivery | [[Delivery/_context]] | **All 21 controllers read** (Phase 2) + **all 17 Razor views read** (Phase 6) — 4th confirmed feature-flag duplicate, two distinct chat systems mapped, a possible webhook-routing gap (#40); shared entities (attendance, transactions, zones, assignment strategies) also done |
| Version API | *(out of scope — not requested)* | Not one of the 4 projects asked for in this pass (`AdminUi`, `Talabatk.IDS`, `TalabatkDelivery`, `TalabatkRestaurants`); `Talabatk.VersionAPI` has no `Shared/*` project references at all per `references/repo-map.md`, so it wouldn't reuse any of this session's shared-entity work anyway |
| *(cross-cutting — no single context)* | [[Admin/Admin Back-Office/_knowledge-graph]] (Application layer is documented inline in `_conflicts.md`, not a separate note) | **Phase 8 (2026-08-13): all 1,847 files in `Shared/TalabatkApplication/Commands`+`Queries`+`Feature`** individually read, zero skipped — the Application-layer business logic behind every controller above. 148 new confirmed findings, `_conflicts.md` #54-201, dominated by 3 repeat-offender patterns found dozens of times each: save-before-upload-then-orphaned-record, a fully-discarded `SaveChangesAsyncWithResult()` result with the handler still reporting success, and unguarded `.Value`/`FirstOrDefault()` derefs post-materialization |

## Phase 8–14 — the "True Zero-Gap Closure" effort (2026-08-13, spanning many sessions)
Everything below Phase 7's 154-controller milestone that this repo still had left to read, in Pile
A (individually read, no exceptions) / Pile B (grep-swept for the confirmed-boilerplate subset,
anything the sweep flags read individually) treatment:
- **Phase 8** — `Shared/TalabatkApplication/Commands` (675) + `Queries` (1,084) + `Feature` (88) =
  **1,847 files**, Pile A. `_conflicts.md` grew from #53 to #201.
- **Phase 9** — `Shared/TalabatkLogic/TalabatkModels/` (288 files), Pile B. 27 files the sweep
  flagged were read individually; 5 new findings, #202-206.
- **Phase 10** — `Shared/TalabatkData/` (2,162 files), Pile B. 34 real-logic files (services,
  `TalabatkContext`, `ChatContext`) read individually; `Mapping/` (236) and `Migrations/` (1,844)
  grep-confirmed 100% declarative boilerplate. 10 new findings, #207-216 — headlined by the
  audit-trail bug (#207).
- **Phase 11** — `TalabatkAPIs/Order.cs` (6,235 lines) + `Order.Partial.cs` + `CustomerUserController.cs`
  + the 7 remaining `TalabatkAPIs` Razor views, Pile A. 12 new findings, #217-228.
- **Phase 12** — `AdminUi/ClientApp` Angular frontend (679 `.ts` files), Pile A, file-by-file across
  10 sub-phases. 14 new findings, #229-242.
- **Phase 13** — `TalabatkRestaurants/ClientApp` Angular frontend (285 `.ts` files), Pile A,
  file-by-file across 8 sub-phases. 26 new findings, #243-254.
- **Phase 14 — final registry sync (this pass):**
  - `_conflicts.md`: verified — exactly 254 sequential entries, #1 through #254, no gaps or
    duplicates.
  - `_entity-index.md`: added the one registry-worthy discovery from Phase 10 (`TalabatkContext` as
    a Hub-typed infra entry, given its system-wide blast radius) plus a closing note explaining why
    Phases 8/9/11/12/13 otherwise added no new rows (their findings are behavior-level, already fully
    recorded in `_conflicts.md`, not new domain entities).
  - `_integrations.md`: added 6 newly-discovered external integrations from Phase 10's non-mapping
    service folders (Fawry payment gateway, Google Maps Directions API, an SMS OTP gateway, WhatsApp
    Business Cloud API, a RoboCall/IVR provider, Bitrix24 CRM) as rows #13-18.
  - `system-graph.html`: regenerated against the current 254-conflict, `TalabatkContext`-inclusive
    state — see that file's own note for what it visualizes.
  - Full wikilink resolution sweep: every wikilink across the vault's 103 markdown files was
    extracted (545 links total) and checked against the actual file tree — 5 were broken (4 real,
    1 a false-positive prose artifact), all fixed: a `Voucher.technical` link in `_conflicts.md` #236
    pointed at a nonexistent `Voucher/` folder instead of the real `Discounts & Coupons/Vouchers/`
    path; `Admin/City/City.business.md` and `.technical.md` both linked a nonexistent `Area/Area`
    file instead of the real `Area-and-Country.md`; `Delivery/DeliveryBouns/DeliveryBouns.technical.md`
    had a redundant, wrongly-pathed `Attendance/DeliveryMenShifts` link sitting right next to an
    already-correct link to the same target, so the broken one was de-linked to plain text.

## Round 2 — "True Zero-Gap Closure, Round 2" (2026-08-20, plan `shimmering-wiggling-trinket.md`)
Round 1's Phase 7/14 claimed complete coverage by enumerating specific named folders per phase; the
gap that started this round (`MartQuantityValidationService.cs`, never enumerated by any Round 1
phase despite living directly in `Shared/TalabatkApplication/Services/`) proved that approach missed
whole folders, not just edge-case files. This round instead built one fresh, uniform file manifest
across the 9 in-scope projects and diffed it against Round 1's own claimed coverage per project —
the governing plan file (`shimmering-wiggling-trinket.md`, outside this vault) records the exact
per-project gap sizes found this way.
- **Phase 1** — `Shared/TalabatkApplication`'s remaining folders (530 files: `Helper/`, `Services/`
  — including the chat-bot subsystem and `OnlinePaymentRefundService` now documented in
  `_entity-index.md` — `DomainEventsHandlers/`, `DTO/`, and 6 smaller feature folders). 18 new
  findings, `_conflicts.md` #255-272, headlined by the fail-open ERP quantity-validation bug (#263)
  that started this whole round and a `System.Random` used for OTP-style codes inside a namespace
  literally called "Encryption" (#271).
- **Phase 2** — `Shared/TalabatkLogic`'s remaining folders (239 files: `Enum/`, `DomainEvents/`,
  9 aggregate/strategy folders, 8 smaller folders). 6 new findings, #273-278.
- **Phase 3** — all of `Shared/SharedWeb` (34 files), never read by any Round 1 phase despite being
  one of the 9 in-scope projects from the start. 5 new findings, #279-283 — this round's first
  cluster of very-high-severity bugs: a 59-hour token-expiry unit bug (#279), a hardcoded OAuth
  client secret (#280), a report viewer that can never generate any report (#281), a completely
  no-op global exception handler (#282), and a legacy online-payment path that's a dead stub for
  every AdminUi-placed order (#283).
- **Phase 4** — `Shared/TalabatkData` reconciliation (13-file drift since Round 1's Phase 10 snapshot)
  + 2 `Scripts/` `.sql` files Round 1 had wrongly recorded as "0 files, empty." 1 new finding, #284.
- **Phase 5** — every host's non-controller `Helper`/`Reports`/root-level `.cs` files and several
  previously-unread Razor views, across `AdminUi` (175 files), `TalabatkAPIs` (60), `TalabatkDelivery`
  (53 + 1 new view), `TalabatkRestaurants` (62 + 11 views) — none of these folders were ever
  enumerated by Round 1 despite its "100% done" claim. 31 new findings, #285-315.
- **Phase 6** — the Angular root-level `.ts` files both frontends' Round 1 Phase 12/13 folder-only
  counting silently excluded (`AdminUi` 11 files, `TalabatkRestaurants` 7 files) — including
  `auth-guard.guard.ts` and both apps' OIDC redirect-callback components, security-relevant files
  with no evidence of ever being read. 5 new findings, #316-320.
- **Phase 7** — 11 `.resx` localization files across 5 hosts + 12 Angular CLI/build-boilerplate files
  (environments, `main.ts`, `polyfills.ts`, `test.ts`, e2e scaffold), none previously in scope
  anywhere. 4 new findings, #321-324 — including `AdminUi`'s production Angular bundle silently
  never running in production mode (#323).
- **Phase 8 — final registry re-sync (this update):**
  - `_conflicts.md`: script-verified — exactly 324 sequential entries, #1 through #324, no gaps or
    duplicates (one duplicate, #314, was found and fixed mid-round before this final check).
  - `_entity-index.md`: added 3 new domain concepts this round surfaced — the CustomerAdminChatBot
    subsystem, `OnlinePaymentRefundService`, and the AccFlex ERP quantity-sync flow (documented as
    4 distinct real paths, correcting an initial under-scoped grep that missed one).
  - `_integrations.md`: added 2 new rows — the AccFlex ERP mart-stock-sync mechanism (row 19) and the
    separately-gated AccFlex ERP GL financial-journal integration (row 20), correcting this round's
    own plan premise that both shared one feature flag.
  - This file (`_system-index.md`): rewrote the completion claim above to be honest and
    scope-qualified instead of repeating Round 1's overclaimed "100% done."
  - `system-graph.html`: regenerated (see below).
  - Full wikilink resolution sweep: see below.

## Round 3 — post-rebase reconciliation (2026-08-20)
Triggered by rebasing `KnowledgeGraph` onto `origin/master` immediately after Round 2 closed. Method:
never trust a phase's self-reported file count — establish coverage by diffing `git ls-tree` file
lists between Round 1's closing commit and current `HEAD`, and establish *reachability* of each
audit's scope by asking whether any sub-phase's **defined pattern** could actually have matched the
file. That second test is what surfaced the `Commands/` root and `POCOs/` gaps, which pure counting
had missed for two whole rounds.
- **Rebase intake** — 45 in-scope files touched by 11 incoming commits (`Low Quality Images`,
  `UnRevised Activation`, `out of stock`, 2 image-fallback fixes). All 10 new files read (Pile A);
  all 35 modified files triaged, with every one carrying an existing finding or line citation
  re-verified against its finding.
- **Structural gaps closed** — the 7 `Commands/` root files and the 4 `TalabatkModels/POCOs/` files.
  The POCOs turned out to be genuinely trivial pure-data shapes (the Pile B classification was right
  even though the folder was never named); the `Commands/` root files were **not** trivial and yielded
  2 confirmed bugs (#327, #328).
- **5 new findings, `_conflicts.md` #325-329**: #325 the `OutOfStock` search regression (very high —
  see above); #326 `ImageBankRootResolver` has already drifted from the `Startup.cs` wiring its own
  comment says to keep it in step with; #327 `UpdateRestaurantOfferCommand`'s request-controlled
  unguarded `FirstOrDefault(...)` dereference; #328 `UnConfirmOrderCommand` guards the multi-restaurant
  case but not the zero case before `.First()`; #329 the new `RemoveAsync` bulk-delete is gated only
  by a `_low` filename suffix (safe as operated — dry-run defaults on — but irreversible).
- **1 finding narrowed, not closed** — #205, see above.
- **2 stale line citations corrected** — `SharedWeb Services.cs:62→63` (finding #283's DI-tracing
  evidence) and `Talabatk.IDS/Startup.cs:455→456` (`_entity-index.md`'s ERP sync-job reference). Every
  other citation into a rebase-modified file was checked and still resolves correctly.
- **1 new domain concept registered** — the Low-Quality Image (`_low` companion) subsystem, in
  `_entity-index.md`, because it introduces a storage-layer naming convention that nothing in the
  database records and is therefore invisible to schema-only reading.
- Noted but deliberately **not** logged as new numbered findings, per the standing "don't re-log
  instances of an already-tracked systemic pattern" rule: `UploadImage` is now duplicated 5× across
  hosts with identical new low-quality-generation logic (the #3 duplication family), and
  `UpdateRestaurantOfferCommand` also exhibits the tracked ignored-`TryParseExact` (#136 family) and
  save-before-upload-orphan patterns.

## Features
| Context | Feature | Business overview | Technical graph | Entities | Shared with |
|---------|---------|----------------------|--------------------|----------|--------------|
| Customer Ordering | Tiered Discount | [[Customer Ordering/Tiered Discount/_overview]] | [[Customer Ordering/Tiered Discount/_knowledge-graph]] | TieredDiscount, TieredDiscountTier, TieredDiscountRestaurant, TieredDiscountCustomer, TieredDiscountSegment | Admin (write path) |
| Customer Ordering | Cart & Checkout | [[Customer Ordering/Cart & Checkout/_overview]] | [[Customer Ordering/Cart & Checkout/_knowledge-graph]] | CustomerCart, CartItem, CartItemOptions | Tiered Discount (lock), Order & Fulfilment (not yet documented), Identity & Access (guest merge) |
| Customer Ordering | Discounts & Coupons | [[Customer Ordering/Discounts & Coupons/_overview]] | [[Customer Ordering/Discounts & Coupons/_knowledge-graph]] | PromoCodes, Vouchers | Cart & Checkout (checkout-time read), Order & Fulfilment |
| Customer Ordering | Order & Fulfilment (**partial** — Customer Ordering slice only) | [[Customer Ordering/Order & Fulfilment/_overview]] | [[Customer Ordering/Order & Fulfilment/_knowledge-graph]] | Order (partial), OrderRestaurantDetails (partial) | Cart & Checkout, Discounts & Coupons, Tiered Discount; Restaurant Portal / Delivery / Admin (not documented — Order is shared with all three) |
| Customer Ordering | Restaurant & Menu Discovery (**partial** — browsing slice only) | [[Customer Ordering/Restaurant & Menu Discovery/_overview]] | [[Customer Ordering/Restaurant & Menu Discovery/_knowledge-graph]] | Restaurant (partial), MenuItem (partial) | Cart & Checkout, Tiered Discount; Restaurant Portal (not documented — manages these same entities) |
| Customer Ordering | Customer Account | [[Customer Ordering/Customer Account/_overview]] | [[Customer Ordering/Customer Account/_knowledge-graph]] | (controller-level map, no dedicated aggregate documented) | Discounts & Coupons (Voucher source) |
| Customer Ordering | Support & Chat | [[Customer Ordering/Support & Chat/_overview]] | [[Customer Ordering/Support & Chat/_knowledge-graph]] | *(none — bridges to existing `docs/CHAT_*.md`, not re-documented here)* | Cart & Checkout (shared guestDeviceId mechanism, confirmed) |
| Customer Ordering | Marketing & Content (light tier) | [[Customer Ordering/Marketing & Content/_overview]] | *(none — controller map only)* | *(none)* | — |
| Customer Ordering | Ops & Infra | [[Customer Ordering/Ops & Infra/_knowledge-graph|Ops & Infra]] | *(none of its own — reads City and Area)* | #616 | The light-tier note that used to sit here was deleted 2026-08-24: it was superseded by the feature note, and two of the four controllers it claimed were in fact mapped to Payments and Order & Fulfilment |
| Delivery | Delivery Man Operations | [[Delivery/Delivery Man Operations/_overview]] | [[Delivery/Delivery Man Operations/_knowledge-graph]] | DeliveryMen, OrderDelivery, DeliverymanTransaction (all pre-existing) | Identity & Access (DeliveryMen identity), Admin (announcements/notifications) |
| Restaurant Portal | Menu & Order Management | *(none — technical graph only, no separate business overview)* | [[Restaurant Portal/Menu & Order Management/_knowledge-graph]] | (all 30 controllers, mapped to already-documented entities) | Customer Ordering (Order, MenuItemPrice), Delivery (ExternalDeliveryRequests) |
| Admin | Admin Back-Office | *(none — technical graph only, no separate business overview)* | [[Admin/Admin Back-Office/_knowledge-graph]] | (all 84 controllers, mapped to already-documented entities) | Every other context — Admin is the back-office for nearly all shared reference/config entities |
| Identity & Access | Login & Activation | *(none — technical graph only, no separate business overview)* | [[Login-and-Activation]] | Customer, DeliveryMen (login/activation paths only, not full entity docs) | Every other context — issues the JWTs each API host validates |

## What this pass proved (Customer Ordering / TalabatkAPIs, all 37 controller areas triaged)
- The context-first vault structure, the `CONTEXT.md`-linking convention, the entity-recognition
  patterns, and the conflict-hunting method in `SKILL.md` all worked against real code without
  needing further adjustment across 6 full/partial feature passes.
- Depth was deliberately **scaled to actual rule density**, not uniform: `Order` (6,235 lines) and
  `CustomerUserController` (32 routes) got scoped, explicitly-partial coverage rather than
  exhaustive line-by-line treatment; Marketing/Content and Ops/Infra got controller-map-only
  treatment; Support & Chat was **bridged to this repo's own excellent existing `docs/CHAT_*.md`
  and `docs/items-replacement.md`** rather than duplicated — extending the skill's "don't
  re-document what already has a canonical source" principle to non-KB docs too.
- Found one integration mechanism the skill's `references/repo-map.md` hadn't anticipated (a shared
  Application/Data library invoked independently by two hosts against the same DB, no network call).
- **Confirmed one repo-wide pattern, not three unrelated bugs:** `CustomerCart.CustomerId` and
  `PromoCodes.Promo` both rely on application-level uniqueness with no matching DB constraint —
  recorded as a systemic theme in `_conflicts.md`, not three separate line items.
- **Confirmed one repo-wide code-duplication pattern:** the same rule implemented twice
  independently, found in `Order`'s auto-approve gate (`CreateOrderFromCustomerCart` vs.
  `InitializeOrderStatus`) and `MenuItem`'s stock toggle (`UpdateStockQuantity` vs. `MaintainStock`)
  — a drift risk worth a team conversation about consolidating.
- **Found 1 confirmed, high-confidence bug**, not just a risk flag: `UserPreferencesController`
  always returns an empty list regardless of its feature flag, due to a hardcoded-`false` field
  that's never reassigned.
- **Resolved a real ambiguity `CONTEXT.md` had already flagged as open:** "Coupon" genuinely refers
  to 3 distinct mechanisms (PromoCodes/Vouchers/TieredDiscount), though the *code itself* — not just
  user language — conflates PromoCode and Voucher naming throughout.
- **Corrected an initial guess mid-pass:** first assumed `IRecycleRedeems` was the loyalty-points
  redemption source for Vouchers; confirmed instead it's an unrelated external recycling-partner
  wallet-credit integration, and the real source is `CustomerUserController.RedeemPoints`. Fixed at
  the point of discovery rather than left inconsistent.
- 1 stale-docs finding: `CONTEXT.md`'s Guest Mode section says "not implemented yet" for a feature
  that has since shipped (confirmed via migrations, commands, and tests).
- Full tally: **11 conflict/gap entries** in `_conflicts.md` across 6 features.
