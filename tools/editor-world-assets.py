#!/usr/bin/env python3
"""Package original generated world sprites, preserving every compressed pixel byte.

Usage: python tools/editor-world-assets.py --rocks original-atlas.png --tech tech-states.png
       python tools/editor-world-assets.py   (no sources: re-derive the small rock sheet and the yaml from the packaged atlases)
PNG Frame metadata selects each object; native sequences set its scale and ground pivot.
The packaged atlases are never cropped, resized, recoloured or alpha-edited by this tool.

The rocks are drawn at about a sixth of their atlas size, and the browser renderer samples sprite sheets with NEAREST,
which turns that minification into pixel noise. So a second sheet, editor-rocks-small.png, holds Lanczos-resampled
copies of the ten rock frames at exactly their drawn size (pivot scaled with them), and the rock sequences read it at
scale 1 with no ZRamp: a rock stands upright, it is not a ground decal, so tree canopies must not overdraw its top.
"""
import argparse
from collections import deque
import hashlib
import json
from pathlib import Path
import struct
import zlib
from PIL import Image, PngImagePlugin

ROOT = Path(__file__).resolve().parents[1]

def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

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
            'sha256': sha256(destination), 'frames': frames}

def frames_of(path):
    """The frame regions and pivots a packaged atlas carries in its PNG Frame metadata."""
    text, frames = Image.open(path).text, []
    while f'Frame[{len(frames)}]' in text:
        region, offset = text[f'Frame[{len(frames)}]'].split(';')
        frames.append({'region': [int(v) for v in region.split(',')], 'offset': [float(v) if '.' in v else int(v) for v in offset.split(',')]})
    return frames

def write(path, text):
    path.write_text(text, encoding='utf-8', newline='\n')

