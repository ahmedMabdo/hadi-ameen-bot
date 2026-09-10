// Phase 8 backfill: give every register row at least one resolvable wikilink.
//
// The destination is derived from what the row already states, in this order — never invented:
//   1. the Entity cell names an entity that has its own note, or is folded into one (covers:);
//   2. the row cites a controller path that _feature-map.tsv maps to a feature  <- code-derived;
//   3. the Feature(s) cell names a feature, or a context;
//   4. an alias for the handful of names the register uses that are not folder names;
//   5. a system register (_master-plan for KG-integrity rows, _integrations for flow rows),
//      else _system-index — and every one of these is reported, so the fallback is never silent.
//
// Run with --write to apply. Without it, prints what it would do.

const fs = require('fs');
const path = require('path');

const REPO = process.cwd();
const KG = path.join(REPO, 'docs/knowledge-graph');
const SYS = path.join(KG, '_system');
const BS = String.fromCharCode(92);
const WRITE = process.argv.includes('--write');

const lines = (t) => String(t).split('\n').map((l) => l.replace(/\r$/, ''));

function cells(rest) {
  const parts = [];
  let cur = '';
  for (let i = 0; i < rest.length; i++) {
    if (rest[i] === BS) { cur += rest[i] + (rest[i + 1] || ''); i++; continue; }
    if (rest[i] === '|') { parts.push(cur); cur = ''; continue; }
    cur += rest[i];
  }
  parts.push(cur);
  return parts;
}

function walk(dir, out = []) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    if (e.name.startsWith('.')) continue;
    const p = path.join(dir, e.name);
    if (e.isDirectory()) walk(p, out);
    else if (e.name.endsWith('.md')) out.push(p);
  }
  return out;
}

// ---- note inventory ----------------------------------------------------------------------
const notes = walk(KG).map((abs) => {
  const rel = path.relative(KG, abs).split(path.sep).join('/');
  const text = fs.readFileSync(abs, 'utf8');
  const fm = (text.match(/^---\r?\n([\s\S]*?)\r?\n---/) || [])[1] || '';
  const entity = ((fm.match(/^entity:\s*(.+)$/m) || [])[1] || '').trim();
  const noteType = ((fm.match(/^note_type:\s*(.+)$/m) || [])[1] || '').trim();
  const coversRaw = ((fm.match(/^covers:\s*\[([^\]]*)\]/m) || [])[1] || '');
  const covers = coversRaw.split(',').map((s) => s.trim()).filter(Boolean);
  return { rel, base: path.basename(rel, '.md'), entity, noteType, covers };
});

const baseCount = new Map();
for (const n of notes) baseCount.set(n.base, (baseCount.get(n.base) || 0) + 1);
const linkFor = (n, label) => ({
  target: baseCount.get(n.base) === 1 ? n.base : n.rel.replace(/\.md$/, ''),
  label: label || n.entity || n.base,
});

// entity name -> note. A technical/single note is the useful destination for a finding, so it wins
// over the business half of a pair; a note of its own wins over a host note that merely covers it.
const entityTarget = new Map();
const RANK = { technical: 3, single: 3, business: 2 };
for (const n of notes) {
  if (!n.entity) continue;
  const rank = RANK[n.noteType] || 1;
  const prev = entityTarget.get(n.entity);
  if (!prev || rank > prev.rank) entityTarget.set(n.entity, { ...linkFor(n), rank });
}
for (const n of notes) {
  for (const c of n.covers) {
    if (!entityTarget.has(c)) entityTarget.set(c, { ...linkFor(n, c), rank: 0 });
  }
}

