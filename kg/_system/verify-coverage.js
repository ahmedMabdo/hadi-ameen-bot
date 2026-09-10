#!/usr/bin/env node
/**
 * 8Orders Knowledge Graph — coverage manifest generator + verifier
 *
 * WHY THIS EXISTS
 * ---------------
 * The KG was declared "100% complete" three times and was wrong three times. Every failure had the
 * same root cause: coverage was asserted in prose, measured by counting files, and never re-derived
 * after the code moved. This script replaces the assertion with a command.
 *
 *   node verify-coverage.js --generate   regenerate the manifest from git at the current commit
 *   node verify-coverage.js              verify: exit 0 if clean, non-zero if coverage drifted
 *
 * VERIFY fails (exit 1) when any in-scope file is:
 *   - NEW      present in git but absent from the manifest      -> never audited
 *   - REMOVED  in the manifest but no longer in git             -> manifest is stale
 *   - UNCLASSIFIED  matches no scope rule                       -> a blind spot, by definition
 *
 * Enumeration is via `git ls-files`, deliberately NOT `find`:
 *   - `find` descends into node_modules before pruning and times out on this repo
 *   - `find -name "*.cs"` without `-type f` silently counts DIRECTORIES as files, and this repo
 *     really does contain a directory named "GetCustomerDetailsToAdminQuery.cs"
 *   - git enumeration also proves there are no untracked source files hiding from the audit
 */

'use strict';
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const REPO = path.resolve(__dirname, '..', '..', '..');
const SYSTEM_DIR = __dirname;
const TSV = path.join(SYSTEM_DIR, '_coverage-manifest.tsv');
const MD = path.join(SYSTEM_DIR, '_coverage-manifest.md');
const LEDGER = path.join(SYSTEM_DIR, '_depth-ledger.tsv');

// ---------------------------------------------------------------------------
// Read a text file as lines, with the line ending normalised away.
//
// Every generator here writes '\n', but this repo sets `core.autocrlf=true` with `* text=auto` in
// `.gitattributes`, so each of these TSVs is LF in git and **CRLF in the working tree on Windows**.
// Splitting on '\n' alone therefore leaves a '\r' glued to the LAST column of every row. That is not
// cosmetic: `sha1_12` is the last column of `_coverage-manifest.tsv`, so every stored hash read back
// as `"<hash>\r"` compared unequal to every freshly computed hash, and the drift check reported all
// 1,879 `depth=evidenced` files as CHANGED on every run — a gate that fails unconditionally reports
// nothing, which is the same blindness as one that passes unconditionally.
//
// It reproduced only on a Windows checkout; on Linux CI the files stay LF and the bug is invisible.
// So the normalisation belongs at the read boundary, once, rather than as a `.trim()` on whichever
// column someone happens to notice next.
// ---------------------------------------------------------------------------
function readLines(file) {
  return fs.readFileSync(file, 'utf8').replace(/\r\n/g, '\n').split('\n');
}

// ---------------------------------------------------------------------------
// Depth ledger (Path A steps 3 + 4).
//
// `status` records what a phase was SUPPOSED to do with a file; `depth` records what the evidence
// actually supports. Those are different claims, and for 1,723 rows they openly contradicted each
// other - `status=read` beside `depth=sweep-only`. The cause was mechanical: depth could only be
// carried forward from the previous manifest, so there was no way to ASSERT a depth for a set of
// files and no place to record WHY.
//
// The ledger is that place. It maps a path pattern to a depth and, crucially, to the evidence for it -
// the parser that ran and what it extracted, or the report that says an agent read the file, or the
// reason a sweep was sufficient. "sweep-only with a stated reason" becomes data instead of prose.
//
// `parsed` is the value step 3 adds. It is deliberately NOT a weaker cousin of `agent-read`: for
// generated files it is the stronger claim, because a parser is reproducible and an agent is not.
// ---------------------------------------------------------------------------
const VALID_DEPTHS = new Set(['evidenced', 'agent-read', 'parsed', 'sweep-only', 'n/a']);

