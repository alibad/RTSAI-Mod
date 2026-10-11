import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--engine', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    engine = args.engine.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    spec = importlib.util.spec_from_file_location('balance', ROOT / 'tools/balance-harness.py')
    balance = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = balance
    spec.loader.exec_module(balance)
    project = ROOT / 'OpenRA.Mods.RTSAI/OpenRA.Mods.RTSAI.csproj'
    original = project.read_text()
    if (ROOT / '.git').exists() or not (ROOT / 'BUILD-INPUTS.json').exists():
        raise ValueError('Probe compilation requires a verified private build copy without Git metadata')
    include = '\n<ItemGroup><Compile Include="../tools/native-observation-probe/Probe.cs" /></ItemGroup>\n'
    project.write_text(original.replace('</Project>', include + '</Project>'))
    env = {k: v for k, v in os.environ.items() if not k.startswith(('OPENRA_AI_', 'RTSAI_'))}
    try:
        with (output / 'build.log').open('w') as log:
            subprocess.run(['dotnet', 'build', str(project), '-c', 'Release', '-p:EngineRootPath=' + str(engine),
                            '-p:TargetPlatform=osx-arm64'], env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
        results = []
        for mode in ['rtsai', 'rtsai-topdown']:
            balance.MOD = mode
            resources = balance.prepare_resources(output / mode, ROOT / 'mods')
            for disabled in [False, True]:
                case = output / mode / ('disabled' if disabled else 'baseline')
                support = case / 'support'
                target = support / balance.user_map_dir(resources / mode) / 'observation-probe'
                shutil.copytree(ROOT / 'mods' / mode / 'campaigns/maps/jizan-corridor', target)
                text = (target / 'map.yaml').read_text()
                text = text.replace('\nRules:\n\tWorld:\n', '\nRules:\n\tWorld:\n\t\tNativeObservationProbe:\n\t\t\tDisableBasePower: ' + str(disabled) + '\n', 1)
                if disabled:
                    text = text.replace('\nFluentMessages:', '\n\tgarefn:\n\t\tPower:\n\t\t\tRequiresCondition: observation-probe-never\n\nFluentMessages:', 1)
                (target / 'map.yaml').write_text(text)
                command = ['dotnet', str(engine / 'bin/OpenRA.dll'), 'Engine.EngineDir=' + str(engine),
                           f'Engine.ModSearchPaths={resources},{engine / "mods"}', 'Engine.SupportDir=' + str(support),
                           'Game.Mod=' + mode, 'Game.Platform=Null', 'Game.FetchNews=false', 'Sound.Mute=true',
                           'Launch.Map=observation-probe']
                with (case / 'game.log').open('w') as log:
                    process = subprocess.Popen(command, cwd=engine / 'bin', env=env, stdout=log, stderr=subprocess.STDOUT)
                    try:
                        code = process.wait(timeout=45)
                    except subprocess.TimeoutExpired:
                        process.kill(); process.wait(); raise RuntimeError('Probe timed out')
                lines = (case / 'game.log').read_text().splitlines()
                reports = [json.loads(line.split('|', 1)[1]) for line in lines if line.startswith('NATIVE_OBSERVATION_PROBE|')]
                if code != 0 or len(reports) != 1 or not reports[0]['passed']:
                    raise RuntimeError(f'Probe failed: {mode} disabled={disabled}; see {case / "game.log"}')
                reports[0]['command'] = command
                results.append(reports[0])
                print(json.dumps(reports[0]), flush=True)
        (output / 'receipt.json').write_text(json.dumps({'passed': True, 'cases': results,
            'testOnlyTransform': 'Compile probe trait in private Mod assembly and add private map rule; never shipped'}, indent=2) + '\n')
    finally:
        project.write_text(original)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