// feature / context targets
const featureTarget = new Map();
const bareFeature = new Map();
const contextTarget = new Map();
for (const n of notes) {
  const parts = n.rel.split('/');
  if (parts.length === 2 && parts[1] === '_context.md') {
    contextTarget.set(parts[0].toLowerCase(), { target: `${parts[0]}/_context`, label: parts[0] });
  }
  if (parts.length === 3 && parts[2] === '_knowledge-graph.md') {
    const [ctx, feat] = parts;
    const t = { target: `${ctx}/${feat}/_knowledge-graph`, label: feat };
    featureTarget.set(`${ctx}/${feat}`.toLowerCase(), t);
    if (!bareFeature.has(feat.toLowerCase())) bareFeature.set(feat.toLowerCase(), []);
    bareFeature.get(feat.toLowerCase()).push(t);
  }
}
for (const [k, v] of bareFeature) if (v.length === 1) featureTarget.set(k, v[0]);

// ---- code-derived: controller path -> feature --------------------------------------------
const featureMap = new Map();      // full path (lowercase) -> {context, feature}
const featureByBase = new Map();   // basename -> Set of "context/feature"
for (const l of lines(fs.readFileSync(path.join(SYS, '_feature-map.tsv'), 'utf8'))) {
  if (!l || l.startsWith('#')) continue;
  const [p, ctx, feat] = l.split('\t');
  if (!p || !ctx || !feat) continue;
  featureMap.set(p.toLowerCase(), { ctx, feat });
  const base = p.split('/').pop().toLowerCase();
  if (!featureByBase.has(base)) featureByBase.set(base, new Set());
  featureByBase.get(base).add(`${ctx}/${feat}`);
}

