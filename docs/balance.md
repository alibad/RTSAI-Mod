# Bot-vs-bot balance evidence

Round 4: 2026-10-06, on the art preview, now promoted to `main` with identical rules, weapons and bot code (a 48-match smoke
on `main`, 0 errors: MIGRATION.md round C). Branch `rtsai/art-preview` (local, not pushed), rules and bot code e2c07b0,
engine `rtsai/engine` 68c1e95557 (local-only: missiles fired over raised ground or ramps hit, and the `WRot.SLerp`
crash of round 3 is fixed). Round 3 (same day, rules a47654a) and the round-2 and round-1 records follow.

Round 6 (2026-10-08) is the current state: the owner's request to put Hezbollah above Israel, with the tank coax cut
from 16 to 12, in both products. It comes first below. Round 5 (2026-10-07/08) follows. It balanced both products,
`main` and the standalone game, with the same faction rules. Before it, a Hezbollah-only pass retuned "Salvo and
swarm" on branch `rtsai/hezbollah-doctrine`; it is the third section.

How each result was established: **[ran]** means the matches or duels were played and the numbers come from their
recorded results. **[inferred]** means it was reasoned from rules, code or those results and not tested directly.

## Round 6: Hezbollah above Israel (2026-10-08)

[ran] Owner request: swap Israel's and Hezbollah's win rates, so Hezbollah is on top and Israel is where Hezbollah
was. It was done in the same round as the planned fix for `main`'s Allied lean. Both products, same faction rules.

Targets:

| | Standalone, vs others | `main`, vs modern |
|---|---|---|
| Hezbollah | about 60% | about 56% |
| Israel | about 54% | about 42% |

Every other faction stays inside 40-60% on standalone, and `main` meets at least 15 of its 16 targets. Hezbollah is
lifted through its own doctrine: basic missiles, powerful soldiers, small drones. Israel is lowered with small,
legible changes.

Setup:
- **Starting rules:** `main` b8ed157 and `rtsai/standalone` 1a14e6b. Their rules are the round-5 final rules: the
  later commits change only text and render offsets.
- **Engine and harness:** engine 68c1e95557, normal bots, 40-minute cap, 3 workers, `OPENRA_AI_HOST=0`.
- **Probes:** a full round robin with 1 replicate, plus 1 more replicate of every Hezbollah and Israel pairing.
  Each probe has 200 games on `main` and 128 on standalone, so Hezbollah and Israel get n=48 each. Every other
  faction is scored from the round-robin part only.
- **Tuning rounds:** three. Probe 1, then probe 2, then the final rule set measured at full scale.

### Round 6 changes

All in `mods/rtsai/modern-factions` (ab878b8), each with its reason in a comment next to it:

| # | Change | Why | Run |
|---|---|---|---|
| 1 | Coaxial machine gun `R2QilinCoax` damage 16 → 12 (Qilin, Bozkir, M1A2S, Merkava; and the Karrar, change 7) | At 16, `main`'s Allied side scored 66% against the Soviet side | probe 1 |
| 2 | Hezbollah doctrine artillery share 175 → 250 | The salvo: more Rocket Batteries, Hezbollah's best trade at 1.8-2.3 destroyed per credit, and more Rail Technicals | probe 1 |
| 3 | FPV Team: a drone regenerates every 100 ticks instead of 150 (still three per team) | The swarm: more drones in the air | probe 1 |
| 4 | Merkava 1300 → 1400 | A third of Israel's kills | probe 1 |
| 5 | Israeli AT team 500 → 550 | Israel's second killer: 17-20% of its kills at 1.3-1.4 per credit | probe 1 |
| 6 | Merkava HP 640 → 580, still above the M1A2S's 520 | Probe 1 left Israel at 60% on `main` | probe 2 |
| 7 | Iran's Karrar gets the coaxial machine gun, 850 → 900 | With Hezbollah stronger, Iran fell to 31% on `main` in both probes (0-7 against China). The Karrar traded 0.66-0.78 per credit | final |

Effect by unit [ran], destroyed per credit, round-5 final → round-6 final:

| Unit | `main` | Standalone |
|---|---|---|
| Rocket Battery | 2.12 → 1.68 | 2.34 → 1.85 |
| Rail Technical | 1.29 → 1.25 | 1.22 → 1.28 |
| FPV Team, counting its drones' kills | 1.0 → 1.24 | 0.89 → 0.97 |
| Merkava | 1.44 → 1.10 | 1.40 → 1.17 |
| Karrar | 0.66 → 1.46 | 0.73 → 1.38 |
| Bozkir | 1.46 → 1.24 | 1.59 → 1.41 |

Share of production:
- Rocket Batteries and Rail Technicals together: 10-12% → 16-17% of Hezbollah's production.
- The Merkava still makes 28% of Israel's kills.

### Standalone result

[ran] Final round robin (`r6-sa-final`): 252 games, 0 errors, 36 draws (14%), median 19.8 game minutes.

| vs | china | iran | turkey | saudi | yemen | israel | hezbollah | vs others |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **china** | — | 6-5 (1d) | 5-3 (4d) | 2-7 (3d) | 6-5 (1d) | 2-8 (2d) | 2-8 (2d) | 41% (30-53) |
| **iran** | 5-6 (1d) | — | 7-4 (1d) | 6-5 (1d) | 5-4 (3d) | 5-6 (1d) | 3-6 (3d) | 50% (39-61) |
| **turkey** | 3-5 (4d) | 4-7 (1d) | — | 6-6 | 5-6 (1d) | 4-7 (1d) | 1-9 (2d) | 38% (28-50) |
| **saudi** | 7-2 (3d) | 5-6 (1d) | 6-6 | — | 7-3 (2d) | 6-4 (2d) | 5-5 (2d) | 57% (45-68) |
| **yemen** | 5-6 (1d) | 4-5 (3d) | 6-5 (1d) | 3-7 (2d) | — | 5-7 | 4-5 (3d) | 44% (34-56) |
| **israel** | 8-2 (2d) | 6-5 (1d) | 7-4 (1d) | 4-6 (2d) | 7-5 | — | 4-7 (1d) | 55% (43-66) |
| **hezbollah** | 8-2 (2d) | 6-3 (3d) | 9-1 (2d) | 5-5 (2d) | 5-4 (3d) | 7-4 (1d) | — | 65% (53-75) |

Probes are shown without an interval; Hezbollah and Israel are scored over every suite (n=48).

| Faction | Target | R5 final | Probe 1 | Probe 2 | R6 final | Met |
|---|---|---:|---:|---:|---:|---|
| China | vs others 40-60% | 48% (37-59) | 40% | 54% | 41% (30-53) | yes |
| Iran | vs others 40-60% | 45% (34-57) | 48% | 52% | 50% (39-61) | yes |
| Türkiye | vs others 40-60% | 46% (35-57) | 35% | 46% | 38% (28-50) | **no**, within noise |
| Saudi Arabia | vs others 40-60% | 54% (43-65) | 60% | 42% | 57% (45-68) | yes |
| Yemen | vs others 40-60% | 43% (32-55) | 50% | 54% | 44% (34-56) | yes |
| Israel | vs others, about 54% | 60% (48-70) | 50% | 48% | 55% (43-66) | yes |
| Hezbollah | vs others, about 60% | 54% (43-65) | 52% | 54% | 65% (53-75) | close: +5, 60 inside the interval |

Each map, round-5 final and round-6 final. The faction columns are each faction's score against the others on that
map:

| Map, run | Games | Draws | Median minutes | Allied side vs Soviet side | China | Iran | Türkiye | Saudi Arabia | Yemen | Israel | Hezbollah |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Harbor Line, R5 final | 126 | 14 (11%) | 14.0 | 65% (54-75) | 61% | 43% | 43% | 67% | 33% | 60% | 43% |
| Twin Fords, R5 final | 126 | 26 (21%) | 25.5 | 42% (32-54) | 35% | 47% | 49% | 42% | 53% | 60% | 65% |
| Harbor Line, R6 final | 126 | 11 (9%) | 15.1 | 64% (52-74) | 44% | 38% | 38% | 68% | 29% | 78% | 56% |
| Twin Fords, R6 final | 126 | 25 (20%) | 24.9 | 27% (18-38) | 38% | 62% | 39% | 46% | 60% | 32% | 74% |

**Verdict, standalone.** [ran]
- **Hezbollah is on top:** 54% → 65% (53-75). That is 5 points over "about 60%", and 60% is inside its interval.
- **Israel:** 60% → 55% (43-66), on the 54% target.
- **Türkiye** fell to 38% (28-50). It misses the 40-60% band by 2 points, within noise.
  - Türkiye depends on the coax most: the Bozkir is 34% of its production.
  - It scored 1-9 (2 draws) against Hezbollah.
- Every other faction is inside 40-60%. Draws are 14%, which meets the 15% target.
- **The coax cut did not fix Harbor Line.** The Allied side is still 64% there. On Twin Fords it fell from 42% to 27%.
  Overall the Allied side scores 45% (38-54); it was 54%.
- 2 of 252 games ended in a conquest at 3.4-3.5 minutes (Israel against Iran on Harbor Line; Türkiye against Israel
  on Twin Fords). One side's starting units destroyed the other's construction yard in the first two minutes.
  - Round 5's standalone runs had no game under 5 minutes.
  - [inferred] It comes from the kit-base start, not from the round-6 rules. It is passed to the standalone agent.

### Main result

[ran] Final round robin (`r6-main-final`): 420 games on Dustbowl and Official Tournament Map A, 0 errors, 68 draws
(16%), median 23.8 game minutes. Draws by map: Dustbowl 54 (26%), Tournament Map A 14 (7%).

| vs | china | iran | turkey | saudi | yemen | israel | hezbollah | america | russia | vs modern | vs America+Russia |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **china** | — | 4-7 (1d) | 3-7 (2d) | 5-5 (2d) | 6-5 (1d) | 5-6 (1d) | 6-5 (1d) | 5-1 (6d) | 6-2 (4d) | 46% (35-57) | 67% (47-82) |
| **iran** | 7-4 (1d) | — | 5-5 (2d) | 4-7 (1d) | 5-3 (4d) | 9-3 | 6-5 (1d) | 5-6 (1d) | 7-4 (1d) | 56% (45-67) | 54% (35-72) |
| **turkey** | 7-3 (2d) | 5-5 (2d) | — | 6-5 (1d) | 5-3 (4d) | 7-2 (3d) | 6-5 (1d) | 5-3 (4d) | 7-4 (1d) | 59% (47-70) | 60% (41-77) |
| **saudi** | 5-5 (2d) | 7-4 (1d) | 5-6 (1d) | — | 8-2 (2d) | 6-4 (2d) | 5-6 (1d) | 4-6 (2d) | 7-5 | 56% (45-67) | 50% (31-69) |
| **yemen** | 5-6 (1d) | 3-5 (4d) | 3-5 (4d) | 2-8 (2d) | — | 4-5 (3d) | 4-7 (1d) | 4-4 (4d) | 4-4 (4d) | 40% (29-51) | 50% (31-69) |
| **israel** | 6-5 (1d) | 3-9 | 2-7 (3d) | 4-6 (2d) | 5-4 (3d) | — | 5-5 (2d) | 5-5 (2d) | 7-5 | 42% (32-54) | 54% (35-72) |
| **hezbollah** | 5-6 (1d) | 5-6 (1d) | 5-6 (1d) | 6-5 (1d) | 7-4 (1d) | 5-5 (2d) | — | 2-8 (2d) | 8-3 (1d) | 51% (39-62) | 48% (30-67) |
| **america** | 1-5 (6d) | 6-5 (1d) | 3-5 (4d) | 6-4 (2d) | 4-4 (4d) | 5-5 (2d) | 8-2 (2d) | — | — | 52% (41-62) | — |
| **russia** | 2-6 (4d) | 4-7 (1d) | 4-7 (1d) | 5-7 | 4-4 (4d) | 5-7 | 3-8 (1d) | — | — | 39% (29-49) | — |

| Faction | Target | R5 final | Probe 1 | Probe 2 | R6 final | Met |
|---|---|---:|---:|---:|---:|---|
| China | vs modern 35-65% | 56% (45-67) | 54% | 54% | 46% (35-57) | yes |
| Iran | vs modern 35-65% | 40% (29-51) | 31% | 31% | 56% (45-67) | yes |
| Türkiye | vs modern 35-65% | 54% (43-65) | 52% | 48% | 59% (47-70) | yes |
| Saudi Arabia | vs modern 35-65% | 66% (54-76) | 46% | 56% | 56% (45-67) | yes |
| Yemen | vs modern 35-65% | 35% (25-47) | 50% | 50% | 40% (29-51) | yes |
| Israel | vs modern 35-65%, about 42% | 56% (45-67) | 60% | 51% | 42% (32-54) | yes |
| Hezbollah | vs modern 35-65%, about 56% | 42% (32-54) | 62% | 60% | 51% (39-62) | yes; −5 from 56, inside the interval |
| China | vs America+Russia ≥35% | 58% (39-76) | 69% | 31% | 67% (47-82) | yes |
| Iran | vs America+Russia ≥35% | 46% (28-65) | 38% | 25% | 54% (35-72) | yes |
| Türkiye | vs America+Russia ≥35% | 62% (43-79) | 75% | 56% | 60% (41-77) | yes |
| Saudi Arabia | vs America+Russia ≥35% | 65% (45-80) | 38% | 62% | 50% (31-69) | yes |
| Yemen | vs America+Russia ≥35% | 48% (30-67) | 50% | 69% | 50% (31-69) | yes |
| Israel | vs America+Russia ≥35% | 71% (51-85) | 69% | 56% | 54% (35-72) | yes |
| Hezbollah | vs America+Russia ≥35% | 46% (28-65) | 50% | 38% | 48% (30-67) | yes |
| America | vs modern ≤65% | 51% (40-61) | 38% | 61% | 52% (41-62) | yes |
| Russia | vs modern ≤65% | 36% (27-47) | 54% | 46% | 39% (29-49) | yes |

