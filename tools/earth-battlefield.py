"""Compile geographic evidence into standalone isometric skirmishes. No source-game assets.

Uses the canonical project's corner-transition terrain compiler. Water/roads/land
cover follow evidence; base zones, routes and resources are deliberate gameplay edits.
Input/output paths are supplied by the local web adapter, never derived from titles.
"""
import argparse
import collections
import importlib.util
import json
import math
from pathlib import Path
import re
import zipfile
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('standalone_maps', ROOT/'tools/standalone-maps.py')
maps = importlib.util.module_from_spec(spec)
spec.loader.exec_module(maps)

def compile_map(request, output):
    lat, lon = float(request['latitude']), float(request['longitude'])
    radius = int(request.get('radius', 2500))
    seed = int(request.get('seed', 42))
    size = int(request.get('size', 64))
    seats = int(request.get('players', 2))
    if not (-85 <= lat <= 85 and -180 <= lon <= 180 and 500 <= radius <= 10000
            and size in (48, 64, 80) and seats in (2, 4) and 0 <= seed <= 2147483647):
        raise ValueError('Invalid geographic selection or battlefield settings')
    features = request.get('features', [])
    if not features:
        raise ValueError('No geographic features were returned; choose another area')
    if len(features) > 12000:
        raise ValueError('This area is too dense; select a smaller radius')
    title = re.sub(r'[\r\n:]', ' ', str(request.get('title', 'Earth Battlefield')))[:80].strip() or 'Earth Battlefield'
    mb = maps.MapBuilder(size, size*2)
    P = np.stack([mb.px, mb.py], -1)
    mb.paint(maps.smooth_noise(mb.px,mb.py,seed,12)>0.65,'rough')
    counts = collections.Counter()
    paths = []
    # North-up evidence fits the same physical square as the isometric MPos rectangle.
    for feature in features:
        points = feature.get('points', [])
        if len(points) < 2 or len(points) > 10000:
            continue
        kind = feature.get('kind', '')
        xy = np.array([[(float(p[1])-lon)*111320*math.cos(math.radians(lat)),
                        (lat-float(p[0]))*111320] for p in points])
        xy = (xy/(2*radius)+.5)*size*2
        xy[:, 1] /= 2
        counts[kind] += 1
        paths.append({'kind':kind,'points':(xy/[size*2,size]).round(5).tolist(),
                      'closed':bool(feature.get('closed'))})
        if kind in ('water','forest','urban','rough','sand') and feature.get('closed'):
            # Ray casting on the corner grid; no plotting dependency.
            inside = np.zeros(mb.px.shape, bool)
            for a,b in zip(xy, np.roll(xy,-1,axis=0)):
                if abs(b[1]-a[1]) < 1e-9: continue
                inside ^= ((a[1]>mb.py)!=(b[1]>mb.py)) & (mb.px < (b[0]-a[0])*(mb.py-a[1])/(b[1]-a[1])+a[0])
            mb.paint(inside, {'forest':'rough','urban':'dirt'}.get(kind,kind))
        elif kind in ('river','water','road','local-road','dry-river','rail'):
            width = 1.3 if kind in ('river','water') else .8
            mask = maps.poly_dist(P, xy) < width
            mb.paint(mask, 'water' if kind in ('river','water') else 'dirt')
        elif kind == 'building':
            center = xy.mean(axis=0)
            mb.paint(np.hypot((mb.px-center[0])/2,mb.py-center[1]) < .8,'rough')
    homes = [(int(size*.23),int(size*.65)),(int(size*.77),int(size*1.35))]
    if seats == 4: homes += [(int(size*.77),int(size*.65)),(int(size*.23),int(size*1.35))]
    home_p = [np.array([2*u,v/2]) for u,v in homes]
    center = np.array([size,size/2])
    for home in home_p:
        mb.paint(np.hypot((mb.px-home[0])/2,mb.py-home[1]) < 9,'grass')
        mb.paint(maps.road_mask(P,home,center,2.1),'dirt')
    # Keep border corners on land: avoids half-water cells outside bounds.
    mb.paint((mb.px<3)|(mb.px>size*2-3)|(mb.py<2)|(mb.py>size-2),'grass')
    resources, mines = {}, []
    for home in home_p:
        for offset in ([10,-5],[-10,5]):
            point = home+offset
            mb.paint(np.hypot((mb.px-point[0])/2,mb.py-point[1])<5,'grass')
            maps.field(resources,mb,point,4.0,1)
            mines.append(maps.cell_at(mb,point))
    maps.field(resources,mb,center,3.5,2)
    tiles = mb.tiles()
    terrain,_ = maps.terrain_types()
    def legal(cell):
        return 1 <= cell[0] < mb.w-1 and 1 <= cell[1] < mb.h-1 and terrain[tiles[cell][0]][0] in ('Clear','Road','Rough','DirtRoad')
    # Validate conservatively against the actual tile classes after transitions.
    starts = [min((c for c in tiles if legal(c)), key=lambda c:(c[0]-u)**2+(c[1]-v)**2) for u,v in homes]
    seen={starts[0]}; queue=collections.deque(seen)
    while queue:
        u,v=queue.popleft()
        # Cardinal MPos adjacency is a conservative connected-route check.
        for cell in ((u-1,v),(u+1,v),(u,v-1),(u,v+1)):
            if cell not in seen and legal(cell): seen.add(cell);queue.append(cell)
    if any(s not in seen for s in starts): raise ValueError('Generated routes are disconnected; change the seed or location')
    output.mkdir(parents=True,exist_ok=True)
    old = maps.MAPS
    maps.MAPS=output.parent
    try:
        maps.write_map(output.name,title,mb,[maps.mpos_to_cpos(*s) for s in starts],resources,'Earth-inspired skirmish',mines)
    finally: maps.MAPS=old
    if seats == 4:
        yaml=(output/'map.yaml').read_text()
        # write_map's terrain/resource compiler is shared, extend its player definitions.
        extra=''
        for k in (2,3): extra+=f'\tPlayerReference@Multi{k}:\n\t\tName: Multi{k}\n\t\tPlayable: True\n\t\tFaction: Random\n\t\tEnemies: Creeps\n'
        yaml=yaml.replace('\nActors:', '\n'+extra+'\nActors:').replace('Enemies: Multi0, Multi1','Enemies: Multi0, Multi1, Multi2, Multi3')
        (output/'map.yaml').write_text(yaml)
    yaml=(output/'map.yaml').read_text()
    yaml=yaml.replace('Author: RTS AI (generated by tools/standalone-maps.py)', 'Author: RTS AI; geography © OpenStreetMap contributors (ODbL)')
    (output/'map.yaml').write_text(yaml,encoding='utf-8')
    report={'id':output.name,'title':title,'players':seats,'seed':seed,'latitude':lat,'longitude':lon,'radius':radius,
            'size':size,'features':dict(counts),'paths':paths,'source':'OpenStreetMap','license':'ODbL-1.0',
            'attribution':'© OpenStreetMap contributors','sourceStatus':request.get('sourceStatus','Preserved geographic evidence'),
            'validation':{'connectedBases':True,'clearBaseZones':True,'homeMines':len(mines),'reachableCells':len(seen)},
            'adaptations':['Flat terrain; land cover simplified to project terrain.',
                          'Base zones cleared, ground corridors added, balanced home ore supplied.',
                          'Building footprints become rough ground; no real buildings or elevation are reproduced.',
                          'Open coastlines are shown in evidence but do not infer an unbounded sea polygon.']}
    (output/'earth.json').write_text(json.dumps(report,indent=2))
    with zipfile.ZipFile(output/'map.oramap','w',zipfile.ZIP_DEFLATED) as package:
        for name in ('map.yaml','map.bin','map.png','earth.json'):
            package.write(output/name,name)
    return report

if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--request',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();compile_map(json.loads(args.request.read_text()),args.output)
