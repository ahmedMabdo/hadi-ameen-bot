---
id: 8orders/system/rebase-playbook
note_type: system
last_updated: 2026-08-23
---
# Rebase playbook — keeping the knowledge graph true after master moves

**The question this file answers:** *after I rebase from master, is the KG easy to maintain?*

Yes, and the reason is structural rather than diligent. Three things were built so that maintenance is a
**lookup**, not a re-read:

| Structure | What it makes cheap |
|---|---|
| `_source-index.tsv` | "file X changed — which notes are now stale?" is a grep of one file, not of 219 notes |
| per-note `sources[].sha1` | staleness is **detected**, not remembered — a changed file fails the check by itself |
| stable `id:` + `_id-index.tsv` | a renamed or moved note keeps its identity, so links never break in a rename |

None of them requires anyone to remember anything. If you skip this playbook entirely, the checkers
still fail loudly on the next run — the worst case is noise, never silent rot.

---

## The sequence

Run it in this order. Each step's failures are explained inline, so you never have to interpret a
checker's output from scratch.

```bash
# 0. rebase (or merge — follow the team convention)
git rebase origin/master

# 1. Did any file appear, vanish, or change?
node docs/knowledge-graph/_system/verify-coverage.js
```

**`NEW`** — a file in git that the manifest has never seen. Classify it:
- source in one of the 9 in-scope projects → it needs a status; run
  `node docs/knowledge-graph/_system/verify-coverage.js --generate` once you have classified it in
  `_depth-ledger.tsv`, or accept the ledger's pattern match if one already covers it;
- a new **entity** (`Shared/TalabatkLogic/TalabatkModels/*.cs` or an `*Aggregate/` folder) → add a row to
  `_entity-classes.tsv`. Every row needs a class, a shape and **evidence**; an exclusion with no stated
  reason is the one thing the checker will not accept;
- a new **controller** → add a row to `_feature-map.tsv` mapping it to a context and feature.

**`REMOVED`** — drop its manifest row. If it was an entity, retire its note: move the content into an
"archived" callout or delete the note and remove the `_entity-classes.tsv` row. Leaving the row is what
turns a deletion into a permanent phantom gap.

**`DRIFTED (cited)`** — a file some note cites has changed. This is the important one and step 2 handles
it.

```bash
# 2. Which notes does that drift actually touch?
MB=$(git merge-base HEAD origin/master)
git diff --name-only "$MB" origin/master > /tmp/drift.txt

while read -r f; do
  hits=$(awk -F'\t' -v p="$f" '$1==p {print $3}' \
    docs/knowledge-graph/_system/_source-index.tsv | sort -u)
  [ -n "$hits" ] && { echo "CITED  $f"; echo "$hits" | sed 's|^|         -> |'; }
done < /tmp/drift.txt
```

That prints exactly the note↔file pairs worth opening. For each one: read the cited lines in the new
code, correct the line numbers if the code moved, then re-stamp **that note only**:

```bash
node docs/knowledge-graph/_system/verify-notes.js --restamp "<path to the note>"
```

`--restamp` is per-note on purpose. A bulk re-stamp would overwrite the sha1s that prove the citations
were checked, converting "verified against this version" into "assumed". The narrow command is the
point: stamping is an assertion that a human looked.

```bash
# 3. Is the knowledge axis still whole?
node docs/knowledge-graph/_system/verify-notes.js
```

- **`CITATION-STALE`** — you skipped a note in step 2. It names the file and both sha1s.
- **`ENTITY-UNCLASSIFIED`** — a new domain type arrived; classify it (step 1). Note that the
  denominator is now **every** `.cs` file under `Shared/TalabatkLogic/`, not just `TalabatkModels/`
  plus the named aggregates — so this fires for new enums, domain events, strategies and helpers too,
  and each needs a row even if that row's whole content is "excluded, because …". That is the point:
  see finding #639 for the 225 files the old allow-list could never report.
