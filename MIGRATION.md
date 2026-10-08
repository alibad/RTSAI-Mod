# RTS AI → OpenRA Mod SDK migration

> **Current direction, 9 October 2026:** the default game is standalone and needs no owned Red Alert/RA2 content.
> Original-content work from `rtsai/standalone` is consolidated into the canonical mod. Classic/top-down and
> isometric gameplay remain the two-mode product target; the Classic port/combined chooser are still in progress.
> Custom resources are preserved under `resources/`; see [product direction](docs/product-direction.md).
>
> **Engine pin:** `rtsai/engine` 68c1e95557 resolves on the public fork (verified 9 October). Future engine pins
> must be published before the mod that references them. A local export is also supported:
> `./fetch-local-engine.sh ../OpenRA-wt-rtsai-engine && ./make.cmd all`.
>
> The rounds below are historical evidence. Their owned-content setup and old "local-only engine" notes are not
> the current player prerequisites or publication state. This transition does not publish or deploy anything.

How each result was established: **[ran]** means a command was run and its output observed.
**[inferred]** means it was reasoned from code or config and not run.

# Round C: the art promotion (2026-10-06/07)

The owner approved the art preview ("I approve all the changes"), so it moved into `main` as the canonical modern-faction
art. Commits: `d5f2ae4` merge of `rtsai/art-preview`, `845f630` fold of the overlay into `modern-factions/art-*.yaml`,
`d28f033` removal of the superseded placeholder art (archived in RTSAI-Art `history/`), `57df33c` engine repin to
68c1e95557, `34f2480` the new `ART-PROVENANCE.json` and guards on the pre-promotion art tools. RTSAI-Art's installers
now write `main`'s canonical files (RTSAI-Art `ca917eb`); docs: [art-provenance.md](docs/art-provenance.md),
[release-notes.md](docs/release-notes.md).

## Verification on main [ran, 34f2480]

| Check | Result |
|---|---|
| `make.cmd all`, `make.cmd test` | exit 0, 0 warnings, 0 errors (Fluent references, sequences for all three tilesets, `CheckFactionAudio`) |
| `tools/art-provenance.py --check` | 307 files covered, none flagged; RTSAI-Web `sync-mod-art.mjs --check`: 304 files, 0 errors |
| RTSAI-Art `tools/hit_lab.py run` (headless) | 191/191 pass: every armament of all 7 modern factions hits its target class, every defence dies to 6 tanks, all 6 designate tests show a marked-target bonus |
| One windowed (rendered) bot match per faction, 3 min wall, Dustbowl | 7/7 ran to the end with no exception: 9-14 game minutes each, 8-14 modern unit types built per match, captures kept privately in RTSAI-Art `.cache/promotion-ingame` |
| Balance smoke: first 36 matches of `r4-final` (land) and 12 of `r4-final-naval` | 48/48 complete, 0 crashes, 0 exceptions, 0 Lua errors; 44 conquests, 4 tick-cap draws; median 25.6 (land) and 22.0 (naval) game minutes. A smoke, too small to rate factions; round 4's 630 games are the balance record and the rules are unchanged since |
| Release build (`build-release.ps1 -Version 0.2.0-alpha.2`, scratch, not published) | portable zip 203.5 -> 222.4 MB, installer 148.2 -> 163.6 MB vs 0.2.0-alpha.1. All of it is `mods/rtsai` (zipped 28.4 -> 47.3 MB, 1291 -> 1638 files); the engine, runtime and companion are unchanged. The zip ships exactly the tracked `mods/rtsai` files and no `art-preview` |

The build reused 0.2.0-alpha.1's companion payload and was not launched; first-launch acceptance is due on the real
release build.

## Remaining (round C)

