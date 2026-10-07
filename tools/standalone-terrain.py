#!/usr/bin/env python3
"""The standalone game's temperate tileset: every template rendered in Blender from procedural geometry and materials.

The tileset keeps the RA2-compatible template table (the ids, sizes, terrain types, heights and ramp types of the
upstream OpenRA RA2 mod's temperat.yaml) so the shipped maps, the classic add-on's maps and the Workshop export all
load. Not one pixel comes from RA2: each template is rebuilt as 3D geometry and lit and textured in Blender.

  1. geometry (here, numpy): per tile a height field from the engine's own ramp planes (MapGrid.Ramps), south-facing
     cliff walls down to the lower neighbour, and per-vertex material weights (grass, rough, dirt road, pavement,
     sand, water, rock, rubble, gravel) blended across tiles of a template and pinned to the tile's own material at
     the template border, so templates tile with each other.
  2. render (tools/terrain/blender_batch.py): batches of ~48 templates per image, orthographic 2:1 camera with exactly
     30 px per cell edge and 15 px per height level, Cycles on the CPU (the GPU belongs to other sessions).
  3. cut (here): each tile's frame is the pixels whose centres fall inside its projected top and walls, so neighbours
     partition pixels exactly; frames get offsets so the engine places them like TS/RA2 tiles.
  4. quantize all frames to one 254-colour palette (index 0 transparent, 1 shadow) -> terrain/temperate.pal, write
     indexed PNG sheets (Frame[i] regions and offsets) and the tileset YAML with radar colours from our pixels.

Extra templates (ids 1000+): 1x1 corner transitions (grass with water, dirt, rough or sand at any of the 4 corners)
for generated maps (tools/standalone-maps.py): coastlines and roads join smoothly because the boundary only depends
on the two corners of each shared edge.

usage: python tools/standalone-terrain.py [--only 0,314,49] [--samples 48] [--threads 20]
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image
from PIL.PngImagePlugin import PngInfo

ROOT = Path(__file__).resolve().parents[1]
SRC_TILESET = ROOT / "mods" / "rtsai-classic" / "tilesets" / "temperat.yaml"
OUT_DIR = ROOT / "mods" / "rtsai" / "standalone" / "terrain"
OUT_TILESET = ROOT / "mods" / "rtsai" / "standalone" / "tilesets" / "temperat.yaml"
BLENDER = Path(r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe")
BATCH_SCRIPT = ROOT / "tools" / "terrain" / "blender_batch.py"

CLASSES = ["grass", "rough", "dirt", "pave", "sand", "water", "rock", "rubble", "gravel"]
CI = {c: i for i, c in enumerate(CLASSES)}
TYPE_CLASS = {"Clear": "grass", "Rough": "rough", "DirtRoad": "dirt", "Road": "pave", "Water": "water",
              "Rail": "gravel", "Impassable": "rock", "Bridge": "pave", "Cliff": "rubble"}
LEVEL = 1 / math.sqrt(6)        # Blender units per height level (15 px)
PX = 30 * math.sqrt(2)          # px per Blender unit across the screen

# MapGrid.Ramps: (tl, tr, br, bl) corner levels and the split diagonal ("X": tr-bl, "Y": tl-br, None: flat plane)
RAMPS = [
    ((0, 0, 0, 0), None), ((0, 1, 1, 0), None), ((0, 0, 1, 1), None), ((1, 0, 0, 1), None), ((1, 1, 0, 0), None),
    ((0, 0, 1, 0), "X"), ((0, 0, 0, 1), "Y"), ((1, 0, 0, 0), "X"), ((0, 1, 0, 0), "Y"),
    ((0, 1, 1, 1), "X"), ((1, 0, 1, 1), "Y"), ((1, 1, 0, 1), "X"), ((1, 1, 1, 0), "Y"),
    ((0, 1, 2, 1), None), ((1, 0, 1, 2), None), ((2, 1, 0, 1), None), ((1, 2, 1, 0), None),
    ((0, 1, 0, 1), "Y"), ((1, 0, 1, 0), "Y"), ((0, 1, 0, 1), "X"), ((1, 0, 1, 0), "X"),
]

TRANSITION_SETS = [("water", "Water"), ("dirt", "DirtRoad"), ("rough", "Rough"), ("sand", "Clear")]
TRANSITION_BASE = 1000


# ------------------------------------------------------------------------------------------------ template table
@dataclass
class Tile:
    type: str
    height: int = 0
    ramp: int = 0
    corners: tuple | None = None        # transition templates: class per corner (tl, tr, br, bl)


@dataclass
class Template:
    id: int
    sx: int
    sy: int
    tiles: dict
    variants: int
    category: str
    block: str = ""                      # original YAML block (RA2-compatible templates)
    images: list = field(default_factory=list)

    @property
    def count(self):
        return self.sx * self.sy


def parse_tileset(text: str):
    head, *blocks = re.split(r"(?m)^(?=\tTemplate@)", text.replace("\r\n", "\n"))
    templates = []
    for b in blocks:
        tid = int(re.search(r"^\t\tId: (\d+)", b, re.M)[1])
        sx, sy = map(int, re.search(r"^\t\tSize: (\d+), *(\d+)", b, re.M).groups())
        if re.search(r"^\t\tPickAny: [Tt]rue", b, re.M):
            raise SystemExit(f"template {tid}: PickAny is not supported")
        images = re.search(r"^\t\tImages: (.*)$", b, re.M)[1].split(",")
        tiles = {}
        for m in re.finditer(r"^\t\t\t(\d+): (\S+)\n((?:\t\t\t\t.*\n?)*)", b.split("\t\tTiles:\n", 1)[1], re.M):
            h = re.search(r"Height: (\d+)", m[3])
            r = re.search(r"RampType: (\d+)", m[3])
            tiles[int(m[1])] = Tile(m[2], int(h[1]) if h else 0, int(r[1]) if r else 0)
        cat = re.search(r"^\t\tCategories: (.*)$", b, re.M)[1]
        templates.append(Template(tid, sx, sy, tiles, len(images), cat, b))
    return head, templates


def transition_templates():
    out = []
    for si, (cls, ttype) in enumerate(TRANSITION_SETS):
        for mask in range(1, 16):
            corners = tuple(cls if mask & (1 << k) else "grass" for k in range(4))   # bit0 tl, 1 tr, 2 br, 3 bl
            n = sum(1 for c in corners if c != "grass")
            tile_type = ttype if n >= 2 else "Clear"     # pathing: a half-water edge is water
            tid = TRANSITION_BASE + si * 16 + mask
            out.append(Template(tid, 1, 1, {0: Tile(tile_type, corners=corners)}, 2, f"RTS AI {cls} edges"))
    return out


# ------------------------------------------------------------------------------------------------ geometry
def ramp_z(ramp: int, u, v):
    (tl, tr, br, bl), split = RAMPS[ramp]
    u, v = np.asarray(u, float), np.asarray(v, float)
    if split is None:
        return tl + (tr - tl) * u + (br - tr) * v
    if split == "X":
        a = tl + (tr - tl) * u + (bl - tl) * v
        b = br + (bl - br) * (1 - u) + (tr - br) * (1 - v)
        return np.where(u + v <= 1, a, b)
    a = tl + (tr - tl) * u + (br - tr) * v
    b = tl + (br - bl) * u + (bl - tl) * v
    return np.where(u >= v, a, b)


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


class Noise:
    """Smooth deterministic 2D noise from a few sine octaves (enough to roughen material boundaries)."""
    def __init__(self, seed: int):
        r = np.random.default_rng(seed)
        self.w = r.normal(size=(6, 2)) * np.array([[1.3], [1.9], [2.7], [3.6], [5.1], [7.3]])
        self.p = r.uniform(0, 2 * np.pi, 6)
        self.a = np.array([0.32, 0.24, 0.16, 0.12, 0.09, 0.07])

    def __call__(self, x, y):
        s = sum(a * np.sin(w[0] * x + w[1] * y + p) for w, p, a in zip(self.w, self.p, self.a))
        return 0.5 + 0.5 * np.clip(s / 1.0, -1, 1)


def tile_class(t: Template, k: int) -> str:
    tile = t.tiles[k]
    if tile.type == "Cliff":
        lo = min(x.height for x in t.tiles.values())
        return "rough" if tile.height > lo else "rubble"
    return TYPE_CLASS.get(tile.type, "grass")


def template_geometry(t: Template, ox: int, oy: int, seed: int, n: int = 8, skirt: float = 0.14):
    """Vertices (Blender units), triangles, weights and per-tile polygon data for one template at cell offset."""
    verts, tris, weights, walls, skirt_tris = [], [], [], {}, []
    noise = [Noise(seed * 31 + i) for i in range(len(CLASSES))]
    lo = min(x.height for x in t.tiles.values())
    present = {(k % t.sx, k // t.sx): k for k in t.tiles}

    def tile_at(x, y):
        return present.get((x, y))

    def z_of(k, u, v):
        tile = t.tiles[k]
        return tile.height + (np.zeros(np.shape(u)) if tile.corners else ramp_z(tile.ramp, u, v))

    def weights_for(k, gx, gy):
        """gx, gy: template-local positions (cells). Blend across tiles of the same height, pin at the border."""
        tile = t.tiles[k]
        x0, y0 = k % t.sx, k // t.sx
        w = np.zeros((len(gx), len(CLASSES)))
        if tile.corners:
            u, v = gx - x0, gy - y0
            for c in set(tile.corners):
                ind = [1.0 if cc == c else 0.0 for cc in tile.corners]          # tl, tr, br, bl
                b = (ind[0] * (1 - u) * (1 - v) + ind[1] * u * (1 - v) + ind[2] * u * v + ind[3] * (1 - u) * v)
                w[:, CI[c]] += b
            other = [c for c in set(tile.corners) if c != "grass"]
            if other:
                c = other[0]
                bump = np.sin(np.pi * np.clip(u, 0, 1)) * np.sin(np.pi * np.clip(v, 0, 1))
                wb = w[:, CI[c]] + 0.45 * bump * (noise[CI[c]](gx + ox, gy + oy) - 0.5)
                wb = smoothstep(0.38, 0.62, wb)
                w[:, :] = 0
                w[:, CI[c]] = wb
                w[:, CI["grass"]] = 1 - wb
            return w
        # Blend over the 3x3 cells around this tile. Cells past the template border repeat the nearest border tile,
        # as if the template continued: the next template along a coast or road then produces the same edge
        # profile, so beaches and road edges run on across template seams. Noise fades to zero at the border.
        mix = np.zeros((len(gx), len(CLASSES)))
        for cy in range(y0 - 1, y0 + 2):
            for cx in range(x0 - 1, x0 + 2):
                src = tile_at(min(max(cx, 0), t.sx - 1), min(max(cy, 0), t.sy - 1))
                if src is None or t.tiles[src].height != tile.height:
                    continue
                dx = np.maximum(np.maximum(cx - gx, gx - (cx + 1)), 0)
                dy = np.maximum(np.maximum(cy - gy, gy - (cy + 1)), 0)
                mix[:, CI[tile_class(t, src)]] += smoothstep(0, 1, 1 - np.hypot(dx, dy) / 0.55)
        border = np.minimum.reduce([gx, gy, t.sx - gx, t.sy - gy])
        f = smoothstep(0.0, 0.5, border)
        for c in range(len(CLASSES)):
            mix[:, c] *= 1 + f * (0.8 * noise[c](gx + ox, gy + oy) - 0.4)
        mix = mix ** 2
        return mix / np.maximum(mix.sum(axis=1, keepdims=True), 1e-9)

    def add_grid(k, us, vs, zfn, wfn, out=None):
        out = tris if out is None else out
        base = len(verts)
        U, V = np.meshgrid(us, vs, indexing="xy")
        z = zfn(U, V)
        x0, y0 = k % t.sx, k // t.sx
        gx, gy = (x0 + U).ravel(), (y0 + V).ravel()
        for X, Y, Z in zip(gx, gy, z.ravel()):
            verts.append((ox + X, -(oy + Y), Z * LEVEL))
        weights.extend(wfn(gx, gy))
        nu, nv = len(us), len(vs)
        split = RAMPS[t.tiles[k].ramp][1] if not t.tiles[k].corners else None
        for j in range(nv - 1):
            for i in range(nu - 1):
                a, b, c, d = base + j * nu + i, base + j * nu + i + 1, base + (j + 1) * nu + i + 1, base + (j + 1) * nu + i
                if split == "X":
                    out.extend([(a, b, d), (b, c, d)])
                else:
                    out.extend([(a, b, c), (a, c, d)])

    for k, tile in t.tiles.items():
        x0, y0 = k % t.sx, k // t.sx
        us = np.linspace(0, 1, n + 1)
        add_grid(k, us, us, lambda U, V, k=k: z_of(k, U, V), lambda gx, gy, k=k: weights_for(k, gx, gy))
        # skirts beyond the template border (or a missing neighbour) so border pixels sample terrain, not sky
        for side, (dxn, dyn) in {"-x": (-1, 0), "+x": (1, 0), "-y": (0, -1), "+y": (0, 1)}.items():
            if tile_at(x0 + dxn, y0 + dyn) is not None:
                continue
            ext = np.concatenate([[-skirt], us, [1 + skirt]])    # past the edge ends: covers outer corners
            if side == "-x":
                ss, tt = np.array([-skirt, 0]), ext
            elif side == "+x":
                ss, tt = np.array([1, 1 + skirt]), ext
            elif side == "-y":
                ss, tt = ext, np.array([-skirt, 0])
            else:
                ss, tt = ext, np.array([1, 1 + skirt])
            add_grid(k, ss, tt, lambda U, V, k=k: z_of(k, np.clip(U, 0, 1), np.clip(V, 0, 1)),
                     lambda gx, gy, k=k, x0=x0, y0=y0: weights_for(k, np.clip(gx, x0, x0 + 1), np.clip(gy, y0, y0 + 1)),
                     out=skirt_tris)

        # south-facing walls (+x edge: u=1, +y edge: v=1)
        walls[k] = []
        for side in ("+x", "+y"):
            nb = tile_at(x0 + 1, y0) if side == "+x" else tile_at(x0, y0 + 1)
            s = np.linspace(0, 1, n + 1)
            top = z_of(k, np.ones_like(s), s) if side == "+x" else z_of(k, s, np.ones_like(s))
            if nb is not None:
                bot = z_of(nb, np.zeros_like(s), s) if side == "+x" else z_of(nb, s, np.zeros_like(s))
            elif tile.type == "Cliff" or tile.height > lo:
                bot = np.full_like(s, float(lo))
            else:
                continue
            if np.max(top - bot) < 0.05:
                continue
            bot = np.minimum(bot, top)
            walls[k].append((side, top, bot))
            rows = max(2, int(np.ceil(np.max(top - bot) * 3)) + 1)
            base = len(verts)
            for r in range(rows):
                f = r / (rows - 1)
                zz = top * (1 - f) + bot * f
                for i, si in enumerate(s):
                    gx, gy = (x0 + 1, y0 + si) if side == "+x" else (x0 + si, y0 + 1)
                    verts.append((ox + gx, -(oy + gy), zz[i] * LEVEL))
                    wv = np.zeros(len(CLASSES))
                    wv[CI["rock"]] = 1.0
                    weights.append(wv)
            m = len(s)
            for r in range(rows - 1):
                for i in range(m - 1):
                    a, b = base + r * m + i, base + r * m + i + 1
                    c, d = base + (r + 1) * m + i + 1, base + (r + 1) * m + i
                    tris.extend([(a, b, c), (a, c, d)])
    return verts, tris, weights, walls, skirt_tris


# ------------------------------------------------------------------------------------------------ projection and masks
def project(x, y, z):
    """Cell coords (+ height levels) -> pixels, world cell origin at pixel (0, 0)."""
    return (x - y) * 30.0, (x + y) * 15.0 - z * 15.0


def tile_polygons(t: Template, k: int, ox: int, oy: int, walls):
    tile = t.tiles[k]
    x0, y0 = ox + k % t.sx, oy + k // t.sx
    (tl, tr, br, bl), split = ((0, 0, 0, 0), None) if tile.corners else RAMPS[tile.ramp]
    h = tile.height
    C = {"tl": (x0, y0, h + tl), "tr": (x0 + 1, y0, h + tr), "br": (x0 + 1, y0 + 1, h + br), "bl": (x0, y0 + 1, h + bl)}
    if split == "X":
        polys = [[C["tl"], C["tr"], C["bl"]], [C["tr"], C["br"], C["bl"]]]
    elif split == "Y":
        polys = [[C["tl"], C["tr"], C["br"]], [C["tl"], C["br"], C["bl"]]]
    else:
        polys = [[C["tl"], C["tr"], C["br"], C["bl"]]]
    for side, top, bot in walls.get(k, []):
        s = np.linspace(0, 1, len(top))
        edge = [(x0 + 1, y0 + si) for si in s] if side == "+x" else [(x0 + si, y0 + 1) for si in s]
        polys.append([(ex, ey, top[i]) for i, (ex, ey) in enumerate(edge)] +
                     [(ex, ey, bot[i]) for i, (ex, ey) in reversed(list(enumerate(edge)))])
    return [[project(*p) for p in poly] for poly in polys], project(x0 + 0.5, y0 + 0.5, h)


def inside(poly, xs, ys):
    """Crossing-number point-in-polygon for pixel centres (xs, ys arrays)."""
    res = np.zeros(xs.shape, bool)
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        cond = (y1 > ys) != (y2 > ys)
        with np.errstate(divide="ignore", invalid="ignore"):
            xin = (x2 - x1) * (ys - y1) / (y2 - y1) + x1
        res ^= cond & (xs < xin)
    return res


# ------------------------------------------------------------------------------------------------ batching
def bbox(t: Template):
    lv = max(x.height for x in t.tiles.values()) + 2
    return -t.sy * 30 - 6, -lv * 15 - 6, t.sx * 30 + 6, (t.sx + t.sy) * 15 + 6


def layout(jobs, cols=8, margin=60):
    """jobs: [(template, variant)] -> per job integer cell offset (ox, oy) and the image size."""
    sw = max(b[2] - b[0] for b in (bbox(t) for t, _ in jobs)) + margin
    sh = max(b[3] - b[1] for b in (bbox(t) for t, _ in jobs)) + margin
    sw, sh = int(math.ceil(sw / 60) * 60), int(math.ceil(sh / 30) * 30)
    placed = []
    for i, (t, v) in enumerate(jobs):
        c, r = i % cols, i // cols
        x0, y0, _, _ = bbox(t)
        X = c * sw + margin // 2 - x0
        Y = r * sh + margin // 2 - y0
        X = int(round(X / 30)) * 30
        Y = int(round(Y / 15)) * 15
        if (X // 30) % 2 != (Y // 15) % 2:
            Y += 15
        ox, oy = ((X // 30) + (Y // 15)) // 2, ((Y // 15) - (X // 30)) // 2
        placed.append((t, v, ox, oy))
    rows = math.ceil(len(jobs) / cols)
    return placed, (cols * sw, rows * sh + 30)


def render_batch(placed, size, work: Path, name: str, threads: int, samples: int, seed: int):
    V, T, Wt, walls, S = [], [], [], {}, []
    for t, v, ox, oy in placed:
        vv, tt, ww, wl, st = template_geometry(t, ox, oy, seed=t.id * 7 + v * 1009 + seed)
        base = len(V)
        V.extend(vv)
        T.extend([(a + base, b + base, c + base) for a, b, c in tt])
        S.extend([(a + base, b + base, c + base) for a, b, c in st])
        Wt.extend(ww)
        walls[(t.id, v)] = wl
    skirt = np.array([False] * len(T) + [True] * len(S))
    V, T, Wt = np.array(V, np.float64), np.array(T + S, np.int64), np.array(Wt, np.float64)
    # face winding towards the camera (Cycles shades both sides, but keep normals sane for bump)
    zc = np.array([0.61237244, -0.61237244, 0.5])
    nrm = np.cross(V[T[:, 1]] - V[T[:, 0]], V[T[:, 2]] - V[T[:, 0]])
    flip = nrm @ zc < 0
    T[flip] = T[flip][:, [0, 2, 1]]
    W, H = size
    s = PX
    xc = np.array([0.70710678, 0.70710678, 0])
    yc = np.array([-0.35355339, 0.35355339, 0.8660254])
    target = (W / 2) / s * xc + (-H / 2) / s * yc
    npz = work / f"{name}.npz"
    np.savez(npz, verts=V, tris=T, skirt=skirt, weights=Wt, size=np.array([W, H]), target=target,
             classes=np.array(CLASSES), seed=np.array([seed]), samples=np.array([samples]))
    png = work / f"{name}.png"
    if not png.exists():
        t0 = time.time()
        r = subprocess.run([str(BLENDER), "-b", "--factory-startup", "-noaudio", "-P", str(BATCH_SCRIPT), "--",
                            str(npz), str(png), str(threads)], capture_output=True, text=True, timeout=3600)
        if r.returncode or not png.exists():
            print(r.stdout[-3000:], r.stderr[-3000:])
            raise SystemExit(f"blender failed on {name}")
        print(f"  {name}: {len(placed)} templates, {W}x{H}, {time.time() - t0:.0f}s", flush=True)
    npz.unlink()
    return png, walls


def cut_frames(png: Path, placed, walls):
    img = np.array(Image.open(png).convert("RGBA"))
    out = {}
    for t, v, ox, oy in placed:
        frames = []
        for k in range(t.count):
            if k not in t.tiles:
                frames.append(None)
                continue
            polys, (cx, cy) = tile_polygons(t, k, ox, oy, walls[(t.id, v)])
            pts = np.array([p for poly in polys for p in poly])
            x0, y0 = int(np.floor(pts[:, 0].min())), int(np.floor(pts[:, 1].min()))
            x1, y1 = int(np.ceil(pts[:, 0].max())), int(np.ceil(pts[:, 1].max()))
            if x1 <= x0 or y1 <= y0:     # a slope seen exactly edge-on (e.g. template 41): nothing to draw
                frames.append(None)
                continue
            ys, xs = np.mgrid[y0:y1, x0:x1].astype(float) + 0.5
            m = np.zeros(xs.shape, bool)
            for poly in polys:
                m |= inside(poly, xs, ys)
            crop = img[y0:y1, x0:x1].copy()
            crop[..., 3] = np.where(m, 255, 0)
            crop[~m] = 0
            fx, fy = (x0 + x1) / 2, (y0 + y1) / 2
            frames.append((crop, (fx - cx, fy - cy)))
        out[(t.id, v)] = frames
    return out


# ------------------------------------------------------------------------------------------------ palette and output
def build_palette(all_frames, samples=400_000, seed=1):
    pix = np.concatenate([f[0][f[0][..., 3] > 0][:, :3] for fr in all_frames.values() for f in fr if f is not None])
    rng = np.random.default_rng(seed)
    pix = pix[rng.choice(len(pix), min(samples, len(pix)), replace=False)]
    side = int(math.ceil(math.sqrt(len(pix))))
    buf = np.zeros((side * side, 3), np.uint8)
    buf[:len(pix)] = pix
    buf[len(pix):] = pix[: side * side - len(pix)]
    q = Image.fromarray(buf.reshape(side, side, 3), "RGB").quantize(254, method=Image.Quantize.MEDIANCUT, kmeans=4)
    pal = np.array(q.getpalette()[: 254 * 3], np.uint8).reshape(-1, 3)
    full = np.zeros((256, 3), np.uint8)
    full[2:2 + len(pal)] = pal
    return full


_PAL_IMG = {}


def quantize(rgba, pal):
    """Nearest palette colour among indices 2..255 (no dithering); transparent -> 0."""
    key = pal.tobytes()
    if key not in _PAL_IMG:
        p = pal.copy()
        p[0], p[1] = (255, 0, 255), (0, 255, 255)    # never chosen: reserved for transparency and shadow
        im = Image.new("P", (1, 1))
        im.putpalette(p.ravel().tolist())
        _PAL_IMG[key] = im
    rgb = Image.fromarray(np.ascontiguousarray(rgba[..., :3]), "RGB")
    out = np.array(rgb.quantize(palette=_PAL_IMG[key], dither=Image.Dither.NONE))
    out[rgba[..., 3] == 0] = 0
    return out


EMPTY = []


def write_sheet(path: Path, frames, pal):
    """Indexed PNG with one Frame[i] region per tile (shelf-packed) and its offset."""
    sizes = [(1, 1) if f is None else (f[0].shape[1], f[0].shape[0]) for f in frames]
    width = max(64, max(w for w, _ in sizes))
    x = y = rowh = 0
    pos = []
    for w, h in sizes:
        if x + w > width:
            x, y, rowh = 0, y + rowh, 0
        pos.append((x, y))
        x, rowh = x + w, max(rowh, h)
    height = y + rowh
    sheet = np.zeros((height, width), np.uint8)
    meta = PngInfo()
    radar = []
    for i, (f, (px, py), (w, h)) in enumerate(zip(frames, pos, sizes)):
        if f is None:
            meta.add_text(f"Frame[{i}]", f"{px},{py},1,1;0,0")
            radar.append(None)
            continue
        q = quantize(f[0], pal)
        sheet[py:py + h, px:px + w] = q
        ox, oy = f[1]
        meta.add_text(f"Frame[{i}]", f"{px},{py},{w},{h};{ox:g},{oy:g}")
        col = f[0][f[0][..., 3] > 0][:, :3]
        if len(col) == 0:
            EMPTY.append(path.name + f"[{i}]")
            radar.append(None)
            continue
        lum = col @ np.array([0.3, 0.59, 0.11])
        lo_, hi_ = col[lum <= np.percentile(lum, 35)], col[lum >= np.percentile(lum, 65)]
        radar.append((lo_.mean(0).astype(int), hi_.mean(0).astype(int)))
    im = Image.fromarray(sheet, "P")
    im.putpalette(pal.ravel().tolist())
    im.info["transparency"] = 0
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, pnginfo=meta, optimize=True, transparency=0)
    return radar


def write_pal(path: Path, pal):
    path.write_bytes(bytes(int(c) >> 2 for c in pal.ravel()))


def tileset_yaml(head: str, templates, extras, images, radar):
    def hexc(c):
        return "".join(f"{int(v):02X}" for v in c)

    out = ["# GENERATED by tools/standalone-terrain.py: the RA2-compatible template table with art rendered in Blender\n"
           "# (no RA2 pixels), plus RTS AI corner-transition templates (ids 1000+) for generated maps.\n"]
    head = head.replace("\tEnableDepth: true", "\tEnableDepth: false")
    head = re.sub(r"(?m)^\tEditorTemplateOrder: (.*)$",
                  lambda m: m[0] + ", " + ", ".join(f"RTS AI {c} edges" for c, _ in TRANSITION_SETS), head)
    out.append(head)
    for t in templates:
        b = t.block
        b = re.sub(r"(?m)^\t\tImages: .*$", "\t\tImages: " + ", ".join(images[t.id]), b)
        b = re.sub(r"(?m)^\t\tDepthImages: .*\n", "", b)
        b = re.sub(r"(?m)^\t\tFrames: .*\n", "", b)
        # The RA2 table's ZOffset (-15) pairs with TMP tiles that carry per-pixel depth. Our tiles are flat and
        # depth-free (EnableDepth: false); that offset would hide the resource layer (ore, gems) behind them.
        b = re.sub(r"(?m)^\t\t\t\tZOffset: -?\d+$", "\t\t\t\tZOffset: 0", b)

        def recolor(m):
            k = int(m[1])
            r = radar[t.id][k] if k < len(radar[t.id]) else None
            body = m[3]
            if r:
                body = re.sub(r"MinColor: \w+", "MinColor: " + hexc(r[0]), body)
                body = re.sub(r"MaxColor: \w+", "MaxColor: " + hexc(r[1]), body)
            return m[0].replace(m[3], body)
        b = re.sub(r"(?m)^\t\t\t(\d+): (\S+)\n((?:\t\t\t\t.*\n?)*)", recolor, b)
        out.append(b if b.endswith("\n") else b + "\n")
    for t in extras:
        tile = t.tiles[0]
        r = radar[t.id][0]
        out.append(f"\tTemplate@{t.id}:\n\t\tCategories: {t.category}\n\t\tId: {t.id}\n\t\tImages: {', '.join(images[t.id])}\n"
                   f"\t\tSize: 1, 1\n\t\tTiles:\n\t\t\t0: {tile.type}\n\t\t\t\tMinColor: {hexc(r[0])}\n\t\t\t\tMaxColor: {hexc(r[1])}\n"
                   f"\t\t\t\tZOffset: 0\n\t\t\t\tZRamp: 0\n")
    return "".join(out)


RES_SCRIPT = ROOT / "tools" / "terrain" / "blender_resources.py"
ART_DIR = ROOT / "mods" / "rtsai" / "standalone" / "art"


def render_resources(work: Path, threads: int):
    """Ore (20 variants) and gems (12 variants), 12 densities each, as 60x60 RGBA frames with baked shadows.
    Frame centre = cell centre + (0, -15): the stock resource sequences' Offset, so the piles sit on their cell."""
    kinds = [("ore", 20), ("gem", 12)]
    slots, cols, step = [], 24, 3
    for kind, nv in kinds:
        for v in range(nv):
            for dens in range(1, 13):
                i = len(slots)
                gx, gy = (i % cols) * step, (i // cols) * step     # screen-grid slot -> cell offset below
                ox, oy = gx + gy, gy - gx                          # (dx - dy) * 30 = gx*60, (dx + dy) * 15 = gy*30*.. spaced
                slots.append({"kind": kind, "variant": v, "density": dens, "cx": ox, "cy": oy,
                              "seed": hash((kind, v, dens)) & 0xFFFFFF})
    pts = np.array([project(s["cx"] + 0.5, s["cy"] + 0.5, 0) for s in slots])
    x0, y0 = pts[:, 0].min() - 80, pts[:, 1].min() - 120
    W, H = int(pts[:, 0].max() - x0 + 80), int(pts[:, 1].max() - y0 + 80)
    W, H = W + W % 2, H + H % 2
    # world origin must land on an integer pixel: shift every slot so the image origin is at (x0, y0)
    xc = np.array([0.70710678, 0.70710678, 0])
    yc = np.array([-0.35355339, 0.35355339, 0.8660254])
    target = ((W / 2 + x0) / PX) * xc + (-(H / 2 + y0) / PX) * yc
    job = work / "resources.json"
    png = work / "resources.png"
    job.write_text(json.dumps({"size": [W, H], "target": target.tolist(), "slots": slots}), encoding="utf-8")
    if not png.exists():
        t0 = time.time()
        r = subprocess.run([str(BLENDER), "-b", "--factory-startup", "-noaudio", "-P", str(RES_SCRIPT), "--", str(job), str(png),
                            str(threads)], capture_output=True, text=True, timeout=3600)
        if r.returncode or not png.exists():
            print(r.stdout[-3000:], r.stderr[-3000:])
            raise SystemExit("blender failed on resources")
        print(f"  resources: {len(slots)} piles, {W}x{H}, {time.time() - t0:.0f}s", flush=True)
    img = np.array(Image.open(png).convert("RGBA"))
    frames = {"ore": [], "gem": []}
    for s, (px, py) in zip(slots, pts):
        cx, cy = int(round(px - x0)), int(round(py - y0))
        frames[s["kind"]].append(img[cy - 45:cy + 15, cx - 30:cx + 30].copy())
    ART_DIR.mkdir(parents=True, exist_ok=True)
    for kind, fr in frames.items():
        h, w = fr[0].shape[:2]
        cols_ = 12
        rows = math.ceil(len(fr) / cols_)
        sheet = np.zeros((rows * h, cols_ * w, 4), np.uint8)
        for i, f in enumerate(fr):
            sheet[(i // cols_) * h:(i // cols_ + 1) * h, (i % cols_) * w:(i % cols_ + 1) * w] = f
        meta = PngInfo()
        meta.add_text("FrameSize", f"{w},{h}")
        meta.add_text("FrameAmount", str(len(fr)))
        Image.fromarray(sheet, "RGBA").save(ART_DIR / f"{kind}.png", pnginfo=meta, optimize=True)
    print(f"resources: {ART_DIR / 'ore.png'} (20x12), {ART_DIR / 'gem.png'} (12x12)")


MINE_SCRIPT = ROOT / "tools" / "terrain" / "blender_oremine.py"


def render_mines(work: Path, threads: int):
    """The ore mine: idle + 10 active frames, 90x90 RGBA with baked shadows. The cell centre sits 15 px below the
    frame centre, like the ore piles (sequence Offset 0, -15)."""
    slots = []
    for f in range(11):
        gx, gy = (f % 6) * 3, (f // 6) * 3
        slots.append({"cx": gx + gy, "cy": gy - gx, "frame": f})
    pts = np.array([project(s["cx"] + 0.5, s["cy"] + 0.5, 0) for s in slots])
    x0, y0 = pts[:, 0].min() - 100, pts[:, 1].min() - 140
    W, H = int(pts[:, 0].max() - x0 + 100), int(pts[:, 1].max() - y0 + 100)
    W, H = W + W % 2, H + H % 2
    xc = np.array([0.70710678, 0.70710678, 0])
    yc = np.array([-0.35355339, 0.35355339, 0.8660254])
    target = ((W / 2 + x0) / PX) * xc + (-(H / 2 + y0) / PX) * yc
    job, png = work / "mines.json", work / "mines.png"
    job.write_text(json.dumps({"size": [W, H], "target": target.tolist(), "slots": slots}), encoding="utf-8")
    t0 = time.time()
    r = subprocess.run([str(BLENDER), "-b", "--factory-startup", "-noaudio", "-P", str(MINE_SCRIPT), "--", str(job), str(png),
                        str(threads)], capture_output=True, text=True, timeout=3600)
    if r.returncode or not png.exists():
        print(r.stdout[-3000:], r.stderr[-3000:])
        raise SystemExit("blender failed on the ore mine")
    img = np.array(Image.open(png).convert("RGBA"))
    frames = []
    for (px, py) in pts:
        cx, cy = int(round(px - x0)), int(round(py - y0))
        frames.append(img[cy - 60:cy + 30, cx - 45:cx + 45].copy())
    sheet = np.concatenate(frames, axis=1)
    meta = PngInfo()
    meta.add_text("FrameSize", "90,90")
    meta.add_text("FrameAmount", str(len(frames)))
    ART_DIR.mkdir(parents=True, exist_ok=True)
    Image.fromarray(sheet, "RGBA").save(ART_DIR / "oremine.png", pnginfo=meta, optimize=True)
    print(f"ore mine: {ART_DIR / 'oremine.png'} (11 frames, {time.time() - t0:.0f}s)")


CRATE_SCRIPT = ROOT / "tools" / "terrain" / "blender_crates.py"


def render_crates(work: Path, threads: int):
    """The bonus crate (land, afloat): 60x60 RGBA frames with baked shadow, cell centre 12 px below the frame centre
    like the stock crate (sequence Offset 0, -12)."""
    frames = []
    for kind in ("land", "water"):
        slots = [{"cx": 0, "cy": 0, "kind": kind}]
        px, py = project(0.5, 0.5, 0)
        x0, y0 = px - 60, py - 70
        W, H = 120, 120
        xc = np.array([0.70710678, 0.70710678, 0])
        yc = np.array([-0.35355339, 0.35355339, 0.8660254])
        target = ((W / 2 + x0) / PX) * xc + (-(H / 2 + y0) / PX) * yc
        job, png = work / f"crate-{kind}.json", work / f"crate-{kind}.png"
        job.write_text(json.dumps({"size": [W, H], "target": target.tolist(), "slots": slots}), encoding="utf-8")
        r = subprocess.run([str(BLENDER), "-b", "--factory-startup", "-noaudio", "-P", str(CRATE_SCRIPT), "--", str(job),
                            str(png), str(threads)], capture_output=True, text=True, timeout=1800)
        if r.returncode or not png.exists():
            print(r.stdout[-3000:], r.stderr[-3000:])
            raise SystemExit("blender failed on the crate")
        img = np.array(Image.open(png).convert("RGBA"))
        cx, cy = int(round(px - x0)), int(round(py - y0))
        frames.append(img[cy - 42:cy + 18, cx - 30:cx + 30].copy())     # frame centre 12 px above the cell centre
    sheet = np.concatenate(frames, axis=1)
    meta = PngInfo()
    meta.add_text("FrameSize", "60,60")
    meta.add_text("FrameAmount", "2")
    Image.fromarray(sheet, "RGBA").save(ART_DIR / "crate.png", pnginfo=meta, optimize=True)
    print(f"crate: {ART_DIR / 'crate.png'} (land, water)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--crates", action="store_true", help="render the bonus crate instead of the tileset")
    ap.add_argument("--resources", action="store_true", help="render the ore and gem piles instead of the tileset")
    ap.add_argument("--mines", action="store_true", help="render the ore mine (resource spawn) instead of the tileset")
    ap.add_argument("--only", help="comma-separated template ids (test renders; output goes to --work only)")
    ap.add_argument("--work", type=Path, default=Path(os.environ.get("TEMP", "/tmp")) / "rtsai-terrain")
    ap.add_argument("--threads", type=int, default=max(4, (os.cpu_count() or 8) - 4))
    ap.add_argument("--samples", type=int, default=64)
    ap.add_argument("--per-batch", type=int, default=48)
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()
    a.work.mkdir(parents=True, exist_ok=True)
    if a.resources:
        render_resources(a.work, a.threads)
        return
    if a.mines:
        render_mines(a.work, a.threads)
        return
    if a.crates:
        render_crates(a.work, a.threads)
        return
    head, templates = parse_tileset(SRC_TILESET.read_text(encoding="utf-8"))
    extras = transition_templates()
    alltpl = templates + extras
    if a.only:
        ids = {int(x) for x in a.only.split(",")}
        alltpl = [t for t in alltpl if t.id in ids]
    jobs = []
    for t in alltpl:
        nv = 4 if t.id == 0 else (2 if t.variants > 1 or t.id >= TRANSITION_BASE else 1)
        jobs += [(t, v) for v in range(nv)]
    print(f"{len(alltpl)} templates, {len(jobs)} renders")
    frames = {}
    for bi in range(0, len(jobs), a.per_batch):
        placed, size = layout(jobs[bi:bi + a.per_batch])
        png, walls = render_batch(placed, size, a.work, f"batch{bi // a.per_batch:02d}", a.threads, a.samples, a.seed)
        frames.update(cut_frames(png, placed, walls))
    pal = build_palette(frames)
    if a.only:
        prev = a.work / "preview"
        prev.mkdir(exist_ok=True)
        for (tid, v), fr in frames.items():
            write_sheet(prev / f"t{tid:04d}{'abcd'[v]}.png", fr, pal)
        print(f"test sheets in {prev}")
        return
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for old in OUT_DIR.glob("t*.png"):
        old.unlink()
    write_pal(OUT_DIR / "temperate.pal", pal)
    images, radar = {}, {}
    for (tid, v), fr in sorted(frames.items()):
        name = f"t{tid:04d}{'abcd'[v]}.png"
        r = write_sheet(OUT_DIR / name, fr, pal)
        images.setdefault(tid, []).append(f"ra2|standalone/terrain/{name}")
        radar.setdefault(tid, r)
    OUT_TILESET.parent.mkdir(parents=True, exist_ok=True)
    OUT_TILESET.write_text(tileset_yaml(head, templates, extras, images, radar), encoding="utf-8", newline="\n")
    if EMPTY:
        print(f"warning: {len(EMPTY)} tile frames have no pixels: {EMPTY[:12]}")
    size = sum(p.stat().st_size for p in OUT_DIR.glob("*"))
    print(f"wrote {len(frames)} sheets ({size / 1e6:.1f} MB), {OUT_DIR / 'temperate.pal'}, {OUT_TILESET}")


if __name__ == "__main__":
    main()
