"""Full unit rule overlays. Base actors, shared weapons and authored resources stay intact."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys

spec = importlib.util.spec_from_file_location('studio_miniyaml', Path(__file__).with_name('apply-sound-decisions.py'))
yaml = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = yaml
spec.loader.exec_module(yaml)
SOURCE = Path('content/unit-details.json')


def load(root):
    p = root / SOURCE
    return json.loads(p.read_text()) if p.exists() else {'schema': 1, 'units': {}}


def emit(nodes, depth=0):
    return ''.join('\t' * depth + n.key + ':' + ((' ' + n.value.replace('#', '\\#')) if n.value is not None else '') + '\n' + emit(n.nodes, depth + 1) for n in nodes)


def parse(text):
    if not isinstance(text, str) or len(text) > 96000 or '\x00' in text:
        raise ValueError('Rule text must be at most 96 KB')
    # Reject duplicate keys and indentation errors rather than silently accepting a lossy parse.
    previous = 0
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith('#'): continue
        indent = len(line) - len(line.lstrip(' \t'))
        prefix = line[:indent]
        if ' ' in prefix or prefix.count('\t') > previous + 1:
            raise ValueError('Use tabs for rule indentation, one level at a time')
        previous = prefix.count('\t')
    nodes = yaml.parse(text)
    def check(rows):
        keys = set()
        for n in rows:
            if n.key in keys or not re.fullmatch(r'-?[A-Za-z0-9_^][A-Za-z0-9_.@^\-]*', n.key):
                raise ValueError('Duplicate or invalid rule key: ' + n.key)
            keys.add(n.key)
            check(n.nodes)
    check(nodes)
    return nodes


def validate(data, registry):
    if set(data) != {'schema', 'units'} or data['schema'] != 1 or type(data['units']) is not dict:
        raise ValueError('Invalid detailed unit source')
    for key, detail in data['units'].items():
        if key not in registry['units'] or type(detail) is not dict or set(detail) != {'actor', 'weapons'}:
            raise ValueError('Unknown unit or invalid rule overlay')
        for n in parse(detail['actor']):
            if n.key.startswith('Inherits'):
                raise ValueError('Edit the unit traits, not its inheritance chain')
            if n.key.lstrip('-').split('@')[0] in ['Valued', 'Health', 'Mobile', 'Aircraft']:
                blocked = {'Valued': 'Cost', 'Health': 'HP', 'Mobile': 'Speed', 'Aircraft': 'Speed'}[n.key.lstrip('-').split('@')[0]]
                if n.key.startswith('-') or any(c.key == blocked or c.key == '-' + blocked for c in n.nodes):
                    raise ValueError('Use the core stat fields for cost, health and speed')
        if type(detail['weapons']) is not dict or len(detail['weapons']) > 32:
            raise ValueError('Invalid weapon overlays')
        for arm, weapon in detail['weapons'].items():
            if not re.fullmatch(r'Armament(?:@[A-Za-z0-9_.-]+)?', arm) or set(weapon) != {'base', 'rules'} or not re.fullmatch(r'[A-Za-z0-9_.-]+', weapon['base']):
                raise ValueError('Invalid weapon binding')
            for n in parse(weapon['rules']):
                if n.key.startswith('Inherits'):
                    raise ValueError('Weapon inheritance is managed by Studio')


def alias(key, arm):
    return 'studio_' + re.sub(r'[^a-z0-9_]', '_', key.lower() + '_' + arm.lower())


def compile_overlays(root, registry):
    data = load(root)
    validate(data, registry)
    actors, weapons = {}, {}
    for key, detail in sorted(data['units'].items()):
        for target, binding in registry['units'][key]['bindings'].items():
            nodes = copy.deepcopy(parse(detail['actor']))
            weapon_nodes = []
            for arm, w in sorted(detail['weapons'].items()):
                if any(n.key == '-' + arm for n in nodes):
                    raise ValueError('Clear the weapon override before removing its armament: ' + arm)
                private = alias(key, arm)
                node = next((n for n in nodes if n.key == arm), None)
                if node is None:
                    node = yaml.Node(arm, None, [])
                    nodes.append(node)
                if any(n.key == 'Weapon' for n in node.nodes):
                    raise ValueError('Use the weapon editor to change an edited weapon binding')
                node.nodes.append(yaml.Node('Weapon', private, []))
                weapon_nodes.append(yaml.Node(private, None, [yaml.Node('Inherits', w['base'], []), *parse(w['rules'])]))
            actors.setdefault(target, []).append(yaml.Node(binding['actor'], None, nodes))
            weapons.setdefault(target, []).extend(weapon_nodes)
    return {t: emit(n) for t, n in actors.items()}, {t: emit(n) for t, n in weapons.items()}


def utility(root, target, command, name=None, config=None):
    config = config or json.loads((root / 'recovery.local.json').read_text(encoding='utf-8-sig'))
    runtime = Path(config['engineDirectory'])
    mods = {'classic-desktop':'rtsai-classic-core', 'classic-web':'rtsai-classic-core', 'ra2-desktop':'rtsai-ra2', 'ra2-web':'rtsai'}
    result = subprocess.run([str(runtime/'bin/OpenRA.Utility.exe'), mods[target], command, *([name] if name else [])],
      cwd=runtime, env={**os.environ, 'ENGINE_DIR':str(runtime), 'MOD_SEARCH_PATHS':str(config.get('mods',root/'mods')),
        'SUPPORT_DIR':config['supportDirectory'], 'OPENRA_UTILITY_EXPERIENCE_PROFILE':'world-war-iii', 'OPENRA_AI_HOST':'0'},
      text=True, capture_output=True, timeout=45)
    if result.returncode:
        raise ValueError(('Engine rejected rules: ' + result.stdout + result.stderr)[-6000:])
    return result.stdout


def node_json(n):
    return {'key':n.key, 'value':n.value, 'children':[node_json(c) for c in n.nodes]}


def view(root, key, registry):
    unit = registry['units'][key]
    saved = load(root)['units'].get(key, {'actor':'', 'weapons':{}})
    targets = {}
    for target, binding in unit['bindings'].items():
        if target == 'classic-web':
            targets[target] = targets['classic-desktop']
            continue
        # The engine resolves inheritance, removals, experience modules and prior custom work.
        actor = yaml.parse(utility(root, target, '--resolved-rules', binding['actor']))
        weapons = []
        for arm in actor:
            if arm.key.split('@')[0] != 'Armament': continue
            reference = yaml.value(arm, 'Weapon')
            if not reference: continue
            base = saved['weapons'].get(arm.key, {}).get('base', reference)
            weapon = yaml.parse(utility(root, target, '--resolved-weapons', base))
            weapons.append({'armament':arm.key, 'base':base, 'nodes':[node_json(n) for n in weapon]})
        targets[target] = {'actor':binding['actor'], 'nodes':[node_json(n) for n in actor], 'weapons':weapons}
    return {'overrides':saved, 'targets':targets}


def check_engine(root, registry, data):
    for target in ['classic-desktop','ra2-desktop','ra2-web']:
        if any(target in registry['units'][key]['bindings'] for key in data['units']):
            utility(root, target, '--check-unit-modifications')


def verification(root, receipt):
    """Compare every saved leaf with engine-resolved native rules; the browser checks the same expectations."""
    native = Path(receipt['native'])
    config = {'engineDirectory':str(native), 'supportDirectory':receipt['support'], 'mods':str(native/'mods')}
    registry=json.loads((native/'mods/rtsai/unit-overrides/bindings.json').read_text())
    manifest=json.loads((native/'mods/rtsai/unit-overrides/manifest.json').read_text())
    results=[]
    def compare(expected, actual, path=()):
        for node in expected:
            if node.key.startswith('-'):
                if any(n.key==node.key[1:] for n in actual): raise ValueError('Removed rule remains: '+str(path+(node.key,)))
                continue
            match=next((n for n in actual if n.key==node.key),None)
            if match is None: raise ValueError('Missing rule: '+str(path+(node.key,)))
            if node.value is not None and match.value!=node.value: raise ValueError('Rule mismatch: '+str(path+(node.key,)))
            compare(node.nodes, match.nodes, path+(node.key,))
    for key, detail in manifest.get('details',{}).items():
        for target,binding in registry['units'][key]['bindings'].items():
            if target=='ra2-web': continue # The native utility above uses the frozen desktop assemblies; actual web is checked in WASM below.
            actual=yaml.parse(utility(root,target,'--resolved-rules',binding['actor'],config))
            compare(parse(detail['actor']),actual)
            for arm,w in detail['weapons'].items():
                compare([yaml.Node(arm,None,[yaml.Node('Weapon',alias(key,arm),[])])],actual)
                compare(parse(w['rules']),yaml.parse(utility(root,target,'--resolved-weapons',alias(key,arm),config)))
            results.append({'unit':key,'target':target,'passed':True})
    return results
