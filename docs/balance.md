# Bot-vs-bot balance evidence

Date: 2026-10-02. Branch `rtsai/balance` (local, not pushed). Engine `rtsai/engine` 5523a9907f (`ENGINE_VERSION`).

How each result was established: **[ran]** means the matches were played and the numbers come from their recorded
results. **[inferred]** means it was reasoned from rules, code or those results and not tested directly.

## What this shows, and what it doesn't

The harness plays the game's own `normal` bot against itself, one faction per side. A win rate here measures
**how well the shipped bot plays each faction** on these maps, which is what a player meets in skirmish. It is
evidence about the rules only through that filter.

It shows:
- unit types the bot buys but cannot use (they destroy little per credit spent);
- openings that leave a faction without an army early;
- rule bugs that stop a game from ending (one found and fixed) and crashes in long unattended games (one found).

It does not show:
- human balance. Humans micro, focus fire, scout, use abilities, garrison and pick counters; the bot does little of
  this. A unit the bot wastes can still be strong in human hands, and the reverse;
- naval or mixed maps. Both maps are land 1v1 maps, so navies and naval doctrine weights are not measured;
- other bot profiles (rush, turtle, naval, medium), team games, or anything after 40 game minutes;
- kills that report no killer. [inferred] Chrono erasure and mind control seem not to: America's Chrono Legionnaire
  and Russia's Yuri show 0 value destroyed in the per-unit trade figures.

## Method

- **Harness** [ran]: `tools/balance-harness.py`, ported from OpenRA-AI `codex/harness` (eb8f6a1).
  - Every match is a private headless process (`Game.Platform=Null`, `Launch.Bots=Multi0:normal,Multi1:normal`; the
    local client spectates) with its own support directory. Owned Red Alert 2 content is linked in, never copied into
    a repo.
  - A disposable copy of the map locks each slot's faction, spawn and colour and adds a telemetry-only Lua script
    (`tools/balance-telemetry.lua`). It records production, structures, every loss with its killer's type, the
    economy every 10 s and the result.
  - A private copy of the manifest sets the `default` speed's Timestep to 1 ms. Every tick is the same simulation;
    only the wall-clock pause between ticks goes. Matches ran 13-18x faster than real time with 8-20 matches in
    parallel on a shared 24-thread host. All durations are normal-speed game minutes (25 ticks/s).
  - Per match it records the winner, end reason (`conquest`, `tick-cap` draw, `mutual-defeat`, crash, hang),
    duration, per-side production (units by type and value, structures), value destroyed and value lost.
  - A suite can carry a MiniYAML `rules` overlay. The tuning candidates were screened this way, on map copies,
    without editing the mod.
- **Factions.** The five modern nations plus two original RA2 countries as baselines: America (Allied) and Russia
  (Soviet).
- **Bots.** `normal` on both sides, with the mod's doctrine bot modules. The stock countries use the same modules
  without a doctrine.
- **Maps.** Two land 1v1 maps from the mod: Dustbowl (70x152) and Official Tournament Map A (87x134), both temperate.
  [inferred] Short game is on (the upstream lobby default), so a player loses with their last building.
- **Design.** All 21 pairings, each from both spawn orientations on both maps, 3 replicates: 12 games per pairing,
  72 per faction, 252 per round robin. Order is shuffled with a fixed seed. The engine seeds its RNGs from the
  clock, so replicates are independent samples, not reruns. Launches are spaced 0.5 s apart because two
  simultaneous starts were seen to share a seed; no run below has a duplicate seed.
- **Cap.** 40 game minutes (60000 ticks). At the cap the script fails both players' objectives on the same tick, so
  the game ends as a recorded draw with a complete replay.
- **Statistics.** Score = (wins + ½ draws) / games. Win rate = wins / games. Intervals are 95% Wilson intervals.
  The tuning target (35-65% for each modern faction) is applied to the **score**. With a fifth of games drawn, the
  strict win rate sits about 10 points lower for every faction, so both are reported.
