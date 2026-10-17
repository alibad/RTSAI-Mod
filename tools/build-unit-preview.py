#!/usr/bin/env python3
"""Freeze local unit edits into separate desktop/web previews. Never publishes or edits a running game."""
import argparse
from datetime import datetime, timezone
import importlib.util
import hashlib
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
    lock = ROOT / 'content/unit-preview.lock'
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    os.write(fd, str(os.getpid()).encode())
    os.close(fd)
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
    out = Path(os.environ.get('LOCALAPPDATA', str(Path.home() / '.cache'))) / 'RTSAI/StudioPreviews' / (datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-') + uuid.uuid4().hex[:8])
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
        result = subprocess.check_output([str(native / 'bin/OpenRA.Utility.exe'), mod, '--check-unit-modifications', 'all'],
                                        cwd=native, env={**os.environ, 'OPENRA_AI_HOST': '0', 'ENGINE_DIR': str(native),
                                                         'SUPPORT_DIR': config['supportDirectory'], 'MOD_SEARCH_PATHS': str(native / 'mods'), 'OPENRA_UTILITY_EXPERIENCE_PROFILE': 'world-war-iii'}, text=True, stderr=subprocess.STDOUT)
        receipts.append(json.loads(result))
    snapshot = native
    runtime_source = seed / 'browser/runtime'
    code_identity = hashlib.sha256((git('rev-parse', 'HEAD:OpenRA.Mods.RTSAI') + git('rev-parse', 'HEAD:OpenRA.Mods.RA2')).encode()).hexdigest()
    latest = web_root / '.cache/unit-runtime-latest.json'
    if latest.is_file():
        previous = json.loads(latest.read_text())
        previous_host = previous.get('browserHostCommit')
        runtime_changed = subprocess.run(['git', '-C', str(game), 'diff', '--quiet', previous_host or host_commit, 'HEAD', '--',
            'sim/OpenRA.WebSim', 'sim/OpenRA.WebSim.Browser', 'sim/OpenRA.Mods.RTSAI', 'sim/OpenRA.Mods.RA2']).returncode != 0
        candidate = Path(previous.get('runtime', str(seed / 'missing')))
        if previous.get('modCodeIdentity') == code_identity and previous.get('engineCommit') == config['engineCommit'] and previous_host and candidate.is_dir() and not runtime_changed:
            runtime_source, host_commit, rebuild_runtime = candidate, previous_host, False
    if rebuild_runtime:
        host = out / 'host'
        run(sys.executable, ROOT / 'tools/build-inputs.py', 'snapshot', '--repo', game, '--out', host,
            '--include', 'sim', '--include', 'tools', '--include', 'server', '--include', 'Directory.Build.props', '--committed')
        host_commit = json.loads((host / 'INPUTS.json').read_text())['head']
        code = out / 'mod-code'
        if not code.exists():
            run(sys.executable, ROOT / 'tools/build-inputs.py', 'snapshot', '--repo', ROOT, '--out', code,
                '--include', 'OpenRA.Mods.RA2', '--include', 'OpenRA.Mods.RTSAI', '--committed')
        browser_engine = out / 'browser-engine'
        run(sys.executable, ROOT / 'tools/build-inputs.py', 'engine', '--repo', engine_source, '--out', browser_engine, '--commit', config['engineCommit'])
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
        unit.atomic(latest, json.dumps({'modCodeIdentity': code_identity, 'engineCommit': config['engineCommit'], 'browserHostCommit': host_commit,
                    'runtime': str(runtime_source)}, indent=2) + '\n')
    data = out / 'data'
    # The recovered Classic packer and the browser must use the same committed host.
    if not (out / 'host').exists():
        run(sys.executable, ROOT / 'tools/build-inputs.py', 'snapshot', '--repo', game, '--out', out / 'host',
            '--include', 'sim', '--include', 'tools', '--include', 'server', '--include', 'Directory.Build.props', '--committed')
    if not (out / 'mod-code').exists():
        run(sys.executable, ROOT / 'tools/build-inputs.py', 'snapshot', '--repo', ROOT, '--out', out / 'mod-code',
            '--include', 'OpenRA.Mods.RA2', '--include', 'OpenRA.Mods.RTSAI', '--committed')
    if not (out / 'browser-engine').exists():
        run(sys.executable, ROOT / 'tools/build-inputs.py', 'engine', '--repo', engine_source, '--out', out / 'browser-engine', '--commit', config['engineCommit'])
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
        shutil.copytree(runtime_source, target / 'wasm-interp')
        profile_data = json.loads((seed_mode / 'data' / profile / 'content-profile.json').read_text())
        profile_data.update(modSource=git('rev-parse', 'HEAD'), unitRevision=content['revision'], modId='rtsai-classic-core' if mode == 'classic' else 'rtsai')
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
    names = ['RTSAI_WEBGAME_PORT', 'RTSAI_WEB_COMPANION_GRPC', 'RTSAI_WEB_COMPANION_PORT', 'RTSAI_WEB_MOCK_AI_PORT', 'RTSAI_WEB_LOCAL_AI_PORT']
    ports, reservations = {}, []
    for name in names:
        sock = socket.socket()
        sock.bind(('127.0.0.1', 0))
        ports[name] = str(sock.getsockname()[1])
        reservations.append(sock)
    port = int(ports['RTSAI_WEBGAME_PORT'])
    for sock in reservations:
        sock.close()
    # Freeze the host and bind all lazy asset reads to this build's immutable address.
    server_file = out / 'host/server/serve.mjs'
    build_id = 'studio-' + out.name
    web_url = f'http://127.0.0.1:{port}/local-builds/{build_id}/'
    receipt = {'schema': 2, 'buildId': build_id, 'revision': content['revision'], 'native': str(native),
               'support': config['supportDirectory'], 'webUrl': web_url, 'sourceCommit': git('rev-parse', 'HEAD'),
               'engineCommit': config['engineCommit'], 'nativeChecks': receipts, 'localOnly': True,
               'builtAt': datetime.now(timezone.utc).isoformat(), 'verified': False,
               'verifiedExperienceProfile': 'world-war-iii', 'serverFile': str(server_file),
               'runtime': str(runtime_source), 'browserHostCommit': host_commit,
               'browserFrontendCommit': json.loads((frontend / 'INPUTS.json').read_text())['head'],
               'scope': 'Classic and RA2 unit content on desktop/web; installed Classic inputs remain local'}
    receipt_file = out / 'receipt.json'
    unit.atomic(receipt_file, json.dumps(receipt, indent=2) + '\n')
    env = {**ports, 'RTSAI_WEB_DATA': str(data), 'RTSAI_WEB_DIST': str(out / 'web'),
           'RTSAI_WEB_SCRATCH': str(out / 'web-scratch'), 'RTSAI_WEB_BUILD': str(out / 'native-host'),
           'RTSAI_WEB_CLASSIC_MOD': 'rtsai-classic-core', 'RTSAI_WEB_SCENARIOS': str(game / 'scenarios'),
           'RTSAI_MAP_MOD_ROOT': str(ROOT), 'RTSAI_MAP_OUTPUT_ROOT': str(out / 'workshop-maps'),
           'RTSAI_SITE_PUBLIC': str(web_root / 'public'), 'RTSAI_OPENRA_AI': str(ROOT.parent / 'OpenRA-AI'),
           'RTSAI_CONTENT_RECEIPT': str(receipt_file),
           'RTSAI_CONTENT_SOURCE': str(ROOT / 'mods/rtsai/unit-overrides/manifest.json'),
           'RTSAI_VERIFIED_LOCAL_BUILD': json.dumps({'buildId': build_id, 'page': str(out / 'web'),
               'data': str(data), 'native': str(out / 'native-host'), 'scenarios': str(game / 'scenarios')})}
    unit.atomic(out / 'server-env.json', json.dumps(env, indent=2) + '\n')
    server_log = (out / 'web-server.log').open('w')
    server = subprocess.Popen(['node', str(server_file)], cwd=game, env={**os.environ, **env},
        stdout=server_log, stderr=server_log, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    import time
    import urllib.request
    try:
        for _ in range(60):
            try:
                urllib.request.urlopen(f'http://127.0.0.1:{port}/', timeout=2).close()
                break
            except OSError:
                if server.poll() is not None: raise ValueError('The frozen local server did not start.')
                time.sleep(.3)
        else: raise ValueError('The local preview server did not become ready.')
        check_spec = importlib.util.spec_from_file_location('verify_content_build', ROOT / 'tools/verify-content-build.py')
        verifier = importlib.util.module_from_spec(check_spec)
        check_spec.loader.exec_module(verifier)
        receipt['verification'] = verifier.verify(receipt, ROOT, out, log)
        if unit.compile_content(ROOT, check=True)['revision'] != content['revision']:
            raise ValueError('Content changed during acceptance. Saved edits are preserved; build again.')
        # These hashes are checked on ordinary local launches, not just during acceptance.
        paths = [*list((native / 'bin').glob('*.dll')), native / 'bin/OpenRA.exe',
                 native / 'mods/rtsai/unit-overrides/manifest.json', out / 'web/index.html', server_file]
        for profile in ['public', 'public-classic']:
            paths += [data / profile / 'web-bundle.pack', data / profile / 'content-profile.json']
            paths += list((data / profile / 'wasm-interp/wwwroot/_framework').glob('*.wasm'))
        receipt['checksums'] = [{'path': str(path), 'sha256': hashlib.file_digest(path.open('rb'), 'sha256').hexdigest()} for path in paths]
        receipt.update(verified=True, verifiedAt=datetime.now(timezone.utc).isoformat(), webPid=server.pid)
        unit.atomic(native / 'content-build.json', json.dumps({'revision': content['revision'], 'verified': True, 'buildId': build_id}) + '\n')
        unit.atomic(receipt_file, json.dumps(receipt, indent=2) + '\n')
        pointer = ROOT / '.recovery/content-current.json'
        if pointer.exists():
            unit.atomic(out / 'previous-pointer.json', pointer.read_text())
        unit.atomic(pointer, json.dumps({'receipt': str(receipt_file), 'sha256': hashlib.sha256(receipt_file.read_bytes()).hexdigest()}, indent=2) + '\n')
        unit.atomic(web_root / '.cache/unit-preview-latest.json', json.dumps(receipt, indent=2) + '\n')
        print(json.dumps({'buildId': build_id, 'revision': content['revision'], 'verified': True, 'webUrl': web_url}))
    except Exception:
        server.terminate()
        server.wait(timeout=15)
        raise



if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--web-root', type=Path, required=True)
    a = ap.parse_args()
    web = a.web_root.resolve()
    (web / '.cache').mkdir(exist_ok=True)
    lock = ROOT / 'content/unit-preview.lock'
    with (web / '.cache/unit-preview-build.log').open('w') as log:
        try:
            build(web, log)
        except Exception as error:
            if isinstance(error, subprocess.CalledProcessError) and error.output:
                print(error.output, file=log)
            print(str(error), file=log)
            print('Local preview build failed; see .cache/unit-preview-build.log', file=sys.stderr)
            sys.exit(1)
        finally:
            if lock.exists() and lock.read_text() == str(os.getpid()): lock.unlink()
