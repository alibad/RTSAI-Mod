# Hezbollah doctrine: Salvo and Swarm

Status: **implemented** on branch `rtsai/hezbollah-doctrine` (local, from `main` 3db6883, main 5df5950 merged). Owner
gates: (a) design approved, (b) art approved at 1x/3x, (c) balance table: see "As built" at the end. Sections 1-8
are the approved design; where the build differs, "As built" says so.
Owner brief (2026-10-07): "basic missiles, very powerful soldiers, very mini drones". Every existing unit stays;
they are retuned, and the doctrine adds what it needs. The faction keeps its real flag.

**[ran]** = measured in the round-4 final (docs/balance.md, `docs/balance-data/r4-final*`). **[inferred]** = from rules.

## The doctrine in one line

Few fighters, many rockets, small drones: a small core of veteran infantry fights from cover, cheap rocket volleys
do the heavy lifting, and FPV teams launch regenerating micro-drones that anti-air and small arms can shoot down.

| Pillar | Existing units retuned | New | Signature mechanic |
|---|---|---|---|
| Basic missiles | Mobile Rocket Battery, Ridge Missile Team, Recoilless Technical, Coastal Missile Emplacement, Coastal Missile Boat | **Rail Technical** (cheap launcher) | Volume over precision: bursts of unguided rockets with scatter, lower unit costs |
| Powerful soldiers | Line Fighter, Ridge Missile Team, Field Spotter, Cedar Scout (hero) | none | Veteran from the barracks, faster promotion, cover on rough ground, stationary concealment |
| Mini drones | Loiter Drone (scaled down), Signal Post (link) | **FPV Team** + its **FPV Drone** | Operator launches 3 one-way micro-drones that regenerate; drones need the operator's link |

## Where Hezbollah stands now [ran]

Round-4 final: 57% (45-68) against the modern factions, 48% (30-67) against America and Russia, 54% (38-69) on the
naval map. Value destroyed per credit produced, land maps:

| Unit | Cost | Share of production | Destroyed / credit |
|---|---:|---:|---:|
| Line Fighter | 150 | 17% | 1.78 |
| Ridge Missile Team | 350 | 27% | 0.79 |
| Cedar Technical | 400 | 13% | 1.09 |
| Recoilless Technical | 550 | 11% | 0.60 |
| Cedar Scout | 1650 | 10% | 0.35 |
| Mobile Rocket Battery | 900 | 9% | **2.33** |
| Loiter Drone | 700 | 8% | **0.14** |
| Escort Gun Truck | 600 | 3% | 0.46 |
| Field Spotter | 525 | 0.6% | 0 |

The rocket truck is already the best trade and the drone the worst; the spotter is almost never built.

## 1. Basic missiles

Cheap, plentiful, unguided or simple. Volume and cost over precision: bursts of rockets with real scatter
(`Inaccuracy`), so they punish clusters, infantry and buildings and waste shots on a lone fast target.

| Unit | Now | Proposed | Why |
|---|---|---|---|
| Mobile Rocket Battery (`r2hzrockets`) | 900; one 150-damage strike missile every 220 ticks, 13 cells | **800**; **volley of 8 unguided rockets** (30 each, scatter 1.25 cells), every 260 ticks, 12 cells, min 4; keeps the SET bonus and the empty-erector reload window | The approved art is a 40-tube launcher; the weapon becomes what the truck shows |
| **Rail Technical** (new, `r2hzrail`) | — | **450**; pickup with a 6-rail rack: 4 unguided rockets (28 each, scatter 1 cell) every 200 ticks, 10 cells, min 3; War Factory, no radar needed; guided by spotters and signal posts | The cheap launcher the roster lacks; early, plentiful, shoot-and-move |
| Ridge Missile Team (`r2hzat`) | 350; RPG 80 every 90 ticks, 4.5 cells | Shoulder-fired, stays unguided; see section 2 for the soldier side | Basic AT, elite crew |
| Recoilless Technical (`r2hzrecoilless`) | 550; 85 damage | **475**; 78 damage | Cheaper, more of them |
| Coastal Missile Emplacement (`r2hzcoastal`) | 1200; 2 x 75 every 170 | **1000**; **4 x 42** every 210, same range and min range | Same damage per cycle, more missiles, cheaper |
| Coastal Missile Boat (`r2hzmissileboat`) | 1100; 2 x 60 every 160 | **1000**; **3 x 42** every 170 | Volume; naval share is small, kept modest |