function loadLedger() {
  if (!fs.existsSync(LEDGER)) return [];
  const rows = [];
  const lines = readLines(LEDGER);
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (!line.trim() || line.trim().startsWith('#')) continue;
    const [pattern, depth, evidence] = line.split('\t');
    if (!pattern || !depth) {
      throw new Error(`_depth-ledger.tsv:${i + 1} malformed (needs pattern<TAB>depth<TAB>evidence)`);
    }
    const d = depth.trim();
    if (!VALID_DEPTHS.has(d)) {
      throw new Error(`_depth-ledger.tsv:${i + 1} unknown depth '${d}'`);
    }
    if (!evidence || !evidence.trim()) {
      // The reason is the point. A ledger line without one would recreate the vagueness this replaces.
      throw new Error(`_depth-ledger.tsv:${i + 1} has no evidence text; every depth claim needs a stated reason`);
    }
    // Two pattern forms. A regex covers a whole folder or extension. `@list:<file>` covers an
    // explicit set of paths, which is what a work order's file list actually is - and it is the
    // honest way to record "these specific files were read", where no folder pattern would be true.
    const pat = pattern.trim();
    if (pat.startsWith('@list:')) {
      const listPath = path.join(SYSTEM_DIR, pat.slice('@list:'.length).trim());
      if (!fs.existsSync(listPath)) {
        throw new Error(`_depth-ledger.tsv:${i + 1} references a missing list: ${listPath}`);
      }
      const set = new Set(readLines(listPath).map((s) => s.trim()).filter(Boolean));
      rows.push({ set, depth: d, evidence: evidence.trim(), line: i + 1, label: pat });
      continue;
    }
    rows.push({ re: new RegExp(pat, 'i'), depth: d, evidence: evidence.trim(), line: i + 1, label: pat });
  }
  return rows;
}

/**
 * Precedence, strongest first:
 *   1. excluded status            -> 'n/a'          (nothing in the KG asserts anything about it)
 *   2. prior depth 'evidenced'    -> 'evidenced'    (a KG citation follows the notes, not a path pattern)
 *   3. first matching ledger row  -> that depth     (asserted, with a reason on record)
 *   4. prior depth                -> carried over   (so an unlisted file does not silently downgrade)
 *   5. otherwise                  -> 'sweep-only'
 */
// Depth strength, so a broad ledger pattern can never DOWNGRADE a stronger per-file claim. Without
// this, the `\.ts$ -> sweep-only` line (correct for the phase as a whole) silently demoted the 166
// TypeScript files a Round 5 batch had actually read - erasing real evidence in the name of recording
// it. `parsed` and `agent-read` are deliberately the same rank: they are different KINDS of evidence,
// not different amounts, so neither should overwrite the other.
const DEPTH_STRENGTH = { 'sweep-only': 1, 'parsed': 2, 'agent-read': 2, 'evidenced': 3, 'n/a': 0 };

function resolveDepth(file, status, priorDepth, ledger) {
  if (String(status).startsWith('excluded')) return { depth: 'n/a', evidence: null };
  if (priorDepth === 'evidenced') return { depth: 'evidenced', evidence: 'cited in the knowledge graph' };

  let hit = null;
  for (const row of ledger) {
    const matched = row.set ? row.set.has(file) : row.re.test(file);
    if (matched) { hit = row; break; }
  }
  const prior = priorDepth && VALID_DEPTHS.has(priorDepth) ? priorDepth : null;

  if (hit && prior) {
    // Ledger wins ties, so a newer parse can replace an older agent read of the same file.
    return DEPTH_STRENGTH[hit.depth] >= DEPTH_STRENGTH[prior]
      ? { depth: hit.depth, evidence: hit.evidence }
      : { depth: prior, evidence: 'carried forward - stronger than the matching ledger line' };
  }
  if (hit) return { depth: hit.depth, evidence: hit.evidence };
  if (prior) return { depth: prior, evidence: null };
  return { depth: 'sweep-only', evidence: null };
}

// ---------------------------------------------------------------------------
// Scope. Repo-root CI/infra is in scope as of Round 4 (user-approved).
// ---------------------------------------------------------------------------
const SCOPE_PATHS = [
  'Shared/SharedWeb', 'Shared/TalabatkApplication', 'Shared/TalabatkData', 'Shared/TalabatkLogic',
  'AdminUi', 'Talabatk.IDS', 'TalabatkAPIs', 'TalabatkDelivery', 'TalabatkRestaurants',
  'Builds', 'docker-compose.elasticsearch-local.yml', 'nuget.config', 'version-update.yml',
];

// Case-INSENSITIVE by design: this repo contains `Available.PNG` alongside `logo.png`, and a
// case-sensitive rule silently left them unclassified. On a case-insensitive filesystem that class
// of miss is invisible until something enumerates for real.
const rx = (s) => new RegExp(s, 'i');

/**
 * Ordered rules. FIRST match wins, so specific exclusions must precede broad inclusions.
 * status: 'read'   -> must be individually read by a phase
 *         'swept'  -> grep/pattern-swept in bulk; individually read only if the sweep flags it
 *         'excluded:<reason>' -> deliberately out of scope, reason recorded
 */
