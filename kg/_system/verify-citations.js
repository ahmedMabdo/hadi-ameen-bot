#!/usr/bin/env node
/**
 * 8Orders Knowledge Graph — CITATION verifier
 *
 * WHY THIS EXISTS
 * ---------------
 * `verify-notes.js` proves nothing is *missing*. It cannot prove that what is written is *true*: a
 * note claiming "rejects orders over 500 EGP (`Order.cs:412`)" is structurally perfect whether or not
 * line 412 has anything to do with it. That gap is the one place where a wrong note can pass every
 * other check, and it is exactly the gap that opens when work is delegated — an author who half-reads
 * a file still produces a citation-shaped string.
 *
 * So this file mechanises the part of "is it true?" that a machine can decide:
 *
 *   1. the cited file exists                                     -> CITE-FILE-MISSING
 *   2. the cited line exists inside it                           -> CITE-LINE-OUT-OF-RANGE
 *   3. the cited line is actual code, not blank / `using` / `}`   -> CITE-LINE-VACUOUS
 *   4. when the citing sentence names symbols, at least one of
 *      them appears near the cited line                          -> CITE-SYMBOL-ABSENT
 *   5. a bare filename shared by several tracked files is
 *      unverifiable and must be spelled out                      -> CITE-BASENAME-AMBIGUOUS
 *
 * Check 5 was added after a register finding was found citing the wrong project: it named
 * `DeliveryMenController.cs:198` meaning the `AdminUi` copy, while `Talabatk.IDS` has a file of the
 * same name whose line 198 also exists. The wrong-file citation therefore looked plausible and stood
 * for months. Silently skipping ambiguity is not neutral — it is where that error lived.
 *
 * Check 4 is the substantive one. A table row almost always names the method, field or type it is
 * describing, in backticks, beside the citation. If none of those names appears within a window
 * around the cited line, the citation points somewhere the claim is not about. That catches drifted
 * line numbers after a rebase and fabricated precision, without needing to understand the claim.
 *
 * It is deliberately a NEAR test, not an exact one: a rule often spans a method whose name is on the
 * signature line a few lines above the guard being cited. WINDOW is generous for that reason, and a
 * row that names no symbol at all is skipped rather than guessed at. False alarms would get this file
 * ignored, which is worse than a slightly loose window.
 *
 *   node verify-citations.js              verify every note; exit non-zero on any failure
 *   node verify-citations.js --note <p>   verify one note (what a delegated author runs)
 *   node verify-citations.js --all        list every failure rather than the first 60
 *   node verify-citations.js --self-test  prove each failure class is detectable
 *
 * Enumeration is `git ls-files`, never `find` — see the header of verify-coverage.js for why.
 */

'use strict';
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const SYSTEM_DIR = __dirname;
const REPO = path.resolve(SYSTEM_DIR, '..', '..', '..');
const KG_REL = 'docs/knowledge-graph';

// How far from the cited line a named symbol may sit and still count as "this is what it is about".
// A guard is commonly a few lines inside the method that names it, and a field table often cites the
// class declaration rather than each property.
const WINDOW = 12;

// Extensions worth checking. A citation to a .json or .md is usually a pointer, not a line claim.
const CODE_EXT = /\.(cs|cshtml|ts|js|razor|sql)$/i;

// A line that carries no claim at all. Split in two deliberately, after calibrating against real
// notes:
//
//   EMPTY   a blank line, a `using`, a `#region`. Nothing was ever there to cite, so a citation
//           landing here is drift — the file moved under the note.
//   BRACKET a lone brace. This is NOT drift: the repo's guards are `if (...) { return Result.Failure }`
//           blocks, and citing the closing line of the construct is normal and verifiable. Accepted
//           when real code sits within BRACKET_REACH lines, which brackets the construct being cited.
//
// Treating a brace as an error produced dozens of false alarms on citations that were correct. A
// checker that cries wolf gets switched off, which costs more than the imprecision it reports.
const EMPTY = /^\s*(using\s|namespace\s|#region|#endregion|\/\/|\/\*|\*\s|\*$|<!--)?\s*$/;
const BRACKET = /^\s*[{}()\];,]+\s*;?\s*$/;
const BRACKET_REACH = 3;