Naval map, Little Big Lake [ran], reported and not tuned for. 210 games per run. R6 final: 0 errors, 38 draws (18%),
Allied side 51% against the Soviet side.

| Faction | R5 final: vs modern | R5 final: vs America+Russia | R6 final: vs modern | R6 final: vs America+Russia |
|---|---:|---:|---:|---:|
| China | 51% (36-67) | 71% (43-89) | 53% (37-68) | 58% (32-81) |
| Iran | 44% (30-60) | 54% (29-78) | 56% (40-70) | 75% (47-91) |
| Türkiye | 53% (37-68) | 50% (25-75) | 43% (28-59) | 50% (25-75) |
| Saudi Arabia | 51% (36-67) | 58% (32-81) | 51% (36-67) | 75% (47-91) |
| Yemen | 50% (34-66) | 17% (5-45) | 43% (28-59) | 46% (22-71) |
| Israel | 65% (49-79) | 62% (35-84) | 54% (38-69) | 62% (35-84) |
| Hezbollah | 35% (21-51) | 46% (22-71) | 50% (34-66) | 29% (11-57) |
| America | 49% (34-63) | — | 51% (37-66) | — |
| Russia | 49% (34-63) | — | 36% (23-51) | — |

On the naval map Hezbollah rose from 35% to 50% against the modern factions and Israel fell from 65% to 54%. Hezbollah
is at 29% (11-57) against America+Russia there, and Russia at 36% against the modern factions.

**Verdict, main.** [ran] All 16 targets are met, up from 15 in round 5.
- **Israel:** 56% → 42% (32-54) against the modern factions, on target.
- **Hezbollah:** 42% → 51% (39-62). That is 5 points under "about 56%", and 56% is inside its interval.
  Hezbollah is above Israel; Türkiye, Iran and Saudi Arabia (56-59%) are above both.
- **The Allied lean is fixed:** the Allied side scores 52% (44-60) against the Soviet side, down from 66%.
- **Iran:** 40% → 56% with the Karrar's coax (31% in both probes without it).
- **Yemen** is lowest of the modern factions at 40%, and Russia is at 39%.

### Round 6: what is left

1. **The two products split the request differently.** The target is about 60% for Hezbollah on standalone and
   about 56% on `main`. Shared rules moved both together; the result was 65% and 51%.
   - Across all probes and finals, the split between the products stayed inside the measurement noise. No change
     could aim at one product.
2. **Türkiye on standalone (38%).** The next lever is Türkiye's own anti-infantry, not the coax again. For example,
   the Turkish rifle's share in its doctrine. It was 46% in round 5.
3. **Harbor Line** still leans Allied (64%) and Twin Fords leans Soviet (27%). The coax cut moved Twin Fords, not
   Harbor Line. The map owner judged both maps fair by geometry (`docs/standalone.md`), so these are rules questions
   for a later round.
4. **Very short standalone games:** 2 of 252 were conquests at 3.5 minutes, when the starting units killed a
   construction yard. They are sent to the standalone agent as a kit-base question.

## Round 5: both products (2026-10-07/08)

[ran] One balance pass over both products. They share the faction rules (`mods/rtsai/modern-factions`).

**Main** (`main`):
- 7 modern factions plus America and Russia.
- Rules and bots:
  - bce9648;
  - the two bot commits ported from the standalone branch (9206146, 5b5faa9);
  - the round-5 rules (7fd8f3f).

**Standalone** (`rtsai/standalone`):
- The 7 modern factions only, on the kit base.
- The Heavy Power Plant, the Ore Purifier upgrade, ore mines and the superweapon bot.
- Maps: Twin Fords and Harbor Line.
- The final run used 841e844 with the round-5 rules. The standalone agent merged 7fd8f3f there as 9f765d2.

**Both:**
- Engine 68c1e95557.
- Normal bots and a 40-minute cap.
- 3 workers, with `OPENRA_AI_HOST=0`.

Targets:
- **Standalone:**
  - each faction scores 40-60% against the others;
  - draws are at most 15%;
  - both maps are reported.
- **Main:** the round-4 targets, with land and naval both reported:
  - 35-65% against the modern factions;
  - at least 35% against America+Russia;
  - America and Russia at most 65% against the modern factions.

There were three tuning rounds:
1. probe 1;
2. probe 2;
3. the final rule set, measured once at full scale.

### Standalone result

[ran] Final round robin (`r5-sa-final`): 252 games, both maps, every pairing in both orientations, 3 replicates. 0
errors, 40 draws (16%).

| vs | china | iran | turkey | saudi | yemen | israel | hezbollah | vs others |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **china** | — | 3-4 (5d) | 7-5 | 4-6 (2d) | 6-5 (1d) | 3-6 (3d) | 5-5 (2d) | 48% (37-59) |
| **iran** | 4-3 (5d) | — | 4-7 (1d) | 6-5 (1d) | 4-4 (4d) | 2-10 | 5-3 (4d) | 45% (34-57) |
| **turkey** | 5-7 | 7-4 (1d) | — | 5-6 (1d) | 3-6 (3d) | 4-5 (3d) | 4-6 (2d) | 46% (35-57) |
| **saudi** | 6-4 (2d) | 5-6 (1d) | 6-5 (1d) | — | 7-5 | 7-3 (2d) | 5-7 | 54% (43-65) |
| **yemen** | 5-6 (1d) | 4-4 (4d) | 6-3 (3d) | 5-7 | — | 0-8 (4d) | 4-6 (2d) | 43% (32-55) |
| **israel** | 6-3 (3d) | 10-2 | 5-4 (3d) | 3-7 (2d) | 8-0 (4d) | — | 5-7 | 60% (48-70) |
| **hezbollah** | 5-5 (2d) | 3-5 (4d) | 6-4 (2d) | 7-5 | 6-4 (2d) | 7-5 | — | 54% (43-65) |

The runs compared below:
- **Baseline:** e2efdd2, 252 games. It has the round-4 rules plus Hezbollah's new doctrine.
- **Probes 1 and 2:** 84 games each, 1 replicate, shown without an interval.
- **Final:** 841e844 plus the final rules, 252 games.

| Faction | Target | Baseline | Probe 1 | Probe 2 | Final | Met |
|---|---|---:|---:|---:|---:|---|
| China | vs others 40-60% | 25% (16-36) | 50% | 40% | 48% (37-59) | yes |
| Iran | vs others 40-60% | 61% (50-72) | 54% | 44% | 45% (34-57) | yes |
| Türkiye | vs others 40-60% | 40% (29-51) | 40% | 44% | 46% (35-57) | yes |
| Saudi Arabia | vs others 40-60% | 47% (35-58) | 52% | 60% | 54% (43-65) | yes |
| Yemen | vs others 40-60% | 56% (44-66) | 54% | 65% | 43% (32-55) | yes |
| Israel | vs others 40-60% | 50% (39-61) | 44% | 50% | 60% (48-70) | yes |
| Hezbollah | vs others 40-60% | 72% (61-81) | 56% | 48% | 54% (43-65) | yes |

Each map, baseline and final. The faction columns are each faction's score against the others on that map:

| Map, run | Games | Draws | Median minutes | Allied side vs Soviet side | China | Iran | Türkiye | Saudi Arabia | Yemen | Israel | Hezbollah |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Harbor Line, baseline | 126 | 17 (13%) | 15.5 | 40% (29-51) | 24% | 61% | 43% | 56% | 43% | 57% | 67% |
| Twin Fords, baseline | 126 | 47 (37%) | 31.8 | 22% (14-32) | 26% | 61% | 36% | 38% | 68% | 43% | 78% |
| Harbor Line, final | 126 | 14 (11%) | 14.0 | 65% (54-75) | 61% | 43% | 43% | 67% | 33% | 60% | 43% |
| Twin Fords, final | 126 | 26 (21%) | 25.5 | 42% (32-54) | 35% | 47% | 49% | 42% | 53% | 60% | 65% |

**Verdict, standalone.** [ran] All seven factions are inside 40-60%. Israel is at the edge: 59.7%, rounded to 60%.

Draws are 16% (40 of 252). That misses the 15% target by one point, within noise (12-21%).
- Harbor Line: 11% draws.
- Twin Fords: 21% draws, down from 37% at baseline.

The standalone agent changed Twin Fords twice during this round:
- 68a7e75 added a central crossing. In the Twin Fords probe (`r5-sa-tf`, probe-2 rules), draws fell to 19%.
- 841e844 made the two gem fords 50% wider. It was first measured in the final, so its effect is not separated
  from the final rule changes.

Overall, the Allied side scores 54% (46-62) against the Soviet side; it was 31% at baseline. By map:
- **Harbor Line:** 40% → 65%. Harbor Line now leans Allied, so China is 61% there and Yemen 33%.
- **Twin Fords:** 22% → 42%. With the central crossing alone (the Twin Fords probe) it was still 23%. The wider
  fords and the final rules came together.
- The per-map scores have intervals of about ±15 points. The targets are set on both maps together, so neither map
  is tuned separately here.

### Why the Allied side lost in the standalone game

[ran] At baseline (e2efdd2), the Allied side scored 31% (24-39) against the Soviet side, and 22% on Twin Fords:
- Allied side: China, Türkiye, Saudi Arabia, Israel.
- Soviet side: Iran, Yemen, Hezbollah.

**Not economy.**
- By minute 10 the Allied factions had earned 23.9-25.8k, against 22.0-24.4k for the Soviet side.
- The Allied bots put more of it into buildings: 13.8-15.0k, against 11.7-13.0k. Part of that was an Air Force
  Command in the opening, which then waited about ten minutes for aircraft.
- Their armies at minute 10 were smaller: 3.0-4.9k against 5.3-6.5k.

**Not superweapons.** 83 teleports and 25 shields in 252 games, about 0.2 per side per game. Ore Purifiers came late,
about one per game.

**The cause is doctrine against infantry.**
- The Allied-side armies are tank-led. The MBT is 20-29% of their production, and its main gun does 25% damage to
  infantry. These tanks traded 0.80-0.87 destroyed per credit.
- The Soviet-side armies are infantry-led. Their cheap riflemen, Yemen's Mountain Rifleman and Hezbollah's Line
  Fighter, trade 2.9 destroyed per credit.
- China against the Soviet side:
  - the Qilin was 20% of China's production and made 12% of its kills (0.72 per credit);
  - the PHL rocket artillery traded 0.69 per credit;
  - China's riflemen made 35% of its kills.

**The map made it worse.** Twin Fords funnels both armies through two fords, which favours massed infantry.

The fixes went to that cause: tanks that can kill infantry, artillery that breaks it, and openings that put the money
into the army.

### Round 5 changes

All seven changes are in `mods/rtsai/modern-factions` (7fd8f3f), each with its reason in a comment next to it.
Each change says which run first had it: probe 1, probe 2 or the final.

1. **Coaxial machine gun on the Allied-side MBTs.**
   - Costs: Qilin 700 → 750, Bozkir 900 → 950, M1A2S 1100 → 1150, Merkava 1250 → 1300.
   - The new weapon, `R2QilinCoax`, does 16 damage every 20 ticks at range 5, about one rifleman's fire.
   - Why: the tanks could not kill the infantry that beat them.
   - Probe 1 gave the coax to the Qilin alone. Probe 2 gave it to the other three MBTs, because Türkiye, Saudi
     Arabia and Israel had the same gap.
   - Effect, standalone baseline → final, destroyed per credit:
     - Qilin: 0.80 → 1.55
     - Bozkir: 0.83 → 1.59
     - M1A2S: 0.87 → 1.56
     - Merkava: 0.82 → 1.40
2. **China's PHL** (probe 1).
   - HP 160 → 220.
   - Rockets: Spread 256 → 341. Damage to None armour goes from 70% to 100%, and to Flak from 70% to 90%.
   - Why: the PHL traded 0.69-0.73 per credit and died to the infantry armies it should break.
   - Effect: 0.89 per credit in the final.
3. **China's bot** (probe 1).
   - Doctrine artillery share 60 → 100 (more PHL).
   - Sky Shield AA sites 7 → 3: they made 1.5% of China's kills and cost 2.4k a game.
   - Bastions 9 → 12: they made 8-9% of its kills.
   - No Air Force Command in the opening.
   - China stays armour-led. The Qilin was 20% of China's production and 13% of its kills; it is now 23% and 29%.
4. **Türkiye's bot.**
   - No Air Force Command in the opening (probe 1).
   - Support, transport and strike-aircraft shares halved (final).
     - Why: Sancak 0.24, Aras 0.36 and Kuzgun 0.54 destroyed per credit.
     - The base shares are 3, 3 and 6. Integer rounding takes them to 1, 1 and 3.
     - The bot now builds almost no Sancaks or Aras: 0-0.1% of production, down from 4-6%.
     - The money goes to Bozkirs: 34% of production and 42% of kills.