- Push order: `rtsai/engine` (68c1e95557) to `alibad/OpenRA` first, then this `main`. Not approved yet.
- RTSAI-Web: the Studio ran `sync:art` on `rtsai/integration` (56f1bf5, ce9b33d); `sync:content` and `sync:game-media`
  remain for its owner. The Levant game-media sync reads `israel-art/` and `hezbollah-art/source-art-review.png`,
  which left the mod (archived in RTSAI-Art `history/_shared/`).
- RTSAI-Art: 28 uncommitted `voxel-v5-glb/meta.json` muzzle edits and 73 untracked candidate folders from other
  agents (2026-10-06) were left alone.

# Round B: five complete factions (Phase 2)

Date: 2026-10-02. The mod's `main` has 6 new commits on 8928ebd (5d352f6 … this document), local only. The engine
branch `rtsai/engine` has one new commit on f2bfa43fba (5523a9907f), local only. `OpenRA-AI`, its worktrees, the
canonical `OpenRA` checkout and `OpenRA-Upstreams` were only read.

| Goal | Result |
|---|---|
| 1. Saudi Arabia and Yemen | Done. Plain mod factions with flags, voices and random-pool entries. One engine commit for the frigate's interceptor magazine |
| 2. Arabic/RTL | Not added. The Saudi/Yemen content has no Arabic text, so the condition is not met |
| 3. Faction bot doctrine | Done, mod only. Role-aware combined-arms modules plus a `BotDoctrine` per faction, with openings |
| 4. Translation warnings | Done: 793 → 0 |
| 5. HUD overlap | Fixed |

## 1. Saudi Arabia and Yemen (5d352f6)

`tools/port-modern-factions.py` is now incremental. It ports the requested factions that `mod.yaml` does not list yet,
then recomputes the shared files: exclusions, bot type lists, pools, flags, metrics and the manifest.
`--factions saudi,yemen --product ../OpenRA-AI-wt-ra2-red-sea` ported 226 files.

- **Source.** `codex/ra2-red-sea` @ b3b0ebd, **working tree**.
  - Included uncommitted edits: `saudi-messages.ftl`, `saudi-roster.yaml`, `saudi-weapons.yaml`,
    `yemen-roster.yaml` and `yemen.yaml`. They cover the brace wording, the National Guard moving while braced,
    the SUPPLIED/LINKED/GUIDED labels, the removed F-15 strike MinRange and the Hodeidah muzzle height.
  - Not included: the untracked `scripts/validate-ra2-red-sea.py`, a product harness that runs on the fork engine.
- **Names, pools and flags.**
  - Display names are "Saudi Arabia" and "Yemen" (`ra2-modern-{saudi,yemen}-name`).
  - Saudi Arabia joins `random-allies` and Yemen joins `random-soviets`.
  - Lobby flags come from the fork's `glyphs-redsea.png` (atlas row y=256, x=90/120).
- **Audio.** 75 files:
  - 56 Arabic/English voice lines. The rsa-veh and naval lines come from the overlay, the rest from the fork's
    `mods/ra/bits`.
  - 19 Red Sea weapon and naval sounds.
- **Fork-only features.**
  - `NavalRadarVisibility` moved into `OpenRA.Mods.RTSAI`.
  - The Saudi frigate's interceptor magazine (`JamsMissiles` AmmoPool/AmmoUsage/InterceptCooldown/InterceptSound)
    cannot live in a mod, because `Missile` only asks the engine trait.
  - Engine commit 5523a9907f adds it: 2 files, +56/−5, and nothing changes when the fields are unused.
    `ENGINE_VERSION` is repinned to it.

## 2. Arabic/RTL: not triggered

A scan for Arabic code points (U+0600–U+06FF) found none in the Saudi/Yemen YAML/FTL (red-sea working tree and mod),
nor in `catalog/factions.json` [ran]. All names and descriptions are English; Arabic exists only in the voice audio.
So there is no engine change.

Windowed captures [ran]:
- Saudi player on the dev build: M1A2S, National Guard and ATGM team, with the green Saudi flag in the tooltip.
- Yemen player on the packaged build, with the Yemen flag in the tooltip.