// Declaration lines, used to name the member that ENCLOSES a cited line. This is the fix for the
// commonest false alarm: this codebase has factory methods whose parameter lists run 20+ lines, so
// the guard on line 126 belongs to a signature on line 100 — far outside any sane line window, yet
// obviously the thing the note means when it writes "(`AddCity`)".
// Must look like a DECLARATION, not a call: an access/modifier keyword, then a return type, then the
// name. The looser earlier version matched `TryParseExact(...)` inside a method body and reported the
// enclosing member as a framework call, which is worse than reporting nothing.
const DECL = /^\s*(?:\[[^\]]*\]\s*)*(?:public|private|protected|internal|static|virtual|override|async|sealed|partial)(?:\s+(?:public|private|protected|internal|static|virtual|override|async|sealed|partial))*\s+[A-Za-z0-9_<>?\[\],. ]+?\b([A-Za-z_][A-Za-z0-9_]*)\s*(?:\(|=>|\{|$)/;
const TYPE_DECL = /^\s*(?:public|internal|private|protected|abstract|sealed|partial|static|\s)*\b(?:class|record|struct|interface|enum)\s+([A-Za-z_][A-Za-z0-9_]*)/;

// Tracked files PLUS untracked-but-present ones. A note written seconds ago is a real note: judging
// only committed state made `--note <new file>` answer "no note matches", which reads like a pass and
// would let a delegated author skip the one check that verifies their citations.
// Enumeration is still git's, never `find` — see the header of verify-coverage.js for why.
function gitFiles() {
  const opts = { cwd: REPO, encoding: 'utf8', maxBuffer: 1024 * 1024 * 400 };
  const tracked = execSync('git ls-files', opts);
  const untracked = execSync('git ls-files --others --exclude-standard', opts);
  return [...new Set((tracked + '\n' + untracked).split('\n').map((s) => s.trim()).filter(Boolean))];
}

function lines(text) {
  return String(text || '').split('\n').map((l) => l.replace(/\r$/, ''));
}

// `File.cs:123`, `Path/To/File.cs:123-140`, `File.cs:12,34`
const CITE = /`([A-Za-z0-9_\-./ ]+\.(?:cs|cshtml|ts|js|razor|sql|json|md|csproj)):(\d+)(?:\s*[-,]\s*(\d+))?`/g;
// Other backticked identifiers on the same line: method/field/type names, and `Name(...)` forms.
const SYMBOL = /`([A-Za-z_][A-Za-z0-9_]{2,})(?:\(\))?`/g;

function buildIndex(files) {
  const byBase = new Map();
  for (const f of files) {
    const b = f.split('/').pop();
    if (!byBase.has(b)) byBase.set(b, []);
    byBase.get(b).push(f);
  }
  return byBase;
}

function resolveCited(token, files, byBase, gitSet) {
  const t = token.trim();
  if (t.includes('/')) {
    if (gitSet.has(t)) return { path: t };
    const tail = files.filter((f) => f.endsWith('/' + t));
    if (tail.length === 1) return { path: tail[0] };
    if (tail.length > 1) return { ambiguous: tail.length };
    return { missing: true };
  }
  const cands = (byBase.get(t) || []).filter((f) => !f.startsWith(KG_REL + '/'));
  if (cands.length === 1) return { path: cands[0] };
  if (cands.length > 1) return { ambiguous: cands.length };
  return { missing: true };
}

/**
 * Pure check over one note's text. Kept free of I/O so --self-test can drive it with synthetic
 * sources: expectation (the note's claim) and observation (the file content) then come from two
 * different places, which is the rule this whole toolchain is built on.
 */
function checkNote(noteRel, noteText, readSource) {
  const findings = [];
  const rows = lines(noteText);
  let inFence = false;

  for (let i = 0; i < rows.length; i++) {
    const row = rows[i];
    if (/^\s*```/.test(row)) { inFence = !inFence; continue; }
    if (inFence) continue;                      // a fenced example is not a claim

    const cites = [...row.matchAll(CITE)];
    if (!cites.length) continue;

    // Symbols named around this citation, excluding the file tokens themselves. The window spans one
    // line either side because Markdown prose wraps: a `- **Source:**` bullet routinely puts the
    // citation on one line and the method name it refers to on the next, and judging the line alone
    // reported dozens of correct citations as wrong.
    const fileTokens = new Set(cites.map((c) => c[1].split('/').pop()));
    // A table row is self-contained: its neighbours are OTHER rows about other things, and borrowing
    // their symbols both hides real errors and invents new ones. Prose wraps instead, so for a
    // non-table line the continuation above and below is part of the same sentence.
    const isTableRow = /^\s*\|/.test(row);
    const context = isTableRow ? row : [rows[i - 1] || '', row, rows[i + 1] || ''].join('\n');
    // Words that make no independent claim about a line: the cited file's own stem (naming the file
    // twice adds nothing to check), project and host names, and language keywords.
    const stems = new Set([...fileTokens].map((f) => f.replace(/\.[a-z]+$/i, '')));
    const NOT_A_SYMBOL = /^(cs|ts|js|md|json|sql|true|false|null|int|string|bool|decimal|DateTime|GET|POST|PUT|DELETE|PATCH|AdminUi|TalabatkAPIs|TalabatkAPI|TalabatkRestaurants|TalabatkDelivery|TalabatkLogic|TalabatkData|TalabatkApplication|SharedWeb|Controllers|ClientApp|Angular|Startup)$/i;
    const symbols = [...context.matchAll(SYMBOL)]
      .map((m) => m[1])
      .filter((s) => !fileTokens.has(s) && !stems.has(s) && !NOT_A_SYMBOL.test(s));

    for (const c of cites) {
      const token = c[1];
      const line = Number(c[2]);
      const endLine = c[3] ? Number(c[3]) : null;
      if (!CODE_EXT.test(token)) continue;      // pointer to a doc/config, not a line claim

      // A path the note abbreviated with `...` is a style choice, not a false claim — but it is a
      // claim no machine can check, which is its own weakness. Reported as its own class so it is
      // triaged as "spell the path out" rather than "this citation is wrong".
      if (token.includes('...')) {
        findings.push({ code: 'CITE-PATH-ELIDED', note: noteRel, noteLine: i + 1,
          detail: `\`${token}:${line}\` — abbreviated path cannot be resolved; write it in full so the citation is checkable` });
        continue;
      }

      const src = readSource(token);
      if (src === undefined) {
        findings.push({ code: 'CITE-FILE-MISSING', note: noteRel, noteLine: i + 1,
          detail: `\`${token}:${line}\` — no tracked file resolves to that path` });
        continue;
      }
      if (src === null) {
        // An ambiguous bare filename cannot be checked — but silence here is a blind spot, not a
        // neutral skip. A register finding cited `DeliveryMenController.cs:198` while meaning the
        // AdminUi copy; `Talabatk.IDS` has a file of the same name whose line 198 also exists, so the
        // wrong-file citation looked plausible for months. Reported as a lead so ambiguity gets spelled
        // out rather than trusted.
        findings.push({ code: 'CITE-BASENAME-AMBIGUOUS', note: noteRel, noteLine: i + 1,
          detail: `\`${token}:${line}\` — several tracked files share that basename, so this citation cannot be verified; write the path in full` });
        continue;
      }

      const srcLines = lines(src);
      if (line < 1 || line > srcLines.length) {
        findings.push({ code: 'CITE-LINE-OUT-OF-RANGE', note: noteRel, noteLine: i + 1,
          detail: `\`${token}:${line}\` — the file has ${srcLines.length} lines` });
        continue;
      }
      // A range citation makes TWO claims and only the first was ever checked. `file:120-137` also
      // asserts that 137 is a real line at or after 120. An unchecked end is exactly how a bulk
      // renumbering pass corrupts a vault in silence: rewriting the start of `Order.cs:4158-4162` to
      // 4280 left `Order.cs:4280-4162` behind — a backwards range that every other check in this file
      // accepted, because they all read the start and stop. Both halves are decidable, so both gate.
      if (endLine !== null) {
        if (endLine < line) {
          findings.push({ code: 'CITE-RANGE-INVERTED', note: noteRel, noteLine: i + 1,
            detail: `\`${token}:${line}-${endLine}\` — the range ends before it starts, so it names no lines at all` });
          continue;
        }
        if (endLine > srcLines.length) {
          findings.push({ code: 'CITE-RANGE-PAST-EOF', note: noteRel, noteLine: i + 1,
            detail: `\`${token}:${line}-${endLine}\` — the range runs past the end of the file, which has ${srcLines.length} lines` });
          continue;
        }
      }

      const cited = srcLines[line - 1];
      const isEmpty = EMPTY.test(cited);
      const isBracket = !isEmpty && BRACKET.test(cited);
      if (isEmpty) {
        findings.push({ code: 'CITE-LINE-VACUOUS', note: noteRel, noteLine: i + 1,
          detail: `\`${token}:${line}\` points at "${cited.trim() || '(blank line)'}" — nothing was ever there to cite` });
        continue;
      }
      if (isBracket) {
        // Accept a brace only if it actually brackets code.
        const near = srcLines.slice(Math.max(0, line - 1 - BRACKET_REACH), line + BRACKET_REACH)
          .filter((l) => !EMPTY.test(l) && !BRACKET.test(l));
        if (!near.length) {
          findings.push({ code: 'CITE-LINE-VACUOUS', note: noteRel, noteLine: i + 1,
            detail: `\`${token}:${line}\` points at "${cited.trim()}" with no code within ${BRACKET_REACH} lines` });
          continue;
        }
      }
      if (symbols.length) {
        const from = Math.max(0, line - 1 - WINDOW);
        const to = Math.min(srcLines.length, line - 1 + WINDOW + 1);
        const window = srcLines.slice(from, to).join('\n');

        // Walk upward for the enclosing member and type, so `(\`AddCity\`)` still matches a guard
        // 26 lines inside a long factory signature.
        const enclosing = [];
        for (let k = line - 1; k >= 0 && enclosing.length < 4; k--) {
          const t = srcLines[k].match(TYPE_DECL);
          if (t) { enclosing.push(t[1]); continue; }
          const d = srcLines[k].match(DECL);
          if (d && d[1] && !/^(if|for|foreach|while|switch|return|else|try|catch|using|lock|get|set|new|var)$/.test(d[1])) {
            enclosing.push(d[1]);
          }
        }
        const hit = symbols.find((s) => window.includes(s) || enclosing.includes(s));
        if (!hit) {
          findings.push({ code: 'CITE-SYMBOL-ABSENT', note: noteRel, noteLine: i + 1,
            detail: `\`${token}:${line}\` — none of ${symbols.slice(0, 4).map((s) => '`' + s + '`').join(', ')} appears within ${WINDOW} lines or encloses it`
              + (enclosing.length ? ` (enclosing: ${enclosing.slice(0, 3).join(' < ')})` : '') });
        }
      }
    }
  }
  return findings;
}

