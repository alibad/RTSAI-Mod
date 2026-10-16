#!/usr/bin/env python3
"""Import the preserved local orchestral take; archive the rejected master and retain exact source provenance."""
import hashlib
import importlib.util
import json
import shutil
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
AUDIO=ROOT/'mods/rtsai/standalone/audio'
SOURCE=ROOT/'resources/music-sources/final-push-orchestral-20261014'
ARCHIVE=ROOT/'resources/music-archive/final-push-techno-20261007'
TAKE='20261014-150725-text2music-629497889-epic-finale-cinematic-game-score-full-or'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')

def main():
    origin=Path('C:/Users/Admin/Code/AI/betenshi-console/generated-music')
    master=AUDIO/'music/rtsai-final-push.ogg'
    prov=json.loads((AUDIO/'PROVENANCE.json').read_text(encoding='utf-8'))
    old=prov['files']['music/rtsai-final-push.ogg']
    if not ARCHIVE.exists():
        assert sha(master)==old['sha256']
        ARCHIVE.mkdir(parents=True)
        shutil.copy2(master,ARCHIVE/'rtsai-final-push.ogg')
        write(ARCHIVE/'PROVENANCE.json',old)
        (ARCHIVE/'README.md').write_text('Rejected by the owner on 16 October 2026 for its abrasive acid bass and alarm-like lead. Preserved master and original provenance; excluded from the shipped playlist. Original raw take was in an external temporary cache and is not present here; its hash remains in the provenance.\n')
    SOURCE.mkdir(parents=True,exist_ok=True)
    for ext in ['flac','json']:
        target=SOURCE/('source.'+ext)
        if not target.exists():shutil.copy2(origin/(TAKE+'.'+ext),target)
    meta=json.loads((SOURCE/'source.json').read_text())
    assert meta['instrumental'] and meta['meta']['dit']=='acestep-v15-xl-turbo'
    spec=importlib.util.spec_from_file_location('music',ROOT/'tools/standalone-music.py')
    music=importlib.util.module_from_spec(spec);spec.loader.exec_module(music)
    seed=meta['meta']['seed']
    with tempfile.TemporaryDirectory(prefix='rtsai-final-push-') as temp:
        cache=Path(temp)
        stem=f'rtsai-final-push.seed{seed}'
        shutil.copy2(SOURCE/'source.flac',cache/(stem+'.flac'))
        write(cache/(stem+'.json'),dict(request=dict(task='text2music',caption=meta['caption'],instrumental='true',duration=str(meta['requestedDuration']),seed=str(seed),bpm=str(meta['meta']['resolved']['bpm']),keyscale=meta['meta']['resolved']['keyscale'],timesignature='4',format='flac'),reply=meta['meta'],generated=meta['savedAt'][:10],service=dict(model='ace-step-1.5',dit=meta['meta']['dit'],lm=meta['meta']['lm'])))
        class Args:only=['rtsai-final-push']
        args=Args();args.cache=temp
        music.master(args)
    current=json.loads((AUDIO/'PROVENANCE.json').read_text(encoding='utf-8'))
    entry=current['files']['music/rtsai-final-push.ogg']
    entry.update(source_metadata='resources/music-sources/final-push-orchestral-20261014/source.json',source_audio='resources/music-sources/final-push-orchestral-20261014/source.flac',replaced='2026-10-16',replacement_reason='Owner rejected abrasive acid bass and alarm leads; use the preserved warm orchestral instrumental.',model='ACE-Step/acestep-v15-xl-turbo DiT + acestep-5Hz-lm-1.7B planner; precision/offload flags were not recorded in the source sidecar',notes='Locally generated instrumental, reused from the preserved 14 October finale cue. No third-party recording was imported. Old master archived under resources/music-archive/final-push-techno-20261007.')
    (AUDIO/'PROVENANCE.json').write_text(json.dumps(current,indent=1,ensure_ascii=False,sort_keys=True)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:entry[k] for k in ['title','seed','generated','sha256','mastering']},indent=2))

if __name__=='__main__':main()
