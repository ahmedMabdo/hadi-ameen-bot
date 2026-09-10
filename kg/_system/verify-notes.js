#!/usr/bin/env node
/**
 * 8Orders Knowledge Graph — KNOWLEDGE-axis verifier
 *
 * WHY THIS EXISTS
 * ---------------
 * `verify-coverage.js` answers "was every file looked at?". It cannot answer "is the knowledge
 * graph finished?", because coverage counts FILES and the graph is made of NOTES. For three weeks
 * the knowledge axis had no denominator: every round guessed how much was left, so "finished" was
 * never provable and was wrong every time it was claimed. This script is the denominator.
 *
 *   node verify-notes.js                 verify: exit 0 if the graph is complete, non-zero otherwise
 *   node verify-notes.js --generate      rebuild the derived indexes (_source-index.tsv, _id-index.tsv)
 *   node verify-notes.js --stamp         fill in MISSING source sha1s (never overwrites a mismatch)
 *   node verify-notes.js --restamp <p>   after a human re-verified note <p> against changed code
 *   node verify-notes.js --register-check  register numbering: sequential, no gaps, no duplicates
 *   node verify-notes.js --self-test     prove the checker can SEE each gap class before it is trusted
 *
 * THE ONE RULE OF THIS FILE
 * -------------------------
 * Expectation comes from CODE. Observation comes from DISK. Never both from the same source.
 * That rule is not stylistic — violating it has already produced two false "all clear" results in
 * this project (see the header of `audit-inbox-merge.js`, and the filename-matching bug that hid a
 * critical finding behind five existing citations). Concretely:
 *   - the set of entities that MUST have notes is derived from the repo's own class files;
 *   - the set of entities that DO have notes is derived from the note files on disk;
 *   - the two are compared in BOTH directions, so neither a missing note nor an invented note
 *     can pass.
 * `_entity-classes.tsv` and `_feature-map.tsv` carry human judgment (what kind of thing a class is,
 * which feature an endpoint belongs to). They are not trusted blindly: every row is checked against
 * git, every excluded row must state its evidence, and any candidate the loader has no row for is a
 * hard failure. Judgment is allowed; unstated judgment is not.
 *
 * `--self-test` exists because a checker that cannot see is worse than no checker: it converts an
 * unknown into a false assurance. It plants one synthetic instance of every failure class and
 * asserts the checker reports it. Run it whenever a check is added or changed.
 *
 * ENUMERATION IS VIA `git ls-files`, DELIBERATELY NOT `find`
 * ---------------------------------------------------------
 * `find` descends node_modules before pruning and times out on this repo; `find -name "*.cs"`
 * without `-type f` counts DIRECTORIES as files, and this repo contains a directory literally named
 * `GetCustomerDetailsToAdminQuery.cs`. This has cost time twice. Every path here is handled with
 * node's fs API rather than a shell loop, because 102 of the note paths contain a space or `&` and
 * unquoted shell loops break on them silently.
 */

'use strict';
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const SYSTEM_DIR = __dirname;
const KG_DIR = path.resolve(SYSTEM_DIR, '..');
const REPO = path.resolve(SYSTEM_DIR, '..', '..', '..');
const KG_REL = 'docs/knowledge-graph';

const ENTITY_TSV = path.join(SYSTEM_DIR, '_entity-classes.tsv');
const FEATURE_TSV = path.join(SYSTEM_DIR, '_feature-map.tsv');
const SOURCE_INDEX = path.join(SYSTEM_DIR, '_source-index.tsv');
const ID_INDEX = path.join(SYSTEM_DIR, '_id-index.tsv');
const CONFLICTS = path.join(SYSTEM_DIR, '_conflicts.md');
const IDOR = path.join(SYSTEM_DIR, '_idor-instances.md');
const INTEGRATIONS = path.join(SYSTEM_DIR, '_integrations.md');

// ---------------------------------------------------------------------------
// Vocabulary. The first four `class` values are the skill's own entity types; the rest are the
// classes that are legitimately NOT knowledge-graph entities. A row in one of the excluded classes
// must state its evidence — the same discipline `_depth-ledger.tsv` enforces on a depth claim, and
// for the same reason: an unexplained exclusion is how a blind spot enters a "complete" graph.
// ---------------------------------------------------------------------------
const DOCUMENTED_CLASSES = new Set(['aggregate-root', 'legacy-poco-root', 'child', 'lookup']);
const EXCLUDED_CLASSES = new Set([
  'projection',          // stored-procedure / report result shape, no invariants
  'join-table',          // pure link row, one-line factory
  'enum-only',           // file declares only enums
  'identity-framework',  // ASP.NET Identity plumbing subclass
  'keyless-view',        // registered .HasNoKey().ToView(null)
  'dto',                 // input/output DTO living under a model folder
  'infrastructure',      // base classes, helpers, non-entity types
  'domain-event',        // event record raised by an aggregate; carries no invariants of its own
  'domain-behaviour',    // strategy / calculator / scheduled job: rule-bearing but not an entity.
                         // Its evidence MUST name the note that documents those rules, so widening
                         // the denominator cannot turn "excluded" into "undocumented".
]);
const RULE_BEARING = new Set(['aggregate-root', 'legacy-poco-root']);

// A shape that says "this entity gets a page of its own". Used by NOTE-STUB: whatever an entity's
// class, if the graph decided it deserves its own note then that note owes the reader its rules.
const OWN_NOTE = new Set(['pair', 'single']);

// A `path.ext:line` claim. Counted rather than resolved here — verify-citations.js decides whether each
// one is true; this file only asks whether a note makes any checkable claim at all.
function countCitations(body) {
  return (String(body || '').match(/`[^`\s:]+\.(?:cs|ts|cshtml|json|js)(?::\d+)/g) || []).length;
}

// Substance thresholds. Every one of these was calibrated against the vault as it actually is, not
// picked round: the floor sits just under the thinnest note that a reader would call an answer, so it
// fails the vacuous ones without demanding uniformity.
const MIN_FEATURE_CITATIONS = 5;   // a feature knowledge-graph with fewer is a map, not a graph
const MIN_SCENARIO_ROWS = 10;      // 5 sections x 2 rows is the floor for "what happens if..."
const MIN_NOTE_CITATIONS = 1;      // a technical note with none cannot be checked at all

// A note admitting in its own words that it was not read. These phrases were written honestly by
// earlier passes and then never revisited; the graph reported them as complete because no check looked
// at prose. Matching the admission is the only way to make the honesty actionable.
//
// Two tiers, because the first cut of this check conflated two very different statements. A note
// calling ITSELF a light note is a gap. A deep note recording "X was not traced in this pass" inside
// its Open Questions is the opposite of a gap — it is the graph doing what it was designed to do, and
// flagging it would punish the honesty that makes the rest trustworthy.
const SELF_FLAGGED_HARD = new RegExp([
  '\\(light note\\)', '\\(light tier\\)', '\\(light-tier\\)',
  'none of these (?:were|was) read',
  'no separate technical depth',
  'controller-level map, not',
  'documented at controller-map depth only',
  'not read past their route list',
  'this note only records that they exist',
  'light tier, per this batch',
  'not traced in this pass \\|',            // a table cell admitting the row is unverified
].join('|'), 'i');

// Tier 2: a scoped "not traced" admission — a named field, method or sub-flow the note says it did not
// follow. Counted and listed, never gated.
//
// The first cut gated on these too, and that was wrong in both directions. It fired on `_master-plan.md`
// for *describing* the light-tier problem, and on a note whose link label happened to contain "light
// note" — neither is a statement about itself. And where it did fire correctly, on a caveat like
// "`DeliveryBoxUnitSizeId` ties to `DeliveryBoxUnitSize` (not opened in this pass)", the caveat is the
// most useful clause in the row: it names exactly which sub-claim is unverified. Forcing it into an Open
// Question would move the warning away from the claim it qualifies.
//
// So the design is the one verify-citations.js already uses: gate on what is decidable (a note calling
// itself thin), report what is judgement (a scoped unknown). Reported means counted and listable, so no
// caveat is lost — which was the actual defect: 40 were accumulating with nothing tracking them.
const SELF_FLAGGED_SCOPED = /not (?:been )?(?:read|traced|opened|investigated|audited)\s+in\s+(?:this|that)\s+pass/i;