Guidance (Field Spotter, Signal Post: +20% range, -20% reload, not stacking) stays and now also reaches the Rail
Technical and the FPV Team.

## 2. Very powerful soldiers

Fewer but stronger: each fighter costs more and is worth more. At equal credits the riflemen keep the same
damage and health per credit as today [inferred], concentrated in fewer bodies, so splash and artillery hurt them
less. The edge comes from rank, cover and concealment.

**Doctrine traits on every Hezbollah infantry unit** (`^R2HezbollahInfantry`):

| Trait | Mechanic | Effect |
|---|---|---|
| Veteran from the barracks | `ProducibleWithLevel@doctrine`, 1 level, no prerequisite | Every fighter starts Veteran: +10% damage, -10% damage taken, +20% speed, -10% reload, slow self-heal |
| Fast promotion | `GainsExperience.ExperienceModifier` = 60% of cost | Elite after about 60% of the usual kills (Elite: +82% damage in total, -25% damage taken) |
| Hill fighters | `GrantConditionOnTerrain` Rough → `DamageMultiplier` 80 | 20% less damage on rough ground |
| Stationary concealment | the Line Fighter's cloak, extended to the AT team, spotter and FPV team | Hidden until it moves, fires or is hit; detectors and splash still find them |

Garrisons: the mod has no general garrison system (one civilian building has fire ports), so "holding a position"
is the stationary concealment above plus the concealed bunker; no garrison mechanic is added.

| Unit | Now | Proposed |
|---|---|---|
| Line Fighter (`r2hzrifle`) | 150; 100 HP; rifle 13 x 2 / 36 ticks | **225**; **130 HP**; rifle **16** x 2 |
| Ridge Missile Team (`r2hzat`) | 350; 95 HP; RPG 80, 4.5 cells | **450**; **120 HP**; RPG **90**, **5 cells**; conceals when stationary (ambush) |
| Field Spotter (`r2hzspotter`) | 525; 90 HP | **450**; **115 HP**; also extends the FPV link (below) |
| Cedar Scout (`r2hzscout`), the hero | 1650; 170 HP; Veteran rank only by kills | **1800**; **240 HP**; leaves the barracks **Elite**; carbine 30 → **34**; demolition kept; still one at a time |

Hero tier: every faction has exactly one build-limit-1 commando (Red Spear, Shadow One, Grey Wolf, Falcon, Wadi
Ghost, Recon Specialist). Hezbollah's is the Cedar Scout, so it becomes the hero instead of adding a second one.

## 3. Very mini drones

### FPV Team (new infantry, `r2hzfpv`) and FPV Drone (new aircraft, `r2hzquad`)

A two-person drone team (operator in goggles with a hand controller, a backpack rack of micro-quadcopters). It
reuses the stock carrier mechanism (`CarrierParent` / `CarrierChild`, as the Aircraft Carrier and its Hornets) and
the faction's own drone rules, scaled down:

| | FPV Team (operator) | FPV Drone (child) |
|---|---|---|
| Cost / health | **500** / 110 HP, Veteran like all fighters | 30 (value for kill accounting) / **25 HP** |
| Build | Barracks + Radar, BuildPaletteOrder 50 | not buildable; 3 carried, launched automatically |
| Weapon | launch link, **7 cells**; light carbine for self-defence | **one-way charge**, 75 damage, small splash: infantry 110%, light 120%, medium 70%, heavy 40%, buildings 20-40% |
| Movement | infantry speed 60 | **very fast** (250), low altitude, tiny |
| Regeneration | one drone every **150 ticks (6 s)**; returned drones re-arm in 40 | consumed on impact |