5. **Hezbollah Line Fighter 275 → 300** (probe 1).
   - It traded 2.88 per credit and made 30% of Hezbollah's kills.
   - At 300 it still trades 2.86 in the standalone final, and 1.44 on `main`.
6. **Yemen Mountain Rifleman 150 → 165** (final). It traded 2.88 per credit and made 30% of Yemen's kills; now 2.59.
7. **Commando bot delay 20 → 10 minutes** (probe 1). This covers Saudi `r2falcon` and Israeli `r2ilrecon`, in every
   bot profile. See "The commando delay" below.

### Main result

[ran] Final round robin (`r5-main-final`): 420 games on Dustbowl and Official Tournament Map A. 0 errors, 81 draws
(19%; 15% in round 4), median 23.8 game minutes. Draws by map: Dustbowl 62 (30%; round 4: 27%), Tournament Map A
19 (9%; round 4: 4%).

| vs | china | iran | turkey | saudi | yemen | israel | hezbollah | america | russia | vs modern | vs America+Russia |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **china** | — | 6-4 (2d) | 6-4 (2d) | 5-5 (2d) | 7-5 | 5-4 (3d) | 4-2 (6d) | 4-6 (2d) | 9-3 | 56% (45-67) | 58% (39-76) |
| **iran** | 4-6 (2d) | — | 5-6 (1d) | 2-7 (3d) | 4-7 (1d) | 4-7 (1d) | 5-6 (1d) | 3-5 (4d) | 4-4 (4d) | 40% (29-51) | 46% (28-65) |
| **turkey** | 4-6 (2d) | 6-5 (1d) | — | 4-7 (1d) | 7-3 (2d) | 5-5 (2d) | 9-3 | 6-4 (2d) | 6-2 (4d) | 54% (43-65) | 62% (43-79) |
| **saudi** | 5-5 (2d) | 7-2 (3d) | 7-4 (1d) | — | 9-0 (3d) | 6-2 (4d) | 7-5 | 7-4 (1d) | 6-2 (4d) | 66% (54-76) | 65% (45-80) |
| **yemen** | 5-7 | 7-4 (1d) | 3-7 (2d) | 0-9 (3d) | — | 3-8 (1d) | 3-7 (2d) | 3-6 (3d) | 5-3 (4d) | 35% (25-47) | 48% (30-67) |
| **israel** | 4-5 (3d) | 7-4 (1d) | 5-5 (2d) | 2-6 (4d) | 8-3 (1d) | — | 8-2 (2d) | 5-3 (4d) | 9-1 (2d) | 56% (45-67) | 71% (51-85) |
| **hezbollah** | 2-4 (6d) | 6-5 (1d) | 3-9 | 5-7 | 7-3 (2d) | 2-8 (2d) | — | 4-5 (3d) | 3-4 (5d) | 42% (32-54) | 46% (28-65) |
| **america** | 6-4 (2d) | 5-3 (4d) | 4-6 (2d) | 4-7 (1d) | 6-3 (3d) | 3-5 (4d) | 5-4 (3d) | — | — | 51% (40-61) | — |
| **russia** | 3-9 | 4-4 (4d) | 2-6 (4d) | 2-6 (4d) | 3-5 (4d) | 1-9 (2d) | 4-3 (5d) | — | — | 36% (27-47) | — |

The runs compared below:
- **R5 baseline:** `main`'s rules before this round. The round-4 final (`r4-final`) has the same rules for every pair
  without Hezbollah. Hezbollah's pairs come from its as-built run (`r5-hz-t5`, d646808, the rules `main` has since
  8357c9b). Together: 420 games.
- **Probe 2:** the port plus the probe-2 rules, 140 games, shown without an interval.
- **Final:** 7fd8f3f, 420 games.

| Faction | Target | R5 baseline | Probe 2 | Final | Met |
|---|---|---:|---:|---:|---|
| China | vs modern 35-65% | 33% (24-45) | 46% | 56% (45-67) | yes |
| Iran | vs modern 35-65% | 58% (46-68) | 33% | 40% (29-51) | yes |
| Türkiye | vs modern 35-65% | 40% (29-51) | 56% | 54% (43-65) | yes |
| Saudi Arabia | vs modern 35-65% | 41% (30-53) | 56% | 66% (54-76) | **no**, within noise |
| Yemen | vs modern 35-65% | 64% (52-74) | 46% | 35% (25-47) | yes |
| Israel | vs modern 35-65% | 46% (35-57) | 71% | 56% (45-67) | yes |
| Hezbollah | vs modern 35-65% | 69% (57-78) | 42% | 42% (32-54) | yes |
| China | vs America+Russia ≥35% | 54% (35-72) | 75% | 58% (39-76) | yes |
| Iran | vs America+Russia ≥35% | 44% (26-63) | 56% | 46% (28-65) | yes |
| Türkiye | vs America+Russia ≥35% | 52% (33-70) | 25% | 62% (43-79) | yes |
| Saudi Arabia | vs America+Russia ≥35% | 50% (31-69) | 62% | 65% (45-80) | yes |
| Yemen | vs America+Russia ≥35% | 42% (24-61) | 75% | 48% (30-67) | yes |
| Israel | vs America+Russia ≥35% | 48% (30-67) | 69% | 71% (51-85) | yes |
| Hezbollah | vs America+Russia ≥35% | 40% (23-59) | 50% | 46% (28-65) | yes |
| America | vs modern ≤65% | 54% (43-64) | 45% | 51% (40-61) | yes |
| Russia | vs modern ≤65% | 52% (42-63) | 38% | 36% (27-47) | yes |

Naval map, Little Big Lake [ran], reported and not tuned for. 210 games per run. The R5 baseline is built like the
land one, from `r4-final-naval` and `r5-hz-t5-naval`. Final: 0 errors, 33 draws (16%).

| Faction | R5 baseline: vs modern | R5 baseline: vs America+Russia | R5 final: vs modern | R5 final: vs America+Russia |
|---|---:|---:|---:|---:|
| China | 39% (25-55) | 54% (29-78) | 51% (36-67) | 71% (43-89) |
| Iran | 57% (41-72) | 58% (32-81) | 44% (30-60) | 54% (29-78) |
| Türkiye | 38% (24-54) | 58% (32-81) | 53% (37-68) | 50% (25-75) |
| Saudi Arabia | 68% (52-81) | 67% (39-86) | 51% (36-67) | 58% (32-81) |
| Yemen | 57% (41-72) | 46% (22-71) | 50% (34-66) | 17% (5-45) |
| Israel | 46% (31-62) | 46% (22-71) | 65% (49-79) | 62% (35-84) |
| Hezbollah | 46% (31-62) | 50% (25-75) | 35% (21-51) | 46% (22-71) |
| America | 46% (32-61) | — | 49% (34-63) | — |
| Russia | 45% (31-60) | — | 49% (34-63) | — |

**Verdict, main.** [ran] 15 of 16 land targets are met.

China is fixed and stays armoured:
- 33% → 56% (45-67) against the modern factions, and 58% against America+Russia.
- The Qilin is 23% of China's production and makes 29% of its kills, at 1.41 destroyed per credit.

The one miss is Saudi Arabia: 66% (54-76) against the modern factions. It misses by one point, within noise.

On `main` the balance swung from the Soviet side to the Allied side:
- The Allied side scored 30% (23-38) against the Soviet side at baseline and 66% (58-74) in the final.
- All three Soviet-side modern factions are now at 35-42% against the modern factions, as is Russia (36%).
- Standalone, the same rules give 54%.
- [inferred] `main`'s maps are open (Dustbowl, Tournament Map A), so the coax-armed tanks meet infantry in the open.
  Twin Fords channels both armies through fords.
- The Allied side's score by map:

| Run | Map | Allied side vs Soviet side |
|---|---|---:|
| Main final | Dustbowl | 62% |
| Main final | Tournament Map A | 71% |
| Standalone final | Harbor Line | 65% |
| Standalone final | Twin Fords | 42% |

Naval (not tuned for):
- **Yemen** is 17% (5-45) against America+Russia: 1-10 with 1 draw. Its interval still reaches 35%.
- **Israel** is 65% against the modern factions.
- **Hezbollah** is 35% against the modern factions.
- Every other score is between 44% and 71%.

### The commando delay (Israeli and Saudi precision strikes)

[ran] The Saudi and Israeli commandos carry the precision strike: one bomber, ChargeInterval 1800. The bots fire it
since 4fb8dfb, which is on `main` as 5b5faa9. Delay 20 minutes in the baseline, 10 in the final:

| Run | Faction | Commando fielded in | Median first commando | Strike kills per game |
|---|---|---:|---:|---:|
| Standalone baseline (20 min) | Saudi Arabia | 31% of games | 23.0 min | 122 credits |
| Standalone baseline (20 min) | Israel | 35% | 24.5 min | 51 credits |
| Standalone final (10 min) | Saudi Arabia | 35% | 18.3 min | 111 credits |
| Standalone final (10 min) | Israel | 39% | 18.0 min | 118 credits |
| Main final (10 min) | Saudi Arabia | 48% | 17.0 min | 315 credits |
| Main final (10 min) | Israel | 44% | 17.9 min | 270 credits |

**Decision: keep 10 minutes.**
- [ran] The strike destroys 50-430 credits a game in every run of this round. A side destroys 34-44k a game, so
  that is at most about 1%. The delay is not a balance lever.
- At 10 minutes, the median first commando comes about 5-7 game minutes earlier: 17-18 game minutes, from 23-25.
  When the bot fields one, the strike lands mid-game instead of in the last minutes.
- [inferred] Removing the delay is not advised. The commando traded 0.5 per credit in round 4. Fielded in the first
  minutes, it would cost the bot its opening army.

### Bot work ported to main

[ran] The standalone agent and this pass agreed how to split the work:
- The faction rules are tuned on `main` and merged into `rtsai/standalone`.
- Standalone-only files stay on the standalone branch, owned by its generators. These are the kit rules, the Heavy
  Power Plant, the Purifier and the maps.

The two bot commits were cherry-picked to `main`:
- **9206146** (from b6fc566): superweapons.
  - `SuperweaponBotModule` teleports the most valuable army group (at least 3000) to an enemy building cluster it
    can take on.
  - It shields an army group under attack.
  - Every profile builds `gacsph` / `nairon`. `main` has both buildings (the Chronosphere and the Iron Curtain), so
    the module applies.
  - Plugs are built only while a host accepts one.
- **5b5faa9** (from 4fb8dfb): the bot decisions for the Israeli and Saudi precision strikes.

Superweapon use in the finals:
- `main`, 420 games: 202 teleports and 25 shields. America and the Allied-side modern factions teleport; Iran,
  Russia, Yemen and Hezbollah shield.
- Standalone, 252 games: 53 teleports and 21 shields.

`make.cmd all` and `make.cmd test` on `main`: 0 warnings, 0 errors.

### Round 5: what is left

The round was capped at three tuning rounds, so these stay open.

1. **`main` leans Allied: 66% Allied side against the Soviet side.** Every target but one is met. The levers that
   would move it back without undoing the standalone balance:
   - the coax damage, 16 → 12;
   - or give the Soviet-side main tanks their own anti-infantry gun. The Toophan is 34% of Iran's production at
     0.77 destroyed per credit.
2. **Harbor Line leans Allied at 65%.** Twin Fords still leans Soviet at 42%. Both maps belong to the standalone
   agent; the tools are its map generator and more replicates per map.
3. **Draws.** [ran]
   - Standalone: 16% (Twin Fords 21%).
   - `main`: 19%, up from 15% in round 4. Dustbowl: 30%, from 27%. Tournament Map A: 9%, from 4%.
4. **Türkiye's halved shares.** They fell to 1 by integer rounding, so the bot builds almost no support or transport
   vehicles. That suited this pass. A doctrine that wants a small, non-zero share needs base shares above 3.

## Round 5: Hezbollah "Salvo and swarm" (2026-10-07)

[ran] Branch `rtsai/hezbollah-doctrine` (local, from `main` 3db6883). Only Hezbollah changed. It now follows the
owner's doctrine: basic missiles, very powerful soldiers, very mini drones. The design and the build are in
`docs/hezbollah-doctrine.md`. The other eight factions keep the round-4 rules, so the round-4 tables below still hold
for every pair without Hezbollah.

The campaigns (`docs/balance-data/r5-hz-campaigns.json`, `focus: [hezbollah]`) pit Hezbollah against all eight other
factions with normal bots and a 40-minute cap:
- land: Dustbowl and Official Tournament Map A, both orientations, 3 replicates (96 games);
- naval: Little Big Lake (48 games);
- probes: 1 replicate (32 games).

Every run had 0 errors.