- **Probes.** A probe is one replicate (84 games, 24 per faction) with a rules overlay. At that size a faction's
  interval is about ±19 points, so probes screen candidates; only full round robins confirm.

## Pilot: 30-minute cap

[ran] The first round robin (252 games, rules at 01adb19) used a 30-minute cap. 112 of 251 completed games (45%)
hit the cap, 76 of 126 on Dustbowl. In 58 of those, one side fielded at least three times the other's army and
still had not finished. Every later run uses 40 minutes. The pilot also found:

- **A game that could not end.** [ran] Yemen's Mountain Bunker and Coastal Missile Battery cloak until they fire or
  take damage, and cannot fire without power. A beaten Yemen base with no power plant was invisible and harmless
  forever: at least five pilot draws ended with a dominant opponent (up to 78k army value) facing only these
  structures. Fixed in 846ad3c (the cloak also needs power now).
- **A crash.** [ran] 1 of 252 games: `Image cow does not have a sequence named die5`, after a Crazy Ivan bomb
  (`IvanBomber`, `PsychicDeath`) killed a cow. [inferred] `^Animal` overrides `WithDeathAnimation@effect` but the
  merge keeps the infantry's `PsychicDeath: 5`, and the cow has only `die1`/`die2`. Inherited RA2 content outside
  this stream's files; **not fixed** here. It did not recur in the 1,000+ later games.

## Before: rules at 01adb19

[ran] 252 games, 0 errors, 60 tick-cap draws (45 of them on Dustbowl), median length 25.2 min.

Win matrix, row's wins-losses (draws) against the column:

| vs | china | iran | turkey | saudi | yemen | america | russia | Total |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **china** | — | 5-4 (3d) | 2-4 (6d) | 3-6 (3d) | 2-9 (1d) | 0-12 | 0-11 (1d) | 12-46 (14d) |
| **iran** | 4-5 (3d) | — | 7-3 (2d) | 2-5 (5d) | 3-3 (6d) | 0-12 | 2-8 (2d) | 18-36 (18d) |
| **turkey** | 4-2 (6d) | 3-7 (2d) | — | 4-5 (3d) | 1-2 (9d) | 2-10 | 0-10 (2d) | 14-36 (22d) |
| **saudi** | 6-3 (3d) | 5-2 (5d) | 5-4 (3d) | — | 4-5 (3d) | 0-11 (1d) | 1-10 (1d) | 21-35 (16d) |
| **yemen** | 9-2 (1d) | 3-3 (6d) | 2-1 (9d) | 5-4 (3d) | — | 0-11 (1d) | 1-5 (6d) | 20-26 (26d) |
| **america** | 12-0 | 12-0 | 10-2 | 11-0 (1d) | 11-0 (1d) | — | 6-1 (5d) | 62-3 (7d) |
| **russia** | 11-0 (1d) | 8-2 (2d) | 10-0 (2d) | 10-1 (1d) | 5-1 (6d) | 1-6 (5d) | — | 45-10 (17d) |

| Faction | Games | W-D-L | Win rate (95% CI) | Score (95% CI) | Median min |
|---|---:|---:|---:|---:|---:|
| China | 72 | 12-14-46 | 17% (10-27%) | 26% (18-38%) | 26.8 |
| Iran | 72 | 18-18-36 | 25% (16-36%) | 38% (27-49%) | 27.7 |
| Türkiye | 72 | 14-22-36 | 19% (12-30%) | 35% (25-46%) | 26.8 |
| Saudi Arabia | 72 | 21-16-35 | 29% (20-40%) | 40% (30-52%) | 27.0 |
| Yemen | 72 | 20-26-26 | 28% (19-39%) | 46% (35-57%) | 27.4 |
| America | 72 | 62-7-3 | 86% (76-92%) | 91% (82-96%) | 15.2 |
| Russia | 72 | 45-17-10 | 62% (51-73%) | 74% (63-83%) | 22.7 |

