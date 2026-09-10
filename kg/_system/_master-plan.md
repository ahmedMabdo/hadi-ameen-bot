---
id: 8orders/system/master-plan
title: 8Orders KG — Master Completion Plan
note_type: system
last_updated: 2026-08-23
tags: [system, master-plan]
status: approved-for-implementation
author: planning session 2026-08-22 (Fable 5), implementer: Opus 5
---

# 8Orders Knowledge Graph — Master Completion Plan

> **The one rule this plan lives by:** no phase after Phase 0 is sized by estimate. Phase 0 builds
> `verify-notes.js`, runs it, and its output — a named list of gaps — becomes the work queue for
> everything after. "Finished" = four commands exit clean at one commit. That is the whole design;
> everything below is the detail.

## Definition of done (commands, not prose)

```
node docs/knowledge-graph/_system/verify-coverage.js     → exit 0
node docs/knowledge-graph/_system/verify-notes.js        → exit 0
node docs/knowledge-graph/_system/audit-inbox-merge.js   → 0 unlanded
node docs/knowledge-graph/_system/verify-notes.js --register-check → sequential, no gaps, no duplicates
```

All four green at a given commit = KG finished, and re-provable at any later commit. The four
acceptance questions map to these commands — see the traceability matrix at the end of this plan.

A fifth command was added during execution and is now part of the gate — see the Progress tracker:

```
node docs/knowledge-graph/_system/verify-citations.js       → HARD failures 0
```

## ✅ ALL GREEN — 2026-08-24, commit `4bb72688d`

> **The 2026-08-23 "all green" was true of the gates as they then existed, and that turned out to be
> the qualification that mattered.** A follow-up audit on 2026-08-24 tested the checkers against
> independent signals instead of re-reading their output, and found four defect classes they could not
> see — one of them an unimplemented line of this plan's own spec (see Denominator 1). Phase 11 below
> records it. The gates now check more than they did, and the numbers in this file are measured at the
> commit named above.

Every gate command passes. Copy-paste to re-prove it at any commit:

```bash
node docs/knowledge-graph/_system/verify-notes.js --self-test       # 40/40 failure classes detectable
node docs/knowledge-graph/_system/verify-notes.js                   # NOTES OK
node docs/knowledge-graph/_system/verify-notes.js --register-check   # REGISTER OK
node docs/knowledge-graph/_system/verify-citations.js                # CITATIONS OK (0 HARD)
node docs/knowledge-graph/_system/verify-citations.js --self-test    # 5/5 + a valid citation accepted
node docs/knowledge-graph/_system/verify-coverage.js                 # COVERAGE OK
node docs/knowledge-graph/_system/audit-inbox-merge.js               # 0 unlanded
```

**1,260 problems → 0**, across all twelve gap classes. Findings grew **605 → 650** rows while closing
them, because closing a gap means reading the code the gap was hiding — and the last 12 of those came
from auditing the closers themselves (Phase 11).

### The four acceptance questions, answered by a command rather than an opinion