| Run | Rules | Games | vs modern (35-65%) | vs America+Russia (≥35%) |
|---|---|---:|---:|---:|
| Round 4 final (reference) | e2c07b0 | 420 | 57% (45-68) | 48% (30-67) |
| Probe, as designed | 2ed217e | 32 | 71% | 25% |
| Land, as designed (stopped) | 2ed217e | 42 | 84% (68-93) | 70% (40-89) |
| Probe, trim 1 (rules overlay) | 2ed217e + overlay | 32 | 65% | 44% |
| Trims 1-2 | b70d61e | 96 | 70% (59-79) | 38% (21-57) |
| Trim 3 (stopped) | efe7750 | 47 | 69% (53-82) | 32% (12-61) |
| Trim 4 | 85d07d4 | 96 | 72% (61-81) | 75% (55-88) |
| **Trim 5 (built)** | **d646808** | **96** | **69% (57-78)** | **40% (23-59)** |
| Naval, round 4 final (reference) | e2c07b0 | 210 | 54% (38-69) | 67% (39-86) |
| Naval, trim 5 | d646808 | 48 | 46% (31-62) | 50% (25-75) |

Trim 5, Hezbollah's wins-losses (draws) against each faction:

| | china | iran | turkey | saudi | yemen | israel | america | russia |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **hezbollah**, land | 10-1 (1d) | 4-3 (5d) | 9-2 (1d) | 9-3 | 4-6 (2d) | 9-3 | 3-6 (3d) | 4-6 (2d) |
| **hezbollah**, naval | 3-1 (2d) | 3-2 (1d) | 1-1 (4d) | 2-4 | 1-4 (1d) | 2-3 (1d) | 1-0 (5d) | 2-3 (1d) |

The trims:
1. Trims 1-2 (b70d61e):
   - the AT team costs 500 and loses its stationary concealment;
   - the Line Fighter costs 275 (it traded 2.07 destroyed per credit at 225);
   - rough-ground cover goes from x0.80 to x0.90.
2. Trim 3 (efe7750): the AT team gets its concealment back at 550, and the rifle drops from 16 to 14. Without
   concealment, Hezbollah fell to 21% against America, whose bots field almost no detectors.
3. Trim 4 (85d07d4), aimed at the trade gap:
   - the AT rocket does 65% against heavy armour and 80% against medium armour (was 95% and 100%);
   - the AT team costs 500, with its concealment;
   - the Rocket Battery and the Rail Technical do full damage to infantry;
   - the bot's anti-air share goes from 24 to 40;
   - the rifle goes back to 16.
4. Trim 5 (d646808): every fighter still leaves the barracks Veteran but earns Elite at the usual rate (the 60%
   promotion thresholds are gone). The Cedar Scout, the hero, starts Veteran instead of Elite.

**Verdict.** [ran] The trim cap was two rounds after trim 3. Trim 5 is the configuration closest to both bands.
- America+Russia is met: 40% (23-59).
- Naval is inside the band on both sides: 46% (31-62) and 50% (25-75).
- The modern band is missed by 4 points, within noise: 69% (57-78).

[inferred] Hezbollah-side levers cannot separate the two scores:
- Across the four trimmed rule sets, the modern score stayed at 69-72% while America+Russia moved from 32% to 75%.
- Most of the gap is China, the round-4 miss (33% against the modern factions). Hezbollah beat China 11-1 in round
  4 and 10-1 (1 draw) here. Against the other five modern factions, Hezbollah scores 65%.
- The rest is defence. America's and Russia's infantry and base defences (pillboxes, Tesla coils, Prism towers,
  sentry guns) kill about 27,000 credits of Hezbollah per game. The modern factions' rifle infantry, militia,
  bunkers and bastions kill about 12,000.

Closing the gap needs an all-faction pass: China's strength and the modern factions' anti-infantry. The full
analysis is in `docs/hezbollah-doctrine.md`, "As built".

## Round 4 result

[ran] Final round robin on the round-4 rules and bots (e2c07b0, engine 68c1e95557): 420 games on Dustbowl and
Official Tournament Map A: 0 errors, 65 tick-cap draws, median 24.8 game minutes.

Row's wins-losses (draws) against the column; the last two columns are the row's score with its 95% Wilson interval:

| vs | china | iran | turkey | saudi | yemen | israel | hezbollah | america | russia | vs modern | vs America+Russia |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **china** | — | 5-7 | 4-8 | 5-5 (2d) | 2-8 (2d) | 4-7 (1d) | 1-11 | 4-4 (4d) | 5-3 (4d) | 33% (23-44) | 54% (35-72) |
| **iran** | 7-5 | — | 7-3 (2d) | 6-5 (1d) | 5-6 (1d) | 7-1 (4d) | 3-7 (2d) | 3-8 (1d) | 6-4 (2d) | 56% (44-66) | 44% (26-63) |
| **turkey** | 8-4 | 3-7 (2d) | — | 4-8 | 3-8 (1d) | 6-5 (1d) | 4-6 (2d) | 3-5 (4d) | 6-3 (3d) | 43% (32-55) | 52% (33-70) |
| **saudi** | 5-5 (2d) | 5-6 (1d) | 8-4 | — | 2-8 (2d) | 3-7 (2d) | 9-3 | 7-2 (3d) | 3-8 (1d) | 49% (38-61) | 50% (31-69) |
| **yemen** | 8-2 (2d) | 6-5 (1d) | 8-3 (1d) | 8-2 (2d) | — | 4-4 (4d) | 6-4 (2d) | 2-6 (4d) | 5-5 (2d) | 64% (52-74) | 42% (24-61) |
| **israel** | 7-4 (1d) | 1-7 (4d) | 5-6 (1d) | 7-3 (2d) | 4-4 (4d) | — | 5-7 | 7-4 (1d) | 2-6 (4d) | 49% (37-60) | 48% (30-67) |
| **hezbollah** | 11-1 | 7-3 (2d) | 6-4 (2d) | 3-9 | 4-6 (2d) | 7-5 | — | 3-8 (1d) | 7-3 (2d) | 57% (45-68) | 48% (30-67) |
| **america** | 4-4 (4d) | 8-3 (1d) | 5-3 (4d) | 2-7 (3d) | 6-2 (4d) | 4-7 (1d) | 8-3 (1d) | — | — | 55% (44-65) | — |
| **russia** | 3-5 (4d) | 4-6 (2d) | 3-6 (3d) | 8-3 (1d) | 5-5 (2d) | 6-2 (4d) | 3-7 (2d) | — | — | 49% (38-59) | — |

Targets, as scores (draw = half a win). Each row shows four runs:
- R3 final: the round-3 result.
- R4 baseline: the same rules after the bot spending fix.
- Probe: one replicate of the round-4 changes, 140 games, shown without an interval.
- R4 final.

"Within noise" means the point estimate misses the target but the 95% interval still reaches it.

| Faction | Target | R3 final | R4 baseline | Probe | R4 final | Met |
|---|---|---:|---:|---:|---:|---|
| China | vs modern 35-65% | 37% (27-48) | 33% (24-45) | 44% | 33% (23-44) | **no**, within noise |
| Iran | vs modern 35-65% | 56% (45-67) | 64% (52-74) | 50% | 56% (44-66) | yes |
| Türkiye | vs modern 35-65% | 41% (30-53) | 33% (23-44) | 54% | 43% (32-55) | yes |
| Saudi Arabia | vs modern 35-65% | 44% (34-56) | 41% (30-53) | 46% | 49% (38-61) | yes |
| Yemen | vs modern 35-65% | 67% (56-77) | 72% (60-81) | 62% | 64% (52-74) | yes |
| Israel | vs modern 35-65% | 42% (32-54) | 45% (34-57) | 42% | 49% (37-60) | yes |
| Hezbollah | vs modern 35-65% | 62% (50-72) | 62% (51-73) | 52% | 57% (45-68) | yes |
| China | vs America+Russia ≥35% | 33% (18-53) | 21% (9-40) | 50% | 54% (35-72) | yes |
| Iran | vs America+Russia ≥35% | 40% (23-59) | 42% (24-61) | 38% | 44% (26-63) | yes |
| Türkiye | vs America+Russia ≥35% | 46% (28-65) | 33% (18-53) | 56% | 52% (33-70) | yes |
| Saudi Arabia | vs America+Russia ≥35% | 65% (45-80) | 50% (31-69) | 31% | 50% (31-69) | yes |
| Yemen | vs America+Russia ≥35% | 42% (24-61) | 48% (30-67) | 62% | 42% (24-61) | yes |
| Israel | vs America+Russia ≥35% | 54% (35-72) | 42% (24-61) | 62% | 48% (30-67) | yes |
| Hezbollah | vs America+Russia ≥35% | 54% (35-72) | 40% (23-59) | 38% | 48% (30-67) | yes |
| America | vs modern ≤65% | 62% (52-72) | 66% (55-75) | 59% | 55% (44-65) | yes |
| Russia | vs modern ≤65% | 42% (32-53) | 55% (45-66) | 45% | 49% (38-59) | yes |

**Verdict.** [ran] Round 4 was one bounded pass, as asked. First it fixed the bots' waste on ships and jets for every
faction. Then it made four changes against the re-baseline those fixes produced. 15 of 16 targets are met.
- Both narrow misses of round 3 are closed:
  - China against America and Russia, 33% → 54% (35-72);
  - Yemen against the modern factions, 67% → 64% (52-74).
- America is at 55% (44-65) against the modern factions and Russia at 49%.
- The one miss is China against the modern factions, 33% (23-44). It is within noise, so it is recorded and tuning
  stops here.
- On the naval map (reported, not tuned for):
  - Hezbollah fell from 69% (R3 final) and 67% (R4 baseline) to 54% (38-69) against the modern factions.
  - Saudi Arabia is now at 68% (52-81) and Türkiye at 33% (20-50). Both are within noise.
  - America is at 45% and Russia at 42%.

Naval map, Little Big Lake [ran], not tuned for. 210 games per run; the R4 baseline and R4 final use the fixed bots.
The naval-reachability check keeps both navies on this map (its water is 11-12 cells from both starts):

| Faction | R4 baseline: vs modern | R4 baseline: vs America+Russia | R4 final: vs modern | R4 final: vs America+Russia |
|---|---:|---:|---:|---:|
| China | 40% (26-56) | 50% (25-75) | 38% (24-54) | 54% (29-78) |
| Iran | 42% (27-58) | 21% (7-49) | 61% (45-75) | 58% (32-81) |
| Türkiye | 44% (30-60) | 46% (22-71) | 33% (20-50) | 58% (32-81) |
| Saudi Arabia | 51% (36-67) | 71% (43-89) | 68% (52-81) | 67% (39-86) |
| Yemen | 51% (36-67) | 58% (32-81) | 53% (37-68) | 46% (22-71) |
| Israel | 54% (38-69) | 75% (47-91) | 43% (28-59) | 46% (22-71) |
| Hezbollah | 67% (50-80) | 75% (47-91) | 54% (38-69) | 67% (39-86) |
| America | 31% (19-46) | — | 45% (31-60) | — |
| Russia | 56% (41-70) | — | 42% (28-57) | — |

## Round 4: the bot spending fix

[ran] In round 3 every bot, stock and modern, put money into units it could not use. On the two land maps 7-12% of
each faction's production was ships, and 11.5-11.9% of America's, Saudi Arabia's and Israel's was airfield jets.
Both came from the bot, not from faction rules, so round 4 fixed them in the bot for all nine factions:

- **Ships only where they can reach the enemy.** [ran] The upstream base builder builds a shipyard whenever it finds
  a 3x3 patch of water within its base radius (50 cells).
  - On Dustbowl that is pieces of the river 26-33 cells from either start, split by bridges and falls. Ships built
    there mostly fought each other: 5.3k of the 7.8k value they destroyed per game was other ships.
  - On Tournament Map A it is the outer ocean, 19 cells from the starts.

  `DoctrineBaseBuilderBotModule` now also asks the path finder whether a naval unit (Locomotor `naval`) can get from
  that water to water within `NavalTargetRadius` (16 cells) of an enemy start location. The 16 cells are about half
  a base plus a destroyer's 8-cell gun.
  - Little Big Lake (water 11-12 cells from both starts) passes. [inferred from the map layouts] So do the mod's other
    naval maps whose starts have water within 16 cells.
  - Dustbowl and Tournament Map A no longer get shipyards.
  - Each bot logs the check (`naval: ...` in `bot-doctrine.log`).

  This is mod code (two files in `OpenRA.Mods.RTSAI`), because no existing bot option can express "reachable".
- **One jet of each airfield type at a time.** [ran] The bot builds a jet whenever its airfield queue is free and a
  pad is empty. America rebuilt 4.6 Harriers a game, and Saudi Arabia and Israel 2.0-2.2 jets at 2,200 credits, all
  at 0.28-0.42 destroyed per credit.
  - `UnitLimits` 1 now applies to every airfield jet in all five bot profiles: Harrier and Black Eagle in
    `combined-arms-ai.yaml`; Skyspear, Şahin, F-15 and Israel's jet in the faction files (they had 4).
  - This uses only existing bot options.
  - Helicopters and drones, built at the war factory, are unchanged.

Production share before and after the fix (R3 final → R4 baseline, land maps):

| Faction | Ships | Airfield jets |
|---|---:|---:|
| China | 11.8% → 0% | 5.6% → 4.0% |
| Iran | 7.4% → 0% | — |
| Türkiye | 11.3% → 0% | 6.0% → 3.7% |
| Saudi Arabia | 8.0% → 0% | 11.9% → 8.2% |
| Yemen | 9.1% → 0% | — |
| Israel | 8.8% → 0% | 11.5% → 9.0% |
| Hezbollah | 9.5% → 0% | — |
| America | 8.4% → 0% | 11.5% → 6.7% |
| Russia | 7.4% → 0% | — |

