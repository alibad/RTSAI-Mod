#!/usr/bin/env python3
"""Freeze local unit edits into separate desktop/web previews. Never publishes or edits a running game."""
import argparse
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]


def link(source, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if os.name == 'nt':
        subprocess.run(['cmd', '/c', 'mklink', '/J', str(dest), str(source)], check=True, capture_output=True)
    else:
        dest.symlink_to(source, target_is_directory=True)


def build(web_root, log):
    def run(*args, **kw):
        subprocess.run(list(map(str, args)), check=True, stdout=log, stderr=log, **kw)
    def git(*args):
        return subprocess.check_output(['git', '-C', str(ROOT), *args], text=True).strip()
    engine_source = ROOT.parent / 'OpenRA'
    for repo, remote in [(ROOT, 'origin'), (engine_source, 'fork')]:
        run('git', '-C', repo, 'fetch', remote, 'main')
        run('git', '-C', repo, 'merge', '--ff-only', f'{remote}/main')
    spec = importlib.util.spec_from_file_location('unit_content', ROOT / 'tools/unit-content.py')
    unit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(unit)
    content = unit.compile_content(ROOT, check=True)
    config = json.loads((ROOT / 'recovery.local.json').read_text(encoding='utf-8-sig'))
    runtime = Path(config['engineDirectory'])
    # A unit edit can reuse verified binaries; engine/mod source changes require the normal canonical build.
    diff = git('diff', config['modCommit'], '--', 'OpenRA.Mods.RA2', 'OpenRA.Mods.RTSAI')
    if git('diff', 'HEAD', '--', 'OpenRA.Mods.RA2', 'OpenRA.Mods.RTSAI'):
        raise ValueError('Commit native source changes before building a preview.')
    if subprocess.check_output(['git', '-C', str(engine_source), 'rev-parse', 'HEAD'], text=True).strip() != config['engineCommit']:
        raise ValueError('Rebuild the canonical desktop runtime for the current engine first.')
    game = ROOT.parent / 'RTSAI-WebGame'
    seed = game / 'build/shared-content-pilot-20261016'
    if not (seed / 'browser/runtime/dotnet.js').is_file():
        # Runtime layout can vary by .NET version; a manifest is sufficient to locate the existing verified runtime.
        if not (seed / 'browser/runtime').is_dir():
            raise ValueError('The verified local browser runtime is missing. Restore it before building unit previews.')
    out = ROOT.parent / 'artifacts/unit-studio-previews' / (datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-') + uuid.uuid4().hex[:8])
    out.mkdir(parents=True)
    native = out / 'native'
    native.mkdir()
    shutil.copytree(runtime / 'bin', native / 'bin')
    for name in ['glsl', 'mods/common', 'mods/common-content']:
        link(runtime / name, native / name)
    for name in ['VERSION', 'global mix database.dat', 'AUTHORS', 'COPYING']:
        if (runtime / name).is_file():
            shutil.copy2(runtime / name, native / name)
    for mod in (ROOT / 'mods').iterdir():
        if mod.is_dir():
            shutil.copytree(mod, native / 'mods' / mod.name)
    if diff:
        code = out / 'mod-code'
        run(sys.executable, ROOT / 'tools/build-inputs.py', 'snapshot', '--repo', ROOT,
            '--out', code, '--include', 'OpenRA.Mods.RA2', '--include', 'OpenRA.Mods.RTSAI', '--committed')
        for project in ['OpenRA.Mods.RA2', 'OpenRA.Mods.RTSAI']:
            run('dotnet', 'build', code / project / f'{project}.csproj', '-c', 'Release', '--nologo', '-v:q',
                f'-p:EngineRootPath={engine_source}', f'-p:OutputPath={native / "bin"}')
    if json.loads((native / 'mods/rtsai/unit-overrides/manifest.json').read_text())['revision'] != content['revision']:
        raise ValueError('Content changed during the preview snapshot; build again.')
    receipts = []
    for mod in ['rtsai-classic-core', 'rtsai-ra2']:
        result = subprocess.check_output([str(native / 'bin/OpenRA.Utility.exe'), mod, '--check-unit-modifications'],
                                        cwd=native, env={**os.environ, 'OPENRA_AI_HOST': '0', 'ENGINE_DIR': str(native),
                                                         'SUPPORT_DIR': config['supportDirectory'], 'MOD_SEARCH_PATHS': str(native / 'mods')}, text=True)
        receipts.append(json.loads(result))
    snapshot = out / 'mod'
    snapshot.mkdir()
    link(native / 'mods', snapshot / 'mods')
    data = out / 'data'
    for mode, profile, folder in [('isometric', 'public', 'isometric'), ('classic', 'public-classic', 'classic')]:
        seed_mode = seed / folder
        runner = seed_mode / 'bin/OpenRA.WebSim.Native-public/Release/net10.0/websim.dll'
        target = data / profile
        target.mkdir(parents=True)
        run('dotnet', runner, 'pack', '--engine', seed_mode / 'work/engine', '--mod', snapshot,
            '--out', target / 'web-bundle.pack', '--content', seed_mode / 'content', '--no-mix-database', '--game-mode', mode)
        scratch = out / f'vfs-{profile}'
        run('dotnet', runner, 'unpack', '--pack', target / 'web-bundle.pack', '--root', scratch)
        run('dotnet', runner, 'bake', '--root', scratch, '--maps', 'web-arena', '--out', target / 'sprites')
        link(seed / 'browser/runtime', target / 'wasm-interp')
        shutil.copy2(seed_mode / 'data' / profile / 'content-profile.json', target / 'content-profile.json')
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    server_log = (out / 'web-server.log').open('w')
    server = subprocess.Popen(['node', str(game / 'server/serve.mjs')], cwd=game,
        env={**os.environ, 'RTSAI_WEBGAME_PORT': str(port), 'RTSAI_WEB_DATA': str(data), 'RTSAI_WEB_DIST': str(seed / 'web'), 'RTSAI_WEB_SCRATCH': str(out / 'web-scratch')},
        stdout=server_log, stderr=server_log, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    import time
    import urllib.request
    for _ in range(30):
        try:
            urllib.request.urlopen(f'http://127.0.0.1:{port}/', timeout=1).close()
            break
        except OSError:
            if server.poll() is not None:
                raise ValueError('The local web preview server did not start.')
            time.sleep(.2)
    else:
        raise ValueError('The local web preview server did not become ready.')
    receipt = {'revision': content['revision'], 'native': str(native), 'support': config['supportDirectory'],
               'webUrl': f'http://127.0.0.1:{port}/', 'webPid': server.pid, 'sourceCommit': git('rev-parse', 'HEAD'),
               'engineCommit': config['engineCommit'], 'nativeChecks': receipts, 'localOnly': True,
               'scope': 'RA2 desktop/web; Classic desktop and explicitly mapped web adapter units only'}
    unit.atomic(out / 'receipt.json', json.dumps(receipt, indent=2) + '\n')
    unit.atomic(web_root / '.cache/unit-preview-latest.json', json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--web-root', type=Path, required=True)
    a = ap.parse_args()
    web = a.web_root.resolve()
    (web / '.cache').mkdir(exist_ok=True)
    with (web / '.cache/unit-preview-build.log').open('w') as log:
        try:
            build(web, log)
        except Exception as error:
            print(str(error), file=log)
            print('Local preview build failed; see .cache/unit-preview-build.log', file=sys.stderr)
            sys.exit(1)
