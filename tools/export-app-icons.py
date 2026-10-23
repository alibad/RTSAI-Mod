"""Export the owner's approved Command Red artwork without regenerating or repainting it.

Inputs are the four square masters under packaging/artwork/command-red/. The first
export extracted exact selected tiles from the approved 3x2 atlases; provenance.json
records those sources and hashes. Run from the canonical checkout to refresh all
four app identities. No production deployment or installed-browser cache is touched.
"""
from pathlib import Path
import base64
import json
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
GAMES = ROOT.parent
ART = ROOT / 'packaging/artwork'
MASTERS = ART / 'command-red'
BACKGROUND = '#151719'
SIZES = (16, 24, 32, 48, 64, 128, 256, 512, 1024)


def export(app, target):
    target.mkdir(parents=True, exist_ok=True)
    with Image.open(MASTERS / f'{app}.png') as image:
        master = image.convert('RGB')
    for size in SIZES:
        master.resize((size, size), Image.Resampling.LANCZOS).save(target / f'icon_{size}x{size}.png', optimize=True)
    for name, size in [('icon-192.png', 192), ('icon-512.png', 512), ('apple-touch-icon.png', 180), ('favicon-32.png', 32), ('favicon-64.png', 64)]:
        master.resize((size, size), Image.Resampling.LANCZOS).save(target / name, optimize=True)
    # Keep the complete approved artwork within the guaranteed circular safe area.
    maskable = Image.new('RGB', (512, 512), BACKGROUND)
    maskable.paste(master.resize((288, 288), Image.Resampling.LANCZOS), (112, 112))
    maskable.save(target / 'icon-maskable-512.png', optimize=True)
    master.resize((256, 256), Image.Resampling.LANCZOS).save(target / 'favicon.ico', sizes=[(s, s) for s in SIZES if s <= 256])
    return target


def copy(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(source.read_bytes())


def main():
    output = MASTERS / 'exports'
    sets = {app: export(app, output / app) for app in ('desktop', 'studio', 'website', 'webgame')}
    web = GAMES / 'RTSAI-Web/public'
    game = GAMES / 'RTSAI-WebGame/web/public'
    common = ('icon-192.png', 'icon-512.png', 'icon-maskable-512.png', 'apple-touch-icon.png', 'favicon-32.png', 'favicon-64.png', 'favicon.ico')
    for app, target in [('website', web), ('studio', web / 'brand/faction-studio'), ('webgame', game)]:
        for name in common:
            copy(sets[app] / name, target / name)
    # Direct favicon.svg requests and the visible website brand use the approved mark too.
    encoded = base64.b64encode((sets['website'] / 'favicon-64.png').read_bytes()).decode()
    (web / 'favicon.svg').write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><image width="64" height="64" href="data:image/png;base64,{encoded}"/></svg>\n')
    for name in ('rtsai-app-icon.png',):
        copy(sets['website'] / 'icon-512.png', web / 'brand' / name)
    copy(sets['website'] / 'favicon-64.png', web / 'brand/rtsai-mark-64.png')
    for size in SIZES:
        copy(sets['desktop'] / f'icon_{size}x{size}.png', ART / f'icon_{size}x{size}.png')
    copy(sets['desktop'] / 'favicon.ico', ART / 'rtsai.ico')
    for mod in ('rtsai', 'rtsai-classic-core', 'rtsai-library', 'rtsai-ra2', 'rtsai-topdown'):
        copy(sets['desktop'] / 'icon_32x32.png', ROOT / 'mods' / mod / 'icon.png')
    print(json.dumps({'theme': 'Command Red', 'selection': [2, 5, 3, 1], 'exports': {k: str(v) for k, v in sets.items()}}, indent=2))


if __name__ == '__main__':
    main()