// Everything from the first `## Open Question` heading onward. Anything after it is a declared unknown.
function beforeOpenQuestions(body) {
  const at = String(body || '').search(/^##+\s*Open Question/im);
  return at < 0 ? String(body || '') : String(body).slice(0, at);
}
const SHAPES = { PAIR: 'pair', SINGLE: 'single', NONE: 'none' }; // plus covered-by:<Entity>

const CONTEXTS = ['Customer Ordering', 'Restaurant Portal', 'Delivery', 'Admin',
  'Identity & Access', 'Version API'];

// A context whose project is excluded from coverage scope still gets a `_context.md` hub (the skill
// lists it as a context) but is not expected to have features. Recording it here is what turns the
// skill-vs-manifest contradiction into data instead of an argument.
const CONTEXTS_WITHOUT_FEATURES = new Set(['Version API']);

const NOTE_TYPES = new Set(['business', 'technical', 'single', 'overview', 'knowledge-graph',
  'scenarios', 'context', 'system', 'register', 'index', 'plan',
  // One file per register finding, generated by gen-issues.js, carrying the per-issue fix status a
  // table cell cannot hold. Derived: `_conflicts.md` remains the source of truth for the findings
  // themselves, and keeps the sha1 stamps — 651 more stamped source lists would be 651 more things to
  // restamp on every code change, for a guarantee the register already provides.
  'issue']);

// Machine-generated files carry no hand-authored frontmatter and are exempt.
const FRONTMATTER_EXEMPT = new Set([
  `${KG_REL}/_system/_coverage-manifest.md`,
]);
// System bookkeeping notes are real notes (they get frontmatter) but they are not feature/entity
// notes, so entity-shaped checks do not apply to them.
const SYSTEM_NOTES = new Set([
  '_conflicts.md', '_coverage-manifest.md', '_entity-index.md', '_glossary.md', '_idor-instances.md',
  '_integrations.md', '_pathA-work-order.md', '_round4-delivery.md', '_system-index.md',
  '_master-plan.md', '_gap-baseline.md', 'REBASE-PLAYBOOK.md',
]);

const FEATURE_REQUIRED = ['_overview.md', '_knowledge-graph.md', '_scenarios.md'];

// ---------------------------------------------------------------------------
// git plumbing
// ---------------------------------------------------------------------------
// Tracked files PLUS untracked-but-present ones. The vault on disk is the observation; a note written
// but not yet `git add`ed is really there, and counting it as absent produced a phantom
// CONTEXT-MISSING for a file that existed. Source files are enumerated the same way, so a new class
// that has not been committed still enters the entity denominator rather than hiding until it does.
function gitFiles() {
  const opts = { cwd: REPO, encoding: 'utf8', maxBuffer: 1024 * 1024 * 400 };
  const tracked = execSync('git ls-files', opts);
  const untracked = execSync('git ls-files --others --exclude-standard', opts);
  return [...new Set((tracked + '\n' + untracked).split('\n').map((s) => s.trim()).filter(Boolean))];
}

// Same fingerprint function `verify-coverage.js` uses (sha1 of file content, first 12 hex chars),
// deliberately NOT the git blob sha: the two verifiers must agree on what "this file changed" means,
// and a content hash also works on a dirty working tree, which is where a rebase leaves you.
//
// **Line endings are normalised before hashing, and that is not cosmetic.** This repository stores LF
// and checks out CRLF, so the bytes on disk change every time git touches a file — a branch switch, a
// fresh clone, a different `core.autocrlf`. Hashing raw bytes made both verifiers report every stamped
// file as changed after a branch switch, with no content difference at all: 1,879 phantom
// CITATION-STALE / COVERAGE-DRIFT failures whose only cause was `\r`. Worse than the noise, it made
// real drift indistinguishable from checkout churn, and it was self-inflicted symmetry — the two tools
// were built to agree, so they agreed on being wrong. See `_conflicts.md` #652.
//
// Binary files keep a raw-byte hash: stripping `\r` from a PNG would be corruption, not normalisation.
// Detection is a NUL byte in the first 8 KB, which is what git itself uses to decide the same question.
function hashOf(relPath) {
  try {
    const buf = fs.readFileSync(path.join(REPO, relPath));
    const isBinary = buf.subarray(0, 8192).includes(0);
    const content = isBinary ? buf : Buffer.from(buf.toString('utf8').replace(/\r\n/g, '\n'), 'utf8');
    return crypto.createHash('sha1').update(content).digest('hex').slice(0, 12);
  } catch { return null; }
}

function readIfExists(p) {
  try { return fs.readFileSync(p, 'utf8'); } catch { return null; }
}

// Every file in this repo is CRLF. A JS regex ending in `$` will not match a line that still carries
// its `\r`, because `\r` is a line terminator and `.` refuses to cross it — so a table-row pattern
// silently matches NOTHING and the check reports a clean zero. That exact bug made the register check
// print "0 rows" against a 605-row register on this file's first run. Normalise once, at the door.
function lines(text) {
  return String(text || '').split('\n').map((l) => l.replace(/\r$/, ''));
}

// ---------------------------------------------------------------------------
// TSV loaders. Line-aware errors, mandatory columns, mandatory evidence — the `_depth-ledger.tsv`
// contract, reused rather than reinvented.
// ---------------------------------------------------------------------------
function loadTsv(file, columns, label) {
  const txt = readIfExists(file);
  if (txt === null) throw new Error(`${label}: ${path.basename(file)} is missing — cannot derive a denominator without it`);
  const rows = [];
  const lines = txt.split('\n');
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].replace(/\r$/, '');
    if (!line.trim() || line.trim().startsWith('#')) continue;
    const parts = line.split('\t');
    if (parts.length < columns.length) {
      throw new Error(`${path.basename(file)}:${i + 1} has ${parts.length} columns, needs ${columns.length} (${columns.join(', ')})`);
    }
    const row = { __line: i + 1 };
    columns.forEach((c, idx) => { row[c] = (parts[idx] || '').trim(); });
    rows.push(row);
  }
  return rows;
}

const ENTITY_COLS = ['entity', 'source_path', 'class', 'shape', 'context', 'feature', 'evidence'];
const FEATURE_COLS = ['controller_path', 'context', 'feature', 'evidence'];

