# Spike: RTS AI as an OpenRA Mod SDK mod (Red Alert 2 base)

Date: 2026-10-02. Engine pin: `alibad/OpenRA` main @ `5ddc34cb91e52953d4844c169075a0dbbd79e139` (.NET 10, fork of upstream bleed @ `ef5541cce4`).
SDK template: `OpenRA/OpenRAModSDK` @ `df10393`. Host: Windows 11, .NET SDK 10.0.400, Git Bash + PowerShell 5.1.

This repo is local-only (no remote). The engine is exported into `./engine` (gitignored) by
`./fetch-local-engine.sh` (a `git archive` of the local fork; read-only). No proprietary RA2
files are committed. Runtime tests used an isolated support dir
(`%TEMP%\claude\...\scratchpad\rtsai-spike-support`) holding copies of `ra2.mix`, `language.mix`
and `theme.mix` from the owned Steam install.

## Verdicts

| # | Question | Verdict |
|---|----------|---------|
| 1 | SDK scaffold builds, lints and runs against the pinned fork engine | **GO** |
| 2 | RA2 data and the fork's net10 `OpenRA.Mods.RA2` as a mod; content installer; skirmish starts | **GO-WITH-CONDITIONS** |
| 3 | Companion gRPC bridge (Kestrel / Grpc.AspNetCore) inside a mod assembly, dev and packaged | **GO** (one engine requirement, see below) |
| 4 | Slim engine: which fork core changes the mod actually needs | **GO**: the list is short (see §4) |

How each result was established: **[ran]** means a command was run and its output observed.
**[read]** means the conclusion comes from reading code or config. **[inferred]** means it is
reasoned but was not run.

---

## 1. Scaffold: GO

What was done
- Started from the unmodified SDK template (commit `96d70b7`), then renamed it to `MOD_ID=rtsai`,
  `OpenRA.Mods.RTSAI` and `RTSAI.sln`.
- `mod.config`: `ENGINE_VERSION=5ddc34cb91e52953d4844c169075a0dbbd79e139`, `AUTOMATIC_ENGINE_MANAGEMENT=True`,
  `AUTOMATIC_ENGINE_SOURCE=https://github.com/alibad/OpenRA/archive/${ENGINE_VERSION}.zip`.
  Expanded, that is `https://github.com/alibad/OpenRA/archive/5ddc34cb91e52953d4844c169075a0dbbd79e139.zip`.
  `alibad/OpenRA` is public and `fork/main` contains the commit, so the stock download path would work
  **[read: `gh repo view`, `git branch -r --contains`]**.
- `fetch-local-engine.sh` is an offline stand-in for the download step. It runs `git archive <pin>` from
  `../OpenRA` into `./engine`, writes `VERSION`, copies the local GeoIP zip so `make all` does no network
  fetch, and removes the engine's `OpenRA.Mods.RA2` (see Q2). Once `engine/VERSION` matches
  `ENGINE_VERSION`, the stock `make.ps1` builds the engine in place and does not download.

Evidence **[ran]**
```
./fetch-local-engine.sh            10 s
.\make.cmd all                      7 s (warm NuGet/compiler; first run 10.7 s)  -> Build succeeded, 0 warnings, 0 errors
.\make.cmd test   (Utility rtsai --check-yaml)   16 s -> exit 0, "Warnings: 793", 0 errors
OpenRA.Utility rtsai-content --check-yaml        -> exit 0
```

SDK script changes needed for net10/bleed

| Script | Change | Status |
|---|---|---|
| `make.ps1`, `make.cmd`, `utility.cmd` | none. The engine's `make.cmd all/version` and `bin/OpenRA.Utility.exe` interface is unchanged | [ran] |
| `fetch-local-engine.sh` | new, offline equivalent of automatic engine management | [ran] |
| `packaging/windows/buildpackage.sh` | The fork's `install_assemblies` dropped the `RUNTIME` ("net6") positional argument. The SDK still passes it, which shifts every flag: `CopyGenericLauncher=net6`, **`CopyCncDll=False`**, `CopyD2kDll=<cnc value>`. Removed the argument. Also changed `build_platform x86` to `arm64` to match the fork, which ships x64 and arm64 only | fixed [read]. The dotnet half was reproduced natively [ran]; NSIS/wine/rcedit not run |
| `packaging/linux/buildpackage.sh` | same `"net6"` argument removed | fixed [read], not run |
| `packaging/macos/buildpackage.sh` | still builds a mono variant (`apphost-mono.c`, `checkmono.c`), and those files no longer exist in bleed. Needs a port to the fork's `packaging/macos/buildpackage.sh` model | **not fixed** [read] |
| `Makefile` (Unix) | still has `RUNTIME=net6`/mono branches. The net path should still work; `make` is not installed on this box | [inferred] |
| `.gitattributes` | `* text=lf` is not a valid setting and `core.autocrlf=true` would turn `.sh` and `mod.config` into CRLF. Added `*.sh`, `mod.config` and `user.config` `eol=lf` | fixed |
| `mod.config` | `PACKAGING_COPY_ENGINE_FILES="./mods/common-content"`, which the content installer mod needs | fixed |