- **`ENTITY-BEHAVIOUR-UNDOCUMENTED`** — a row classed `domain-behaviour` (a strategy, calculator or
  scheduled job: rule-bearing but not an entity) whose `evidence` cell names no note, or names one
  that does not resolve. Point it at the note that actually documents the rules. Do **not** downgrade
  the row to `infrastructure` to silence this — that is how rule-bearing code goes quiet (#640).
- **`CONTROLLER-UNMAPPED`** — a new entry point arrived; map it, and extend that feature's
  `_scenarios.md` if the behaviour is new rather than a variant.
- **`NOTE-ABSENT` / `NOTE-STUB`** — an entity now needs a note, or has one with no rules. Extract the
  rules from the code; do not add a `rule_count` to satisfy the check.
- **`COVERS-UNMENTIONED`** — a note's `covers:` list names an entity its body never discusses. Write the
  entity up, or remove it from the list and give it a note of its own.
- **`WIKILINK-BROKEN`** — usually a folder rename. Path-form links must resolve as paths, deliberately:
  accepting a basename match here is exactly how a stale relative path survived a folder move unnoticed.

```bash
# 4. Do the citations still point at real code?
node docs/knowledge-graph/_system/verify-citations.js
```

Four classes gate, and each says what to do:
- **`CITE-LINE-OUT-OF-RANGE`** — the file shrank. Re-anchor from what the row quotes (see below).
- **`CITE-LINE-VACUOUS`** — the line is now blank or a lone brace. Same fix, usually a shift of 1–5 lines.
- **`CITE-FILE-MISSING`** — the file moved or was renamed. Find it and spell the path out in full.
- **`CITE-PATH-ELIDED`** — someone wrote `.../Foo.cs`. Spell it out; an abbreviated path is unverifiable.

Two classes are **leads, not gates**, and are meant to accumulate: `CITE-SYMBOL-ABSENT` (a symbol named
in prose but not within 12 lines of the citation — frequently correct, e.g. a row naming a method and
citing its caller) and `CITE-BASENAME-AMBIGUOUS` (a bare filename several tracked files share). Neither
is mechanically decidable, which is why neither blocks.

**Re-anchoring, when many citations drift at once.** The register quotes real code in backticks, and that
quote is the durable evidence — the line moved, the code did not. `_system/backfill-register-links.js`
is the linking tool; for line drift, the approach that worked on 88 citations in one pass was: find the
line carrying the row's most specific quoted token, preferring a token with a member access, a call or an
internal capital over a bare word, and among equal candidates the one nearest the recorded line. The
three guards matter — without the specificity rule a row quoting both `SaveChangesAsyncWithResult` and
the word `customer` re-anchors to the wrong line, and without the proximity rule a row naming two sibling
methods sends the second citation to the first method.

```bash
# 5. Registers still coherent?
node docs/knowledge-graph/_system/verify-notes.js --register-check
node docs/knowledge-graph/_system/audit-inbox-merge.js

# 6. New findings need linking; the tool is idempotent, so just run it
node docs/knowledge-graph/_system/backfill-register-links.js --write

# 7. Regenerate the derived files
node docs/knowledge-graph/_system/verify-notes.js --generate      # _source-index.tsv, _id-index.tsv
node docs/knowledge-graph/_system/gen-entity-index.js --write     # the generated half of _entity-index.md
node docs/knowledge-graph/_system/gen-system-spec.js docs/knowledge-graph/_system/_system-spec.json
python .claude/skills/8orders-knowledge-graph/scripts/build_system_graph.py \
  --spec docs/knowledge-graph/_system/_system-spec.json \
  --title "8Orders — System Knowledge Graph" \
  --out docs/knowledge-graph/_system/system-graph.html
```

Step 7's regenerations are cheap and safe: each derives from a registry, so running them when nothing
changed produces no diff. Only rebuild a **feature** context graph if that feature's entity set changed.

```bash
# 8. The gate. All five must pass before the branch is considered clean.
node docs/knowledge-graph/_system/verify-notes.js --self-test
node docs/knowledge-graph/_system/verify-notes.js
node docs/knowledge-graph/_system/verify-notes.js --register-check
node docs/knowledge-graph/_system/verify-citations.js
node docs/knowledge-graph/_system/verify-coverage.js
```

---

## Rehearsal, run 2026-08-23 against real drift

Not a hypothetical. At the time of writing, `origin/master` was **30 files ahead** of this branch's merge
base (`87fc92480`), so the playbook was exercised against a genuine divergence.

**Step 1 — what changed.** 30 files: 8 added, 22 modified. Categorised by what the KG needs from each:

| Kind | Count | Action needed |
|---|---|---|
| New Angular component files (`item-replacement-report`) | 3 | none — the ledger's `\.ts$`/`\.html$`/`\.css$` patterns cover them |
| New EF migration pair | 2 | none — `excluded:ef-migration` |
| New helper (`RestaurantAccessScope.cs`) | 1 | classify in the manifest; **not** an entity and **not** a controller, so neither denominator changes |
| New DTO / interface (`ItemReplacementReportDto.ts`) | 1 | none |
| Regenerated NSwag clients + `specification.json` | 3 | none — `excluded:nswag-generated-client` |
| i18n and module registration | 4 | none |
| Modified source the KG cites | 5 | **step 2** |
| Modified source the KG does not cite | 11 | manifest sha1 refresh only |

**No new entity and no new controller**, so neither the entity nor the feature denominator moves. That is
the common case, and it is why most rebases are cheap.

**Step 2 — the lookup.** Five of the thirty changed files are cited, and `_source-index.tsv` named
**20 note↔file pairs** to re-verify:

| Changed file | Notes citing it |
|---|---|
| `Shared/TalabatkLogic/TalabatkModels/Order.cs` | 12 — including `Order.technical`, `Order-Lifecycle.technical`, `Money-Path.technical`, `Discount-Resolution.technical`, `_conflicts.md` |
| `Shared/TalabatkData/Talabatk_Context/TalabatkContext.cs` | 2 — `Admin-Access-and-Oversight.technical`, `_conflicts.md` |
| `TalabatkRestaurants/Controllers/Reports/ReportController.cs` | 3 — `Merchant Finance & Reporting`'s `_knowledge-graph` and `_scenarios`, `_conflicts.md` |
| `Shared/TalabatkApplication/ITalabatkContext.cs` | 1 — `CustomerAddress.technical` |
| `TalabatkRestaurants/ClientApp/src/assets/i18n/en.json` | 1 — `_conflicts.md` |

**That is the whole cost of this rebase**: read the cited lines in 20 places, most of them in one file.
Without the reverse index the same question would mean opening 219 notes and hoping. `Order.cs` being the
hot spot is expected and worth internalising — it is 6,285 lines and the single most-cited file in the
graph, so any master change touching it dominates the maintenance bill.

**Not performed here:** the rebase itself, and the re-verification of those 20 pairs. Both belong to
whoever runs the rebase; this rehearsal establishes that the *detection* works and quantifies the work,
which is what acceptance question 4 asks.

---

## Merging a fix branch — the same drift, arriving from the other direction

Everything above assumes drift comes *from master*. It also comes from **our own fix branches**, and
that case is easier to miss because nobody thinks of their own work as drift.

**Reviewing that branch?** [[FIX-650-REVIEW|FIX-650-REVIEW.md]] is the guide — what to check in
risk order, where each fix could break a legitimate caller, and the two deployment steps.

**Open obligation as of 2026-08-24.** The security fixes for the 38 findings this vault marks closed
live on `fix/650-user-privilege-escalation`, which is **not merged**. That branch edits source the vault
cites, so merging it invalidates citations exactly the way a master rebase does — except later, and
into our own history. Measure it before merging, never after:

```bash
node docs/knowledge-graph/_system/merge-reverify.js fix/650-user-privilege-escalation
```

At the time of writing that reports **30 cited files, 103 note↔file pairs**. The number is deliberately
not repeated anywhere as a fact: the branch keeps moving, so a written-down count is right once and
wrong afterwards. Re-run the tool; believe the tool.

Then work the list exactly as steps 4–8 above: re-read each cited rule against the new code, correct the
line numbers, `--restamp` the note, and finish with the five gates green.

**Two things about that branch that are not citation problems, but will bite:**

- Its commit hashes (`deac2d45e`, `0bdb2c2aa`, `64040cf80`) are cited in `_conflicts.md` status cells and
  are reachable **only from that branch**. A squash-merge — which is this repo's PR convention, judging
  by the `Merged PR NNNNN:` commits on master — replaces them with a single new hash, and every one of
  those references dies. `_conflicts.md` #651 records this and is what the status cells point at, so the
  trail survives the squash even though the hashes will not.
- The fixes carry **two deployment steps** that no gate can check, both flagged with `⚠️ DEPLOYMENT`
  comments in the code: the JWT audience list in `Talabatk.IDS/Configurations/Identity.cs` (#649) and the
  `ApiKey` row the Ziwo webhook now requires (#643). Neither fails at build time; both fail in
  production, quietly, by locking out a client or silently dropping robo-call results.

---

## The two rules that must not be relaxed

Everything above is procedure. These two are load-bearing, and both were learned by being burned:

1. **A checker must never derive both its expectation and its observation from the same filter.**
   `verify-coverage.js` once enumerated `git ls-files` through a 13-path whitelist and compared it to a
   manifest built from that same whitelist. It agreed with itself and printed `COVERAGE OK` while 5,585
   tracked files were not excluded but **invisible**. Today the expectation comes from **code** (entity
   files, controller files, git's own file list) and the observation from **disk** (notes, manifest rows),
   and they are compared in both directions. See `_conflicts.md` #384.
2. **Never edit these markdown files with `sed`.** A previous `sed` pass over `_conflicts.md` corrupted
   wikilinks whose alias pipe is escaped as `\|` inside a table cell. Use the Edit tool, or a script that splits table rows on
   *unescaped* pipes only and asserts the cell count is unchanged before writing — a row that gains or
   loses a cell reflows every column after it, and that is invisible in a diff of hundreds of rows.

## Also worth knowing

- **Every file here is CRLF.** A JS regex anchored with `$` will not match a line still carrying its
  `\r`, so a table-row pattern silently matches nothing and the check reports a clean zero. Every tool in
  `_system/` normalises line endings at the door; any new one must too.
- **102 of the note paths contain a space or `&`.** Quote every path in every shell loop.
- **Never run unbounded `find`** in this repo — it descends `node_modules` and times out. Use
  `git ls-files` or a scoped `find <dir>`.
- **`--stamp` fills a missing sha1; `--restamp` overwrites one.** The asymmetry is deliberate: only the
  second asserts that a human re-read the lines.
