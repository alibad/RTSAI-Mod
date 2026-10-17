#!/usr/bin/env python3
"""Package original generated world sprites, preserving every compressed pixel byte.

Usage: python tools/editor-world-assets.py --rocks original-atlas.png --tech tech-states.png
PNG Frame metadata selects each object; native sequences set its scale and ground pivot.
No image is cropped, resized, recoloured or alpha-edited by this tool.
"""
import argparse
from collections import deque
import hashlib
import json
from pathlib import Path
import struct
import zlib
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]

def regions(path, columns, rows):
    image = Image.open(path)
    width, height = image.size
    mask = bytearray(a > 64 for a in image.getchannel('A').tobytes())
    found = []
    for p in range(width * height):
        if not mask[p]:
            continue
        mask[p] = 0
        queue = deque([p])
        count = 0
        left = right = p % width
        top = bottom = p // width
        while queue:
            at = queue.popleft()
            x, y = at % width, at // width
            count += 1
            left, right = min(left, x), max(right, x)
            top, bottom = min(top, y), max(bottom, y)
            for other in ([at-1] if x else []) + ([at+1] if x+1 < width else []) + ([at-width] if y else []) + ([at+width] if y+1 < height else []):
                if mask[other]:
                    mask[other] = 0
                    queue.append(other)
        if count > 500:
            found.append([left, top, right+1, bottom+1])
    assert len(found) == columns * rows, f'Expected {columns} × {rows} isolated sprites, found {len(found)}'
    # Group rows by vertical centers, then order each row left to right.
    found.sort(key=lambda b: (b[1]+b[3])/2)
    return [b for row in range(rows) for b in sorted(found[row*columns:(row+1)*columns], key=lambda b: b[0])]

def chunk(kind, payload):
    body = kind + payload
    return struct.pack('>I', len(payload)) + body + struct.pack('>I', zlib.crc32(body) & 0xffffffff)

def package(source, destination, columns, rows):
    original = source.read_bytes()
    assert original[-12:] == b'\0\0\0\0IEND\xaeB`\x82'
    frames, metadata = [], b''
    for i, (x0, y0, x1, y1) in enumerate(regions(source, columns, rows)):
        width, height = x1-x0, y1-y0
        offset = round(width/4-height/2, 2)
        metadata += chunk(b'tEXt', f'Frame[{i}]\0{x0},{y0},{width},{height};0,{offset}'.encode())
        frames.append({'region': [x0, y0, width, height], 'offset': [0, offset]})
    destination.write_bytes(original[:-12] + metadata + original[-12:])
    return {'source': source.name, 'sourceSha256': hashlib.sha256(original).hexdigest(),
            'sha256': hashlib.sha256(destination.read_bytes()).hexdigest(), 'frames': frames}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rocks', type=Path, required=True)
    parser.add_argument('--tech', type=Path, required=True)
    parser.add_argument('--out', type=Path, default=ROOT/'mods/rtsai/standalone/editor-world')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    atlases = {'rocks': package(args.rocks, args.out/'editor-rocks.png', 4, 4),
               'tech': package(args.tech, args.out/'editor-tech-states.png', 3, 5)}
    actors = {name: ('tech', i*3, width) for i, (name, width) in enumerate([
        ('caairp', 180), ('cahosp', 300), ('caoild', 120), ('caoutp', 210), ('cathosp', 300)])}
    actors.update({f'srock{i+1:02}': ('rocks', 5+i, width) for i, width in enumerate([38,48,58,52,50])})
    actors.update({f'trock{i+1:02}': ('rocks', 10+i, width) for i, width in enumerate([42,54,66,60,52])})
    removals = {'caairp': ['WithIdleOverlay@decoration'], 'cahosp': ['WithIdleOverlay'],
                'caoild': ['WithIdleOverlay@pump'], 'caoutp': ['WithIdleOverlay@tower',
                'WithIdleOverlay@tower-shadow', 'WithIdleOverlay@bib', 'WithVoxelTurret', 'RenderVoxels']}
    sequences = ['# Original generated artwork. PNG frame metadata preserves source pixels.']
    rules = ['# Rendering-only overrides. Native capture, economy, repair and combat traits are preserved.']
    for actor, (atlas, index, target) in actors.items():
        image = f'editor-world-{actor}'
        rules += [f'\n{actor}:', '\tRenderSprites:', f'\t\tImage: {image}']
        rules += [f'\t-{trait}:' for trait in removals.get(actor, [])]
        sequences += [f'\n{image}:']
        states = [('idle', index)]
        if atlas == 'tech':
            states += [('damaged-idle', index+1), ('rubble', index+2)]
            if actor == 'caoutp':
                states += [('active-crane', index), ('damaged-active-crane', index+1)]
        for sequence, frame in states:
            scale = target/atlases[atlas]['frames'][frame]['region'][2]
            sequences += [f'\t{sequence}:', f'\t\tFilename: ra2|standalone/editor-world/editor-{ "tech-states" if atlas == "tech" else "rocks" }.png',
                          f'\t\tStart: {frame}', '\t\tLength: 1', '\t\tShadowStart: -1', f'\t\tScale: {scale:.6f}', '\t\tZRamp: 1']
        if atlas == 'tech':
            sequences += ['\tflag:', '\t\tFilename: ra2|standalone/art/rallypoint-flag.png', '\t\tLength: 10', '\t\tShadowStart: -1', '\t\tOffset: 0, -16, 16']
            if actor != 'cathosp':
                rules += [f'\n{actor}.rubble:', '\tRenderSprites:', f'\t\tImage: {image}']
    (args.out/'sequences.yaml').write_text('\n'.join(sequences)+'\n', encoding='utf-8')
    (args.out/'rules.yaml').write_text('\n'.join(rules)+'\n', encoding='utf-8')
    (args.out/'PROVENANCE.json').write_text(json.dumps({
        'origin': 'Original assets generated for RTS AI using OpenAI image_gen on 2026-10-17. No source-game pixels.',
        'packaging': 'PNG frame metadata only. Original IDAT bytes are preserved verbatim.',
        'actors': actors, 'atlases': atlases, 'unusedRockAtlasFrames': [0,1,2,3,4,15],
        'limitations': ['Outpost turret and resupply crane are static artwork; native combat and repair logic remains.'],
    }, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'actors': len(actors), 'out': str(args.out)}))

if __name__ == '__main__':
    main()
