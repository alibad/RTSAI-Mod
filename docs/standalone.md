# Standalone RTS AI: playable without Red Alert 2

Branch `rtsai/standalone`, rebased onto RTSAI-Mod main (`57df33c`). First measured on 6 October 2026.

The owner's goal: "you should not need red alert to play the ra2 mod". RA2 was never released as freeware, so its
files cannot be shipped. A standalone build has to load only project-made or properly licensed files. This page is
the first phase: what the game loads from EA today (measured), a plan, and a boot prototype.

**[ran]** means a command was run and its output read. **[inferred]** means reasoning, not a run.

## Status, 7 October 2026

Rebased onto RTSAI-Mod main `57df33c` (the promoted art); measurements below were re-run there.

### Phase 1: done [ran]

- **Two mods.** `mods/rtsai` is the standalone game: the 7 modern factions, no content installer, no archive
  formats, one theatre. `mods/rtsai-classic` is the optional add-on with the 9 original factions, the 27 Westwood
  maps, the original tilesets, music and cursors; it needs the player's own RA2 files (`mods/rtsai-content` now
  installs for `rtsai-classic`). Its manifest is generated from the standalone one by
  `tools/build-classic-manifest.py`, so shared files are listed once.
- **Modern-only rosters** (`modern-factions/modern-scope.yaml`, shared by both mods): the original heroes (Chrono
  Commando, Yuri Prime) are no longer won by infiltrating a tech centre, and a destroyed building drops the owner's
  own riflemen instead of a GI or conscript (new `SurvivorReplacements` player trait in `OpenRA.Mods.RA2`). The Flak
  Track, amphibious transport and landing craft stay: they are the modern factions' only AA track and naval
  transports, and Phase 3 reskins them.
- **Provisional identity "RTS AI"** in one place: the `-product-name` term in `languages/identity.ftl`. Window title,
  mod title and the menu note use it; bots are "Normal AI", "Rush AI", and so on. `ModTabTitle` and
  `PACKAGING_DISPLAY_NAME` cannot use Fluent; the check below makes `ModTabTitle` match.
- **The no-EA test.** `OpenRA.Utility rtsai --check-standalone` runs in `make test` (both `make.ps1` and `Makefile`).
  It fails on a content installer, a mounted player-content path, a registered archive format, a mounted package
  that is not a mod or engine folder, any archive/video file in the mod, any unresolved sprite, tile, model,
  palette, cursor, chrome, font or load-screen reference, Red Alert/RA2/Westwood/C&C wording in shipped text, and a
  classic manifest that lacks a shared file. Missing audio and placeholder stand-ins are warnings until Phase 3
  lands (`--strict` makes them errors). Today: passed, 2 warnings (712 sound names unresolved, 1,933 placeholders).
