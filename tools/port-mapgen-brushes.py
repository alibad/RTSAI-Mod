#!/usr/bin/env python3
"""Port the Tiberian Sun map generator's terrain data to the RTS AI temperate tileset.

The RA2-compatible template table we use descends from Tiberian Sun's: its cliff set, shore pieces, cliff/water
pieces, slope set pieces, water and ramp edge fixups come in the same order with the same shapes (size, tile slots,
heights, ramps). So the engine's own TS data, written for TS template ids, describes our templates once the ids are
mapped. This writes, for tools/standalone-terrain.py to apply when it writes the tileset:

  tools/terrain/mapgen-brushes.yaml  the tileset's MultiBrushCollections (cliffs, beaches, water cliffs, water)
  tools/terrain/mapgen-risers.json   per-tile Riser heights (how a cliff tile's corners meet its neighbours)
  tools/terrain/mapgen-lat.yaml      ramp edge fixup rules for the generator's LatTiler

Only templates whose shape matches exactly are mapped; brushes on any other template are left out and listed.

  python tools/port-mapgen-brushes.py --ts <engine>/mods/ts/tilesets/temperate.yaml [--apply]

--apply also rewrites mods/rtsai/standalone/tilesets/temperat.yaml in place (no re-render needed).
"""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TILESET = ROOT / "mods/rtsai/standalone/tilesets/temperat.yaml"
OUT = ROOT / "tools/terrain"

# (TS category, our category). Pairs are matched in id order; a pair is used only if the shapes agree.
CATEGORIES = [("Cliff Set", "Cliff Set"), ("Shore Pieces", "Shore Pieces"), ("Cliff/Water pieces", "Cliff/Water pieces"),
              ("Slope Set Pieces", "Slope Set Pieces"), ("Water", "Water"), ("Ramp edge fixup", "Ramp edge fixup")]
# TS's flat ramps (40-57, RampType 1-18) and ours (29-46) differ only by offset; the ramp edge rules refer to them.
RAMPS = {ts: ts - 11 for ts in range(40, 58)}
# Slope set pieces whose shape differs from TS's only in one tile's ramp (TS 408 tile 1 and TS 411 tile 5 slope, ours
# are flat). They are the cliff end caps facing right and down: without them no cliff can end in those directions.
NEAR = {408: 389, 411: 392}

# Collections the generator reads that are not ported from TS (our actors; see rules/map-generators.yaml).
OWN_COLLECTIONS = """	Trees:
		FromActors: tree01,tree02,tree03,tree04,tree05,tree06,tree07,tree08,tree09,tree10,tree11,tree12,tree13,tree14,tree15,tree16,tree17,tree18,tree19,tree20,tree21,tree22,tree23,tree24,tree25,tree26,tree27,tree28
	Obstructions:
		FromActors: tree01,tree02,tree03,tree04,tree05,tree06,tree07,tree08
	CivilianBuildings:
		FromActors: cahse01,cahse02,cahse03,cahse04,cahse05,cahse06,cahse07,cabarn02
"""


def templates(text):
    body = text.split("\nTemplates:\n", 1)[1].split("\nMultiBrushCollections:", 1)[0]
    out = {}
    for m in re.finditer(r"\tTemplate@(\d+):\n((?:\t\t.*\n?)+)", body):
        b = m[2]
        size = tuple(int(x) for x in re.search(r"\t\tSize: (\d+), ?(\d+)", b).groups())
        tiles = {}
        for t in re.finditer(r"\t\t\t(\d+): (\S+)\n((?:\t\t\t\t.*\n?)*)", b):
            h, r, s = (re.search(rf"\t{k}: (.+)", t[3]) for k in ("Height", "RampType", "Riser"))
            tiles[int(t[1])] = dict(height=int(h[1]) if h else 0, ramp=int(r[1]) if r else 0, riser=s[1].strip() if s else None)
        out[int(m[1])] = dict(cat=re.search(r"\t\tCategories: (.*)", b)[1].strip(), size=size, tiles=tiles)
    return out


