"""Create disposable native acceptance maps; baseline maps and saves are never edited.

The map supplies a powered barracks, then trains one unit through the real
production queue and records the loaded cost and credits actually deducted.
"""
import argparse
import json
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--mode', choices=['classic', 'ra2'], required=True)
    a = p.parse_args()
    config = json.loads((ROOT / 'recovery.local.json').read_text(encoding='utf-8-sig'))
    runtime = Path(config['engineDirectory'])
    mode = 'rtsai-classic-core' if a.mode == 'classic' else 'rtsai-ra2'
    target = a.mode + '-desktop'
    content = json.loads((runtime / 'mods/rtsai/shared-content/manifest.json').read_text())
    unit = content['targets'][target]['actor'].lower()
    source = runtime / ('mods/rtsai-classic-core/maps/a-nuclear-winter' if a.mode == 'classic' else 'mods/rtsai/standalone/maps/twin-fords')
    support = a.out.resolve() / a.mode / 'support'
    support.mkdir(parents=True, exist_ok=True)
    # Reuse installed content via a link, never duplicate or change the user's content.
    installed = Path(config['supportDirectory']) / 'Content'
    if installed.exists() and not (support / 'Content').exists():
        import subprocess
        subprocess.run(['cmd', '/c', 'mklink', '/J', str(support / 'Content'), str(installed)], check=True, capture_output=True)
    manifest = (runtime / 'mods' / mode / 'mod.yaml').read_text(encoding='utf-8-sig')
    version = re.search(r'^\s*Version: (.+)$', manifest, re.M).group(1).strip()
    dest = support / 'maps' / mode / version / 'shared-content-proof'
    if dest.exists():
        raise ValueError(f'Refusing to overwrite existing proof: {dest}')
    dest.mkdir(parents=True)
    for name in ('map.bin', 'map.png'):
        if (source / name).exists(): shutil.copyfile(source / name, dest / name)
    text = (source / 'map.yaml').read_text(encoding='utf-8')
    spawns = re.findall(r'\t[^\n]+: mpspawn\n\t\tOwner: Neutral\n\t\tLocation: (-?\d+),(-?\d+)', text)
    if len(spawns) < 2: raise ValueError('Source map needs two spawn positions')
    header = text.split('\nActors:', 1)[0]
    header = re.sub(r'^RequiresMod:.*$', f'RequiresMod: {mode}', header, flags=re.M)
    header = re.sub(r'^Title:.*$', 'Title: Shared content production proof', header, flags=re.M)
    x, y = map(int, spawns[0])
    actors = '\nActors:\n'
    for i, (sx, sy) in enumerate(spawns[:2]):
        actors += f'\tSpawn{i}: mpspawn\n\t\tOwner: Neutral\n\t\tLocation: {sx},{sy}\n'
    buildings = [('fact', -3, 0), ('powr', 3, 0), ('tent', 0, 4)] if a.mode == 'classic' else [('gacnst', -3, 0), ('gapowr', 3, 0), ('gapile', 0, 4)]
    for i, (actor, dx, dy) in enumerate(buildings):
        actors += f'\tProofBuilding{i}: {actor}\n\t\tOwner: Multi0\n\t\tLocation: {x+dx},{y+dy}\n'
    (dest / 'map.yaml').write_text(header + actors + '\nRules: proof.yaml\n', encoding='utf-8')
    (dest / 'proof.yaml').write_text('World:\n\tScriptTriggers:\n\tLuaScript:\n\t\tScripts: proof.lua\nPlayer:\n\tScriptTriggers:\n', encoding='utf-8')
    lua = f'''WorldLoaded = function()
    local owner = Player.GetPlayer("Multi0")
    Trigger.AfterDelay(125, function()
        Camera.Position = owner.GetActorsByType("{'tent' if a.mode == 'classic' else 'gapile'}")[1].CenterPosition
        owner.Resources = 0
        owner.Cash = 5000
        local before = owner.Cash
        print("SHARED_CONTENT|{target}|{content['revision']}|cost|" .. Actor.Cost("{unit}") .. "|before|" .. before)
        local accepted = owner.Build({{ "{unit}" }}, function(actors)
            print("SHARED_PRODUCTION|{target}|trained|" .. #actors .. "|spent|" .. (before - owner.Cash))
        end)
        print("SHARED_QUEUE|{target}|accepted|" .. tostring(accepted))
    end)
end
'''
    (dest / 'proof.lua').write_text(lua, encoding='utf-8')
    args = [str(runtime / 'bin/OpenRA.exe'), f'Engine.EngineDir={runtime}', f'Engine.ModSearchPaths={runtime}/mods',
            f'Engine.SupportDir={support}', f'Game.Mod={mode}', 'Launch.Map=shared-content-proof',
            f"Launch.Faction={'england' if a.mode == 'classic' else 'america'}", 'Launch.Bots=Multi1:normal:russia',
            'Game.FetchNews=false', 'Game.IntroductionPromptVersion=99', 'Debug.SystemInformationVersionPrompt=99',
            'Graphics.Mode=Windowed', 'Graphics.WindowedSize=1440,900', 'Graphics.UIScale=1', 'Sound.Mute=true']
    (support.parent / 'launch.json').write_text(json.dumps(args, indent=2))
    print(json.dumps(dict(mode=mode, target=target, support=str(support), revision=content['revision'], args=args), indent=2))


if __name__ == '__main__':
    main()
