# Local web map studio

The web surface has **Map studio** at the main menu and skirmish setup. The generators, original mode ports and source inventory live in this canonical checkout. No owned Red Alert installation or original-game artwork is used by the added maps.

## Map library

`tools/catalog-web-maps.py` indexes folder maps and `.oramap` archives from the canonical mod, preserved worktrees, Classic OpenRA, the companion's missions/generated missions, the browser content and the nested upstream mod checkouts. The current inventory has **466 unique maps / 1,277 source copies**, plus dynamically listed Earth workshop creations. Content hashes group duplicates; source paths stay visible.

The library distinguishes available maps from sources that need a provenance or mode port review. It does not silently load third-party rules, Lua missions, actor sets or tilesets into the web engine. An indexed source is not a claim of integration. Existing campaign adaptations remain accessible through Missions.

Two additional, project-authored skirmishes are available: **Classic Coast · Isometric** and **Classic Frontier · Isometric**. Their original rectangular layouts come from `tools/build-classic-mode.py`; `resources/web-maps/port-classic-*` translates their terrain, resource cells and spawns to the project's isometric terrain. The original Classic maps remain intact. These are adaptations, not a switch to a Classic renderer.

Run the inventory/port builder with Python containing NumPy and Pillow:

```powershell
python tools/catalog-web-maps.py
```

## Earth workshop

1. Choose a preset or latitude/longitude and area radius.
2. **Read this area** obtains OpenStreetMap ways. A north-up vector preview shows roads, waterways, land cover and building footprints. The source status distinguishes current acquisition from preserved local evidence.
3. **Generate battlefield** compiles project terrain using `tools/earth-battlefield.py` and the canonical `standalone-maps.py` corner-transition compiler. The adjacent preview is the resulting game's terrain, not a satellite mockup.
4. **Use this map** reloads the web worker, mounts its files before the map cache scans, and selects the map in skirmish setup. **Download map** exports an attributed `.oramap`.

Maps and evidence persist in `resources/earth-maps/earth-<content-hash>/`. This local directory is ignored by Git, not discarded. Each successful map retains `request.json`, `earth.json`, tile binary, YAML, preview and archive. The library indexes successful generated packages dynamically. Failed attempts are not advertised as playable. Review geographic data and licensing before distributing a generated package.

The compiler preserves evidence where possible but deliberately clears base zones, adds ground corridors and equal home ore mines. It simplifies buildings to rough ground and vegetation to terrain. It does not reproduce elevation, individual real buildings, satellite photography or unbounded seas inferred from open coastlines. These changes appear beside the result. Seeded rough terrain supplies deterministic variation.

OpenStreetMap data is attributed and licensed under [ODbL](https://www.openstreetmap.org/copyright). Source services can be unavailable or reject very dense areas; failures are explicit, with no invented geography fallback. Previously saved geographic evidence is reusable offline. Place lookup is not implemented through public Nominatim. Coordinates and presets remain available, with a link to explore the selected location on OpenStreetMap.

## Local adapter and verification

`RTSAI-WebGame/server/map-workshop.mjs` provides the loopback-only library, package, evidence and generation APIs. Python can be selected with `RTSAI_MAP_PYTHON`; the local bundled Python is detected on this development machine. `RTSAI_OVERPASS_URL` can select another geographic endpoint. Public static builds hide the local studio and use their bundled maps. Older local servers returning an HTML homepage for the new API retain their bundled map catalog.

The native replay verification path mounts the same reviewed/generated packages. Room joins and spectators reject mismatching local map catalogs rather than attempting an unknown terrain package.

Validated locally:

- TypeScript and Vite production build.
- `tools/test-earth-battlefield.py`: deterministic binary terrain, four player definitions, connected base-cell routes, eight home mines, binary layout and invalid-coordinate rejection.
- Native Classic Coast and Cairo Crossing runs: 300 ticks, rendering snapshots and zero unsupported renderables; Classic Frontier additionally checked natively.
- Live OpenStreetMap acquisition for a 500 m Cairo district, containing 337 geographic ways across roads, buildings, parks, urban areas and Nile water features; browser generation, preview, selection and actual AOT match launch.
- Room API tests including local map library mismatch rejection for players and spectators.

The final local studio preview uses the interpreter runtime, whose asset manifest hashes all match. During concurrent local runtime publication, the shared AOT folder became inconsistent (56 asset hash mismatches), causing integrity-protected browser downloads to fail. The earlier AOT Cairo launch succeeded before that update; no unrelated runtime files were overwritten to repair it.

The compiler's route check uses conservative terrain-cell connectivity and wide cleared corridors. It is not a proof of every unit's naval, air or special locomotor behavior. A map can contain more water than is useful for a particular faction; preview before launching.
