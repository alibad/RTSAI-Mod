# RTS AI

**A Red Alert 2 mod for [OpenRA](https://www.openra.net): five modern nations and an AI co-commander.**

The co-commander watches your match, speaks up when it matters, answers spoken questions, and takes command only when you switch AUTO on. It sees only what you can see.

Status: **in development.** The current public release is the OpenRA AI Classic alpha at [rtsai.net](https://rtsai.net). This repository is where the Red Alert 2 mod is being built. See `MIGRATION.md` for progress.

## You need your own Red Alert 2

This mod does not include any Command & Conquer: Red Alert 2 game data, and never will. On first launch, the content installer imports the copy you own from any of these:

- Steam (Command & Conquer: The Ultimate Collection)
- the EA app or Origin
- the original disc or The First Decade

Independent project. EA has not endorsed and does not support this mod.

## Factions

The original RA2 countries plus modern nations, each with its own doctrine, signature units and voice lines:

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

Until the pinned engine commit is published (see the push-order note at the top of `MIGRATION.md`), export it from a
local engine checkout first: `sh ./fetch-local-engine.sh ../OpenRA-wt-rtsai-engine`, then `.\make.cmd all`.

A Windows release (per-user installer, portable zip, voice pack) is built on Windows with
`packaging\windows\build-release.ps1`; the first-launch flow, installer options, code signing and the AI
companion host are described in [`docs/first-launch.md`](docs/first-launch.md).

The engine is the slim `rtsai/engine` branch of [alibad/OpenRA](https://github.com/alibad/OpenRA/tree/rtsai/engine): upstream OpenRA bleed plus a few small commits. They add loopback-service hosting for the companion, in-process screenshots, held-key tracking for push-to-talk, a headless platform for automated tests, an interceptor magazine for missile jammers, missiles that follow raised ground and ramps, consistent turret depth, and a fix for a divide by zero between near-equal ramp tilts. `mod.config` pins the exact commit.

## Layout

| Path | Contents |
|---|---|
| `mods/rtsai` | Game rules, maps, chrome and the modern factions (their art: `modern-factions/art-*.yaml` and the `vehicles`, `infantry`, `buildings` and `icons` folders, installed by RTSAI-Art's tools) |
| `mods/rtsai-content` | The content installer that imports owned RA2 data |
| `OpenRA.Mods.RA2` | RA2 game logic |
| `OpenRA.Mods.RTSAI` | The AI companion bridge (loopback gRPC), its in-game HUD, and the faction bot doctrines |
| `tools/` | Porting and validation scripts |

The companion's voice and strategy service lives in [alibad/OpenRA-AI](https://github.com/alibad/OpenRA-AI) (`services/companion`).

## License

Code is GPLv3, like the OpenRA engine and the [OpenRA Mod SDK](https://github.com/OpenRA/OpenRAModSDK) this repository is built from. See `COPYING`.
