"""Replay an actual browser-exported match; require every browser tick hash and length to match."""
import argparse
import json
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('build', type=Path)
parser.add_argument('record', type=Path)
parser.add_argument('output', type=Path)
parser.add_argument('--runner', type=Path, required=True, help='websim.dll supporting run --outcome')
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
record = json.loads(args.record.read_text(encoding='utf-8-sig'))
(args.output / 'browser-record.json').write_text(json.dumps(record))
(args.output / 'scenario.json').write_text(json.dumps(record['scenario']))
(args.output / 'browser-log.json').write_text(json.dumps(record['log']))
command = ['dotnet', str(args.runner), 'run', '--root', str(args.build / 'vfs-public'),
    '--scenario', str(args.output / 'scenario.json'), '--replay', str(args.output / 'browser-log.json'),
    '--ticks', str(len(record['log']['hashes'])), '--hashes', str(args.output / 'native.hashes'),
    '--outcome', str(args.output / 'outcome.json')]
process = subprocess.run(command, capture_output=True, text=True, timeout=300)
(args.output / 'native.log').write_text(process.stdout + process.stderr)
if process.returncode:
    raise RuntimeError(process.stderr[-2000:])
native = [int(line.split()[1]) for line in (args.output / 'native.hashes').read_text().splitlines()]
browser = record['log']['hashes']
first = next((i+1 for i, (a, b) in enumerate(zip(browser, native)) if a != b), None)
outcome = json.loads((args.output / 'outcome.json').read_text())
report = dict(match=bool(browser) and len(browser) == len(native) and first is None,
    browserTicks=len(browser), nativeTicks=len(native), firstMismatch=first,
    runtime=record['log']['runtime'], outcome=outcome,
    completed=any(player['win'] == 'Won' for player in outcome['players']))
(args.output / 'verification.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report))
raise SystemExit(0 if report['match'] else 1)
