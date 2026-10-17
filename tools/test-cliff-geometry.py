"""Regression for cliff templates whose cells are all above their zero datum."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('terrain', ROOT/'tools/standalone-terrain.py')
terrain = importlib.util.module_from_spec(spec)
sys.modules['terrain'] = terrain
spec.loader.exec_module(terrain)
_, templates = terrain.parse_tileset(terrain.SRC_TILESET.read_text(encoding='utf-8'))
record = json.loads((terrain.OUT_DIR/'CLIFF-REPAIR.json').read_text())
assert hashlib.sha256((terrain.OUT_DIR/'temperate.pal').read_bytes()).hexdigest() == record['paletteSha256']
walls_checked = 0
for template in templates:
    if template.id not in record['templates']:
        continue
    *_, walls, skirts = terrain.template_geometry(template, 0, 0, seed=7)
    assert any(walls.values()), f'{template.id}: raised-only cliff has no exterior wall'
    image = Image.open(terrain.OUT_DIR/f't{template.id:04d}a.png')
    for index, edges in walls.items():
        if not edges:
            continue
        frame = image.info[f'Frame[{index}]']
        _, _, width, height = map(int, frame.split(';')[0].split(','))
        for side, top, bottom in edges:
            assert bottom.min() == 0, f'{template.id}/{index}: cliff floor remains raised'
            assert (top-bottom).max() >= 4, f'{template.id}/{index}: wall does not span the full cliff'
            assert height >= 90, f'{template.id}/{index}: exported frame clips the wall'
            walls_checked += 1
for item in record['files']:
    assert hashlib.sha256((terrain.OUT_DIR/item['file']).read_bytes()).hexdigest() == item['sha256']
print(f"PASS: {len(record['templates'])} templates, {walls_checked} exterior walls, {len(record['files'])} installed sheets; palette preserved")