China was below the 35% band; Türkiye sat on it. Among themselves the modern factions were close; the large gap
is to the two stock countries, which won 100 of the 106 decided games against them.

## Diagnosis

Economies were similar: by 10 minutes every faction had earned 11-21k credits [ran]. The difference was what the
bots bought. [ran] Per unit type, value destroyed per credit produced on the before rules, and on the doctrine-tuned
rules (the "after doctrine" round robin below):

| Faction | Unit | Before: share of production | Before: destroyed / credit | After doctrine: share | After doctrine: destroyed / credit |
|---|---|---:|---:|---:|---:|
| China | Mantis (AA) | 12.1% | 0.04 | 3.4% | 0.04 |
| Iran | Raad (AA) | 7.7% | 0.06 | 4.0% | 0.08 |
| Türkiye | Gökkalkan (AA) | 14.0% | 0.05 | 7.9% | 0.05 |
| Saudi Arabia | SADS (AA) | 9.9% | 0.06 | 5.5% | 0.02 |
| America | IFV (AA role, dual-purpose) | 12.1% | 0.56 | 13.0% | 0.59 |
| Russia | Flak Trooper / Flak Track | 15.6% / 7.1% | 0.92 / 0.80 | 15.4% / 7.0% | 0.99 / 0.92 |
| Yemen | Samad (one-way drone) | 9.2% | 0.13 | 2.1% | 0.02 |
| China | PHL (artillery) | 14.9% | 0.58 | 14.7% | 0.64 |
| Saudi Arabia | Caesar (artillery) | 12.0% | 0.81 | 9.2% | 0.91 |
| Yemen | RPG team | 24.1% | 0.43 | 23.0% | 0.55 |
| Iran | Toophan team | 32.4% | 0.75 | 28.5% | 0.75 |
| Iran | Shadow One (commando) | 12.4% | 0.50 | 10.1% | 0.46 |
| Yemen | Wadi Ghost (commando) | 14.6% | 0.44 | 9.6% | 0.37 |
| Saudi Arabia | Falcon (commando) | 6.1% | 0.60 | 5.2% | 0.59 |
| China / Türkiye | Red Spear / Grey Wolf (commando) | 8.8% / 8.9% | 0.73 / 0.72 | 8.6% / 7.3% | 0.67 / 0.92 |
| Yemen | Mountain Rifleman | 8.7% | 2.58 | 13.1% | 2.45 |
| China | Rifleman | 9.2% | 1.65 | 8.4% | 1.38 |
| America / Russia | GI / Conscript | 15.4% / 9.3% | 1.58 / 2.00 | 16.1% / 9.7% | 1.64 / 3.08 |
| China / Türkiye / Saudi | Qilin / Bozkır / M1A2S | 16.4 / 21.2 / 22.8% | 0.94 / 0.89 / 0.91 | 21.4 / 27.6 / 28.5% | 0.69 / 0.85 / 0.82 |
| America / Russia | Grizzly / Rhino | 17.9% / 14.3% | 0.83 / 1.55 | 18.9% / 14.2% | 0.83 / 1.53 |

- [inferred] The modern AA vehicles fire `^AAMissile` weapons (air only); the stock units sharing the anti-air role
  also hit ground targets. Against these opponents, 8-14% of the China, Iran, Türkiye and Saudi armies (Yemen 3%)
  was dead weight.
- [inferred] The bot picks at random among units of the same role, so whenever its one allowed commando died,
  about half of the next line-infantry orders bought a 1,650-1,900 credit commando instead of a 100-220 credit
  rifleman.
- [inferred] Per credit, the modern core units deal less damage than the stock ones: riflemen 3.5-3.8 damage per
  tick per 1,000 credits for China, Türkiye and Saudi Arabia, against 5.0 (GI), 6.0 (Conscript), 4.8 (Basij) and
  7.2 (Yemeni Mountain Rifleman); MBTs 1.05-1.33 against 1.55 (Grizzly) and 1.54 (Rhino).

## Tuning steps

