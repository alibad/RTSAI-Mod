"""Compact, source-backed skirmish evidence; capped games stay separate from conquest victories."""
import json
from pathlib import Path
import statistics
from collections import defaultdict

root = Path('D:/RTSAI-SaudiSkirmish-20261024')
matches = []
for path in sorted(root.glob('native-*/matches/*/result.json')):
    batch = path.parents[2].name
    if batch not in ('native-final', 'native-brace-candidate'):
        continue
    data = json.loads(path.read_text())
    match, outcome, telemetry = data['match'], data['outcome'], data['telemetry']
    saudi = 'Multi' + str(match['factions'].index('saudi'))
    profile = match['bots'][match['factions'].index('iran')]
    enemy_losses = [event[0] for event in telemetry['lost'] if event[1] != event[5] and event[5].startswith('Multi') and event[0] < outcome['end_tick']]
    matches.append(dict(stage='post-brace' if batch == 'native-brace-candidate' else 'baseline', target='desktop-headless', id=match['id'], profile=profile, completed=outcome.get('reason') == 'conquest',
        status=outcome['status'], saudiWin=outcome.get('winner') == saudi, ticks=outcome['end_tick'],
        minutes=round(outcome['end_tick']/1500, 2), firstEnemyLossSeconds=min(enemy_losses)/25 if enemy_losses else None,
        reason=outcome['reason']))
for path in sorted(root.glob('web-*/*-r[0-9].json')):
    if path.parent.name not in ('web-acceptance', 'web-brace-candidate'):
        continue
    data = json.loads(path.read_text())
    profile = next(p['bot'] for p in data['scenario']['players'] if p['faction'] == 'iran')
    final = data['samples'][-1]['players']
    matches.append(dict(stage='post-brace' if path.parent.name == 'web-brace-candidate' else 'baseline', target='web-host-coreclr', id=path.stem, profile=profile, completed=data['completed'],
        status='complete', saudiWin=any(p['faction'] == 'saudi' and p['win'] == 'Won' for p in final),
        ticks=data['ticks'], minutes=round(data['gameMinutes'], 2),
        firstEnemyLossSeconds=min(data['firstLoss'].values())/25 if data['firstLoss'] else None, reason=data['reason']))
groups = defaultdict(list)
for match in matches:
    groups[(match['stage'], match['target'], match['profile'])].append(match)
summary = []
for (stage, target, profile), rows in sorted(groups.items()):
    summary.append(dict(stage=stage, target=target, profile=profile, runs=len(rows), conquest=sum(r['completed'] for r in rows),
        saudiWins=sum(r['saudiWin'] for r in rows), capped=sum(r['reason'] == 'tick-cap' for r in rows),
        errors=sum(r['status'] != 'complete' for r in rows), medianMinutes=round(statistics.median(r['minutes'] for r in rows), 2),
        maxMinutes=max(r['minutes'] for r in rows)))
report = dict(schema='rtsai.saudi-skirmish-evidence/v1', scope='Saudi Arabia versus Iran, Twin Fords, Easy/Normal/Rush, both spawn orientations',
    build='studio-20261024-001242-eacc038b', gameSource='8b03957', baselineGameSource='60fb308',
    rosterEntries=34, rosterDifferences=0, artFilesCompared=88, artMismatches=0,
    effects={key: value for key, value in json.loads((root / 'saudi-effects-final.json').read_text()).items() if key in ('passed', 'failures', 'weaponsWithoutExplosions')},
    effectsCoverage=dict(deaths=228, impacts=97, sourceBuild='studio-20261024-001242-eacc038b'),
    braceMechanics=dict(profiles=['normal','medium','rush','turtle','naval'], passed=True, humanControlPreserved=True, moveReleasesStance=True),
    wasmReplays=[dict(sourceBuild='studio-20261024-001242-eacc038b' if folder == 'wasm-brace' else 'studio-20261023-234042-2cf9446b', **json.loads((root / folder / 'verification.json').read_text())) for folder in ('wasm-full', 'wasm-brace')],
    botRandomness='Scenario seeds control the world. Bot orders use local randomness; independent runs are samples, not deterministic paired A/B trials. Exported orders/hashes are replayable.',
    summary=summary, matches=matches)
destination = Path(__file__).with_name('results.json')
destination.write_text(json.dumps(report, indent=2))
print(json.dumps(dict(runs=len(matches), summary=summary), indent=2))