const RULES = [
  // ---- out-of-scope PROJECTS, by direct user instruction -----------------
  // These must be stated as exclusions rather than left out of enumeration. Previously the scope
  // whitelist simply never enumerated them, which made them indistinguishable from an oversight —
  // the manifest could not show that they were skipped deliberately. Now the reason is on record.
  [rx('^(Shared/)?(TalabatkApplication|TalabatkData|TalabatkLogic)\\.Test/'), 'excluded:test-project-user-instruction', '-'],
  [rx('^Talabatk\\.VersionAPI/'),               'excluded:out-of-scope-user-instruction', '-'],
  [rx('^TalabatkAPI(\\.Data)?/'),               'excluded:legacy-project-user-instruction', '-'],
  // ---- repo furniture: not application source ----------------------------
  [rx('^docs/knowledge-graph/'),                'excluded:this-knowledge-graph',   '-'],
  [rx('^docs/'),                                'excluded:documentation',          '-'],
  [rx('^\\.claude/'),                           'excluded:agent-tooling',          '-'],
  [rx('^\\.cursor/'),                           'excluded:ide-tooling',            '-'],
  [rx('^\\.cr/'),                               'excluded:ide-tooling',            '-'],
  [rx('^\\.obsidian/'),                         'excluded:ide-tooling',            '-'],
  [rx('^\\.azuredevops/'),                      'excluded:repo-template',          '-'],
  [rx('^TieredDiscountPlan/'),                  'excluded:planning-notes-not-source', '-'],
  // ---- root-level tracked files: the class the old whitelist made invisible
  // Solution files define what actually compiles, so they are IN scope and read, not excluded.
  [rx('^[^/]+\\.sln$'),                         'read',                            'P10'],
  [rx('^[^/]+\\.(sql|py|bat)$'),                'read',                            'P10'],
  [rx('^(CONTEXT-MAP|README|pull_request_template)\\.md$'), 'read',                 'P10'],
  [rx('^(build-out|AI apis)\\.txt$'),           'excluded:scratch-output',         '-'],
  [rx('^[^/]+\\.(csv|xlsm)$'),                  'excluded:spreadsheet-test-data',  '-'],
  [rx('^keys/'),                                'excluded:runtime-generated-keyring', '-'],
  // Operational scripts are real behaviour and belong in scope, not in the furniture pile.
  [rx('^scripts/'),                             'read',                            'P10'],
  [rx('(^|/)\\.gitattributes$'),                'excluded:tooling-dotfile',        '-'],
  // ---- hard exclusions that must beat everything below -------------------
  [rx('/node_modules/'),                        'excluded:third-party-dependency', '-'],
  [rx('^AdminUi/ClientApp/dist/'),              'excluded:build-output',           '-'],
  [rx('/wwwroot/lib/'),                         'excluded:vendor-library',         '-'],
  // Vendor DevExtreme bundles ship under wwwroot/js/devextreme/, NOT wwwroot/lib/, so the rule
  // above missed them and 73 vendor files (54 MB, incl. a 15 MB dx.all.debug.js) were classified
  // in-scope 'sweep-only' — contradicting Phase 8, which explicitly audited only the 24 custom
  // loose files in wwwroot/js and excluded vendor. Scoped to the devextreme/ subdirectory alone:
  // every custom file sits directly in wwwroot/js/, so this cannot swallow one.
  [rx('/wwwroot/js/devextreme/'),               'excluded:vendor-library',         '-'],
  // A THIRD vendor location, found the same way as the two above: by asking which `sweep-only` rows
  // had no stated reason. `TalabatkDelivery/wwwroot/jquery/` holds jQuery 3.5.1 in four variants
  // (full, min, slim, slim.min) and was matching neither `/wwwroot/lib/` nor `/wwwroot/js/devextreme/`,
  // so it was being counted as in-scope application JavaScript.
  [rx('/wwwroot/jquery/'),                      'excluded:vendor-library',         '-'],
  // Compiled TypeScript output committed alongside its source. Verified, not assumed: all 62
  // `*.spec.js` files under ClientApp/src have a matching `*.spec.ts`, and the one non-spec file
  // (`Shared/Enums/OrderStatus.js`) is transpiler output down to its trailing
  // `//# sourceMappingURL=OrderStatus.js.map` — with `OrderStatus.ts` and the `.js.map` both present.
  // The `.js.map` siblings were already excluded as source maps; the `.js` files were not, so 68 build
  // artifacts were classified as in-scope custom JavaScript for phase 8-1 to have swept.
  [rx('^(AdminUi|TalabatkRestaurants)/ClientApp/src/.*\\.js$'), 'excluded:build-output',    '-'],
  [rx('^(AdminUi|TalabatkRestaurants)/ClientApp/(karma\\.conf|custom-webpack\\.config)\\.js$'), 'excluded:build-tooling', '-'],
  [rx('/\\.cr/personal/'),                      'excluded:ide-personal-settings',  '-'],
  [rx('/\\.vscode/'),                           'excluded:editor-settings',        '-'],
  [rx('\\.angulardoc\\.json$'),                 'excluded:ide-tool-artifact',      '-'],
  [rx('\\.map$'),                               'excluded:source-map',             '-'],
  [rx('package-lock\\.json$'),                  'excluded:lockfile',               '-'],
  [rx('\\.lnk$'),                               'excluded:windows-shortcut-junk',   '-'],

  // ---- the two big justified code exclusions ----------------------------
  [rx('/Migrations/.*\\.Designer\\.cs$'),       'swept',                           '1-4'],
  // `(^|/)` and not `/`: the repo also has a ROOT-LEVEL `GeneratedClient/` directory, which the
  // leading-slash form silently missed. Its two files (32,887 lines of nswag output) therefore fell
  // through to the `\.cs$ -> read, 2-x` catch-all at the bottom and were counted as in-scope code that
  // some phase was supposed to have read individually. They are also STALE and uncompiled: the root
  // copies are ~1,800 lines behind their project-scoped twins, and no .csproj includes them (the
  // `<Folder Include="GeneratedClient\" />` entries in TalabatkAPIs.csproj:65 and AdminUi.csproj:161
  // refer to directories inside those projects, which SDK-style globbing picks up).
  // This is the same shape as the path-whitelist bug described in this file's header: a pattern that
  // looked exhaustive, agreed with itself, and left a class of files invisible.
  [rx('(^|/)GeneratedClient/.*\\.cs$'),         'excluded:nswag-generated-client',  '-'],

  // ---- binary secret material: recorded in Appendix A, not "read" -------
  [rx('\\.(pfx|cer|jwk)$'),                     'read',                            '5-5'],

  // ---- presentation + assets -------------------------------------------
  [rx('\\.(css|scss)$'),                        'excluded:styling-no-business-rules', '-'],
  [rx('\\.(png|ico|ttf|woff2?|svg|jpe?g|gif|webp|wav|mp3)$'), 'excluded:binary-asset', '-'],
  [rx('(^|/)(\\.gitignore|\\.gitkeep|\\.editorconfig|\\.browserslistrc)$'), 'excluded:tooling-dotfile', '-'],
  [rx('(^|/)LICENSE(\\.txt|\\.md)?$'),          'excluded:vendor-license',         '-'],

  // ---- Phase 1: database ------------------------------------------------
  [rx('/Migrations/TalabatkContextModelSnapshot\\.cs$'), 'read',                   '1-2'],
  [rx('/Migrations/.*\\.cs$'),                  'read',                            '1-1'],
  [rx('/TalabatkData/Mapping/.*\\.cs$'),        'read',                            '1-3'],

  // ---- Phase 2: ambiguous-coverage re-verify ----------------------------
  [rx('/TalabatkApplication/Commands/.*\\.cs$'), 'read',                           '2-1'],
  [rx('/TalabatkApplication/Queries/.*\\.cs$'),  'read',                           '2-2'],
  [rx('/TalabatkLogic/Enum/.*\\.cs$'),           'read',                           '2-3'],
  [rx('/TalabatkApplication/DTO/.*\\.cs$'),      'read',                           '2-4'],
  [rx('/Reports/.*\\.Designer\\.cs$'),           'read',                           '2-5'],

  // ---- Phase 3: Angular templates + i18n --------------------------------
  [rx('^AdminUi/ClientApp/src/.*\\.html$'),                'read',                 '3-1'],
  [rx('^TalabatkRestaurants/ClientApp/src/.*\\.html$'),     'read',                 '3-2'],
  [rx('/assets/i18n/.*\\.json$'),                           'read',                 '3-3'],

  // angular.json is NOT boilerplate: its `fileReplacements` block is the evidence finding #323
  // rests on (prod build swaps in an environment.prod.ts that declares production:false).
  [rx('/angular\\.json$'),                      'read',                            '3-1'],
  [rx('(^|/)package\\.json$'),                  'read',                            '6-3'],
  [rx('/(tsconfig[^/]*|tslint)\\.json$'),       'swept',                           '3-1'],

  // ---- Phase 4: report layouts ------------------------------------------
  [rx('\\.vsrepx$'),                            'read',                            '4-1'],

  // ---- Phase 5: configuration + secrets ---------------------------------
  [rx('(appsettings.*|launchSettings|nswag|libman|FireBaseConfigurations|appSettings)\\.json$'), 'read', '5-1'],
  [rx('/wwwroot/api/specification\\.json$'),    'read',                            '5-2'],
  [rx('\\.bak$'),                               'read',                            '5-3'],
  [rx('\\.pubxml$'),                            'read',                            '5-4'],
  [rx('/(ErrorLogs|App_Data)/.*\\.txt$'),       'read',                            '5-5'],

  // ---- Phase 6: CI/CD + infra -------------------------------------------
  [rx('^Builds/.*\\.(yml|yaml)$'),              'read',                            '6-1'],
  [rx('^(docker-compose.*\\.yml|nuget\\.config|version-update\\.yml)$'), 'read',    '6-2'],
  [rx('\\.csproj$'),                            'read',                            '6-3'],
  [rx('\\.sln$'),                               'read',                            '6-3'],
  [rx('\\.config$'),                            'read',                            '6-2'],
  [rx('\\.xml$'),                               'read',                            '6-2'],

  // ---- Phase 7: in-project docs ----------------------------------------
  [rx('\\.md$'),                                'read',                            '7-1'],

  // ---- Phase 8: custom application JS -----------------------------------
  [rx('/wwwroot/js/.*\\.js$'),                  'read',                            '8-1'],
  [rx('\\.js$'),                                'swept',                           '8-1'],

  // ---- Angular TS + Razor + resources (prior rounds; re-verified) -------
  // `swept`, not `read`: phase 3-1/3-2's method for TypeScript WAS a bulk sweep, with the files it
  // flagged individually read afterwards (the Round 5 phase4-TS batches). Claiming `read` for all 980
  // and then recording `sweep-only` as the evidence is the #382 contradiction in its purest form - one
  // column stating a phase's intent while the other denies it happened. `swept` states the method
  // truthfully, and the per-file `depth` still records which ones an agent actually opened.
  [rx('\\.ts$'),                                'swept',                           '3-1/3-2'],
  // `9-9`, not `5-3`. Phase 5-3 is the `.bak` backup parse; Razor views were sharing its code purely
  // because both were added to the rule list at the same time. They are not the same method and not
  // the same kind of file, and lumping them meant the phase column said nothing true about either.
  [rx('\\.cshtml$'),                            'read',                            '9-9'],
  [rx('\\.resx$'),                              'read',                            '5-1'],
  [rx('\\.sql$'),                               'read',                            '1-1'],

  // ---- Phase 9: Path A ---------------------------------------------------
  // `2-x` was never a phase. It was the label the catch-all below stamped on every .cs file no
  // earlier rule claimed, and it recorded "some phase-2 activity happened here" with no method. 1,722
  // files carried it, which is why the size of the remaining gap was misread twice: a file genuinely
  // covered by a named parse and a file nobody had ever opened were indistinguishable in the manifest.
  //
  // These rules name the method instead. Each maps to one Path A inbox report under `_inbox/`, so a
  // phase code can be traced to the evidence for it rather than taken on trust.
  [rx('^Shared/TalabatkLogic/TalabatkModels/.*\\.cs$'),   'read', '9-1'], // pathA-A-models-batch00..04
  [rx('^Shared/TalabatkLogic/DomainEvents/.*\\.cs$'),     'read', '9-2'], // pathA-C-domainevents
  [rx('^Shared/TalabatkApplication/OrderBuilder/.*\\.cs$'), 'read', '9-3'], // pathA-F-orderbuilder
  [rx('^Shared/TalabatkData/Cassandra/.*\\.cs$'),         'read', '9-4'], // pathA-G-cassandra
  [rx('^Shared/TalabatkData/ElasticSerarchServices/.*\\.cs$'), 'read', '9-5'], // pathA-E-elastic
  [rx('/Helpers?/.*\\.cs$'),                              'read', '9-6'], // pathA-D-helpers
  [rx('^Shared/TalabatkLogic/DomainEventHelpers/.*\\.cs$'), 'read', '9-6'],
  [rx('^(AdminUi|TalabatkRestaurants)/[Rr]eports/(?!.*\\.Designer\\.cs$).*\\.cs$'), 'read', '9-7'], // pathA-B-reports

  // ---- everything else .cs: host + shared code --------------------------
  // Still a catch-all, but it now means something narrower and honest: a .cs file that no named phase
  // claims. Anything landing here is a gap by definition, and the depth ledger must say why.
  [rx('\\.cs$'),                                'read',                            '2-x'],

  // ---- residual text ----------------------------------------------------
  [rx('\\.txt$'),                               'read',                            '5-5'],
];

