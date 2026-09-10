---
id: 8orders/system/patha-work-order
note_type: system
sources:
  - path: AdminUi/ClientApp/src/app/Shared/Enums/OrderStatus.js
    sha1: c7e37ba4527c
  - path: Shared/TalabatkData/Migrations/TalabatkContextModelSnapshot.cs
    sha1: 5c6f6a5d28cf
  - path: Shared/TalabatkLogic/TalabatkModels/Order.cs
    sha1: a8504688c441
  - path: Talabatk.IDS/Controllers/RestaurantUserController/RestaurantUserController.cs
    sha1: a4c44c8baa83
  - path: TalabatkRestaurants/Controllers/OptionGroup/MenuItemOptionGroupController.cs
    sha1: 508717543974
last_updated: 2026-08-23
tags: [system, work-order]
---
# Path A work order — close the coverage gap and fix the mislabelling

Written to disk deliberately, before a context compaction, so this survives as a file rather than a
summary. Round 5's own lesson: conversation is not storage (#433, three recurrences).

## Corrected scope — read this first

An earlier estimate in conversation said "~140 files, low value". **Both halves were wrong.** The real
figure is **748 files**, and the largest block is the **domain layer**, which is high value.

The error: I assumed `TalabatkLogic/TalabatkModels` was covered because a schema reference exists. That
reference came from parsing `TalabatkContextModelSnapshot.cs` (phase 1-2), which yields the EF-mapped
*shape* — tables, columns, relationships, delete behaviours. It says nothing about the model classes'
**domain methods, factories and validation**, which is where much of this round's real substance lives:
`Brand.Instance` (fallible, #394), `WalletTransaction.Instance` (infallible, a rejected claim),
`DeliveryMen.UpdateRequiredPaymentAndExceededCashLimit` (#448), `Order.cs:2421` (#449),
`AspNetUserShift.Instance` (#432). Every one of those was found *incidentally* while verifying an agent
claim — never by a systematic pass. 212 unread files in that folder is a real gap.

## Root cause of the confusion: `2-x` is a catch-all, not a phase

**613 sweep-only files carry `phase=2-x`**, which records "some phase-2 activity" and no method. It is
indistinguishable in the manifest from a file genuinely covered by a named parse. That is why the
number was misread — by me, twice.

Second, narrower contradiction, same root: the 1,723 migration files carry **`status=read` but
`depth=sweep-only`**. One column states the phase's *intent*, the other its *evidence*, and for those
files they disagree. This is #382's exact tension still sitting in the data.

## The work

### Step 1 — read the 748 (24 batches of 32)

File list: `scratchpad/gapA.txt`. Composition:

| Files | Area | Why it matters |
|---|---|---|
| **212** | `Shared/TalabatkLogic/TalabatkModels` | **Domain layer.** Factories, invariants, validation. Highest value in this list |
| 104 | `AdminUi/Reports` (89) + `TalabatkRestaurants/Reports` (15) | 37 `.vsrepx` + designer files; 29 already have phase `4-1`, 30 have `2-5` |
| 57 | `Shared/TalabatkLogic/DomainEvents` | Event records — likely thin, confirm rather than assume |
| 73 | Host `Helpers` — Delivery 29, Restaurants 24, SharedWeb 20 | Shared logic; a defect multiplies across callers |
| 17 | `Shared/TalabatkData/ElasticSerarchServices` | Search. `SearchScoring.md` is the canonical spec — bridge, don't restate |
| 14 | `Shared/TalabatkApplication/OrderBuilder` | Order construction. #449 already found a dropped parameter here |
| 13 | `Shared/TalabatkData/Cassandra` | Chat data layer. #404 instance 4 came from here |
| ~250 | Remainder — `ViewModels`, `Abstractions`, `Common`, `.cshtml`, `.json`, `.md`, `.sln` | Mixed; low individual value |

Use `RPROMPT.md` as the methodology — it targets the ten confirmed defect shapes and already carries
the `find /` prohibition and the "open the repo's own factory" rule. For the model files, add: **check
every `Instance`/factory for whether it has a `Result.Failure` path**, because that single fact decided
two same-shaped claims oppositely this round.

### Step 2 — replace `2-x` with real method codes

For each of the 613, record what actually happened. Where nothing did, leave `sweep-only` — an honest
gap beats a vague one.

### Step 3 — add a `parsed` depth value

Distinct from both `agent-read` and `sweep-only`, and it must **name the parser and what it extracted**.
Apply to the files genuinely covered deterministically: migrations (`1-1`, 935 bodies parsed — 114 real
`Up()` drops, 98 stored procedures inventoried), `.Designer.cs` (`1-4`, `[Migration]` attribute
confirmed in all 921), enums (`2-3`), DTOs (`2-4`), custom JS (`8-1`), `.bak` (`5-3`).

### Step 4 — resolve `status=read` vs `depth=sweep-only`

Those 1,723 rows must not claim "read" in one column and deny it in another. `status` should say what
the phase did; `depth` should say what the evidence supports. Make them consistent or make the
difference explicit in the verifier's output.

### Step 5 — verify and commit

`verify-coverage.js` (exit 0), `audit-inbox-merge.js` (0 unlanded), the register integrity check
(rows == max, 0 malformed, 0 gaps). Regenerate the manifest **after** the commit that adds files —
the manifest enumerates tracked files, so adding files invalidates a manifest built before the commit.

## Definition of done

Every in-scope file is `evidenced`, `agent-read`, `parsed` (with the parser named), or `sweep-only`
**with a stated reason** — and no file's `status` contradicts its `depth`.

That is a **justified** coverage claim, not a 100%-read claim. The distinction is the whole point: four
prior rounds died on unjustified claims of the second kind.

---

# Path A outcome (written on completion, before the commit)

## The five steps

| Step | State | Evidence |
|---|---|---|
| 1 — read the 748 | **done** | 748/748, plus 35 Razor views step 4 exposed. Nine reports: `_inbox/pathA-*.md` |
| 2 — replace `2-x` | **done** | The 613 `2-x` + `sweep-only` files are now **0**. 1,042 files moved to named `9-x` codes; the 739 files still labelled `2-x` all carry `agent-read` (570) or `evidenced` (169) |
| 3 — add `parsed` | **done** | 2,020 files, each with the parser and its extraction named in the new `_depth-ledger.tsv` |
| 4 — status vs depth | **done** | contradictions **2,037 → 0**; `sweep-only` 3,041 → 241, of which **0** lack a stated reason |
| 5 — verify | **2 of 3** | verifier exit 0; register 551 rows / 0 gaps / 0 dupes; inbox audit **54 unlanded, all Round 5** |

Depth split at completion: evidenced 1,879 · agent-read 3,335 · parsed 2,020 · sweep-only 241.

**Definition of done is met** for the four depth values and the status/depth consistency. It is **not**
met for "0 unlanded" — see below, and note that the 54 are not Path A's.

## RPROMPT.md does not exist

The work order names `RPROMPT.md` as the methodology. There is no such file in the repo — the only
match anywhere is this document's own reference to it. It was a conversation artefact, which is the
failure this work order's opening line warns about (#433, now four recurrences). Path A ran on the
methodology restated inline here instead: the ten defect shapes, the `find /` prohibition, "open the
repo's own factory", "trace assignments, not identifier names", 32-file batches, and the added rule
about checking every `Instance`/factory for a `Result.Failure` path.

That last rule paid for itself: **11 factories in `TalabatkModels` return `Result<T>` and cannot
fail**, and three of them are load-bearing for four unchecked `.Value` unwraps in the order-creation
path (`pathA-F-orderbuilder.md`). Any future claim of the form "callers ignore this factory's failure"
has to be checked against that table first.

## The 54 unlanded findings are Round 5's, and here is why nobody saw them

`audit-inbox-merge.js` matched a finding to the registers **by filename alone**. So a new finding in a
file some earlier round had already written about counted as landed. Making it line-aware exposed:

- **Path A: 88 findings, 88 landed** (rows #459–551).
- **Round 5 `phase3-C` controller sweep: 76 findings, 22 landed, 54 not.**

Concentrated in `OrdersController.cs` (8), `ReportController.cs` (5),
`MenuItemOptionGroupController.cs` (4), `RestaurantUserController.cs` (3), and ~20 more controllers —
mostly missing tenant checks, absent `[Permission]` attributes, and V2 endpoints taking
`restaurantId` from the caller where V1 used the session value. `_idor-instances.md` cites
`OrdersController.cs:216-225`, `:499-522` and `:789`; the unlanded ones are at `:151`, `:259`, `:297`,
`:347`, `:445`, `:624`, `:864`, `:911` — different findings, same file.

**This is the same defect class the KG has failed on four times**: a checker whose resolution is
coarser than the thing it certifies, reporting zero and being believed. Not folded in here because
they are prior-round analysis and 54 register rows is a decision, not a mechanical step.

## Tooling defects found and fixed during steps 2–4

Each was found by asking the manifest a question it could not previously answer:

1. **`docs/knowledge-graph/_system/verify-coverage.js:219`** — the `GeneratedClient` exclusion required a leading `/`, so the
   repo-root `GeneratedClient/` fell through to the `.cs → read, 2-x` catch-all: **32,887 lines** of
   nswag output counted as in-scope code. The directory is also stale and compiled by nothing.
   Logged as #511.
2. **`wwwroot/jquery/`** — a third vendor directory matching neither `/wwwroot/lib/` nor
   `/wwwroot/js/devextreme/`. Four jQuery 3.5.1 variants were in-scope application JavaScript.
3. **68 compiled-TypeScript artifacts** under `ClientApp/src` counted as custom JS for phase 8-1 to
   sweep. Verified, not assumed: all 62 `*.spec.js` have a matching `*.spec.ts`, and `OrderStatus.js`
   is transpiler output down to its `sourceMappingURL`.
4. **`.cshtml` was phase `5-3`** — the `.bak` backup-parse code — so the phase column described
   neither. Razor views now carry `9-9`.
5. **`audit-inbox-merge.js`** — filename-only matching (above), and an extension regex that truncated
   `.cshtml` to `.cs`, reporting two correctly-landed findings as unlanded.

Findings 1–3 mean the previous "unread in-scope code" figure was overstated by ~33,000 lines.

## What is deliberately still open

- **Nothing is committed.** 22 files changed or added. The manifest must be regenerated **after** the
  commit that adds them, per step 5 — a manifest built before is stale by construction.
- The 54 Round 5 controller findings.
- No source file was edited. Every change is under `docs/knowledge-graph/_system/`.

## Corrections to this work order's own estimates

- `.vsrepx` + designer counts were "37 / 29 at `4-1` / 30 at `2-5`". Actual: **34** at `4-1`,
  **35** at `2-5`, plus a third block of **35** report code-behind files at `2-x` the estimate did not
  separate.
- "212 files … the domain layer … highest value" is right for roughly 130 of them. **38 of the 212 are
  stored-procedure projections** with no invariants, and ~20 more are one-line join-table factories.
  The genuine domain surface in that folder is closer to 130 files than 212 — size the next round from
  evidence, not file count.

---

## Method notes that will save time

- **32-file batches.** Every stall this round was a 64-file batch, a single >400-line file read end to
  end, an unbounded `find /`, or too many concurrent agents. Not model capability — sizing.
- For any file over ~400 lines, grep for the target patterns and read around the hits.
- Tell each agent to **write its inbox file before running long**; a partial report that exists beats a
  complete one that never lands.
- Require the `FINDING: <verdict> | <file>:<line> | <claim>` line — it is what makes
  `audit-inbox-merge.js` exact rather than heuristic.
- Launch in waves of ~6, not 12+.
- **Trace assignments, not identifier names.** A variable called `userPermissions` held a string and
  cost a missed defect (#316's second site).
