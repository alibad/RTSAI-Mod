#!/usr/bin/env python3
"""Package hash-approved loose original-country art with native render-only rules.

Uses the web game's shared original-art generator, without its retail gameplay
conversion. Inputs stay outside Git; no game archives, audio, music or videos are
copied. Only the two isometric playable profiles receive the generated overlays.
"""
import argparse
import hashlib
import importlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

NOTICE = 'EA has not endorsed and does not support this product.'
ALLOWED = re.compile(r'[a-z0-9][a-z0-9_.-]*\.(shp|vxl|hva|pal)')
PALETTES = {'PaletteFromFile', 'PlayerColorPalette', 'PaletteFromPaletteWithAlpha',
            'PaletteFromPlayerPaletteWithAlpha'}
RENDER = {'RenderSprites', 'RenderVoxels', 'WithFactionPalettes',
          'WithBuildingPlacedAnimation', 'WithDeathAnimation', 'WithFacingSpriteBody',
          'WithIdleOverlay', 'WithOriginalVoxelUnloadBody', 'WithSpriteTurret',
          'WithSupportPowerActivationAnimation', 'WithVoxelBarrel', 'WithVoxelBody',
          'WithVoxelHelicopterBody', 'WithVoxelTurret', 'FactionSupportPowerIcons'}
