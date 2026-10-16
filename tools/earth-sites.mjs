// Explicit, bounded public-source snapshots. No cloud database, background worldwide crawl or paid API.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../resources/earth-sites');
const regions = {
  cairo: { name: 'Greater Cairo', lat: 30.0444, lon: 31.2357, radius: 25000 },
  hormuz: { name: 'Strait of Hormuz', lat: 26.6, lon: 56.4, radius: 75000 },
  riyadh: { name: 'Riyadh', lat: 24.7136, lon: 46.6753, radius: 25000 },
  qatar: { name: 'Al Udeid and Doha', lat: 25.1173, lon: 51.3149, radius: 25000 },
  suez: { name: 'Ismailia and Suez Canal', lat: 30.592, lon: 32.318, radius: 20000 },
};
const headers = { 'User-Agent': 'RTSAI-EarthSites/1.0 (+https://github.com/alibad/RTSAI-Mod)' };
const hash = value => crypto.createHash('sha256').update(value).digest('hex');
const write = (file, value) => { fs.mkdirSync(path.dirname(file), { recursive: true }); fs.writeFileSync(file, JSON.stringify(value, null, 2) + '\n'); };
async function read(url, options = {}) {
  const r = await fetch(url, { headers, signal: AbortSignal.timeout(25000), ...options });
  if (!r.ok) throw Error(`${new URL(url).hostname}: ${r.status}`);
  const text = await r.text(); if (text.length > 10000000) throw Error('Snapshot exceeds 10 MB');
  return JSON.parse(text);
}
function osmSites(payload, updatedAt) {
  return (payload.elements ?? []).flatMap(e => {
    const p = e.center ?? e, t = e.tags ?? {};
    if (!Number.isFinite(p.lat) || !Number.isFinite(p.lon)) return [];
    const kind = t.aeroway === 'aerodrome' ? (t.military || t.landuse === 'military' || /air ?base|military/i.test(t.name ?? '') ? 'Air base' : 'Airfield')
      : t.landuse === 'port' || t.landuse === 'harbour' || t.harbour || t.industrial === 'port' || t['seamark:type'] === 'harbour' ? 'Port'
      : t.military === 'barracks' ? 'Barracks' : t.military === 'naval_base' ? 'Naval base' : t.military === 'airfield' ? 'Air base' : 'Military area';
    return [{ id: `osm-${e.type}-${e.id}`, name: String(t['name:en'] || t.name || kind).slice(0, 200), kind, lat: p.lat, lon: p.lon,
      source: 'OpenStreetMap', url: `https://www.openstreetmap.org/${e.type}/${e.id}`, operator: t['operator:en'] || t.operator || t.military_service, updatedAt }];
  });
}
const args = process.argv.slice(2), collect = args.includes('--collect') ? args[args.indexOf('--collect') + 1].split(',') : [];
for (const id of collect) {
  const r = regions[id]; if (!r) throw Error(`Unknown region ${id}`);
  const dy = r.radius / 111320, dx = dy / Math.cos(r.lat * Math.PI / 180);
  const bounds = [r.lat - dy, r.lon - dx, r.lat + dy, r.lon + dx];
  const bb = bounds.join(',');
  const query = `[out:json][timeout:20];(nwr["landuse"="military"](${bb});nwr["military"](${bb});nwr["aeroway"="aerodrome"](${bb});nwr["landuse"~"^(port|harbour)$"](${bb});nwr["harbour"](${bb});nwr["industrial"="port"](${bb});nwr["seamark:type"="harbour"](${bb}););out tags center;`;
  const oldFile = path.join(root, 'regions', `${id}.json`);
  const previous = fs.existsSync(oldFile) ? JSON.parse(fs.readFileSync(oldFile, 'utf8')) : null;
  const updatedAt = Date.now(), sites = [...(previous?.sites ?? [])], coverage = { ...(previous?.coverage ?? {}) }, sources = [...(previous?.sources ?? [])];
  for (const endpoint of ['https://overpass.private.coffee/api/interpreter', 'https://overpass-api.de/api/interpreter']) {
    try {
      const raw = await read(endpoint, { method: 'POST', body: new URLSearchParams({ data: query }) });
      if (raw.remark || !Array.isArray(raw.elements)) throw Error('Incomplete Overpass response');
      write(path.join(root, 'sources', `${id}-osm.json`), { endpoint, query, updatedAt, payload: raw });
      sites.splice(0, sites.length, ...sites.filter(s => s.source !== 'OpenStreetMap'), ...osmSites(raw, updatedAt)); coverage.OpenStreetMap = updatedAt; sources.push({ provider: 'OpenStreetMap', license: 'ODbL-1.0', url: 'https://www.openstreetmap.org/copyright' }); break;
    } catch (e) { console.warn(id, e.message); }
  }
  try {
    const url = `https://en.wikipedia.org/w/api.php?action=query&list=geosearch&gscoord=${r.lat}|${r.lon}&gsradius=10000&gslimit=500&format=json&origin=*`;
    const raw = await read(url);
    if (!Array.isArray(raw.query?.geosearch)) throw Error('Invalid Wikipedia response');
    write(path.join(root, 'sources', `${id}-wiki.json`), { url, updatedAt, payload: raw });
    sites.splice(0, sites.length, ...sites.filter(s => s.source !== 'Wikipedia'));
    sites.push(...raw.query.geosearch.filter(a => /air ?base|airbase|naval|military|army|camp |fort|barracks|garrison|airport|port|harbou?r|strait|bridge|dam|canal|island/i.test(a.title) && !/stadium|university|school|hospital|mosque|church|club|museum|hotel|mall/i.test(a.title))
      .map(a => ({ id: `wiki-${a.pageid}`, name: a.title, kind: 'Infrastructure', lat: a.lat, lon: a.lon, source: 'Wikipedia', url: `https://en.wikipedia.org/wiki/${encodeURIComponent(a.title.replaceAll(' ', '_'))}`, updatedAt })));
    // Geosearch covers a 10 km circle, not the whole packaged region. Do not claim broader completeness.
    sources.push({ provider: 'Wikipedia', license: 'CC0 geographic metadata; linked articles carry their own licenses', url: 'https://www.mediawiki.org/wiki/API:Geosearch', radius: 10000 });
  } catch (e) { console.warn(id, e.message); }
  if (!sites.length) throw Error(`No source data for ${id}; previous snapshot preserved`);
  write(path.join(root, 'regions', `${id}.json`), { schema: 1, id, name: r.name, bounds, updatedAt, coverage, sources, sites });
  console.log(`${id}: ${sites.length} site records saved`);
}

