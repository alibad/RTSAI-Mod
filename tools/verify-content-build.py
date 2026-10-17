"""Acceptance for one frozen local content build. No edits to canonical content."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

def verify(receipt, root, out, log):
    native = Path(receipt['native'])
    proofs = []
    config = out / 'receipt.json'
    for mode, actor, cost in [('classic', 'e6', None), ('ra2', 'engineer', None)]:
        result = subprocess.check_output([sys.executable, str(root / 'tools/stage-shared-content-proof.py'),
            '--runtime-config', str(config), '--out', str(out / 'acceptance'), '--mode', mode, '--no-hud'], text=True)
        stage = json.loads(result)
        args = stage['args'] + ['Game.Platform=Null', 'Sound.Engine=Null']
        process = subprocess.Popen(args, cwd=native, env={**os.environ, 'OPENRA_AI_HOST': '0'}, stdout=log, stderr=log)
        lua = Path(stage['support']) / 'Logs/lua.log'
        try:
            deadline = time.monotonic() + 90
            text = ''
            while time.monotonic() < deadline:
                if lua.exists(): text = lua.read_text(encoding='utf-8-sig')
                if 'SHARED_PRODUCTION|' in text: break
                if process.poll() is not None: raise ValueError(f'{mode} native proof exited before producing a unit')
                time.sleep(.3)
            loaded = re.search(r'SHARED_CONTENT\|[^|]+\|([^|]+)\|cost\|(\d+)\|before\|(\d+)', text)
            trained = re.search(r'SHARED_PRODUCTION\|[^|]+\|trained\|(\d+)\|spent\|(\d+)', text)
            if not loaded or not trained or loaded[1] != receipt['revision'] or trained[1] != '1' or loaded[2] != trained[2]:
                raise ValueError(f'{mode} native production did not match its frozen content revision; see {lua}')
            proofs.append({'mode': mode, 'actor': actor, 'revision': loaded[1], 'cost': int(loaded[2]), 'spent': int(trained[2]), 'passed': True, 'log': str(lua)})
        finally:
            if process.poll() is None: process.terminate()
            process.wait(timeout=15)
    game = root.parent / 'RTSAI-WebGame'
    subprocess.run(['node', str(game / 'tools/classic-studio-browser-test.mjs')], cwd=game,
        env={**os.environ, 'RTSAI_TEST_URL': receipt['webUrl'], 'RTSAI_TEST_OUT': str(out / 'acceptance')}, stdout=log, stderr=log, check=True)
    browser = json.loads((out / 'acceptance/browser-receipt.json').read_text())
    if not browser['passed'] or browser['revision'] != receipt['revision']:
        raise ValueError('Browser acceptance revision mismatch')
    return {'passed': True, 'revision': receipt['revision'], 'nativeProduction': proofs,
            'browser': str(out / 'acceptance/browser-receipt.json'),
            'targets': ['classic-desktop', 'classic-web', 'ra2-desktop', 'ra2-web'],
            'scope': 'All bound unit stats; native Engineer production in each mode; browser stock/custom Classic and RA2 production. Not full campaign or UI parity.'}
