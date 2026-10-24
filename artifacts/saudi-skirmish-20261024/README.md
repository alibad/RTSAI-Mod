# Saudi Arabia skirmish acceptance — 24 October 2026

Saudi Arabia (Red Sea Command) versus Iran on Twin Fords is the first focused modern-faction acceptance slice. Both platforms use the same 34-entry Saudi roster, rules and art. The accepted local build is `studio-20261024-001242-eacc038b`, game source `8b03957`, engine `f158a224d52b16359ed3c0d643f0f0f5ec53f2c5`, content revision `aac51015616427013190ddba51af8d73bd371818ab2db8583306e728cb86d39b`.

## What changed

- Saudi bots now issue ordinary Guard deploy orders when stationary and aiming. The existing move order releases their braced stance. Human Guards remain manually controlled. Normal, Easy, Rush, Turtle and Naval bot profiles are covered.
- The legacy `medium` profile was identical to Normal. It is now explicitly **Easy AI (60% firepower)**, with slower production/attack decisions and a higher cash reserve. This is a visible training handicap, not a hidden buff to the player's units. It applies wherever this shared bot profile is offered; competitive validation here covers Saudi versus Iran only.
- The browser calls the picker **AI profile**. Rush is an aggressive strategy, not a promise of a universal higher difficulty. Bot labels now come from the authoritative desktop localization instead of a stale copied web list.
- The canonical desktop launcher can select a mode while retaining receipt verification and the return-to-Library path. `launch-saudi-skirmish.cmd` starts Saudi versus Normal Iran directly; `-Difficulty medium` or `-Difficulty rush` selects the other tested opponents.

## Play locally

- Desktop: run `C:/Users/Admin/Code/hq/games/RTSAI-Mod/launch-saudi-skirmish.cmd`. The wrapper was exercised against the accepted build: first-run setup, Saudi starting units, approved MCV deployment, production icons and the pause/objectives screen all rendered correctly. A fresh Saudi-versus-Normal-Iran match was left paused.
- Browser: `http://127.0.0.1:52099/local-builds/studio-20261024-001242-eacc038b/?runtime=interp&profile=public&mode=skirmish&map=twin-fords`. The prepared tab has Saudi, Normal Iran, $5,000, medium forces, fog, unrevealed terrain and crates off. These URL parameters choose the page/map; other setup choices are visible UI state, so recheck them on a fresh tab.
- The desktop quick launch uses the mod's map/lobby defaults: $5,000, medium forces, fog, unrevealed terrain, and supply crates enabled. The browser batch explicitly disables crates. Consequently the separate pacing samples are not a controlled platform-versus-platform timing comparison.

## Evidence

`results.json` separates the 54 pre-brace baseline games from the 12 post-brace games. All games use ordinary bots, both spawn orientations and full conquest resolution. The native harness adds passive telemetry and accelerates wall-clock ticking; durations below are normalized to 25 ticks/second.

| Check | Result |
| --- | --- |
| Accepted shared build | Classic and isometric, desktop and actual WASM verification passed; saved unit edits preserved |
| Saudi resolved roster | 34 entries, zero differences in exported desktop/web actor facts |
| Art bytes | 88 SHP/palette/image files identical; no replacement artwork introduced |
| Sprite inspection | Eight core ground/infantry units on a contact sheet; Abrams hull/turret cardinal handedness and 32 unique facings checked |
| Effects in accepted build | 228 death and 97 impact cases, zero failures |
| Guard mechanics | All five bot profiles brace; move releases; human negative control passes |
| Baseline desktop | 36 games: 27 conquest, nine 40-minute caps, zero crashes |
| Baseline web host (CoreCLR) | 18 games: 16 conquest, two caps, zero crashes |
| Post-brace desktop | Six games: six conquest, no caps/crashes; 6.8–34.3 minutes, median 15.2 |
| Post-brace web host (CoreCLR) | Six games: six conquest, no caps/crashes; 9.8–36.8 minutes |
| Actual browser full skirmish | Pre-brace build: Saudi victory; all 61,178 exported WASM tick hashes match native replay |
| Actual browser new code | Accepted build's bracing fixture: all 11,766 exported WASM tick hashes match native replay; visible actors and combat, no browser warnings/errors |
| Harness regression checks | Seven tests passed, including swapping factions together with their bot profiles |

The full browser victory and the short new-code fixture are distinct evidence. The latter is a mechanics/rendering/replay check, not a second full skirmish. The 12 full post-brace games run native desktop and the web simulation under CoreCLR, not 12 browser sessions.

In the post-brace sample, Easy Iran lost all four matches to Normal Saudi, Normal Iran won one of four, and Rush Iran won all four. That is an encouraging separation, not a statistically established difficulty ladder. Bot decisions use local randomness: independent seeded scenarios are samples, not deterministic paired A/B experiments. Exported order logs plus tick hashes are reproducible.

## Reproduce and inspect

- Native batch: `tools/balance-harness.py run --campaign saudi --campaigns-file artifacts/saudi-skirmish-20261024/difficulty-campaign.json --standalone --limit 6 --engine <accepted-build>/native --mods <accepted-build>/native/mods --output <new-output> --parallel 2 --bot-log`.
- Web host batch: `python artifacts/saudi-skirmish-20261024/run-web-suite.py <accepted-build> <new-output> --runner <websim.dll> --replicates 1`.
- Mechanics: `dotnet <websim.dll> saudibracetest --root <accepted-build>/vfs-public`.
- Effects: `dotnet <websim.dll> effectsaudit --root <accepted-build>/vfs-public --factions saudi --out <file.json>`.
- Actual browser recording: use Saves & replays → Save → Export, then `verify-browser.py <accepted-build> <export.json> <new-output> --runner <matching-websim.dll>`; this requires every hash and the lengths to agree.
- `audit-art.py <accepted-build>` compares frozen native/web bytes and extracts the contact sheet without modifying sprites.
- Raw replays, samples, screenshots, sprite exports, build provenance and rejected experiments are retained at `D:/RTSAI-SaudiSkirmish-20261024`. Accepted build/receipt: `D:/RTSAI-StudioPreviews/20261024-001242-eacc038b/receipt.json`.

The native campaign uses six replicates by default (36 games); `--limit 6` selects one balanced six-game pass. `run-web-suite.py` defaults to three replicates (18 games). Existing result files are preserved for resumption; use a new output directory for a fresh sample. `summarize.py` reads the named evidence batches from the retained local audit directory.

## Remaining limits

This is a test-ready local skirmish slice, not a certification of every faction/map or multiplayer balance. The smaller post-fix sample does not prove that long stalemates are eliminated. Additional naval maps, larger player counts, human playtests and sustained browser performance remain separate validation work. Art is consistent across the two builds; this pass does not replace the full art direction or validate every animation in every situation. Artillery-share and infantry-share experiments were rejected and are retained only as audit material.

Source changes are committed on canonical main; source pushes deploy neither the mod nor WebGame. No website push, production deployment or public game release belongs to this acceptance.