What the fix did to the balance [ran] (R3 final → R4 baseline, against the modern factions):
- All the money went into the land war, and draws fell from 102 to 52.
- The modern factions on the Soviet side (Iran, Yemen, Hezbollah) gained the most. Iran went 56% → 64%, Yemen 67% → 72%,
  Hezbollah 62% → 62%. Their infantry-heavy armies, with cheap anti-tank teams, met more of the vehicle-heavy Allied-side
  armies.
- China fell 37% → 33% and Türkiye 41% → 33%. China fell to 21% against America and Russia.
- America rose 62% → 66%: its jets had been its worst spending.

The round-4 tuning answers that new baseline.

## Round 4: changes after the re-baseline

All in e2c07b0. The last column shows the effect:
- for 16-17, R3 final → R4 baseline;
- for 18-21, enemy value destroyed per credit produced, R4 baseline → probe.

| # | Change | Reason | Destroyed / credit |
|---|---|---|---|
| 16 | Naval reachability check (`NavalTargetRadius` 16) in the bot base builder, all factions | Ships on land maps: 7-12% of production | ships 0% of land production |
| 17 | `UnitLimits` 1 for each airfield jet, all factions and profiles | Jets 11.5-11.9% of three factions' production at 0.28-0.42 | jets 6.7-9.0% of production, never more than one alive |
| 18 | Yemen and Hezbollah RPG teams 300 → 350 credits | 80 damage at 95% against heavy armour every 90 ticks for 300 credits is 2.8 per tick per 1,000 credits, the most of any AT team; at 350 it is 2.4, the Saudi ATGM's. RPGs were 29% and 25% of Yemen's and Hezbollah's production and caused 30% and 26% of China's and Türkiye's losses to Yemen | Yemen 0.85 → 0.62, Hezbollah 0.86 → 0.75 |
| 19 | ZBD autocannon: Burst 2 → 3, ReloadDelay 40 → 30 | It fired 0.7 damage per tick for 850 credits, half the Bradley's 1.4 at the same cost | 0.33 → 0.79 |
| 20 | China support share 150 → 100 | Lynx 4.2% of production at 0.24 | Lynx share 4.2 → 2.0% |
| 21 | Türkiye main-battle-tank share 130 → 110 | Bozkır 30% of production at 0.83; riflemen 1.26 and AT teams 1.18 | Bozkır 0.83 → 0.91 |

Numbering continues from round 3. Changes 18-21 are the minimal set: one cost, one weapon and two doctrine weights.
America's and Russia's rules are unchanged; their bots get the same spending fix (16, 17) as everyone.

The probe [ran] moved every changed unit as intended (last column above). It put all seven modern factions at 42-62%
against each other, but at 140 games its scores are ±20 points, and the final full round robin is the result.

## Round 4: what is left

- **China against the modern factions, 33% (23-44): within noise, not tuned further.** [ran] China now beats America
  and Russia (54%), but it lost to Hezbollah 1-11 and Yemen 2-8.
  - Its Qilin and PHL are 38% of its production and destroyed 0.68 and 0.75 per credit against the modern factions.
  - Its riflemen and AT teams destroyed 1.58 and 1.21.
  - Hezbollah and Yemen's infantry, RPG and rocket-truck armies kill exactly the vehicles China's doctrine leads with.

  [inferred] This is the same counter structure as Yemen in round 3. The doctrine-consistent next step would be a
  smaller China MBT share, which is a doctrine-identity choice for the owner rather than a balance number.
- **Free infantry by side** (round 3) is unchanged. Cloning Vats and armed War Miners favour the Soviet-side
  factions. America's paratroopers are its national power.
- **Airfield jets** are capped, not gone. In the final they were 4-8% of the production of the five factions with an
  airfield (America 8.4%, Israel 7.4%, Saudi Arabia 6.9%), because the bot rebuilds each jet it loses.
- **Not measured:** human play, other bot profiles, other maps' naval reachability beyond the layout check, team games.

## Round 3 result (2026-10-06)

[ran] Final round robin on the round-3 rules (a47654a): 420 games on Dustbowl and Official Tournament Map A, 0 errors,
102 tick-cap draws, median 26.0 game minutes. Row's wins-losses (draws) against the column; the last two columns are
the row's score with its 95% Wilson interval:

| vs | china | iran | turkey | saudi | yemen | israel | hezbollah | america | russia | vs modern | vs America+Russia |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **china** | — | 5-5 (2d) | 7-3 (2d) | 2-7 (3d) | 1-9 (2d) | 4-5 (3d) | 1-10 (1d) | 1-7 (4d) | 3-5 (4d) | 37% (27-48) | 33% (18-53) |
| **iran** | 5-5 (2d) | — | 9-2 (1d) | 8-1 (3d) | 1-7 (4d) | 7-2 (3d) | 2-6 (4d) | 1-6 (5d) | 5-5 (2d) | 56% (45-67) | 40% (23-59) |
| **turkey** | 3-7 (2d) | 2-9 (1d) | — | 4-4 (4d) | 3-7 (2d) | 7-3 (2d) | 4-6 (2d) | 3-4 (5d) | 4-5 (3d) | 41% (30-53) | 46% (28-65) |
| **saudi** | 7-2 (3d) | 1-8 (3d) | 4-4 (4d) | — | 4-6 (2d) | 4-5 (3d) | 4-7 (1d) | 4-5 (3d) | 8-0 (4d) | 44% (34-56) | 65% (45-80) |
| **yemen** | 9-1 (2d) | 7-1 (4d) | 7-3 (2d) | 6-4 (2d) | — | 5-4 (3d) | 5-1 (6d) | 3-8 (1d) | 6-5 (1d) | 67% (56-77) | 42% (24-61) |
| **israel** | 5-4 (3d) | 2-7 (3d) | 3-7 (2d) | 5-4 (3d) | 4-5 (3d) | — | 3-6 (3d) | 4-6 (2d) | 6-2 (4d) | 42% (32-54) | 54% (35-72) |
| **hezbollah** | 10-1 (1d) | 6-2 (4d) | 6-4 (2d) | 7-4 (1d) | 1-5 (6d) | 6-3 (3d) | — | 4-5 (3d) | 5-2 (5d) | 62% (50-72) | 54% (35-72) |
| **america** | 7-1 (4d) | 6-1 (5d) | 4-3 (5d) | 5-4 (3d) | 8-3 (1d) | 6-4 (2d) | 5-4 (3d) | — | — | 62% (52-72) | — |
| **russia** | 5-3 (4d) | 5-5 (2d) | 5-4 (3d) | 0-8 (4d) | 5-6 (1d) | 2-6 (4d) | 2-5 (5d) | — | — | 42% (32-53) | — |

Targets, as scores (draw = half a win). Baseline and Final are full round robins (420 games each: a modern faction
plays 72 games against the other modern factions and 24 against America and Russia, an original country 84 against
the modern factions); P1 and P2 are one-replicate probes (140 games), so their scores move by ±20-30 points between
runs and are shown without intervals:

| Faction | Target | Baseline | P1 | P2 | Final | Met |
|---|---|---:|---:|---:|---:|---|
| China | vs modern 35-65% | 21% (13-32) | 19% | 23% | 37% (27-48) | yes |
| Iran | vs modern 35-65% | 53% (42-65) | 71% | 50% | 56% (45-67) | yes |
| Türkiye | vs modern 35-65% | 38% (27-49) | 35% | 33% | 41% (30-53) | yes |
| Saudi Arabia | vs modern 35-65% | 55% (43-66) | 42% | 60% | 44% (34-56) | yes |
| Yemen | vs modern 35-65% | 79% (68-87) | 60% | 71% | 67% (56-77) | **no** |
| Israel | vs modern 35-65% | 35% (25-46) | 58% | 46% | 42% (32-54) | yes |
| Hezbollah | vs modern 35-65% | 69% (58-79) | 65% | 67% | 62% (50-72) | yes |
| China | vs America+Russia ≥35% | 21% (9-40) | 44% | 62% | 33% (18-53) | **no** |
| Iran | vs America+Russia ≥35% | 33% (18-53) | 44% | 44% | 40% (23-59) | yes |
| Türkiye | vs America+Russia ≥35% | 25% (12-45) | 31% | 19% | 46% (28-65) | yes |
| Saudi Arabia | vs America+Russia ≥35% | 52% (33-70) | 38% | 56% | 65% (45-80) | yes |
| Yemen | vs America+Russia ≥35% | 46% (28-65) | 38% | 88% | 42% (24-61) | yes |
| Israel | vs America+Russia ≥35% | 31% (16-51) | 44% | 31% | 54% (35-72) | yes |
| Hezbollah | vs America+Russia ≥35% | 35% (20-55) | 69% | 44% | 54% (35-72) | yes |
| America | vs modern ≤65% | 71% (61-80) | 55% | 62% | 62% (52-72) | yes |
| Russia | vs modern ≤65% | 59% (48-69) | 57% | 39% | 42% (32-53) | yes |

**Verdict.** [ran] Three tuning rounds moved every faction that was named. China went from 21% to 37% against the
modern factions and from 21% to 33% against America and Russia; Türkiye from 38% to 41% and from 25% to 46%; Iran from
33% to 40% against the originals; Israel from 35% to 42% and from 31% to 54%. America fell from 71% (61-80) to 62%
(52-72) against the modern factions without any change to its rules. Fourteen of the sixteen targets are met at the
point estimate. Two are missed narrowly, both inside their own intervals:

- Yemen scores 67% (56-77) against the modern factions (baseline 79%).
- China scores 33% (18-53) against America and Russia (baseline 21%).

Tuning stopped after three rounds, as asked. Both misses have a cause the numbers here do not remove. They are
described under "Round 3: what numbers did not fix".

Naval map, Little Big Lake [ran], reported separately and not tuned for. Each run is 6 games per pairing, 210 games.
Before: rules 243c138, 0 errors, 68 draws. After: the final rules, 51 draws, 0 errors after the replay described below.
Score (95% Wilson interval):

| Faction | Before: vs modern | Before: vs America+Russia | After: vs modern | After: vs America+Russia |
|---|---:|---:|---:|---:|
| China | 28% (16-44) | 29% (11-57) | 38% (24-54) | 38% (16-65) |
| Iran | 57% (41-72) | 46% (22-71) | 49% (33-64) | 50% (25-75) |
| Türkiye | 44% (30-60) | 33% (14-61) | 40% (26-56) | 46% (22-71) |
| Saudi Arabia | 56% (40-70) | 54% (29-78) | 47% (32-63) | 50% (25-75) |
| Yemen | 61% (45-75) | 46% (22-71) | 64% (48-78) | 58% (32-81) |
| Israel | 49% (33-64) | 54% (29-78) | 43% (28-59) | 71% (43-89) |
| Hezbollah | 56% (40-70) | 21% (7-49) | 69% (53-82) | 50% (25-75) |
| America | 58% (43-72) | — | 46% (32-61) | — |
| Russia | 61% (46-74) | — | 50% (36-64) | — |

On the naval map the band is met more fully after round 3 than before.
- Before, China was at 28% against the modern factions and Hezbollah at 21% against the originals.
- After, every modern faction scores at least 38% against America and Russia.
- Against each other, all seven modern factions are within 35-65% except Hezbollah, at 69% (53-82).
- America scores 46% and Russia 50% against the modern factions.

Round 2's naval figures (five modern factions, older engine and art) are not comparable.

**Engine crash found and fixed.** [ran] 2 of the 210 games in the after run crashed: yemen-hezbollah r0 and
iran-yemen r1.
- The error was `System.DivideByZeroException` in `WRot.SLerp`.
- The engine owner traced it to one Little Big Lake cell, where a full-tile slope lies next to a half-ramp sloped
  about the same axis. A vehicle tilting between them (Hezbollah's rocket truck in one game, Yemen's missile launcher
  in the other) made `SLerp` blend two rotations one angle step apart. Integer truncation zeroed both weights, and the
  normalisation then divided by zero.
- The fix is `rtsai/engine` 68c1e95557, preview pin 8c74dd4. It changes the result for no other input, so the other
  games stand. It is not specific to the naval map: any ramp pair of that shape can trigger it, though the 1,120 land
  games here did not.
- The two crashed games were voided and replayed on 68c1e95557. The table counts all 210.

## Round 3: method

- **What was measured.** Branch `rtsai/art-preview`: the new faction art and the art agents' muzzle offsets, with the
  local engine `rtsai/engine` 265db7a4a7. That engine has two Missile fixes. ae14ce6b01 makes missiles fired over
  raised ground hit. 265db7a4a7 keeps low-cruise missiles clear of ramps, which fixed misses by the Yemen and
  Hezbollah RPGs, the Iran Toophan and the coastal launchers. The engine was re-pinned to 265db7a4a7 while the first
  baseline was running. That baseline was discarded and the whole baseline was replayed on the new engine.
  Round 3 found a crash in that engine (`WRot.SLerp`, see the naval section). It was fixed in 68c1e95557, which
  changes no other result. The two crashed naval games were replayed on it.
