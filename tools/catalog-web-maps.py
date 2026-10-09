"""Index local map sources without modifying or activating unresolved content.

The only automatic mode ports are the two original maps made by build-classic-mode.py.
All other maps retain their source path, content hash and explicit review/port status.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import struct
import zipfile
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT.parent
spec=importlib.util.spec_from_file_location('standalone_maps',ROOT/'tools/standalone-maps.py')
maps=importlib.util.module_from_spec(spec);spec.loader.exec_module(maps)

def value(text,key,default=''):
    m=re.search(r'^'+re.escape(key)+r':\s*(.*)$',text,re.M)
    return m.group(1).strip() if m else default

def classic_ports():
    for name in ('classic-coast','classic-frontier'):
        src=ROOT/'mods/rtsai-topdown/maps'/name
        data=(src/'map.bin').read_bytes();_,w,h,offset,_,resoff=struct.unpack_from('<BHHIII',data)
        mb=maps.MapBuilder(w,h*2)
        # Preserve north-up layout and double MPos rows for the isometric cell proportions.
        gx=np.clip((mb.px/2).astype(int),0,w-1);gy=np.clip(mb.py.astype(int),0,h-1)
        kinds=np.empty((h,w),dtype=object)
        for u in range(w):
            for v in range(h):
                tid,_=struct.unpack_from('<HB',data,offset+3*(u*h+v))
                kinds[v,u]=('grass','water','rough','dirt')[tid]
        mb.cls=kinds[gy,gx]
        text=(src/'map.yaml').read_text()
        points=re.findall(r'\t(\w+): (mpspawn|oremine)\n\t\tOwner: Neutral\n\t\tLocation: (\d+),(\d+)',text)
        spawns=[maps.mpos_to_cpos(int(x),int(y)*2) for _,kind,x,y in points if kind=='mpspawn']
        mines=[maps.mpos_to_cpos(int(x),int(y)*2) for _,kind,x,y in points if kind=='oremine']
        resources={}
        for u in range(w):
            for v in range(h):
                kind,density=struct.unpack_from('<BB',data,resoff+2*(u*h+v))
                if kind:
                    for row in (v*2,v*2+1):resources[maps.mpos_to_cpos(u,row)]=(kind,density)
        old=maps.MAPS;maps.MAPS=ROOT/'resources/web-maps'
        try:maps.write_map('port-'+name,value(text,'Title')+' · Isometric',mb,spawns,resources,'Original Classic map adapted to isometric terrain',mines)
        finally:maps.MAPS=old
        dest=ROOT/'resources/web-maps'/('port-'+name)
        (dest/'provenance.json').write_text(json.dumps({'source':str(src.relative_to(ROOT)),'generator':'tools/build-classic-mode.py',
            'adaptation':'Original rectangular layout translated to project isometric terrain. Original retained.',
            'license':'Project-authored; see repository license'},indent=2))

def catalog():
    sources=[]
    repositories=['RTSAI-Mod','RTSAI-Mod-wt-web-public','RTSAI-Mod-wt-art-preview','OpenRA','OpenRA-wt-rtsai-engine','OpenRA-AI','OpenRA-AI/engine/openra','OpenRA-AI-wt-ra2-red-sea','RTSAI-WebGame']
    repositories += ['OpenRA-Upstreams/'+p.name for p in (WORK/'OpenRA-Upstreams').iterdir() if p.is_dir()]
    for repo in repositories:
        base=WORK/repo
        for folder in ('mods','missions','generated/missions','content/maps'):
            root=base/folder
            if root.exists():
                sources.extend((repo,p) for p in root.rglob('map.yaml'))
                sources.extend((repo,p) for p in root.rglob('*.oramap'))
    entries=[]
    for repo,p in sources:
        try:
            if p.suffix=='.oramap':
                with zipfile.ZipFile(p) as z:text=z.read('map.yaml').decode('utf-8-sig');data=z.read('map.bin')
            else:text=p.read_text(encoding='utf-8-sig');data=p.with_name('map.bin').read_bytes()
        except (OSError,ValueError,KeyError,zipfile.BadZipFile):continue
        rel=p.relative_to(WORK).as_posix()
        original=(repo=='RTSAI-Mod' and ('/standalone/maps/' in rel or '/rtsai-topdown/maps/classic-' in rel)) or (repo=='RTSAI-WebGame' and p.parent.name=='four-fronts')
        isometric='/standalone/maps/' in rel or (repo=='RTSAI-WebGame' and p.parent.name=='four-fronts')
        status='compatible' if original and isometric else 'ported' if original else 'review-required'
        reason='Project terrain and actors' if status=='compatible' else 'Original Classic layout; isometric adaptation available' if status=='ported' else 'Needs provenance, terrain/actor and scripting compatibility review'
        entries.append({'id':hashlib.sha256((text+data.hex()).encode()).hexdigest()[:20],'folder':p.parent.name,
            'title':value(text,'Title',p.parent.name),'author':value(text,'Author','Unknown'),
            'mod':value(text,'RequiresMod'),'tileset':value(text,'Tileset'),'size':value(text,'MapSize'),
            'players':len(re.findall(r'Playable: [Tt]rue',text)),'visibility':value(text,'Visibility'),
            'source':rel,'status':status,'reason':reason,'preview':p.with_name('map.png').exists() if p.suffix!='.oramap' else False})
    grouped={}
    for e in entries:
        if e['id'] not in grouped:grouped[e['id']]={**e,'copies':[e['source']]}
        else:grouped[e['id']]['copies'].append(e['source'])
    result={'maps':sorted(grouped.values(),key=lambda e:(e['status'],e['title'])),'sourceCopies':len(entries),
        'note':'Indexed sources are preserved in place. Review-required maps are not advertised as integrated.'}
    dest=ROOT/'resources/map-library.json';dest.write_text(json.dumps(result,indent=2));print(f'{len(grouped)} unique maps, {len(entries)} source copies indexed')

if __name__=='__main__':
    classic_ports();catalog()