| Question | Answer | What proves it |
|---|---|---|
| Does the plan have gaps? | **No known gaps, and the checks that would find them are stronger than they were** | `verify-notes.js` prints 0 problems and `--self-test` proves all 40 failure classes are detectable, so a zero means "checked". The honest caveat: this was also true on 2026-08-23, when three of those classes did not yet exist and the entity denominator could not see 225 files. A zero is only as wide as the denominators behind it — which is why Phase 11 audited them from the outside |
| Is the KG 100% finished? | **Yes**, for the 9 in-scope projects | **529** entity candidates (the whole domain layer, widened in #639 from an allow-list that asked about 304) → 243 documented + 286 excluded each with stated evidence, **0 without a note**; 198 of 198 entry points mapped, cross-checked against class declarations rather than paths; 31 of 31 features complete; 0 stubs |
| Can we depend on it to answer any tech or business question about existing code? | **Yes**, with one stated limit | **4,245** citations, 0 pointing at code that does not exist and **154 of them now naming their file in full** rather than by an ambiguous basename; **686** register rows all reachable from a note; 95 glossary terms; **14,358** files enumerated with 0 unclassified. The limit: **572** judgement leads remain triageable but ungated (down from 664 — see Phase 11 for why that number moved and what it was hiding), and `sweep-only` depth does not mean read line-by-line — see `_system-index.md`'s tiered claim |
| After a rebase from master, is it easy to maintain? | **Yes** | [[REBASE-PLAYBOOK\|REBASE-PLAYBOOK.md]], rehearsed against real drift: 30 files changed on master, 5 of them cited, and the reverse index named exactly 20 note↔file pairs to re-verify |

---

# Progress tracker

> **Updated 2026-08-23.** Numbers come from the verifiers, not from judgement. Completed phases are
> struck through below. Re-generate this block by running the five commands above.

| Phase | Scope | Status | Landed at |
|---|---|---|---|
| **0** | `verify-notes.js` + the three denominators | ✅ **done** | `9900087ce` |
| **0b** | `verify-citations.js` (added during execution — not in the original plan) | ✅ **done** | `bc89cc7f7` |
| **1** | Structural normalisation, frontmatter, integrations | ✅ **done** | `b9f085315` |
| **2** | Restaurant Portal — 4 features | ✅ **done** | `c89f0ad77` |
| **3** | Order & Fulfilment (already complete at baseline) + Payments | ✅ **done** | `bc89cc7f7` |
| **4** | Identity & Access — 5 features | ✅ **done** (5 of 5) | `18c212bfb` |
| **5** | Delivery — 4 features | ✅ **done** (4 of 4) | `75fc1ed6a` |
| **6** | Admin — 8 features | ✅ **done** (8 of 8) | `307040fdd` |
| **7** | Customer Ordering remainder — 4 features | ✅ **done** (4 of 4) | `fb841fae2` |
| ~~**8**~~ | Register backfill (450 rows) + folded entities (148) | ✅ **done** | `051b9e1da`, `c19ba47a6`, `4e1033446`, `d2ae4b72e` |
| ~~**8b**~~ | Stub notes (3) + citation HARD failures (140) | ✅ **done** | `7ecdb3799`, `9740209fc`, `989a78d3c` |
| ~~**9**~~ | Graphs + system layer resync | ✅ **done** | `5c902157b` |
| ~~**10**~~ | Rebase playbook + rehearsal | ✅ **done** | `d20932679` |
| ~~**11**~~ | **Audit of the closers** (not in the original plan — added because "all green" needed testing from outside) | ✅ **done** | `03f39eb6d`, `75db7485d`, `4bb72688d` |

## Measured position

Measured at `d20932679`. Every number below is printed by `verify-notes.js`,
`verify-citations.js` or `verify-coverage.js` — none is a judgement.

| Metric | Baseline | Now | Target |
|---|---|---|---|
| **Total problems** | **1260** | **0** ✅ | 0 |
| Features complete | 5 of 31 | **31 of 31** ✅ | 31 |
| Missing feature files | 93 | **0** ✅ | 0 |
| Entities with no note at all | 56 | **0** ✅ | 0 |
| Frontmatter problems | 398 | **0** ✅ | 0 |
| Broken wikilinks | 4 | **0** ✅ | 0 |
| Unregistered integrations | 4 | **0** ✅ | 0 |
| Stale citations | (unmeasurable) | **0** ✅ | 0 |
| Unstamped citations | (unmeasurable) | **0** ✅ | 0 |
| Register rows linking no note | 447 | **0** ✅ | 0 |
| Folded entities not written up | 205 | **0** ✅ | 0 |
| Stub notes | 2 | **0** ✅ | 0 |
| Citation HARD failures | (unmeasurable) | **0** ✅ | 0 |
| Coverage drift (cited files changed) | (unmeasurable) | **0** ✅ | 0 |
| Files enumerated / unclassified | 14076 / 0 | **14353 / 0** ✅ | 0 unclassified |
| Register rows | 605 | **670** (`_conflicts.md` alone: 635) | sequential, no gaps |

**All twelve gap classes are closed.** What deliberately remains, and why:

- **664 citation leads.** `CITE-SYMBOL-ABSENT` (409) fires when a symbol named in prose is not within
  12 lines of the citation — often correct, e.g. a row naming a method and citing its caller.
  `CITE-BASENAME-AMBIGUOUS` (now 117) fires on a bare filename several tracked files share.
  ~~Neither is mechanically decidable, so neither gates.~~ **That justification was wrong about the
  second class and the audit disproved it (#647).** A bare-basename citation is not undecidable, it is
  *unfalsifiable* — the checker cannot verify a line in a file it cannot identify, which is not the same
  as the citation being unknowable. Measured against what each note already carried, **76% were
  decidable**: 154 from exactly one candidate path in the note's own `sources:`, 12 from a full path
  elsewhere in the note, 40 from only one candidate having code at the cited line. The 154 strong ones
  were expanded, and **five then failed immediately** — three named the wrong same-basename file, two
  had stale line numbers. So the class was not neutral; it was hiding a ~3% error rate behind
  unverifiability. The remaining 117 are genuinely undecidable from the note alone: they cluster on
  names that exist once per host (`Startup.cs`, `OrderController.cs`, `appsettings.json`), where
  nothing in the note picks the host. `CITE-SYMBOL-ABSENT` (455) remains a true judgement class.
- **The tiered coverage claim.** `sweep-only` depth (241 files) does not mean unread, and `read` does
  not mean read line-by-line by a human. `_system-index.md` states this in tiers with the evidence for
  each; quote from there, not from a single number.
- **The #509 code fixes.** Still a documentation-only effort by design — see the decision below.

## Execution notes — what changed about *how* the plan runs

1. **Sub-agents do not work in this environment.** Two waves were attempted (6 agents, then 2). All
   eight produced **0 files, 0 inbox reports and 0-byte transcripts** — they stalled on a 600-second
   watchdog during their reading phase, before any tool result returned. Because the brief forbade
   agents from touching any register, a total failure was also a harmless one: nothing to unpick.
   **Phases 4–10 are therefore solo.** The "no sub-agents for KG work" standing preference is back in
   force, now with a mechanical reason behind it rather than a preference.
2. **`verify-citations.js` was added** (Phase 0b) because the original plan's checks could prove
   nothing was *missing* but not that what was written was *true*. Its first run found **138 wrong
   citations in the pre-existing KG** — 55 pointing past the end of their file, 48 at blank lines,
   20 at files git does not track, 15 at paths abbreviated so no machine can resolve them. Fixing
   those is folded into Phases 4–7 (each note is corrected as its feature is worked) with a sweep in
   Phase 9.
3. **Findings grew during documentation, as intended.** #606–#608 (Restaurant Portal tenant scoping)
   and #609–#610 (unauthenticated FCM-token disclosure and rider-queue exposure, both in the same file
   as #509) were found by reading code the register had not covered. Register: 605 → 645 rows.
4. **Three checker holes were found and closed by their own output** — a path-form wikilink accepted on
   basename alone, a `covers:` list verified against text that included itself, and a feature folder
   identified by its contents rather than by the feature map. Each had been silently passing work.

## Scope

**The 9 in-scope projects** (the non-test, non-legacy `.csproj` set):
`AdminUi`, `Shared/SharedWeb`, `Shared/TalabatkApplication`, `Shared/TalabatkData`,
`Shared/TalabatkLogic`, `Talabatk.IDS`, `TalabatkAPIs`, `TalabatkDelivery`, `TalabatkRestaurants`.

Excluded, per the standing coverage manifest (`_coverage-manifest.md`, attested at `dca0bd06f`):
`TalabatkAPI` + `TalabatkAPI.Data` (legacy, `excluded:legacy-project-user-instruction`), the three
`*.Test` projects, `Talabatk.VersionAPI` (`excluded:out-of-scope-user-instruction`).

**Hard constraints carried from the work order:**
- No source-code edits. Only `docs/knowledge-graph/**` (KG artifacts + its own tooling).
- Never run unbounded `find` — `git ls-files` or scoped `find <dir>` only (documented trap,
  `verify-coverage.js` header).
- Quote every path in every shell loop — 102 of the note paths contain a space or `&`.
- Never edit wikilinks with `sed` — escaped-pipe `\|` links corrupt; use the Edit tool
  (documented failure, memory `feedback_sed_wikilink_corruption`).
- Folder names with spaces/`&` are **per-spec** (exact `CONTEXT-MAP.md` names, Obsidian vault).
  Do not rename. Two note shapes (aggregate-root pair vs. single file) are **per-spec**. Do not
  "normalize" them.
- Reuse existing machinery: `_depth-ledger.tsv` (`@list:` support, mandatory evidence),
  `verify-coverage.js` (git enumeration, sha1 drift, two-tier severity),
  `audit-inbox-merge.js` (report→register reconciliation). Never reinvent.

---

# ~~Phase 0 — Make "finished" computable: `verify-notes.js`~~ ✅ DONE (`9900087ce`)

> **Landed.** `verify-notes.js` exists with 32 self-tested failure classes; both bridge files are
> populated (305 entity rows, 198 controller rows); `_gap-baseline.md` recorded the first real
> numbers. Everything below is kept as the record of what was built and why.

**Everything else waits for this.** Three weeks were lost because the knowledge axis had no
denominator; every round guessed what was left. This phase replaces the guess with a command.

## 0.1 The three denominators, each derived from code

`verify-notes.js` lives at `docs/knowledge-graph/_system/verify-notes.js`, modelled directly on
`verify-coverage.js` (same repo-root resolution, same `git ls-files` enumeration, same two-tier
severity, same `--generate` / verify split). **Expectation always comes from code; observation
always comes from disk. Never both from the same source** — that circularity produced two false
"all clear" results already (see `audit-inbox-merge.js` header lines 1–13, and the
`cshtml`-before-`cs` alternation bug that hid two landed findings).

### Denominator 1 — Entities

**Candidate set — as originally specified, and what actually got built:**

> ⚠️ **This spec was only two-thirds implemented, and the missing third is what broke it (#639).**
> Kept here verbatim because the gap between a plan and its implementation is the thing nobody was
> checking.
>
> 1. ~~Class files in the 4 aggregate folders … (exclude their `POCOs/` input-DTO subfolders).~~
>    Implemented — including the exclusion, which is exactly how `TieredDiscountTierPoco.cs` went
>    missing, and the folder anchor `[^/]+\.cs$` dropped anything one level deeper.
> 2. ~~`git ls-files "Shared/TalabatkLogic/TalabatkModels/*.cs"` — 290 files at plan time.~~ Implemented.
> 3. **EF-mapped names: strip `Map`/`Maping` from `Shared/TalabatkData/Mapping/*.cs` … plus `DbSet<X>`
>    declarations parsed from `TalabatkContext.cs` and `ChatContext.cs`. — NEVER IMPLEMENTED.**
>    `candidateEntityFiles` only ever did 1 and 2. Input 3 was the *independent signal* — the one
>    derivation not keyed on paths — and without it the denominator was a pure allow-list that agreed
>    with itself. It is precisely what would have surfaced `Shared/TalabatkLogic/AccountingEntry.cs`,
>    a keyed `TA_AccountingEntry` table sitting at the domain-layer root, four days earlier.

**Candidate set as it now stands:** every `.cs` file under `Shared/TalabatkLogic/` — **529**, no
allow-list, no folder anchor. Each needs a row that is either a documented class or an excluded one
with a stated reason, so `ENTITY-UNCLASSIFIED` is a real signal instead of a guaranteed empty set.
Two classes were added for the newly visible files: `domain-event`, and `domain-behaviour` for
strategies, calculators and scheduled jobs that *are* rule-bearing but are not entities — the latter
gated by `ENTITY-BEHAVIOUR-UNDOCUMENTED`, which requires its `evidence` to name a note that resolves.
Spec input 3 survives as the **cross-check** rather than as candidate input: derive the set from
`DbSet<T>` and class declarations, diff against the path-derived set, and expect the difference to be
empty or explained. Run that diff after any rebase that adds domain files.

**Classification bridge — `_system/_entity-classes.tsv`** (same design as the proven
`_depth-ledger.tsv`: a hand-reviewed file the verifier *validates in both directions*, so it can
carry judgment without being able to hide a gap):

```
# entity <TAB> source_path <TAB> class <TAB> shape <TAB> context <TAB> feature <TAB> evidence
Order	Shared/TalabatkLogic/TalabatkModels/Order.cs	legacy-poco-root	pair	Customer Ordering	Order & Fulfilment	hub entity, event-raising
TieredDiscount	Shared/TalabatkLogic/TieredDiscountAggregate/TieredDiscount.cs	aggregate-root	pair	Customer Ordering	Tiered Discount	DDD aggregate, Create factory
CartItemOptions	Shared/TalabatkLogic/TalabatkModels/CartItemOptions.cs	child	covered-by:CartItem	Customer Ordering	Cart & Checkout	documented inside CartItem.md
ReadyOrder	Shared/TalabatkLogic/TalabatkModels/ReadyOrder.cs	projection	none	—	—	SP projection, no invariants (pathA-A-models-batch04-final.md)
AspNetUserRole	Shared/TalabatkLogic/TalabatkModels/AspNetUserRole.cs	identity-framework	none	—	—	ASP.NET Identity plumbing, no business rules
```

Valid `class` values: `aggregate-root` · `legacy-poco-root` · `child` · `lookup` (the skill's four
types) plus the excluded classes `projection` · `join-table` · `enum-only` · `identity-framework` ·
`keyless-view`. Valid `shape`: `pair` (business + technical file), `single` (one `.md`),
`covered-by:<Entity>` (folded into a canonical note), `none` (excluded classes only — and the
`evidence` column is then **mandatory**, loader rejects a `none` with no reason, exactly like the
depth ledger rejects an evidence-free line).

**Seed data for the excluded rows** (do not re-derive — already measured):
`_inbox/pathA-A-models-batch04-final.md` names the ~50 SP-projection shapes (full list in its
"Full list, for the KG classification" section, including the 4 keyless `HasNoKey().ToView(null)`
types registered at `TalabatkContext.cs:98-101`), the ~20 one-line join-table factories, the
Identity subclasses (`AspNetUserRole`, `AspNetUserLogin`, `AspNetUserClaim`, `AspNetUserTokens`,
`AspNetRoleClaims`), and the enum-only files (`RecommendationEventType.cs` etc.). The same report's
key correction: **the genuine domain surface in TalabatkModels is ~130 files, not 290** — the tsv
records that per-file so the number is no longer a prose claim.

**Verifier cross-checks (all four directions — this is what prevents self-verification):**
- Candidate-set member with no tsv row → **FAIL** (`ENTITY-UNCLASSIFIED`).
- tsv row whose `source_path` is not in `git ls-files` → **FAIL** (`ENTITY-STALE-ROW`).
- Row with shape `pair`/`single` and no matching note(s) on disk → **FAIL** (`NOTE-ABSENT`).
- Note on disk claiming an entity (frontmatter `entity:` or filename) with no tsv row → **FAIL**
  (`NOTE-ORPHAN`).
- `covered-by:` target must exist and its frontmatter `covers:` list must include this entity →
  **FAIL** (`COVERS-MISMATCH`) otherwise.

### Denominator 2 — Features

**Candidate set (from code):** every controller file across the 6 hosts —
`git ls-files "TalabatkAPIs/Controllers/*.cs" "TalabatkRestaurants/Controllers/*.cs"
"TalabatkDelivery/Controllers/*.cs" "AdminUi/Controllers/*.cs" "Talabatk.IDS/Controllers/*.cs"
"Talabatk.VersionAPI/Controllers/*.cs"` (41 + 30 + 21 + 84 + 19 + 3 = **198 files** at plan time).
Controllers are the system's entry points; every one must belong to exactly one documented feature.

**Bridge file — `_system/_feature-map.tsv`:**
```
# controller_path <TAB> context <TAB> feature <TAB> evidence
TalabatkAPIs/Controllers/CartController.cs	Customer Ordering	Cart & Checkout	cart CRUD entry point
Talabatk.VersionAPI/Controllers/VersionsController.cs	Version API	excluded:out-of-scope-user-instruction	matches coverage manifest exclusion
```

**Verifier checks:**
- Controller in git with no map row → **FAIL** (`CONTROLLER-UNMAPPED`).
- Map row whose path left git → **FAIL** (`FEATURE-MAP-STALE`).
- Every non-excluded feature named in the map must have all four required files on disk:
  `_overview.md`, `_knowledge-graph.md`, `_scenarios.md`, `<feature>-context-graph.html` →
  **FAIL** (`FEATURE-INCOMPLETE`, names the missing file).
- Feature folder on disk that appears in no map row → **FAIL** (`FEATURE-ORPHAN`).
- Every feature folder's parent must be a context folder; a folder containing `<X>.business.md` /
  `<X>.technical.md` directly under a context (entity at feature depth) → **FAIL**
  (`ENTITY-AT-FEATURE-DEPTH`). This makes structural defect #1 machine-detected, permanently.

### Denominator 3 — Flows (cross-context behavior)

**Decision (explicit, closing structural defect #2): `_flows/` is dropped.** The skill defines no
`_flows/` concept; its `_scenarios.md` Integration section is the specified home for "what happens
across contexts". The empty `docs/knowledge-graph/_flows/` directory is deleted in Phase 1. Flow
knowledge lands as Integration rows in the owning feature's `_scenarios.md`.

**Candidate set (from code + the integration register):** every row of `_system/_integrations.md`
(itself sourced from `DomainEventsHandlers` / `MapHub` / Hangfire scans per `repo-map.md`).
**Verifier check:** every integration register row's id must be cited in at least one
`_scenarios.md` Integration-section row or one `.technical.md` Cross-Context Integrations table →
**FAIL** (`INTEGRATION-UNTRACED`). Expectation = register (which cites code); observation = the
scenario/technical notes. To keep the register itself honest, `--generate` re-runs the mechanical
scan (grep `ApiClientHandler` calls in `DomainEventsHandlers`, `MapHub` in `Startup.cs`,
`BackgroundJob.Schedule` sites) and fails on any hit absent from the register
(`INTEGRATION-UNREGISTERED`).

## 0.2 Note-level checks (the rest of the verifier)

For every `.md` under `docs/knowledge-graph/` except `_system/_inbox/` and generated manifests:

1. **Frontmatter present and schema-valid** → **FAIL** (`FRONTMATTER-MISSING` / `-INVALID`).
   Schema in §0.3. (18 files lack frontmatter today, including 11 `_knowledge-graph.md` files.)
2. **Stale citation:** frontmatter `sources:` lists each cited file with its git blob sha1
   (`git ls-tree HEAD -- <path>`, same mechanism as `verify-coverage.js`). Mismatch → **FAIL**
   (`CITATION-STALE`, names note + file). Files mentioned in the body but not declared in
   `sources:` → informational, two-tier like coverage.
3. **Broken wikilink:** every wikilink (bare or aliased) must resolve to a note in the vault
   → **FAIL** (`WIKILINK-BROKEN`). Resolution follows Obsidian rules (basename match, path match).
4. **Stub detection:** a `.technical.md` (or `single`-shape note) for a `class` that carries rules
   (`aggregate-root`, `legacy-poco-root`) with `rule_count: 0` or no Rule/Decision Matrix section
   → counted as **stub**, and stubs > 0 → **FAIL** (`NOTE-STUB`). `child`/`lookup` notes may
   legitimately have zero rules — the tsv `class` decides the expectation, per-type, per-spec.
5. **Register linkage:** every row in `_conflicts.md` and `_idor-instances.md` must contain at
   least one resolvable wikilink in its Entity column (linking the entity note, or the owning
   feature's `_knowledge-graph` for controller-level findings) → **FAIL** (`REGISTER-UNLINKED`).
   147 rows fail this today; Phase 8 closes them.
6. **`--register-check`:** `_conflicts.md` numbering sequential from 1, no gaps, no duplicates
   (605 rows today, clean — this keeps it provably so).
7. **Required-file completeness** per feature and context: each of the 6 contexts has `_context.md`
   (5 exist; `Version API` created in Phase 1) → **FAIL** (`CONTEXT-MISSING`).

**Output format** (mirrors `verify-coverage.js`): a summary block —

```
entities: <n> total · <n> need-note · <n> noted · <n> excluded (with reasons)
depth:    rules-extracted <n> · stub <n> · absent <n>
features: <n> total · <n> complete · <n> incomplete (named)
flows:    <n> integrations · <n> traced · <n> untraced
notes:    <n> · frontmatter-valid <n> · stale-citations <n> · broken-links <n>
register: <n> rows · <n> linked · <n> unlinked
```

— then one line per failure with its code and path. Exit 0 only when every FAIL class is empty.

`--generate` mode writes `_system/_source-index.tsv` (reverse index: `source_path <TAB> sha1 <TAB>
note_path`, one row per citation — "file X changed, which notes are stale?" becomes a lookup) and
refreshes the sha1s it derives; it never invents classification rows — those are human-authored,
verifier-validated.

## 0.3 Frontmatter schema (the AI-agent contract, applied now, consumed later)

Every note gets this (Phase 1 backfills existing notes; all new notes born with it):

```yaml
---
id: 8orders/customer-ordering/order-fulfilment/order.technical   # stable; NEVER changes on rename/move
entity: Order                       # omit on _overview/_context/_scenarios/_knowledge-graph
entity_type: legacy-poco-root       # tsv `class`; omitted on non-entity notes
note_type: technical                # business|technical|single|overview|knowledge-graph|scenarios|context
context: Customer Ordering
feature: Order & Fulfilment
side: backend-domain                # skill's side taxonomy
covers: [OrderDetails, OrderStatusLog]   # entities folded into this canonical note, if any
sources:
  - path: Shared/TalabatkLogic/TalabatkModels/Order.cs
    sha1: <git blob sha1>
rule_count: 23
last_updated: 2026-08-22
tags: [customer-ordering, order-fulfilment, transactional, technical, backend-domain]
---
```

`id` is the machine-stable key: wikilinks may break on a rename, `id` never does — the verifier
maintains `_system/_id-index.tsv` (`id <TAB> current_path`) in `--generate` so any consumer (the
future chat agent) resolves ids to paths in one lookup. This is the entire AI-readiness deliverable:
machine-readable frontmatter, stable ids, resolvable links — designed now, consumed later, nothing
else to build.

## ~~0.4 Phase 0 exit criteria~~ ✅ all met

- `verify-notes.js` exists, passes a self-test (`--self-test` flag: plant one synthetic gap of each
  FAIL class in a temp dir, assert each is caught — the checker proves it can see before its "all
  clear" is trusted; this is the lesson of `feedback_coverage_checker_circularity` made executable).
- `_entity-classes.tsv` and `_feature-map.tsv` fully populated (every candidate row classified;
  evidence on every exclusion).
- First real run executed; its output committed as `_system/_gap-baseline.md` (a snapshot, marked
  machine-generated). **Every phase below is then re-sized from that file's real numbers.** The
  estimates given below are planning aids only and are expected to be replaced.

---

# ~~Phase 1 — Structural normalization (cheap, mechanical, do before content)~~ ✅ DONE (`b9f085315`)

> **Landed.** 12 entity folders and 23 loose notes moved into owning features; `_flows/` removed;
> `Version API/_context.md` written; frontmatter + 1,482 stamped citations across all notes;
> 734 wikilinks rewritten; 4 unregistered Hangfire integrations found and registered as rows 21-24.

All items verifier-backed — each fixes a named FAIL class.

1. **Move the 12 entity folders at feature depth** into owning features (`git mv`, wikilinks fixed
   with the Edit tool, never sed):
   - `Admin/City`, `Admin/CityRushTimeConfiguration`, `Admin/Configuration`, `Admin/StoreTypes` →
     into Admin features created in Phase 6's layout (interim: `Admin/Admin Back-Office/` is the
     existing feature; final feature assignment decided by `_feature-map.tsv` when Admin's
     84 controllers are mapped — do the move once, after the map exists, not twice).
   - `Delivery/DeliveryBouns`, `Delivery/DeliverymanTransaction`, `Delivery/OrderDelivery` →
     `Delivery/Delivery Man Operations/` (or a new Delivery feature per the map).
   - `Identity & Access/Customer`, `CustomerAddress`, `DeliveryMen`, `Identity`, `Permission` →
     Identity & Access features per the map (verified: all five sit at feature depth today).
   Update `_entity-index.md` canonical paths in the same commit.
2. **Delete empty `_flows/`** (decision recorded in §Denominator 3).
3. **Create `Version API/_context.md`** — a minimal context hub stating: context exists per
   `CONTEXT-MAP.md`/skill; project `Talabatk.VersionAPI` is `excluded:out-of-scope-user-instruction`
   in the coverage manifest; fully standalone (no `Shared/*` references, 3 controller files); no
   features documented by that standing instruction. Contradiction resolved without touching the
   skill (which is outside `docs/knowledge-graph/**`).
4. **Frontmatter backfill:** add the §0.3 schema to all existing notes (136 + system files;
   18 currently have none). sha1s computed per cited source at backfill time. This is also the
   moment each existing note's citations get re-verified against current `HEAD` — any that moved
   since writing get corrected now (the rebase-staleness debt is paid once, here).
5. Re-run `verify-notes.js` — structural FAIL classes (`ENTITY-AT-FEATURE-DEPTH`,
   `CONTEXT-MISSING`, `FRONTMATTER-MISSING`, `WIKILINK-BROKEN`) must be zero before Phase 2 starts.

---

# ~~Phases 2–7 — Close what the verifier names, risk-first~~  ✅ COMPLETE (31 of 31 features)

Ordered by risk/value concentration (findings are uneven — order matters):

| Phase | Scope | Why this order | Planning estimate (replaced by `_gap-baseline.md`) |
|---|---|---|---|
| ~~**2**~~ ✅ | ~~**Restaurant Portal**~~ — 4 features, +3 findings | Weakest area (3 business / 1 technical note, 1 feature for 30 controllers) and holds the 24 newest findings (#580–605), all tenant-isolation | ~3–4 features to create, ~15–20 entity notes |
| ~~**3**~~ ✅ | ~~**Order & Fulfilment + Payments**~~ — Payments written; O&F was already complete | Most findings, most business value, the money path | Payments feature missing `_overview`/`_scenarios`/graph; ~10–15 entity notes |
| ~~**4**~~ ✅ | ~~**Identity & Access**~~ — 5 features; +#609-#615; #375 re-attributed | Holds the criticals: #509, #566, #573, #575 | Features formalized from the 5 moved entity folders + 19 IDS controllers; ~8–12 notes |
| ~~**5**~~ ✅ | ~~**Delivery**~~ — 4 features; +#616-#619 | 21 controllers, existing notes strong but feature-incomplete | ~2–3 features, ~10 notes |
| ~~**6**~~ ✅ | ~~**Admin**~~ — 8 features; +#620-#622 | 84 controllers — the largest map, mostly thin CRUD | ~4–6 features, many `single`-shape lookup notes |
| ~~**7**~~ ✅ | ~~**Remainder**~~ — Customer Ordering's last 4 (Ops & Infra, Marketing & Content upgraded from light tier, Support & Chat, Customer Account); +#623-#628, #227 extended | Customer Ordering incompletes | per baseline |

**Phase 7 outcome:** `FEATURE-INCOMPLETE` 4 → **0**. All 31 features now carry
`_knowledge-graph.md`, `_overview.md`, `_scenarios.md` and a built context graph. Marketing &
Content was the last light-tier feature note in the vault and is now full depth; reading its
authoring path against its read query produced five of the six new findings (#623–#627), all in
`AddAnnouncementCommand`/`EditAnnouncementCommand`.

**Per-phase working protocol (identical every phase — this is the loop that converges):**

1. `node verify-notes.js` → take only this phase's context's FAIL lines as the work queue.
2. For each named gap, follow the skill workflow (steps 1–5b: read `CONTEXT.md`, explore code,
   extract rules with `file:line`, reconcile sides, write per `document-templates.md`), producing
   notes with full §0.3 frontmatter. Enumerate, don't sample — `rule_count` is now checked.
3. New conflicts/integrations found → register rows (next sequential number) + inline callouts,
   per the standing terse-entry convention (`feedback_kg_conserve_tokens`).
4. Feature completion: write `_overview.md`, `_scenarios.md` (including Integration rows that
   trace this context's register integrations — this is what closes `INTEGRATION-UNTRACED`),
   spec JSON + `python .claude/skills/8orders-knowledge-graph/scripts/build_context_graph.py`
   for the feature graph. Never hand-write D3.
5. Re-run `verify-notes.js` — this context's FAIL count must be **zero** before the phase closes.
   Commit per phase with the verifier summary in the commit message.

**Execution mode:** solo by default. If the run is unattended, sub-agents are permitted per the
standing override (`feedback_no_subagents_knowledge_graph`): batches of ≤32 files/agent, agents
write findings **only** to `_system/_inbox/` reports carrying machine-readable `FINDING:` lines
(the `audit-inbox-merge.js` contract), the main session folds them into registers/notes.
Progress summaries at each phase boundary; criticals surfaced immediately
(`feedback_progress_reports_long_runs`).

---

# ~~Phase 8 — Register backfill: 450 rows to wikilinks~~  ✅ COMPLETE (REGISTER-UNLINKED 0)

With entity notes now existing, edit `_conflicts.md` (Edit tool, never sed) linking every unlinked
row's Entity cell to its note (or the owning feature's `_knowledge-graph` for controller-level
findings). `REGISTER-UNLINKED` reaches zero. `--register-check` stays green (numbering untouched).

The 450 count spans three files, not one — `_conflicts.md`, `_idor-instances.md` and
`_integrations.md` — and the estimate rose from 147 because Phase 0's verifier counts every register
file, not only `_conflicts.md`. Rows whose subject is a controller or a cross-cutting concern rather
than an entity link to the owning feature's `_knowledge-graph`; that is the majority.

# ~~Phase 8b — The three stubs and the 140 citation repairs~~  ✅ COMPLETE (NOTE-STUB 0, CITE HARD 0)

Two gap classes that are neither feature work nor register work:

- **`NOTE-STUB` (3):** `CityBreakConfiguration`, `PaymentMethod` and `Customer.technical` are
  classified `legacy-poco-root` but carry no `rule_count` and no rule matrix. Each needs its rules
  extracted from code, not a frontmatter edit — a stub that declares a rule count it does not have
  would defeat the check.
- **`CITE-*` HARD failures (140):** inherited from notes written before `verify-citations.js`
  existed — 55 pointing past the end of their file, 50 at blank lines, 20 at files git does not
  track, 15 at paths abbreviated past resolution. Every note written in Phases 2–7 passes with zero,
  so this set only shrinks.

# ~~Phase 9 — Graphs, system layer, final sync~~  ✅ COMPLETE (COVERAGE OK)

1. Rebuild every feature's context-graph spec + HTML (features created in Phases 2–7 need theirs;
   the 5 existing ones regenerate if their entity sets changed).
2. Rebuild the system spec from `_entity-index.md` + `_integrations.md` (per `system-graph.md`:
   contexts as `applications`, features as `cycles`, every entity with its canonical `note` path)
   and run `build_system_graph.py`. All three toggle views must reflect the finished registry.
3. Refresh `_system-index.md`, `_entity-index.md`, `_glossary.md` closing notes.
4. `verify-coverage.js --generate` + verify: the KG's own new files land as
   `excluded:this-knowledge-graph`; citations added during Phases 2–7 raise the `evidenced` depth
   count — the coverage and knowledge axes now certify each other's file sets without sharing a
   derivation.

# ~~Phase 10 — Rebase maintenance (acceptance question 4)~~  ✅ COMPLETE (playbook + rehearsal)

Deliverable: `_system/REBASE-PLAYBOOK.md` — the exact post-rebase sequence:

```
git rebase master                                   # (or merge — team convention)
node docs/knowledge-graph/_system/verify-coverage.js
#   NEW files      → classify in _depth-ledger.tsv / manifest --generate; new entities → _entity-classes.tsv
#   REMOVED files  → drop manifest rows; if an entity died, retire its note (move content to an
#                    "archived" callout or delete + register note), remove tsv row
#   DRIFTED (cited)→ hard fail: the note citing it is stale — see next step
node docs/knowledge-graph/_system/verify-notes.js
#   CITATION-STALE → open _source-index.tsv, look up every note citing the changed file,
#                    re-verify each cited rule against the new code, update line numbers + sha1
#   ENTITY-UNCLASSIFIED → a new domain class arrived: classify it, note it if class requires
#   CONTROLLER-UNMAPPED → a new entry point arrived: map it to a feature, extend _scenarios if behavior is new
node docs/knowledge-graph/_system/audit-inbox-merge.js    # must stay 0 unlanded
node docs/knowledge-graph/_system/verify-notes.js --register-check
# regenerate graphs only if _entity-index.md changed
```

Each failure's meaning is documented inline in the playbook (as above). The structural pieces that
make this cheap — `_source-index.tsv` (change → affected notes is a lookup, not a 136-note grep),
per-note `sources:` sha1s (staleness is detected, not remembered), stable `id:` (renames never
break links) — are all built in Phases 0–1, not here; this phase only writes the procedure and
runs one rehearsal: `git ls-tree` drift check against the current master merge-base, per the
standing post-rebase rule (`project_kg_round2_complete`).

---


# ~~Phase 11 — Audit the closers~~  ✅ COMPLETE (`03f39eb6d`, `75db7485d`, `4bb72688d`)

Not in the original plan. Added because Phases 0–10 all closed and every gate read green, which is
exactly the state the first three rounds of this project were in each time they were wrong. The
question Phase 11 asks is not "do the checks pass?" but **"could these checks fail if the thing they
look for were present?"** — answered by deriving each denominator a second way and diffing.

**Method:** never re-read a checker's own output as evidence about that checker. For each number the
plan quotes as proof, build an independent derivation and compare in both directions.

| What was tested | Independent signal used | Result |
|---|---|---|
| Controller denominator (198) | every `.cs` file declaring a class whose base chain names a `Controller`, plus `[ApiController]` | **Passed.** 233 declare one; the 44 outside the path filter are 43 in the excluded legacy host (all enumerated, reason stated) plus one abstract base with no routes. The 9 files under `Controllers/` declaring no controller already carried `non-controller` rows |
| Entity denominator (304) | EF `DbSet<T>` registrations + class-content scan — i.e. this plan's own unimplemented spec input 3 | **Failed.** The filter was an allow-list asking about 304 of 529 domain-layer files; 37 of the invisible 225 were substantive and **11 appeared nowhere in the vault** |
| Citation verifiability (258 leads) | resolve each ambiguous basename against the note's own `sources:` | **Failed.** 76% were decidable; expanding 154 exposed **5 wrong citations** |
| Register integrity | cell count per row vs. its table header, splitting on unescaped pipes | **Failed.** 9 rows misaligned, 2 of them since the day they were written |
| The 41 tracked caveats | read the code each caveat says it did not read | **2 became findings**, one critical (#650) |

**Findings #639–#650 and IDOR instance 36.** The two that matter most operationally:

- **#650, critical.** `POST /Users/EditUser` binds `UserId`, `FullControl` and the whole `Roles` list
  from the form; nothing compares `UserId` to the caller, the handler clears the target's roles and
  re-adds what was sent, and no guard excludes `admin` — which short-circuits the authorization filter.
  One form post takes Users-*page* access to unrestricted access, plus the Hangfire dashboard.
- **#649.** Four hosts pin their JWT audience; `Talabatk.IDS` sets `ValidateAudience = false`, so the
  roleless operator tooling of #615 is reachable with a customer or driver app token.

**Three new gates, so none of this class can recur silently:** `ENTITY-BEHAVIOUR-UNDOCUMENTED` (an
exclusion whose honesty rests on a claim must have that claim checked), `REGISTER-ROW-MALFORMED`, and
the widened entity denominator itself. Self-test 37 → **40**.

**The transferable lesson, and the reason this phase exists as a permanent part of the plan rather
than a one-off:** fixing one denominator does not fix the others. `verify-coverage.js` was rebuilt in
Phase 0 specifically to defeat this bug shape, and `verify-notes.js`'s entity denominator — in the same
directory, written in the same week — still had it. Audit **every** filter that produces a number
someone might call "complete", separately, from the outside. And when a spec names an independent
signal, check that the code actually implements it; input 3 above was specified, skipped, and never
missed by anything.

**Re-run Phase 11 after any rebase that adds domain files or hosts:**

```bash
# does the path-derived entity set still match the content-derived one?
node docs/knowledge-graph/_system/verify-notes.js          # ENTITY-UNCLASSIFIED names any new domain file
node docs/knowledge-graph/_system/verify-citations.js      # 0 HARD; watch whether BASENAME-AMBIGUOUS grows
```

A rising `CITE-BASENAME-AMBIGUOUS` count after a rebase is the signal that new same-named files have
appeared across hosts — cheap to see, and it silently degrades every citation sharing those basenames.

---

# Future-proofing (design only — explicitly NOT built now)

**Second repo root (Mobile Apps).** `verify-notes.js` and `verify-coverage.js` both read a
`ROOTS` table (this repo hard-wired as root `8orders` today, but the code paths take
`(root, relpath)` pairs from day one). Adding Mobile = one new `ROOTS` entry (path + git dir +
scope rules), a `root` column already present in `_entity-classes.tsv`/`_feature-map.tsv`
(defaulted to `8orders`, so today's files need no edit), and id namespaces already carry the root
(`8orders/...` → `mobile/...`). Context folders for mobile contexts sit beside the existing six.
No existing file restructures.

**AI-agent consumption.** Already satisfied by §0.3: every note machine-parsable (YAML
frontmatter with typed fields), every note addressable (stable `id`, `_id-index.tsv`), every claim
verifiable (`sources[].path`+`sha1`), every relation resolvable (wikilinks + the tsv
bridges + registers). An agent needs only a loader, no KG changes.

---

# One decision surfaced, not assumed (needs Ahmed's answer, blocks nothing)

**Does "gap closed" include code fixes?** `_conflicts.md` #509 is a live unauthenticated account
takeover (`POST api/DeliveryMen/ResetPassword`, `[AllowAnonymous]`, mints its own reset token,
never reads `model.Code` — `Talabatk.IDS/Controllers/DeliveryMenController.cs:239`,
`DeliveryUserManager.cs:69`). #566/#573/#575 and the #580–605 tenant-isolation block are similar
live defects. Commit `81068c034` shows some criticals already get fixed on this branch.

**Updated 2026-08-24 — the list grew, and the top of it changed.** Phase 11 added **#650**, which is
the one to look at first: `POST /Users/EditUser` lets an account holding only Users-*page* access give
itself the `admin` role and `FullControl`, and `admin` short-circuits the authorization filter
entirely. It is a single form post from limited back-office access to unrestricted access plus the
Hangfire dashboard, and unlike #509 it needs no anonymous entry point — it escalates a session the
attacker already holds. **#649** compounds the same area: `Talabatk.IDS` alone sets
`ValidateAudience = false`, so the roleless operator tooling of #615 is reachable with a customer or
driver app token. **#638** (cross-merchant financial ledger via one query parameter) and **#643**
(unauthenticated, unsigned robo-call webhook) are the other additions. Suggested order if closure does
include fixes: **#650 → #509 → #638 → #649 → #643**, then the #580–605 block.

**This plan's position:** the KG's definition of done **documents** defects (register + linked
notes); it does **not** include fixing them — the plan's own hard constraint is "no source-code
edits", and mixing fixes into a documentation branch makes both unreviewable. The criticals list
(#509, #566, #573, #575, #580–605) is handed off as CR candidates; sizing them is exactly what the
finished KG's CR-estimation mode is for. **If Ahmed rules that closure includes fixes**, they run
as a separate branch/PR series after the four commands are green, sized via
`references/cr-estimation.md` — the plan is unchanged either way.

---

# Traceability matrix — every acceptance question to its proof

| Acceptance question | Proof (command / artifact) |
|---|---|
| "Does the plan have gaps?" → **no known gaps** | Every defect and metric in the work order maps to a phase + a named FAIL class above. The denominators are code-derived — **529 domain-layer files** (the whole of `Shared/TalabatkLogic/`, not the 290-models-plus-4-aggregates allow-list this row used to claim, which Phase 11 proved could not see 225 files) and 198 controllers, the latter cross-checked against class declarations. `--self-test` proves the checker sees every gap class it claims. **The load-bearing addition from Phase 11:** `--self-test` proves a checker can detect what it looks *for*, and says nothing about what it does not look at — so a denominator's width has to be tested separately, from an independent derivation. That test is now part of the rebase routine, not a one-off. |
| "Is the KG 100% finished?" → **yes** | The four Definition-of-done commands, green at one commit. |
| "Can we depend on the KG for any tech/business question?" → **yes** | Business: `_overview` + `_scenarios` + business notes per feature, glossary routing. Technical: rule matrices with `file:line`, sha1-verified (`CITATION-STALE` = 0), stubs = 0, every entry point mapped (`CONTROLLER-UNMAPPED` = 0), every integration traced. "Depend on" is enforced, not asserted: a claim whose source moved fails the build. |
| "After rebase, easy to maintain?" → **yes** | `REBASE-PLAYBOOK.md` + `_source-index.tsv` lookup + frontmatter sha1s + stable ids; one rehearsal run executed in Phase 10. |
| Old developer + tester + PO in one | Developer: technical notes/matrices/change surfaces. Tester: `_scenarios.md` per feature (verifier-required), register-linked. PO: `_overview`/business notes/glossary. |
| Mobile repo later, no restructure | ROOTS design, root column, id namespace (§Future-proofing). |
| Chat agent later | §0.3 schema + `_id-index.tsv` (§Future-proofing). |
| Concrete, every claim `file:line` | `rule_count` + matrix required per rule-bearing class; sha1 per cited source; stub FAIL class. |

# Implementation order & commit discipline (for Opus 5)

One commit per phase minimum, verifier summary pasted into each commit message. Phase 0 → 1 →
(2…7 in order) → 8 → 9 → 10. After every phase: run all four commands; never advance with a
regression in an already-green class. If context compaction threatens mid-phase, write state to
`_system/_inbox/` first — conversation is not storage (the #433 lesson, three recurrences on
record).
