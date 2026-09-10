/**
 * merge-reverify.js — what does merging a branch oblige this vault to re-check?
 *
 *   node docs/knowledge-graph/_system/merge-reverify.js <branch> [--files]
 *
 * Answers one question: of the source files <branch> changes, which ones does the knowledge graph
 * cite, and which notes cite them? Those note<->file pairs are the re-verify work list — a fix that
 * shifts a line by one makes every citation below it wrong, and `verify-citations.js` will only say so
 * *after* the merge, when the damage is already in the history.
 *
 * Why this exists rather than a list written into the playbook: a frozen list is right on the day it is
 * written and wrong every day after, because the branch keeps moving. The obligation has to be
 * recomputable or it rots — which is the same reason every denominator in this system is derived from
 * code rather than typed out (see _conflicts.md #384, #639).
 *
 * This is a pre-merge tool. It does not gate anything; nothing here can fail a build. Run it before
 * merging, work the list, then let `verify-notes.js` / `verify-citations.js` confirm the result.
 */
'use strict';

const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

const KG_REL = 'docs/knowledge-graph';
const REPO = process.cwd();

const args = process.argv.slice(2);
const branch = args.find((a) => !a.startsWith('--'));
const filesOnly = args.includes('--files');

if (!branch) {
  console.error('usage: node merge-reverify.js <branch> [--files]');
  console.error('   e.g. node merge-reverify.js fix/650-user-privilege-escalation');
  process.exit(2);
}

function git(...a) {
  return execFileSync('git', a, { cwd: REPO, maxBuffer: 1 << 28 }).toString();
}

let base;
try {
  base = git('rev-parse', '--abbrev-ref', 'HEAD').trim();
} catch {
  console.error('not a git working tree');
  process.exit(2);
}

let changed;
try {
  changed = git('diff', '--name-only', `${base}..${branch}`)
    .split('\n')
    .map((s) => s.trim())
    .filter((f) => /\.(cs|ts|cshtml|js|json)$/.test(f));
} catch {
  console.error(`cannot diff ${base}..${branch} — does the branch exist locally?`);
  process.exit(2);
}

const notes = git('ls-files', KG_REL)
  .split('\n')
  .map((s) => s.trim())
  .filter((f) => f.endsWith('.md') && !f.includes('/_inbox/'));

const text = new Map();
for (const n of notes) {
  try { text.set(n, fs.readFileSync(path.join(REPO, n), 'utf8')); } catch { /* unreadable, skip */ }
}

const esc = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

const rows = [];
for (const f of changed) {
  const base_ = path.basename(f);
  // Cited either by full path, or by bare basename with a line number. The bare form is the one that
  // matters most here: it cannot be verified at all (#647), so a silent line shift under it is
  // invisible in both directions.
  const byBasename = new RegExp('`' + esc(base_) + ':\\d+');
  const citing = [];
  for (const [n, t] of text) {
    if (t.includes(f) || byBasename.test(t)) citing.push(n.replace(`${KG_REL}/`, ''));
  }
  if (citing.length) rows.push({ file: f, notes: citing });
}

const pairs = rows.reduce((a, r) => a + r.notes.length, 0);

console.log(`base branch          : ${base}`);
console.log(`merging              : ${branch}`);
console.log(`source files changed : ${changed.length}`);
console.log(`of those, KG-cited   : ${rows.length}`);
console.log(`note<->file pairs    : ${pairs}   <- the re-verify work list`);
console.log('');

if (!rows.length) {
  console.log('Nothing this branch touches is cited by the vault. Merge needs no citation work.');
  process.exit(0);
}

rows.sort((a, b) => b.notes.length - a.notes.length || a.file.localeCompare(b.file));

if (filesOnly) {
  for (const r of rows) console.log(r.file);
} else {
  for (const r of rows) {
    console.log(`${String(r.notes.length).padStart(3)}  ${r.file}`);
    for (const n of r.notes) console.log(`       ${n}`);
  }
}

console.log('');
console.log('After merging, for each file above: re-read the cited rule against the new code, correct');
console.log('the line numbers, and re-stamp the note\'s sha1 —');
console.log('  node docs/knowledge-graph/_system/verify-notes.js --restamp "<note path>"');
console.log('Then confirm: verify-notes.js (0 CITATION-STALE) and verify-citations.js (0 HARD).');
