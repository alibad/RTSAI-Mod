# RTS AI

**A standalone modern RTS built on [OpenRA](https://www.openra.net), with seven factions and project-made art, sound and maps. No Red Alert or Red Alert 2 installation is required.**

The co-commander watches your match, speaks up when it matters, answers spoken questions, and takes command only when you switch AUTO on. It sees only what you can see.

Status: **in development.** This is the canonical standalone game checkout. The earlier OpenRA AI Classic alpha remains a historical release; it is not the current standalone build. See [the product direction](docs/product-direction.md) and `MIGRATION.md` for integration status.

## One product, two gameplay modes

Launch `launch-game.cmd`, open **Game modes**, and choose **Classic** or **Isometric**. Both standalone profiles have 16 country choices, seven authored modern faction packs and six campaigns. Classic currently uses the shared modern army on an original rectangular terrain set; additional mechanics and maps from the historical Classic fork remain a porting task.

The two delivery surfaces are **Downloadable RTS** (Windows EXE installer and portable ZIP; Mac later) and **Web RTS** (`RTSAI-WebGame`, static browser game with direct peer multiplayer, chat and optional calls). The browser Classic profile and complete parity between the two surfaces remain roadmap items. See [the delivery roadmap](../OpenRA-AI/docs/roadmap.md).

The default launcher and standalone Windows package load only project and engine resources. The old owned-content importer and `rtsai-classic` manifest are retained for migration reference, excluded from the standalone package, and are not the dependency-free Classic/top-down mode.

Independent project. EA has not endorsed and does not support this mod.

## Factions

Seven modern factions, each with its own doctrine, signature units and voice lines:

| Nation | Status in this mod |
|---|---|
| China | Playable |
| Iran | Playable |
| Türkiye | Playable |
| Saudi Arabia | Playable |
| Yemen | Playable |
| Israel | Playable |
| Hezbollah | Playable |

These are fictional game factions, not claims about real-world forces. The shared faction catalog (names, roles and stories used by the game and the website) lives in [alibad/OpenRA-AI](https://github.com/alibad/OpenRA-AI/blob/main/catalog/factions.json).

Each modern nation also has its own announcer. Every modern voice is synthetic and made locally with
openly licensed speech models; [docs/audio-provenance.md](docs/audio-provenance.md) lists the engines,
licenses and voices.

All modern-faction art is rendered from the project's own 3D models: 69 prerendered vehicles, ships and aircraft,
28 infantry in faction uniforms, 25 buildings and defenses, and 122 build-menu cameos with name bars.
[docs/art-provenance.md](docs/art-provenance.md) explains how each file is made; the per-file record is
`mods/rtsai/modern-factions/ART-PROVENANCE.json`. What changed in the next alpha:
[docs/release-notes.md](docs/release-notes.md).

## Build and run (Windows)

Requirements: the .NET 10 SDK.

```powershell
.\make.cmd all          # downloads the pinned engine and builds the mod
.\make.cmd test         # rules and YAML checks
.\launch-game.cmd       # start the game
```

For a local engine export: `sh ./fetch-local-engine.sh ../OpenRA-wt-rtsai-engine`, then `.\make.cmd all`. `mod.config` pins the exact engine commit.

A Windows release (per-user installer, portable zip, voice pack) is built on Windows with
`packaging\windows\build-release.ps1`; the first-launch flow, installer options, code signing and the AI
companion host are described in [`docs/first-launch.md`](docs/first-launch.md).

The engine is the slim `rtsai/engine` branch of [alibad/OpenRA](https://github.com/alibad/OpenRA/tree/rtsai/engine): upstream OpenRA bleed plus a few small commits. They add loopback-service hosting for the companion, in-process screenshots, held-key tracking for push-to-talk, a headless platform for automated tests, an interceptor magazine for missile jammers, missiles that follow raised ground and ramps, consistent turret depth, and a fix for a divide by zero between near-equal ramp tilts. `mod.config` pins the exact commit.

## Layout

| Path | Contents |
|---|---|
| `mods/rtsai` | Game rules, maps, chrome and the modern factions (their art: `modern-factions/art-*.yaml` and the `vehicles`, `infantry`, `buildings` and `icons` folders, installed by RTSAI-Art's tools) |
| `mods/rtsai/standalone` | Original terrain, maps, shared buildings/units, effects, sounds, UI and their provenance |
| `resources/` | Preserved legacy source resources and migration inventory; not mounted or shipped as game content |
| `mods/rtsai-content`, `mods/rtsai-classic` | Legacy owned-content references, excluded from standalone distribution |
| `OpenRA.Mods.RA2` | RA2 game logic |
| `OpenRA.Mods.RTSAI` | The AI companion bridge (loopback gRPC), its in-game HUD, and the faction bot doctrines |
| `tools/` | Porting and validation scripts |

The companion's voice and strategy service lives in [alibad/OpenRA-AI](https://github.com/alibad/OpenRA-AI) (`services/companion`).

## License

Code is GPLv3, like the OpenRA engine and the [OpenRA Mod SDK](https://github.com/OpenRA/OpenRAModSDK) this repository is built from. See `COPYING`.