// ---------------------------------------------------------------------------
// Frontmatter. A deliberately strict miniature YAML reader: it understands exactly the schema the
// KG uses and rejects anything else. Strictness is the point — a silently mis-parsed field would
// make a note look compliant while carrying nothing a consumer can use.
// ---------------------------------------------------------------------------
function parseFrontmatter(text) {
  if (!text.startsWith('---')) return { ok: false, error: 'no frontmatter block' };
  const end = text.indexOf('\n---', 3);
  if (end === -1) return { ok: false, error: 'frontmatter block never closes' };
  const body = text.slice(3, end).replace(/^\r?\n/, '');
  const fm = { sources: [] };
  const lines = body.split('\n');
  let inSources = false;
  let current = null;
  for (let i = 0; i < lines.length; i++) {
    const raw = lines[i].replace(/\r$/, '');
    if (!raw.trim()) continue;
    if (inSources) {
      let m = raw.match(/^\s{2,}-\s*path:\s*(.+)$/);
      if (m) { current = { path: m[1].trim().replace(/^["']|["']$/g, ''), sha1: null }; fm.sources.push(current); continue; }
      m = raw.match(/^\s{3,}sha1:\s*(.+)$/);
      if (m && current) { current.sha1 = m[1].trim().replace(/^["']|["']$/g, ''); continue; }
      if (/^\s/.test(raw)) return { ok: false, error: `unparsed line inside sources: "${raw.trim()}"` };
      inSources = false;
    }
    const m = raw.match(/^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$/);
    if (!m) return { ok: false, error: `unparsed frontmatter line: "${raw.trim()}"` };
    const key = m[1];
    const val = m[2].trim();
    if (key === 'sources') {
      if (val && val !== '[]') return { ok: false, error: 'sources must be a block list' };
      inSources = true; continue;
    }
    if (val.startsWith('[') && val.endsWith(']')) {
      fm[key] = val.slice(1, -1).split(',').map((s) => s.trim().replace(/^["']|["']$/g, '')).filter(Boolean);
    } else {
      fm[key] = val.replace(/^["']|["']$/g, '');
    }
  }
  return { ok: true, fm, endOffset: end + 4 };
}

// ---------------------------------------------------------------------------
// Model: everything the checks run against. Built from git + disk; NEVER from the checks' own output.
// ---------------------------------------------------------------------------
// The whole domain layer, not a hand-picked corner of it.
//
// This filter used to be an allow-list: `TalabatkModels/` plus four named aggregate folders. It
// therefore asked about 304 of the 529 .cs files in the domain layer and was silent about the other
// 225 — including `AccountingEntry.cs` (a live DbSet sitting at the folder root), the profit
// calculators under `DomainServices/`, the order-to-driver assignment strategies, and one POCO whose
// only crime was living one folder deeper than `[^/]+\.cs$` allows. None of them could ever be
// reported missing, because nothing ever asked.
//
// An allow-list denominator is the same mistake as finding #384 wearing different clothes: it makes
// the answer to "is anything undocumented?" a function of the filter rather than of the code. So the
// denominator is now the domain layer itself, and every file in it needs a row — either a documented
// class or an excluded one with a stated reason. Widening this is what turned 225 silent omissions
// into 225 answerable questions.
// Markdown table cells, splitting on unescaped pipes only. Used by REGISTER-ROW-MALFORMED.
function registerCells(row) {
  return String(row).split(/(?<!\\)\|/).length;
}

function candidateEntityFiles(files) {
  return files.filter((f) => /^Shared\/TalabatkLogic\/.*\.cs$/.test(f));
}

function candidateControllerFiles(files) {
  const HOSTS = ['TalabatkAPIs', 'TalabatkRestaurants', 'TalabatkDelivery', 'AdminUi',
    'Talabatk.IDS', 'Talabatk.VersionAPI'];
  return files.filter((f) => {
    const host = f.split('/')[0];
    if (!HOSTS.includes(host)) return false;
    return /\/Controllers\//.test(f) && /\.cs$/.test(f);
  });
}

function vaultNotes(files) {
  return files.filter((f) => f.startsWith(`${KG_REL}/`) && f.endsWith('.md')
    && !f.startsWith(`${KG_REL}/_system/_inbox/`));
}

function buildModel() {
  const files = gitFiles();
  const gitSet = new Set(files);
  const entityRows = loadTsv(ENTITY_TSV, ENTITY_COLS, 'entity denominator');
  const featureRows = loadTsv(FEATURE_TSV, FEATURE_COLS, 'feature denominator');

  const notes = [];
  for (const rel of vaultNotes(files)) {
    const abs = path.join(REPO, rel);
    const text = readIfExists(abs);
    if (text === null) continue;
    const parsed = parseFrontmatter(text);
    notes.push({
      rel,
      base: rel.split('/').pop(),
      dir: rel.split('/').slice(0, -1).join('/'),
      text,
      fm: parsed.ok ? parsed.fm : null,
      fmError: parsed.ok ? null : parsed.error,
      // Body only. The `covers:` mention test must never see the frontmatter, or it grades the covers
      // list against itself — the entity name is literally in that list, so every claim would pass.
      // Same circularity error as before, one field over.
      body: parsed.ok ? text.slice(parsed.endOffset) : text,
    });
  }

  return {
    gitSet,
    candidateEntities: candidateEntityFiles(files),
    candidateControllers: candidateControllerFiles(files),
    entityRows,
    featureRows,
    notes,
    dirs: new Set(files.filter((f) => f.startsWith(`${KG_REL}/`))
      .map((f) => f.split('/').slice(0, -1).join('/'))),
    integrationsText: readIfExists(INTEGRATIONS) || '',
    conflictsText: readIfExists(CONFLICTS) || '',
    idorText: readIfExists(IDOR) || '',
    // Mechanical integration scan: expectation for the register comes from code, not from the
    // register itself.
    integrationHits: scanIntegrationSites(files),
    hash: hashOf,
  };
}

function scanIntegrationSites(files) {
  const hits = [];
  const want = files.filter((f) =>
    /^Shared\/TalabatkApplication\/DomainEventsHandlers\/.*\.cs$/.test(f)
    || /Startup\.cs$/.test(f)
    || /^Shared\/SharedWeb\/Helpers\/AuthHelper\/ApiClientHandler\.cs$/.test(f));
  for (const f of want) {
    const txt = readIfExists(path.join(REPO, f));
    if (!txt) continue;
    for (const m of txt.matchAll(/ApiClientHandler\.([A-Za-z0-9_]+)\s*\(/g)) {
      hits.push({ kind: 'ApiClientHandler', symbol: m[1], file: f });
    }
    for (const m of txt.matchAll(/MapHub<\s*([A-Za-z0-9_]+)\s*>/g)) {
      hits.push({ kind: 'SignalR hub', symbol: m[1], file: f });
    }
    for (const m of txt.matchAll(/BackgroundJob\.(?:Schedule|Enqueue)<\s*([A-Za-z0-9_]+)\s*>/g)) {
      hits.push({ kind: 'Hangfire job', symbol: m[1], file: f });
    }
  }
  // dedupe by kind+symbol; one register row may legitimately cover many call sites
  const seen = new Set();
  return hits.filter((h) => {
    const k = `${h.kind}:${h.symbol}`;
    if (seen.has(k)) return false;
    seen.add(k); return true;
  });
}

// ---------------------------------------------------------------------------
// Wikilink resolution (Obsidian rules: basename match OR path match, anchors and aliases stripped).
// ---------------------------------------------------------------------------
function buildLinkTargets(model) {
  const byBase = new Set();
  const byPath = new Set();
  for (const n of model.notes) {
    byBase.add(n.base.replace(/\.md$/, ''));
    byPath.add(n.rel.replace(/^docs\/knowledge-graph\//, '').replace(/\.md$/, ''));
  }
  for (const f of model.gitSet) {
    if (f.endsWith('.html') && f.startsWith(`${KG_REL}/`)) {
      byBase.add(f.split('/').pop());
      byPath.add(f.replace(/^docs\/knowledge-graph\//, ''));
    }
  }
  return { byBase, byPath };
}

function resolveLink(target, targets, model, fromDir) {
  let t = target.trim();
  if (!t) return false;
  t = t.split('#')[0].trim();          // strip anchor
  if (!t) return true;                  // pure anchor, same-note link
  const clean = t.replace(/\.md$/, '');

  // A link WITH a path must resolve as that path. Accepting a basename match here would let a stale
  // relative path survive a folder move: `[[../Delivery/DeliveryZone]]` still "resolves" because a
  // note named DeliveryZone exists somewhere, while the path it actually names is gone. Obsidian
  // would show a dead link and the checker would report all clear — the precise shape of silent rot
  // this file exists to prevent.
  if (clean.includes('/')) {
    const vaultRel = path.posix.normalize(clean);                       // from the vault root
    if (targets.byPath.has(vaultRel)) return true;
    const fromVault = fromDir.replace(/^docs\/knowledge-graph\/?/, '');  // relative to this note
    const rel = path.posix.normalize(path.posix.join(fromVault, clean));
    if (targets.byPath.has(rel)) return true;
    // Links out of the vault (a service's CONTEXT.md, an ADR) resolve against git instead.
    const repoRel = path.posix.normalize(path.posix.join(fromDir, clean));
    if (model.gitSet.has(`${repoRel}.md`) || model.gitSet.has(repoRel)) return true;
    if (model.gitSet.has(`${clean}.md`) || model.gitSet.has(clean)) return true;
    return false;
  }
  return targets.byBase.has(clean);
}

function extractLinks(text) {
  const out = [];
  for (const m of text.matchAll(/\[\[([^\]]+)\]\]/g)) {
    // Table cells escape the alias pipe as `\|`; both forms mean the same thing.
    const inner = m[1].replace(/\\\|/g, '|');
    out.push(inner.split('|')[0]);
  }
  return out;
}

// ---------------------------------------------------------------------------
// THE CHECKS. Pure function of the model, so `--self-test` can drive them with synthetic input.
// ---------------------------------------------------------------------------
function runChecks(model, opts = {}) {
  const F = [];
  const add = (code, where, detail) => F.push({ code, where, detail });

  // ---- 1. entity denominator, checked in BOTH directions ----------------------------------
  const rowByEntity = new Map();
  const rowsByPath = new Map();
  for (const r of model.entityRows) {
    // One entity may legitimately span several files — `Order` is declared across `Order.cs` and
    // `Order.Partial.cs`. So a repeat is only a defect when the two rows CONTRADICT each other about
    // what the thing is; agreeing rows are just a partial class, and both files still need a row so
    // neither can go unclassified.
    const prev = rowByEntity.get(r.entity);
    if (prev && (prev.class !== r.class || prev.shape !== r.shape)) {
      add('ENTITY-DUPLICATE-ROW', `_entity-classes.tsv:${r.__line}`,
        `entity '${r.entity}' is classified as ${prev.class}/${prev.shape} on line ${prev.__line} and ${r.class}/${r.shape} here`);
    }
    if (!prev) rowByEntity.set(r.entity, r);
    if (!rowsByPath.has(r.source_path)) rowsByPath.set(r.source_path, []);
    rowsByPath.get(r.source_path).push(r);

    if (!DOCUMENTED_CLASSES.has(r.class) && !EXCLUDED_CLASSES.has(r.class)) {
      add('ENTITY-BAD-CLASS', `_entity-classes.tsv:${r.__line}`, `unknown class '${r.class}'`);
    }
    const shapeOk = r.shape === SHAPES.PAIR || r.shape === SHAPES.SINGLE || r.shape === SHAPES.NONE
      || r.shape.startsWith('covered-by:');
    if (!shapeOk) add('ENTITY-BAD-SHAPE', `_entity-classes.tsv:${r.__line}`, `unknown shape '${r.shape}'`);
    if (EXCLUDED_CLASSES.has(r.class) && r.shape !== SHAPES.NONE) {
      add('ENTITY-BAD-SHAPE', `_entity-classes.tsv:${r.__line}`,
        `class '${r.class}' is excluded from documentation, so shape must be 'none', not '${r.shape}'`);
    }
    if (DOCUMENTED_CLASSES.has(r.class) && r.shape === SHAPES.NONE) {
      add('ENTITY-BAD-SHAPE', `_entity-classes.tsv:${r.__line}`,
        `class '${r.class}' must be documented somewhere; shape 'none' is only for excluded classes`);
    }
    // An exclusion without a reason recreates the vagueness the depth ledger exists to remove.
    if (EXCLUDED_CLASSES.has(r.class) && !r.evidence) {
      add('ENTITY-EVIDENCE-MISSING', `_entity-classes.tsv:${r.__line}`,
        `'${r.entity}' is excluded as '${r.class}' with no stated reason`);
    }
    if (!model.gitSet.has(r.source_path)) {
      add('ENTITY-STALE-ROW', `_entity-classes.tsv:${r.__line}`,
        `source_path '${r.source_path}' is not tracked by git (renamed or deleted upstream?)`);
    }
  }
  for (const f of model.candidateEntities) {
    if (!rowsByPath.has(f)) {
      add('ENTITY-UNCLASSIFIED', f, 'candidate entity file with no row in _entity-classes.tsv');
    }
  }

  // ---- 2. feature denominator, both directions -------------------------------------------
  const mappedControllers = new Set();
  const featuresByKey = new Map(); // "Context/Feature" -> rows
  for (const r of model.featureRows) {
    mappedControllers.add(r.controller_path);
    if (!model.gitSet.has(r.controller_path)) {
      add('FEATURE-MAP-STALE', `_feature-map.tsv:${r.__line}`,
        `controller_path '${r.controller_path}' is not tracked by git`);
    }
    if (r.feature.startsWith('excluded:') || r.feature === 'non-controller') {
      if (!r.evidence) {
        add('FEATURE-EVIDENCE-MISSING', `_feature-map.tsv:${r.__line}`,
          `'${r.controller_path}' is excluded from the feature map with no stated reason`);
      }
      continue;
    }
    if (!CONTEXTS.includes(r.context)) {
      add('FEATURE-BAD-CONTEXT', `_feature-map.tsv:${r.__line}`,
        `'${r.context}' is not one of the CONTEXT-MAP.md contexts`);
      continue;
    }
    const key = `${r.context}/${r.feature}`;
    if (!featuresByKey.has(key)) featuresByKey.set(key, []);
    featuresByKey.get(key).push(r);
  }
  for (const f of model.candidateControllers) {
    if (!mappedControllers.has(f)) {
      add('CONTROLLER-UNMAPPED', f, 'entry point in git with no row in _feature-map.tsv');
    }
  }

  // ---- 3. structure: contexts, features, note placement ----------------------------------
  const noteByRel = new Map(model.notes.map((n) => [n.rel, n]));
  for (const c of CONTEXTS) {
    if (!noteByRel.has(`${KG_REL}/${c}/_context.md`)) {
      add('CONTEXT-MISSING', `${KG_REL}/${c}/_context.md`, `context '${c}' has no _context.md hub`);
    }
  }
  // Every mapped feature must exist on disk with all of its required files.
  for (const key of featuresByKey.keys()) {
    const dir = `${KG_REL}/${key}`;
    for (const req of FEATURE_REQUIRED) {
      if (!noteByRel.has(`${dir}/${req}`)) {
        add('FEATURE-INCOMPLETE', `${dir}/${req}`, `feature '${key}' is missing ${req}`);
      }
    }
    const hasGraph = [...model.gitSet].some((f) => f.startsWith(`${dir}/`) && f.endsWith('-context-graph.html'));
    if (!hasGraph) {
      add('FEATURE-INCOMPLETE', `${dir}/<feature>-context-graph.html`,
        `feature '${key}' has no context graph`);
    }
    // FEATURE-INCOMPLETE above counts FILES. That is existence, not substance: a _knowledge-graph.md
    // with no citation at all and a _scenarios.md with two rows both satisfied it, and 13 feature notes
    // were passing with zero traceability. Existence was the wrong denominator for the same reason a
    // `read` status was: it records that something was scheduled, not that it happened.
    const kgNote = noteByRel.get(`${dir}/_knowledge-graph.md`);
    if (kgNote) {
      const cites = countCitations(kgNote.body);
      if (cites < MIN_FEATURE_CITATIONS) {
        add('FEATURE-SHALLOW', `${dir}/_knowledge-graph.md`,
          `feature '${key}' has ${cites} file:line citation(s), under the floor of ${MIN_FEATURE_CITATIONS}`
          + ' — a controller map rather than a knowledge graph');
      }
    }
    const scNote = noteByRel.get(`${dir}/_scenarios.md`);
    if (scNote) {
      const rows = (scNote.body.match(/^\|\s*[A-Z]+\d+\s*\|/gm) || []).length;
      if (rows < MIN_SCENARIO_ROWS) {
        add('FEATURE-SHALLOW', `${dir}/_scenarios.md`,
          `feature '${key}' has ${rows} scenario row(s), under the floor of ${MIN_SCENARIO_ROWS}`);
      }
    }
  }
  // Placement. The skill mandates contexts -> features -> entities. A note sitting directly under a
  // context folder, or an entity folder at feature depth, is a level-skip: it has no owning feature,
  // so nothing links it into the graph and no _scenarios.md covers its behavior.
  for (const n of model.notes) {
    const parts = n.rel.split('/');
    if (parts.length < 4) continue;                        // docs/knowledge-graph/<x>
    const context = parts[2];
    if (context === '_system' || context === '_flows') continue;
    if (!CONTEXTS.includes(context)) {
      add('UNKNOWN-CONTEXT-FOLDER', n.rel, `'${context}' is not a CONTEXT-MAP.md context name`);
      continue;
    }
    const depth = parts.length - 3;                        // 1 = directly under context
    if (depth === 1 && n.base !== '_context.md') {
      add('NOTE-AT-CONTEXT-DEPTH', n.rel,
        'note sits directly under a context; it belongs inside a feature folder');
    }
    if (depth === 2) {
      // Whether a folder is a feature is decided by the feature map (derived from the code's entry
      // points), not by which files happen to be sitting in it. Judging by contents would call a
      // real-but-unfinished feature an entity folder and send someone to "fix" the wrong thing —
      // FEATURE-INCOMPLETE is the finding for a real feature missing its files.
      const isMappedFeature = featuresByKey.has(`${context}/${parts[3]}`);
      if (!isMappedFeature && !FEATURE_REQUIRED.includes(n.base)) {
        add('ENTITY-AT-FEATURE-DEPTH', n.rel,
          `'${parts[3]}' is not a feature in _feature-map.tsv, so these entity notes have no owning feature`);
      }
    }
  }
  // A feature folder on disk that no mapped controller points at: either dead or unmapped work.
  for (const n of model.notes) {
    if (n.base !== '_knowledge-graph.md' && n.base !== '_overview.md') continue;
    const parts = n.rel.split('/');
    if (parts.length !== 5) continue;
    const key = `${parts[2]}/${parts[3]}`;
    if (!featuresByKey.has(key)) {
      add('FEATURE-ORPHAN', n.rel, `feature '${key}' exists on disk but no controller maps to it`);
    }
  }

  // ---- 4. notes: frontmatter, citations, links, stubs -------------------------------------
  const targets = buildLinkTargets(model);

  // `domain-behaviour` is the one excluded class that admits its rows ARE rule-bearing — a strategy, a
  // profit calculator, a scheduled job. Its whole justification is that the rules live in a note
  // instead of in an entity page, so the evidence must NAME that note and the name must resolve.
  // Without this check the class is a laundering mechanism: 17 files could be marked "excluded, rules
  // documented over there" while pointing at a folder that does not exist. That is not hypothetical —
  // the first draft of these rows pointed at `Delivery/Driver Assignment & Dispatch/`, a path this
  // vault has never had, and every gate still reported green.
  for (const r of model.entityRows) {
    if (r.class !== 'domain-behaviour') continue;
    const links = extractLinks(r.evidence || '');
    if (!links.length) {
      add('ENTITY-BEHAVIOUR-UNDOCUMENTED', `_entity-classes.tsv:${r.__line}`,
        `'${r.entity}' is excluded as rule-bearing behaviour but its evidence names no note`);
      continue;
    }
    for (const link of links) {
      if (!resolveLink(link, targets, model, KG_REL)) {
        add('ENTITY-BEHAVIOUR-UNDOCUMENTED', `_entity-classes.tsv:${r.__line}`,
          `'${r.entity}' points its rules at '${link}', which does not resolve`);
      }
    }
  }

  const idSeen = new Map();
  const noteByEntity = new Map();
  let stubs = 0; let rulesExtracted = 0;
  const caveats = [];   // scoped "not traced in this pass" admissions: reported, never gated

  for (const n of model.notes) {
    if (FRONTMATTER_EXEMPT.has(n.rel)) continue;
    if (!n.fm) {
      add(n.fmError === 'no frontmatter block' ? 'FRONTMATTER-MISSING' : 'FRONTMATTER-INVALID',
        n.rel, n.fmError);
      continue;
    }
    const fm = n.fm;
    if (!fm.id) add('FRONTMATTER-INVALID', n.rel, 'no `id:` — a rename would break every reference to this note');
    else {
      if (idSeen.has(fm.id)) add('ID-DUPLICATE', n.rel, `id '${fm.id}' is also used by ${idSeen.get(fm.id)}`);
      idSeen.set(fm.id, n.rel);
    }
    if (!fm.note_type) add('FRONTMATTER-INVALID', n.rel, 'no `note_type:`');
    else if (!NOTE_TYPES.has(fm.note_type)) add('FRONTMATTER-INVALID', n.rel, `unknown note_type '${fm.note_type}'`);

    const isSystem = n.rel.startsWith(`${KG_REL}/_system/`);
    if (!isSystem && !fm.context) add('FRONTMATTER-INVALID', n.rel, 'no `context:`');
    if (fm.context && !CONTEXTS.includes(fm.context)) {
      add('FRONTMATTER-INVALID', n.rel, `context '${fm.context}' is not a CONTEXT-MAP.md name`);
    }

    // Citation staleness. This is the whole rebase story: the note names a file AND the version of
    // it that was read. When the file moves on, the note is stale by definition and says so.
    for (const s of fm.sources || []) {
      if (!s.path) { add('FRONTMATTER-INVALID', n.rel, 'a sources entry has no path'); continue; }
      if (!model.gitSet.has(s.path)) {
        add('CITATION-DEAD', n.rel, `cites '${s.path}', which git does not track`);
        continue;
      }
      if (!s.sha1 || s.sha1 === '?') {
        add('CITATION-UNSTAMPED', n.rel, `cites '${s.path}' with no sha1 — run --stamp`);
        continue;
      }
      const now = opts.hashOverride ? opts.hashOverride(s.path) : model.hash(s.path);
      if (now && now !== s.sha1) {
        add('CITATION-STALE', n.rel,
          `'${s.path}' changed since this note was verified (${s.sha1} -> ${now}); re-verify the cited lines, then --restamp`);
      }
    }

    for (const link of extractLinks(n.text)) {
      if (!resolveLink(link, targets, model, n.dir.replace(/^docs\/knowledge-graph/, `${KG_REL}`))) {
        add('WIKILINK-BROKEN', n.rel, `[[${link}]] resolves to nothing`);
      }
    }

    // A note that says in its own prose that it was not read. Earlier passes wrote these honestly —
    // "none of these were read in this pass", "light note", "controller-level map, not a rule-by-rule
    // audit" — and then the graph reported those features as complete, because no check read prose.
    // The admission is the most reliable gap signal in the vault and it was going unused.
    // `note_type: system` is exempt: the plan, the indexes and the playbook exist partly to DISCUSS
    // incompleteness, so matching that vocabulary there is matching the subject matter. `issue` is
    // exempt for the same reason and more strongly — an issue file's entire subject is a known gap, and
    // it quotes the register verbatim, so flagging its wording would flag it for doing its job.
    if (fm.note_type !== 'system' && fm.note_type !== 'issue') {
      const hard = n.body.match(SELF_FLAGGED_HARD);
      if (hard) {
        add('NOTE-SELF-FLAGGED', n.rel,
          `the note calls itself "${String(hard[0]).trim()}" — it declares its own incompleteness,`
          + ' so the graph must not count it as done');
      }
      for (const line of lines(beforeOpenQuestions(n.body))) {
        if (SELF_FLAGGED_SCOPED.test(line)) caveats.push({ rel: n.rel, text: line.trim().slice(0, 150) });
      }
    }

    // A technical or single note with no citation at all passes verify-citations.js by having nothing to
    // check. That is a vacuous pass, the same shape as the `covers:` list that was verified against text
    // including itself: the check agrees because there is nothing to disagree with.
    if ((fm.note_type === 'technical' || fm.note_type === 'single') && countCitations(n.body) < MIN_NOTE_CITATIONS) {
      add('NOTE-UNCITED', n.rel,
        'a technical note with no file:line citation — nothing in it is traceable, so verify-citations.js passes it vacuously');
    }

    // A rule matrix the frontmatter does not count is invisible to any consumer reading frontmatter
    // only, which is exactly how the future chat agent will read this graph.
    //
    // Scoped to technical/single notes on purpose. The business half of a pair carries the same
    // "Business Rules" heading but narrates rather than enumerates — that division is the skill's, and
    // demanding a count there would be asking prose to be a table. 31 of the 47 this check first
    // reported were business notes, and counting them would have made the number meaningless.
    if ((fm.note_type === 'technical' || fm.note_type === 'single')
      && /##\s*(Rule\s*\/\s*Decision Matrix|Business Rules)/i.test(n.body)
      && !Number.isFinite(Number(fm.rule_count))) {
      add('RULECOUNT-MISSING', n.rel,
        'has a rule matrix but declares no rule_count — the rules are unreachable for a frontmatter-only reader');
    }

    if (fm.entity) {
      if (!noteByEntity.has(fm.entity)) noteByEntity.set(fm.entity, []);
      noteByEntity.get(fm.entity).push(n);
      const row = rowByEntity.get(fm.entity);
      if (!row) {
        add('NOTE-ORPHAN', n.rel, `declares entity '${fm.entity}', which has no row in _entity-classes.tsv`);
      } else if (OWN_NOTE.has(row.shape.split(':')[0]) && (fm.note_type === 'technical' || fm.note_type === 'single')) {
        // Widened deliberately. This check was originally scoped to RULE_BEARING classes
        // (aggregate-root, legacy-poco-root), which exempted 23 of the 38 entities that have a note of
        // their own — every `child` and `lookup` one. An entity important enough to be given its own
        // note is important enough to have its rules extracted, whatever its class: the shape
        // (pair/single) is the graph's own statement that this entity warrants a page, so the shape,
        // not the class, is the right trigger. Six notes passed under the old scope with neither a rule
        // matrix nor a rule_count.
        const count = Number(fm.rule_count);
        const hasMatrix = /##\s*(Rule\s*\/\s*Decision Matrix|Business Rules)/i.test(n.text);
        if (!Number.isFinite(count) || count < 1 || !hasMatrix) {
          stubs++;
          add('NOTE-STUB', n.rel,
            `'${fm.entity}' has a note of its own (shape '${row.shape}', class ${row.class}) but this note has ${fm.rule_count || 'no'} rule_count`
            + `${hasMatrix ? '' : ' and no rule matrix'} — a stub, not an answer`);
        } else rulesExtracted++;
      }
    }
    for (const covered of fm.covers || []) {
      if (!rowByEntity.has(covered)) {
        add('COVERS-UNKNOWN', n.rel, `covers '${covered}', which has no row in _entity-classes.tsv`);
      }
    }
  }

  // Shape expectations: derived from the tsv (code side), observed on disk (note side).
  // Iterate distinct entities, not rows, so a partial class spanning two files is not reported twice.
  for (const r of rowByEntity.values()) {
    if (r.shape === SHAPES.NONE) continue;
    const notes = noteByEntity.get(r.entity) || [];
    if (r.shape === SHAPES.PAIR) {
      const hasB = notes.some((n) => n.fm && n.fm.note_type === 'business');
      const hasT = notes.some((n) => n.fm && n.fm.note_type === 'technical');
      if (!hasB) add('NOTE-ABSENT', `_entity-classes.tsv:${r.__line}`, `'${r.entity}' has no .business note`);
      if (!hasT) add('NOTE-ABSENT', `_entity-classes.tsv:${r.__line}`, `'${r.entity}' has no .technical note`);
    } else if (r.shape === SHAPES.SINGLE) {
      if (!notes.length) add('NOTE-ABSENT', `_entity-classes.tsv:${r.__line}`, `'${r.entity}' has no note`);
    } else if (r.shape.startsWith('covered-by:')) {
      // A canonical note may be a single entity's note (`entity:`) or a grouped note that documents
      // a family of small entities together (`group:`). The vault already uses the second shape
      // (`Area-and-Country.md`, `Mart-and-Reference-Entities.md`) and the skill allows it for
      // child/master/lookup types — so the check accepts both, and insists the host note names the
      // covered entity explicitly. Folding is fine; folding silently is not.
      const host = r.shape.slice('covered-by:'.length).trim();
      const hostNotes = model.notes.filter((n) => n.fm && (n.fm.entity === host || n.fm.group === host));
      const covering = hostNotes.filter((n) => (n.fm.covers || []).includes(r.entity));
      if (!hostNotes.length) {
        add('COVERS-MISMATCH', `_entity-classes.tsv:${r.__line}`,
          `'${r.entity}' is covered-by '${host}', but no note declares entity '${host}'`);
      } else if (!covering.length) {
        add('COVERS-MISMATCH', `_entity-classes.tsv:${r.__line}`,
          `'${r.entity}' is covered-by '${host}', but that note's covers: list does not mention it`);
      } else if (!covering.some((n) => (n.body || '').includes(r.entity))) {
        // Without this, `covers:` degrades into a rubber stamp: a frontmatter list long enough to
        // satisfy the denominator while the note body says nothing about the entity. Folding a small
        // entity into a canonical note is per-spec; folding it into a name-drop is not.
        add('COVERS-UNMENTIONED', covering[0].rel,
          `claims to cover '${r.entity}' but never mentions it in the body`);
      }
    }
  }

  // ---- 5. registers ----------------------------------------------------------------------
  const registerRows = [];
  for (const [name, txt] of [['_conflicts.md', model.conflictsText], ['_idor-instances.md', model.idorText]]) {
    const rows = lines(txt);
    // The header's cell count is the contract every data row owes. Split on UNESCAPED pipes only:
    // `[[Target\|Label]]` is one cell's content, not a column boundary.
    let want = 0; let headerLine = 0;
    for (let i = 0; i < rows.length; i++) {
      if (/^\|\s*#\s*\|/.test(rows[i])) { want = registerCells(rows[i]); headerLine = i + 1; break; }
    }
    for (let i = 0; i < rows.length; i++) {
      const m = rows[i].match(/^\|\s*(\d+)\s*\|(.*)$/);
      if (!m) continue;
      registerRows.push({ file: name, line: i + 1, num: Number(m[1]), rest: m[2] });
      // A stray `|` in prose or code (`||`, `Weekly|Monthly|Yearly`) silently becomes a column
      // boundary, shifting every cell after it one place right. Two rows had rendered that way since
      // they were written, and seven more were added in this round before anything noticed — because
      // nothing checked. Cheap to check, invisible otherwise.
      if (want) {
        const got = registerCells(rows[i]);
        if (got !== want) {
          add('REGISTER-ROW-MALFORMED', `${name}:${i + 1}`,
            `finding #${m[1]} has ${got} cells, header (line ${headerLine}) has ${want} — an unescaped `
            + `'|' in prose or a wikilink shifts every later column; write it as '\\|'`);
        }
      }
    }
  }
  for (const r of registerRows) {
    const links = extractLinks(r.rest);
    const resolved = links.filter((l) => resolveLink(l, targets, model, `${KG_REL}/_system`));
    if (!resolved.length) {
      add('REGISTER-UNLINKED', `${r.file}:${r.line}`,
        `finding #${r.num} links to no note — unreachable from the graph`);
    }
  }

  // ---- 6. integrations: register vs code, and register vs notes ---------------------------
  for (const h of model.integrationHits) {
    if (!model.integrationsText.includes(h.symbol)) {
      add('INTEGRATION-UNREGISTERED', h.file,
        `${h.kind} '${h.symbol}' is wired in code but named nowhere in _integrations.md`);
    }
  }
  {
    const rows = lines(model.integrationsText);
    const allNotes = model.notes.map((n) => n.text).join('\n');
    for (let i = 0; i < rows.length; i++) {
      const m = rows[i].match(/^\|\s*(\d+)\s*\|(.*)$/);
      if (!m) continue;
      // The register row names a mechanism symbol; some note must trace it, otherwise the
      // integration is recorded but its behavior is documented nowhere.
      const syms = [...m[2].matchAll(/`([A-Za-z0-9_]+)(?:\.cs)?`/g)].map((x) => x[1]);
      if (!syms.length) continue;
      if (!syms.some((s) => allNotes.includes(s))) {
        add('INTEGRATION-UNTRACED', `_integrations.md:${i + 1}`,
          `integration #${m[1]} names ${syms.slice(0, 3).map((s) => `'${s}'`).join(', ')} but no note mentions any of them`);
      }
    }
  }

  return { findings: F, stats: { stubs, rulesExtracted, registerRows: registerRows.length, caveats } };
}

// ---------------------------------------------------------------------------
// register sequence check (--register-check)
// ---------------------------------------------------------------------------
function registerCheck() {
  const txt = readIfExists(CONFLICTS);
  if (txt === null) { console.log('REGISTER: _conflicts.md missing'); return 1; }
  const nums = [];
  for (const line of lines(txt)) {
    const m = line.match(/^\|\s*(\d+)\s*\|/);
    if (m) nums.push(Number(m[1]));
  }
  const seen = new Set(); const dups = [];
  for (const n of nums) { if (seen.has(n)) dups.push(n); seen.add(n); }
  const max = nums.length ? Math.max(...nums) : 0;
  const gaps = [];
  for (let i = 1; i <= max; i++) if (!seen.has(i)) gaps.push(i);
  console.log(`register rows   : ${nums.length}`);
  console.log(`highest number  : ${max}`);
  console.log(`duplicates      : ${dups.length}${dups.length ? ' -> ' + dups.slice(0, 20).join(', ') : ''}`);
  console.log(`gaps            : ${gaps.length}${gaps.length ? ' -> ' + gaps.slice(0, 20).join(', ') : ''}`);
  if (!dups.length && !gaps.length) {
    console.log('REGISTER OK - sequential, no gaps, no duplicates.');
    return 0;
  }
  return 1;
}

// ---------------------------------------------------------------------------
// --generate: derived indexes. These are conveniences built FROM the notes; no check may read them,
// or the checker would be grading its own homework.
// ---------------------------------------------------------------------------
function generate(model) {
  const src = [];
  const ids = [];
  for (const n of model.notes) {
    if (!n.fm) continue;
    if (n.fm.id) ids.push([n.fm.id, n.rel].join('\t'));
    for (const s of n.fm.sources || []) {
      src.push([s.path, s.sha1 || '?', n.rel].join('\t'));
    }
  }
  src.sort();
  ids.sort();
  fs.writeFileSync(SOURCE_INDEX,
    '# source_path\tsha1_12\tnote_path\n'
    + '# Reverse index: "file X changed - which notes are stale?" is a lookup, not a grep over 136 notes.\n'
    + '# Machine-generated by verify-notes.js --generate. Do not hand-edit.\n'
    + src.join('\n') + '\n', 'utf8');
  fs.writeFileSync(ID_INDEX,
    '# id\tnote_path\n'
    + '# Stable id -> current path. A rename changes the path, never the id, so links and any future\n'
    + '# agent resolve through this file instead of guessing at filenames.\n'
    + '# Machine-generated by verify-notes.js --generate. Do not hand-edit.\n'
    + ids.join('\n') + '\n', 'utf8');
  console.log(`generated: ${src.length} citation rows -> _source-index.tsv`);
  console.log(`generated: ${ids.length} ids           -> _id-index.tsv`);
}

// ---------------------------------------------------------------------------
// --stamp / --restamp. Stamping fills in a MISSING sha1 only. It deliberately refuses to overwrite a
// mismatch, because that would let a stale citation be "fixed" without anyone re-reading the code -
// exactly the silent staleness this column exists to expose. Clearing a real mismatch is an explicit,
// per-note act (--restamp), performed after the lines were re-verified.
// ---------------------------------------------------------------------------
function stamp(model, restampRel) {
  let changed = 0;
  for (const n of model.notes) {
    if (!n.fm || !(n.fm.sources || []).length) continue;
    if (restampRel && n.rel !== restampRel) continue;
    let text = n.text;
    let touched = false;
    for (const s of n.fm.sources) {
      if (!s.path || !model.gitSet.has(s.path)) continue;
      const now = model.hash(s.path);
      if (!now) continue;
      if (s.sha1 && s.sha1 !== '?' && !restampRel) continue;      // never silently re-stamp a mismatch
      if (s.sha1 === now) continue;
      const esc = s.path.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      const re = new RegExp(`(-\\s*path:\\s*${esc}\\s*\\r?\\n\\s*sha1:\\s*)([^\\r\\n]*)`);
      if (re.test(text)) { text = text.replace(re, `$1${now}`); touched = true; }
      else {
        const re2 = new RegExp(`(-\\s*path:\\s*${esc})(\\s*\\r?\\n)`);
        if (re2.test(text)) { text = text.replace(re2, `$1$2    sha1: ${now}$2`); touched = true; }
      }
    }
    if (touched) { fs.writeFileSync(path.join(REPO, n.rel), text, 'utf8'); changed++; }
  }
  console.log(`${restampRel ? 'restamped' : 'stamped'}: ${changed} note(s)`);
}

// ---------------------------------------------------------------------------
// Reporting
// ---------------------------------------------------------------------------
function report(model, result) {
  const { findings, stats } = result;
  const byCode = {};
  for (const f of findings) byCode[f.code] = (byCode[f.code] || 0) + 1;

  const documented = model.entityRows.filter((r) => DOCUMENTED_CLASSES.has(r.class));
  const excluded = model.entityRows.filter((r) => EXCLUDED_CLASSES.has(r.class));
  const own = documented.filter((r) => r.shape === SHAPES.PAIR || r.shape === SHAPES.SINGLE);
  const folded = documented.filter((r) => r.shape.startsWith('covered-by:'));
  const featureKeys = new Set(model.featureRows
    .filter((r) => !r.feature.startsWith('excluded:') && r.feature !== 'non-controller')
    .map((r) => `${r.context}/${r.feature}`));
  const incomplete = new Set(findings.filter((f) => f.code === 'FEATURE-INCOMPLETE')
    .map((f) => f.where.split('/').slice(2, 4).join('/')));

  console.log(`commit           : ${(() => { try { return execSync('git rev-parse HEAD', { cwd: REPO, encoding: 'utf8' }).trim(); } catch { return 'unknown'; } })()}`);
  console.log('');
  console.log(`entities: candidates in code            : ${model.candidateEntities.length}`);
  console.log(`entities: classified rows               : ${model.entityRows.length}`);
  console.log(`entities: to document                   : ${documented.length}  (own note ${own.length} · folded into a canonical note ${folded.length})`);
  console.log(`entities: excluded, with stated reason   : ${excluded.length}`);
  console.log('');
  console.log(`depth:    rules-extracted notes          : ${stats.rulesExtracted}`);
  console.log(`depth:    stub notes                     : ${stats.stubs}${stats.stubs ? '  <- these FAIL' : ''}`);
  console.log(`depth:    entities with no note at all    : ${byCode['NOTE-ABSENT'] || 0}${byCode['NOTE-ABSENT'] ? '  <- these FAIL' : ''}`);
  console.log('');
  console.log(`features: entry points in code           : ${model.candidateControllers.length}`);
  console.log(`features: mapped                         : ${model.featureRows.length}`);
  console.log(`features: total                          : ${featureKeys.size}  (complete ${featureKeys.size - incomplete.size} · incomplete ${incomplete.size})`);
  console.log('');
  console.log(`notes:    in vault                       : ${model.notes.length}`);
  console.log(`notes:    frontmatter problems           : ${(byCode['FRONTMATTER-MISSING'] || 0) + (byCode['FRONTMATTER-INVALID'] || 0)}`);
  console.log(`notes:    stale citations                : ${byCode['CITATION-STALE'] || 0}`);
  console.log(`notes:    unstamped citations            : ${byCode['CITATION-UNSTAMPED'] || 0}`);
  console.log(`notes:    broken wikilinks               : ${byCode['WIKILINK-BROKEN'] || 0}`);
  console.log(`notes:    scoped caveats (reported, not gated) : ${stats.caveats.length}`
    + `${stats.caveats.length ? '  <- list them with --caveats' : ''}`);
  console.log('');

  if (process.argv.includes('--caveats')) {
    console.log('Scoped caveats — a named field, method or sub-flow a note says it did not follow.');
    console.log('Not gated: the caveat belongs next to the claim it qualifies, which is where it is useful.');
    console.log('Listed so none is lost, which was the actual defect.');
    console.log('');
    for (const c of stats.caveats) {
      console.log(`  ${c.rel.replace(/^docs\/knowledge-graph\//, '')}`);
      console.log(`      ${c.text}`);
    }
    console.log('');
  }
  console.log(`register: rows                           : ${stats.registerRows}`);
  console.log(`register: rows linking no note           : ${byCode['REGISTER-UNLINKED'] || 0}`);
  console.log(`flows:    integrations wired in code     : ${model.integrationHits.length}`);
  console.log(`flows:    unregistered / untraced        : ${byCode['INTEGRATION-UNREGISTERED'] || 0} / ${byCode['INTEGRATION-UNTRACED'] || 0}`);
  console.log('');

  if (!findings.length) {
    console.log('NOTES OK - every entity in the code has a note, every entry point has a feature,');
    console.log('           every citation matches the code it names, every link resolves.');
    return 0;
  }
  console.log(`KNOWLEDGE GAPS - ${findings.length} problem(s) in ${Object.keys(byCode).length} class(es):`);
  for (const code of Object.keys(byCode).sort((a, b) => byCode[b] - byCode[a])) {
    console.log(`  ${String(code).padEnd(26)} ${byCode[code]}`);
  }
  console.log('');
  const limit = process.argv.includes('--all') ? findings.length : 80;
  for (const f of findings.slice(0, limit)) {
    console.log(`  ${f.code}  ${f.where}`);
    console.log(`      ${f.detail}`);
  }
  if (findings.length > limit) console.log(`  ... and ${findings.length - limit} more (pass --all to list every one)`);
  return 1;
}

// ---------------------------------------------------------------------------
// --self-test. A checker that cannot see a gap is worse than no checker: it turns an unknown into a
// false assurance. This project has been there twice. So before any "all clear" is believed, plant
// one synthetic instance of each failure class in a fabricated model and assert it is reported.
// The expectation here is hand-written, and the observation is the checker's own output - the two
// come from different places, which is the whole point.
// ---------------------------------------------------------------------------
function selfTest() {
  // `body` mirrors what buildModel derives (text minus frontmatter), so a check that reads the body
  // is exercised the same way here as in a real run.
  const withBody = (n) => Object.assign(n, { body: n.body !== undefined ? n.body : String(n.text || '').replace(/^---[\s\S]*?\n---\n?/, '') });
  const baseNote = (over = {}) => withBody(Object.assign({
    rel: `${KG_REL}/Customer Ordering/Cart & Checkout/Widget.technical.md`,
    base: 'Widget.technical.md',
    dir: `${KG_REL}/Customer Ordering/Cart & Checkout`,
    text: '---\nid: x\n---\n## Business Rules\n',
    fm: { id: 'x', note_type: 'technical', context: 'Customer Ordering', sources: [] },
    fmError: null,
  }, over));

  const model = () => ({
    gitSet: new Set(['Shared/TalabatkLogic/TalabatkModels/Widget.cs',
      'TalabatkAPIs/Controllers/Cart/CartController.cs']),
    candidateEntities: ['Shared/TalabatkLogic/TalabatkModels/Widget.cs'],
    candidateControllers: ['TalabatkAPIs/Controllers/Cart/CartController.cs'],
    entityRows: [{ __line: 1, entity: 'Widget', source_path: 'Shared/TalabatkLogic/TalabatkModels/Widget.cs', class: 'legacy-poco-root', shape: 'single', context: 'Customer Ordering', feature: 'Cart & Checkout', evidence: 'x' }],
    featureRows: [{ __line: 1, controller_path: 'TalabatkAPIs/Controllers/Cart/CartController.cs', context: 'Customer Ordering', feature: 'Cart & Checkout', evidence: 'cart' }],
    notes: [],
    dirs: new Set(),
    integrationsText: '', conflictsText: '', idorText: '', integrationHits: [],
    hash: () => 'aaaaaaaaaaaa',
  });

  const cases = [];
  const T = (code, mutate) => cases.push({ code, mutate });

  T('ENTITY-UNCLASSIFIED', (m) => { m.entityRows = []; });
  T('ENTITY-STALE-ROW', (m) => { m.entityRows[0].source_path = 'Shared/TalabatkLogic/TalabatkModels/Gone.cs'; m.candidateEntities = []; });
  T('ENTITY-BAD-CLASS', (m) => { m.entityRows[0].class = 'wat'; });
  T('ENTITY-BAD-SHAPE', (m) => { m.entityRows[0].shape = 'sideways'; });
  T('ENTITY-EVIDENCE-MISSING', (m) => { m.entityRows[0].class = 'projection'; m.entityRows[0].shape = 'none'; m.entityRows[0].evidence = ''; });
  T('ENTITY-DUPLICATE-ROW', (m) => { m.entityRows.push(Object.assign({}, m.entityRows[0], { __line: 2, class: 'lookup' })); });
  // Both halves of the behaviour rule: evidence that names no note, and evidence naming one that
  // does not exist. The second is the failure that actually happened.
  T('ENTITY-BEHAVIOUR-UNDOCUMENTED', (m) => {
    m.entityRows[0].class = 'domain-behaviour'; m.entityRows[0].shape = 'none';
    m.entityRows[0].evidence = 'a strategy, rules live elsewhere';
  });
  T('ENTITY-BEHAVIOUR-UNDOCUMENTED', (m) => {
    m.entityRows[0].class = 'domain-behaviour'; m.entityRows[0].shape = 'none';
    m.entityRows[0].evidence = 'rules documented in [[Delivery/No Such Feature/_knowledge-graph]]';
  });
  T('NOTE-ABSENT', () => { /* base model has a row and no notes */ });
  T('NOTE-ORPHAN', (m) => {
    m.entityRows = [];
    m.candidateEntities = [];
    m.notes = [baseNote({ fm: { id: 'x', note_type: 'technical', context: 'Customer Ordering', entity: 'Ghost', sources: [] } })];
  });
  T('COVERS-MISMATCH', (m) => { m.entityRows[0].shape = 'covered-by:Nobody'; });
  T('CONTROLLER-UNMAPPED', (m) => { m.featureRows = []; });
  T('FEATURE-MAP-STALE', (m) => { m.featureRows[0].controller_path = 'TalabatkAPIs/Controllers/Gone.cs'; m.candidateControllers = []; });
  T('FEATURE-EVIDENCE-MISSING', (m) => { m.featureRows[0].feature = 'excluded:whatever'; m.featureRows[0].evidence = ''; });
  T('FEATURE-BAD-CONTEXT', (m) => { m.featureRows[0].context = 'Nowhere'; });
  T('FEATURE-INCOMPLETE', () => { /* mapped feature, no files on disk */ });
  T('CONTEXT-MISSING', () => { /* no _context.md anywhere */ });
  T('NOTE-AT-CONTEXT-DEPTH', (m) => {
    m.notes = [baseNote({ rel: `${KG_REL}/Customer Ordering/Loose.md`, base: 'Loose.md', dir: `${KG_REL}/Customer Ordering` })];
  });
  T('ENTITY-AT-FEATURE-DEPTH', (m) => {
    m.notes = [baseNote({ rel: `${KG_REL}/Admin/City/City.technical.md`, base: 'City.technical.md', dir: `${KG_REL}/Admin/City`, fm: { id: 'y', note_type: 'technical', context: 'Admin', sources: [] } })];
  });
  T('FEATURE-ORPHAN', (m) => {
    m.notes = [baseNote({ rel: `${KG_REL}/Admin/Ghost Feature/_knowledge-graph.md`, base: '_knowledge-graph.md', dir: `${KG_REL}/Admin/Ghost Feature`, fm: { id: 'z', note_type: 'knowledge-graph', context: 'Admin', sources: [] } })];
  });
  T('FRONTMATTER-MISSING', (m) => { m.notes = [baseNote({ fm: null, fmError: 'no frontmatter block' })]; });
  T('FRONTMATTER-INVALID', (m) => { m.notes = [baseNote({ fm: { note_type: 'technical', context: 'Customer Ordering', sources: [] } })]; });
  T('ID-DUPLICATE', (m) => {
    m.notes = [baseNote(), baseNote({ rel: `${KG_REL}/Customer Ordering/Cart & Checkout/Other.md`, base: 'Other.md' })];
  });
  T('CITATION-DEAD', (m) => {
    m.notes = [baseNote({ fm: { id: 'x', note_type: 'technical', context: 'Customer Ordering', sources: [{ path: 'Nope.cs', sha1: 'aaaaaaaaaaaa' }] } })];
  });
  T('CITATION-UNSTAMPED', (m) => {
    m.notes = [baseNote({ fm: { id: 'x', note_type: 'technical', context: 'Customer Ordering', sources: [{ path: 'Shared/TalabatkLogic/TalabatkModels/Widget.cs', sha1: '?' }] } })];
  });
  T('CITATION-STALE', (m) => {
    m.notes = [baseNote({ fm: { id: 'x', note_type: 'technical', context: 'Customer Ordering', sources: [{ path: 'Shared/TalabatkLogic/TalabatkModels/Widget.cs', sha1: 'bbbbbbbbbbbb' }] } })];
  });
  T('WIKILINK-BROKEN', (m) => {
    m.notes = [baseNote({ text: '---\nid: x\n---\nsee [[No Such Note]]\n' })];
  });
  T('NOTE-STUB', (m) => {
    m.notes = [baseNote({
      text: '---\nid: x\n---\nno rules here\n',
      fm: { id: 'x', note_type: 'technical', context: 'Customer Ordering', entity: 'Widget', rule_count: '0', sources: [] },
    })];
  });
  // A `child`-class entity with a note of its own: exempt under the old RULE_BEARING scope, caught now.
  T('NOTE-STUB', (m) => {
    m.entityRows[0].class = 'child';
    m.notes = [baseNote({
      text: '---\nid: x\n---\nno rules here\n',
      fm: { id: 'x', note_type: 'technical', context: 'Customer Ordering', entity: 'Widget', sources: [] },
    })];
  });
  T('FEATURE-SHALLOW', (m) => {
    m.notes = [
      baseNote({ rel: `${KG_REL}/Customer Ordering/Cart & Checkout/_knowledge-graph.md`, base: '_knowledge-graph.md', text: '---\nid: a\n---\nno citations at all\n', fm: { id: 'a', note_type: 'knowledge-graph', context: 'Customer Ordering', sources: [] } }),
      baseNote({ rel: `${KG_REL}/Customer Ordering/Cart & Checkout/_overview.md`, base: '_overview.md', text: '---\nid: b\n---\nx\n', fm: { id: 'b', note_type: 'overview', context: 'Customer Ordering', sources: [] } }),
      baseNote({ rel: `${KG_REL}/Customer Ordering/Cart & Checkout/_scenarios.md`, base: '_scenarios.md', text: '---\nid: c\n---\n| H1 | a | b | c |\n', fm: { id: 'c', note_type: 'scenarios', context: 'Customer Ordering', sources: [] } }),
    ];
    m.gitSet.add(`${KG_REL}/Customer Ordering/Cart & Checkout/cart-context-graph.html`);
  });
  T('NOTE-SELF-FLAGGED', (m) => {
    m.notes = [baseNote({ text: '---\nid: x\n---\n## Business Rules\nThis is a light note — none of these were read in this pass.\n' })];
  });
  T('NOTE-UNCITED', (m) => {
    m.notes = [baseNote({ text: '---\nid: x\n---\n## Business Rules\nprose with no file line reference\n' })];
  });
  T('RULECOUNT-MISSING', (m) => {
    m.notes = [baseNote({
      text: '---\nid: x\n---\n## Business Rules\nsee `Foo.cs:12`\n',
      fm: { id: 'x', note_type: 'technical', context: 'Customer Ordering', sources: [] },
    })];
  });
  T('COVERS-UNMENTIONED', (m) => {
    m.entityRows[0].shape = 'covered-by:Host';
    m.notes = [baseNote({
      text: '---\nid: h\n---\nthis note says nothing about the folded entity\n',
      fm: { id: 'h', note_type: 'single', context: 'Customer Ordering', group: 'Host', covers: ['Widget'], sources: [] },
    })];
  });
  T('COVERS-UNKNOWN', (m) => {
    m.notes = [baseNote({ fm: { id: 'x', note_type: 'technical', context: 'Customer Ordering', covers: ['Phantom'], sources: [] } })];
  });
  T('REGISTER-UNLINKED', (m) => { m.conflictsText = '| 1 | Something | no link here |\n'; });
  // An unescaped pipe in the row body: 5 cells against the header's 4.
  T('REGISTER-ROW-MALFORMED', (m) => {
    m.conflictsText = '| # | Entity | What | Status |\n|---|---|---|---|\n'
      + '| 1 | [[Customer Ordering/_context\\|ctx]] | uses `a || b` unescaped | ok |\n';
  });
  T('INTEGRATION-UNREGISTERED', (m) => {
    m.integrationHits = [{ kind: 'SignalR hub', symbol: 'GhostHub', file: 'AdminUi/Startup.cs' }];
  });
  T('INTEGRATION-UNTRACED', (m) => { m.integrationsText = '| 1 | A | B | via | `GhostHandler.cs` | x |\n'; });
  T('UNKNOWN-CONTEXT-FOLDER', (m) => {
    m.notes = [baseNote({ rel: `${KG_REL}/Nonsense/x/y.md`, base: 'y.md', dir: `${KG_REL}/Nonsense/x` })];
  });

  let pass = 0; const fails = [];
  for (const c of cases) {
    const m = model();
    c.mutate(m);
    const { findings } = runChecks(m);
    if (findings.some((f) => f.code === c.code)) pass++;
    else fails.push({ code: c.code, got: [...new Set(findings.map((f) => f.code))].join(', ') || '(nothing)' });
  }
  console.log(`self-test: ${pass}/${cases.length} failure classes are detectable`);
  for (const f of fails) console.log(`  BLIND SPOT  ${f.code}  -> checker reported: ${f.got}`);
  if (fails.length) {
    console.log('');
    console.log('A class the checker cannot see is a class it will certify as clean. Fix before trusting a pass.');
    return 1;
  }
  console.log('SELF-TEST OK - every failure class this file claims to check is provably detectable.');
  return 0;
}

// ---------------------------------------------------------------------------
const args = process.argv.slice(2);
if (args.includes('--self-test')) {
  process.exit(selfTest());
} else if (args.includes('--register-check')) {
  process.exit(registerCheck());
} else if (args.includes('--generate')) {
  generate(buildModel());
  process.exit(0);
} else if (args.includes('--stamp')) {
  stamp(buildModel(), null);
  process.exit(0);
} else if (args.includes('--restamp')) {
  const rel = args[args.indexOf('--restamp') + 1];
  if (!rel) { console.log('usage: --restamp <path relative to repo root>'); process.exit(2); }
  stamp(buildModel(), rel.replace(/\\/g, '/'));
  process.exit(0);
} else {
  const model = buildModel();
  process.exit(report(model, runChecks(model)));
}
