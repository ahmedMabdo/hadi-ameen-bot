// Build the system-graph spec from the registry rather than by hand, so the graph cannot drift from
// _entity-classes.tsv / _feature-map.tsv again.
//
// Derived from the registry:
//   applications = the contexts that have a _context.md
//   cycles       = the 31 features, each under the context that actually owns it
//   entities     = every entity with a note of its own (pair or single shape), with its real note path
// Carried over from the previous hand-curated spec, because they encode judgement no table holds:
//   links, integrations — but only where both endpoints still exist, and nothing invented.

const fs = require('fs');
const path = require('path');

const REPO = process.cwd();
const KG = path.join(REPO, 'docs/knowledge-graph');
const SYS = path.join(KG, '_system');
const OUT = process.argv[2] || path.join(REPO, 'system-spec.json');

const lines = (t) => String(t).split('\n').map((l) => l.replace(/\r$/, ''));
const slug = (s) => s.toLowerCase().replace(/&/g, 'and').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');

// ---- applications ------------------------------------------------------------------------
function walk(dir, out = []) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    if (e.name.startsWith('.')) continue;
    const p = path.join(dir, e.name);
    if (e.isDirectory()) walk(p, out);
    else out.push(p);
  }
  return out;
}
const allFiles = walk(KG).map((p) => path.relative(KG, p).split(path.sep).join('/'));

const contexts = allFiles.filter((f) => /^[^/]+\/_context\.md$/.test(f)).map((f) => f.split('/')[0]).sort();
const applications = contexts.map((c) => ({ id: slug(c), label: c }));

// ---- cycles ------------------------------------------------------------------------------
const featureNotes = allFiles.filter((f) => /^[^/]+\/[^/]+\/_knowledge-graph\.md$/.test(f));
const cycles = [];
const cycleId = new Map();               // "Context/Feature" -> cycle id
for (const f of featureNotes) {
  const [ctx, feat] = f.split('/');
  const id = slug(`${ctx}-${feat}`);
  cycles.push({ id, label: feat, application: slug(ctx) });
  cycleId.set(`${ctx}/${feat}`, id);
}

// ---- entities ----------------------------------------------------------------------------
const TYPE = { 'aggregate-root': 'transaction', 'legacy-poco-root': 'master', child: 'transaction', lookup: 'master' };
const FINANCIAL = /wallet|transaction|payment|bouns|bonus|compensation|statement|loyalty|voucher|journal|treasury|sales/i;

const rows = lines(fs.readFileSync(path.join(SYS, '_entity-classes.tsv'), 'utf8'))
  .filter((l) => l && !l.startsWith('#'))
  .map((l) => l.split('\t'))
  .filter((f) => f.length >= 6);

// note path per entity, from the note that declares `entity:`
const noteFor = new Map();
for (const f of allFiles.filter((x) => x.endsWith('.md'))) {
  const text = fs.readFileSync(path.join(KG, f), 'utf8');
  const fm = (text.match(/^---\r?\n([\s\S]*?)\r?\n---/) || [])[1] || '';
  const ent = ((fm.match(/^entity:\s*(.+)$/m) || [])[1] || '').trim();
  const nt = ((fm.match(/^note_type:\s*(.+)$/m) || [])[1] || '').trim();
  if (!ent) continue;
  const strong = nt === 'technical' || nt === 'single';
  const prev = noteFor.get(ent);
  if (!prev || (strong && !prev.strong)) noteFor.set(ent, { path: `../${f}`, strong });
}

const entities = [];
const seen = new Set();
for (const r of rows) {
  const [entity, , cls, shape, ctx, feat] = r;
  if (!/^(pair|single)$/.test(shape)) continue;               // folded entities would swamp the graph
  if (seen.has(entity)) continue;
  seen.add(entity);
  const cyc = cycleId.get(`${ctx}/${feat}`);
  const note = noteFor.get(entity);
  entities.push({
    id: entity,
    label: entity.replace(/([a-z])([A-Z])/g, '$1\n$2'),
    type: FINANCIAL.test(entity) ? 'financial' : (TYPE[cls] || 'transaction'),
    module: applications.some((a) => a.id === slug(ctx)) ? slug(ctx) : null,
    cycles: cyc ? [cyc] : [],
    ...(note ? { note: note.path } : {}),
  });
}

// ---- links and integrations, carried over -----------------------------------------------
const html = fs.readFileSync(path.join(SYS, 'system-graph.html'), 'utf8');
const start = html.indexOf('const DATA = ');
const from = html.indexOf('{', start);
// scan to the matching close brace, so a `};` inside a label cannot truncate the parse
let depth = 0;
let to = from;
for (; to < html.length; to++) {
  if (html[to] === '{') depth++;
  else if (html[to] === '}') { depth--; if (!depth) break; }
}
const prev = JSON.parse(html.slice(from, to + 1));
const ids = new Set(entities.map((e) => e.id));
const links = (prev.links || []).filter((l) => ids.has(l.source) && ids.has(l.target));
const dropped = (prev.links || []).length - links.length;
// The previous spec called the identity context `identity`; slugging its folder name gives
// `identity-and-access`. Without this alias the four token-issuance integrations would be dropped as
// dangling, silently losing the fact that every host authenticates through one service.
const APP_ALIAS = { identity: 'identity-and-access' };
const appIds = new Set(applications.map((a) => a.id));
const integrations = (prev.integrations || [])
  .map((i) => ({ ...i, source: APP_ALIAS[i.source] || i.source, target: APP_ALIAS[i.target] || i.target }))
  .filter((i) => appIds.has(i.source) && appIds.has(i.target));

fs.writeFileSync(OUT, JSON.stringify({ applications, cycles, entities, links, integrations }, null, 2), 'utf8');
console.log(`applications : ${applications.length}`);
console.log(`cycles       : ${cycles.length}`);
console.log(`entities     : ${entities.length}  (${entities.filter((e) => e.note).length} with a note path)`);
console.log(`links        : ${links.length}  (${dropped} dropped: endpoint no longer an own-note entity)`);
console.log(`integrations : ${integrations.length}`);
console.log(`spec -> ${OUT}`);
const noCycle = entities.filter((e) => !e.cycles.length).map((e) => e.id);
if (noCycle.length) console.log(`\nentities with no cycle (feature not found in the map): ${noCycle.join(', ')}`);
