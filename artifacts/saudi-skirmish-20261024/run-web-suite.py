"""Full matches in the web host under CoreCLR. Check actual WASM separately with exported browser hashes."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('build', type=Path, help='Accepted shared build containing vfs-public/')
parser.add_argument('output', type=Path, help='New or resumable result directory')
parser.add_argument('--runner', type=Path, help='Override websim.dll (must support skirmishaudit --support)')
parser.add_argument('--replicates', type=int, default=3)
parser.add_argument('--parallel', type=int, default=2)
args = parser.parse_args()
runner = args.runner or args.build / 'native-host/bin/OpenRA.WebSim.Native-public/Release/net10.0/websim.dll'
root = args.build / 'vfs-public' if (args.build / 'vfs-public').is_dir() else args.build
args.output.mkdir(parents=True, exist_ok=True)

def run_case(case):
    profile, swap, replicate = case
    name = f'{profile}-saudi-spawn-{2 if swap else 1}-r{replicate}'
    result = args.output / (name + '.json')
    if result.exists():
        print(name, 'existing result retained', flush=True)
        return
    players = [dict(faction='saudi', bot='normal', color='2A6FDB'), dict(faction='iran', bot=profile, color='D83A2E')]
    if swap:
        players.reverse()
    for i, player in enumerate(players):
        player.update(slot=f'Multi{i}', spawn=i+1)
    scenario = dict(map='twin-fords', seed=4242 + replicate, players=players,
        options=dict(startingcash='5000', startingunits='medium', fog='True', explored='False', crates='False', shortgame='True', gamespeed='default'))
    scenario_file = args.output / (name + '-scenario.json')
    scenario_file.write_text(json.dumps(scenario))
    process = subprocess.run(['dotnet', str(runner), 'skirmishaudit', '--check-training', '--root', str(root),
        '--support', str(args.output / (name + '-support')), '--scenario', str(scenario_file),
        '--ticks', '60000', '--out', str(result)], capture_output=True, text=True, timeout=900)
    (args.output / (name + '.log')).write_text(process.stdout + process.stderr)
    print(name, process.returncode, process.stdout.strip()[-500:], flush=True)
    if process.returncode not in (0, 1) or not result.exists():
        raise RuntimeError(f'{name} failed; inspect its log')

if args.replicates < 1 or args.parallel < 1:
    parser.error('replicates and parallel must be positive')
cases = [(profile, swap, replicate) for replicate in range(args.replicates)
    for profile in ['medium', 'normal', 'rush'] for swap in [False, True]]
with ThreadPoolExecutor(max_workers=args.parallel) as pool:
    list(pool.map(run_case, cases))
