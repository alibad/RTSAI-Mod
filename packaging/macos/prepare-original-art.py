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


NOTICE_KEY = 'mainmenu-prerelease-notification-prompt-text-e-text'
CREDIT = ('\nOriginal Red Alert 2 art, unit voices and sounds (the nine original countries):\n'
          '* Westwood Studios / Electronic Arts. Used under EA\'s Command & Conquer Franchise Modding Guidelines:\n'
          '  free and non-commercial; no C&C music, EVA, video or archives are included.\n'
          '* ' + NOTICE + '\n')

# Original unit voices and sounds (RTSAI-WebGame tools/ea_voices.py, as on the web): sound-only changes, proven here.
AUDIO = re.compile(r'[a-z0-9][a-z0-9_.-]*\.wav')
WEAPON_SOUNDS = {'Report', 'StartBurstReport', 'AfterFireSound', 'ImpactSounds'}
SOUND_FIELD = re.compile(r'(Sound|Sounds|Audio)$')
DEATH = 'FireWarheadsOnDeath'
# The voice twins' faction conditions (one per group of countries that speak alike, e.g. the engineer) and the deaths'.
CONDITION = re.compile(r'GrantConditionOnFaction@(ea-voice(-[a-z]+)?|ea-death)')


def is_sound_field(key):
    name = key.lstrip('-').split('@')[0]
    return name in WEAPON_SOUNDS or bool(SOUND_FIELD.search(name))


def strip_sounds(node):
    copy = node.clone()
    def walk(n):
        n.children = [c for c in n.children if not is_sound_field(c.key)]
        for c in n.children:
            walk(c)
    walk(copy)
    return copy


def condition_rest(value, token):
    """A RequiresCondition with the ea condition taken out, to compare with the native one."""
    text = re.sub(r'!?\b' + re.escape(token) + r'\b', '', value or '')
    return re.sub(r'&&|\(|\)|\s', '', text)


def sound_rules(voices, E, rule_sources, weapon_sources, voice_sources):
    """Hard gate: the voice overlay may change only voices, sounds and which sound-only copy of a death weapon fires."""
    low = lambda tree: {key.lower(): value for key, value in tree.items()}
    rules_before, rules_after = low(E.merge(rule_sources)), low(E.merge(rule_sources + [voices.rules_nodes]))
    weapons_before = low(E.merge(weapon_sources))
    weapons_after = low(E.merge(weapon_sources + [voices.weapon_nodes]))
    existing_voices = low(E.merge(voice_sources))
    body = lambda node: E.dump(strip_sounds(node).children)
    for name, weapon in weapons_before.items():
        require(body(weapons_after[name]) == body(weapon), 'Weapon changed beyond its sounds: ' + name)

    def twin(new, old, where):
        if new is None and old is None:
            return
        new, old = (new or 'UnitExplode').lower(), (old or 'UnitExplode').lower()
        require(new in weapons_after and old in weapons_before, 'Unknown death weapon at ' + where)
        require(body(weapons_after[new]) == body(weapons_before[old]), new + ' is not a sound-only copy of ' + old + ' at ' + where)

    for node in voices.voice_nodes:
        require(node.key.startswith('Ea') and node.key.lower() not in existing_voices, 'Voice overlay replaces a voice set: ' + node.key)

    def neutral(actor):
        kept = []
        for trait in actor.children:
            kind = E.trait_type(trait.key).removeprefix('-')
            if kind in ('RTSAIVoiced', DEATH) or CONDITION.fullmatch(trait.key):
                continue
            copy = strip_sounds(trait)
            if kind == 'FallsToEarth':
                copy.children = [c for c in copy.children if c.key != 'Explosion']
            kept.append(copy)
        return E.dump(kept)

    for node in voices.rules_nodes:
        name = node.key.lower()
        before, after = rules_before.get(name), rules_after[name]
        require(before is not None, 'The voice overlay adds an actor: ' + name)
        if neutral(after) != neutral(before):
            import difflib
            delta = difflib.unified_diff(neutral(before).splitlines(), neutral(after).splitlines(), 'native', 'with voices', lineterm='', n=1)
            raise ValueError('Gameplay changed: ' + name + '\n' + '\n'.join(list(delta)[:40]))
        for trait in node.children:
            kind, where = E.trait_type(trait.key).removeprefix('-'), name + '.' + trait.key
            if kind == 'GrantConditionOnFaction':
                require(CONDITION.fullmatch(trait.key) and trait.val('Condition') == trait.key.split('@')[1]
                        and set(E.split_list(trait.val('Factions'))) <= set(E.COUNTRIES) | set(E.MODERN), 'Unexpected condition: ' + where)
            elif kind == 'RTSAIVoiced':
                # A twin behind ea-voice, or (the Attack Dog, every faction) the voice set alone.
                condition = trait.get('RequiresCondition')
                require({c.key for c in trait.children} <= {'VoiceSet', 'RequiresCondition'}
                        and (condition is None or 'ea-voice' in (condition.value or '')), 'Unexpected voice change: ' + where)
            elif kind == 'FallsToEarth':
                require({c.key for c in trait.children} <= {'Explosion'}, 'Unexpected crash change: ' + where)
                twin(after.get(trait.key).val('Explosion'), before.get(trait.key).val('Explosion'), where)
            elif kind != DEATH:
                require(all(is_sound_field(c.key) for c in trait.children), 'Non-sound field: ' + where)
        # Each effective death trait is the native one, firing a sound-only copy of its weapons behind ea-death.
        for trait in after.children:
            if E.trait_type(trait.key) != DEATH:
                continue
            where = name + '.' + trait.key
            base = before.get(trait.key[:-len('@ea-death')] if trait.key.endswith('@ea-death') else trait.key)
            require(base is not None, 'A death trait without a native original: ' + where)
            rest = lambda t: E.dump([c for c in t.children if c.key not in ('Weapon', 'EmptyWeapon', 'RequiresCondition')])
            require(rest(trait) == rest(base), 'Death trait changed: ' + where)
            twin(trait.val('Weapon'), base.val('Weapon'), where)
            twin(trait.val('EmptyWeapon'), base.val('EmptyWeapon'), where)
            require(condition_rest(trait.val('RequiresCondition'), 'ea-death') == condition_rest(base.val('RequiresCondition'), 'ea-death'),
                    'Death condition changed: ' + where)


