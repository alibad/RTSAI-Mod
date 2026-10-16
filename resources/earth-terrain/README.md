# Saved battlefield geography

Complete OpenStreetMap Overpass replies, with the exact terrain query, queried coverage, source timestamp and checksums. A site's name/center alone is not terrain evidence. Never infer coverage from feature extents: a river or road can extend beyond the queried box.

Import validated evidence and export the same immutable files to the browser game:

```
node tools/earth-terrain.mjs --payload response.json --query-file query.txt --title Cairo --export ../RTSAI-WebGame/web/public/earth-terrain
```

Data: © OpenStreetMap contributors, [ODbL 1.0](https://www.openstreetmap.org/copyright). Provider data is a dated geographic snapshot, not a representation of current operations. Keep old evidence recoverable when adding new snapshots.
