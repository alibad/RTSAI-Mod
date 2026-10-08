#!/usr/bin/env python3
"""Build the standalone rectangular Classic profile from shared modern-faction rules.

Both profiles use the same authored faction assets and companion contracts. Classic
has its own rectangular map grid, original square terrain and maps; it never mounts
an owned-content package. Historical Classic campaigns are retained separately.
"""
from pathlib import Path
import math
import random
import re
import struct
from PIL import Image
from PIL.PngImagePlugin import PngInfo

ROOT = Path(__file__).resolve().parents[1]
MODE = ROOT / 'mods/rtsai-topdown'


def text(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding='utf-8', newline='\n')


def terrain():
    # Procedural textures, generated directly into a new palette: no source game pixels.
    kinds = [('Clear', (78, 105, 51)), ('Water', (42, 80, 106)),
             ('Rough', (98, 99, 69)), ('DirtRoad', (122, 105, 74))]
    palette = [0, 0, 0] * 256
    for k, (_, base) in enumerate(kinds):
        for shade in range(32):
            palette[3*(2+k*32+shade):3*(3+k*32+shade)] = [max(0, min(255, c + shade - 16)) for c in base]
    (MODE/'terrain').mkdir(parents=True, exist_ok=True)
    (MODE/'terrain/terrain.pal').write_bytes(bytes(c//4 for c in palette))
    templates = []
    for k, (kind, _) in enumerate(kinds):
        rng = random.Random(2401+k)
        image = Image.new('P', (32, 32)); image.putpalette(palette)
        image.putdata([2+k*32+max(0, min(31, int(16+rng.gauss(0, 3)+2*math.sin(x/7)))) for y in range(32) for x in range(32)])
        metadata = PngInfo(); metadata.add_text('Frame[0]', '0,0,32,32;0,0')
        image.save(MODE/f'terrain/{k}.png', pnginfo=metadata)
        templates.append(f'\tTemplate@{k}:\n\t\tId: {k}\n\t\tImages: classic|terrain/{k}.png\n\t\tSize: 1,1\n\t\tTiles:\n\t\t\t0: {kind}\n')
    source = (ROOT/'mods/rtsai/standalone/tilesets/temperat.yaml').read_text(encoding='utf-8')
    definitions = source.split('Terrain:\n',1)[1].split('\nTemplates:',1)[0]
    text(MODE/'tileset.yaml', 'General:\n\tTileSize: 32,32\n\tName: tileset-temperate\n\tId: TEMPERATE\n\tExtensions: .png\n\tEnableDepth: false\n\nTerrain:\n'+definitions+'\nTemplates:\n'+''.join(templates))


def maps():
    for name, title, naval in [('classic-frontier','Classic Frontier',False),('classic-coast','Classic Coast',True)]:
        w=h=80; area=w*h; data=bytearray(17+area*6)
        struct.pack_into('<BHHIII',data,0,2,w,h,17,17+area*3,17+area*4)
        preview=Image.new('RGB',(w,h)); rng=random.Random(9271)
        homes=[(18,40),(61,40)];mines=[(18,30),(18,51),(61,30),(61,51)]
        for x in range(w):
            for y in range(h):
                water=naval and y<20
                k=1 if water else 3 if y in (39,40,41) else 2 if rng.random()<.09 else 0
                i=x*h+y;struct.pack_into('<HB',data,17+i*3,k,0)
                if not water and any(0<(x-mx)**2+(y-my)**2<20 for mx,my in mines):
                    struct.pack_into('<BB',data,17+area*4+i*2,1,12)
                preview.putpixel((x,y),[(78,105,51),(42,80,106),(98,99,69),(122,105,74)][k])
        players='\tPlayerReference@Neutral:\n\t\tName: Neutral\n\t\tOwnsWorld: True\n\t\tNonCombatant: True\n\t\tFaction: china\n\tPlayerReference@Creeps:\n\t\tName: Creeps\n\t\tNonCombatant: True\n\t\tFaction: china\n'
        for i in range(2):players+=f'\tPlayerReference@Multi{i}:\n\t\tName: Multi{i}\n\t\tPlayable: True\n\t\tFaction: Random\n\t\tEnemies: Creeps\n'
        actors=''
        for i,(x,y) in enumerate(homes):actors+=f'\tSpawn{i}: mpspawn\n\t\tOwner: Neutral\n\t\tLocation: {x},{y}\n'
        for i,(x,y) in enumerate(mines):actors+=f'\tMine{i}: oremine\n\t\tOwner: Neutral\n\t\tLocation: {x},{y}\n'
        directory=MODE/'maps'/name;directory.mkdir(parents=True,exist_ok=True)
        text(directory/'map.yaml',f'MapFormat: 12\nRequiresMod: rtsai-topdown\nTitle: {title}\nAuthor: RTS AI\nTileset: TEMPERATE\nMapSize: {w},{h}\nBounds: 1,1,78,78\nVisibility: Lobby\nCategories: Conquest\nPlayers:\n{players}Actors:\n{actors}')
        (directory/'map.bin').write_bytes(data);preview.save(directory/'map.png')
    import shutil
    shell=MODE/'maps/blank';shell.mkdir(parents=True,exist_ok=True)
    for filename in ['map.bin','map.png']:
        shutil.copyfile(MODE/'maps/classic-frontier'/filename,shell/filename)
    text(shell/'map.yaml',(MODE/'maps/classic-frontier/map.yaml').read_text(encoding='utf-8').replace('Title: Classic Frontier','Title: Classic Background').replace('Visibility: Lobby','Visibility: Shellmap'))


def manifest():
    source=(ROOT/'mods/rtsai/mod.yaml').read_text(encoding='utf-8')
    source=source.replace('\tTitle: mod-title','\tTitle: classic-mode-title').replace('\tWindowTitle: ra2-preview-window-title','\tWindowTitle: classic-mode-title')
    source=source.replace('\t\t$rtsai: ra2','\t\t$rtsai: ra2\n\t\t$rtsai-topdown: classic')
    source=re.sub(r'MapFolders:\n.*?(?=\nRules:)', 'MapFolders:\n\tclassic|campaigns/maps: System\n\tclassic|maps: System\n\t~^SupportDir|maps/rtsai-topdown/{DEV_VERSION}: User\n',source,flags=re.S)
    source=source.replace('\tra2|standalone/rules.yaml','\tra2|standalone/rules.yaml\n\tclassic|rules.yaml')
    source=source.replace('TileSets:\n\tra2|standalone/tilesets/temperat.yaml','TileSets:\n\tclassic|tileset.yaml')
    source=re.sub(r'MapGrid:\n.*?(?=\nMusic:)', 'MapGrid:\n\tType: Rectangular\n\tEnableDepthBuffer: false\n\tMaximumTerrainHeight: 0\n',source,flags=re.S)
    source=source.replace('FluentMessages:\n','FluentMessages:\n\tclassic|mode.ftl\n')
    text(MODE/'mod.yaml',source)
    text(MODE/'mode.ftl','classic-mode-title = RTS AI — Classic\n')
    rules='^Palettes:\n\tPaletteFromFile@terrain-temperate:\n\t\tFilename: classic|terrain/terrain.pal\n\n^SpriteActor:\n\tBodyOrientation:\n\t\tUseClassicPerspectiveFudge: true\n'
    for actor in sorted({match[1] for path in (ROOT/'mods/rtsai').rglob('*.yaml')
                         for match in re.finditer(r'^([^\s#][^:\n]*):[^\n]*\n((?:\t[^\n]*\n|\n)*)', path.read_text(encoding='utf-8'), re.M)
                         if '\n\tIsometricSelectable:' in '\n'+match[2]}):
        rules+=f'\n{actor}:\n\t-IsometricSelectable:\n\tSelectable:\n'
    rules+='\n^Building:\n\t-IsometricSelectionDecorations:\n\tSelectionDecorations:\n'
    # Rectangular cells require rectangular selection shapes instead of the isometric yaw.
    for shape in re.findall(r'^(\^\d+x\d+Shape):', (ROOT/'mods/rtsai/rules/defaults.yaml').read_text(encoding='utf-8'),re.M):
        rules+=f'\n{shape}:\n\tHitShape:\n\t\tType: Rectangle\n\t\t\tLocalYaw: 0\n'
    text(MODE/'rules.yaml',rules)


if __name__=='__main__':
    terrain();maps();manifest()
    print('Built standalone Classic profile, original terrain and two rectangular maps.')
