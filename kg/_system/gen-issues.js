/**
 * gen-issues.js — one issue file per register finding, so each can carry its own fix status.
 *
 *   node docs/knowledge-graph/_system/gen-issues.js            # dry run, reports what would change
 *   node docs/knowledge-graph/_system/gen-issues.js --write
 *
 * `_conflicts.md` stays the single source of truth for *what was found*. These files add the one thing
 * a table cannot carry well: per-issue state that a person edits as work happens, plus room for a fix
 * decision written by whoever takes it on.
 *
 * That split is the whole design, and it is why regeneration is safe:
 *
 *   GENERATED, overwritten every run  — title, severity, where, what-it-is, evidence, related links.
 *                                       All of it derived from the register row.
 *   HAND-OWNED, never overwritten     — `status:` in the frontmatter, and everything after the
 *                                       END-GENERATED marker (the fix decision, working notes).
 *
 * Two sources of truth for the same fact is the failure this vault keeps finding elsewhere (#384,
 * #639), so nothing here duplicates the register's findings — the body quotes the row and links back to
 * it by number. Re-run after the register changes and the descriptions follow; your status and your
 * notes survive.
 *
 * A fix suggestion is never invented. Each issue gets one of three, and says which:
 *   - authored     the fix is known and shipped, or known and specified
 *   - starting point  the register names a sibling that does it right; that hint is repeated, not dressed
 *                     up as a plan
 *   - needs a decision  nothing in the record implies a fix. Saying so is more useful than filler.
 */
'use strict';

const fs = require('fs');
const path = require('path');

const SYSTEM_DIR = __dirname;
const REPO = path.resolve(SYSTEM_DIR, '..', '..', '..');
const CONFLICTS = path.join(SYSTEM_DIR, '_conflicts.md');
const ISSUES_DIR = path.join(SYSTEM_DIR, '_issues');
const WRITE = process.argv.includes('--write');

const BEGIN = '<!-- BEGIN generated: derived from _conflicts.md by gen-issues.js — edits here are lost -->';
const END = '<!-- END generated — everything below is yours to edit and is never overwritten -->';

const lines = (t) => String(t).replace(/\r\n/g, '\n').split('\n');
const cells = (s) => s.split(/(?<!\\)\|/).map((x) => x.trim());

// ---------------------------------------------------------------------------------------------
// read the register
// ---------------------------------------------------------------------------------------------
const rows = [];
for (const l of lines(fs.readFileSync(CONFLICTS, 'utf8'))) {
  if (!/^\|\s*\d+\s*\|/.test(l)) continue;
  const c = cells(l);
  rows.push({ id: +c[1], entity: c[2], sides: c[3], what: c[4], backend: c[5], other: c[6], feature: c[7], status: c[8] });
}
if (!rows.length) { console.error('no rows parsed from _conflicts.md'); process.exit(1); }

// ---------------------------------------------------------------------------------------------
// derive the fields the issue file needs
// ---------------------------------------------------------------------------------------------

