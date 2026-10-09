"""Deterministic compiler checks using original test geometry, without geographic networking."""
import importlib.util
import json
from pathlib import Path
import struct
import tempfile

spec=importlib.util.spec_from_file_location('earth',Path(__file__).with_name('earth-battlefield.py'))
earth=importlib.util.module_from_spec(spec);spec.loader.exec_module(earth)
request={'latitude':30.,'longitude':31.,'radius':2500,'size':48,'players':4,'seed':27,'title':'Compiler Test',
         'features':[{'kind':'river','closed':False,'points':[[29.97,31.],[30.03,31.]]},
                     {'kind':'road','closed':False,'points':[[30.,30.97],[30.,31.03]]}]}
with tempfile.TemporaryDirectory() as temp:
    a,b=Path(temp)/'test-a',Path(temp)/'test-b'
    report=earth.compile_map(request,a);earth.compile_map(request,b)
    assert (a/'map.bin').read_bytes()==(b/'map.bin').read_bytes(),'Same inputs must reproduce identical terrain'
    assert (a/'map.yaml').read_text().count('Playable: True')==4
    assert report['validation']['connectedBases'] and report['validation']['homeMines']==8
    raw=(a/'map.bin').read_bytes();version,w,h,*_=struct.unpack_from('<BHHIII',raw)
    assert (version,w,h)==(2,48,96) and len(raw)==17+w*h*6
    assert report['features']['river']==1 and len(report['paths'])==2
    bad={**request,'latitude':100}
    try:earth.compile_map(bad,Path(temp)/'bad')
    except ValueError:pass
    else:raise AssertionError('Invalid coordinates accepted')
    print('Earth compiler passed: deterministic terrain, 4 slots, connected base cells, 8 mines, valid binary and invalid-input rejection.')
