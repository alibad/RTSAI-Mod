# Hezbollah doctrine: Salvo and Swarm (design for review)

Status: **design, gate (a)**. Branch `rtsai/hezbollah-doctrine` (local), from `main` 3db6883. No rules changed yet.
Owner brief (2026-10-07): "basic missiles, very powerful soldiers, very mini drones". Every existing unit stays;
they are retuned, and the doctrine adds what it needs. The faction keeps its real flag.

**[ran]** = measured in the round-4 final (docs/balance.md, `docs/balance-data/r4-final*`). **[inferred]** = from rules.

## The doctrine in one line

Few fighters, many rockets, small drones: a small core of veteran infantry fights from cover, cheap rocket volleys
do the heavy lifting, and FPV teams launch regenerating micro-drones that only anti-air can stop.

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