// Enumerate EVERY tracked file, with no path filter.
//
// This used to run `git ls-files -- <SCOPE_PATHS>`, a 13-path whitelist — which meant any tracked
// file outside those paths was not "excluded", it was **invisible**: never enumerated, never
// classified, never reported as unclassified. `git ls-files` returns 14,076 files; the whitelist
// returned 8,491, and the verifier then compared that filtered list against a manifest built from
// the same filtered list, so it agreed with itself and exited 0.
//
// That is the Round 2 defect reproduced one level up. Round 1 walked `Commands/` in letter-FOLDER
// buckets, so loose root-level files matched no bucket and were missed; this walked the repo in PATH
// buckets, so everything outside them was missed the same way — including all 5 `.sln` files, the
// root-level `.sql` scripts, `CONTEXT-MAP.md`, `README.md`, `reconcile_all.py` and `TieredDiscountPlan/`.
// Phase 10 caught it only because it re-derived the file list by walking the filesystem instead of
// asking git the same question twice.
//
// Now: enumerate everything, and let RULES classify it. Out-of-scope projects are `excluded:` with a
// stated reason rather than absent, so "unclassified" becomes a real signal instead of an empty set.
// SCOPE_PATHS is kept only for documentation of the in-scope 9 projects; it no longer gates enumeration.
function gitFiles() {
  const out = execSync('git ls-files', {
    cwd: REPO, encoding: 'utf8', maxBuffer: 1024 * 1024 * 400,
  });
  return out.split('\n').map((s) => s.trim()).filter(Boolean);
}