All text renders. When Arabic text ships, port `UnicodeText.cs` and the font fallback from fork 35b0199795.

## 3. Faction bot doctrine (21ff8f6)

No engine change. Three modules in `OpenRA.Mods.RTSAI/Traits/BotModules`:
- `DoctrineUnitBuilderBotModule`: the upstream unit builder plus the fork's `RoleShares` (StrategicRole shares
  balanced per production queue).
- `DoctrineBaseBuilderBotModule` (plus its queue manager): the upstream base builder plus the fork's
  `InitialBuildOrder` and its low-power guard.
- `BotDoctrine` (new; `modern-factions/doctrines.yaml`): per faction, `RoleShareModifiers` scale the bot profile's
  RoleShares, and its own `InitialBuildOrder` replaces the profile's. The openings follow the tech tree.

The five doctrines:

| Faction | Doctrine | Opening | Role emphasis |
|---|---|---|---|
| China | networked-combined-arms | standard | support ×2, transport, navy |
| Iran | layered-denial | radar and AA site before the factory | AA, artillery, anti-armor |
| Türkiye | mobile-defense | early service depot | MBT, IFV transport, drones |
| Saudi Arabia | expeditionary | Air Force Command before the factory | MBT, air, artillery |
| Yemen | asymmetric-defense | barracks before the refinery, early bunker | infantry, RPG, rockets, drones, boats |

Tooling:
- `port-modern-factions.py --doctrine-ai` renames the stock modules in every bot profile and restores the
  InitialBuildOrder openings. It also ports `combined-arms-ai.yaml`: RoleShares, bot caps and stock-actor roles.
- `RTSAI_BOT_LOG=1` writes `Logs/bot-doctrine.log`.
- `tools/replay-production.py` summarises the production in any replay.

Evidence [ran]:
- **Logs.** They show each faction's scaled shares, for example Saudi main-battle-tank 39 (profile 26) and Iran
  (turtle) anti-air 28. They also show the bots following the doctrine openings.
- **8-minute five-bot match.**
  - China: rifle, portable, Qilin, PHL, Mantis.
  - Iran: Toophan ×6, Basij ×5, Raad, plus radar and an AA site.
  - Türkiye: service depot, Gökkalkan ×2, Bozkır.
  - Saudi Arabia: AF Command, Patriot, TOW, Caesar, ATGM team.
  - Yemen: bunker before the refinery, RPG ×5, Mountain Rifleman ×3, technical RR, MLR.
- **A/B, 300 s, same five bots.** Every doctrine bot fielded vehicles, while the stock bots built mostly infantry.
  Total output is similar: stock 13–29 production orders, doctrine 12–17. The upstream RA2 bot economy limits the
  early-game pace, not these modules.

## 4. Translation warnings (ebf61b8)

`tools/fluentize.py` runs the lint and turns each reported literal into a Fluent key:
- 437 rules messages, in `languages/rules/en.ftl`;
- 40 chrome and hotkey messages, in `languages/chrome/en.ftl`;
- 71 widget strings that reuse identical engine `common|fluent` keys.

Special cases:
- Two `{0}` labels lost their dead text.
- The dead LoadScreen `Text` became `loadscreen-loading`.
- `support-power-timer` takes upstream RA's format.
- The old `{(Ctrl)}` markup became `<(Ctrl)>`.

`make test`: 0 errors, 0 warnings [ran].

## 5. HUD overlap (40901fa)

- **Cause.** "AUTO: STARTING…", shown until the companion acknowledges, is wider than the fixed 72 px AUTO button,
  so it was drawn over LOG. A capture of the early state showed "LOGAUTO: STARTING." [ran]
- **Fix.** The strip's buttons grow to fit their text, and the layout uses the measured widths.
- **After.** The buttons are separate in the startup state and with a two-line status [ran].
- Also fixed a mojibake bullet in two error messages.