def shrink(atlas, destination, picks, pad=2, per_row=5):
    """Resample the picked atlas frames (index, drawn width) to their drawn size into a small sheet.

    Lanczos on premultiplied alpha keeps the silhouette clean (no dark fringe); each frame's pivot is scaled with it,
    so a sequence reading the small sheet at scale 1 draws the rock where the atlas frame at Scale drawn/width stood.
    """
    image, frames, tiles = Image.open(atlas).convert('RGBA'), frames_of(atlas), []
    for index, target in picks:
        x, y, width, height = frames[index]['region']
        scale = target / width
        tile = image.crop((x, y, x+width, y+height)).convert('RGBa').resize((target, max(1, round(height*scale))), Image.LANCZOS)
        tiles.append((tile.convert('RGBA'), [round(v*scale, 2) for v in frames[index]['offset']]))
    rows = [tiles[i:i+per_row] for i in range(0, len(tiles), per_row)]
    sheet = Image.new('RGBA', (max(sum(t.width+pad for t, _ in row) for row in rows) + pad,
                               sum(max(t.height for t, _ in row) + pad for row in rows) + pad), (0, 0, 0, 0))
    info, placed, y = PngImagePlugin.PngInfo(), [], pad
    for row in rows:
        x = pad
        for tile, offset in row:
            sheet.paste(tile, (x, y))
            info.add_text(f'Frame[{len(placed)}]', f'{x},{y},{tile.width},{tile.height};{offset[0]:g},{offset[1]:g}')
            placed.append({'region': [x, y, tile.width, tile.height], 'offset': offset})
            x += tile.width + pad
        y += max(t.height for t, _ in row) + pad
    sheet.save(destination, pnginfo=info)
    return {'source': atlas.name, 'sourceSha256': sha256(atlas), 'sha256': sha256(destination),
            'resample': 'LANCZOS on premultiplied alpha, one frame per (atlas frame, drawn width)', 'picks': picks, 'frames': placed}

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--rocks', type=Path, help='original rock atlas to package (together with --tech)')
    parser.add_argument('--tech', type=Path, help='original tech-building atlas to package (together with --rocks)')
    parser.add_argument('--out', type=Path, default=ROOT/'mods/rtsai/standalone/editor-world')
    args = parser.parse_args()
    if bool(args.rocks) != bool(args.tech):
        parser.error('--rocks and --tech go together; pass neither to re-derive from the packaged atlases')
    args.out.mkdir(parents=True, exist_ok=True)
    if args.rocks:
        atlases = {'rocks': package(args.rocks, args.out/'editor-rocks.png', 4, 4),
                   'tech': package(args.tech, args.out/'editor-tech-states.png', 3, 5)}
    else:
        atlases = json.loads((args.out/'PROVENANCE.json').read_text(encoding='utf-8'))['atlases']
        for name, file in (('rocks', 'editor-rocks.png'), ('tech', 'editor-tech-states.png')):
            assert atlases[name]['sha256'] == sha256(args.out/file), f'{file} is not the atlas PROVENANCE.json records; package it again with --rocks/--tech'
            atlases[name]['frames'] = frames_of(args.out/file)
    actors = {name: ('tech', i*3, width) for i, (name, width) in enumerate([
        ('caairp', 180), ('cahosp', 300), ('caoild', 120), ('caoutp', 210), ('cathosp', 300)])}
    actors.update({f'srock{i+1:02}': ('rocks', 5+i, width) for i, width in enumerate([38,48,58,52,50])})
    actors.update({f'trock{i+1:02}': ('rocks', 10+i, width) for i, width in enumerate([42,54,66,60,52])})
    rocks = [[index, width] for atlas, index, width in actors.values() if atlas == 'rocks']
    atlases['rocks-small'] = shrink(args.out/'editor-rocks.png', args.out/'editor-rocks-small.png', rocks)
    removals = {'caairp': ['WithIdleOverlay@decoration'], 'cahosp': ['WithIdleOverlay'],
                'caoild': ['WithIdleOverlay@pump'], 'caoutp': ['WithIdleOverlay@tower',
                'WithIdleOverlay@tower-shadow', 'WithIdleOverlay@bib', 'WithVoxelTurret', 'RenderVoxels']}
    sequences = ['# Original generated artwork. PNG frame metadata preserves source pixels.',
                 '# Rocks read editor-rocks-small.png: the atlas frames resampled to their drawn size (see tools/editor-world-assets.py).']
    rules = ['# Rendering-only overrides. Native capture, economy, repair and combat traits are preserved.']
    for actor, (atlas, index, target) in actors.items():
        image = f'editor-world-{actor}'
        key = actor.upper() if atlas == 'rocks' else actor
        rules += [f'\n{key}:', '\tRenderSprites:', f'\t\tImage: {image}']
        rules += [f'\t-{trait}:' for trait in removals.get(actor, [])]
        sequences += [f'\n{image}:']
        if atlas == 'rocks':
            # Drawn 1:1 from the small sheet; no ZRamp, so the rock keeps the depth of its base like other upright scenery.
            sequences += ['\tidle:', '\t\tFilename: ra2|standalone/editor-world/editor-rocks-small.png',
                          f'\t\tStart: {rocks.index([index, target])}', '\t\tLength: 1', '\t\tShadowStart: -1']
            continue
        states = [('idle', index), ('damaged-idle', index+1), ('rubble', index+2)]
        if actor == 'caoutp':
            states += [('active-crane', index), ('damaged-active-crane', index+1)]
        for sequence, frame in states:
            scale = target/atlases[atlas]['frames'][frame]['region'][2]
            sequences += [f'\t{sequence}:', '\t\tFilename: ra2|standalone/editor-world/editor-tech-states.png',
                          f'\t\tStart: {frame}', '\t\tLength: 1', '\t\tShadowStart: -1', f'\t\tScale: {scale:.6f}', '\t\tZRamp: 1']
        sequences += ['\tflag:', '\t\tFilename: ra2|standalone/art/rallypoint-flag.png', '\t\tLength: 10', '\t\tShadowStart: -1', '\t\tOffset: 0, -16, 16']
        if actor != 'cathosp':
            rules += [f'\n{actor}.rubble:', '\tRenderSprites:', f'\t\tImage: {image}']
    write(args.out/'sequences.yaml', '\n'.join(sequences)+'\n')
    write(args.out/'rules.yaml', '\n'.join(rules)+'\n')
    write(args.out/'PROVENANCE.json', json.dumps({
        'origin': 'Original assets generated for RTS AI using OpenAI image_gen on 2026-10-17. No source-game pixels.',
        'packaging': 'PNG frame metadata only. Original IDAT bytes are preserved verbatim. '
                     'editor-rocks-small.png is derived from editor-rocks.png: its rock frames resampled to their drawn size.',
        'actors': actors, 'atlases': atlases, 'unusedRockAtlasFrames': [0,1,2,3,4,15],
        'limitations': ['Outpost turret and resupply crane are static artwork; native combat and repair logic remains.'],
    }, indent=2)+'\n')
    print(json.dumps({'actors': len(actors), 'rocksSmall': atlases['rocks-small']['frames'], 'out': str(args.out)}))

if __name__ == '__main__':
    main()
