# Earth site snapshots

Canonical, public geographic evidence for the browser game's Earth studio. The collector is `../../tools/earth-sites.mjs`.

`regions/` preserves normalized site records and acquisition/coverage metadata. `sources/` preserves the actual provider replies. `packs/` contains immutable content-addressed JSON; `manifest.json` is the small index. Export to `RTSAI-WebGame/web/public/earth-sites` for browser delivery. Do not delete old pack versions merely because a newer manifest exists.

This initial dataset is a bounded set of known references, not every site on Earth. It contains public OpenStreetMap and Wikipedia coordinates/names, with individual source links and dates. Mapped military tags do not establish current occupancy, force positions, conflict status or operational activity.

OpenStreetMap records are © OpenStreetMap contributors under ODbL-1.0: https://www.openstreetmap.org/copyright . Wikipedia geographic metadata is factual; linked article text retains its own license. Article prose and thumbnails are not copied into these packs. The preserved local OSM reply has unknown original query bounds, so it carries no full-region coverage assertion.

Normal builds use these saved files without calling any public API. A maintainer can explicitly collect named preset regions, or import an attributed saved Overpass response. Failed providers retain previous good records. Keep collection bounded and preserve provenance when extending the catalog.