- **Factions and design.** The seven modern factions (now including the local Israel and Hezbollah packs) plus America
  and Russia. Every pairing with a modern faction was played (35 pairings; America-Russia was not played). Each was
  played from both spawn orientations on both maps with 3 replicates: 12 games per pairing as in round 2, 420 games per
  round robin. The naval map, Little Big Lake, used 6 games per pairing (210 games). Bots: `normal` on both sides,
  40-minute cap, same harness and telemetry as round 2. Campaign definitions: `docs/balance-data/r3-campaigns.json`.
- **Frozen rules per run.** Other agents committed art while round 3 ran. Each run therefore used a `git archive`
  snapshot of `mods/`, plus the candidate's rule edits, and a private copy of the built engine. Commits and engine
  rebuilds during a run could not change it.
  - Baseline: rules 243c138.
  - P1, P2: 243c138 + the candidate changes.
  - Final: e15542b + the round-3 changes. a47654a commits the same changes on top of later art-only commits.
  - Between 243c138 and e15542b, and up to a47654a, only art-preview overlay files (sprite installs, muzzle offsets)
    and audio changed. The coordinator classed these as non-material. They were not measured separately.
- **Execution.** `OPENRA_AI_HOST=0`, 3 games at a time. The game processes ran at Normal priority: at the shared
  BelowNormal priority, concurrent Blender renders held each game to about 0.1 core. Priority changes only the speed,
  not the simulation.
- **Disk incident.** The disk filled up briefly (not from this harness). 9 final games were recorded as errors and
  were replayed; no counted game was affected.
- **Reading probes.** A one-replicate probe gives each faction 24 games against the modern factions and 8 against the
  originals. Its score intervals are about ±20 and ±30 points. Probes were therefore read mainly through per-unit
  trade (enemy value destroyed per credit produced), which moves much less between runs. The full round robin
  confirms.

## Round 3: why China and Türkiye lost (baseline)

[ran] Baseline round robin, 420 games, 0 errors, 90 draws, median 26.1 min:

| vs | china | iran | turkey | saudi | yemen | israel | hezbollah | america | russia | vs modern | vs America+Russia |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **china** | — | 1-9 (2d) | 2-9 (1d) | 2-8 (2d) | 1-11 | 3-3 (6d) | 0-11 (1d) | 1-8 (3d) | 2-9 (1d) | 21% (13-32) | 21% (9-40) |
| **iran** | 9-1 (2d) | — | 6-2 (4d) | 4-3 (5d) | 1-8 (3d) | 5-4 (3d) | 4-6 (2d) | 2-9 (1d) | 4-5 (3d) | 53% (42-65) | 33% (18-53) |
| **turkey** | 9-2 (1d) | 2-6 (4d) | — | 2-5 (5d) | 0-11 (1d) | 6-4 (2d) | 1-10 (1d) | 1-6 (5d) | 0-7 (5d) | 38% (27-49) | 25% (12-45) |
| **saudi** | 8-2 (2d) | 3-4 (5d) | 5-2 (5d) | — | 3-6 (3d) | 9-1 (2d) | 3-9 | 2-6 (4d) | 8-3 (1d) | 55% (43-66) | 52% (33-70) |
| **yemen** | 11-1 | 8-1 (3d) | 11-0 (1d) | 6-3 (3d) | — | 10-0 (2d) | 5-4 (3d) | 4-7 (1d) | 4-3 (5d) | 79% (68-87) | 46% (28-65) |
| **israel** | 3-3 (6d) | 4-5 (3d) | 4-6 (2d) | 1-9 (2d) | 0-10 (2d) | — | 4-5 (3d) | 3-7 (2d) | 3-8 (1d) | 35% (25-46) | 31% (16-51) |
| **hezbollah** | 11-0 (1d) | 6-4 (2d) | 10-1 (1d) | 9-3 | 4-5 (3d) | 5-4 (3d) | — | 2-8 (2d) | 3-4 (5d) | 69% (58-79) | 35% (20-55) |
| **america** | 8-1 (3d) | 9-2 (1d) | 6-1 (5d) | 6-2 (4d) | 7-4 (1d) | 7-3 (2d) | 8-2 (2d) | — | — | 71% (61-80) | — |
| **russia** | 9-2 (1d) | 5-4 (3d) | 7-0 (5d) | 3-8 (1d) | 3-4 (5d) | 8-3 (1d) | 4-3 (5d) | — | — | 59% (48-69) | — |

[ran] figures from that run unless marked:

1. **Not the economy.** By 10 minutes China and Türkiye had each earned 22.3k credits with 2.1-2.2 refineries. Iran,
   Yemen and Hezbollah had earned 20.3-20.8k, America 23.5k.