## Acceptance [ran, on 446479f]

| Check | Result |
|---|---|
| `make clean && make all` | exit 0, 0 warnings, 0 errors |
| `make test` | exit 0, 0 errors, 0 warnings |
| 180 s headless, each modern faction as a bot | 5 parallel runs, all exit 124 (timeout), 0 exceptions. Own units queued: China r2cnrifle, r2cnportable; Iran r2toophan, r2basij; Türkiye r2trat; Saudi r2sang, r2saat; Yemen r2yrpg, r2ymr |
| Bot-vs-bot spectator | 300 s with five bots on the normal/rush/turtle/naval/normal profiles: 0 exceptions. An earlier 480 s run also had 0 |
| Windowed capture, Saudi/Yemen | 1152×720 frames of the Saudi (dev) and Yemen (packaged) bases, with faction flags and the HUD |
| Probe as Saudi Arabia (packaged build; also dev, windowed) | Observe ticks 20→150→260, units `amcv engineer r2m1a2s r2saat r2sang`. GetState `player_faction=saudi enemy_faction=yemen`. Deploy → `gacnst` |
| Packaged Windows build | `spike-portable.sh`: 19 s, 404 files, 191 MB, `includedFrameworks` NETCore + AspNetCore 10.0.11. `RTSAI.exe` launched headless (the probe above, Kestrel loaded from the package) and windowed (the Yemen frame) |

Housekeeping:
- Every game process was stopped by PID after its run; none remain.
- `%APPDATA%\OpenRA` was not written: the ModMetadata timestamp is unchanged since 2026-08-21.
- The copied `.mix` files and the support dirs were deleted.

## Reproduce (round B)
```
python tools/port-modern-factions.py --factions saudi,yemen --product ../OpenRA-AI-wt-ra2-red-sea --doctrine-ai  # applied
python tools/fluentize.py                     # applied; finds nothing left to convert
RTSAI_BOT_LOG=1 tools/run-headless.sh <support> 180 defcon-6 Multi1:normal:saudi yemen   # <support>/Logs/bot-doctrine.log
python tools/replay-production.py <support>/Replays/rtsai/{DEV_VERSION}/<replay>.orarep
# windowed + companion, then:
OpenRA-AI/.venv/Scripts/python tools/probe-bridge.py --deploy-mcv --early-frame start.png --frame later.png --status "long text"
packaging/windows/spike-portable.sh <outdir>   # then <outdir>/RTSAI.exe Engine.SupportDir=<support> ...
```

## Remaining gaps (round B)

1. **Nothing is pushed.** `AUTOMATIC_ENGINE_SOURCE` cannot resolve 5523a9907f until `rtsai/engine` is pushed.
2. **Balance is unproven.**
   - The doctrine multipliers and openings come from the catalog doctrines, not from win-rate tuning.
   - No automated balance matches with recorded outcomes have been run.
   - Early bots are economy-bound on DEFCON 6.
3. **Squads are not doctrine-aware.** SquadSize stays per profile. Not ported from the fork: the Experience-only
   `formation-size` parameter and the SupportPower, Minelayer and AirStates bot changes.
4. **Not ported:**
   - the per-country validators (`validate-ra2-*.py`);
   - the catalog flip in OpenRA-AI;
   - painted cameos, EVA and website captures.
5. **Packaging.** The NSIS installer, macOS and Linux were not run. makensis, rcedit and wine are not installed.
6. **Translations.** The generated keys are English only. The upstream pre-release notice still names
   "OpenRA's Red Alert 2 mod".

# Round A

Date: 2026-10-02. Mod repo: `RTSAI-Mod` (local only). Engine: branch `rtsai/engine` in the canonical
OpenRA repo, worktree `C:\Users\Admin\Code\hq\games\OpenRA-wt-rtsai-engine` (local only, never pushed).
The canonical checkout's working tree and branch (`main` @ 5ddc34cb91) were not touched. `OpenRA-AI` was
only read (working tree on `refocus/phase-0`).

