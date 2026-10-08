# RTS AI product direction — 9 October 2026

RTS AI is a standalone OpenRA game. Players do not need to own, buy, install or import Red Alert or Red Alert 2.

Keep both Classic/top-down and RA2/isometric gameplay, with a single product entry and an in-game mode choice. These names describe the gameplay families, not a promise to ship the original games' assets or campaigns.

## Current implementation

The standalone isometric content has been consolidated into the canonical `RTSAI-Mod` checkout: seven modern factions, original terrain and maps, shared base/units, effects, sounds, cursors, palettes and UI. The default manifest mounts project and engine packages only. The strict standalone check rejects missing or placeholder art for fieldable actors and imported commercial content paths. Windows packaging ships only that mod.

The old dual-game build and its Classic/top-down custom resources are retained. The combined mode chooser is not yet ported into this Mod SDK project. This is remaining integration work, not an owned-content prerequisite for the playable standalone game.

The historical `rtsai-classic` manifest means an optional owned-RA2 add-on. It is not the Classic/top-down mode. It and the content importer remain migration references and are not included in standalone packages. No player should be instructed to install them to play RTS AI.

## Resource preservation

- Preserve installed custom faction assets and the original-content assets with their per-file provenance.
- Preserve RTSAI-Art's models, candidates, review history and generation tools; it remains the editable art source library.
- Inventory legacy Classic assets and WIP variants by source and SHA-256 in `resources/resource-transition.json`. Preserve unique legacy bytes in the local `resources/preserved/` archive, outside runtime mounts and release packaging. An added or modified legacy file is not automatically licensed for distribution; provenance review precedes activation.
- Port compatible resources into the appropriate game mode; preserve earlier variants as sources/history. Never overwrite a reviewed current asset with an older sprite merely to flatten folders.
- Preserve all original repositories/worktrees until unique files, source models, generators and review evidence have a verified destination. No cleanup is part of this transition.

## Remaining Classic integration

Port the Classic rules, faction definitions, missions, catalog UI and companion behavior into the canonical mod architecture. Resolve top-down art and terrain independently of the isometric renderer. Replace any original-game file dependency with project-made or appropriately licensed content. Reintroduce the mode chooser, then verify both modes with empty content folders. Do not call an archived resource runtime-integrated until its manifest, sequences, rules and gameplay are checked.

Build and verification remain local. No hosted CI workflow is added, and no website deployment or release publishing is implied.
