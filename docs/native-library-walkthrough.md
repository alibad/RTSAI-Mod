# Local native desktop Library — 16 October 2026

Run `launch-game.cmd` in canonical RTSAI-Mod main. This opens the native C#/OpenRA Library. The website/browser edition was not changed or deployed.

| Destination | Identity | Content |
| --- | --- | --- |
| Classic | rtsai-classic-core | Original top-down foundation, existing custom catalogs and original game controls. |
| RA2 | rtsai-ra2 | Existing isometric foundation, original countries, authored campaigns and compatible additions. Standalone artwork is project-authored, not the retail RA2 asset/campaign release. |
| RTS | rtsai | Experimental modern factions and independent setup. |

Each has its own `.recovery/support/Games/<identity>` for settings, saves, maps, replays and imported additions. Migration copies without deleting originals. Customize offers Original/Enhanced/Custom, explanations/dependencies, AI preference and Save setup. Saved matches retain their rules. Full Experience Builder remains in Creator Tools. Not every Classic module has an isometric port; unresolved resources remain preserved in their existing indexed sources.

The game's own settings manage Gameplay/Input/Display/Audio/AI/Hotkeys/Advanced. Display Apply restarts the current game, with Keep/Revert and a 20-second rollback timer. The entry hub has launcher preferences only.

Community complete games use compatible engines and separate support: pinned official portable OpenHV 20250725 and Combined Arms 1.09. Both were installed locally with the native utility worker, length/hash checks and safe staging/extraction. OpenHV's own menu/settings were tested. Combined Arms reaches first-run setup; owner telemetry consent remains pending. Optional missing freeware content belongs to that game's installer.

Add-ons use the existing capability-pack format and an explicit Classic/RA2/RTS target. Cameo, Generals Alpha, RA+, Romanov's Vengeance, Shattered Paradise, OpenRA RA2 and Mod SDK source checkouts are separately preserved/listed. Source code is not silently treated as an installed portable game.

## Reproduce and evidence

Build: `powershell -NoProfile -ExecutionPolicy Bypass -File tools/build-desktop-recovery.ps1`. It fetches/fast-forwards canonical mod and owner engine main, builds a committed immutable snapshot and records SHAs in recovery.local.json/recovery-build.json. Verify with `tools/verify-desktop-recovery.ps1`: profiles, settings/identity isolation, dependencies/extraction boundaries, strict standalone assets and all four mod YAML/map checks.

The engine change is small: seven settings-panel constructors use the existing ISettingsLogic interface. The rest is native mod code/assets. The initial walkthrough was accepted locally before publishing. The subsequent owner-authorized engine publication, matching engine pin and categorized source commits are recorded in [main-publication-20261016.md](main-publication-20261016.md).

Artifact root: `C:/Users/Admin/Code/hq/games/artifacts/desktop-three-games-design-20261016/`.

- `desktop-walkthrough.mp4`: chaptered actual window recordings, local Kokoro am_michael narration. Menu illustrations are distinguished from gameplay.
- `narration-timed.json`, `assemble-walkthrough.py`, raw captures and logs preserve the edit trail.
- `final-verification-b59393f.log`: final full code verification. Compilation has zero warnings/errors. YAML checks retain missing-Fluent-key warnings with readable literal fallback.
- `compare-*.jpg`/focused comparisons and root design-qa.md document native design acceptance.

Tested: all entries, independent setup, native Classic/RA2 construction/production, RA2 campaign listing, seven settings panels, fullscreen Keep/timed rollback, community install and independent launch. Not exhaustively tested: full multiplayer sessions, every authored mission/module combination, arbitrary external add-ons. No retail RA2 restoration or complete Classic-to-RA2 feature port is claimed. Builds and capture artifacts remain local; source publication follows the separate owner request recorded in the category index.