Doctrine weights and openings first, as asked; one cost change only after probes. Scores per faction [ran]:

| Faction | Before | P1 | P2a | P2b | P3 | After doctrine | P4 |
|---|---:|---:|---:|---:|---:|---:|---:|
| China | 26% | 31% | 44% | 33% | 28% | 29% | 38% |
| Iran | 38% | 35% | 31% | 40% | 28% | 31% | 33% |
| Türkiye | 35% | 27% | 33% | 25% | 20% | 28% | 25% |
| Saudi Arabia | 40% | 42% | 46% | 52% | 72% | 48% | 31% |
| Yemen | 46% | 46% | 40% | 40% | 38% | 62% | 58% |
| America | 91% | 94% | 85% | 94% | 84% | 85% | 92% |
| Russia | 74% | 75% | 71% | 67% | 69% | 67% | 73% |
| games | 252 | 84 | 84 | 84 | 61 | 252 | 84 |

- **P1** (overlay): anti-air cut for all five. Less AA was built; no score moved beyond noise.
- **P2a** (overlay): P1 plus the other doctrine cuts and the Iran/Saudi openings. China rose to 44%.
- **P2b** (overlay): P2a plus squad sizes 80/105/80/70/135 (China/Iran/Türkiye/Saudi/Yemen). China and Türkiye
  fell at 80, so both stay at 100 in the commit.
- **P3** (overlay, stopped at 61 games): P2b plus cheaper riflemen and MBTs for China, Türkiye and Saudi Arabia.
  Saudi Arabia jumped to 72%; rejected.
- **After doctrine** (round robin, 605f111): the committed doctrine and bot changes. Yemen went to 62% and beat the
  other modern factions 31-7; China, Iran and Türkiye stayed below 35%.
- **P4** (overlay on 605f111): cheaper rifleman and MBT for China and Türkiye. China 38%; Türkiye unchanged. Only the
  China part was kept.
- **After** (round robin, 414f8fa): Yemen's anti-armor cut reverted, China's cost change applied. See below.

## Changes made

| Commit | Change | Evidence |
|---|---|---|
| 46dcbd3 | Balance harness, telemetry script, campaigns, unit tests | — |
| 1edb435 | `DoctrineSquadManagerBotModule`, `BotDoctrine.SquadSizeModifier`: per-faction squad sizes (the known gap). No engine change | Mechanism; values in 93681eb |
| 846ad3c | Yemen concealed defenses lose their camouflage without power | Pilot: ≥5 unfinishable games |
| 75f1fea | Doctrine weights: anti-air down for all five; Yemen strike-aircraft 170→50; China artillery 100→60, support 200→150; Saudi artillery 120→80; Iran anti-armor 130→110, strike-aircraft 130→80, MBT and line-infantry cuts dropped; Türkiye transport 160→100, strike-aircraft 140→80 | Diagnosis table; P1, P2a |
| 798ba3c | Iran and Saudi Arabia open with the war factory | First vehicle 5.2 and 5.5 min vs 3.2-4.2 for the rest; probe 4.2 and 3.6 min |
| 93681eb | Squad size: Saudi Arabia 70, Iran 105, Yemen 135; China and Türkiye 100 | Unit cost (Saudi 702 … Yemen 351 per land unit); P2b |
| 605f111 | Bots train Shadow One, Wadi Ghost and Falcon only after 20 minutes (bot setting, `UnitDelays`) | Diagnosis table |
| 17e15bd | Yemen anti-armor back to 160 | After-doctrine round robin: Yemen 62% |
| 414f8fa | China rifleman 180→150, Qilin 850→750 credits (the only unit-stat change) | Lowest before tuning (26%), 29% after doctrine; per-credit damage; P4 |

## After: rules at 414f8fa

[ran] 252 games, 0 errors, 54 tick-cap draws (34 on Dustbowl), median length 24.9 min. This is the final win matrix.

