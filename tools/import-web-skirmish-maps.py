#!/usr/bin/env python3
"""Restore reviewed RA2 skirmish layouts with the project's compatible terrain.

No conversion of terrain, heights, resources, positions, bridges or actors. Only
the mod id and the ore drills' rendering change. Keep upstream authors and source
hashes. Snow/urban maps and maps with unfinished scenery are deliberately excluded.
Run from any directory; --check verifies the installed files without writing.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
MAPS = {
    'little-big-lake': 'Two elevated starting areas around a central lake.',
    'tournament-2B': 'Two-player tournament battlefield with repairable river crossings.',
    'tsunami': 'Four islands: build a navy or use amphibious transports.',
    'valley-of-gems': 'Four starting areas, rich gem expansions and wooded approaches.',
    'defcon-6': 'Six-player battlefield with distinct plateaus and contested expansions.',
    'a-path-beyond-2': 'Eight-player land and sea battlefield with elevated crossings.',
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    records = []
    for name, description in MAPS.items():
        source = ROOT / 'mods/rtsai-classic/maps' / name
        target = ROOT / 'mods/rtsai/standalone/maps' / ('ra2-' + name)
        original = (source / 'map.yaml').read_bytes()
        terrain = (source / 'map.bin').read_bytes()
        text = original.decode('utf-8-sig').replace('\r\n', '\n')
        assert 'Tileset: TEMPERATE' in text and 'RequiresMod: ra2' in text
        text = text.replace('RequiresMod: ra2', 'RequiresMod: rtsai')
        # These actors already inherit exactly the same ^OreDrill mechanics as
        # oremine. Override rendering only, preserving identities and footprints.
        assert '\nRules:' in text
        for drill in sorted(set(re.findall(r'^\t\w+: (tibtre0[123])$', text, re.M))):
            text = text.rstrip() + f'\n\t{drill.upper()}:\n\t\tRenderSprites:\n\t\t\tImage: oremine\n'
        files = {'map.yaml': text.encode('utf-8'), 'map.bin': terrain}
        # The original preview remains a faithful layout overview. Native QA
        # writes a separate engine-rendered preview for comparison.
        files['map.png'] = (source / 'map.png').read_bytes()
        record = {
            'schema': 1, 'id': target.name,
            'title': re.search(r'^Title: (.*)$', text, re.M)[1],
            'author': re.search(r'^Author: (.*)$', text, re.M)[1],
            'players': len(re.findall(r'Playable: True', text)),
            'description': description,
            'collection': 'Red Alert 2',
            'source': source.relative_to(ROOT).as_posix(),
            'upstream': 'https://github.com/OpenRA/ra2/tree/61e24e3c1d7b586aa55a86096d29e1559aa9b994/mods/ra2/maps/' + name,
            'sourceYamlSha256': sha(original.decode('utf-8-sig').replace('\r\n', '\n').encode('utf-8')), 'sourceTerrainSha256': sha(terrain),
            'yamlHashEncoding': 'UTF-8 without BOM, LF line endings',
            'adaptation': 'RequiresMod changed to rtsai; ore drill RenderSprites.Image uses project oremine artwork. Terrain, heights, resources, actors, starting locations and map rules preserved.',
            'contentNotice': 'Westwood map layout from the existing OpenRA RA2 port. Project terrain and scenery; no original game archives or installation required. Upstream repository: GPL-3.0; original map authorship retained. Local integration is not a publication authorization.',
            'files': {key: sha(data) for key, data in files.items()},
        }
        files['provenance.json'] = (json.dumps(record, indent=2, ensure_ascii=False) + '\n').encode('utf-8')
        for filename, data in files.items():
            path = target / filename
            if args.check:
                actual = path.read_bytes()
                if filename.endswith(('.yaml', '.json')):
                    actual = actual.replace(b'\r\n', b'\n')
                assert actual == data, f'{path}: differs from reviewed source adapter'
            else:
                target.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
        records.append(record)
    catalog = ROOT / 'resources/web-skirmish-maps.json'
    data = (json.dumps({'schema': 1, 'maps': records}, indent=2, ensure_ascii=False) + '\n').encode('utf-8')
    if args.check:
        assert catalog.read_bytes().replace(b'\r\n', b'\n') == data, 'Catalog differs from map provenance'
    else:
        catalog.write_bytes(data)
    print(f'{len(records)} reviewed maps; terrain byte-identical; 2/4/6/8-player coverage; ' + ('verified' if args.check else 'installed'))


if __name__ == '__main__':
    main()