SKIP = {'Building', 'Exit', 'HitShape', 'IsometricSelectable', 'RallyPoint',
        'ProvidesPrerequisite', 'SpriteGroupFactions'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def render_rules(generator, E, baseline, raw_sources=None):
    """Hard allowlist: new simulation traits and unknown generator changes fail."""
    output = []
    dropped = []
    compatibility = []
    for actor in generator.rules_nodes:
        node = E.Node(actor.key)
        for trait in actor.children:
            kind = E.trait_type(trait.key).removeprefix('-')
            if kind in SKIP:
                dropped.append(actor.key + '.' + trait.key)
                continue
            if kind == 'Buildable':
                original = baseline[actor.key.lower()].get('Buildable')
                fields = [x.clone() for x in trait.children if x.key == 'IconPalette' and original is not None]
                if fields:
                    node.children.append(E.Node(trait.key, trait.value, fields))
                dropped.extend(actor.key + '.' + trait.key + '.' + x.key
                               for x in trait.children if x.key != 'IconPalette')
                continue
            if kind == 'GrantConditionOnFaction':
                require(trait.key == 'GrantConditionOnFaction@ea-art', 'Unexpected condition-grant delta')
                require(trait.val('Condition') == 'ea-art', 'Unexpected original-art condition')
                require(set(E.split_list(trait.val('Factions'))) == set(E.COUNTRIES), 'Original-art condition scope changed')
            elif kind in PALETTES:
                require(actor.key == '^Palettes', 'Palette added outside the palette definition')
            elif kind not in RENDER:
                raise ValueError('Non-render rule rejected: ' + actor.key + '.' + trait.key)
            copy = trait.clone()
            if actor.key.lower() == 'sref' and kind == 'WithVoxelTurret':
                native_grants_charge = any(t.val('Condition') == 'turretcharge'
                                           for t in baseline['sref'].children)
                condition = copy.get('RequiresCondition')
                if not native_grants_charge and condition is not None and re.search(r'\bturretcharge\b', condition.value or ''):
                    # The native project skin removes the charge-animation grants.
                    # Keep its simulation untouched: display the ordinary original
                    # turret, with charge-stage renderers disabled.
                    condition.value = 'ea-art' if trait.key == 'WithVoxelTurret' else 'false'
                    compatibility.append(actor.key + '.' + trait.key + ': no native turretcharge animation state')
            node.children.append(copy)
        if actor.key.lower() == 'r2crane':
            consumes_original_art = any(re.search(r'\bea-art\b', t.val('RequiresCondition', ''))
                                        for t in node.children if E.trait_type(t.key) in RENDER)
            if not consumes_original_art:
                node.children = [t for t in node.children if t.key != 'GrantConditionOnFaction@ea-art']
                compatibility.append('r2crane: omitted unused render-only ea-art condition grant')
        if node.children:
            output.append(node)
    # Compare every non-render trait with the unmodified native definitions.
    sources = raw_sources if raw_sources is not None else [list(baseline.values())]
    effective = {key.lower(): value for key, value in E.merge(sources + [output]).items()}
    crane = effective.get('r2crane')
    if crane is not None and crane.get('GrantConditionOnFaction@ea-art') is not None:
        consumers = any(re.search(r'\bea-art\b', t.val('RequiresCondition', ''))
                        for t in crane.children if E.trait_type(t.key) in RENDER)
        if not consumers:
            output.append(E.Node(crane.key, None, [E.Node('-GrantConditionOnFaction@ea-art')]))
            compatibility.append('r2crane: omitted inherited unused render-only ea-art condition grant')
            effective = {key.lower(): value for key, value in E.merge(sources + [output]).items()}
    for name, before in baseline.items():
        current = effective[name]
        def gameplay(actor):
            result = []
            for trait in actor.children:
                kind = E.trait_type(trait.key)
                if kind in RENDER or kind in PALETTES or trait.key == 'GrantConditionOnFaction@ea-art':
                    continue
                copy = trait.clone()
                if kind == 'Buildable':
                    copy.children = [x for x in copy.children if x.key != 'IconPalette']
                result.append(copy)
            return E.dump(result)
        require(gameplay(current) == gameplay(before), 'Gameplay changed: ' + name)
    generator.native_render_compatibility = compatibility
    return output, dropped


def append_section(text, key, value):
    lines = text.splitlines()
    start = lines.index(key + ':') + 1
    end = next((i for i in range(start, len(lines)) if lines[i] and not lines[i][0].isspace()), len(lines))
    if '\t' + value not in lines[start:end]:
        lines.insert(end, '\t' + value)
    return '\n'.join(lines) + '\n'


def power_widget_chrome(text):
    result = re.sub(r'(?m)^(\s*)SupportPowers@SUPPORT_PALETTE:',
                    r'\1OriginalSupportPowers@SUPPORT_PALETTE:', text)
    require('OriginalOriginalSupportPowers' not in result, 'Invalid repeated power-widget adapter')
    require(len(re.findall(r'(?m)^\s*OriginalSupportPowers@SUPPORT_PALETTE:', result)) == 1,
            'Native support-power widget binding is missing or ambiguous')
    return result


def verify(resources):
    record = json.loads((resources / 'native-original-art.json').read_text())
    require(record['notice'] == NOTICE and record['renderOnly'], 'Missing notice or native render-only scope')
    directory = resources / 'mods/rtsai/web/ea'
    for file in record['files']:
        require(ALLOWED.fullmatch(file['name']), 'Unsafe art name: ' + file['name'])
        require(sha(directory / file['name']) == file['sha256'], 'Art hash differs: ' + file['name'])
    # Distinguish the actual Grizzly, IFV, Prism and Tank Destroyer models.
    names = ['gtnk.vxl', 'fv.vxl', 'sref.vxl', 'tnkd.vxl']
    hashes = [sha(directory / n) for n in names]
    require(len(set(hashes)) == len(names), 'Original-country models collapse to one model')
    for name in names:
        placeholder = resources / 'mods/rtsai/standalone/placeholders' / name
        require(not placeholder.exists() or sha(placeholder) != sha(directory / name), name + ' is a stand-in')
    require((resources / 'NOTICE-original-country-art.txt').read_text().startswith(NOTICE), 'Missing attribution')
    print('PASS native original-country art: approved hashes, distinct US models, no placeholder substitutions')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mod', type=Path)
    parser.add_argument('--webgame', type=Path)
    parser.add_argument('--art', type=Path)
    parser.add_argument('--resources', required=True, type=Path)
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    if args.verify:
        verify(args.resources)
        return
    if not all((args.mod, args.webgame, args.art)):
        parser.error('--mod, --webgame and --art are required when preparing')
    sys.path.insert(0, str(args.webgame.resolve() / 'tools'))
    E = importlib.import_module('ea_originals')
    approved = json.loads((args.art / 'EA-INPUTS.json').read_text())
    require(approved['notice'] == NOTICE, 'Approved source notice differs')
    manifest = {f['name']: f for f in approved['files']}
    require(len(manifest) == len(approved['files']), 'Duplicate approved file')
    for name, file in manifest.items():
        require(ALLOWED.fullmatch(name), 'Unsafe approved art name: ' + name)
        require(sha(args.art / name) == file['sha256'], 'Approved input hash differs: ' + name)
    content = args.resources / 'mods/rtsai/web/content'
    # Read the native baseline independently before the shared generator performs
    # planning-only availability changes. Never compare against its mutated cur.
    native_rules = E._section((args.mod / 'mods/rtsai/mod.yaml').read_text(), 'Rules')
    native_files = E.ModFiles(args.mod.resolve(), content)
    raw_sources = [E.parse(native_files.path(path).read_text()) for path in native_rules]
    baseline = {key.lower(): value for key, value in E.merge(raw_sources).items()}
    generator = E.Generator(args.mod.resolve(), content, target='native-render-only').plan().generate()
    rules, dropped = render_rules(generator, E, baseline, raw_sources)
    art_out = args.resources / 'mods/rtsai/web/ea'
    art_out.mkdir(parents=True, exist_ok=True)
    content.mkdir(parents=True, exist_ok=True)
    files = []
    for name in generator.ea_files:
        if name not in manifest:
            raise ValueError('Native plan requests unapproved art: ' + name)
        shutil.copy2(args.art / name, art_out / name)
        files.append({'name': name, 'sha256': manifest[name]['sha256']})
    header = '# Generated native render-only original-country art. ' + NOTICE + '\n\n'
    overlays = [('Rules', 'native-ea-art.yaml', rules),
                ('Sequences', 'native-ea-sequences.yaml', generator.seq_nodes),
                ('ModelSequences', 'native-ea-models.yaml', generator.model_nodes)]
    for _, filename, nodes in overlays:
        (content / filename).write_text(header + E.dump(nodes) + '\n')
    (content / E.BLANK_FILE).write_bytes(E.blank_png())
    for mod in ('rtsai', 'rtsai-ra2'):
        path = args.resources / 'mods' / mod / 'mod.yaml'
        text = path.read_text()
        for section, filename, _ in overlays:
            text = append_section(text, section, 'ra2|web/content/' + filename)
        path.write_text(text)
    # Keep the attribution in the packaged native prerelease notice as well as
    # the payload record. This does not change the notice's continue action.
    prompt = args.resources / 'mods/rtsai/chrome/mainmenu-prerelease-notification.yaml'
    text = prompt.read_text().replace('Text: mainmenu-prerelease-notification-prompt-text-e-text', 'Text: ' + NOTICE)
    prompt.write_text(text)
    powers = args.resources / 'mods/rtsai/chrome/ingame-player.yaml'
    powers.write_text(power_widget_chrome(powers.read_text()))
    (args.resources / 'NOTICE-original-country-art.txt').write_text(
        NOTICE + '\nOriginal country art reused from the hash-verified public game asset manifest.\n'
        'Free, non-commercial modding use; no C&C music, EVA, video or archives included.\n')
    commit = lambda repo: subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
    record = {'schema': 1, 'notice': NOTICE, 'renderOnly': True,
              'modCommit': commit(args.mod), 'generatorCommit': commit(args.webgame),
              'generatorSha256': sha(args.webgame / 'tools/ea_originals.py'),
              'gateSha256': sha(Path(__file__).resolve()),
              'approvedManifestSha256': sha(args.art / 'EA-INPUTS.json'),
              'approvedPublicManifestSha256': approved.get('publicManifestSha256'),
              'countries': list(E.COUNTRIES), 'modernFactionsPreserved': list(E.MODERN),
              'actors': sorted(generator.actors), 'files': files,
              'expectedOriginalImages': {name: {f: 'ea-' + image for f, image in facts['images'].items()}
                                         for name, facts in generator.actors.items() if 'images' in facts},
              'expectedModernImages': {name: {f: E.render_image(actor, f) for f in E.MODERN}
                                       for name, actor in baseline.items()
                                       if not name.startswith('^') and actor.get('RenderSprites') is not None},
              'expectedVoxelImages': {name: 'ea-' + facts['voxel'] for name, facts in generator.actors.items() if 'voxel' in facts},
              'gameplayDeltasRejected': True, 'droppedNonRenderDeltas': dropped,
              'renderCompatibility': generator.native_render_compatibility,
              'supportPowerIcons': 'Original9 native UI sprite/palette adapter; modern7 delegate to unchanged engine behavior.',
              'audio': 'Existing native voices retained; original web voices are not included.'}
    (args.resources / 'native-original-art.json').write_text(json.dumps(record, indent=2) + '\n')
    verify(args.resources)


if __name__ == '__main__':
    main()