- Also fixed: an upstream indentation bug in `audio/voices.yaml` made `DisablePrefixes` a voice, so prefixed death
  voices looked up nonexistent files. Ogg is a registered sound format (the audio agent's music).
- Checks: `--check-yaml` passes for both mods (the add-on with owned content mounted, all 28 maps); boot to the main
  menu with the "RTS AI" title; a Türkiye vs Hezbollah bot skirmish ran 5 minutes with 0 exceptions.

### Phase 2: done [ran]

Everything below is drawn or rendered by code in this repository; nothing reads an RA2 file.

| Item | What it is | Tool |
|---|---|---|
| Shroud and fog | 48 edge masks for ShroudRenderer's extended index, soft smoothstep edges, tiles that partition pixels exactly; fog is the same set at 55% | `tools/standalone-art.py shroud` |
| Temperate tileset | All 511 templates of the RA2-compatible table (same ids, sizes, terrain types, heights, ramps), rebuilt as geometry: engine ramp planes, cliff walls, material blending that continues across template seams. Rendered in Blender (Cycles, CPU), cut per tile pixel-exactly, quantized to one 254-colour palette. Plus 60 corner-transition templates (ids 1000+) for generated maps. 763 indexed sheets, 3.1 MB | `tools/standalone-terrain.py`, `tools/terrain/blender_batch.py` |
| Minimap | Radar colours (MinColor/MaxColor) measured from our rendered tiles; map previews drawn the way `Map.SavePreview` draws them | same, and `tools/standalone-maps.py` |
| Ore and gems | 20 ore and 12 gem variants at 12 densities, rendered in Blender with baked shadows | `tools/standalone-terrain.py --resources` |
| Cursors | 117 cursor sequences (556 frames) and the rally point marker, with the standalone's own `cursors.yaml` | `tools/standalone-art.py cursors` |
| Palettes | A project general palette replaces cameo, palette, mousepal, citytem, libtem, temperat and the rest; the terrain palette comes from the tileset. Two RA2 palette names remain for the Phase 3 deliveries: `anim.pal` (effects) and `unittem.pal` (until the base kit's `kitbase.pal` is wired) | `tools/standalone-art.py palettes`, `standalone/rules.yaml` |
| Chrome | chrome, dialog, buttons, strategic, music player and load screen atlases redrawn in place (every chrome.yaml rectangle), dark steel with a teal or amber accent; the Allied eagle and Soviet hammer-and-sickle are replaced by an RTS AI radar-scope emblem | `tools/standalone-chrome.py` |
| Orphan bits | The 20 unrecorded upstream files are gone: pips, build clock, construction-yard cameos, markers, bomb, classic cursors and cameo chevron redrawn; isodepth re-derived from its formula (identical indices: a lookup table); four edited RA2 sprites removed (the classic add-on uses the player's originals) | `tools/standalone-art.py bits` |
| Maps | **Twin Fords** (point-symmetric: river, two fords, home ore, gems by the fords) and **Harbor Line** (mirror-symmetric: north sea for naval play, central lake with gems). Author: RTS AI (generated). The 27 Westwood maps are classic-only | `tools/standalone-maps.py` |

Checks: `--check-yaml` and `--check-missing-sprites` pass for both mods (the add-on with owned content mounted);
`--check-standalone` passes with two warnings (712 sound names unresolved, 980 placeholder files: the Phase 3
debt). Bot matches with no exceptions: Israel vs Yemen on Twin Fords (6 min), Türkiye vs Iran on Harbor Line
(5 min). Placeholder debt went from 1,933 to 980 files.

Found on the way: the RA2 table's tile `ZOffset: -15` assumes TMP tiles with per-pixel depth; on flat tiles it hid
the whole resource layer, so the generated tileset sets 0. Diagonal generated roads showed a one-cell staircase
edge (fixed in Phase 3).

### Phase 3: art and audio complete [ran]

- **Base kit v2 wired** (`tools/standalone-kit-rules.py` writes `standalone/base-kit.yaml`, standalone only).
  - The 22 stock buildings the modern factions use render their kit role, painted per faction, in the kit palette
    with the player-colour remap.
  - The Soviet-side power plant, barracks, service depot and tech centre take the Allied footprints the kit is drawn
    for.
  - The two superweapon slots are the Strategic Uplink (Chronosphere function) and the EW Array (Iron Curtain
    function).
  - The classic add-on keeps the original buildings.
- **Shared units and effects wired** (art agent, approved):
  - Kit sprites for the MCVs, harvesters, AA track, amphibious APC, landing craft, engineer, operative and K9 dog.
    Each draws a combined image `unit-<role>-<faction>`: first the stock templates whose effects its traits play,
    then the kit image.
  - The effects batch, with the 20 PNG-delivered effects repointed by stem.
  - Rank chevrons drawn by us.
  - Art provenance: `standalone/ART-PROVENANCE-STANDALONE.json` (421 files), `docs/standalone-art-provenance.md`.
- **No placeholder left for anything the factions can field.**
  - The 980-file placeholder pack still answers the sequences of actors they cannot field, so every sequence keeps
    loading.
  - `make test` runs `--check-standalone --strict`. These fail the build: any placeholder or missing sound for a
    fieldable actor, any sequence whose frames do not resolve, and any palette served by the placeholder pack.
  - **"Fieldable" covers everything a game can draw.** The check reads every string of the traits of:
    - the factions' reachable actors;
    - the World and Player actors;
    - the actors on the standalone maps;
    - the actors the World spawns, such as crates.

    That holds whatever the field is called, and it follows nested warheads and weapons. An actor's look is its
    render image per faction.
  - The wider check found 27 more placeholder files that the earlier field-name rule missed. They are replaced by
    code-drawn art:
    - the scorch marks and craters left by explosions (the "flat yellow disc");
    - the bonus crate, on land and afloat;
    - the move-order flash.
  - "player" and "effect" now use the kit and effects palettes.
  - The green blocks in the earlier screenshots were the starting dog and engineer before their kit art landed. A
    census of every actor type in a staged battle confirms none is left.
- **Audio wired**: the audio agent's SFX, UI sounds, stock-unit voices and music (plus its polish pass: loop seams,
  dog barks, death cries). 0 unresolved sounds for what the 7 factions can field.
- **Branded main menu** (`chrome/rtsai-mainmenu.yaml`, replacing the stock layout; same widget ids and logic):
  - a full-window backdrop of one flagship per faction (Qilin, Karrar, Bozkir, M1A2S, Merkava, the Yemeni launcher,
    Hezbollah rockets), rendered from the project's own GLB meshes in RTSAI-Art on a procedural desert at golden
    hour (`tools/standalone-menu.py`, Blender Cycles on the CPU). The new `CoverImageWidget` scales it to cover any
    window, and the vehicles stay inside a safe area, so 16:10 and 4:3 windows crop only sky and sand;
  - the product name from `-product-name`, in a new 56 px `Hero` font;
  - the version line shows the manifest version for packaged builds (`make version`), and otherwise the git commit
    the mod assembly was built from (an MSBuild stamp), instead of `{DEV_VERSION}`;
  - the forum-account box is now a single small link at the top right;
  - no news box and no content manager.
- **Roads, rivers and coasts without staircases** (`tools/standalone-maps.py`):
  - **Roads** run along the cell axes (2:1 on screen) and the screen horizontal and vertical. Each road is a Z of
    those legs and stays symmetric.
  - **Twin Fords' river** banks and **Harbor Line's coast** use the cell axes only. A boundary along an axis crosses
    the corner-transition templates through two adjacent corners and draws one straight edge. A horizontal or
    vertical boundary alternates one- and three-corner templates: fine under a wide road, but a sawtooth along a
    thin shore.
  - The fords are cut along an axis, and the central lake is an octagon with clean sides.
  - **Twin Fords has a third crossing** at its symmetry centre. The balance agent measured 37% draws on Twin Fords
    at the 40-minute cap (e2efdd2, 252 games). A drawn game there is not a stall but a grind at the two fords:
    income holds at about 2,800 a minute, and both sides spend it all. The central crossing has no road, because a
    road there would cross the home ore. Ore and gems are unchanged (306 resource cells).
    - With the central crossing and the round-5 candidate rules, Twin Fords draws fell from 38% to 19%, and the median
      game from 32.9 to 25.1 minutes. First-slot score was 47%, so the map stays fair.
    - The two gem fords were then widened by 50% (half-width 2.6 to 3.9 cells), so the combined draw rate lands
      safely under 15%.
    - **Result** (balance round 5 final: 841e844 with the round-5 rules, 252 games): draws are 16% overall, Harbor
      Line 11% and Twin Fords 21%. Every faction scores 43–60%, and the Allied side scores 54% (46–62) against the
      Soviet side. See `docs/balance.md`.
    - **Per-map side lean.** The Allied side scores 65% (54–75) on Harbor Line and 42% (32–54) on Twin Fords.
      - My call: no map change. Both maps are exactly symmetric, so their geometry gives neither start position an
        edge. A side lean comes from how the rosters fit the terrain:
        - Harbor Line is open ground with a sea;
        - Twin Fords is crossings that favour massed infantry and rockets.
      - Harbor Line was 40% before the round-5 rules (coaxial machine guns on the Allied-side tanks), so the lean
        there follows the rules. Twin Fords' 42% is within noise.
      - Biasing a symmetric map toward one side would only hide a roster question. The levers are in the rules
        (open-field tank fights; the naval units on Harbor Line). This is left for the next balance round.
- `--check-standalone` also fails on chrome sheets that are not power-of-two sized (the renderer refuses them at the
  first draw). `--list-placeholders` prints every placeholder still in use.

**Cut buildings: what the modern rosters lose** (owner decision, 7 October 2026). These eight leave the standalone
rosters (`Buildable: Prerequisites: ~disabled`); the classic add-on keeps them. Numbers are from the resolved rules.

| Cut building | Side | Cost / power | Role lost | For the balance pass |
|---|---|---|---|---|
| Ore Purifier `gaorep` | Allied (China, Türkiye, Saudi, Israel) | 2500 / −200 | +25% on every ore delivery | Allied-side late income is 20% lower than with it. Candidates: a refinery upgrade, cheaper harvesters, or more ore value |
| Nuclear Reactor `nanrct` | Soviet (Iran, Yemen, Hezbollah) | 1000 / +2000 | Bulk power at 0.5 credits per power | Only the power plant is left: 150 power for 600 (4 credits per power, the Allied rate is 200 for 800). Replacing one reactor takes 13 plants and about 8 times the credits. It now uses the Allied 2×2 footprint and kit art, so it could also give 200 |
| Cloning Vats `naclon` | Soviet | 2500 / −200 | A free copy of each infantry unit produced | Soviet-side late infantry output halves |
| Missile Silo `namisl` | Soviet | 5000 / −200 | Damage superweapon (nuke, 15000-tick charge) | No faction keeps a damage superweapon. The two kit slots are utility powers; only Israel and Saudi Arabia have a strike power (`AirstrikePower@falcon`). Late sieges may stall |
| Weather Control `gaweat` | Allied | 5000 / −200 | Damage superweapon (lightning storm, 15000-tick charge) | Same as above |
| Spy Satellite `gaspysat` | Allied | 1500 / −100 | Reveals the whole map | Allied-side late scouting rests on units |
| Gap Generator `gagap` | Allied | 1000 / −100 | Shroud over a 10-cell radius | Base concealment is gone. A defence role, but a minor one |
| Psychic Sensor `napsis` | Soviet | 1000 / −100 | Detects cloaked units within 6 cells | Small loss: every faction keeps roster detectors (Iran: drone control, Ghadir, Peykaap; Yemen: Mokha, spotter; Hezbollah: relay, spotter, survey, workshop) and the dog |

**What replaces them** (coordinator, 7 October 2026; `tools/standalone-kit-rules.py`):

| Piece | Side | Numbers | Notes |
|---|---|---|---|
| Heavy Power Plant (the reactor actor `nanrct`, kit role `hpwr`) | Soviet | 2000 power for 1000 credits, needs the tech centre | The reactor's economics come back: 0.5 credits per power. One plant replaces the 13 light plants the cut would have needed. It dies like any building (no nuclear blast). Bots already treat it as their best power type. Footprint 3x3 on the kit's `hpwr` art |
| Ore Purifier refinery upgrade (`gapurifier`) | Allied | 1000 credits and 50 power per refinery, needs the tech centre | A plug placed onto a refinery (TS-style `Pluggable`). That refinery pays 125% for ore (`ResourceValueMultiplier`). The old purifier gave +25% on every refinery for 2500. Bots build it. The kit draws a purification tower on upgraded refineries |

The other six roles get no direct replacement: their jobs are covered or minor (see the table above). The two
superweapon slots stay the kit's utility powers.

**Bots and superweapons.** The stock support-power module cannot aim a teleport (that needs a source and a
destination), and it has no rule for a protection field. A new `SuperweaponBotModule` (OpenRA.Mods.RTSAI) handles
both:
- **Strategic Uplink:** moves the most valuable army group (worth at least 3000) beside the most valuable known enemy
  building cluster that the group can take on. The cluster must be at least 24 cells away, and its defence must be
  worth no more than 125% of the group. The group then attack-moves. The units return after 30 seconds.
- **EW Array:** covers the most valuable army group (worth at least 1800) when enemy armed units worth 1000 or more
  are within 7 cells.

Every bot profile builds both buildings. The base builder now builds a plug only while some own building still
accepts one.

The Israeli and Saudi precision strikes (`AirstrikePower@falcon`, on the r2ilrecon and r2falcon commandos) had no
bot rule either. The stock support-power module now aims them at the most valuable known enemy structures or
vehicles: at least 1000 worth within 3 cells, and never near own units. In 6 test matches with the commandos'
20-minute bot delay lifted, the replays hold 11 strike orders. With the delay, strikes stay rare, because the
commandos come late.

**No stock names on screen.**
- The shared text keeps Red Alert 2's coined names, which the classic add-on shows with the player's own files.
  The standalone game loads `standalone/names.ftl` last, generated by `tools/standalone-names.py`.
- That file overrides every message that uses one of these names, so the AI co-commander's actor names, which it
  reads through Fluent, change too:

  | Stock name | Standalone name |
  |---|---|
  | Tesla Reactor | Power Plant |
  | Chrono Miner | Ore Harvester |
  | War Miner | Armed Harvester |
  | Flak Track | AA Carrier |
  | Airforce Command Headquarters | Airfield |
  | Battle Lab | Tech Center |
  | War Factory | Vehicle Factory |
  | Allied Wall, Soviet Wall | Wall |

  The service depot's mention of Terror Drones is gone, the refinery upgrade is the Refinery Purifier, and unit
  descriptions follow the new building names.
- `--check-standalone` fails on any such name, or any other stock unit, building or faction name, in the text of
  anything the factions can field. `--list-names` prints every name a player can see. `make test` also fails when
  `names.ftl` is stale.

**Hezbollah's flag.** The lobby and tooltip flag is the real flag, set on RTSAI-Mod main (owner decision,
7 October 2026; see `docs/art-provenance.md` for its non-free status and the risks the owner accepted).

**Ore mines (found while measuring).** In the first smoke, bots stalled. Twin Fords and Harbor Line had no ore spawn,
so the fields ran dry by about minute 10. Both sides then sat at 0 credits for the rest of the game, nobody reached a
tech centre, and half the games hit the cap. The Westwood maps regrow ore from the stock ore drills, which are EA art.
- The fix is our own ore mine (`oremine`, `tools/standalone-terrain.py --mines`): a rock mound with an ore vent and a
  burst animation, rendered like the ore piles.
- There is one at the centre of each home field, 4 per map.
- The generated maps also moved to `mods/rtsai/standalone/maps`. Their corner-transition templates do not exist in
  the classic tilesets, so the classic add-on, which mounts `ra2|maps`, failed to load them.

**Standalone balance smoke** [ran], the first run before the fixes above: `tools/balance-harness.py run --campaign standalone-smoke --standalone`.
- Setup: headless, no RA2 content linked anywhere, the 7 factions on the base kit, Twin Fords and Harbor Line.
  Every pairing was played from both spawn orientations with the normal bot and a 40-minute cap: 84 matches.
- **Stability:** 84 of 84 complete. No crash, hang, exception or Lua error.
- **Endings:** 44 conquests, 40 draws at the cap (48%). Median length 22.5 game minutes; Harbor Line 19.1,
  Twin Fords 31.7.
- **Map fairness:** first-slot score 56% on Harbor Line and 46% on Twin Fords (42 games each, within noise).
- **Factions:**

  | Faction | Score (draw = ½) | W-D-L |
  |---|---|---|
  | Saudi Arabia | 56% | 10-7-7 |
  | Israel | 54% | 6-14-4 |
  | Hezbollah | 54% | 9-8-7 |
  | Yemen | 52% | 6-13-5 |
  | Iran | 50% | 5-14-5 |
  | China | 42% | 4-12-8 |
  | Türkiye | 42% | 4-12-8 |

  All 95% intervals overlap 50%. Nothing is broken; China and Türkiye are the ones to watch.
- Every faction built power, refineries, production and tech on the kit: about 3 power plants and 15 structures
  per game.
- What it showed:
  - No bot built a superweapon: the bots had no rules for the two kit powers.
  - Half the games reached the cap. The main cause turned out to be the dry ore fields, not the cuts.
  - Both are fixed above, and the comparison below measures the cuts.

**What the cuts cost: the comparison** [ran]. Campaign `standalone-cuts`, run from a frozen worktree at `300a377`
(heavy plant still on its interim 2x2 art). Each arm is 84 headless bot matches: the 7 factions on Twin Fords and
Harbor Line, every pairing from both spawn orientations, normal bot, 40-minute cap, no RA2 files. All three arms
share the ore mines and the superweapon bot module.
- **precut:** the 8 buildings restored with their original rules (reactor 4x4), no refinery upgrade.
- **nocomp:** the cuts, with no heavy plant and no refinery upgrade.
- **now:** the standalone game.

| | precut | nocomp | now | first smoke (no mines, no superweapon bots) |
|---|---|---|---|---|
| Completed, no crash or hang | 84/84 | 84/84 | 84/84 | 84/84 |
| Draws at the 40-min cap | 17 (20%) | 19 (23%) | **13 (15%)** | 40 (48%) |
| Median length (min) | 20.8 | 24.0 | 19.8 | 22.5 |
| Players who reached a tech centre | 61% | 67% | 57% | 48% |
| Soviet side: credits per unit of power | 1.72 | 4.00 | **1.74** | 4.00 |
| Soviet side: power built per game | 1876 | 673 | 1847 | 450 |
| Soviet side's score against the Allied side (48 cross-side games) | 60% | 72% | 68% | 53% |
| Strategic Uplink teleports / EW Shields fired | 26 / 2 | 31 / 1 | 19 / 11 | 0 / 0 |
| Refinery upgrades placed | – | – | 105 | – |

Faction scores (draw counts as half; 24 games each, 95% intervals about ±20 points):

| Faction | precut | nocomp | now |
|---|---|---|---|
| China | 23% | 40% | 31% |
| Iran | 52% | 62% | 73% |
| Türkiye | 46% | 33% | 40% |
| Saudi Arabia | 56% | 48% | 40% |
| Israel | 54% | 35% | 54% |
| Yemen | 62% | 62% | 48% |
| Hezbollah | 56% | 69% | 65% |

Reading:
- **Power economy fixed.** The cuts quadrupled the Soviet side's power price, and the heavy plant brings it back to
  the pre-cut figure (1.74 against 1.72 credits per power).
- **Draws** come mostly from Twin Fords: 12 of the 13 in `now`. Its river with two fords makes for long sieges.
- **In bot play the cuts did not weaken the Soviet side; they strengthened it** (60% → 72% against the Allied side,
  68% with the compensation). Pre-cut Soviet bots put about 7,500 credits per game into cloning vats and missile
  silos, which the cut frees for armies. The difference is within noise on 48 games, but it points the same way in
  both arms.
- **For the balance pass:**
  - China trails in every arm (23–40%).
  - Iran and Hezbollah lead.
  - The Allied side as a whole is about 10–20 points behind against the Soviet side.
  - The bots never fire the Israeli and Saudi strike powers (`AirstrikePower@falcon`): there is no bot rule for
    them.

### Deliverables for Phase 3

The exact file lists are in `docs/standalone-deliverables.json` (`tools/standalone-deliverables.py`, from an audit of
the add-on with owned content mounted). Keep the listed file names; for sprites, at least the listed frame counts.
The standalone manifest already mounts the delivery folders after the placeholders, so a delivered file overrides
its stand-in as soon as it lands.

| For | Folder | What |
|---|---|---|
| Art agent: base kit | `mods/rtsai/standalone/base/` | 13 roles × 7 factions: `cnst`, `powr` 2x2, `refn`, `barr` 3x2, `weap`, `radr` (Soviet side), `airf` (Allied side), `yard`, `dept` 3x3, `tech` 3x2, `sw1` (Chronosphere art), `sw2` (Iron Curtain art), `wall`; `<kit>-<faction>.shp`, `kitbase.pal`, `<kit>-<faction>icon.png`, `kit-sequences.yaml`. Replaces 22 stock buildings (229 EA sprite files); the other 8 are cut |
| Art agent: shared units | `mods/rtsai/standalone/units/` | MCV (amcv, smcv), harvester (cmin, harv), engineer, dog, spy, AA track (htk), amphibious transport (sapc), landing craft (lcrf): 38 EA sprite files and 12 EA voxel models (24 VXL/HVA files) |
| Art agent: effects | `mods/rtsai/standalone/effects/` | 22 shared effect images (95 EA files: explosions, pips, rank, parachute, wake, smoke, crate, beacon, rally point, flameguy...) + 8 stock files named in modern-unit sequences (`fire01-03`, `gunfire`, `lgrysmk1`, `sgrysmk1`, `vtmuzzle`, `yuricntl`); `anim.pal` |
| Audio agent | `mods/rtsai/standalone/audio/{sfx,ui,voices,music}/` | 77 weapon/impact SFX (+4 names missing even in RA2), 14 UI sounds, 108 stock-unit voices (+3 missing), new `music.yaml` (Ogg) |

Rules decisions taken with the art agent, to apply when the kit lands: the Soviet-side power plant, barracks,
service depot and tech centre take the Allied footprints; the ore purifier, gap generator, spy satellite, weather
control, nuclear reactor, psychic sensor, cloning vats and missile silo leave the modern rosters. The owner confirmed
the cuts on 7 October 2026. Both decisions are applied (see Phase 3 above).

## How it was measured [ran]

`tools/standalone-audit.py` compiles `tools/standalone-audit/StandaloneAudit.cs` (an OpenRA utility command) against
the mod's engine and runs it in a sandbox with the owned RA2 content mounted read-only. Every reference is resolved
through the engine's own file system, which gives the real mount order, explicit prefixes and mod overrides. That
covers every sprite of every image in all three tilesets, terrain templates, voxel models, palettes and other
`Filename` fields, cursors, chrome, fonts, the load screen, voices and notifications per faction, music, and sound
names in rules and weapons. It also computes which actors each faction can reach in a skirmish (starting units,
prerequisites, production queues, transforms, free and spawned actors). From EA packages it reads only names, frame
counts and frame sizes.

```
python tools/standalone-audit.py --content ../OpenRA/Support/Content --out <scratch>/audit.json --summary
python tools/standalone-audit.py --out <scratch>/standalone.json --summary      # same audit, no EA content
```

## Inventory: what the RA2-mode mod loads from EA

The counts are unique files. "Modern scope" means what the 7 modern factions can actually reach in a skirmish.

| Category | EA items (measured) | Already project-made | Still EA in modern scope | Effort |
|---|---|---|---|---|
| Packages mounted | 25 EA packages (23 MIX, 1 BAG, the content folder), 7,383 entries; `rtsai-content` installer with 4 sources | — | All 25 (prototype mounts none) | done in prototype |
| Terrain | 3 theatres, 1,694 templates, 2,269 tile files, all EA; tile radar colours copied from them | 0 | 1 theatre minimum (temperate, 511 templates) | **L** |
| Maps | 27 of 28 shipped maps are `Author: Westwood Studios` conversions on EA tiles; 19,718 actor instances, 18,007 of them EA-only scenery, civilian or tech actors; ore/gem fields on all 27; previews rendered from EA tile colours | 0 (blank shellmap is upstream) | all; ship original maps instead | **M** |
| UI chrome | 10 files, all shipped by the mod: 6 identical to the upstream OpenRA RA2 mod (chrome, dialog, load screen, music player, spawn points, strategic), `buttons.png` = upstream + project flags; Allied-eagle and Soviet-star emblems in the RA2 style | flags, faction-flag sheets, engine glyphs | 6 upstream files (provenance not established; RA2-style emblems) | **M** |
| Cursors, palettes, fonts | `mouse.shp` EA (112 cursor sequences); 17 EA palettes (`unittem.pal`, `isotem.pal`, `cameo.pal`, `anim.pal`, ...); fonts are the engine's FreeSans (GPL) | 2 cursors, 83 palettes | `mouse.shp`, 17 palettes | **S** |
| Upstream mod bits | 20 sprites identical to upstream (pips, `isodepth`, waypoint, spawn, camera) | — | 20, provenance unverified (`pipsra.shp` looks RA1-derived) | **S** |
| Shared buildings | 30 stock buildings reachable (15 Allied-side for China/Türkiye/Saudi/Israel, 15 Soviet-side for Iran/Yemen/Hezbollah) incl. RA2 superweapons (Chronosphere, Weather Control, Iron Curtain, Nuclear Silo, Psychic Sensor, Cloning Vats); 284 EA sprite files with build-palette icons | 0 | all 30 | **L** |
| Shared units | 16 stock units: 2 MCVs, 2 harvesters, engineer, dog, spy, sell-spawned GI/conscript, burning-death `flameguy`, still-buildable stock specials (Chrono Commando, Yuri Prime, Flak Track, amphibious APC, landing craft), the airstrike reveal camera; 34 EA sprite files, 12 EA voxel models | 0 | all 16 (5 can simply leave the modern rosters) | **M** |
| Modern units | 142 actors (122 buildable + husks and drones) | 246 sprite files (incl. 122 icons), 69 voxel images, all project | 16 stock FX files inside their sequences (below) | done |
| Effects | 55 shared effect images, 308 EA files; modern scope uses 22 images (94 files: explosions, pips, rank, chrono, crate, parachute, wake, smoke, beacon, rally point) plus 16 stock files named in new-unit sequences (`gunfire`, `vtmuzzle`, `sgrysmk1`, `lgrysmk1`, `fire01-03`, `mgun-*`, `yuricntl`); shroud and fog | 0 | 110 files + shroud | **M** |
| Weapon, impact and UI SFX | 163 EA sound files named in rules and weapons; 14 EA UI sounds | 23 | 88 rule/weapon SFX (56 used by modern units' own weapons) + 14 UI | **M** |
| Unit voices | modern units: 244 project, 9 EA; stock units in modern scope: 180 EA | 244 | 189 | **S** |
| Announcer (EVA) | modern factions 777 project; original factions 222 EA | 777 | 0 | done |
| Music | 16 EA tracks (`theme.mix`) | 0 | 16 | **S-M** |
| Original factions | 9 factions (America ... Russia), 54 actors only they reach: 147 EA sprite files, 42 voxel models, 446 voice and 222 EVA files | — | out of scope | **S** (cut) |
| Scenery and civilians | 204 actor types placed on the maps (664 files) + 336 files of editor-only scenery: 1,000 EA sprite files | — | only what new maps use | **M** |
| Naming | window title "RTS AI — Red Alert 2", mod tab "Red Alert 2", bots "RA2 Normal AI", prerelease prompt, stock unit names | — | all | **S** |

Totals: 1,744 EA sprite files, 2,269 EA tiles, 172 EA VXL/HVA files (62 stock voxel images), 17 palettes,
1 cursor sheet, 966 EA sound files, 16 music tracks. The standalone modern scope needs replacements for about
430 sprite files (shared base, shared units, effects), one tileset, maps, chrome and about 300 sounds.

## Recommended scope

- **Default:** the 7 modern factions only, on a project-made modern base, project tilesets and original maps.
- **Original factions:** not in the standalone build. If the owner wants them, ship them as an optional "classic
  content" add-on that imports the player's own RA2 files, which is today's `rtsai-content` installer moved to its
  own mod.
- **Shared base:** one modern base kit (about 11 buildings), tinted per side, instead of 30 RA2 buildings. Replace
  RA2's signature superweapons with modern-doctrine powers, or cut them.

## Replacement approach per category (reuse our pipelines)

| Category | Approach | Pipeline |
|---|---|---|
| Terrain | One original temperate theatre first, about 40-60 templates: clear/rough/sand, water and shores, cliffs, ramps, roads, bridge ends. Height-field meshes rendered top-down in Blender at 60x30 into TS TMP (with depth), then a radar colour and minimap preview from our own tiles | Blender CPU render (as `glb_prerender.py`), new TMP writer |
| Maps | 2 original 1v1 maps first, then 4-6; Workshop seeded maps already export `.oramap` | RTSAI-Web `/workshop` export |
| Shared buildings and units | Modern base kit and MCV/harvester/engineer/dog/spy as GLB, then prerendered SHP with make/damage/destroy frames; `e1`/`e2` sell-spawns become each faction's rifleman (rules only) | `glb_prerender.py`, building and infantry routes in art-preview |
| Effects | Procedural sprite sheets for muzzle flashes, explosions, smoke, fire, debris, shroud/fog edges, ore/gems, pips | Python/Blender, new effects route |
| Chrome, cursors, palettes | Original sidebar/dialog chrome (no faction emblems from RA2), a code-drawn cursor set, palettes computed from our art | PIL/SVG + Qwen-Image (Apache-2.0) backgrounds |
| SFX | Generated or CC0/royalty-free SFX with a per-file provenance record like `audio/PROVENANCE.json` | new; licence check per source |
| Voices | Stock-unit lines (MCV, harvester, engineer, dog, spy) with the existing licensed TTS chain | Kokoro / Chatterbox / MOSS |
| Music | A licensed set, or a generator whose weights allow commercial redistribution (check before use) | licence review first |

Effort key [inferred]: S = days, M = 1-2 weeks, L = 2-4 weeks of agent work, each with owner review.

## Naming (decision for the owner)

"Red Alert" and "Command & Conquer" are EA trademarks. A standalone release should not use them in its name, window
title, store text or bot names. Proposed wording, to be decided by the owner:

- Product: **RTS AI**, "a modern-era real-time strategy game built on OpenRA".
- Window title: "RTS AI". Bots: "Normal AI", "Rush AI", and so on.
- Optional add-on, if kept: "Classic content: imports the Red Alert 2 files you own. RTS AI is not affiliated with or
  endorsed by Electronic Arts." (stating compatibility, not branding).
- Also drop RA2-specific names and emblems from what ships (Chronosphere, Iron Curtain, Kirov, Tanya, Yuri, the
  Allied eagle and Soviet star art in the chrome).

## Phases to a playable standalone skirmish

1. **Clean boot (days).** Done as a prototype here. Add a modern-only rules split (no original factions in the lobby,
   sell-spawns become faction infantry, stock specials leave modern rosters), the renames, and a `make test` gate:
   `standalone-audit` must report zero EA files.
2. **One good-looking 1v1 (1-2 weeks).** The temperate theatre, 2 original maps, shroud/fog, ore, cursor, palettes,
   reskinned chrome, UI sounds. Placeholders still stand in for the base.
3. **The modern base (2-4 weeks).** Base kit, MCV, harvester, engineer, dog, spy, effects set, weapon SFX, stock-unit
   voices. Delete the placeholder pack.
4. **Release polish.** Second theatre, 4-6 maps, music, provenance pages, owner review gates, then a standalone alpha.
   The optional classic-content add-on comes after.

## Prototype: boot with no RA2 content [ran]

What changed on this branch:

- `mod.yaml`: `ContentInstallerFileSystem` replaced by `DefaultFileSystem` with only mod and engine packages; tilesets
  point at `standalone/tilesets/*.yaml`.
- `mods/rtsai/standalone/`: placeholders from `tools/standalone-placeholders.py` (1,936 files, 1.9 MB), drawn by code
  under the EA file names that rules and sequences still use: 1,744 sprite sheets (category-coloured shapes; build
  icons labelled "EA <name>"), 172 box VXL/HVA files in the player-remap ramp, 17 procedural palettes, a cursor sheet,
  and three tilesets with the same template ids, sizes and terrain types drawing flat coloured diamonds.
  `placeholders.json` holds only names, frame counts and frame sizes.
- `tools/standalone-smoke.py`: runs the rendered client with an empty support dir, the shared `game-window` lock, a
  `gpu-yield.txt` line and `OPENRA_AI_HOST=0`.

Results, all with an empty support dir (no `Content` at all):

| Check | Result |
|---|---|
| `--check-yaml` (all lints, 28 maps) | exit 0 |
| `--check-missing-sprites` (3 tilesets) | no missing files |
| `standalone-audit` with no content | every sprite, tile, model, palette, cursor, chrome and font resolves to the mod or engine; only audio is missing |
| Boot | first-run prompt and main menu over the shellmap; no content installer; no exceptions |
| Skirmish, 2 bots (China vs Iran, Tournament Map B), 7 min | 0 exceptions. Both bots deployed, built power, barracks, refinery with harvester, war factory, radar or airfield and defences, produced 14 modern unit and defence types, and fought (Lua census every 30 s) |
| Skirmish, host as China vs Iran bot | MCV deploys (scripted); build palette fills with the 9 shared Allied buildings as labelled placeholders |

What breaks or is wrong without EA content:

1. **Terrain:** flat diamonds only; cliffs, ramps and shores read badly; the minimap still shows the original
   maps' colours (radar colours copied from EA tiles).
2. **Shroud and fog** use EA sprites; the placeholder floods unexplored ground with yellow ellipses. It is the worst
   visual and the first thing to replace.
3. **Shared base:** the construction yard and every other stock building or unit is a box; their icons are labels.
4. **Effects:** explosions, muzzle flashes, smoke, fire, ore and gems are coloured blobs.
5. **Audio:** every EA sound is skipped silently. 27 distinct sound lookups failed in 7 minutes: weapons, deaths,
   impacts and one notification (`120.wav`). There is no music and no UI click sounds. The engine does not crash on
   missing audio.
6. **Identity:** the window title says "Red Alert 2", bots are "RA2 Normal AI", and the inherited chrome shows
   RA2-style faction emblems.
7. **Not exercised:** manual input (no clicks were simulated), the map editor, multiplayer, missions.

## Reproduce

```
python tools/standalone-audit.py --content ../OpenRA/Support/Content --out <scratch>/audit.json --summary
python tools/standalone-placeholders.py manifest --from-audit <scratch>/audit.json   # names, frames, sizes only
python tools/standalone-placeholders.py build
python tools/standalone-audit.py --out <scratch>/lint.txt --utility --check-yaml
python tools/standalone-smoke.py menu --out <scratch>/menu
python tools/standalone-smoke.py skirmish --observe --map tournament-2B \
    --bots Multi0:normal:china,Multi1:normal:iran --seconds 420 --out <scratch>/skirmish
python tools/standalone-smoke.py skirmish --lua deploy.lua --bots Multi1:normal:iran --faction china --out <scratch>/player
python tools/standalone-art.py all              # shroud/fog, cursors, palettes, orphan bits
python tools/standalone-chrome.py                # UI atlases
python tools/standalone-terrain.py               # Blender tileset (CPU, ~8 min); --resources for ore and gems
python tools/standalone-maps.py                  # Twin Fords, Harbor Line
python tools/build-classic-manifest.py           # after any manifest change (make test checks it)
python tools/standalone-smoke.py skirmish --observe --map twin-fords --bots Multi0:normal:israel,Multi1:normal:yemen \
    --seconds 360 --out <scratch>/match       # --look X,Y holds the camera on a cell
python tools/standalone-kit-rules.py             # base kit rules (after a kit delivery)
python tools/standalone-menu.py                  # main-menu backdrop (Blender, CPU, ~2 min); --quick for a draft
python tools/balance-harness.py run --campaign standalone-smoke --standalone --output <scratch>/smoke --parallel 10
python tools/standalone-terrain.py --mines              # the ore mine (Blender, CPU, seconds)
python tools/balance-harness.py run --campaign standalone-cuts --suite now --standalone --output <scratch>/now   # also precut, nocomp
python tools/standalone-smoke.py skirmish --lua showcase.lua --look 50,36 --map-rules tools/standalone-smoke/showcase-rules.yaml \n    --map twin-fords --bots Multi0:normal:saudi,Multi1:normal:iran --seconds 20 --out <scratch>/showcase
```

This branch changes C# (`SurvivorReplacements`, `--check-standalone`, the menu widgets), so build first: `./make.cmd all`, then
`./make.cmd test`. The worktree uses its own copy of the engine at the pinned commit (gitignored).