/** Strip wikilinks, bold, code ticks and italics down to readable words. */
function plain(s) {
  return String(s || '')
    .replace(/\[\[([^\]|\\]*)(?:\\?\|([^\]]*))?\]\]/g, (_, target, label) => (label || target).split('/').pop())
    .replace(/\*\*/g, '').replace(/`/g, '').replace(/\*/g, '')
    .replace(/\s+/g, ' ')
    .trim();
}

/**
 * Severity from the row's own words, not from a guess. The register states it — "critical",
 * "high severity", "moderate" — and the leading status marker carries the confidence.
 */
function severity(r) {
  const t = `${r.sides} ${r.status} ${r.what}`.toLowerCase();
  if (/\bcritical\b/.test(t)) return 'critical';
  if (/high[- ]severity|high severity/.test(t)) return 'high';
  if (/\bmoderate\b/.test(t)) return 'moderate';
  if (/^⚠️/.test(r.status)) return 'observation';
  if (/^🟡/.test(r.status)) return 'low';
  if (/idor|privilege escalation|account takeover|authentication bypass|unauthenticated/.test(t)) return 'high';
  return 'medium';
}

/** open | fixed | tracked — the *starting* value only; a person owns it after that. */
function initialStatus(r) {
  if (/^✅/.test(r.status)) return 'fixed';
  if (/^⚠️/.test(r.status)) return 'tracked';
  return 'open';
}

/**
 * Every `path/to/File.ext:line` in a cell, deduplicated, order preserved.
 *
 * Bare basenames are resolved against the full paths in the same row before being emitted. The register
 * often writes a path once and then refers back to the same file by basename — perfectly clear in
 * running prose, but lifting `Query.cs:450` out into a standalone bullet strips the context that made
 * it resolvable and can point the reader at a different file, or at a line that does not exist in the
 * one they guess. Exactly the shorthand-citation trap this vault has already been bitten by twice.
 * A basename with no matching path in its row is dropped rather than emitted unresolvable.
 */
function citations(...fields) {
  const text = fields.map((f) => String(f || '')).join(' ');
  const re = /`([A-Za-z0-9_.\-]+(?:\/[A-Za-z0-9_.\- &]+)*\.(?:cs|ts|cshtml|js|json|yml|md))(:\d+(?:-\d+)?)?`?/g;

  const full = [];
  const bare = [];
  let m;
  while ((m = re.exec(text))) {
    const entry = { path: m[1], line: m[2] || '' };
    (entry.path.includes('/') ? full : bare).push(entry);
  }

  const out = [];
  const push = (c) => { if (c && !out.includes(c)) out.push(c); };
  for (const f of full) push(f.path + f.line);
  for (const b of bare) {
    const owner = full.find((f) => f.path.endsWith('/' + b.path));
    if (owner) push(owner.path + b.line);   // same file, stated in full
    // else: unresolvable on its own. The body still quotes the row verbatim, so nothing is lost.
  }
  return out;
}

/** Wikilinks the row already carries — the notes that explain the surrounding feature. */
function relatedLinks(...fields) {
  const out = [];
  const re = /\[\[([^\]|\\]+)(?:\\?\|([^\]]*))?\]\]/g;
  for (const f of fields) {
    let m; re.lastIndex = 0;
    while ((m = re.exec(String(f || '')))) {
      const link = `[[${m[1]}${m[2] ? `\\|${m[2]}` : ''}]]`;
      if (!out.includes(link)) out.push(link);
    }
  }
  return out;
}

/** Other findings this row cites, so the family is navigable from any member. */
function relatedFindings(id, ...fields) {
  const out = [];
  for (const f of fields) {
    for (const m of String(f || '').matchAll(/#(\d{1,3})\b/g)) {
      const n = +m[1];
      if (n !== id && n >= 1 && n <= 999 && !out.includes(n)) out.push(n);
    }
  }
  return out.sort((a, b) => a - b);
}

/**
 * A short title. The register has no title column, so it is built from the subject plus the row's own
 * opening claim — which is usually written as a sentence and makes a serviceable headline.
 */
function title(r) {
  const subject = plain(r.entity).replace(/^\(|\)$/g, '').replace(/^—\s*see.*$/, '').trim();
  let claim = plain(r.what);
  const stop = claim.search(/[.:;] |\.$/);
  if (stop > 20) claim = claim.slice(0, stop);
  claim = claim.replace(/^(the|a|an)\s+/i, '');
  if (claim.length > 96) claim = claim.slice(0, 93).replace(/\s+\S*$/, '') + '…';
  return { subject: subject || '(system)', claim };
}

function slug(r) {
  const { claim } = title(r);
  const s = claim.toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 58)
    .replace(/-+$/, '');
  return `${String(r.id).padStart(3, '0')}-${s || 'finding'}`;
}

/**
 * The fix section. Authored where the fix is genuinely known, a repeated hint where the register names a
 * correct sibling, and an honest blank otherwise. The label is part of the output so nobody mistakes a
 * hint for a decision.
 */
function fixSection(r) {
  const st = initialStatus(r);
  const body = `${r.what} ${r.other}`;

  if (st === 'fixed') {
    const commit = (r.status.match(/`([0-9a-f]{7,40})`/) || [])[1];
    return {
      kind: 'authored',
      text: `**Already fixed.**${commit ? ` Shipped on \`fix/650-user-privilege-escalation\`, commit \`${commit}\`.` : ''
        } The register row records what was changed and why. Verify against the current code before closing:\nthe branch is not merged at the time of writing, so this fix is not in production yet (see #651).`,
    };
  }

  // The register frequently names the place that does it right. That is the most useful thing that can
  // be said without a fresh decision, so it is repeated verbatim rather than paraphrased.
  const sibling = body.match(/[^.]*\b(?:sibling|gets it right|does it right|correct(?:ly)? scop|the pattern that)\b[^.]*\./i);
  if (sibling) {
    return {
      kind: 'starting point',
      text: `**Starting point, not a decision.** The register names a place in this codebase that already handles this correctly:\n\n> ${sibling[0].trim()}\n\nApply that pattern here, or record why it does not transfer.`,
    };
  }

  return {
    kind: 'needs a decision',
    text: '**Needs a decision.** Nothing in the record implies the fix — it depends on intended behaviour, not on\nreading the code harder. Decide what *should* happen, write it here, then implement.',
  };
}

