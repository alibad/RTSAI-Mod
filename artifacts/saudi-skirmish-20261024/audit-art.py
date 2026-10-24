"""Read-only Saudi art inventory, exact native/web comparison and extracted contact sheet."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from PIL import Image, ImageDraw

build = Path(sys.argv[1])
output = Path('D:/RTSAI-SaudiSkirmish-20261024/art')
output.mkdir(parents=True, exist_ok=True)
native = build / 'native/mods/rtsai'
web = build / 'vfs-public/mods/rtsai'
units = ['r2m1a2s', 'r2bradley', 'r2caesar', 'r2sads', 'r2sang', 'r2saat', 'r2sajtac', 'r2falcon']
roster = json.loads(Path('D:/RTSAI-SaudiSkirmish-20261024/web-roster.json').read_text())['rosters']['saudi']
inventory = []
for source in native.rglob('*'):
    if not source.is_file() or source.suffix not in ('.shp', '.pal', '.png'):
        continue
    if source.stem not in roster and 'saudi' not in source.name:
        continue
    relative = source.relative_to(native)
    counterpart = web / relative
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    inventory.append({'file': relative.as_posix(), 'sha256': digest,
        'matches': counterpart.is_file() and hashlib.sha256(counterpart.read_bytes()).hexdigest() == digest})

sheet = Image.new('RGB', (1000, 8 * 150), '#151719')
draw = ImageDraw.Draw(sheet)
env = dict(os.environ, ENGINE_DIR=str(build / 'native'), DOTNET_ROLL_FORWARD='Major')
for row, unit in enumerate(units):
    infantry = row >= 4
    category = 'infantry' if infantry else 'vehicles'
    pal = native / 'modern-factions' / category / (unit + '.pal' if infantry else 'saudi-prerender.pal')
    dest = output / unit
    dest.mkdir(exist_ok=True)
    shutil.copy2(native / 'modern-factions' / category / (unit + '.shp'), dest / (unit + '.shp'))
    subprocess.run([str(build / 'native/bin/OpenRA.Utility.exe'), 'rtsai', '--png', './' + unit + '.shp', str(pal), '--noshadow'], cwd=dest, env=env, check=True, capture_output=True)
    frames = sorted(dest.glob(unit + '-*.png'))
    draw.text((12, row * 150 + 8), f'{unit}  |  {len(frames)} frames', fill='#F5EFE4')
    icon = Image.open(native / 'modern-factions/icons' / (unit + '.png')).convert('RGBA')
    sheet.paste(icon.resize((128, 96), Image.Resampling.NEAREST), (12, row * 150 + 35), icon.resize((128, 96), Image.Resampling.NEAREST))
    for i, direction in enumerate([0, 8, 16, 24] if not infantry else [0, 2, 4, 6]):
        frame_index = direction * 8 if unit == 'r2sads' else direction
        frame = Image.open(frames[frame_index]).convert('RGBA')
        if unit in ('r2m1a2s', 'r2bradley', 'r2sads'):
            turret_index = (512 if unit == 'r2sads' else 64) + direction
            frame = Image.alpha_composite(frame, Image.open(frames[turret_index]).convert('RGBA'))
        frame = frame.resize((frame.width * 2, frame.height * 2), Image.Resampling.NEAREST)
        x, y = 165 + i * 210, row * 150 + 30
        sheet.paste(frame, (x, y), frame)
sheet.save(output / 'saudi-roster-sheet.png')
report = {'build': str(build), 'filesCompared': len(inventory), 'mismatches': [i for i in inventory if not i['matches']], 'files': inventory}
(output / 'asset-parity.json').write_text(json.dumps(report, indent=2))
print(json.dumps({'filesCompared': len(inventory), 'mismatches': report['mismatches']}))
sys.exit(bool(report['mismatches']))