function resolveByCitedController(rowText) {
  const paths = [...rowText.matchAll(/`([^`]*?\.cs)[`:]/g)].map((m) => m[1]);
  for (const p of paths) {
    const hit = featureMap.get(p.toLowerCase());
    if (hit) {
      const t = featureTarget.get(`${hit.ctx}/${hit.feat}`.toLowerCase());
      if (t) return t;
    }
  }
  for (const p of paths) {
    const base = p.split('/').pop().toLowerCase();
    const set = featureByBase.get(base);
    if (set && set.size === 1) {
      const t = featureTarget.get([...set][0].toLowerCase());
      if (t) return t;
    }
  }
  return null;
}

// ---- the names the register uses that are not folder names -------------------------------
const ALIAS = {
  'admin portal': 'Admin',
  'delivery portal': 'Delivery',
  'restaurant': 'Restaurant Portal',
  'merchant portal': 'Restaurant Portal',
  'chat': 'Customer Ordering/Support & Chat',
  'online payment': 'Customer Ordering/Payments',
  'payments & wallet': 'Customer Ordering/Payments',
  'loyalty points': 'Customer Ordering/Customer Account',
  'audience segmentation': 'Admin/Catalog & Content Administration',
  'audiences': 'Admin/Catalog & Content Administration',
  'search & discovery': 'Customer Ordering/Restaurant & Menu Discovery',
  'recommendations': 'Customer Ordering/Restaurant & Menu Discovery',
  'erp integration': 'Admin/ERP & Integrations',
  'integrations': 'Admin/ERP & Integrations',
  'accounting': 'Admin/ERP & Integrations',
  'external delivery': 'Admin/Delivery Administration',
};

function resolveName(raw) {
  let s = String(raw || '').replace(/\*\*/g, '').replace(/^\*|\*$/g, '').trim();
  s = s.split('(')[0].split(/\s+[—–]\s+/)[0].replace(/\s+/g, ' ').trim();
  if (!s) return null;
  const key = s.toLowerCase();
  const aliased = ALIAS[key];
  if (aliased) {
    const ak = aliased.toLowerCase();
    if (featureTarget.has(ak)) return featureTarget.get(ak);
    if (contextTarget.has(ak)) return contextTarget.get(ak);
  }
  if (featureTarget.has(key)) return featureTarget.get(key);
  if (contextTarget.has(key)) return contextTarget.get(key);
  return null;
}

// Try every comma- and slash-separated segment, so "Cross-cutting (X), Customer Ordering (Y)"
// still lands on Customer Ordering rather than falling through to the system index.
function resolveFeatureCell(raw) {
  const segs = String(raw || '').split(/,| \/ /);
  for (const seg of segs) {
    const t = resolveName(seg);
    if (t) return t;
  }
  return null;
}

// Only two shapes count as the row naming an entity: the "*(Name, no dedicated note)*" opener, and a
// backticked identifier. A bare capitalised word anywhere in the cell is not enough — "Customer-Delivery
// chat proxy" is about the chat, not about Customer, and matching the word would file it wrongly.
function resolveEntityCell(raw) {
  const s = String(raw || '');
  const candidates = [];
  const bare = s.match(/^\s*\*?\(\s*([A-Z][A-Za-z0-9_]*)s?\s*[,)]/);
  if (bare) candidates.push(bare[1], bare[1].replace(/s$/, ''));
  for (const m of s.matchAll(/`([A-Z][A-Za-z0-9_]*)`/g)) candidates.push(m[1]);
  for (const c of candidates) if (entityTarget.has(c)) return entityTarget.get(c);
  for (const c of candidates) {
    if (c.endsWith('s') && entityTarget.has(c.slice(0, -1))) return entityTarget.get(c.slice(0, -1));
  }
  return null;
}

// A row that declares itself system-wide or cross-cutting must not be filed under whichever feature
// happens to own the first file it cites — that reads as a scope it explicitly denies.
const CROSSCUT = /system-wide|cross-cutting|knowledge graph|repo-wide|all hosts|all apps|all contexts/i;

const KG_TOPIC = /knowledge graph|kg tooling|kg process/i;
const FLOW_TOPIC = /notification|webhook|hangfire|integration|firebase|fcm|sms|erp/i;

// An IDOR row names the actor whose data leaks ("Another restaurant's...", "Any driver's...").
// That is the row's own statement of which context owns the exposure, so it is a fair destination
// when nothing more specific resolves.
const ACTOR = [
  [/\b(restaurant|merchant|store)('s|s')/i, 'Restaurant Portal'],
  [/\b(driver|delivery ?man|supplier)('s|s')/i, 'Delivery'],
  [/\bcustomers?('s|s')/i, 'Customer Ordering'],
  [/\b(admin|aspnetuser|user)('s|s')/i, 'Identity & Access'],
];

function resolveByActor(rowText) {
  for (const [re, ctx] of ACTOR) {
    if (re.test(rowText)) return contextTarget.get(ctx.toLowerCase()) || null;
  }
  return null;
}

function systemFallback(rowText, featCell) {
  if (KG_TOPIC.test(featCell)) return { target: '_system/_master-plan', label: 'master plan' };
  if (FLOW_TOPIC.test(featCell)) return { target: '_system/_integrations', label: 'integrations' };
  if (FLOW_TOPIC.test(rowText)) return { target: '_system/_integrations', label: 'integrations' };
  return { target: '_system/_system-index', label: 'system index' };
}

const link = (t) => `[[${t.target}${BS}|${t.label}]]`;

// ---- rewrite -----------------------------------------------------------------------------
const tally = { entity: 0, controller: 0, feature: 0, context: 0, system: 0 };
const fellBack = [];
const SAMPLE = process.argv.includes('--sample');
const samples = { entity: [], controller: [], feature: [], context: [], system: [] };

for (const file of ['_conflicts.md', '_idor-instances.md']) {
  const abs = path.join(SYS, file);
  const rows = lines(fs.readFileSync(abs, 'utf8'));
  let changed = 0;

  for (let i = 0; i < rows.length; i++) {
    const m = rows[i].match(/^(\|\s*(\d+)\s*\|)(.*)$/);
    if (!m) continue;
    if (/\[\[/.test(m[3])) continue;
    const c = cells(m[3]);
    if (c.length < 4) continue;

    const isConflicts = file === '_conflicts.md';
    const featCell = isConflicts ? String(c[c.length - 3] || '') : '';
    let target = null;
    let mode = null;

    const crosscut = CROSSCUT.test(c[0]) || CROSSCUT.test(featCell);

    target = resolveEntityCell(c[0]);
    if (target) mode = 'entity';

    // Only the Backend-ref / other-side-ref cells, never the whole row: the prose often names other
    // files for contrast ("the sibling that gets it right", "rejected on inspection"), and filing a
    // finding under the feature of a file it merely mentions is worse than filing it under a context.
    const refCells = isConflicts ? [c[3], c[4]].join(' ') : m[3];
    if (!target && !crosscut) {
      target = resolveByCitedController(refCells);
      if (target) mode = 'controller';
    }
    if (!target && isConflicts) {
      target = resolveFeatureCell(featCell);
      if (target) mode = /_knowledge-graph$/.test(target.target) ? 'feature' : 'context';
    }
    if (!target && !isConflicts) {
      target = resolveByActor(m[3]);
      if (target) mode = 'context';
    }
    if (!target) {
      target = systemFallback(m[3], featCell);
      mode = 'system';
      fellBack.push(`${file} #${m[2]}  ${(featCell || c[0]).trim().slice(0, 58)}`);
    }
    tally[mode]++;

    const body0 = String(c[0] || '').trim();
    const pureNoNote = /^\*?\([^)]*no dedicated[^)]*\)\*?$/i.test(body0);
    if (isConflicts && (!body0 || body0 === '—')) {
      c[0] = ` ${link(target)} `;
    } else if (isConflicts && mode === 'entity' && pureNoNote) {
      c[0] = ` ${link(target)} `;                      // the cell said "no note"; there is one now
    } else if (isConflicts) {
      c[0] = ` ${body0} — see ${link(target)} `;
    } else {
      const last = Math.max(0, c.length - 2);
      const body = String(c[last] || '').trim();
      c[last] = body && body !== '—' ? ` ${body} · ${link(target)} ` : ` ${link(target)} `;
    }

    const rewritten = m[1] + c.join('|');
    // Integrity: the edit must change one cell's text and nothing structural. A markdown table row
    // that gains or loses a cell silently reflows every column after it.
    const before = cells(m[3]).length;
    const after = cells(rewritten.match(/^\|\s*\d+\s*\|(.*)$/)[1]).length;
    if (before !== after) {
      throw new Error(`row #${m[2]} in ${file}: cell count changed ${before} -> ${after}; refusing to write`);
    }
    if ((rewritten.match(/\[\[/g) || []).length !== 1) {
      throw new Error(`row #${m[2]} in ${file}: expected exactly one new link`);
    }
    rows[i] = rewritten;
    changed++;
    if (SAMPLE && samples[mode] && samples[mode].length < 8) {
      samples[mode].push(`  #${m[2]}  ${c[0].trim().slice(0, 150)}`);
    }
  }

  if (WRITE) fs.writeFileSync(abs, rows.join('\r\n'), 'utf8');
  console.log(`${file}: ${changed} row(s) ${WRITE ? 'rewritten' : 'would be rewritten'}`);
}

console.log('');
console.log(`entity note (own or host)      : ${tally.entity}`);
console.log(`feature, via a cited controller: ${tally.controller}   <- code-derived`);
console.log(`feature, via the Feature cell  : ${tally.feature}`);
console.log(`context note                   : ${tally.context}`);
console.log(`system register (fallback)     : ${tally.system}`);
if (SAMPLE) {
  for (const k of Object.keys(samples)) {
    if (!samples[k].length) continue;
    console.log('');
    console.log(`--- sample rewrites, mode "${k}":`);
    for (const s of samples[k]) console.log(s);
  }
}
if (fellBack.length) {
  console.log('');
  console.log(`Rows that fell back to a system register: ${fellBack.length}`);
  if (!SAMPLE) for (const f of fellBack) console.log('  ' + f);
}