def shape(t):
    return t["size"], tuple(sorted((i, v["height"], v["ramp"]) for i, v in t["tiles"].items()))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ts", type=Path, required=True)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    ts_text = args.ts.read_text(encoding="utf-8")
    ts, ours = templates(ts_text), templates(TILESET.read_text(encoding="utf-8"))

    ids = dict(RAMPS) | NEAR
    for tc, oc in CATEGORIES:
        a = sorted(k for k, t in ts.items() if t["cat"] == tc)
        b = sorted(k for k, t in ours.items() if t["cat"] == oc)
        for x, y in zip(a, b):
            if shape(ts[x]) == shape(ours[y]):
                ids[x] = y

    # Segmented brushes and the water collection, with our template ids.
    collections = ts_text.split("\nMultiBrushCollections:\n", 1)[1]
    out, dropped = ["MultiBrushCollections:\n"], []
    for name, body in re.findall(r"(?m)^\t(\w+):\n((?:\t\t.*\n?)*)", collections):
        if name not in ("Segmented", "Water"):
            continue
        lines = [f"\t{name}:\n"]
        for brush, bb in re.findall(r"\t\tMultiBrush@(\S+):\n((?:\t\t\t.*\n?)+)", body):
            used = [int(t) for t in re.findall(r"Template: (\d+)", bb)]
            if any(t not in ids for t in used):
                dropped.append(brush)
                continue
            # Template-less brushes connect segment types and are the same for every tileset. Others are named after
            # their kind (Cliff, Shore, Shore_WaterCliff, ...) and our template ids.
            kind = "_".join(p for p in brush.split("_") if not p.isdigit()) or "Water"
            name_ids = "_".join(str(ids[t]) for t in used)
            lines.append(f"\t\tMultiBrush@{kind + '_' + name_ids if used else brush}:\n"
                         + re.sub(r"Template: (\d+)", lambda m: f"Template: {ids[int(m[1])]}", bb))
        from_templates = re.search(r"\t\tFromTemplates: (.*)", body)
        if from_templates:
            src = [int(x) for x in from_templates[1].split(",")]
            lines.insert(1, "\t\tFromTemplates: " + ", ".join(str(ids[x]) for x in src if x in ids) + "\n")
        out.extend(lines)
    out.append(OWN_COLLECTIONS)
    brushes = "".join(out)

    # Risers: TS tile -> our tile in the same slot.
    risers = {}
    for x, y in ids.items():
        if x in ts and y in ours:
            for slot, tile in ts[x]["tiles"].items():
                if tile["riser"] and slot in ours[y]["tiles"]:
                    risers.setdefault(str(y), {})[str(slot)] = tile["riser"]

    # Ramp edge fixups (TS LatTiler rules RampEdge40-43) with our ids.
    gen = (args.ts.parents[1] / "rules/map-generators.yaml").read_text(encoding="utf-8")
    rules = re.findall(r"(\t+Rule@RampEdge\d+:\n(?:\t+(?:AutoMain|Low|[_x]{4}):.*\n)+)", gen.split("Choice@snow")[0])
    def remap(m):
        return m[1] + ", ".join(str(ids[int(v)]) for v in m[2].split(","))
    lat = "".join(re.sub(r"(?m)^(\t+(?:Low|[_x]{4}): )([\d, ]+)$", remap, r) for r in rules)
    lat = re.sub(r"Rule@RampEdge(\d+)", lambda m: f"Rule@RampEdge{ids[int(m[1])]}", lat)

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "mapgen-brushes.yaml").write_text(brushes, encoding="utf-8", newline="\n")
    (OUT / "mapgen-risers.json").write_text(json.dumps(risers, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    (OUT / "mapgen-lat.yaml").write_text(lat, encoding="utf-8", newline="\n")
    kinds = {}
    for k in re.findall(r"MultiBrush@(\w+?)_\d+", brushes):
        kinds[k] = kinds.get(k, 0) + 1
    print(f"mapped {len(ids)} templates; brushes {kinds}; dropped {len(dropped)}: {' '.join(dropped)}")
    print(f"risers on {sum(len(v) for v in risers.values())} tiles of {len(risers)} templates; {len(rules)} ramp edge rules")

    if args.apply:
        TILESET.write_text(apply(TILESET.read_text(encoding="utf-8"), brushes, risers), encoding="utf-8", newline="\n")
        print(f"applied to {TILESET.relative_to(ROOT)}")


def apply(text, brushes, risers):
    """The tileset with these brush collections (replacing any) and Riser lines on the mapped tiles."""
    text = text.split("\nMultiBrushCollections:", 1)[0].rstrip("\n") + "\n\n" + brushes

    def template(m):
        tid, block = m[1], m[0]
        if tid not in risers:
            return block

        def tile(t):
            body = re.sub(r"(?m)^\t\t\t\tRiser: .*\n", "", t[3])
            riser = risers[tid].get(t[1])
            return f"\t\t\t{t[1]}: {t[2]}\n" + (f"\t\t\t\tRiser: {riser}\n" if riser else "") + body
        return re.sub(r"\t\t\t(\d+): (\S+)\n((?:\t\t\t\t.*\n?)*)", tile, block)
    return re.sub(r"\tTemplate@(\d+):\n(?:\t\t.*\n?)+", template, text)


if __name__ == "__main__":
    main()
