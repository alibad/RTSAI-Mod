# RTS AI → OpenRA Mod SDK migration: round A

Date: 2026-10-02. Mod repo: `RTSAI-Mod` (local only). Engine: branch `rtsai/engine` in the canonical
OpenRA repo, worktree `C:\Users\Admin\Code\hq\games\OpenRA-wt-rtsai-engine` (local only, never pushed).
The canonical checkout's working tree and branch (`main` @ 5ddc34cb91) were not touched. `OpenRA-AI` was
only read (working tree on `refocus/phase-0`).

How each result was established: **[ran]** means a command was run and its output observed.
**[inferred]** means it was reasoned from code or config and not run.

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
