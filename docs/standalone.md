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
the whole resource layer, so the generated tileset sets 0. Diagonal generated roads show a one-cell staircase edge.

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
control, nuclear reactor, psychic sensor, cloning vats and missile silo leave the modern rosters. **The cuts are a
design decision for the owner to confirm.**

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
python tools/standalone-smoke.py skirmish --observe --map twin-fords --bots Multi0:normal:israel,Multi1:normal:yemen     --seconds 360 --out <scratch>/match       # --look X,Y holds the camera on a cell
```

The worktree's `engine` is a junction to the art-preview worktree's built engine (gitignored). The C# on this branch
is unchanged, so no build is needed.
