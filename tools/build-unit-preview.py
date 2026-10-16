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
    run('git', '-C', game, 'fetch', 'origin', 'main')
    run('git', '-C', game, 'merge', '--ff-only', 'origin/main')
    host_commit = json.loads((seed / 'host/INPUTS.json').read_text())['head']
    rebuild_runtime = subprocess.run(['git', '-C', str(game), 'diff', '--quiet', host_commit, 'HEAD', '--', 'sim']).returncode != 0
    changed = git('diff', '--name-only', config['modCommit'], '--', 'OpenRA.Mods.RA2', 'OpenRA.Mods.RTSAI').splitlines()
    rebuild_runtime |= config['engineCommit'] != '8dfa3b12ea9039b1f23dcaf6d7e9e0d3405bdd28'
    rebuild_runtime |= any(not path.startswith('OpenRA.Mods.RTSAI/UtilityCommands/') for path in changed)
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
    runtime_source = seed / 'browser/runtime'
    if rebuild_runtime:
        host = out / 'host'
        run(sys.executable, ROOT / 'tools/build-inputs.py', 'snapshot', '--repo', game, '--out', host,
            '--include', 'sim', '--include', 'tools', '--include', 'Directory.Build.props', '--committed')
        host_commit = json.loads((host / 'INPUTS.json').read_text())['head']
        code = out / 'mod-code'
        if not code.exists():
            run(sys.executable, ROOT / 'tools/build-inputs.py', 'snapshot', '--repo', ROOT, '--out', code,
                '--include', 'OpenRA.Mods.RA2', '--include', 'OpenRA.Mods.RTSAI', '--committed')
        browser_engine = out / 'browser-engine'
        run(sys.executable, ROOT / 'tools/build-inputs.py', 'snapshot', '--repo', engine_source, '--out', browser_engine, '--committed')
        (browser_engine / 'VERSION').write_text(config['engineCommit'] + '\n')
        dotnet = Path.home() / '.dotnet/dotnet.exe' if os.name == 'nt' else 'dotnet'
        runtime_source = out / 'runtime'
        run(dotnet, 'publish', host / 'sim/OpenRA.WebSim.Browser/OpenRA.WebSim.Browser.csproj', '-c', 'Release',
            '--runtime', 'browser-wasm', '-p:DefineConstants=BROWSER', '-p:WebProfile=public',
            f'-p:EngineRoot={browser_engine.as_posix()}/', f'-p:ModRoot={code.as_posix()}/',
            f'-p:WebBuildRoot={(out / "browser-build").as_posix()}/', '-o', runtime_source)
        framework = runtime_source / 'wwwroot/_framework'
        run('node', game / 'tools/stamp-runtime.mjs', framework)
        run('node', game / 'tools/verify-runtime.mjs', framework)
    data = out / 'data'
    # The recovered Classic packer and the browser must use the same committed host.
    if not (out / 'host').exists():
        run(sys.executable, ROOT / 'tools/build-inputs.py', 'snapshot', '--repo', game, '--out', out / 'host',
            '--include', 'sim', '--include', 'tools', '--include', 'Directory.Build.props', '--committed')
    if not (out / 'mod-code').exists():
        run(sys.executable, ROOT / 'tools/build-inputs.py', 'snapshot', '--repo', ROOT, '--out', out / 'mod-code',
            '--include', 'OpenRA.Mods.RA2', '--include', 'OpenRA.Mods.RTSAI', '--committed')
    if not (out / 'browser-engine').exists():
        run(sys.executable, ROOT / 'tools/build-inputs.py', 'snapshot', '--repo', engine_source, '--out', out / 'browser-engine', '--committed')
    run('dotnet', 'build', out / 'host/sim/OpenRA.WebSim.Native/OpenRA.WebSim.Native.csproj', '-c', 'Release',
        '-p:WebProfile=public', f'-p:EngineRoot={(out / "browser-engine").as_posix()}/',
        f'-p:ModRoot={(out / "mod-code").as_posix()}/', f'-p:WebBuildRoot={(out / "native-host").as_posix()}/')
    runner = out / 'native-host/bin/OpenRA.WebSim.Native-public/Release/net10.0/websim.dll'
    for mode, profile, folder in [('isometric', 'public', 'isometric'), ('classic', 'public-classic', 'classic')]:
        seed_mode = seed / folder
        target = data / profile
        target.mkdir(parents=True)
        pack_mode = 'classic-core' if mode == 'classic' else mode
        run('dotnet', runner, 'pack', '--engine', seed_mode / 'work/engine', '--mod', snapshot,
            '--out', target / 'web-bundle.pack', '--content', seed_mode / 'content', '--no-mix-database',
            '--game-mode', pack_mode, '--support', config['supportDirectory'])
        scratch = out / f'vfs-{profile}'
        run('dotnet', runner, 'unpack', '--pack', target / 'web-bundle.pack', '--root', scratch)
        run('dotnet', runner, 'bake', '--root', scratch, '--maps', 'web-arena', '--out', target / 'sprites')
        link(runtime_source, target / 'wasm-interp')
        profile_data = json.loads((seed_mode / 'data' / profile / 'content-profile.json').read_text())
        profile_data.update(modSource=git('rev-parse', 'HEAD'), unitRevision=content['revision'])
        if mode == 'classic':
            profile_data.update(modId='rtsai-classic-core', localOnly=True, gameMode='classic', foundation='recovered-classic')
        unit.atomic(target / 'content-profile.json', json.dumps(profile_data, indent=2) + '\n')
    # Rebuild the current committed web interface; only the unchanged simulation runtime is reused.
    frontend = out / 'frontend'
    run(sys.executable, ROOT / 'tools/build-inputs.py', 'snapshot', '--repo', game, '--out', frontend, '--include', 'web', '--committed')
    link(game / 'web/node_modules', frontend / 'web/node_modules')
    run('node', game / 'tools/sync-catalog.mjs', '--from', web_root, '--out', frontend / 'web/src/data/factions.json')
    run('node', web_root / 'scripts/sync-shared-content.mjs', cwd=web_root)
    run('node', '--import', 'tsx', web_root / 'scripts/export-viewer-data.mts', frontend / 'web/public/viewer', cwd=web_root)
    run('node', game / 'web/node_modules/vite/bin/vite.js', 'build', '--outDir', out / 'web', cwd=frontend / 'web', env={**os.environ, 'RTSAI_SITE_ROOT': str(web_root)})
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    server_log = (out / 'web-server.log').open('w')
    server = subprocess.Popen(['node', str(game / 'server/serve.mjs')], cwd=game,
        env={**os.environ, 'RTSAI_WEBGAME_PORT': str(port), 'RTSAI_WEB_DATA': str(data), 'RTSAI_WEB_DIST': str(out / 'web'), 'RTSAI_WEB_SCRATCH': str(out / 'web-scratch')},
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
               'browserHostCommit': host_commit, 'browserFrontendCommit': json.loads((frontend / 'INPUTS.json').read_text())['head'],
               'scope': 'RA2 and recovered Classic desktop/web; all Studio roster units; installed Classic inputs remain local'}
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