## Done

| Goal | Status |
|---|---|
| 1. Slim engine branch | Done. 9 small commits on upstream bleed `7d57605bca` |
| 2. Repin the mod | Done. `ENGINE_VERSION=f2bfa43fba…`; `make all` and `make test` exit 0 [ran] |
| 3. Clean up the mod | Done. Trait renamed back to `CompanionBridge`, companion-only RPCs, HUD logic moved, guarded startup |
| 4. Spectator crash | Fixed. Root cause found (stale RA2 observer chrome) [ran] |
| 5. Modern factions | Done. China, Iran and Türkiye are plain mod rules, selectable alongside the 9 RA2 countries [ran] |
| 6. Acceptance checks | All pass [ran]; details below |

## 1. Slim engine diff (`origin/bleed` 7d57605bca → `rtsai/engine` f2bfa43fba)

12 files, +352 / −11. Of that, 239 lines are the Null platform. For comparison, the fork's main changed
83 core files (+2064/−350) and 232 `Mods.Common` files (+33.8k).

| Commit | Change | Files (lines) |
|---|---|---|
| 83ebc052d1 | Launchers reference `Microsoft.AspNetCore.App` (a mod cannot add a shared framework) | Launcher + WindowsLauncher csproj (+10) |
| 503c345520 | `Renderer.CaptureScreenshot` → PNG bytes; row stride and row count come from the texture actually read back | Renderer.cs (+37) |
| e0703e7f64 | `Game.IsKeyDown` key-state tracking for push-to-talk | Game.cs, InputHandler.cs (+12) |
| f1da4cd281 | `OpenRA.Platforms.Null` headless platform and `Game.IsHeadless` | NullPlatform.cs, csproj, slnx, Game.cs (+243) |
| 06d6850e50 | `Launch.Bots=slot:bot[:faction],…` and `Launch.Faction` for `Launch.Map` (bot in Multi0 → spectate) | Game.cs, LaunchArguments.cs, BlankLoadScreen.cs (+36/−6) |
| d25fffa52e | Headless: no CursorManager on the Null platform (it reads texture pixels) | Game.cs (+6/−4) |
| ec03561fed | RenderVoxels.PlayerPalette is `[PaletteReference(true)]`, as in RenderSprites (upstream lint bug) | RenderVoxels.cs (+1/−1) |
| 491e33291d | Viewport starts with `LastMousePos` at screen centre, so the cursor default of (0,0) no longer edge-scrolls the camera away | Viewport.cs (+5) |
| f2bfa43fba | CaptureScreenshot error now reports the texture, data, screen and window sizes | Renderer.cs (+3/−1) |

Left out on purpose: the Experience system, `mods/ra` changes, the engine `OpenRA.Mods.RA2`, companion/RL code in
`Mods.Common`, hard-coded `"ra2"` checks, and Arabic/RTL text.
- **Bot hooks were not needed.** `ModularBot.Deactivate` was replaced in the mod by `ModularBot.IsEnabled = false`.
  `IBotOrderFilter` only served the fork's support-power blast-zone AI, not the companion.
- **Two commits were not on the requested list:** `ec03561fed` and `491e33291d`. Both are upstreamable bug fixes the
  mod needed. Without the first, the modern-faction voxels fail lint. Without the second, the camera drifted to the
  map corner in automated windowed runs.

**Correction to SPIKE.md B3.** The "CaptureScreenshot throws" bug was a misdiagnosis. `settings.yaml` in the
isolated support dir had persisted `Game.Platform: Null` from the headless runs, so every "windowed" spike run was
really headless (texture 0×0) [ran: the new diagnostic message showed `NullGraphicsContext`]. With
`Game.Platform=Default`, a real 1152×720 frame is captured on the slim engine [ran]. The old message of
`503c345520` still claims a windowed RA2 failure; `f2bfa43fba` explains what actually happened.