Note: the stock automatic-download path also deletes `engine/OpenRA.Mods.Common/Lint/CheckFluentReferences.cs`
(an SDK hack for the Example mod). It is harmless here and is not needed: the lint passes with the file present.

---

## 2. RA2 content: GO-WITH-CONDITIONS

What was done
- `OpenRA.Mods.RA2/`: the fork's net10 copy (36 files, from `5ddc34cb91`) with an SDK-style csproj
  (`EngineRootPath=../engine`). The fork's copy is a further evolution of upstream `ra2@61e24e3` plus the
  C# half of `compatibility.patch` (verified by diff). The engine's own `OpenRA.Mods.RA2` is removed from the export
  so only one `OpenRA.Mods.RA2.dll` reaches `engine/bin`. The only Experience coupling in RA2
  (`MindController` reads `ExperienceCatalog` for a capacity override) was removed. After that,
  **`OpenRA.Mods.RA2` compiles against upstream bleed `ef5541cce4` with zero errors** [ran; upstream exported to
  scratch and retargeted to net10/C# 13].
- `mods/rtsai/` was generated by `tools/port-ra2.py`: upstream `ra2@61e24e3`, plus the data half of
  `OpenRA-AI/apps/installer/ra2/compatibility.patch`, plus the non-experience subset of `prepare-ra2.py:integrate()`:
  AI HUD strip from `mods/ra/chrome/ingame-player.yaml`, `settings-ai.yaml`, common main menu,
  five bot profiles, `rules/companion.yaml`, fence trim and glyphs. It skips the modern-faction overlay,
  `experiences.yaml`, composer/review/Earth-studio chrome, the flag atlas and faction metrics.
  The filesystem was switched to the RV layout: `ContentInstallerFileSystem` with nested mixes
  (`content|ra2.mix: ra2mix`, `ra2mix|conquer.mix: conquer`, …) and `ContentInstallerMod: rtsai-content`.
- `mods/rtsai-content/` follows RV's `rv-content` model, RA2-only: `ra2.yaml` (disc), `origin.yaml` (EA/Origin registry
  `EA Games\Command and Conquer Red Alert II`), `firstdecade.yaml` (TFD), and `steam.yaml` (`AppId: 2229850`,
  IDFile `THEME.MIX` sha1 `184f99e3…`, which matches the owned install [ran: sha1sum]).

Evidence **[ran]**
- `check-yaml`: 0 errors. The 793 warnings are all missing Fluent keys carried over from upstream RA2's literal strings.
- The same data with the AI chrome removed (companion rule, `settings-ai.yaml`, HUD strip, one fork-only ftl) also
  **lints with 0 errors against upstream bleed**, together with the RA2 dll built against upstream.
  RA2 gameplay therefore needs no fork engine changes.
- Headless skirmish (fork `Game.Platform=Null` + `Launch.Map=defcon-6 Launch.Bots=Multi1:normal`) with the
  owned mixes in the isolated support dir: `Loading mod: rtsai`, `Game started.`,
  `ReplayRecorder: StartGame detected`. The run lasted 60 s with no exception, and the replay grew to 24 KB of orders.
  Through the bridge (Q3), ticks advanced `10 -> 250 -> 470` and the local MCV (`amcv`/`smcv`) was observed.
- Windowed run (`Graphics.Mode=Windowed`, default GL platform): the match started and the bridge answered
  (ticks `20 -> 370`). No visual screenshot was obtained: the engine capture failed (see blocker B3), and this
  agent session could not enumerate the game window. Rendering is **partially verified**: the renderer was active,
  but no image was inspected.
- Packaged self-contained build (Q3) loads `rtsai` from the package dir with the same isolated support dir.

