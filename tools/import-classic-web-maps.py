#!/usr/bin/env python3
"""Curate native Classic, Red Alert Plus and Combined Arms maps for Classic web.

Retain terrain binaries, author credits, actors and gameplay rules. No conversion
to isometric terrain and no replacement of unfamiliar actors with placeholders.
ClassicBundle packages only this reviewed collection when it is present.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT.parent
SOURCES = [
    ('Classic', 'classic', ROOT/'mods/rtsai-classic-core/maps', [
        'discovery.oramap', 'agenda.oramap', 'behind-the-veil.oramap',
        'crossfire.oramap', 'doughnut.oramap', 'ardennes.oramap']),
    ('Red Alert Plus', 'raplus', WORK/'OpenRA-Upstreams/raplusmod/mods/raplus/maps', [
        'amsterdamned11', 'Black_Belt', 'belligerent', 'bayofbays']),
    ('Combined Arms', 'ca', WORK/'OpenRA-Upstreams/CAmod/mods/ca/maps', [
        'green-belt.oramap', 'outdoor-trails.oramap', 'haos-ridges.oramap', 'all-connected.oramap']),
]

def digest(data): return hashlib.sha256(data).hexdigest()
def field(text, key): return re.search(r'^'+key+r':\s*(.*)$', text, re.M)[1].strip()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    records, terrain_ids = [], set()
    for collection, prefix, folder, names in SOURCES:
        for name in names:
            source = folder/name
            if source.suffix == '.oramap':
                with zipfile.ZipFile(source) as package:
                    original = {key: package.read(key) for key in ['map.yaml','map.bin','map.png']}
            else:
                original = {key: (source/key).read_bytes() for key in ['map.yaml','map.bin','map.png']}
            yaml = original['map.yaml'].decode('utf-8-sig').replace('\r\n','\n')
            assert field(yaml,'Tileset') in ['TEMPERAT','SNOW','DESERT']
            assert 'MissionSelector' not in yaml
            assert not re.search(r'^\t(?:LuaScript|ScriptTriggers)', yaml, re.M), source
            for key in ['Rules','Sequences','Weapons','VoxelSequences']:
                assert not re.search('^'+key+r':[^\n\S]*\S+', yaml, re.M), f'{source}: external {key}'
            terrain_hash = digest(original['map.bin'])
            assert terrain_hash not in terrain_ids, f'{source}: duplicate layout'
            terrain_ids.add(terrain_hash)
            target_id = prefix+'-'+re.sub(r'[^a-z0-9]+','-',Path(name).stem.lower()).strip('-')
            text = re.sub(r'^RequiresMod:.*$', 'RequiresMod: rtsai-classic-core', yaml, count=1, flags=re.M)
            record = {'schema':1, 'id':target_id, 'title':field(yaml,'Title'), 'author':field(yaml,'Author'),
                'collection':collection, 'players':yaml.count('Playable: True'), 'tileset':field(yaml,'Tileset'),
                'source':source.relative_to(WORK).as_posix(), 'sourceYamlSha256':digest(yaml.encode('utf-8')),
                'terrainSha256':terrain_hash, 'adaptation':'RequiresMod only. Native Classic terrain, actors, resources, starts and gameplay rules preserved.',
                'scope':'Local Classic preview. Source authors retained; upstream collection files preserved in place.'}
            files = {**original, 'map.yaml':text.encode('utf-8')}
            record['files'] = {key:digest(value) for key,value in files.items()}
            files['provenance.json'] = (json.dumps(record,indent=2,ensure_ascii=False)+'\n').encode('utf-8')
            dest = ROOT/'resources/classic-web-maps'/target_id
            for key, data in files.items():
                if args.check:
                    actual = (dest/key).read_bytes()
                    if key.endswith(('.json','.yaml')): actual = actual.replace(b'\r\n',b'\n')
                    assert actual == data, dest/key
                else:
                    dest.mkdir(parents=True,exist_ok=True); (dest/key).write_bytes(data)
            records.append(record)
    data = (json.dumps({'schema':1,'maps':records},indent=2,ensure_ascii=False)+'\n').encode('utf-8')
    catalog = ROOT/'resources/classic-web-maps.json'
    if args.check: assert catalog.read_bytes().replace(b'\r\n',b'\n') == data
    else: catalog.write_bytes(data)
    print(f'{len(records)} native maps, {sum(r["players"] for r in records)} seats, three collections; terrain byte-identical; '+('verified' if args.check else 'installed'))

if __name__ == '__main__': main()
