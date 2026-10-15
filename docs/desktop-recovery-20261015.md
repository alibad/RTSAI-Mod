# Local desktop recovery — 15 October 2026

RTS AI remains a native C# OpenRA product. `launch-game.cmd` is the canonical entry. The locally built
recovery runtime opens a native game library with Classic and RA2 choices. The HTML audit and design
pages are planning artifacts; they do not host the desktop game.

## What was missing from the active desktop

The `rtsai-topdown` profile reused the isometric army on a rectangular grid. It did not reproduce the older
Classic game in `OpenRA/mods/ra`. The older code and content were still present, so this was primarily a
loss of integration and entry points, rather than deletion of the underlying work.

* `mods/rtsai-classic-core` restores the actual older Classic rules, terrain, HUD, maps, seven modern
  faction packs, five saved experience presets and 25 gameplay/authoring modules. It includes the
  existing custom sprites, audio, previews, Lua missions, map-generator definitions and provenance.
* The shared engine restores the Experience Composer, review flow, presentation/capability packs,
  faction catalog, custom gameplay traits, bot parameter hooks, naval mechanics, projectile interception
  and the native Classic Mission Studio and generator command. Default behavior of upstream traits
  remains unchanged unless the recovered mod opts into a component.
* `rtsai` retains the established isometric game, current authored standalone assets, campaigns,
  companion bridge, doctrine AI and audio. It gains an independent composer with modern, original-country
  and original-country-with-combined-arms presets. Country labels refer to gameplay selection; they use
  our existing standalone content, not an installed EA game.
* The experimental `rtsai-topdown` work remains preserved. The historical `rtsai-classic` is an optional
  **owned RA2 content add-on**, not the restored top-down Classic mode. Neither is offered as the default
  Classic choice.

## What is preserved, and where

No source checkout, worktree, archive, model library or user installation was retired or deleted.
The audit is `../artifacts/desktop-recovery-audit-20261015/`, including `audit.json`, `verification.json`,
`preserved-resources.csv`, `installed-resources.csv`, `maps.csv`, `components.csv` and `custom-classes.csv`.

The canonical preservation archive remains `resources/preserved/legacy-custom-resources-20261009.zip`:
all 5,104 entries were hash-checked. All 12,413 indexed RTSAI-Art files exist. The installed-content snapshot
has 3,796 unchanged files, 219 intentional updated files and four obsolete tree PNGs superseded by the
current tree library. Those earlier versions remain in the preservation archive. Branch variants retain
176 verified file objects and six recorded deletions.

Source models, procedural generators, map evidence, unused variants and unresolved art provenance remain
in RTSAI-Art and the preservation indexes. Preservation is not a claim that every archived resource is
integrated or cleared for redistribution. Unmerged vision/map-generation branch work remains indexed at
its original worktree; it has not been silently described as part of this recovery build.

## Settings and content

Display mode, monitor, resolution, UI scale and audio use OpenRA's actual native settings. Controls,
scrolling, camera distance, status bars, target lines, unit-voice preference and experience selections
are kept per mode. Native hotkeys and skirmish preferences use the mod's own settings namespace.

The local build copies relevant player data from the existing roaming OpenRA support directory and the
older `OpenRA/Support` into `.recovery/support`. Original files remain untouched. Classic profiles,
hotkeys and skirmish preferences are copied to the new Classic mod ID. Conflicting source copies remain
available in their original installations.

Authentic Classic currently uses the already installed OpenRA freeware Red Alert data, plus our custom
content. It needs no owned Red Alert installation. Its installer can acquire the OpenRA freeware package
if that data is absent. RA2's default mode remains standalone and passes the strict no-owned-content
asset/audio check. This local recovery does not bundle or distribute the original game data.

## Optional community packs

OpenHV, Combined Arms, RA+, Generals Alpha, Shattered Paradise, Romanov's Vengeance, OpenRA RA2 and Cameo
remain downloaded source references under `OpenRA-Upstreams`. ModSDK is tooling. Complete game mods need
their own compatible engine/content/runtime packaging; they are not interchangeable toggles inside RA2.
Small data modules may use the existing capability-pack contract after compatibility and provenance
review. The native pack library labels these projects as pending, without offering fake download buttons.

## Build, verify and launch locally

```
powershell -NoProfile -ExecutionPolicy Bypass -File tools/build-desktop-recovery.ps1
make.cmd test
launch-game.cmd
```

The build fetches both remotes, checks clean committed inputs and produces a runtime keyed by the local
mod and engine commits. `recovery.local.json` points the launcher to that exact build. The remote
`mod.config` engine pin is deliberately unchanged: the recovery engine is local and has not been pushed.
With the local override present, `make.cmd all` and `make.cmd test` use the recovery workflow.

`tools/recovery-smoke.py` checks real rendered windows, switches modes through the real handlers, and
records actor censuses for requested bot factions. Its support files are isolated from player settings.
The native generator also validates tracked-unit reachability between spawns. The Mission Studio requires
the existing local companion/world-generation service for Earth retrieval and generation; the game remains
playable while those optional services are unavailable.

## Relationship to the web

RTSAI-Web remains the website; RTSAI-WebGame remains the separate browser runtime. The shared catalog and
companion contracts connect those surfaces to the native game. A shared source contract does not mean
the browser has automatically received the restored desktop features. No website or browser build was
published, deployed or released as part of this local recovery.

## Verification boundaries

Rendered Classic and RA2 matches, real bidirectional mode switches, native settings, composer popups and
all eight built-in profile rule sets are checked. Full campaign lint catches broken rules, references and
script interfaces; it does not prove every campaign's victory/defeat path or balance. Source recovery and
smoke matches do not establish competitive balance. Keep the preserved older engine and archives until
the owner has reviewed the actual game.