**Mechanics reused from the faction:**
- **One-way strike** (Loiter Drone, Attack Skiff): the drone is destroyed by its own attack.
- **Relay link** (Attack Skiff's `r2-hz-link`): drones need `r2-hz-fpvlink`, given within 8 cells of an FPV Team,
  6 cells of a Field Spotter or 6 cells of a powered Signal Post. A drone that spends 1.6 s outside every link
  crashes.

**Counter-play window** (what the opponent does):

| Answer | Why it works |
|---|---|
| Any anti-air (flak, IFV, AA vehicles and sites, rocketeers) | Drones are air targets with 25 HP: one hit each |
| Small arms (every rifle and machine gun built on the stock `^MG`) | Drones also carry a `MicroDrone` target type that `^MG` weapons and the ground auto-target lists include: 2-3 rifle hits each |
| Kill or detect the operator | Launching reveals the concealed team; when it dies, its airborne drones die with it |
| Push right after a salvo | 3 drones spent = 18 s to a full rack again |
| Kite out of the link | Chasing drones crash 1.6 s after leaving the link |
| Armor | Heavy armor takes 40% |

Cannons, artillery and missiles still cannot hit them: that is the "hard to hit" side, paid for by one-hit deaths to
anti-air, small-arms fire and the operator dependency. The balance run reports the FPV trade per opponent, so a
faction short on anti-air that collapses against them shows up (owner watch item, gate a).

### Loiter Drone (`r2hzdrone`), scaled down

**700 → 450**, 90 → 60 HP, speed 150 → 190, warhead 220 → 150 (same armour mix). It stays the long-reach one-way
strike; the cheaper price fits the swarm doctrine and its 0.14 trade [ran].

### Signal Post (`r2hzrelay`)

Also gives the FPV link within its 6 cells while powered, so base drone teams can defend around posts.

## 4. Unchanged

Cedar Technical, Escort Gun Truck, Attack Skiff, Coastal Survey Boat, Concealed Bunker, Short-Range AA Nest, Field
Workshop: rules unchanged (descriptions only where a cross-reference changes).

## 5. Bot doctrine

`doctrines.yaml` `BotDoctrine@hezbollah`:

| Setting | Now | Proposed |
|---|---|---|
| Doctrine id | `concealed-defense` | `salvo-and-swarm` |
| Opening | power, barracks, refinery, **bunker**, factory, refinery, radar, signal post | power, barracks, refinery, factory, refinery, radar, signal post (the bunker moves to normal base building) |
| Squad size | 130 | **100** (pricier units: squads keep similar value) |
| line-infantry / anti-armor | 140 / 140 | **100 / 120** |
| artillery | 125 | **175** (rocket volume) |
| support / anti-air / strike-aircraft | 120 / 40 / (100) | 100 / 40 / **50** |
| new role `drone-swarm` | — | share **8** in all five profiles (only Hezbollah has the role), FPV Team tagged with it |

`hezbollah-ai.yaml` / `hezbollah.yaml`: limits Rocket Battery 4 → 5, Rail Technical 6, FPV Team 6, Loiter Drone 5 → 4;
the Rail Technical joins the vehicle list. `bot-types.yaml`: no change (the FPV Drone never joins squads: it rejects
orders like a Hornet; it is added to `ExcludeFromSquadsTypes` if the squad manager picks it up).

## 6. Catalog (`OpenRA-AI/catalog/factions.json`)

Edited on a separate local branch so the narrative agent's identity and rival-view fields are not touched.

| Field | Now | Proposed |
|---|---|---|
| title (doctrine) | Concealed defense | **Salvo and swarm** |
| tagline | Hold the ground. Move before the counterattack. | **Few fighters. Many rockets. Small drones.** |
| playstyle | Scout, spread out ... | Field a small core of veteran fighters, cover them with cheap rocket volleys and launch FPV drones from concealment. Fight from rough ground, keep drone teams inside their link and move launchers after each volley. |
| strengths | Low-cost forces ... | Veteran infantry from the first minute, cheap rocket volume, regenerating micro-drones that ground fire cannot hit. |
| counterplay | Detect concealed units ... | Anti-air downs FPV drones in one hit; kill the operator or leave the link. Close the rocket minimum range and use splash and detection against fewer, costlier fighters. |
| units | 17 | 19: + `hzfpv` (FPV Team, role "Drone swarm"), + `hzrail` (Rail Technical, "Artillery"); every changed unit's story follows its new in-game description |

Left alone: `story` (faction identity) and anything the narrative agent adds. `content_catalog.py` must pass against
this branch (`--mod ../RTSAI-Mod-wt-hezbollah`).

## 7. Voices

Same licensed set as the other Hezbollah lines (`OpenRA-AI/scripts/generate-levant-voices.py`: Chatterbox
Multilingual cloned from the Lebanese reference, Kokoro for English, "handheld field radio" finish), one new set
`R2HezbollahfpvVoice`, 8 clips, reviewed in `docs/voice-review.csv`:

| File | Lebanese Arabic | English |
|---|---|---|
| `hz-fpv-select` | فريق المسيّرات جاهز. | Drone team ready. |
| `hz-fpv-move` | منغيّر الموقع. | Changing position. |
| `hz-fpv-attack` | المسيّرات طالعة. | Drones away. |
| `hz-fpv-action` | الإشارة منيحة. | Signal's good. |

The Rail Technical uses the existing vehicle set; FPV Drones are not voiced (not selectable). Neutral unit
acknowledgements only, like every other line.

## 8. Art (authored in Blender, no image-to-3D)

Three new models, scripted with bmesh in Blender 5.2 (hard-surface parts, real pivots, explicit team-colour
regions), faction look from `RTSAI-Art/bible/hezbollah.md`: pale stone lit faces, olive and khaki accents, dark
mechanisms, short antennas.

| Actor | Route | Size target (true 1x) | Design |
|---|---|---|---|
| `r2hzquad` FPV Drone | GLB prerender (`glb_prerender.py`), aircraft, 4 spinning rotors as spin frames | about a third of the Loiter Drone's area, still a readable X at 1x | X-frame, 4 rotor guards (team colour), slung charge tube, camera nub |
| `r2hzfpv` FPV Team | infantry route (`infantry_route.py`) | person-sized like the other fighters | goggles band, hand controller, backpack rack with a strapped quad and 2 antennas |
| `r2hzrail` Rail Technical | GLB prerender, light-truck class | light-truck band, a little smaller than the Cedar Technical | pickup with a raised 6-rail rocket rack, reload sprite with an empty rack |

Cameos (`cameo_render.py`, name bars `FPV TEAM`, `RAIL TECH`) and the gates (`art_metrics`, route verify) run
before the review sheet. Sheet at 1x and 3x goes to the owner (gate b) before anything is installed.

## 9. Balance plan

Harness `tools/balance-harness.py`, normal bots, 40-minute cap, campaigns with `focus: [hezbollah]` against all
eight other factions:
- land: Dustbowl and Tournament Map A, both orientations, 3 replicates: **96 games**;
- naval: Little Big Lake, 3 replicates: **48 games**;
- screening probes first (1 replicate, 32 land games), with rules overlays where possible.

Targets (round 4): **35-65% against the modern factions, at least 35% against America and Russia** on land; naval
reported and held to the same band if possible. Tuning order if a target is missed: Rocket Battery and Rail
Technical cost, FPV respawn time, infantry cost step, then doctrine shares. The balance table goes to the owner
(gate c) before any merge.

## 10. Checks before merge

`make test` with 0 warnings; `hit_lab.py --faction hezbollah` (new armaments included); `content_catalog.py`
against the branch; one windowed bot match (game-window lock, gpu-yield line, `OPENRA_AI_HOST=0`); path-limited
local commits, nothing pushed.

## Owner decisions in this design

1. FPV Team as **infantry** (soldier + drones, uses the infantry route) rather than a vehicle.
2. The new cheap launcher is a **Rail Technical** pickup (mobile), not a static launch-rail defence.
3. The Cedar Scout is the hero; no second hero.
4. Doctrine name **Salvo and swarm** and the tagline above (the narrative agent's identity text may want to match).

## As built

Differences from the design above. Each one was decided at an owner gate or measured by the harness (balance trims
1-5, round 5 in `docs/balance.md`):

| Item | Design | Built | Why |
|---|---|---|---|
| FPV drones vs small arms | anti-air only | `MicroDrone` target type: every `^MG` rifle and machine gun can hit them, and the ground auto-target lists include them | Owner watch item, gate (a) |
| Ridge Missile Team | 450; RPG 90 against every armour as before | **500**, stationary concealment kept; RPG against heavy / medium armour 95 / 100 -> **65 / 80** | Trims 1-4. At 450 it traded 1.31 per credit. Without concealment (trims 1-2), Hezbollah fell to 21% against America, whose bots field almost no detectors. The modern factions lead with tanks. |
| Line Fighter | 225, rifle 16 | **275**, rifle 16 | Trims 1-2: it traded 2.07 per credit at 225. Trim 3 tried rifle 14; trim 4 reverted it, because the riflemen's core stats carry the doctrine. |
| Fast promotion | Elite after 60% of the usual kills | **usual rate**; every fighter still leaves the barracks Veteran | Trim 5: elite riflemen snowballed where they killed most cheaply (2.19 per credit against the modern factions, 1.19 against America and Russia) |
| Cedar Scout (hero) | leaves the barracks Elite | leaves the barracks **Veteran** | Trim 5 ("Veteran rather than more") |
| Rough-ground cover | damage x0.80 | **x0.90** | Trim 1 (it stacks with the Veteran start) |
| Rocket Battery / Rail Technical vs infantry | 60-70% / 80% | **100% / 100%** | Trim 4: rocket volume answers the infantry masses of America and Russia |
| Bot anti-air share | 24 (unchanged) | **40** | Trim 4: America's jets and rocketeers caused a fifth of Hezbollah's losses |
| FPV Drone art | spinning rotor frames | dark prop blur discs inside the ducts | Thin spinning blades speckled at 1x (art gate) |
| FPV Team art | goggles, controller, small backpack quad | a large quad carried over the shoulders, a whip antenna, the controller held forward (operator pose) | Owner revision, gate (b) |
| Rail Technical art | 6-rail rack, empty reload sprite | six square launch tubes on a dark core raised 22 degrees, dark mouths at both ends; no empty sprite | Owner revision, gate (b): it reads as a launcher at 1x |
| Voices | design lines | `hz-fpv-move`: رايحين عالموقع الجديد. / Moving to a new position.; `hz-fpv-attack`: طلعنا المسيرات. / Drones away. | Clearer Lebanese phrasing (منغيّر can be heard as من غير) |

### Balance (gate c)

Harness: normal bots, 40-minute cap. Hezbollah played all eight other factions on Dustbowl and Official Tournament
Map A, in both orientations with 3 replicates (96 games). 0 errors in every run. Score = wins plus half the draws,
with the 95% Wilson interval.

| Run | Rules | vs modern (target 35-65%) | vs America+Russia (target ≥35%) |
|---|---|---:|---:|
| Round 4 final | e2c07b0 | 57% (45-68) | 48% (30-67) |
| As designed, 42 of 96 (stopped) | 2ed217e | 84% (68-93) | 70% (40-89) |
| Trims 1-2 | b70d61e | 70% (59-79) | 38% (21-57) |
| Trim 3, 47 of 96 (stopped) | efe7750 | 69% (53-82) | 32% (12-61) |
| Trim 4 | 85d07d4 | 72% (61-81) | 75% (55-88) |
| **Trim 5 (built)** | **d646808** | **69% (57-78)** | **40% (23-59)** |

Trim 5 against each opponent: America 38%, Russia 42%, China 88%, Iran 54%, Israel 75%, Saudi Arabia 75%, Türkiye 79%,
Yemen 42%. Naval (Little Big Lake, 48 games): 46% (31-62) against the modern factions,
50% (25-75) against America and Russia, both inside the band (round 4: 54% and 67%).

**Result.** The America+Russia target is met. The modern target is missed by 4 points, but its 95% interval
(57-78) still reaches the band ("within noise", as `docs/balance.md` uses the term). Trim 5 is the configuration
closest to both bands: it is 4 points out in total, against 5 for trims 1-2 and 7 for trims 3 and 4.
The trim cap (two rounds after trim 3) is reached.

**Why the modern band cannot be met from Hezbollah's side [inferred from the per-opponent data].** Over the four
trimmed rule sets, Hezbollah's score against the modern factions stayed at 69-72%. Over the same rule sets, its score
against America and Russia moved from 32% to 75%. Each trim after trims 1-2 moved the America+Russia score by 6 to 43
points and the modern score by at most 3. A cut large enough to bring the modern score to 65% would take America+Russia back to about
the 32% of trim 3. The gap sits with the opponents:
- **China** was the weakest modern faction in round 4 (33% against the modern factions, the one target round 4
  missed). Hezbollah beat it 11-1 in round 4 and goes 10-1 (1 draw) now. Against the other five modern factions,
  Hezbollah scores **65%**, inside the band.
- **Defences and infantry mass.** Against America and Russia, Hezbollah loses about 48,000 credits per game. GIs,
  conscripts and flak troopers kill about 16,000 of it. Pillboxes, Tesla coils, Prism towers and sentry guns kill
  about 10,700. Against the modern factions it loses about 35,000 per game. Their rifle infantry and militia kill
  about 10,800 of it, and their bunkers and bastions about 1,500. So the veteran riflemen trade 1.89 destroyed per credit against the modern
  factions and 1.23 against America and Russia. The AT team trades 1.02 against the modern factions and 0.57
  against America and Russia.
- The fix belongs in an all-faction pass, which this branch does not make: China's strength, and the modern
  factions' anti-infantry answers.

**FPV watch item (gate a).** Over the whole trim-5 run, the FPV Team and its drones destroyed 0.99 per credit.
Against single opponents, the drones destroyed from 0.49 per credit (America) to 1.07 (Israel). No faction collapses
against them.

Art: `RTSAI-Art/tools/hz_doctrine_models.py` (Blender bmesh, no image-to-3D) -> `units/<actor>/candidates/
mesh-v1-blender`; FPV Drone and Rail Technical through `glb_prerender.py` (Hornet and light-truck family gates
pass), FPV Team through `infantry_route.py` with authored landmarks (gate vs GI/Conscript passes), cameos with name
bars. Checks on the final rules:
- `make test`: exit 0, 0 warnings.
- Hezbollah hit lab: 27/27, including the FPV launch link and both rocket launchers.
- `art-provenance.py --check`: 313 files, none flagged.
- The catalog validates against this branch.
- One windowed bot match, Hezbollah vs America (game-window lock, gpu-yield line, `OPENRA_AI_HOST=0`, rules of
  2ed217e): 10.8 game minutes, no exception or Lua error. The FPV Team, Rail Technical and Loiter Drone were built.
