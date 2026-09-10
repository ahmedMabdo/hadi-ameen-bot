// Audit: which findings in the Round 5 batch reports never reached a register?
//
// THIRD ATTEMPT. The first two failed by being too broad; a fourth failure mode then showed up that
// mattered more: my "36/36 verified" check derived its expectation from MY OWN claims about what I had
// folded, so any finding I never claimed was invisible to it. Q23's two confirmed findings were missing
// and the check could not see them. That is expectation and observation from the same source — the
// exact circularity error already on record.
//
// So: expectation comes ONLY from the report files, never from my claims. Scope is restricted to the
// Round 5 batch reports (phase2-Q-batch*, phase2-R-batch*), which share a structure — one section per
// finding, verdict word in the heading or first lines. Earlier attempts drowned in phase1-3-mapping.md
// and phase2-1a-commands-CD.md, which are INVENTORIES (what was read) rather than finding lists.
'use strict';
const fs = require('fs');
const path = require('path');

// This directory, resolved from the script's own location. It was previously hardcoded to one
// absolute path on one machine, which made this gate lie in a way its own header warns about: run
// from a git worktree, a second clone, or the mirror repo, it read the registers of a DIFFERENT
// checkout while reporting on this one — and "0 unlanded" from the wrong tree is indistinguishable
// from "0 unlanded" from the right one. It only crashed here because the main checkout happened to
// be on a branch with no `docs/knowledge-graph`; had it been on this branch, the pass would have
// been false and silent.
const SYS = __dirname;
const INBOX = path.join(SYS, '_inbox');
const registers =
  fs.readFileSync(path.join(SYS, '_conflicts.md'), 'utf8') +
  fs.readFileSync(path.join(SYS, '_idor-instances.md'), 'utf8');

// Covers every Round 5 batch family: Queries, Remainder, Controllers, TypeScript.
// The C and TS families additionally emit a machine-readable `FINDING:` line per finding (the #433
// fix), so for those the check is exact rather than heuristic — see below.
// Path A reports are included here deliberately. Left out, this script would scan only the Round 5
// families, find nothing unlanded, print "0" and be believed - while a round's worth of new findings
// sat in the same directory, invisible to it. That is the circularity this file's header is about,
// one directory over: a checker whose scope is narrower than the thing it certifies.
// Path A reports use the same machine-readable `FINDING:` line, so they land in the exact pass below.
const reports = fs.readdirSync(INBOX)
  .filter((f) => /^(phase2-[QR]|phase3-C|phase4-TS)-batch\d+\.md$/.test(f) || /^pathA-.*\.md$/.test(f))
  .sort();

const rows = [];

// ---- exact pass: batches that emit the machine-readable FINDING: line -------------------------
// This is what #433 asked for. No heuristics: one line per finding, verdict and citation explicit.
for (const f of reports) {
  const txt = fs.readFileSync(path.join(INBOX, f), 'utf8');
  for (const line of txt.split('\n')) {
    const m = line.match(/^FINDING:\s*(confirmed|likely)\s*\|\s*([^|]+?)\s*\|\s*(.+)$/i);
    if (!m) continue;
    const cite = m[2].trim();
    // `cshtml` must precede `cs` in the alternation: regex alternation is ordered, so `.cs|.ts` matched
    // `_Layout.cshtml` as `_Layout.cs` and then looked for a citation that does not exist. Two correctly
    // landed findings were reported as unlanded by that alone.
    const base = (cite.match(/([A-Za-z0-9_]+\.(?:cshtml|cs|ts))/) || [])[1];
    if (!base) continue;
    const citeLine = (cite.match(/:(\d+)/) || [, '?'])[1];

    // FOURTH failure mode of this check, and the worst so far: matching on FILENAME ALONE.
    // `DeliveryMenController` appears 5 times in _conflicts.md from earlier rounds, so a brand-new
    // CRITICAL finding at DeliveryMenController.cs:239 was reported as already landed and vanished
    // from the output. Eleven Path A findings were hidden this way - every one in a file some earlier
    // round had already written about, which is exactly where new findings are most likely to be.
    //
    // A filename is not a finding. So: a finding counts as landed only when the registers cite that
    // file AT THAT LINE. When the file is present but the line is not, that is its own bucket -
    // 'line-not-found' - rather than a silent pass, because the alternative is choosing between false
    // positives (whole file re-reported) and false negatives (new finding swallowed). Naming the
    // ambiguity beats guessing which way to resolve it.
    const fileInRegisters = registers.includes(base) || registers.includes(base.replace(/\.(cs|ts)$/, ''));
    const lineInRegisters = citeLine !== '?' && registers.includes(`${base}:${citeLine}`);
    if (fileInRegisters && lineInRegisters) continue;

    rows.push({
      report: f.replace(/^phase\d-|\.md$/g, ''),
      verdict: m[1].toLowerCase(),
      file: base,
      line: citeLine,
      claim: m[3].slice(0, 90),
      bucket: fileInRegisters ? 'line-not-found' : 'missing',
    });
  }
}

// ---- heuristic pass: older batches with prose sections and no FINDING: line -------------------
for (const f of reports) {
  const txt = fs.readFileSync(path.join(INBOX, f), 'utf8');
  if (/^FINDING:/m.test(txt)) continue; // already covered exactly above
  for (const sec of txt.split(/\n(?=#{2,4} )/)) {
    const head = sec.split('\n')[0] || '';
    const lead = sec.slice(0, 500);
    // A finding section: verdict word present near the top.
    const isConfirmed = /\bconfirmed\b/i.test(head) || /\*\*confirmed\*\*|`confirmed`|^- \*\*confirmed/im.test(lead);
    const isLikely = /\blikely\b/i.test(head) || /\*\*likely\*\*|`likely`/i.test(lead);
    if (!isConfirmed && !isLikely) continue;
    // Exclude explicit negative-result sections.
    if (/no finding|ruled out|not reported|checked.{0,20}(clean|no issue)|already (logged|tracked|recorded|documented)|not duplicated/i.test(head)) continue;
    // Primary citation = first File.cs:LINE in the section.
    const cite = sec.match(/([A-Za-z0-9_]+\.cs):(\d+)/);
    if (!cite) continue;
    const base = cite[1];
    // Match on the bare type name too: the instance register cites some handlers without the ".cs"
    // extension (e.g. `GetLastLocationByIdQuery`), which produced two false "missing" reports.
    const stem = base.replace(/\.cs$/, '');
    if (registers.includes(base) || registers.includes(stem)) continue;
    rows.push({
      report: f.replace(/^phase2-|\.md$/g, ''),
      verdict: isConfirmed ? 'confirmed' : 'likely',
      file: base,
      line: cite[2],
      claim: head.replace(/^#+\s*/, '').slice(0, 90),
    });
  }
}

console.log(`Round 5 batch reports scanned : ${reports.length}`);
console.log(`finding sections whose primary cited file is in NO register : ${rows.length}`);
console.log('');
const conf = rows.filter((r) => r.verdict === 'confirmed');
console.log(`  confirmed: ${conf.length}   likely: ${rows.length - conf.length}`);
const missing = rows.filter((r) => r.bucket === 'missing').length;
const lineNF = rows.filter((r) => r.bucket === 'line-not-found').length;
console.log(`  file absent from every register: ${missing}   file present but NOT at this line: ${lineNF}`);
console.log('');
for (const r of rows) {
  console.log(`  ${r.verdict.padEnd(10)} ${String(r.bucket || 'missing').padEnd(14)} ${(r.file + ':' + r.line).padEnd(46)} ${r.claim}`);
}