function classify(file) {
  for (const [re, status, phase] of RULES) {
    if (re.test(file)) return { status, phase };
  }
  return { status: 'UNCLASSIFIED', phase: '?' };
}

function sizeOf(file) {
  try { return fs.statSync(path.join(REPO, file)).size; } catch { return 0; }
}

// Content fingerprint, so the verifier can detect that covered code CHANGED - not merely that files
// appeared or vanished. Without this the manifest passes cleanly while the code beneath a finding is
// rewritten, i.e. the graph goes stale silently. That is the one drift class the file-list check
// cannot see, and citations here have already gone stale twice across a single rebase.
// Excluded files are skipped: nothing in the KG asserts anything about their contents, and it keeps
// the hash pass off ~6,500 files (including 329 MB of generated migration snapshots).
//
// **Line endings are normalised before hashing, and must stay identical to `verify-notes.js`'s
// `hashOf`.** This repository stores LF and checks out CRLF, so the bytes on disk change whenever git
// touches a file — branch switch, fresh clone, a teammate with a different `core.autocrlf`. Hashing raw
// bytes reported all 1,879 cited files as drifted after one branch switch, with zero content change,
// and made genuine drift indistinguishable from checkout churn. See `_conflicts.md` #652.
//
// Binary files keep a raw-byte hash — stripping `\r` from a PNG is corruption, not normalisation.
// A NUL byte in the first 8 KB is the binary test, the same one git uses.
function hashOf(file, status) {
  if (String(status).startsWith('excluded')) return '-';
  try {
    const buf = fs.readFileSync(path.join(REPO, file));
    const isBinary = buf.subarray(0, 8192).includes(0);
    const content = isBinary ? buf : Buffer.from(buf.toString('utf8').replace(/\r\n/g, '\n'), 'utf8');
    return crypto.createHash('sha1').update(content).digest('hex').slice(0, 12);
  } catch { return '-'; }
}