if (args.includes('--import-osm')) {
  const input = path.resolve(args[args.indexOf('--import-osm') + 1]), id = args[args.indexOf('--region') + 1];
  if (!regions[id]) throw Error('Import requires a known --region');
  const raw = JSON.parse(fs.readFileSync(input, 'utf8')), updatedAt = Date.parse(raw.osm3s?.timestamp_osm_base);
  if (!Number.isFinite(updatedAt) || !Array.isArray(raw.elements) || raw.remark) throw Error('Import requires an intact attributed Overpass response');
  const file = path.join(root, 'regions', `${id}.json`), region = JSON.parse(fs.readFileSync(file, 'utf8'));
  region.sites = [...new Map([...region.sites, ...osmSites(raw, updatedAt)].map(s => [s.id, s])).values()];
  const query = args.includes('--query-file') ? fs.readFileSync(path.resolve(args[args.indexOf('--query-file') + 1]), 'utf8') : null;
  const archived = { query, updatedAt, payload: raw }, sourceFile = `${id}-osm-preserved-${hash(JSON.stringify(archived)).slice(0, 16)}.json`;
  const source = { provider: 'OpenStreetMap', license: 'ODbL-1.0', url: 'https://www.openstreetmap.org/copyright', file: sourceFile,
    note: query ? 'Exact bounded query and public-source response preserved; no full-region coverage claim.' : 'Preserved local public-source response. Original query bounds unavailable; no full-region coverage claim.' };
  if (!region.sources.some(s => s.file === sourceFile)) region.sources.push(source);
  region.updatedAt = Math.max(region.updatedAt, updatedAt);
  write(file, region); write(path.join(root, 'sources', sourceFile), archived);
}

// Build deterministic immutable packs from every preserved region. Old packs remain available for old manifests.
const packed = [], all = new Map();
for (const file of fs.existsSync(path.join(root, 'regions')) ? fs.readdirSync(path.join(root, 'regions')).sort() : []) {
  if (!file.endsWith('.json')) continue;
  const region = JSON.parse(fs.readFileSync(path.join(root, 'regions', file), 'utf8'));
  const body = JSON.stringify(region), digest = hash(body), name = `region-${region.id}-${digest.slice(0, 16)}.json`;
  fs.mkdirSync(path.join(root, 'packs'), { recursive: true }); fs.writeFileSync(path.join(root, 'packs', name), body);
  packed.push({ ...region, sites: undefined, file: name, sha256: digest, bytes: Buffer.byteLength(body), count: region.sites.length });
  for (const s of region.sites) all.set(s.id, { id: s.id, name: s.name, kind: s.kind, lat: s.lat, lon: s.lon, source: s.source, url: s.url, updatedAt: s.updatedAt });
}
const overviewBody = JSON.stringify([...all.values()].sort((a, b) => a.id.localeCompare(b.id)));
const overviewHash = hash(overviewBody), overviewFile = `overview-${overviewHash.slice(0, 16)}.json`;
fs.mkdirSync(path.join(root, 'packs'), { recursive: true }); fs.writeFileSync(path.join(root, 'packs', overviewFile), overviewBody);
const manifest = { schema: 1, version: hash(JSON.stringify(packed) + overviewHash).slice(0, 16), count: all.size, updatedAt: Math.max(0, ...packed.map(p => p.updatedAt)),
  scope: 'Known public geographic sites in the listed snapshots. Not a complete world inventory or current force positions.',
  overview: { file: overviewFile, sha256: overviewHash, bytes: Buffer.byteLength(overviewBody) }, regions: packed };
write(path.join(root, 'manifest.json'), manifest);
if (args.includes('--export')) {
  const target = path.resolve(args[args.indexOf('--export') + 1]); fs.mkdirSync(target, { recursive: true });
  fs.copyFileSync(path.join(root, 'manifest.json'), path.join(target, 'manifest.json'));
  for (const file of [overviewFile, ...packed.map(p => p.file)]) fs.copyFileSync(path.join(root, 'packs', file), path.join(target, file));
}
console.log(`Dataset ${manifest.version}: ${all.size} known sites, ${packed.length} region packs, ${manifest.overview.bytes} overview bytes`);