| vs | china | iran | turkey | saudi | yemen | america | russia | Total |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **china** | — | 2-5 (5d) | 6-3 (3d) | 5-5 (2d) | 2-9 (1d) | 0-10 (2d) | 0-11 (1d) | 15-43 (14d) |
| **iran** | 5-2 (5d) | — | 4-4 (4d) | 1-6 (5d) | 2-6 (4d) | 0-12 | 1-8 (3d) | 13-38 (21d) |
| **turkey** | 3-6 (3d) | 4-4 (4d) | — | 2-8 (2d) | 1-8 (3d) | 0-12 | 2-8 (2d) | 12-46 (14d) |
| **saudi** | 5-5 (2d) | 6-1 (5d) | 8-2 (2d) | — | 2-8 (2d) | 0-12 | 0-8 (4d) | 21-36 (15d) |
| **yemen** | 9-2 (1d) | 6-2 (4d) | 8-1 (3d) | 8-2 (2d) | — | 2-9 (1d) | 0-6 (6d) | 33-22 (17d) |
| **america** | 10-0 (2d) | 12-0 | 12-0 | 12-0 | 9-2 (1d) | — | 7-1 (4d) | 62-3 (7d) |
| **russia** | 11-0 (1d) | 8-1 (3d) | 8-2 (2d) | 8-0 (4d) | 6-0 (6d) | 1-7 (4d) | — | 42-10 (20d) |

| Faction | Games | W-D-L | Win rate (95% CI) | Score (95% CI) | Before → after score | Median min |
|---|---:|---:|---:|---:|---:|---:|
| China | 72 | 15-14-43 | 21% (13-32%) | 31% (21-42%) | 26% → 31% | 26.9 |
| Iran | 72 | 13-21-38 | 18% (11-28%) | 33% (23-44%) | 38% → 33% | 26.1 |
| Türkiye | 72 | 12-14-46 | 17% (10-27%) | 26% (18-38%) | 35% → 26% | 21.7 |
| Saudi Arabia | 72 | 21-15-36 | 29% (20-40%) | 40% (29-51%) | 40% → 40% | 27.6 |
| Yemen | 72 | 33-17-22 | 46% (35-57%) | 58% (46-68%) | 46% → 58% | 27.1 |
| America | 72 | 62-7-3 | 86% (76-92%) | 91% (82-96%) | 91% → 91% | 17.4 |
| Russia | 72 | 42-20-10 | 58% (47-69%) | 72% (61-81%) | 74% → 72% | 28.2 |

**The target is not met.** [ran] Saudi Arabia (40%) and Yemen (58%) are inside 35-65%; China (31%), Iran (33%) and
Türkiye (26%) are below it. Every before → after change except Yemen's lies inside the 95% intervals.

What the tuning did and did not do:
- [ran] It removed most of the measured waste: air-only AA fell from 8-14% of the China, Iran, Türkiye and Saudi
  armies to 3-8%, the Samad from 9% of Yemen's production to 2%, and the first Iran and Saudi vehicles come 1.2 and
  1.8 minutes earlier.
- [ran] It did not close the gap to the stock countries. They won 96 of 101 decided games against the modern
  factions (before: 100 of 106), and the five modern scores average 37.4% (before 36.9%).
- [inferred] It moved strength between the modern factions instead. Yemen gained most, because the money freed
  from the Samad, AA and its commando went to its riflemen and technicals, the most cost-effective units in the
  game (Mountain Rifleman 2.45-2.58 destroyed per credit). Türkiye and Iran, which had less waste to remove, lost
  ground to Yemen (Türkiye 1-8, Iran 2-6) and Saudi Arabia.
- [ran] Draws fell from 60 to 54 and errors stayed at 0. Dustbowl still produces most draws; its first slot scored
  61% (Tournament A: 48%), which the swapped spawns cancel within each pairing.

## Remaining caveats