Conditions / blockers
- **B1: spectator UI crash.** In all-bot matches (`Launch.Bots=Multi0:normal,Multi1:normal`, so the local client spectates),
  the first frame throws `Sprite '/' was not found`. Instrumented (engine copy only, then reverted), the failing widget is
  `INGAME_ROOT/WORLD_ROOT/PLAYER_ROOT/OBSERVER_WIDGETS/OBSERVER_CONTROL_BG/SHROUD_SELECTOR/FLAG`, and
  `ObserverShroudSelectorLogic` never reaches its `FLAG` binding. The root cause is not yet isolated. The chrome is
  identical to the product's RA2 observer chrome, so the product probably has the same bug (not verified).
  Fix: debug `ObserverShroudSelectorLogic` construction for RA2 (see if it throws or is skipped), or align the RA2
  observer layout with the fork's `ra` layout. The player-vs-bot path is unaffected.
- **B2: hard-coded `"ra2"` mod id in the fork engine.** `MainMenuLogic` (ra/ra2 game selection, content check),
  `LoadIngamePlayerOrObserverUILogic` and `OpenRA.Launcher` (companion autostart for `ra`/`ra2`). Under `rtsai`
  these branches do not apply. Fix: remove them from the slim engine; the mod does not need them.
- 793 Fluent warnings (upstream RA2 debt). Not a blocker; convert names to Fluent keys during the migration.
- Not exercised: the content-installer UI itself (Steam/Origin detection). Only the YAML lints and the Steam IDFile hash matches.

---

## 3. Companion bridge inside a mod assembly: GO

What was done
- `OpenRA.Mods.RTSAI/Companion/` copies the bridge closure from the fork's `OpenRA.Mods.Common/Traits/Player`:
  `CompanionBridge`, `ExternalBotBridge` (hosts Kestrel), `RLBridgeService`, `RLSessionManager`,
  `ObservationSerializer`, `ObservationWeaponTargets`, `ActionHandler` and `rl_bridge.proto`, compiled by `Grpc.Tools`
  with `csharp_namespace = OpenRA.Mods.RTSAI.RL` (wire names unchanged). The csproj carries `Grpc.AspNetCore 2.67.0`,
  `Google.Protobuf 3.29.3` and `FrameworkReference Microsoft.AspNetCore.App`, at the same versions as the engine.
- **Choice: copy and rename, against an unmodified fork engine.** The engine's Mods.Common still ships
  `CompanionBridgeInfo`. `ObjectCreator.FindType` returns the *first* assembly/namespace match (Mods.Common comes before
  the mod), so the YAML-visible traits were renamed `RTSAICompanionBridge` / `RTSAIExternalBotBridge`, and
  `rules/companion.yaml` uses `RTSAICompanionBridge`. Internal helper types keep their names: the mod namespace wins
  over `using` imports. This keeps the engine pin byte-identical, so the result isolates "does it work from a mod".
- One mod-side workaround: `IgnoresDisguiseInfo` is `internal` in Mods.Common, so the serializer matches it by type name.

Evidence **[ran]** (`tools/probe-bridge.py` imports `OpenRA-AI/services/companion` read-only and uses its venv)
```
rl-bridge.log: OpenRA AI companion enabled on port 9998 (trait OpenRA.Mods.RTSAI.Traits.RTSAICompanionBridge from OpenRA.Mods.RTSAI)
               Kestrel: C:\Users\Admin\.dotnet\shared\Microsoft.AspNetCore.App\10.0.10\Microsoft.AspNetCore.dll
               Grpc.AspNetCore.Server: ...\RTSAI-Mod\engine\bin\Grpc.AspNetCore.Server.dll
               Load contexts: mod=OpenRA.Support.ManagedLoadContext #5, kestrel=Default, grpc=ManagedLoadContext #5
probe: Observe first response 4.2 s after launch; Observe tick 10 -> 130/250/470; GetState ok;
       UpdateCompanionStatus accepted=true;
       ExecuteCompanionActions(deploy MCV) accepted ("Queued as a synchronized local-player order")
       -> Observe tick 60: units [], buildings ["gacnst"]   (action round-trip through the mod bridge)
netstat: 127.0.0.1:9998 and [::1]:9998 LISTENING (loopback only)
```
Grpc resolves through the **mod's own** `deps.json` into the mod's load context, not through Mods.Common.
Kestrel comes from the shared framework in the Default context.

