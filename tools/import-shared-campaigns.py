#!/usr/bin/env python3
"""Import project-authored browser factions and campaigns into both native profiles.

Run after build-classic-mode.py. No commercial game content is copied.
The browser campaign controller is adapted into a per-world native trait.
"""
from pathlib import Path
import json
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT.parent / 'RTSAI-WebGame'


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8', newline='\n')


def controller():
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
    source = source.replace('\n\t\t\tif (states.Any', '''
			for (var i = 0; i < states.Count; i++)
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
            countries += f'\n{actor}:\n\tVoiced:\n\t\tVoiceSet: {voice}\n'
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
            source = source.replace('\tWorld:\n', '\tWorld:\n\t\tRTSAICampaign:\n\t\t\tMission: '+mission['id']+'\n\t\tObjectivesPanel:\n\t\t\tPanelName: MISSION_OBJECTIVES\n\t\tMissionData:\n\t\t\tBriefing: '+json.dumps(mission['briefing'])+'\n')
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


if __name__ == '__main__':
    controller()
    content()
    print('Imported 16-country overlay and six campaigns into both standalone native modes.')