- **Three modern factions remain below 35%.** In order of evidence, the next candidates are:
  - Türkiye's Gökkalkan is still 8.2% of its production at 0.08 destroyed per credit; anti-air 40 → 20 would cut
    it further. [ran for the figures; the change is untested]
  - Iran's Shadow One is still 9.6% of its production at 0.48. The 20-minute delay only trimmed it, because many
    games run longer. A bot `UnitLimits` of 0, or a code change so the bot prefers the cheaper unit within a role,
    would remove it. [inferred]
  - Yemen's Mountain Rifleman gives 7.2 damage per tick per 1,000 credits, against 6.0 for the Conscript. A cost
    of 120 would bring it to 6.0 and would mainly help China, Iran and Türkiye in their games against Yemen.
    [inferred]
  - The cheaper riflemen and MBTs that helped China did not help Türkiye in P4, so Türkiye's weakness is not
    simply cost. It needs its own look (early army: the smallest at 10 minutes in every run). [ran]
- **The stock baselines dominate the bot ladder.** America scored 91% and Russia 72-74% in every round robin. While
  that holds, the five modern factions can average only about 37%, so all five can sit inside 35-65% only if they
  are within a few points of each other. Stock RA2 rules were left alone: they are the reference, not the target.
- **The shipped bot is the instrument.** The cuts make the bot stop buying units it cannot use; they say nothing
  about those units in human hands. The bot-only commando delay does not touch human play. The China cost change
  does, and its human effect is untested.
- **Land maps only.** Naval doctrine weights were not tuned, and on these maps every faction, stock ones included,
  still spends 5-10% of its production on ships that do almost nothing.
- **Noise.** A round robin gives each faction a 95% interval about ±11 points wide; a probe about ±19. Several
  committed changes (Türkiye transport, Iran strike-aircraft, the commando delay) were confirmed only as part of
  a whole round robin, not one at a time.
- **Not fixed:** the `cow`/`die5` crash (see the pilot). Kill credit seems to be missing for chrono erasure and mind
  control, so those units read zero in the per-unit table.
- **Reproducibility.** The engine has no launch seed, so a match cannot be replayed from the campaign seed; each
  match's replay and engine seed are kept in the run directory (not in the repo).

## Data

All in `docs/balance-data/`. Each `*.csv` has one row per match (`matches.csv` from the harness): map, factions and
spawns per slot, result, winner, end reason, end tick and game minutes, wall seconds, engine seed, and per side the
units produced (count, value, by type), structures placed, value destroyed and value lost. Each `*-summary.json`
holds the aggregates the tables above come from (matrix, per-faction W-D-L, Wilson intervals, lengths, draws,
per-unit trade).

| Files | Run | Rules |
|---|---|---|
| `pilot-30min` | Round robin, 30-minute cap | 01adb19 |
| `before` | Round robin | 01adb19 |
| `probe-p1-aa`, `probe-p2a-doctrine`, `probe-p2b-squads`, `probe-p3-costs` | Probes; overlays in `probe-overlays.json` | 846ad3c + overlay |
| `after-doctrine` | Round robin | 605f111 |
| `probe-p4-china-turkey-costs` | Probe | 605f111 + overlay |
| `after` | Round robin | 414f8fa |

## Reproduce

```
./fetch-local-engine.sh && ./make.cmd all
# <content> holds ra2/ra2.mix and ra2/language.mix copied from an owned Red Alert 2; delete it afterwards.
python tools/balance-harness.py run --campaign round-robin --content <content> --output <scratch>/rr --parallel 8
python tools/balance-harness.py run --campaign <probe> --campaigns-file docs/balance-data/probe-overlays.json \
    --content <content> --output <scratch>/<probe>
python tools/balance-harness.py report --campaign round-robin --output <scratch>/rr   # rebuild the summary
python tools/test_balance_harness.py                                                    # harness unit tests
```

Add `--bot-log` to keep each match's `bot-doctrine.log` (role shares, opening, squad size and every build choice).
`--keep-support` keeps the support directory; each match keeps its replay, which `tools/replay-production.py` reads.
The `before` run used a snapshot of the 01adb19 `mods/` passed with `--mods`.