## 2. Repin and build

- `mod.config` `ENGINE_VERSION=f2bfa43fbab7f3f3416b7c4b1b2c35afcfc71f9f`. `fetch-local-engine.sh` runs `git archive`
  from `../OpenRA` (the worktree's branch lives in the same object store).
- **Blocker for others:** `AUTOMATIC_ENGINE_SOURCE` still points at `alibad/OpenRA`, which does not have this commit
  until `rtsai/engine` is pushed.
- `OpenRA.Mods.RA2` was ported to upstream's float→`System.Numerics` migration (`90c4415b7e`): 4 files.
- Evidence [ran]:
  - `fetch` 5 s.
  - `make.cmd all` 7 s, `0 Warning(s) 0 Error(s)` for both the engine and the mod.
  - `make.cmd test` exit 0, 0 errors, `Warnings: 793`. All 793 are missing Fluent keys carried over from upstream RA2's literal strings.
  - `rtsai-content --check-yaml` exit 0.

## 3. Mod cleanup

- `CompanionBridge` trait (no collision; the engine ships none). `rules/companion.yaml` uses it.
- `CompanionService` implements only Observe, GetState, UpdateCompanionStatus, UpdateCompanionThreat,
  CaptureCompanionFrame and ExecuteCompanionActions.
  - **RL seam:** GameSession, FastAdvance, CreateSession and DestroySession are not overridden, so they answer
    UNIMPLEMENTED. In OpenRA-AI these are used only by the multi-session evaluation harness (`autonomous.py`,
    `mission_eval.py`, `game_runtime.py`), not by the in-game companion.
  - `ExternalBotBridge` and `RLSessionManager` were deleted. The proto is unchanged, so the Python stubs still match.
- `CompanionGrpcHost` hosts Kestrel once per process behind a `NoInlining` seam. A missing ASP.NET Core framework
  logs `Companion bridge disabled: …` to `companion.log`, and the game keeps running.
- HUD moved into `OpenRA.Mods.RTSAI.Widgets.Logic`: CompanionStatusLogic, AISettingsLogic, AIHotkeyLogic,
  AIControlDisplay and OpenRAAILocalClient. The mod now owns `chrome/ingame.yaml` (adds AIHotkeyLogic),
  `chrome/settings.yaml` (adds the AI panel), `settings-ai.yaml`, `hotkeys-ai.yaml` and 52 AI Fluent strings (`languages/ai.ftl`).

## 4. Spectator crash: root cause

`ObserverShroudSelectorLogic` and `ObserverStatsLogic` now expect `LabelWithTooltip@LABEL/PLAYER` and
`ScrollableLineGraph@INCOME_GRAPH/ARMY_VALUE_GRAPH`, but the RA2 chrome still declared `Label`/`LineGraph`.
The slim engine surfaced the `InvalidCastException`; the fork had swallowed it, which left `FLAG` unbound and
produced "Sprite `/`". Fixed in `mods/rtsai/chrome/ingame-observer.yaml` (8 widgets).

## 5. Modern factions

`tools/port-modern-factions.py` does once, statically, what the Experience system did at load time:
- static manifest entries;
- merged `~!faction.X` exclusions;
- `RandomFactionMemberOf` → upstream `RandomFactionMembers`;
- fork-only `Additional*Types` folded into `bot-types.yaml`;
- fork-only `InitialBuildOrder` dropped;
- flags appended to the lobby atlas;
- `FactionSuffix` metrics;
- 96 original bilingual voice lines (20 MB) taken from the fork's `mods/ra/bits`.

`StrategicRole` (metadata only) moved into the mod. Not ported: `ra2-combined-arms-ai`, which needs the fork's
role-based bot modules.

## 6. Acceptance evidence [ran]

| Check | Result |
|---|---|
| `make all` / `make test` | exit 0 / exit 0, 0 errors (793 inherited Fluent warnings) |
| Headless ≥60 s, each modern faction as a bot | 65 s each for `Multi1:normal:china`, `:iran`, `:turkey` vs the local slot: exit 124 (timeout), 0 exceptions, replay `Faction: <x>` |
| Same, with production | 180 s spectator matches. Türkiye bot built `r2trrifle r2hisar r2trat`; Iran bot built `r2toophan r2basij r2irbunker`. China bot (180 s, final pin) built `r2cnrifle r2cnportable r2bastion` |
| Bot-vs-bot spectator | 90 s with 3 modern bots, then 180 s ×3: 0 exceptions (crashed on the first frame before the fix). Windowed spectator (Türkiye vs Iran bots): CaptureCompanionFrame at tick 731 shows the observer UI (timer, minimap, shroud selector) and the rendered map |
| Companion, player is a modern faction | Türkiye (headless): Observe ticks 20→260, units `amcv engineer r2bozkir r2trat r2trrifle`; GetState `player_faction=turkey enemy_faction=iran`; deploy → `gacnst`. China (windowed): Observe/GetState ok, CaptureCompanionFrame 1152×720 shows the base, the China flag and the mod HUD strip |
| Guarded startup | ASP.NET removed from the runtimeconfig: `Companion bridge disabled: …FileNotFoundException…`, and the game ran the full 40 s |

## Remaining blockers / follow-ups

1. **Engine branch not pushed.** `AUTOMATIC_ENGINE_SOURCE` cannot resolve `f2bfa43fba` for anyone else until
   `rtsai/engine` is on `alibad/OpenRA`.
2. **793 Fluent warnings** from upstream RA2's literal names. Convert them to Fluent keys; this is mechanical, not done.
3. **Not ported:** `ra2-combined-arms-ai` and `InitialBuildOrder` (fork bot modules). Bots use upstream production
   with the faction `UnitsToBuild`. WarRoom panel and the AI-hotkey group in the hotkey settings: not ported.
4. **HUD:** the strip's `LOG` and `AUTO: STARTING.` buttons overlap when the status text is long (cosmetic).
5. **Not re-run on the slim engine:** the self-contained package (`packaging/windows/spike-portable.sh`).
   The launcher change is the same as the one proven in the spike [inferred].
6. **macOS SDK packaging script** still needs porting (from SPIKE.md).
7. **Product companion launch:** `CompanionBootstrap` is not in the slim launcher. Decide on mod-side process
   hosting vs a wrapper.

## Next round (B)

Push `rtsai/engine`, or open upstream PRs for the 9 commits; most are upstreamable. Then:
- Arabic/RTL text, together with Saudi Arabia and Yemen from `codex/ra2-red-sea`;
- the role-based bot modules as a mod `BotModule`, which restores combined-arms AI and `InitialBuildOrder`;
- the Fluent key conversion;
- a companion process host;
- re-running packaging on all platforms.

## Reproduce
```
./fetch-local-engine.sh && ./make.cmd all && ./make.cmd test
python tools/port-modern-factions.py      # one-shot, already applied (needs Pillow, e.g. OpenRA-AI/.venv)
tools/run-headless.sh <support> 90 defcon-6 Multi0:normal:china,Multi1:rush:iran,Multi2:turtle:turkey
OPENRA_AI_COMPANION=1 tools/run-headless.sh <support> 100 defcon-6 Multi1:normal:iran turkey &
OpenRA-AI/.venv/Scripts/python tools/probe-bridge.py --deploy-mcv
# windowed: pass Game.Platform=Default explicitly (support-dir settings persist Null from headless runs)
```

Cleanup: all game processes were killed after each run. The copied `.mix` files were deleted from the scratch
support dirs at the end. No `.mix` file is tracked in any repo.