function build() {
  return gitFiles().map((file) => {
    const { status, phase } = classify(file);
    const ext = (file.split('/').pop().match(/\.([A-Za-z0-9_]+)$/) || [, '(noext)'])[1].toLowerCase();
    return { file, ext, size: sizeOf(file), status, phase, hash: hashOf(file, status) };
  });
}

function commitSha() {
  try { return execSync('git rev-parse HEAD', { cwd: REPO, encoding: 'utf8' }).trim(); }
  catch { return 'unknown'; }
}

function writeManifest(rows) {
  const sha = commitSha();
  // Preserve the `depth` column across regeneration. Without this, a --generate after any rebase
  // would silently reset every read-evidence marker to blank and the honest depth split would be
  // lost - reintroducing exactly the "status says read, nothing proves it" problem the column exists
  // to expose. A file new to this commit has no evidence yet, so it starts as sweep-only.
  const prior = new Map();
  const existing = readManifest();
  if (existing) for (const r of existing) if (r.depth) prior.set(r.file, r.depth);
  const ledger = loadLedger();
  const depthOf = (r) => resolveDepth(r.file, r.status, prior.get(r.file), ledger).depth;

  const header = `# path\text\tbytes\tstatus\tphase\tdepth\tsha1_12\n# commit=${sha}\tgenerated_at_commit_only\tfiles=${rows.length}\n`;
  fs.writeFileSync(TSV,
    header + rows.map((r) => [r.file, r.ext, r.size, r.status, r.phase, depthOf(r), r.hash].join('\t')).join('\n') + '\n', 'utf8');

  // ---- human-readable summary -------------------------------------------
  const byStatus = {}, byPhase = {}, byExt = {};
  for (const r of rows) {
    const key = r.status.startsWith('excluded') ? r.status : r.status;
    byStatus[key] = (byStatus[key] || 0) + 1;
    if (!r.status.startsWith('excluded')) byPhase[r.phase] = (byPhase[r.phase] || 0) + 1;
    byExt[r.ext] = (byExt[r.ext] || 0) + 1;
  }
  const covered = rows.filter((r) => !r.status.startsWith('excluded'));
  const lines = [];
  lines.push('# 8Orders KG — Coverage Manifest (summary)');
  lines.push('');
  lines.push('> Machine-generated. **Do not hand-edit.** Regenerate with');
  lines.push('> `node docs/knowledge-graph/_system/verify-coverage.js --generate`,');
  lines.push('> verify with `node docs/knowledge-graph/_system/verify-coverage.js`.');
  lines.push('>');
  lines.push('> Row-level data lives in `_coverage-manifest.tsv` (one line per file). This file is the');
  lines.push('> summary. The verifier is the authority — if it exits non-zero, this summary is stale.');
  lines.push('');
  lines.push(`**Attested commit:** \`${sha}\``);
  lines.push('');
  lines.push(`**Total tracked in-scope files:** ${rows.length}`);
  lines.push(`**In coverage scope (read + swept):** ${covered.length}`);
  lines.push(`**Deliberately excluded:** ${rows.length - covered.length}`);
  lines.push('');
  lines.push('## By status');
  lines.push('');
  lines.push('| status | files |');
  lines.push('|---|---|');
  for (const k of Object.keys(byStatus).sort()) lines.push(`| \`${k}\` | ${byStatus[k]} |`);
  lines.push('');
  lines.push('## By phase (covered files only)');
  lines.push('');
  lines.push('| phase | files |');
  lines.push('|---|---|');
  for (const k of Object.keys(byPhase).sort()) lines.push(`| ${k} | ${byPhase[k]} |`);
  lines.push('');
  lines.push('## By extension');
  lines.push('');
  lines.push('| ext | files |');
  lines.push('|---|---|');
  for (const k of Object.keys(byExt).sort((a, b) => byExt[b] - byExt[a])) lines.push(`| \`${k}\` | ${byExt[k]} |`);
  lines.push('');
  lines.push('## How this prevents a fourth false completion');
  lines.push('');
  lines.push('Every prior round asserted completeness in prose and could not detect its own staleness.');
  lines.push('This manifest is derived from `git ls-files`, so a rebase, merge, or new commit that adds');
  lines.push('a file makes the verifier fail and name that file. Coverage is therefore a property that');
  lines.push('is re-provable at any commit, not a claim frozen at the moment someone wrote it down.');
  lines.push('');
  fs.writeFileSync(MD, lines.join('\n'), 'utf8');
}