Counterfactual: the engine requirement **[ran]**. With `Microsoft.AspNetCore.App` removed from `engine/bin/OpenRA.runtimeconfig.json`,
the bridge cannot start: `FileNotFoundException: Microsoft.AspNetCore, Version=10.0.0.0`, and it is *unhandled*, so the
whole game process dies, because the JIT fails outside the `try` in the thread body. A mod **cannot** add a shared
framework to the host process. The launcher's `<FrameworkReference Include="Microsoft.AspNetCore.App" />` (already in the
fork's `OpenRA.Launcher` and `OpenRA.WindowsLauncher`) is therefore a required engine change. Mod fix: wrap the server
thread in a non-inlined `try` so a missing framework disables the bridge instead of crashing.

Packaged self-contained build **[ran]**
`packaging/windows/spike-portable.sh` reproduces the dotnet half of the SDK's `buildpackage.sh`: engine
`dotnet publish --self-contained -r win-x64`, the mod `.sln` publish into the same dir, then `OpenRA.WindowsLauncher`
published as `RTSAI.exe` with `ModID=rtsai`. Result: 146 MB, 404 files, in 9 s warm. `RTSAI.runtimeconfig.json` lists
`includedFrameworks: Microsoft.NETCore.App 10.0.11, Microsoft.AspNetCore.App 10.0.11`, and `RTSAI.deps.json` contains the
`runtimepack.Microsoft.AspNetCore.App.Runtime.win-x64` assets. Running `RTSAI.exe` (inner-launcher child process) headless
with `OPENRA_AI_COMPANION=1`: Kestrel loaded from `pkg\Microsoft.AspNetCore.dll` (Default), Grpc from `pkg\` (mod context),
and all probe RPCs answered as in dev. macOS and Linux packaging were not run. They publish `OpenRA.Launcher`
self-contained, which carries the same FrameworkReference, so the same result is expected [inferred]. The macOS SDK
script must be ported first (Q1).

Blockers and follow-ups
- **B3: `Renderer.CaptureScreenshot` throws** (`Array.Copy` "Source array was not long enough", `Renderer.cs:579`) on every
  `CaptureCompanionFrame` in windowed RA2 runs at 1280×800 and 1024×768. This is engine code, not the mod. The math only
  fails if `screenSprite.Bounds.Width > Sheet.Size.Width`, so suspect a stale sheet or a DPI-scaled surface. Not checked
  in the product. Fix in the fork, then re-test live vision.
- **B4: HUD widgets are bound to the engine's bridge.** The copied AI HUD strip uses Mods.Common logic
  (`CompanionStatusLogic`, `AISettingsLogic`; also `WarRoomLogic`, `AIHotkeyLogic`, `AIControlDisplay`). These read
  the *engine* `CompanionBridge` statics, so the in-game strip will not reflect the mod bridge. Fix: move these logic
  classes into `OpenRA.Mods.RTSAI` with the bridge. That is mechanical, and they then point at the mod types.
- RL-only code came along with the closure: `RLSessionManager`, FastAdvance in `ExternalBotBridge`. Split the companion
  service from RL training so the mod depends only on what the companion needs (see §4).
- The product's Python services auto-start comes from the fork's `WindowsLauncher` `CompanionBootstrap` metadata and the
  `OpenRA.Launcher` PowerShell autostart (gated on `ra`/`ra2`). The SDK launcher does not set it. Decide whether the mod
  spawns/monitors the companion process itself (recommended) or a thin product wrapper launches `RTSAI.exe`.

---

## 4. Slim engine list: GO

Method: compile the mod projects against **upstream bleed `ef5541cce4`** (the fork's merge base, retargeted to net10/C# 13)
and lint the RA2 data on it [ran], plus the runtime counterfactual above [ran]. The fork changes 83 core files
(+2064/-350 in Game/Platforms/launchers/Server/Utility) and 232 Mods.Common files (+33.8k).

**Required core changes (OpenRA.Game / Platforms / launchers)**
1. `OpenRA.Launcher` + `OpenRA.WindowsLauncher` `<FrameworkReference Include="Microsoft.AspNetCore.App" />`. **Proven required** (counterfactual crash).
2. `Renderer.CaptureScreenshot` (companion live vision; compile-required by the bridge). Needs the B3 fix.
3. `Game.IsKeyDown` / `Game.HandleKeyInput` key-state tracking (`InputHandler` hook), for push-to-talk (`AIHotkeyLogic`
   checks held keys). Required if push-to-talk ships [read].
4. Arabic/RTL text: `Graphics/UnicodeText.cs`, `SpriteFont`, `Fonts`, `FreeTypeFont.HasGlyph`, and the Arabic fonts in
   `mods/common`. **Not needed by the RA2 port.** Required only when Arabic UI/content ships (modern factions). Good upstream candidate.

**Mods.Common changes the mod's bridge needs** (compile-derived; could move into the mod or stay as small engine patches)
- `ModularBot.Deactivate` (assistant auto-play toggling) is a modification of an engine trait, so keep it as a patch or upstream it.
- `AIControlDisplay`, `CompanionStatusLogic`, `AISettingsLogic`, `AIHotkeyLogic`, `WarRoomLogic` and `settings-ai.yaml` should **move to the mod** (B4).

**Not required by the mod (drop from the slim engine, or keep only for tooling)**
- Experience system: `ModData` `IModFileConfiguration`, `Ruleset` overlays, `ExperienceCatalog`, the capability and presentation
  packs inside `ContentInstallerFileSystemLoader`, the composer/review/Earth-studio chrome, and faction cursor effects
  (`CursorEffectRenderer`). **Confirmed not needed**: RA2 compiles and lints without it.
- RL training: `World.SetTickScale`, `World.IsConnectionAlive`, `OrderManager.IsFastForwarding`, the 4-argument `World` ctor,
  `PerfHistory.Disabled`, and multi-session `Launch.MultiSession` / `RLSessionManager`. Keep these only if RL training stays on this engine.
- Dev/QA only (worth keeping): `OpenRA.Platforms.Null` headless mode, `Launch.Bots` + `Game.LoadMap(map, bots)`, and
  headless replay fixes. These made this spike's automated skirmish tests possible.
- Product coupling to remove: hard-coded `"ra"`/`"ra2"` branches (B2), `CompanionBootstrap` / PowerShell autostart,
  branded-launcher runtime tweaks, the `rl-bridge` log channel in `Game.cs` (the mod can `Log.AddChannel` its own),
  `mods/ra` and the engine's `OpenRA.Mods.RA2`. `mods/ra` lists `OpenRA.Mods.RA2.dll` in its Assemblies, so remove both together.
- Unclear, needs an owner decision: `LocalPlayerProfile` (+219), the `Server.cs` and network changes, and `TerrainInfo` (+118).

## Recommended next steps
1. Create the slim engine branch on `alibad/OpenRA`: upstream bleed + items 1–3 (+4 when Arabic ships) + `ModularBot.Deactivate`
   + Null platform/`Launch.Bots` + the B3 fix. Drop Experience, `mods/ra`, `OpenRA.Mods.RA2` and the companion/RL code from Mods.Common. Pin `ENGINE_VERSION` to it.
2. In the mod: trim the bridge to companion-only, move the HUD/settings logic into `OpenRA.Mods.RTSAI`, drop the
   `RTSAI` trait prefix once the engine no longer ships `CompanionBridge`, harden the server thread, and add a companion process host.
3. Fix B1 (spectator crash); port `packaging/macos/buildpackage.sh`; run the full NSIS/AppImage/macOS packaging in CI-free local builds.
4. Re-apply the modern-faction overlay as plain mod YAML. It needs no Experience system: use rulesets or a lobby option plus
   `~!faction.X` prerequisites in the mod.
5. Exercise the `rtsai-content` installer UI against the Steam and EA installs, then delete the copied mixes from the scratch support dir.

## Reproduce
```
./fetch-local-engine.sh                 # or let make.ps1 download from AUTOMATIC_ENGINE_SOURCE
./make.cmd all && ./make.cmd test
# headless skirmish + bridge (owned mixes in <support>/Content/ra2/{ra2,language,theme}.mix):
cd engine && OPENRA_AI_COMPANION=1 ./bin/OpenRA.exe Game.Mod=rtsai Engine.EngineDir=.. \
  "Engine.ModSearchPaths=<repo>/mods,./mods" "Engine.SupportDir=<support>" \
  Game.Platform=Null Launch.Map=defcon-6 Launch.Bots=Multi1:normal &
../OpenRA-AI/.venv/Scripts/python.exe tools/probe-bridge.py --deploy-mcv
packaging/windows/spike-portable.sh <outdir>   # self-contained build; run <outdir>/RTSAI.exe with the same args
```
