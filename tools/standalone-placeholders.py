#!/usr/bin/env python3
"""Standalone prototype: project-made placeholder stand-ins for every EA file the RA2-mode mod still loads.

Two steps:

  manifest  --from-audit <audit.json>   (from tools/standalone-audit.py --content ...)
            Writes mods/rtsai/standalone/placeholders.json: the NAMES of the EA files the mod references, with
            frame counts and frame sizes, plus which palettes, models and cursor files are EA. No pixels, samples
            or palette values are read or recorded.
  build     (default)
            Draws placeholders from that manifest into mods/rtsai/standalone/placeholders/ and writes placeholder
            tilesets to mods/rtsai/standalone/tilesets/. Everything is drawn here, procedurally:
              - sprites: RGBA PNG sheets (FrameSize/FrameAmount metadata) under the EA file name, one flat
                category-coloured shape per frame; build-palette icons carry the image name as text;
              - voxels: one box VXL + one-frame HVA per EA model name, painted in the player-remap ramp 16-31;
              - palettes: one procedural 256-colour palette (remap ramp 16-31) under each EA palette name;
              - terrain: a single PNG sheet of flat 60x30 diamonds, one per terrain type and ramp; each tileset
                template keeps its id, size and terrain types and points at that sheet with Frames.

The placeholders exist only to find out what breaks without EA content. They are not art and not a release path.
usage: python tools/standalone-placeholders.py manifest --from-audit <scratch>/audit-content.json
       python tools/standalone-placeholders.py build
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import struct
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from PIL.PngImagePlugin import PngInfo

ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "mods" / "rtsai"
OUT = MOD / "standalone"
MANIFEST = OUT / "placeholders.json"

KIND_COLORS = {
    "structure": (70, 110, 205, 210),
    "infantry": (60, 190, 90, 220),
    "vehicle": (235, 140, 40, 220),
    "effect": (250, 220, 60, 150),
    "scenery": (130, 95, 55, 210),
    "ui": (200, 200, 200, 220),
}


def kind_of(image_groups: set[str], sequences: set[str]) -> str:
    if "icon" in sequences:
        return "icon"
    g = " ".join(sorted(image_groups))
    if "structures" in g:
        return "structure"
    if "infantry" in g or "civilians" in g or "animals" in g:
        return "infantry"
    if "vehicles" in g or "aircraft" in g or "naval" in g:
        return "vehicle"
    if "trees" in g or "props" in g or "bridges" in g:
        return "scenery"
    return "effect"


# ------------------------------------------------------------------------------------------------ manifest
def make_manifest(audit_path: Path):
    a = json.loads(audit_path.read_text(encoding="utf-8"))
    files = a["sprites"]["files"]
    isrc = a["sprites"]["imageSources"]
    users: dict[str, dict] = {}
    for ts in a["sprites"]["tilesets"].values():
        for image, seqs in ts["imageSequences"].items():
            group = isrc.get(image, ["?"])[0].split("|")[-1]
            for seq, flist in seqs.items():
                for f in flist:
                    u = users.setdefault(f, {"groups": set(), "sequences": set(), "images": set()})
                    u["groups"].add(group)
                    u["sequences"].add(seq)
                    u["images"].add(image)
    sprites = {}
    for name, info in sorted(files.items()):
        if info["by"] != "ea":
            continue
        u = users.get(name, {"groups": set(), "sequences": set(), "images": set()})
        sprites[name] = {"frames": info.get("frames", 1), "w": info.get("w", 24), "h": info.get("h", 24),
                         "kind": kind_of(u["groups"], u["sequences"]), "image": sorted(u["images"])[0] if u["images"] else ""}
    models = sorted({r["file"] for seqs in a["models"]["images"].values() for pair in seqs.values() for r in pair
                     if r["by"] == "ea"})
    palettes = sorted({p["resolve"]["file"] for p in a["palettes"] if p["resolve"]["by"] == "ea"})
    cursors = sorted({c["resolve"]["file"] for c in a["cursors"] if c["resolve"] and c["resolve"]["by"] == "ea"})
    tile_files = sum(len(t["files"]) for t in a["terrain"].values())
    manifest = {
        "note": "Names, frame counts and frame sizes of EA files the RA2-mode mod references, measured by "
                "tools/standalone-audit.py. No EA pixels, samples or palette values. Input to the placeholder build.",
        "sprites": sprites, "models": models, "palettes": palettes, "cursors": cursors,
        "terrain_tile_files_replaced": tile_files,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, indent=0, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"{MANIFEST}: {len(sprites)} sprites, {len(models)} model files, {len(palettes)} palettes, cursors {cursors}")


# ------------------------------------------------------------------------------------------------ drawing
def sheet(frame: Image.Image, count: int) -> tuple[Image.Image, PngInfo]:
    cols = max(1, min(count, int(math.ceil(math.sqrt(count)))))
    rows = int(math.ceil(count / cols))
    w, h = frame.size
    im = Image.new("RGBA", (cols * w, rows * h), (0, 0, 0, 0))
    for i in range(count):
        im.paste(frame, ((i % cols) * w, (i // cols) * h))
    meta = PngInfo()
    meta.add_text("FrameSize", f"{w},{h}")
    meta.add_text("FrameAmount", str(count))
    return im, meta


def sprite_frame(kind: str, w: int, h: int, label: str) -> Image.Image:
    if kind == "icon":
        im = Image.new("RGBA", (60, 48), (28, 34, 44, 255))
        d = ImageDraw.Draw(im)
        d.rectangle((0, 0, 59, 47), outline=(120, 140, 170, 255))
        d.text((4, 4), "EA", fill=(230, 90, 90, 255), font=ImageFont.load_default())
        d.text((4, 26), label[:9], fill=(235, 235, 235, 255), font=ImageFont.load_default())
        return im
    fw = max(6, min(64, round(w * 0.5)))
    fh = max(6, min(64, round(h * 0.5)))
    im = Image.new("RGBA", (fw, fh), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    color = KIND_COLORS.get(kind, KIND_COLORS["effect"])
    edge = tuple(max(0, c - 70) for c in color[:3]) + (255,)
    if kind == "effect":
        d.ellipse((0, 0, fw - 1, fh - 1), fill=color, outline=edge)
    elif kind == "infantry":
        d.rectangle((fw // 4, 0, fw - 1 - fw // 4, fh - 1), fill=color, outline=edge)
    else:
        d.rectangle((0, 0, fw - 1, fh - 1), fill=color, outline=edge)
    return im


def write_png(path: Path, im: Image.Image, meta: PngInfo):
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, format="PNG", pnginfo=meta, optimize=True)


# ------------------------------------------------------------------------------------------------ voxels
IDENTITY = (1., 0., 0., 0., 0., 1., 0., 0., 0., 0., 1., 0.)


def box_vxl(palette: bytes) -> bytes:
    sx, sy, sz = 10, 7, 5
    lower = (-sx / 2, -sy / 2, 0.)
    voxels = {(x, y, z): (16 + min(15, 4 + z * 3), 0) for x in range(sx) for y in range(sy) for z in range(sz)}
    starts, ends, spans = [], [], bytearray()
    for y in range(sy):
        for x in range(sx):
            starts.append(len(spans))
            spans.extend((0, sz))
            for z in range(sz):
                spans.extend(voxels[x, y, z])
            spans.append(sz)
            ends.append(len(spans) - 1)
    body = struct.pack(f"<{len(starts)}i", *starts) + struct.pack(f"<{len(ends)}i", *ends) + spans
    header = b"Voxel Animation\0" + struct.pack("<4I", 1, 1, 1, len(body)) + bytes((16, 31)) + palette
    limb = b"body".ljust(16, b"\0") + struct.pack("<3I", 0, 1, 0)
    bounds = (*lower, *(lower[i] + (sx, sy, sz)[i] for i in range(3)))
    footer = struct.pack("<3If12f6f4B", 0, sx * sy * 4, sx * sy * 8, 1. / 12., *IDENTITY, *bounds, sx, sy, sz, 4)
    return header + limb + body + footer


def box_hva() -> bytes:
    return bytes(16) + struct.pack("<2I", 1, 1) + b"body".ljust(16, b"\0") + struct.pack("<12f", *IDENTITY)


# ------------------------------------------------------------------------------------------------ palettes
def procedural_palette() -> bytes:
    """256 x RGB, 6-bit (VGA) like RA2 .pal files: 0 transparent, 1 shadow, 16-31 remap ramp, rest an HSV sweep."""
    import colorsys
    pal = []
    for i in range(256):
        if i < 16:
            v = i * 4
            rgb = (v, v, v)
        elif i < 32:
            t = (i - 16) / 15
            rgb = (int(255 * (0.25 + 0.75 * (1 - t))), int(40 * (1 - t)), int(40 * (1 - t)))
        else:
            hue = ((i - 32) % 28) / 28
            val = 0.35 + 0.65 * ((i - 32) // 28) / 7
            rgb = tuple(int(c * 255) for c in colorsys.hsv_to_rgb(hue, 0.55, min(1, val)))
        pal.append(rgb)
    return bytes(c >> 2 for rgb in pal for c in rgb)


# ------------------------------------------------------------------------------------------------ terrain
TERRAIN_RGB = {
    "Clear": (92, 140, 62), "Rough": (122, 112, 72), "Road": (112, 112, 112), "DirtRoad": (146, 112, 72),
    "Water": (44, 84, 164), "Cliff": (70, 60, 52), "Rail": (92, 92, 92), "Impassable": (58, 58, 58),
    "Ore": (182, 150, 62), "Gems": (132, 82, 172), "Bridge": (104, 92, 82), "Tunnel": (50, 50, 50),
    "Beach": (204, 184, 124), "Tiberium": (80, 180, 80), "Wall": (90, 90, 100),
}
RAMPS = 21


def terrain_types(text: str) -> list[str]:
    return re.findall(r"^\tTerrainType@[^:]+:\n\t\tType: (\S+)", text, re.M)


def terrain_sheet(types: list[str]) -> tuple[Image.Image, PngInfo, int]:
    frames = []
    for t in types:
        base = TERRAIN_RGB.get(t) or tuple(int(hashlib.md5(t.encode()).hexdigest()[i:i + 2], 16) for i in (0, 2, 4))
        for r in range(RAMPS):
            shade = 1.0 if r == 0 else 0.82 + 0.06 * (r % 5)
            frames.append(tuple(min(255, int(c * shade)) for c in base))
    frames.append(None)  # transparent: template cells without a tile
    w, h = 60, 30
    cols = 32
    rows = int(math.ceil(len(frames) / cols))
    im = Image.new("RGBA", (cols * w, rows * h), (0, 0, 0, 0))
    px = im.load()
    for n, rgb in enumerate(frames):
        if rgb is None:
            continue
        ox, oy = (n % cols) * w, (n // cols) * h
        edge = tuple(max(0, c - 28) for c in rgb)
        for y in range(h):
            for x in range(w):
                d = abs(x - 29.5) / 30 + abs(y - 14.5) / 15
                if d <= 1.0:
                    px[ox + x, oy + y] = (*(edge if d > 0.93 else rgb), 255)
    meta = PngInfo()
    meta.add_text("FrameSize", f"{w},{h}")
    meta.add_text("FrameAmount", str(len(frames)))
    return im, meta, len(frames) - 1


def placeholder_tileset(src: Path, dst: Path, sheet_name: str):
    text = src.read_text(encoding="utf-8").replace("\r\n", "\n")
    types = terrain_types(text)
    index = {t: i for i, t in enumerate(types)}
    im, meta, empty = terrain_sheet(types)
    write_png(OUT / "placeholders" / sheet_name, im, meta)

    out, blocks = [], re.split(r"(?m)^(?=\tTemplate@)", text)
    head = blocks[0].replace("\tEnableDepth: true", "\tEnableDepth: false")
    head = re.sub(r"(?m)^\tName: .*$", lambda m: m[0], head)
    out.append(head)
    for b in blocks[1:]:
        size = re.search(r"^\t\tSize: (\d+), *(\d+)", b, re.M)
        sx, sy = int(size[1]), int(size[2])
        pick_any = re.search(r"^\t\tPickAny: [Tt]rue", b, re.M) is not None
        tiles = {}
        tiles_block = b.split("\t\tTiles:\n", 1)[1]
        for m in re.finditer(r"^\t\t\t(\d+): (\S+)\n((?:\t\t\t\t.*\n?)*)", tiles_block, re.M):
            ramp = re.search(r"RampType: (\d+)", m[3])
            tiles[int(m[1])] = (m[2], int(ramp[1]) if ramp else 0)
        count = len(tiles) if pick_any else sx * sy
        frames = []
        for k in range(count):
            if k in tiles:
                t, r = tiles[k]
                frames.append(index.get(t, 0) * RAMPS + min(r, RAMPS - 1))
            else:
                frames.append(empty)
        b = re.sub(r"(?m)^\t\tImages: .*$", f"\t\tImages: {sheet_name}\n\t\tFrames: " + ", ".join(map(str, frames)), b)
        b = re.sub(r"(?m)^\t\tDepthImages: .*\n", "", b)
        out.append(b)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text("# GENERATED by tools/standalone-placeholders.py from " + src.name +
                   ": same templates, ids, sizes and terrain types; flat placeholder diamonds instead of EA tiles.\n"
                   + "".join(out), encoding="utf-8", newline="\n")
    return len(blocks) - 1


# ------------------------------------------------------------------------------------------------ build
def cursor_frames(name: str) -> int:
    text = (MOD / "cursors.yaml").read_text(encoding="utf-8").replace("\r\n", "\n")
    block = re.search(rf"^\t{re.escape(name)}:.*\n((?:\t\t.*\n?)*)", text, re.M)
    hi = 1
    for seq in re.finditer(r"^\t\t\S+:\n((?:\t\t\t.*\n?)*)", block[1] if block else "", re.M):
        start = re.search(r"Start: (\d+)", seq[1])
        length = re.search(r"Length: (\d+)", seq[1])
        hi = max(hi, (int(start[1]) if start else 0) + (int(length[1]) if length else 1))
    return hi


def cursor_frame() -> Image.Image:
    im = Image.new("RGBA", (24, 24), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.polygon([(2, 2), (2, 19), (7, 14), (11, 22), (14, 21), (10, 13), (17, 13)], fill=(250, 250, 250, 255),
              outline=(20, 20, 20, 255))
    return im


def build():
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    ph = OUT / "placeholders"
    ph.mkdir(parents=True, exist_ok=True)
    for name, s in m["sprites"].items():
        frame = sprite_frame(s["kind"], s["w"], s["h"], s["image"] or name.split(".")[0])
        im, meta = sheet(frame, s["frames"])
        # "conquer|wake1.shp": an explicit package prefix becomes a subfolder mounted under that name in mod.yaml
        write_png(ph / name.replace("|", "/"), im, meta)
    pal = procedural_palette()
    for name in m["palettes"]:
        (ph / name).write_bytes(pal)
    vxl, hva = box_vxl(pal), box_hva()
    for name in m["models"]:
        (ph / name).write_bytes(vxl if name.endswith(".vxl") else hva)
    for name in m["cursors"]:
        im, meta = sheet(cursor_frame(), cursor_frames(name))
        write_png(ph / name, im, meta)
    n = 0
    for ts in ["temperat"]:   # the standalone game ships one theatre; snow and urban are classic-only
        n += placeholder_tileset(ROOT / "mods" / "rtsai-classic" / "tilesets" / f"{ts}.yaml", OUT / "tilesets" / f"{ts}.yaml", f"standalone-{ts}.png")
    size = sum(p.stat().st_size for p in ph.rglob("*") if p.is_file())
    print(f"{len(m['sprites'])} sprites, {len(m['models'])} model files, {len(m['palettes'])} palettes, "
          f"{len(m['cursors'])} cursors, {n} templates; placeholders {size / 1e6:.1f} MB")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("step", nargs="?", default="build", choices=["manifest", "build"])
    ap.add_argument("--from-audit", type=Path)
    a = ap.parse_args()
    if a.step == "manifest":
        if not a.from_audit:
            sys.exit("manifest needs --from-audit")
        make_manifest(a.from_audit)
    else:
        build()


if __name__ == "__main__":
    main()