def add_voices(voices, E, approved, art, resources, content, sources):
    """Generate the original voices from the approved clips, prove them sound-only, copy the clips they use."""
    audio = approved.get('audio')
    require(audio is not None, 'The approved folder has no original voice clips: run prepare-ea-art.py with sounds')
    folder = art / audio['folder']
    files = {f['name']: f for f in audio['files']}
    planned = set(voices.needed_clips())
    # The web extract also carries clips only the browser's retail layer names (V3, Dreadnought): not planned here.
    voices.generate([n for n in files if n in planned], [n for n in audio['absent'] if n in planned])
    sound_rules(voices, E, *sources)
    out = resources / 'mods/rtsai/web/ea/audio'
    out.mkdir(parents=True, exist_ok=True)
    clips = []
    for name in voices.summary['clips']:
        require(AUDIO.fullmatch(name) and name in files, 'Unapproved clip: ' + name)
        require(sha(folder / name) == files[name]['sha256'], 'Approved clip hash differs: ' + name)
        shutil.copy2(folder / name, out / name)
        clips.append({'name': name, 'sha256': files[name]['sha256']})
    header = '# Generated native original unit voices and sounds (sound-only). ' + NOTICE + '\n\n'
    overlays = [('Rules', 'native-ea-audio.yaml', voices.rules_nodes),
                ('Voices', 'native-ea-voices.yaml', voices.voice_nodes),
                ('Weapons', 'native-ea-weapons.yaml', voices.weapon_nodes)]
    for _, filename, nodes in overlays:
        (content / filename).write_text(header + E.dump(nodes) + '\n', encoding='utf-8')
    summary = {'clips': clips, 'absentFromRa2': voices.summary['absent'], 'actors': sorted(voices.summary['actors']),
               'voiceSets': len(voices.voice_nodes), 'weapons': len(voices.weapon_nodes),
               'approvedAudioSha256': audio.get('sha256'), 'soundOnly': True}
    return overlays, summary


def prompt_notice(text):
    """The developer-preview prompt's fifth line (Label@PROMPT_TEXT_E, empty in the source) shows the notice."""
    lines = text.splitlines()
    start = lines.index('\t\tLabel@PROMPT_TEXT_E:')
    end = next((i for i in range(start + 1, len(lines)) if not lines[i].startswith('\t\t\t')), len(lines))
    texts = [l for l in lines[start + 1:end] if l.strip().startswith('Text:')]
    require(texts in ([], ['\t\t\tText: ' + NOTICE_KEY]), 'The prompt line for the notice already says something else')
    if not texts:
        lines.insert(end, '\t\t\tText: ' + NOTICE_KEY)
    return '\n'.join(lines) + '\n'


