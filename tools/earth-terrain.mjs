// Preserve complete provider evidence with its exact query and coverage; export immutable browser packs.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', 'resources', 'earth-terrain');
const args = process.argv.slice(2), option = key => args.includes(key) ? args[args.indexOf(key) + 1] : undefined;
fs.mkdirSync(root, { recursive: true });
const sha = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
if (args.includes('--payload')) {
  const raw = fs.readFileSync(option('--payload')), payload = JSON.parse(raw);
  const query = fs.readFileSync(option('--query-file'), 'utf8').trim();
  if (!Array.isArray(payload.elements) || payload.remark) throw Error('Refusing failed or partial provider evidence');
  if (!query.includes('out tags geom;') || !query.includes('[building];out tags center;')) throw Error('Expected a complete local terrain query');
  const boxes = [...query.matchAll(/(?:way|relation)\(([-\d.e]+),([-\d.e]+),([-\d.e]+),([-\d.e]+)\)/g)].map(m => m.slice(1).map(Number));
  if (!boxes.length || boxes.some(b => b.some((n, i) => !Number.isFinite(n) || n !== boxes[0][i]))) throw Error('Query must have one consistent coverage box');
  const [s, w, n, e] = boxes[0];
  if (s >= n || w >= e) throw Error('Invalid coverage');
  const id = sha(query + '\n' + raw).slice(0, 16);
  const snapshot = { schema: 1, id, title: option('--title') || 'Saved area', bounds: { s, w, n, e }, detail: 'local',
    fetchedAt: new Date().toISOString(), endpoint: option('--endpoint') || 'Local Overpass relay (preserved response)',
    osmBase: payload.osm3s?.timestamp_osm_base, sourceSha256: sha(raw), attribution: '© OpenStreetMap contributors; ODbL 1.0', query, payload };
  const file = path.join(root, `area-${id}.json`);
  if (!fs.existsSync(file)) fs.writeFileSync(file, JSON.stringify(snapshot));
}
const areas = fs.readdirSync(root).filter(f => /^area-[a-f0-9]+\.json$/.test(f)).sort().map(file => {
  const bytes = fs.readFileSync(path.join(root, file)), { payload, query, ...metadata } = JSON.parse(bytes);
  return { ...metadata, file, bytes: bytes.length, sha256: sha(bytes) };
});
const manifest = { schema: 1, version: sha(JSON.stringify(areas)).slice(0, 16), areas };
fs.writeFileSync(path.join(root, 'manifest.json'), JSON.stringify(manifest, null, 2) + '\n');
if (args.includes('--export')) {
  const destination = path.resolve(option('--export')); fs.mkdirSync(destination, { recursive: true });
  for (const f of ['manifest.json', ...areas.map(a => a.file)]) fs.copyFileSync(path.join(root, f), path.join(destination, f));
}
console.log(`Preserved ${areas.length} terrain areas (${manifest.version}).`);