// ---------------------------------------------------------------------------------------------
// render
// ---------------------------------------------------------------------------------------------
const TODAY = '2026-08-24';

function render(r, keep) {
  const { subject, claim } = title(r);
  const sev = severity(r);
  const st = keep.status || initialStatus(r);
  const cites = citations(r.backend, r.other);
  const links = relatedLinks(r.entity, r.other);
  const kin = relatedFindings(r.id, r.what, r.other);
  const fix = fixSection(r);

  // Scalars only. `where:` rather than `context:` because the note contract requires `context:` to be a
  // CONTEXT-MAP name and these rows carry a feature string. No `sources:` list either: that key demands
  // a sha1 per path, and stamping 651 derived files would mean restamping all of them on every code
  // change to re-prove what `_conflicts.md` already guarantees. The citations live in the body, where
  // verify-citations.js checks them — which is the right place for that check.
  const fm = [
    '---',
    `id: 8orders/issue/${r.id}`,
    'note_type: issue',
    `finding: ${r.id}`,
    `status: ${st}            # open | in-progress | fixed | wont-fix | not-a-defect`,
    `severity: ${sev}`,
    `where: ${plain(r.feature) || '—'}`,
    `last_generated: ${TODAY}`,
    'tags: [issue, generated]',
    '---',
  ];

  const out = [
    ...fm,
    '',
    `# #${r.id} — ${claim}`,
    '',
    BEGIN,
    '',
    `**Status** \`${st}\` · **Severity** \`${sev}\` · **Subject** ${r.entity} · **Where** ${r.feature}`,
    '',
    `**Sides touched.** ${r.sides}`,
    '',
    '## What it is',
    '',
    r.what,
    '',
  ];

  if (cites.length) {
    out.push('## Evidence', '');
    for (const c of cites) out.push(`- \`${c}\``);
    out.push('');
  }

  if (r.other && r.other !== '—' && r.other !== '-') {
    out.push('## Other side / related code', '', r.other, '');
  }

  if (links.length || kin.length) {
    out.push('## Related', '');
    for (const l of links) out.push(`- ${l}`);
    for (const k of kin) out.push(`- finding #${k} — \`_issues/\` has its own file if it is registered`);
    out.push('');
  }

  out.push(
    `Full row, with the reasoning that produced it: [[_system/_conflicts\\|_conflicts.md]] row #${r.id}.`,
    '',
    // The suggested fix sits INSIDE the generated region on purpose. It is derived from the register
    // like everything else, so improving the derivation should improve all 651 files — which cannot
    // happen if it lives in the preserved tail. The human's own conclusion goes under ## Decision
    // below, where nothing will ever overwrite it.
    `## Suggested fix — *${fix.kind}*`,
    '',
    fix.text,
    '',
    END,
    '',
    '## Decision',
    '',
    '<!-- What we are actually going to do, once someone decides. This survives regeneration. -->',
    '',
    '## Working notes',
    '',
    '<!-- Yours: what you tried, what you ruled out, who is on it. Also survives regeneration. -->',
    '',
  );
  return out.join('\n');
}

/** Read back what a person owns: the status, and everything after END. */
function existing(file) {
  if (!fs.existsSync(file)) return {};
  const t = fs.readFileSync(file, 'utf8');
  const status = (t.match(/^status:\s*([a-z-]+)/m) || [])[1];
  const at = t.indexOf(END);
  return { status, tail: at < 0 ? null : t.slice(at + END.length) };
}

// ---------------------------------------------------------------------------------------------
// run
// ---------------------------------------------------------------------------------------------
if (WRITE && !fs.existsSync(ISSUES_DIR)) fs.mkdirSync(ISSUES_DIR, { recursive: true });

const written = [];
const kinds = {};
const sevs = {};
const states = {};
const preserved = [];

for (const r of rows) {
  const file = path.join(ISSUES_DIR, `${slug(r)}.md`);
  const keep = existing(file);
  let text = render(r, keep);

  // splice a person's tail back on, if there is one
  if (keep.tail !== null && keep.tail !== undefined) {
    text = text.slice(0, text.indexOf(END) + END.length) + keep.tail;
    if (keep.tail.trim() && !keep.tail.includes('*(needs a decision)*')) preserved.push(r.id);
  }

  const kind = fixSection(r).kind;
  kinds[kind] = (kinds[kind] || 0) + 1;
  const sev = severity(r); sevs[sev] = (sevs[sev] || 0) + 1;
  const st = keep.status || initialStatus(r); states[st] = (states[st] || 0) + 1;

  if (WRITE) fs.writeFileSync(file, text, 'utf8');
  written.push(path.basename(file));
}