function run(only) {
  const files = gitFiles();
  const gitSet = new Set(files);
  const byBase = buildIndex(files);
  const notes = files.filter((f) => f.startsWith(KG_REL + '/') && f.endsWith('.md')
    && !f.includes('/_inbox/'));
  const targets = only ? notes.filter((n) => n === only || n.endsWith(only)) : notes;
  if (only && !targets.length) {
    console.log(`no note matches "${only}"`);
    return 2;
  }

  const cache = new Map();
  const ambiguous = new Map();
  const readSource = (token) => {
    if (cache.has(token)) return cache.get(token);
    const r = resolveCited(token, files, byBase, gitSet);
    let v;
    if (r.path) {
      try { v = fs.readFileSync(path.join(REPO, r.path), 'utf8'); } catch { v = undefined; }
    } else if (r.ambiguous) {
      ambiguous.set(token, r.ambiguous);
      v = null;
    } else v = undefined;
    cache.set(token, v);
    return v;
  };

  const all = [];
  let cited = 0;
  for (const n of targets) {
    const text = fs.readFileSync(path.join(REPO, n), 'utf8');
    cited += [...text.matchAll(CITE)].length;
    all.push(...checkNote(n, text, readSource));
  }

  // Two tiers, because they carry different weight of proof.
  //
  // HARD  — decidable without judgement: the file is absent, the line does not exist, the line is
  //         blank, or the path was written so it cannot be resolved. These gate the build.
  // LEAD  — CITE-SYMBOL-ABSENT. Strong evidence, not proof: prose can legitimately name a symbol
  //         defined elsewhere while citing a line about it. Reported for triage, never a gate.
  //
  // Mixing the two would be the mistake this project has already paid for twice, in the opposite
  // direction: a check whose failures include judgement calls gets waved through, and then the
  // decidable failures inside it are waved through too.
  const HARD = new Set(['CITE-FILE-MISSING', 'CITE-LINE-OUT-OF-RANGE', 'CITE-LINE-VACUOUS', 'CITE-PATH-ELIDED',
    'CITE-RANGE-INVERTED', 'CITE-RANGE-PAST-EOF']);
  const hard = all.filter((f) => HARD.has(f.code));
  const leads = all.filter((f) => !HARD.has(f.code));
  const count = (arr) => arr.reduce((m, f) => (m[f.code] = (m[f.code] || 0) + 1, m), {});

  console.log(`notes checked        : ${targets.length}`);
  console.log(`line citations found : ${cited}`);
  console.log(`ambiguous basenames  : ${ambiguous.size}  (skipped — a bare filename with several matches proves nothing either way)`);
  console.log('');
  const hardBy = count(hard);
  const leadBy = count(leads);
  console.log(`HARD failures (decidable, these gate)   : ${hard.length}`);
  for (const k of Object.keys(hardBy).sort((a, b) => hardBy[b] - hardBy[a])) {
    console.log(`  ${k.padEnd(26)} ${hardBy[k]}`);
  }
  console.log(`LEADS (judgement, triage not gate)      : ${leads.length}`);
  for (const k of Object.keys(leadBy).sort((a, b) => leadBy[b] - leadBy[a])) {
    console.log(`  ${k.padEnd(26)} ${leadBy[k]}`);
  }
  console.log('');
  const limit = process.argv.includes('--all') ? Infinity : 60;
  const show = process.argv.includes('--leads') ? leads : hard;
  for (const f of show.slice(0, limit)) {
    console.log(`  ${f.code}  ${f.note}:${f.noteLine}`);
    console.log(`      ${f.detail}`);
  }
  if (show.length > limit) console.log(`  ... and ${show.length - limit} more (pass --all; --leads to list the judgement tier)`);
  if (!hard.length) {
    console.log('');
    console.log('CITATIONS OK - every resolvable cited line exists and carries code.');
    console.log(`             (${leads.length} lead(s) remain for human triage: node verify-citations.js --leads)`);
    return 0;
  }
  return 1;
}

