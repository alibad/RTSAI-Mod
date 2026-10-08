# RTS AI product direction — 9 October 2026

One standalone OpenRA game, two delivery surfaces: **Web RTS** and **Downloadable RTS**. Neither requires owning, buying, installing or importing Red Alert or Red Alert 2. Windows first; macOS follows on the owner's Mac.

The canonical checkout is `RTSAI-Mod` main. Launch `launch-game.cmd`, open **Game modes**, and select **Classic** or **Isometric**. Windows packages expose the same choice in `RTSAI.exe`.

- `rtsai`: RA2/isometric grid and presentation.
- `rtsai-topdown`: Classic/rectangular grid, original square terrain and two skirmish maps.
- Both share seven modern army packs, nine restored historical country rule sets, project-owned replacement assets, six campaign maps and native AI companion integration.
- Campaign objectives use simulation ticks, the normal mission panel, civilian convoy orders, enemy waves and difficulty. Coordinates and terrain are converted for each grid.
- All 16 choices pass strict standalone checks: no missing audio or placeholder art for fieldable units and no owned-content mounts. Some countries share reviewed art and voice families.

This Classic profile presents shared modern army rules on a rectangular grid. It does not reproduce every mechanic, map or visual from the earlier Classic fork. Those sources are preserved; additional ports remain roadmap work.

Windows `0.4.0-alpha.1` has an NSIS per-user EXE installer and portable ZIP, with the frozen local companion, catalog and inference runtimes. It is not an MSI. Models are optional downloads, not embedded; model-dependent speech/reasoning needs those downloads. Native bots and existing non-model fallbacks remain available. Local builds are unsigned.

The historical `rtsai-classic` manifest is an owned-RA2 migration reference. It is not the shipped Classic mode and is excluded from packages alongside the importer.

`resources/resource-transition.json` indexes 5,104 legacy entries and 4,019 original-content resources. Earlier installed hashes are preserved when authored resources change. RTSAI-Art retains editable models, candidates, generators and review history on main. All-ref bundles and dirty-file snapshots are under `D:/rtsai-consolidation/20261009`.

Never replace reviewed assets with older variants just to flatten folders. Activate archived resources after checking provenance, manifests, sequences, rules and gameplay. Preserve original worktrees until unique work has a verified destination.

The delivery plan is `OpenRA-AI/docs/roadmap.md`. Build and verification stay local; public distribution and production deployment are separate actions.