function readManifest() {
  if (!fs.existsSync(TSV)) return null;
  return readLines(TSV)
    .filter((l) => l && !l.startsWith('#'))
    .map((l) => { const [file, ext, size, status, phase, depth, hash] = l.split('\t'); return { file, ext, size, status, phase, depth, hash }; });
}

function verify() {
  const current = build();
  const stored = readManifest();
  const problems = [];
  let changedEvidenced = [];
  let changedOther = 0;

  const unclassified = current.filter((r) => r.status === 'UNCLASSIFIED');
  for (const r of unclassified) problems.push(`UNCLASSIFIED  ${r.file}  (ext=${r.ext}) -> matches no scope rule`);

  if (!stored) {
    problems.push('NO MANIFEST  _coverage-manifest.tsv is missing - run with --generate');
  } else {
    const s = new Set(stored.map((r) => r.file));
    const c = new Set(current.map((r) => r.file));
    for (const r of current) if (!s.has(r.file)) problems.push(`NEW      ${r.file} -> in git, absent from manifest (never audited)`);
    for (const r of stored) if (!c.has(r.file)) problems.push(`REMOVED  ${r.file} -> in manifest, gone from git (manifest stale)`);

    // ---- content drift ----------------------------------------------------
    // Deliberately two-tier, because a single tier would make this check useless. Treating ANY content
    // change as failure means the verifier goes red on every ordinary commit and gets ignored; treating
    // none as failure is the silent-staleness hole this column exists to close. So: a change to a file
    // the KG actually CITES (depth=evidenced) is drift and fails, because a finding may no longer hold
    // at the line it names. Changes elsewhere are counted and shown, not failed.
    const priorHash = new Map(stored.filter((r) => r.hash && r.hash !== '-').map((r) => [r.file, r.hash]));
    changedEvidenced = [];
    changedOther = 0;
    const depthOfStored = new Map(stored.map((r) => [r.file, r.depth]));
    for (const r of current) {
      const was = priorHash.get(r.file);
      if (!was || r.hash === '-' || was === r.hash) continue;
      if (depthOfStored.get(r.file) === 'evidenced') changedEvidenced.push(r.file);
      else changedOther++;
    }
    for (const f of changedEvidenced) {
      problems.push(`CHANGED  ${f} -> content differs from the audited version, and the KG cites this file`);
    }
  }

  console.log(`commit         : ${commitSha()}`);
  console.log(`tracked files  : ${current.length}`);
  console.log(`covered        : ${current.filter((r) => !r.status.startsWith('excluded')).length}`);
  console.log(`excluded       : ${current.filter((r) => r.status.startsWith('excluded')).length}`);
  console.log(`unclassified   : ${unclassified.length}`);

  // Depth split. The `status` column says what a phase was SUPPOSED to do with a file; `depth` says
  // whether anything in the knowledge graph actually cites it. Printing both is the point: three
  // previous rounds declared completion on the strength of the first number alone. `sweep-only` does
  // NOT mean unread - a file read in an earlier round and found clean leaves no citation - it means
  // the claim is not provable from the KG, which is the only thing an attestation may rely on.
  if (stored && stored.some((r) => r.depth)) {
    const scope = stored.filter((r) => !String(r.status || '').startsWith('excluded'));
    const count = (d) => scope.filter((r) => r.depth === d).length;
    const ev = count('evidenced'), ar = count('agent-read'), pa = count('parsed'), sw = count('sweep-only');
    console.log('');
    console.log(`depth: evidenced  (a KG note cites this file)        : ${ev}`);
    console.log(`depth: agent-read (a named report says it was read)  : ${ar}`);
    console.log(`depth: parsed     (a named parser extracted from it) : ${pa}`);
    console.log(`depth: sweep-only (bulk pass, reason in the ledger)  : ${sw}`);
    const unaccounted = scope.length - ev - ar - pa - sw;
    if (unaccounted !== 0) console.log(`depth: UNKNOWN VALUE                                 : ${unaccounted}  <- these FAIL the check`);

    // ---- Step 4: status vs depth ------------------------------------------
    // The contradiction this resolves: `status` is the phase's INTENT and `depth` is the EVIDENCE, and
    // for 1,723 rows they disagreed outright - `read` next to `sweep-only`. Rather than quietly pick a
    // winner, the two claims are now reconciled out loud. A row is consistent when its status's
    // promise is backed by its depth; `swept` promises only a bulk pass, so `sweep-only` satisfies it.
    const backed = new Set(['evidenced', 'agent-read', 'parsed']);
    const contradictions = scope.filter((r) => r.status === 'read' && !backed.has(r.depth));
    // A `sweep-only` row is only acceptable if the ledger says WHY. Without this check the value is
    // indistinguishable from the old `2-x`: a shrug that looks like a record. A file that reaches
    // `sweep-only` by falling through every ledger line has no stated reason and is a bare gap.
    const ledgerForCheck = loadLedger();
    const reasonFor = (f) => {
      for (const row of ledgerForCheck) {
        if (row.set ? row.set.has(f) : row.re.test(f)) return row;
      }
      return null;
    };
    const unreasoned = scope.filter((r) => r.depth === 'sweep-only' && !reasonFor(r.file));
    console.log(`              of which sweep-only WITHOUT a stated reason      : ${unreasoned.length}` +
                (unreasoned.length ? '  <- bare gaps' : ''));
    if (unreasoned.length) {
      const byExt = {};
      for (const r of unreasoned) byExt[r.ext] = (byExt[r.ext] || 0) + 1;
      for (const k of Object.keys(byExt).sort((a, b) => byExt[b] - byExt[a]).slice(0, 12)) {
        console.log(`                .${String(k).padEnd(12)} ${byExt[k]}`);
      }
    }

    console.log('');
    console.log(`status/depth: consistent rows                        : ${scope.length - contradictions.length}`);
    console.log(`status/depth: status=read but depth is not evidenced/agent-read/parsed : ${contradictions.length}`);
    if (contradictions.length) {
      const byPhase = {};
      for (const r of contradictions) byPhase[r.phase] = (byPhase[r.phase] || 0) + 1;
      console.log('              ^ these are the honest remaining gaps, by phase:');
      for (const k of Object.keys(byPhase).sort((a, b) => byPhase[b] - byPhase[a])) {
        console.log(`                ${String(k).padEnd(10)} ${byPhase[k]}`);
      }
      console.log('              A `read` status is a phase\'s intent, not evidence. Either add a');
      console.log('              ledger line stating what covered these, or leave them listed here.');
    }
    if (stored.some((r) => r.hash && r.hash !== '-')) {
      console.log('');
      console.log(`content drift: cited files changed  : ${changedEvidenced.length}  ${changedEvidenced.length ? '<- these FAIL the check' : ''}`);
      console.log(`content drift: other covered changed: ${changedOther}  (informational - ordinary development)`);
    }
  }
  console.log('');
  if (problems.length === 0) {
    console.log('COVERAGE OK - manifest matches git, every file enumerated and classified.');
    console.log('             (This proves nothing is MISSED. Read-depth is the `depth` split above.)');
    return 0;
  }
  console.log(`COVERAGE DRIFT - ${problems.length} problem(s):`);
  for (const p of problems.slice(0, 60)) console.log('  ' + p);
  if (problems.length > 60) console.log(`  ... and ${problems.length - 60} more`);
  return 1;
}

const arg = process.argv[2];
if (arg === '--generate') {
  const rows = build();
  writeManifest(rows);
  const un = rows.filter((r) => r.status === 'UNCLASSIFIED');
  console.log(`generated: ${rows.length} files -> _coverage-manifest.tsv + .md`);
  console.log(`unclassified: ${un.length}`);
  for (const r of un.slice(0, 40)) console.log('  UNCLASSIFIED ' + r.file);
  process.exit(un.length === 0 ? 0 : 1);
} else {
  process.exit(verify());
}