def add_notice_text(resources):
    prompt = resources / 'mods/rtsai/chrome/mainmenu-prerelease-notification.yaml'
    prompt.write_text(prompt_notice(prompt.read_text(encoding='utf-8')), encoding='utf-8')
    strings = resources / 'mods/rtsai/languages/chrome/en.ftl'
    text = strings.read_text(encoding='utf-8')
    if NOTICE_KEY + ' =' not in text:
        strings.write_text(text.rstrip('\r\n') + '\n' + NOTICE_KEY + ' = ' + NOTICE + '\n', encoding='utf-8')
    credits = resources / 'mods/rtsai/CREDITS'
    text = credits.read_text(encoding='utf-8')
    if NOTICE not in text:
        credits.write_text(text.rstrip('\r\n') + '\n' + CREDIT, encoding='utf-8')


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
    audio = record.get('audio')
    require(isinstance(audio, dict) and audio.get('soundOnly') and audio['clips'], 'Missing the original voices and sounds')
    for clip in audio['clips']:
        require(AUDIO.fullmatch(clip['name']), 'Unsafe clip name: ' + clip['name'])
        require(sha(directory / 'audio' / clip['name']) == clip['sha256'], 'Clip hash differs: ' + clip['name'])
    # The notice in the game itself: the developer-preview prompt every start shows, and the Credits screen.
    prompt = (resources / 'mods/rtsai/chrome/mainmenu-prerelease-notification.yaml').read_text(encoding='utf-8')
    require('\t\t\tText: ' + NOTICE_KEY in prompt.splitlines(), 'The developer-preview prompt does not show the notice')
    require(NOTICE_KEY + ' = ' + NOTICE in (resources / 'mods/rtsai/languages/chrome/en.ftl').read_text(encoding='utf-8'),
            'The notice text is missing from the prompt strings')
    require(NOTICE in (resources / 'mods/rtsai/CREDITS').read_text(encoding='utf-8'), 'The Credits screen does not credit EA')
    print('PASS native original-country art: approved hashes, distinct US models, no placeholder substitutions, '
          'EA notice in the start-up prompt and the Credits')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mod', type=Path)
    parser.add_argument('--webgame', type=Path)
    parser.add_argument('--art', type=Path)
    parser.add_argument('--resources', required=True, type=Path)
    parser.add_argument('--verify', action='store_true')
    parser.add_argument('--generator-commit', help='the RTSAI-WebGame commit to record when its checkout is ahead of '
                        'origin/main with commits that do not touch tools/ (the caller checks that)')
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
    native_manifest = (args.mod / 'mods/rtsai/mod.yaml').read_text(encoding='utf-8')
    native_files = E.ModFiles(args.mod.resolve(), content)
    load = lambda section: [E.parse(native_files.path(path).read_text(encoding='utf-8')) for path in E._section(native_manifest, section)]
    raw_sources = load('Rules')
    baseline = {key.lower(): value for key, value in E.merge(raw_sources).items()}
    generator = E.Generator(args.mod.resolve(), content, target='native-render-only').plan()
    # The voices plan reads the generator's planned state, as the web build does (prepare-content.py originals).
    voices = importlib.import_module('ea_voices').VoiceGenerator(generator).plan()
    generator.generate()
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
    sound_overlays, audio_summary = add_voices(voices, E, approved, args.art, args.resources, content,
                                               (raw_sources + [rules], load('Weapons'), load('Voices')))
    overlays += sound_overlays
    for mod in ('rtsai', 'rtsai-ra2'):
        path = args.resources / 'mods' / mod / 'mod.yaml'
        text = path.read_text()
        for section, filename, _ in overlays:
            text = append_section(text, section, 'ra2|web/content/' + filename)
        path.write_text(text)
    # Keep the attribution in the packaged native prerelease notice and the Credits as well as
    # the payload record. This does not change the notice's continue action.
    add_notice_text(args.resources)
    powers = args.resources / 'mods/rtsai/chrome/ingame-player.yaml'
    powers.write_text(power_widget_chrome(powers.read_text()))
    (args.resources / 'NOTICE-original-country-art.txt').write_text(
        NOTICE + '\nOriginal country art, unit voices and sounds reused from the hash-verified public game asset manifest.\n'
        'Free, non-commercial modding use; no C&C music, EVA, video or archives included.\n')
    commit = lambda repo: subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
    record = {'schema': 1, 'notice': NOTICE, 'renderOnly': True,
              'modCommit': commit(args.mod), 'generatorCommit': args.generator_commit or commit(args.webgame),
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
              'audio': {**audio_summary, 'generatorSha256': sha(args.webgame / 'tools/ea_voices.py')}}
    (args.resources / 'native-original-art.json').write_text(json.dumps(record, indent=2) + '\n')
    verify(args.resources)


if __name__ == '__main__':
    main()