2. **The smallest standing armies.** Army value at 5 and 10 minutes:
   - China 2.6k and 3.1k, Türkiye 2.5k and 3.1k;
   - Iran 4.5k and 6.0k, Yemen 4.8k and 5.9k, Hezbollah 4.5k and 6.2k.

   In the first 10 minutes China and Türkiye traded about even (7.4k and 7.3k destroyed for 7.8k and 7.7k lost), while
   Yemen and Hezbollah destroyed 9.6-9.7k for 7.2-7.7k lost. China and Türkiye also put 0.9-2.0k more into buildings
   (Air Force Command, Türkiye's early service depot, AA sites and tech). Their mean time to the first enemy building
   destroyed was 22 minutes, counting games with none as 40. Hezbollah's was 10 and Yemen's 11.
3. **Low-value spending.** Share of production and enemy value destroyed per credit:

   | Faction | Unit | Share | Destroyed / credit |
   |---|---|---:|---:|
   | China | Qilin (MBT) | 19.3% | 0.75 |
   | China | PHL (rocket artillery) | 14.3% | 0.47 |
   | China | Red Spear (commando) | 8.0% | 0.77 |
   | China | Cloud (armed drone) | 6.5% | 0.38 |
   | China | Mantis (air-only AA) | 4.5% | 0.27 |
   | China | Rifleman | 10.0% | 1.67 |
   | Türkiye | Bozkır (MBT) | 27.1% | 0.65 |
   | Türkiye | Grey Wolf (commando) | 7.6% | 0.85 |
   | Türkiye | Sancak, Aras, Kuzgun | 8.6% | 0.23-0.35 |
   | Türkiye | Rifleman | 8.6% | 1.64 |
   | Iran | Toophan (ATGM team) | 33.8% | 0.84 |
   | Iran | Basij | 11.7% | 1.68 |
   | Israel | Merkava (MBT) | 30.8% | 0.63 |
   | Yemen, Hezbollah | Rifleman | 12.8%, 16.1% | 1.93, 1.79 |
   | Saudi, Iran, Russia | M1A2S, Karrar, Rhino | 24.3%, 17.5%, 12.6% | 0.80, 0.76, 1.17 |

   Riflemen were the most cost-effective unit of China, Türkiye, Iran, Yemen and Hezbollah (1.6-1.9 destroyed per
   credit; most MBTs 0.6-0.8). China and Türkiye fielded the fewest of them.
4. **Unit-stat causes** [inferred from the rules; the probes then confirmed the per-unit effect]:
   - Qilin and Bozkır fire the 105mm base, range 5c0. They are outranged by every modern ATGM team (6c-8c), the Rhino's
     and Karrar's 120mm (5c768) and the M1A2S/Merkava gun (6c).
   - The Bozkır costs as much as the Rhino and has the same HP (900 credits, 400 HP), but it dealt 80 damage every 70
     ticks against the Rhino's 90 every 65.
   - The China and Türkiye portable ATGMs dealt about 1.6 heavy-armour damage per tick per 1,000 credits at 6c. The
     Saudi and Israeli ATGM deals 2.4 at 8c, and those teams destroyed 1.36-1.41 per credit against 0.90-0.94.
   - The PHL rockets had Inaccuracy 1c0 and did 60% against heavy armour.
   - `R2DroneMissile` did 35 damage every 140 ticks for a 1,000-credit drone (Cloud, Kuzgun, Mohajer). That is a
     quarter of a Qilin's damage rate at 1.4 times its cost.
5. **Bot doctrine.** China and Türkiye were the only modern factions without the 20-minute bot delay on their
   commando.

Other findings:
- **Israel.** [ran] `bot-types.yaml` never listed Israel's or Hezbollah's aircraft, ships and defenses (the Levant
  packs were added after the port tool built the lists), so their jets and boats joined the ground squads. Israel's
  Merkava had the same gun as the 1,100-credit M1A2S, 23% more HP, and cost 1,450.
- **Yemen and Hezbollah** (79% and 69% against the modern factions). Their riflemen, at 135 credits, were the most
  cost-effective units in the game (1.93 and 1.79 destroyed per credit).
- **America** (71%). [ran] Against the modern factions its GIs made 22% of its kills at 1.94 destroyed per credit. This
  includes the free paratroopers, whose cost is not counted. Rocketeers made 12% (1.43) and Prism tanks 10% (1.48). The
  Chrono Legionnaire was 11% of America's production but records no kills, because erased units are not reported as
  killed. No America change was needed in the end. Its score fell as the modern factions improved.

## Round 3: changes

All changes are in a47654a. P1 and P2 are the probes; "final" is the final round robin. The last column gives enemy
value destroyed per credit produced, baseline → final, for the unit changed.

| # | Change | Reason | In | Destroyed / credit |
|---|---|---|---|---|
| 1 | `bot-types.yaml`: Israel's and Hezbollah's aircraft (`AirUnitsTypes`), ships (`NavalUnitsTypes`) and defenses (`DefenseTypes`) added to all five bot profiles | Bug: Levant units missing from the bot type lists | P1 | Israel's jet 0.20 → 0.28 (P1 0.62) |
| 2 | Bots train China's Red Spear and Türkiye's Grey Wolf only after 20 minutes (`UnitDelays` 30000), as the other five commandos | Commandos 8% of production at 0.77-0.85 | P1 | share 8.0 → 5.9%, 7.6 → 5.4% |
| 3 | China line infantry 100 → 140, Türkiye 100 → 130 (`RoleShareModifiers`) | Riflemen China's and Türkiye's most cost-effective unit (1.67, 1.64 per credit) | P1 | rifle share 10.0 → 12.6%, 8.6 → 11.0% |
| 4 | PHL rockets: Inaccuracy 1c0 → 0c512; 80% against heavy and 90% against medium armour (were 60/75) | 14% of China's production at 0.47 | P1 | 0.47 → 0.78 |
| 5 | `R2DroneMissile` damage 35 → 60 (Cloud, Kuzgun, Mohajer) | 1,000-credit drones at 0.30-0.38 | P1 | Cloud 0.38 → 0.66, Kuzgun 0.30 → 0.38 |
| 6 | Bozkır gun reload 70 → 60 | Rhino damage per credit at the Rhino's cost | P1 | 0.65 → 0.64 alone (P1) |
| 7 | Merkava 1,450 → 1,250 credits | Same gun as the 1,100 M1A2S | P1 | 0.63 → 0.75 |
| 8 | Hezbollah rifleman 135 → 150 credits | 69% against the modern factions; 1.79 per credit | P1 | 1.79 → 1.66 |
| 9 | Qilin and Bozkır guns: range 5c0 → 5c768, the reach of the Rhino's and Karrar's 120mm | Outranged by every ATGM team | P2 | Qilin 0.75 → 0.77, Bozkır 0.65 → 0.82 (P2 0.86) |
| 10 | China anti-air share 40 → 25 | Mantis 0.27 per credit | P2 | Mantis share 4.5 → 3.1% |
| 11 | China portable ATGM: damage 65 → 80, range 6c → 7c | 1.6 vs 2.4 damage per tick per 1,000 credits for the Saudi ATGM | final | 0.90 → 1.22 |
| 12 | Türkiye portable ATGM: damage 60 → 75, range 6c → 7c | as 11 | final | 0.94 → 1.22 |
| 13 | Türkiye support share 130 → 100 | Sancak 0.23 per credit | final | Sancak share 3.4 → 3.7% (unchanged) |
| 14 | Yemeni Mountain Rifleman 135 → 150 credits | Yemen 79% against the modern factions; same step as its Hezbollah twin (8) | final | 1.93 → 1.85 |
| 15 | Iran line infantry 100 → 120, anti-armor 110 → 100 | Basij 1.68 per credit, Toophan 0.84; Iran 33% against the originals | final | Basij share 11.7 → 14.8% |

Each change answers a measured cause; none is a blanket cost cut. Weak units were made worth their cost. Where the bot
misuses a unit (commandos, Mantis, Sancak), the bot now buys fewer of them. Yemen and Hezbollah were trimmed one cost
step each because their scores were above the band. America's and Russia's rules are unchanged.

The three rounds [ran]:
- **P1** (changes 1-8). The changed units moved as intended: PHL 0.47 → 0.87, Cloud 0.38 → 0.69, Israel's jet
  0.20 → 0.62, Merkava 0.63 → 0.79. China (19%) and Türkiye (35%) still trailed the other modern factions, and the
  Bozkır reload alone did not change the Bozkır's value (0.65 → 0.64).
- **P2** (+ 9-10). The longer range raised the Qilin to 0.81 and the Bozkır to 0.86 per credit. Pooled over P1 and
  P2 (48 games each), China scored 53% against America and Russia but 21% against the modern factions: 0-8 against
  Yemen, 0-6 against Saudi Arabia and Hezbollah. Its tanks still met ATGM teams that outranged and outdamaged its own.
  This pointed to change 11.
- **Final** (+ 11-15), the full round robin above. Changes 11-15 were not probed separately.

## Round 3: what numbers did not fix

- **Yemen against the modern factions (67%).** [ran] The modern doctrines put half their production into vehicles
  (China 50%, Türkiye 52%, Saudi Arabia and Israel 50%, Iran 46%). Yemen's army of RPG teams, recoilless trucks and
  cheap riflemen is built to kill vehicles: its RPG teams were 26% of its production. The same army scores only 42%
  against America and Russia, which field more infantry. [inferred] A rock-paper-scissors effect of the doctrines, not
  of one unit. Another cost step on Yemen would take its score against the originals towards 35%. Moving the other
  modern doctrines away from vehicles would change their identity.
- **Free units by side.** [ran] The Soviet-side factions (Iran, Yemen, Hezbollah, Russia) build the stock Cloning Vats,
  and their cloned infantry was 10-12% of the unit value they fielded. The Allied-side modern factions (China,
  Türkiye, Saudi Arabia, Israel) have no equivalent. America has its paratroopers. This side asymmetry comes from
  stock RA2 and was left alone. It favors the infantry-heavy Soviet-side factions.
- **China against the originals (33%).** [ran] China lost to America 1-7 (4 draws) and to Russia 3-5 (4 draws). Its
  army is still half vehicles, which meet America's GIs, rocketeers and Prism tanks and Russia's Tesla coils.
  Interval 18-53.
Round 4 fixed the next two items in the bot ("Round 4: the bot spending fix").

- **Airfield jets.** [inferred from `DoctrineUnitBuilderBotModule`] The bot gives each production queue a turn, and
  in the Plane queue the jet is the only unit of its role, so a faction with an airfield keeps building jets up to its
  unit limit. Role shares cannot lower that; only unit limits can. [ran] Saudi Arabia's F-15 was 12% of its production
  at 0.32 destroyed per credit, Israel's jet 11.5% at 0.28 and America's Harrier 11.5% at 0.42.
- **Ships on land maps.** [ran] Every faction builds a shipyard when its base has water, and ships were 7-13% of
  production on Dustbowl and Tournament Map A (China 13%, Türkiye 11%), mostly destroying nothing. This is the
  upstream base builder.
- **Russia** fell from 59% to 42% against the modern factions with no change to its rules, because the modern factions
  improved. Russia is a reference, not a target.
- **Not measured:** human play, other bot profiles, team games, kills by chrono erasure. Unit values were read from the
  bot games; no duels were run in round 3.

## Round 2 result (2026-10-03)

Branch `rtsai/balance` (local, not pushed), final rules at 31912c4, engine `rtsai/engine` 5523a9907f.

[ran] Final round robin: 252 games on Dustbowl and Official Tournament Map A, 0 errors, 67 tick-cap draws, median
26.7 game minutes. Row's wins-losses (draws) against the column:

| vs | china | iran | turkey | saudi | yemen | america | russia | Score |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **china** | — | 6-4 (2d) | 1-7 (4d) | 2-7 (3d) | 4-6 (2d) | 1-6 (5d) | 0-8 (4d) | 33% |
| **iran** | 4-6 (2d) | — | 8-2 (2d) | 3-5 (4d) | 4-6 (2d) | 3-5 (4d) | 0-6 (6d) | 44% |
| **turkey** | 7-1 (4d) | 2-8 (2d) | — | 2-6 (4d) | 2-6 (4d) | 1-9 (2d) | 1-7 (4d) | 35% |
| **saudi** | 7-2 (3d) | 5-3 (4d) | 6-2 (4d) | — | 6-5 (1d) | 3-7 (2d) | 6-4 (2d) | 57% |
| **yemen** | 6-4 (2d) | 6-4 (2d) | 6-2 (4d) | 5-6 (1d) | — | 2-6 (4d) | 5-3 (4d) | 54% |
| **america** | 6-1 (5d) | 5-3 (4d) | 9-1 (2d) | 7-3 (2d) | 6-2 (4d) | — | 9-1 (2d) | 72% |
| **russia** | 8-0 (4d) | 6-0 (6d) | 7-1 (4d) | 4-6 (2d) | 3-5 (4d) | 1-9 (2d) | — | 56% |

Round-2 targets, as scores (draw = half a win); the final column has 95% Wilson intervals. "Start" is the round-1
result (414f8fa, 252 games):

| Faction | Target | Start | Pass 1 (84 games) | Pass 2a (238 games) | Final (252 games) | Met |
|---|---|---:|---:|---:|---:|---|
| China | vs modern 35-65% | 43% | 44% | 29% | 39% (26-53) | yes |
| Iran | vs modern 35-65% | 44% | 50% | 56% | 50% (36-64) | yes |
| Türkiye | vs modern 35-65% | 33% | 41% | 44% | 42% (29-56) | yes |
| Saudi Arabia | vs modern 35-65% | 55% | 53% | 53% | 62% (48-75) | yes |
| Yemen | vs modern 35-65% | 75% | 62% | 66% | 57% (43-70) | yes |
| China | vs America+Russia ≥35% | 6% | 6% | 19% | 23% (11-43) | **no** |
| Iran | vs America+Russia ≥35% | 10% | 19% | 37% | 33% (18-53) | **no** (edge) |
| Türkiye | vs America+Russia ≥35% | 12% | 19% | 23% | 21% (9-40) | **no** |
| Saudi Arabia | vs America+Russia ≥35% | 8% | 56% | 30% | 46% (28-65) | yes |
| Yemen | vs America+Russia ≥35% | 23% | 44% | 30% | 46% (28-65) | yes |
| America | vs modern ≤65% | 94% | 92% | 82% | 69% (57-79) | **no** (edge) |
| Russia | vs modern ≤65% | 82% | 50% | 63% | 63% (51-74) | yes |

Pass 1 is one replicate of the round robin at eba846d. Pass 2a is the round robin at c89a76c; 238 of its games
finished before the anti-air targeting bug was found, and the 14 that would have mixed two rule sets were dropped.
The final run is at 31912c4.

**Verdict.** Two tuning passes closed most of the gap. The original countries won 96 of 101 decided games against
the modern factions at the start of round 2 and 61 of 83 now, and all five modern factions are inside 35-65% among
themselves. Four targets are still missed: China (23%), Türkiye (21%) and, narrowly, Iran (33%) against the
originals, and America (69%, interval 57-79) against the modern factions. As asked, tuning stopped after two
passes. What a third pass would take is under "Round 2: what would still be needed".

Naval map, Little Big Lake (126 games, 0 errors, 34 draws) [ran], reported separately and not tuned for: America
53% and Russia 65% against the modern factions; among the modern factions China 33% and Saudi Arabia 73% fall
outside 35-65%; against the originals China 50%, Saudi Arabia 62%, Yemen 38%, Türkiye 29% and Iran 25%.

## What this shows, and what it doesn't

The harness plays the game's own `normal` bot against itself, one faction per side. A win rate here measures
**how well the shipped bot plays each faction** on these maps, which is what a player meets in skirmish. It is
evidence about the rules only through that filter.

It shows:
- unit types the bot buys but cannot use (they destroy little per credit spent);
- with the duels (no bot), what a unit is worth for its cost against the stock RA2 equivalent;
- openings that leave a faction without an army early;
- rule bugs that stop a game from ending (one found and fixed) and crashes in long unattended games (one found, fixed in round 2).

It does not show:
- human balance. Humans micro, focus fire, scout, use abilities, garrison and pick counters; the bot does little of
  this. A unit the bot wastes can still be strong in human hands, and the reverse;
- naval balance beyond one map. The round robin uses two land maps; Little Big Lake, the only two-player naval map,
  is reported separately (round 2) and was not tuned for;
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
  (Soviet). Round 3 adds Israel and Hezbollah (see "Round 3: method").
- **Bots.** `normal` on both sides, with the mod's doctrine bot modules. The stock countries use the same modules
  without a doctrine.
- **Maps.** Two land 1v1 maps from the mod: Dustbowl (70x152) and Official Tournament Map A (87x134), both temperate.
  [inferred] Short game is on (the upstream lobby default), so a player loses with their last building.
- **Design** (rounds 1-2). All 21 pairings, each from both spawn orientations on both maps, 3 replicates: 12 games per pairing,
  72 per faction, 252 per round robin. Order is shuffled with a fixed seed. The engine seeds its RNGs from the
  clock, so replicates are independent samples, not reruns. Launches are spaced 0.5 s apart because two
  simultaneous starts were seen to share a seed; no run below has a duplicate seed.
- **Cap.** 40 game minutes (60000 ticks). At the cap the script fails both players' objectives on the same tick, so
  the game ends as a recorded draw with a complete replay.
- **Statistics.** Score = (wins + ½ draws) / games. Win rate = wins / games. Intervals are 95% Wilson intervals.
  The tuning target (35-65% for each modern faction) is applied to the **score**. With a fifth of games drawn, the
  strict win rate sits about 10 points lower for every faction, so both are reported.
- **Duels** [ran] (round 2): `tools/balance-duel.py` measures unit value without any bot. On a copy of the flat blank
  map, two non-playable players get groups of equal build value (the counts whose totals differ least, within 4%)
  and attack-move through each other; the value left on each side is recorded. 8 duels per pair, side A alternating
  between start lines, successive duels on separate fields, rank 0 and elite (rank 2). Each modern unit is compared
  with its own side's stock unit, because the stock sides differ: the Conscript beats the GI 8-0 and the Rhino
  beats the Grizzly at equal cost. Near parity a pair flips by about 3 of 8 between runs, so costs are set to within
  a cost step, not closer.
- **Naval map** (round 2): the same design on Little Big Lake, 3 replicates (126 games), reported separately.
- **Probes.** A probe is one replicate (84 games, 24 per faction) with a rules overlay. At that size a faction's
  interval is about ±19 points, so probes screen candidates; only full round robins confirm.

## Round 2: why the original countries won

The question was whether the bot plays the modern rosters badly or the modern units are worth less. The answer is
**both, with unit value and two rule bugs first**. Numbers are on the round-1 rules (414f8fa) unless stated.

1. **Unit value** [ran]. Equal-value duels against the same side's stock unit, rank 0, 8 duels each (modern wins
   first):

   | Unit (cost before → after) | Against | Before | After |
   |---|---|---:|---:|
   | Qilin (750 → 700) | Grizzly | 0-8 | 7-1 |
   | Bozkır (950 → 900) | Grizzly | 4-4 | 4-4 |
   | M1A2S (1250 → 1100) | Grizzly | 0-8 | 5-3 |
   | Karrar (900 → 850) | Rhino | 0-8 | 7-1 |
   | China rifleman (150 → 170) | GI | 5-3 | 7-1 |
   | Saudi National Guard (220) | GI | 0-8 | 4-4 |
   | Türkiye rifleman (200 → 155) | GI | 0-8 | 7-1 |
   | Basij (100 → 90) | Conscript | 0-8 | 4-4 |
   | Yemeni Mountain Rifleman (100 → 135) | Conscript | 8-0 | 5-3 |
   | All nine | | 17 of 72 | 50 of 72 |

   "After" includes the prone fix below, which shifted every rifleman pairing. Elite against elite, the modern MBTs
   won 0 of 64 duels before and 47 of 64 after. Anti-tank infantry were already worth their cost (every type beats
   the Rhino 8-0 at rank 0, like the Tesla trooper).
2. **A prone asymmetry** [ran]. The modern infantry had TakeCover removed (no prone art), but their rifles inherit the
   stock M60 or M1Carbine and their tank guns the stock 105mm or 120mm. Those damage types make RA2 infantry go prone
   and take 70% or 50% damage; stock fire on modern infantry always did 100%.
3. **Modern air defense never fired at aircraft** [ran]. Every modern AA vehicle and AA defense resolved to an
   auto-target priority that, in the default stance and while attack-moving, listed only ground targets: the ground
   and air auto-target templates merged badly (`--resolved-rules r2gokkalkan` shows it). In duels the Mantis, Raad,
   Gökkalkan and SADS did no damage at all to rocketeers, Harriers, Nighthawks or a Kirov (0-8, 100% left), while
   the stock flak track beat rocketeers 8-0. This is why their trade figures were 0.02-0.08 in round 1. America's air
   (rocketeers, Harriers, Nighthawks, carrier drones) made 37% of its kills against the modern factions; rocketeers
   alone made 23%.
4. **Economy: the openings** [ran]. Every doctrine opening put its support buildings before a second refinery. In an
   84-game probe at 10 minutes, America had 2.5 refineries and had earned 22.5k credits; the modern bots had 1.3-1.8
   refineries and 11.3-14.3k. Final: America 2.3 and 20.6k, the modern bots 2.0-2.2 and 15.7-18.5k (Russia 1.2 and
   10.7k).
5. **Bot composition** [ran]. Infantry/vehicle splits were similar for all seven factions. The remaining waste was in
   specific units: Türkiye's air-only AA was 16% of its first 10 minutes of production, and Iran still put 9.6% into
   the Shadow One. Veterancy mattered little to the bots: averaged over 5-minute spans, at most 4% of any army's value was
   elite, so the missing elite weapons matter mainly for human play.

## Round 2: changes