function selfTest() {
  const SRC = {
    'Order.cs': [
      'using System;',                                   // 1
      '',                                                // 2
      'public class Order {',                            // 3
      '    public Result Confirm(int restaurantId) {',   // 4
      '        if (Total > 500) return Result.Failure("too big");', // 5
      '    }',                                           // 6
      '}',                                               // 7
    ].join('\n'),
  };
  // `null` is what buildModel's reader returns for an ambiguous basename.
  const read = (t) => (t === AMBIGUOUS + '.cs' ? null : (t in SRC ? SRC[t] : undefined));

  // Two tracked files share this basename, so a bare-filename citation to it is unverifiable.
  const AMBIGUOUS = '__ambiguous__';
  const cases = [
    ['CITE-BASENAME-AMBIGUOUS', 'the guard at `' + AMBIGUOUS + '.cs:3` in `Confirm`'],
    ['CITE-FILE-MISSING', 'claim about `Ghost.cs:3` and `Confirm`'],
    ['CITE-LINE-OUT-OF-RANGE', 'the guard at `Order.cs:900` in `Confirm`'],
    ['CITE-LINE-VACUOUS', 'the guard at `Order.cs:2` in `Confirm`'],
    ['CITE-SYMBOL-ABSENT', 'the `PickupTag` rule at `Order.cs:5`'],
    ['CITE-RANGE-INVERTED', 'the guard at `Order.cs:5-3` in `Confirm`'],
    ['CITE-RANGE-PAST-EOF', 'the guard at `Order.cs:5-900` in `Confirm`'],
  ];
  let pass = 0; const fails = [];
  for (const [code, text] of cases) {
    const got = checkNote('note.md', text, read).map((f) => f.code);
    if (got.includes(code)) pass++; else fails.push({ code, got: got.join(', ') || '(nothing)' });
  }
  // And the true-positive case must stay silent, or the check is useless noise.
  const clean = checkNote('note.md', 'the `Confirm` guard rejects a total over 500 (`Order.cs:5`)', read);
  const cleanOk = clean.length === 0;
  console.log(`self-test: ${pass}/${cases.length} failure classes detectable; valid citation ${cleanOk ? 'accepted' : 'WRONGLY FLAGGED'}`);
  for (const f of fails) console.log(`  BLIND SPOT  ${f.code} -> got: ${f.got}`);
  if (!cleanOk) for (const c of clean) console.log(`  FALSE ALARM  ${c.code}: ${c.detail}`);
  if (fails.length || !cleanOk) {
    console.log('');
    console.log('A citation check that cannot see, or that cries wolf, will be ignored. Fix before trusting a pass.');
    return 1;
  }
  console.log('SELF-TEST OK');
  return 0;
}

const args = process.argv.slice(2);
if (args.includes('--self-test')) process.exit(selfTest());
else if (args.includes('--note')) process.exit(run(args[args.indexOf('--note') + 1].replace(/\\/g, '/')));
else process.exit(run(null));
