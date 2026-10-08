#!/usr/bin/env python3
"""Exact replacement lists for the Phase 3 art agent and the audio agent: docs/standalone-deliverables.json.

Input: an audit of the classic add-on with the player's RA2 content mounted (it reaches every file the modern
factions use, and shows which ones are EA):

  python tools/standalone-audit.py --mod rtsai-classic --content ../OpenRA/Support/Content --out <s>/classic.json
  python tools/standalone-deliverables.py --audit <s>/classic.json

Everything listed is an EA file that the 7 modern factions reach in a skirmish today; deliveries keep these exact
file names (and, for sprites, at least these frame counts) unless the entry says otherwise. Names, frame counts and
frame sizes only; no EA data.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "standalone-deliverables.json"
MODERN = ["china", "iran", "turkey", "saudi", "israel", "yemen", "hezbollah"]
ALLIED_SIDE = ["china", "turkey", "saudi", "israel"]
SOVIET_SIDE = ["iran", "yemen", "hezbollah"]

# Base kit: one original design per role, painted per faction (art agent proposal of 7 Oct, accepted).
KIT = {
    "cnst": {"footprint": "4x4", "allied": "gacnst", "soviet": "nacnst"},
    "powr": {"footprint": "2x2", "allied": "gapowr", "soviet": "napowr", "note": "napowr is 3x2 today; standalone rules move it to 2x2"},
    "refn": {"footprint": "4x3", "allied": "garefn", "soviet": "narefn", "note": "dock column like garefn"},
    "barr": {"footprint": "3x2", "allied": "gapile", "soviet": "nahand", "note": "nahand is 2x2 today; standalone rules move it to 3x2"},
    "weap": {"footprint": "5x3", "allied": "gaweap", "soviet": "naweap"},
    "radr": {"footprint": "2x2", "allied": None, "soviet": "naradr", "note": "radar for the Soviet-side factions"},
    "airf": {"footprint": "3x2", "allied": "gaairc", "soviet": None, "note": "airfield + radar for the Allied-side factions"},
    "yard": {"footprint": "4x4", "allied": "gayard", "soviet": "nayard", "note": "on water"},
    "dept": {"footprint": "3x3", "allied": "gadept", "soviet": "nadept", "note": "nadept is 4x3 today; standalone rules move it to 3x3"},
    "tech": {"footprint": "3x2", "allied": "gatech", "soviet": "natech", "note": "natech is 3x3 today; standalone rules move it to 3x2"},
    "sw1": {"footprint": "4x3", "allied": "gacsph", "soviet": None, "note": "replaces the Chronosphere's art; the power itself is a later rules decision"},
    "sw2": {"footprint": "3x3", "allied": None, "soviet": "nairon", "note": "replaces the Iron Curtain's art; the power itself is a later rules decision"},
    "wall": {"footprint": "1x1", "allied": "gawall", "soviet": "nawall", "note": "connecting wall: keep the stock wall frame layout (16 connection frames + damaged)"},
}
CUT = ["gaorep", "gagap", "gaspysat", "gaweat", "nanrct", "napsis", "naclon", "namisl"]
UNIT_GROUPS = {
    "mcv": ["amcv", "smcv"], "harvester": ["cmin", "harv"], "engineer": ["engineer"], "dog": ["dog"], "spy": ["spy"],
    "flameguy": ["flameguy"], "aa-track": ["htk"], "amphibious-transport": ["sapc"], "landing-craft": ["lcrf"],
}


def build(audit: dict) -> dict:
    files, imf = audit["sprites"]["files"], audit["sprites"]["imageFiles"]
    isrc = audit["sprites"]["imageSources"]
    seqs = audit["sprites"]["tilesets"]["TEMPERATE"]["imageSequences"]
    acts, reach = audit["actors"], audit["reachable"]
    models = audit["models"]["images"]
    modern = defaultdict(set)
    for f in MODERN:
        for x in reach[f]["actors"]:
            modern[x].add(f)

    def group(img):
        return isrc.get(img, ["?"])[0].split("|")[-1]

    def sprite(f):
        r = files.get(f, {})
        return {"file": f, "frames": r.get("frames"), "w": r.get("w"), "h": r.get("h")}

    def own_images(x):
        return [i for i in acts[x]["images"] if i in imf and group(i) != "sequences/misc.yaml"]

    def image_entry(img):
        return {"image": img, "sequences": {s: [f for f in fl if files.get(f, {}).get("by") == "ea"]
                                            for s, fl in seqs.get(img, {}).items()},
                "ea_files": [sprite(f) for f in imf.get(img, []) if files.get(f, {}).get("by") == "ea"]}

    kit = {}
    for role, k in KIT.items():
        kit[role] = {**k, "factions": (ALLIED_SIDE if k["allied"] else []) + (SOVIET_SIDE if k["soviet"] else []),
                     "replaces": {a: [image_entry(i) for i in own_images(a)] for a in (k["allied"], k["soviet"]) if a}}

    units = {}
    for name, actors in UNIT_GROUPS.items():
        units[name] = {"actors": actors, "factions": sorted(set().union(*(modern[a] for a in actors))),
                       "images": {a: [image_entry(i) for i in own_images(a)] for a in actors},
                       "voxel_models": {a: [r["file"] for i in acts[a]["images"] if i in models
                                            for pair in models[i].values() for r in pair if r["by"] == "ea"]
                                        for a in actors}}

    fx_imgs = set()
    for x in modern:
        fx_imgs |= {i for i in acts[x]["images"] + acts[x]["weaponImages"] if i in imf and group(i) == "sequences/misc.yaml"}
    effects = {i: image_entry(i) for i in sorted(fx_imgs)}
    residue = sorted({f for x in modern for i in acts[x]["images"] if i in imf and group(i) != "sequences/misc.yaml"
                      and (isrc.get(i, ["?"])[0].startswith("ra2|modern-factions"))
                      for f in imf[i] if files.get(f, {}).get("by") == "ea"})

    # audio
    weapons = set().union(*(set(acts[x]["weapons"]) for x in modern))
    sfx = defaultdict(lambda: {"by": None, "used_by": set()})
    for k, r in audit["audio"]["ruleSounds"].items():
        kind, name = k.split(":")[0], k.split(":")[1]
        if (kind == "actor" and name in modern) or (kind == "weapon" and name in weapons):
            sfx[r["file"]]["by"] = r["by"]
            sfx[r["file"]]["used_by"].add(f"{kind}:{name}")
    voices = {k.lower(): v for k, v in audit["audio"]["voices"].items()}
    vo = defaultdict(lambda: {"by": None, "sets": set(), "actors": set()})
    for f in MODERN:
        for x in reach[f]["actors"]:
            for vs in acts[x]["voiceSets"]:
                for e in voices.get(vs.lower(), {}).get(f, []):
                    d = vo[e["r"]["file"]]
                    d["by"] = e["r"]["by"]
                    d["sets"].add(f"{vs}/{e['def']}")
                    d["actors"].add(x)
    ui = sorted({e["r"]["file"] for e in audit["audio"]["notifications"].get("Sounds", audit["audio"]["notifications"].get("sounds", {})).get("china", [])
                 if e["r"]["by"] == "ea"})

    def listing(d):
        return [{"file": f, "status": v["by"], **{k: sorted(x) for k, x in v.items() if isinstance(x, set)}}
                for f, v in sorted(d.items()) if v["by"] in ("ea", "missing")]

    return {
        "note": "EA files the 7 modern factions reach today, by deliverable. Keep the file names (sprites: frame counts "
                "at least as listed). 'missing' = referenced by rules but absent even in RA2: deliver or tell the "
                "rtsai/standalone agent to drop the reference. Generated by tools/standalone-deliverables.py.",
        "art": {
            "dir": {"base_kit": "mods/rtsai/standalone/base/", "shared_units": "mods/rtsai/standalone/units/",
                    "effects": "mods/rtsai/standalone/effects/"},
            "base_kit": kit, "cut_from_modern_rosters": CUT, "shared_units": units,
            "effects": effects, "effects_in_modern_unit_sequences": [sprite(f) for f in residue],
            "palettes": {"anim.pal": "effects agent (fire/smoke/spark ramps)", "kitbase.pal": "base kit + shared units",
                         "others": "the 16 other EA palettes are replaced by the rtsai/standalone agent (Phase 2)"},
        },
        "audio": {
            "dir": {"sfx": "mods/rtsai/standalone/audio/sfx/", "ui": "mods/rtsai/standalone/audio/ui/",
                    "voices": "mods/rtsai/standalone/audio/voices/", "music": "mods/rtsai/standalone/audio/music/ + music.yaml"},
            "sfx": listing(sfx), "ui": ui, "voices": listing(vo),
            "music": "replace mods/rtsai/standalone/audio/music.yaml (new keys); the RA2 soundtrack stays classic-only",
        },
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--audit", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args()
    d = build(json.loads(a.audit.read_text(encoding="utf-8")))
    a.out.write_text(json.dumps(d, indent=1, sort_keys=False) + "\n", encoding="utf-8", newline="\n")
    au = d["audio"]
    print(f"wrote {a.out}: kit roles {len(d['art']['base_kit'])}, unit groups {len(d['art']['shared_units'])}, "
          f"effect images {len(d['art']['effects'])} + {len(d['art']['effects_in_modern_unit_sequences'])} files, "
          f"sfx {len(au['sfx'])}, ui {len(au['ui'])}, voices {len(au['voices'])}")


if __name__ == "__main__":
    main()