| Commit | Change | Kind |
|---|---|---|
| a0ebf1e, 1e0a5e0 | `tools/balance-duel.py` (+ `.lua`) unit-value duels; veterancy telemetry; `naval` campaign | Tools |
| f3b0e84 | Crash fix: animals map PsychicDeath to `die1`. A Crazy Ivan bomb killing a cow had crashed the game. Verified headless: 24 animals killed by every effect damage type without an exception; the same test crashed before | Content bug |
| c2e9b8f | Modern infantry get TakeCover back with an empty prone prefix (mechanics, no art). Modern units get FirepowerMultiplier 140 at elite rank, standing in for the stock elite weapon swaps (+25-67% damage) | Mechanics parity |
| a8c91d5 | `^AutoTargetAir` also defines `@ATTACKANYTHING` with Air, so the modern AA targets aircraft. Stock air-only actors are unchanged (a duplicate priority) | Rule bug |
| 97154a3, 31912c4 | Core unit costs set by duels (table above). The first calibration (97154a3) used a duel harness with a start-line bias; 31912c4 redoes it after the fix in 1e0a5e0 | Unit costs |
| ddfc241 | Mantis, Raad and Gökkalkan reload ×0.5, SADS ×0.35. These are unit-level: the shared missile weapon, and the sites, ships and jets that use it, are unchanged. Against rocketeers: 0-8 before, 7-1 to 8-0 after | Unit stats |
| eba846d | Count-aware `InitialBuildOrder` (a building listed twice is wanted twice). Every doctrine opening takes a second refinery right after the factory. Türkiye anti-air 40 → 20. Iran's bot never trains the Shadow One | Bot logic |
| c89a76c | Anti-air response: while visible enemy aircraft outvalue the bot's own anti-air units, the doctrine raises the anti-air share to 24 (`BotDoctrine.AirDefenseShare`) | Bot logic |

Commit messages before 1e0a5e0 quote duel results from the biased harness. The duel tables in this report all
come from the fixed harness.

## Round 2: what would still be needed

Round 3 acted on the first two items (China's and Türkiye's spending, America); see the round-3 sections.
[inferred] from the final run's figures:

- **China and Türkiye against the originals (23% and 21%).** Their armies still carry the most low-value spending.
  China's PHL artillery is 13% of production at 0.53 destroyed per credit, its Cloud drone 7% at 0.33, and its submarine and
  carrier about 5% at near 0 on land maps. Türkiye's anti-tank teams are 15% at 0.63, and the Sancak, Kuzgun and Aras
  together about 9% at 0.31-0.33. Both factions' commandos (Red Spear, Grey Wolf) are about 8% at 0.72-0.78. A third
  pass would cut these from the bots' mix. It would also make the bot's naval production depend on the map: every
  faction, stock included, builds shipyards and ships on land maps. That is doctrine work, not a redesign, but it was
  not run.
- **America (69%).** Its remaining edge is its GIs (24% of its kills, including the free paratroopers), rocketeers
  (14%), the Prism Tower (9%), Hornet carrier drones (7%) and Prism tanks (6%). The stock rules were left alone as the
  reference. Getting America below 65% without touching them needs the modern bots to fight better, for example by
  attacking before America's air and Prism units arrive. That is bot-behaviour work beyond doctrine weights.
- **Naval map.** Not tuned: Saudi Arabia (73%) and China (33%) are outside the band among the modern factions.
- **Duel resolution.** Duels near parity flip by about 3 of 8 between runs. Several modern core units now win their
  duels 5-3 to 7-1 (Qilin, Karrar, M1A2S, China and Türkiye riflemen), so they may be slightly over-valued against
  the stock units. That is within about one cost step.

## Round 1 (2 October)

The first round, kept as the record of how the round-1 rules were reached. Commit hashes are round-1 commits.

### Pilot: 30-minute cap

[ran] The first round robin (252 games, rules at 01adb19) used a 30-minute cap. 112 of 251 completed games (45%)
hit the cap, 76 of 126 on Dustbowl. In 58 of those, one side fielded at least three times the other's army and
still had not finished. Every later run uses 40 minutes. The pilot also found:

- **A game that could not end.** [ran] Yemen's Mountain Bunker and Coastal Missile Battery cloak until they fire or
  take damage, and cannot fire without power. A beaten Yemen base with no power plant was invisible and harmless
  forever: at least five pilot draws ended with a dominant opponent (up to 78k army value) facing only these
  structures. Fixed in 846ad3c (the cloak also needs power now).
- **A crash.** [ran] 1 of 252 games: `Image cow does not have a sequence named die5`, after a Crazy Ivan bomb
  (`IvanBomber`, `PsychicDeath`) killed a cow. [inferred] `^Animal` overrides `WithDeathAnimation@effect` but the
  merge keeps the infantry's `PsychicDeath: 5`, and the cow has only `die1`/`die2`. Inherited RA2 content; not fixed in
  round 1, fixed in round 2 (f3b0e84).

### Before: rules at 01adb19

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

### Diagnosis

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

### Tuning steps

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

### Changes made

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

### After: rules at 414f8fa

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

### Round 1 caveats (superseded where round 2 addresses them)

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
- **Not fixed in round 1:** the `cow`/`die5` crash (fixed in round 2). Kill credit seems to be missing for chrono erasure and mind
  control, so those units read zero in the per-unit table.
- **Reproducibility.** The engine has no launch seed, so a match cannot be replayed from the campaign seed; each
  match's replay and engine seed are kept in the run directory (not in the repo).

## Data

All files are in `docs/balance-data/`. Each `*.csv` has one row per match:
- map, the factions and spawns per slot;
- result, winner, end reason, end tick, game minutes, wall seconds and engine seed;
- per side: units produced (count, value, by type), structures placed, value destroyed and value lost.

Each `*-summary.json` holds the aggregates: matrix, per-faction W-D-L, Wilson intervals, lengths, draws and per-unit
trade. The `r2-duels-*.csv` files have one row per duel: pair, level, replicate, ticks, and each side's value and
value left.

| Files | Run | Rules |
|---|---|---|
| `r3-baseline`, `r3-baseline-naval` | Round 3: baseline round robin (420) and naval (210) | 243c138 |
| `r3-p1`, `r3-p2` | Round 3: probes, one replicate (140 each) | 243c138 + changes 1-8, 1-10 |
| `r3-final`, `r3-final-naval` | Round 3: final round robin (420) and naval (210) | e15542b + changes 1-15 (= a47654a) |
| `r3-campaigns.json` | Round 3 campaign definitions (`--campaigns-file`) | — |
| `r4-baseline`, `r4-baseline-naval` | Round 4: round robin (420) and naval (210) after the bot spending fix | a47654a + changes 16-17 |
| `r4-p1` | Round 4: probe, one replicate (140) | + changes 18-21 |
| `r4-final`, `r4-final-naval` | Round 4: final round robin (420) and naval (210) | e2c07b0 |
| `r4-campaigns.json` | Round 4 campaign definitions | — |
| `r5-hz-probe`, `r5-hz-designed` | Round 5: Hezbollah probe (32) and stopped land run (42), as designed | 2ed217e |
| `r5-hz-probe-t1` | Round 5: probe with the trim-1 rules overlay (32) | 2ed217e + overlay |
| `r5-hz-t2`, `r5-hz-t3`, `r5-hz-t4` | Round 5: land runs after trims 1-2 (96), 3 (47 of 96, stopped) and 4 (96) | b70d61e, efe7750, 85d07d4 |
| `r5-hz-t5`, `r5-hz-t5-naval` | Round 5: land (96) and naval (48), as built | d646808 |
| `r5-hz-campaigns.json` | Round 5 campaign definitions (Hezbollah focus) | — |
| `r5-sa-baseline` | Round 5, standalone: baseline round robin (252) | `rtsai/standalone` e2efdd2 |
| `r5-sa-p1` | Round 5, standalone: probe 1, one replicate (84) | e2efdd2 + probe-1 changes |
| `r5-sa-p2` | Round 5, standalone: probe 2, one replicate (84) | + the coax on the other three MBTs |
| `r5-sa-tf` | Round 5, standalone: Twin Fords only, central crossing (84; 1 host-side socket error) | probe-2 rules + 68a7e75 map |
| `r5-sa-final` | Round 5, standalone: final round robin (252) | 841e844 + the 7fd8f3f rules |
| `r5-main-p2` | Round 5, `main`: probe 2, one replicate (140) | 8357c9b + the bot port + probe-2 rules |
| `r5-main-final`, `r5-main-final-naval` | Round 5, `main`: final round robin (420) and naval (210) | 7fd8f3f |
| `r5-campaigns.json` | Round 5 campaign definitions (`r5-main-*`; `r5-sa-*` run with `--standalone`) | — |
| `r6-sa-p1`, `r6-sa-p2` | Round 6, standalone: probes (128 each: round robin + Hezbollah/Israel replicate) | 1a14e6b rules + changes 1-5; + 6 |
| `r6-sa-final` | Round 6, standalone: final round robin (252) | 841e844 maps + the ab878b8 rules |
| `r6-main-p1`, `r6-main-p2` | Round 6, `main`: probes (200 each: round robin + Hezbollah/Israel replicate) | b8ed157 rules + changes 1-5; + 6 |
| `r6-main-final`, `r6-main-final-naval` | Round 6, `main`: final round robin (420) and naval (210) | ab878b8 |
| `r6-campaigns.json` | Round 6 campaign definitions (`r6-main-*`; `r6-sa-*` run with `--standalone`) | — |
| `r2-duels-before`, `r2-duels-after` | Duels, rank 0 and 2, 8 per pair | 414f8fa / 31912c4 |
| `r2-start-probe` | Probe (84 games) with veterancy telemetry | 414f8fa |
| `r2-pass1` | Round robin, replicate 0 (84 games) | eba846d |
| `r2-pass2`, `r2-pass2-naval` | Round robin (238 of 252) and naval (126) | c89a76c |
| `r2-after`, `r2-after-naval` | Final round robin (252) and naval (126) | 31912c4 |
| `pilot-30min` | Round 1: round robin, 30-minute cap | 01adb19 |
| `before` | Round 1: round robin | 01adb19 |
| `probe-p1-aa` … `probe-p4-china-turkey-costs`, `probe-overlays.json` | Round 1 probes | see round 1 |
| `after-doctrine`, `after` | Round 1: round robins | 605f111, 414f8fa |

## Reproduce

```
./fetch-local-engine.sh && ./make.cmd all
# <content> holds ra2/ra2.mix and ra2/language.mix copied from an owned Red Alert 2; delete it afterwards.
python tools/balance-harness.py run --campaign round-robin --content <content> --output <scratch>/rr --parallel 8
python tools/balance-harness.py run --campaign naval --content <content> --output <scratch>/naval --parallel 8
python tools/balance-duel.py run --content <content> --output <scratch>/duels --parallel 8
python tools/balance-harness.py run --campaign <probe> --campaigns-file docs/balance-data/probe-overlays.json \
    --content <content> --output <scratch>/<probe>
python tools/balance-harness.py report --campaign round-robin --output <scratch>/rr   # rebuild the summary
python tools/test_balance_harness.py                                                    # harness unit tests
# Rounds 3-4 (art preview, local engine): 9 factions, 420 land games, 210 naval; round 4 uses r4-campaigns.json
# (r4-final, r4-final-naval) and needs the bot code of e2c07b0 built (make.cmd all)
python tools/balance-harness.py run --campaign r3-round-robin --campaigns-file docs/balance-data/r3-campaigns.json \
    --content <content> --output <scratch>/r3 --parallel 3
python tools/balance-harness.py run --campaign r3-naval --campaigns-file docs/balance-data/r3-campaigns.json \
    --content <content> --output <scratch>/r3-naval --parallel 3
# Round 5 (Hezbollah only): 96 land games, 48 naval
python tools/balance-harness.py run --campaign hz-land --campaigns-file docs/balance-data/r5-hz-campaigns.json \
    --content <content> --output <scratch>/r5-land --parallel 8
python tools/balance-harness.py run --campaign hz-naval --campaigns-file docs/balance-data/r5-hz-campaigns.json \
    --content <content> --output <scratch>/r5-naval --parallel 8
# Round 5 (both products): main 420 land + 210 naval; standalone 252 (from an rtsai/standalone checkout)
python tools/balance-harness.py run --campaign r5-main-final --campaigns-file docs/balance-data/r5-campaigns.json \
    --content <content> --output <scratch>/r5-main --parallel 3
python tools/balance-harness.py run --campaign r5-main-final-naval --campaigns-file docs/balance-data/r5-campaigns.json \
    --content <content> --output <scratch>/r5-main-naval --parallel 3
python tools/balance-harness.py run --campaign r5-sa-final --campaigns-file docs/balance-data/r5-campaigns.json \
    --standalone --output <scratch>/r5-sa --parallel 3
# Round 6: the same three runs with r6-campaigns.json (r6-main-final, r6-main-final-naval, r6-sa-final)
python tools/balance-harness.py run --campaign r6-main-final --campaigns-file docs/balance-data/r6-campaigns.json \
    --content <content> --output <scratch>/r6-main --parallel 3
```

Options:
- `--bot-log` keeps each match's `bot-doctrine.log`: role shares, opening, squad size, air-defense switches and every
  build choice.
- `--keep-support` keeps the support directory.
- Each match keeps its replay, which `tools/replay-production.py` reads.
- A "before" run uses a `git archive` snapshot of the older `mods/`, passed with `--mods` (also accepted by the duel
  tool).