// stale files: an issue whose row left the register
if (fs.existsSync(ISSUES_DIR)) {
  const onDisk = fs.readdirSync(ISSUES_DIR).filter((f) => /^\d{3}-.*\.md$/.test(f));
  const orphans = onDisk.filter((f) => !written.includes(f));
  if (orphans.length) {
    console.log(`⚠️  ${orphans.length} issue file(s) no longer match a register row — rename or delete by hand:`);
    for (const o of orphans.slice(0, 10)) console.log(`      ${o}`);
  }
}

// ---------------------------------------------------------------------------------------------
// index — 651 files need a door
// ---------------------------------------------------------------------------------------------
const SEV_ORDER = ['critical', 'high', 'moderate', 'medium', 'low', 'observation'];

function writeIndex() {
  const byId = new Map(rows.map((r) => [r.id, r]));
  const entries = rows.map((r) => {
    const file = `${slug(r)}.md`;
    const keep = existing(path.join(ISSUES_DIR, file));
    return {
      r, file,
      status: keep.status || initialStatus(r),
      sev: severity(r),
      claim: title(r).claim,
    };
  });

  const open = entries.filter((e) => e.status !== 'fixed' && e.status !== 'wont-fix' && e.status !== 'not-a-defect');
  const bySev = (s) => open.filter((e) => e.sev === s);

  const out = [
    '---',
    'id: 8orders/system/issues-index',
    'note_type: index',
    `last_generated: ${TODAY}`,
    'tags: [index, generated]',
    '---',
    '# Issues — one file per register finding',
    '',
    'Generated by `gen-issues.js` from `_conflicts.md`. **The register stays the source of truth for what',
    'was found**; these files exist to carry the part a table cell cannot — a status you edit as work',
    'happens, and a place to record the fix decision.',
    '',
    'In each file, everything above the END-GENERATED marker is derived and will be overwritten on the',
    'next run. Your `status:` and everything below that marker are never touched.',
    '',
    `**${open.length} open** of ${entries.length} · `
      + SEV_ORDER.map((s) => `${bySev(s).length} ${s}`).filter((x) => !x.startsWith('0 ')).join(' · '),
    '',
    '## Status vocabulary',
    '',
    '`open` · `in-progress` · `fixed` · `wont-fix` · `not-a-defect` — edit the `status:` line in the file.',
    '',
    '## A caution on severity',
    '',
    'Severity is read off the register\'s own wording, not judged fresh. A `medium` here means the row did',
    'not describe itself in stronger terms — it is a starting sort order, not a risk assessment. And a',
    '`🔴 Confirmed` finding is not automatically a live vulnerability: most confirm an observation about',
    'correctness or naming. The access-control subset is what #651 tracks.',
    '',
    '## Open issues, most severe first',
    '',
  ];

  for (const s of SEV_ORDER) {
    const group = bySev(s);
    if (!group.length) continue;
    out.push(`### ${s} (${group.length})`, '');
    out.push('| # | Issue | Where | Status |', '|---|---|---|---|');
    for (const e of group.sort((a, b) => a.r.id - b.r.id)) {
      const claim = e.claim.replace(/\|/g, '\\|');
      out.push(`| ${e.r.id} | [[_system/_issues/${e.file.replace(/\.md$/, '')}\\|${claim}]] | ${plain(e.r.feature)} | \`${e.status}\` |`);
    }
    out.push('');
  }

  const done = entries.filter((e) => !open.includes(e));
  if (done.length) {
    out.push(`## Closed (${done.length})`, '');
    out.push('| # | Issue | Status |', '|---|---|---|');
    for (const e of done.sort((a, b) => a.r.id - b.r.id)) {
      const claim = e.claim.replace(/\|/g, '\\|');
      out.push(`| ${e.r.id} | [[_system/_issues/${e.file.replace(/\.md$/, '')}\\|${claim}]] | \`${e.status}\` |`);
    }
    out.push('');
  }

  if (WRITE) fs.writeFileSync(path.join(ISSUES_DIR, '_index.md'), out.join('\n'), 'utf8');
  return { open: open.length, total: entries.length };
}

const idx = writeIndex();

console.log(`issues ${WRITE ? 'written' : 'to write'} : ${written.length}  (index: ${idx.open} open of ${idx.total})`);
console.log(`by severity          : ${JSON.stringify(sevs)}`);
console.log(`by status            : ${JSON.stringify(states)}`);
console.log(`fix section          : ${JSON.stringify(kinds)}`);
if (preserved.length) console.log(`hand-written tails preserved: ${preserved.length}`);
if (!WRITE) console.log('\n(dry run — pass --write)');
