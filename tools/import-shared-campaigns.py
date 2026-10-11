#!/usr/bin/env python3
"""Import project-authored browser factions and campaigns into both native profiles.

Run after build-classic-mode.py. No commercial game content is copied.
The browser campaign controller is adapted into a per-world native trait.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
WEB = None


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8', newline='\n')


def briefings(catalog):
    for mission in catalog:
        for mode in ['rtsai', 'rtsai-topdown']:
            dst = ROOT / 'mods' / mode / 'campaigns/maps' / mission['id']
            source = (dst / 'map.yaml').read_text(encoding='utf-8')
            source = re.sub(r'^\t\t\tBriefing: .*$', '\t\t\tBriefing: briefing', source, flags=re.M)
            if not re.search(r'^FluentMessages:', source, flags=re.M):
                source = source.rstrip() + '\n\nFluentMessages: briefing.ftl\n'
            write(dst / 'map.yaml', source)
            lines = ['briefing ='] + ['    ' + line for line in mission['briefing'].splitlines()]
            write(dst / 'briefing.ftl', '\n'.join(lines) + '\n')


def controller():
    if WEB is None:
        raise ValueError("Pass an explicit frozen --web-source; live sibling inputs are not implicit")
    source = (WEB/'sim/OpenRA.WebSim/Missions.cs').read_text(encoding='utf-8')
    source = source.replace('namespace OpenRA.WebSim', 'namespace OpenRA.Mods.RTSAI.Traits')
    source = source.replace('public static class Missions', '''[TraitLocation(SystemActors.World)]
	public class RTSAICampaignInfo : TraitInfo
	{
		public readonly string Mission = null;
		public override object Create(ActorInitializer init) => new RTSAICampaign(this);
	}

	public class RTSAICampaign : ITick''')
    source = source.replace('static Definition[] catalog;', '''readonly RTSAICampaignInfo info;
		World campaignWorld;
		MissionObjectives objectives;
		int[] objectiveIds;
		bool initialized;
		public RTSAICampaign(RTSAICampaignInfo info) { this.info = info; }
		Definition[] catalog;''')
    source = source.replace('public static ', 'public ').replace('\t\tstatic ', '\t\t')
    source = source.replace('SimHost.ModData', 'campaignWorld.Map')
    source = source.replace('ra2|web/content/missions.json', 'ra2|campaigns/missions.json')
    source = source.replace('campaignWorld.Map.DefaultFileSystem', 'campaignWorld.Map')
    source = re.sub(r'\n\t\t\tif \(SimHost.Scenario.Map.*?Invalid mission player slot\."\);', '''
			human = campaignWorld.Players.FirstOrDefault(p => p.InternalName == current.Slot)
				?? throw new InvalidDataException("Invalid mission player slot.");''', source, flags=re.S)
    source = source.replace('SimHost.World.WorldActor', 'campaignWorld.WorldActor')
    source = source.replace('SimHost.Scenario.Options.GetValueOrDefault("difficulty", "normal")', 'campaignWorld.LobbyInfo.GlobalSettings.LobbyOptions.TryGetValue("difficulty", out var option) ? option.Value : "normal"')
    source = source.replace('difficulty = campaignWorld', 'difficulty = campaignWorld')
    source = source.replace('states = current.Objectives.Select(o => new State { Spec = o }).ToList();', '''states = current.Objectives.Select(o => new State { Spec = o }).ToList();
			objectives = human.PlayerActor.Trait<MissionObjectives>();
			objectiveIds = current.Objectives.Select(o => objectives.Add(human, o.Text, o.Secondary ? "Secondary" : "Primary", !o.Secondary, true)).ToArray();''')
    source = source.replace('public void Tick(World world)\n\t\t{', '''void ITick.Tick(Actor self)
		{
			var world = self.World;
			if (!initialized)
			{
				initialized = true;
				campaignWorld = world;
				Start(info.Mission);
			}''')
    source = source.replace('if (states.Where(s => !s.Spec.Secondary && s.Spec.Kind != "protect").All(s => s.Status == "complete"))', 'if (won)')
    source = source.replace('\n\t\t\t\tforeach (var s in states.Where(s => s.Spec.Kind == "protect" && s.Status == "active")) s.Status = "complete";', '')
    source = source.replace('\n\t\t\tif (states.Any', '''
			var won = !states.Any(s => !s.Spec.Secondary && s.Status == "failed")
				&& states.Where(s => !s.Spec.Secondary && s.Spec.Kind != "protect").All(s => s.Status == "complete");
			if (won)
				foreach (var s in states.Where(s => s.Spec.Kind == "protect" && s.Status == "active"))
					s.Status = "complete";
			// Publish secondary statuses first: completing the last primary can
			// award victory immediately and stops further campaign ticks.
			foreach (var i in Enumerable.Range(0, states.Count).OrderByDescending(i => states[i].Spec.Secondary))
			{
				if (states[i].Status == "complete") objectives.MarkCompleted(human, objectiveIds[i]);
				else if (states[i].Status == "failed") objectives.MarkFailed(human, objectiveIds[i]);
			}
			if (states.Any''')
    # Native objectives drive the standard mission panel, surrender and game-over.
    source = source[:source.index('\n\t\tpublic string StateJson()')] + '\n\t}\n}\n'
    source = source.replace('human.WinState = won ? WinState.Won : WinState.Lost;\n\t\t\tworld.OnPlayerWinStateChanged(human);', '''for (var i = 0; i < states.Count; i++)
			{
				if (!states[i].Spec.Secondary)
				{
					if (won) objectives.MarkCompleted(human, objectiveIds[i]);
					else { objectives.MarkFailed(human, objectiveIds[i]); break; }
				}
			}''')
    write(ROOT/'OpenRA.Mods.RTSAI/Traits/RTSAICampaign.cs', source)


def content():
    directory = ROOT/'mods/rtsai/campaigns'
    for filename in ['countries.yaml', 'country-sequences.yaml', 'country-notifications.yaml', 'missions.json']:
        directory.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(WEB/'content'/filename, directory/filename)
    countries = (directory/'countries.yaml').read_text(encoding='utf-8')
    countries += '\nmgtk:\n\tWithMirageSpriteBody:\n\t\tName: camouflage\n\tWithFacingSpriteBody:\n\t\tRequiresCondition: !tree\n'
    countries += '\nsref:\n\t-GrantConditionOnAttack@turretcharge1:\n\t-GrantConditionOnAttack@turretcharge2:\n\t-GrantConditionOnAttack@turretcharge3:\n'
    infantry = 'e1 e2 snipe ghost ccomand ptroop tany jumpjet cleg flakt shk terror deso ivan civan yuri yuripr'.split()
    vehicles = 'mtnk fv mgtk htnk apoc ttnk sref dtruck dron'.split()
    aircraft = 'shad zep orca beag pdplane hornet asw'.split()
    naval = 'dest aegis dlph carrier sub hyd sqd'.split()
    for actors, voice in [(infantry,'R2ChinainfantryVoice'),(vehicles,'R2ChinavehicleVoice'),(aircraft,'R2ChinaairVoice'),(naval,'R2ChinanavalVoice')]:
        for actor in actors:
            countries += f'\n{actor}:\n\tRTSAIVoiced:\n\t\tVoiceSet: {voice}\n'
    # These capturable structures reuse our authored base kit rather than legacy scenery.
    for actor, image in [('caoild','campaign-oil'),('cahosp','campaign-hospital'),('caoutp','campaign-outpost')]:
        countries += f'\n{actor}:\n\tRenderSprites:\n\t\tImage: {image}\n\t\tPlayerPalette: kitplayer\n'
        countries += f'\n{actor}.rubble:\n\tRenderSprites:\n\t\tImage: {image}\n\t\tPalette: kitbase\n'
    countries += '\ncaoutp:\n\tWithVoxelTurret:\n\t\tRequiresCondition: false\n'
    countries += '\namradr:\n\tRenderSprites:\n\t\tImage: airf-china\n\t\tPlayerPalette: kitplayer\n'
    countries += '\ndest:\n\tWithFacingSpriteBody:\n\t\tRequiresCondition: loaded\n\tWithFacingSpriteBody@EMPTY:\n\t\tName: empty-body\n\t\tRequiresCondition: !loaded\n'
    write(directory/'countries.yaml', countries)
    sequences = (directory/'country-sequences.yaml').read_text(encoding='utf-8')
    for image, filename in [('campaign-oil','refn-china.shp'),('campaign-hospital','tech-china.shp'),('campaign-outpost','cnst-china.shp')]:
        sequences += f'\n{image}:\n\tDefaults:\n\t\tFilename: ra2|standalone/base/{filename}\n\t\tOffset: 0,-24\n'
        for name in ['idle','damaged-idle','critical-idle','idle-pump','damaged-idle-pump','critical-idle-pump','idle-overlay','damaged-idle-overlay','critical-idle-overlay','flag','idle-tower','idle-tower-shadow','bib','active-crane','rubble']:
            sequences += f'\t{name}:\n\t\tStart: {1 if name.startswith("damaged") else 2 if name.startswith("critical") or name=="rubble" else 0}\n'
    sequences += '\nfalc:\n\ticon:\n\t\tFilename: ra2|modern-factions/icons/r2kunlun.png\ngaairc:\n\ticon:\n\t\tFilename: ra2|standalone/base/airf-chinaicon.png\njumpjet.husk:\n\tidle:\n\t\tFilename: ra2|modern-factions/infantry/r2falcon.shp\n\t\tStart: 0\n\t\tLength: 1\n\t\tFacings: 1\n'
    # Fresh vector-drawn trees for camouflage visuals; these are independent project pixels.
    from PIL import Image, ImageDraw
    from PIL.PngImagePlugin import PngInfo
    for i in range(1,5):
        img=Image.new('RGBA',(64,96)); draw=ImageDraw.Draw(img)
        draw.ellipse((5,72,59,90),fill=(0,0,0,60)); draw.rectangle((29,50,35,82),fill=(89,65,43))
        for x,y,r in [(31,27,21),(20,43,17),(43,47,17),(31,57,20)]:
            draw.ellipse((x-r,y-r,x+r,y+r),fill=(43+i*4,78+i*5,40+i*3,255))
        meta=PngInfo();meta.add_text('FrameSize','64,96');meta.add_text('FrameAmount','1')
        img.save(directory/f'tree{i}.png',pnginfo=meta)
        sequences += f'\ntree0{i}:\n\tidle:\n\t\t-TilesetFilenames:\n\t\tFilename: ra2|campaigns/tree{i}.png\n\t\tStart: 0\n\t\tShadowStart: -1\n'
    write(directory/'country-sequences.yaml',sequences)
    voices = ''
    for voice, prefix in [('R2ChinainfantryVoice','rcn-infantry'),('R2ChinavehicleVoice','rcn-vehicle'),('R2ChinaairVoice','rcn-air')]:
        voices += voice+':\n\tVoices:\n'
        for action in ['SpecialAttack','Build','Deploy']:
            voices += f'\t\t{action}: ra2|modern-factions/audio/{prefix}-action-en\n'
    write(directory/'country-voices.yaml',voices)
    catalog = json.loads((directory/'missions.json').read_text(encoding='utf-8'))
    for mission in catalog:
        for mode in ['rtsai', 'rtsai-topdown']:
            dst = ROOT/'mods'/mode/'campaigns/maps'/mission['id']
            shutil.copytree(WEB/'content/maps'/mission['id'], dst, dirs_exist_ok=True)
            source = (dst/'map.yaml').read_text(encoding='utf-8')
            source = source.replace('RequiresMod: rtsai', 'RequiresMod: '+mode)
            difficulty = '\t\tScriptLobbyDropdown@difficulty:\n\t\t\tID: difficulty\n\t\t\tLabel: dropdown-missionbrowser-difficulty.label\n\t\t\tDescription: dropdown-missionbrowser-difficulty.description\n\t\t\tDefault: normal\n\t\t\tValues:\n\t\t\t\teasy: campaign-difficulty-easy\n\t\t\t\tnormal: label-missionbrowser-normal-difficulty\n\t\t\t\thard: campaign-difficulty-hard\n'
            source = source.replace('\tWorld:\n', '\tWorld:\n'+difficulty+'\t\tRTSAICampaign:\n\t\t\tMission: '+mission['id']+'\n\t\tObjectivesPanel:\n\t\t\tPanelName: MISSION_OBJECTIVES\n\t\tMissionData:\n\t\t\tBriefing: '+json.dumps(mission['briefing'])+'\n')
            if mode == 'rtsai-topdown':
                # Inverse of rectangular-isometric MPos -> CPos; map.bin is already MPos-indexed.
                def location(match):
                    x, y = map(int, match.groups())
                    return f'Location: {(x-y)//2},{x+y}'
                source = re.sub(r'Location: (-?\d+),(-?\d+)', location, source)
                import struct
                data = bytearray((dst/'map.bin').read_bytes())
                _, w, h, tiles, _, _ = struct.unpack_from('<BHHIII', data)
                for i in range(w*h):
                    tile = struct.unpack_from('<H', data, tiles+i*3)[0]
                    struct.pack_into('<HB', data, tiles+i*3, {1015:1,1047:2,1031:3}.get(tile,0),0)
                (dst/'map.bin').write_bytes(data)
            write(dst/'map.yaml', source)
    briefings(catalog)
    for mode in ['rtsai','rtsai-topdown']:
        path = ROOT/'mods'/mode/'mod.yaml'
        source = path.read_text(encoding='utf-8')
        alias = 'ra2' if mode == 'rtsai' else 'classic'
        for reference in [f'{alias}|campaigns/maps: System','ra2|campaigns/countries.yaml','ra2|campaigns/country-sequences.yaml','ra2|campaigns/country-notifications.yaml','ra2|campaigns/country-voices.yaml']:
            source = source.replace('\t'+reference+'\n','')
        source = source.replace('MapFolders:\n', f'MapFolders:\n\t{alias}|campaigns/maps: System\n')
        # Run last: restores historical country definitions with project-owned replacement assets.
        source = source.replace('\nSequences:', '\n\tra2|campaigns/countries.yaml\n\nSequences:')
        source = source.replace('\nModelSequences:', '\n\tra2|campaigns/country-sequences.yaml\n\nModelSequences:')
        source = source.replace('\nTileSets:', '\n\tra2|campaigns/country-notifications.yaml\n\nTileSets:')
        source = source.replace('\nNotifications:', '\n\tra2|campaigns/country-voices.yaml\n\nNotifications:')
        source = source.replace('# The original factions and maps live in the separate classic add-on (mods/rtsai-classic, needs the player\'s RA2).', '# Both shipped modes use project-authored resources. Historical country mechanics are restored by campaigns/countries.yaml.')
        # Stable on repeated imports: removing/reinserting references must not grow blank lines.
        write(path,re.sub(r'\n{3,}', '\n\n', source))


def classic_candidate(candidate):
    spec = json.loads((candidate / 'INPUTS.json').read_text())
    entries = []
    for item in sorted(candidate.rglob('*')):
        if item.is_file() and item not in (candidate / 'INPUTS.json', candidate / 'BUILD-INPUTS.json'):
            entries.append({'path': item.relative_to(candidate).as_posix(), 'size': item.stat().st_size,
                            'sha256': hashlib.sha256(item.read_bytes()).hexdigest(),
                            'executable': bool(item.stat().st_mode & 0o111)})
    identity = hashlib.sha256(json.dumps(entries, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    if entries != spec['files'] or identity != spec['sourceSha256']:
        raise ValueError('Frozen campaign candidate identity changed')
    catalog = json.loads((ROOT / 'mods/rtsai/campaigns/missions.json').read_text())
    incoming = {m['id']: m for m in json.loads((candidate / 'missions.json').read_text())}
    receipts = []
    for mission in catalog:
        original = {k: v for k, v in mission.items() if k != 'briefing'}
        source = {k: v for k, v in incoming[mission['id']].items() if k != 'briefing'}
        if original != source:
            raise ValueError('Objective/catalog mismatch: ' + mission['id'])
        src = candidate / 'maps' / mission['id']
        dst = ROOT / 'mods/rtsai-topdown/campaigns/maps' / mission['id']
        native = (dst / 'map.yaml').read_text(encoding='utf-8')
        geometry = (src / 'map.yaml').read_text(encoding='utf-8')
        if 'RequiresMod: rtsai-topdown' not in geometry:
            raise ValueError('Wrong Classic profile')
        output = geometry.split('Rules:', 1)[0] + 'Rules:' + native.split('Rules:', 1)[1]
        for filename in ['map.bin', 'map.png']:
            shutil.copyfile(src / filename, dst / filename)
        write(dst / 'map.yaml', output)
        receipts.append({'id': mission['id'], 'geometry_input': 'maps/' + mission['id'],
                         'native_objectives': 'OpenRA.Mods.RTSAI/Traits/RTSAICampaign.cs',
                         'native_objective_rule_sha256': hashlib.sha256(re.sub(r'^\t\t\tBriefing: .*$', '', native.split('Rules:', 1)[1].split('\nFluentMessages:', 1)[0], flags=re.M).strip().encode()).hexdigest(),
                         'output': {}})
    for mission in catalog:
        mission['briefing'] = incoming[mission['id']]['briefing']
    briefings(catalog)
    write(ROOT / 'mods/rtsai/campaigns/missions.json', json.dumps(catalog, ensure_ascii=False, indent=2) + '\n')
    for receipt in receipts:
        dst = ROOT / 'mods/rtsai-topdown/campaigns/maps' / receipt['id']
        receipt['output'] = {f: hashlib.sha256((dst / f).read_bytes()).hexdigest()
                             for f in ['map.yaml', 'map.bin', 'map.png', 'briefing.ftl']}
    write(ROOT / 'mods/rtsai-topdown/campaigns/geometry-provenance.json',
          json.dumps({'schema': 1, 'inputSourceSha256': identity, 'missions': receipts,
                      'transforms': ['preserve native mission rules, difficulty and briefings',
                                     'use square-mode source coordinates and tile vocabulary',
                                     'omit browser-only inline weapon dependencies',
                                     'publish briefings through native Fluent map resources']}, indent=2) + '\n')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--web-source', type=Path)
    ap.add_argument('--classic-candidate', type=Path)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    ROOT = args.output.resolve()
    if args.classic_candidate:
        classic_candidate(args.classic_candidate.resolve())
    elif args.web_source:
        WEB = args.web_source.resolve()
        controller()
        content()
    else:
        ap.error('an explicit frozen input is required')
    print('Imported explicit campaign inputs into native output: ' + str(ROOT))


