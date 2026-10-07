#!/usr/bin/env python3
"""Original 1v1 maps for the standalone game, generated from code on the Blender tileset's corner-transition templates.

Each map is a few continuous fields (coast, river, lakes, dirt roads, rough ground) sampled at cell CORNERS. A cell's
template follows from its four corners (ids 1000+ in tools/standalone-terrain.py: grass with water, dirt, rough or
sand on any subset of corners), so coastlines and roads join smoothly across cells. Layouts are symmetric for fair
1v1 play: Twin Fords is point-symmetric, Harbor Line is mirror-symmetric with a sea for naval play. Ore and gem
fields go on Clear/Rough cells only (the ResourceLayer rule); each home ore field has an ore mine at its centre that
regrows the ore (without one the fields ran dry by about minute 10 and games stalled). No scenery: every actor type on
these maps is ours.

  python tools/standalone-maps.py      # writes mods/rtsai/standalone/maps/{twin-fords,harbor-line}/{map.yaml,map.bin,map.png}

The preview (map.png) is drawn the way Map.SavePreview draws it, from the tileset's radar colours.
"""
from __future__ import annotations

import io
import math
import re
import struct
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
MAPS = ROOT / "mods" / "rtsai" / "standalone" / "maps"   # standalone only: the classic tilesets lack the 1000+ templates
TILESET = ROOT / "mods" / "rtsai" / "standalone" / "tilesets" / "temperat.yaml"
SETS = {"water": 0, "dirt": 1, "rough": 2, "sand": 3}       # order of TRANSITION_SETS in standalone-terrain.py
PRIORITY = ["water", "dirt", "sand", "rough"]
GRASS = 0


def tid(cls: str, mask: int) -> int:
    return GRASS if mask == 0 else 1000 + SETS[cls] * 16 + mask


def mpos_to_cpos(u, v):
    off = v & 1
    return (v + off) // 2 + u, (v - off) // 2 - u


def cpos_to_mpos(x, y):
    v = x + y
    return (v - (v & 1)) // 2 - y, v


def seg_dist(p, a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    ab = b - a
    t = np.clip(((p[..., 0] - a[0]) * ab[0] + (p[..., 1] - a[1]) * ab[1]) / (ab @ ab), 0, 1)
    return np.hypot(p[..., 0] - (a[0] + t * ab[0]), p[..., 1] - (a[1] + t * ab[1]))


# Road directions whose edges come out straight on the corner-transition templates, in the isotropic plane
# (px, py): along a cell axis (2:1 on screen) or along x + y or x - y (screen horizontal or vertical). Corners at the
# same distance from such a line share a row, so the road band switches whole rows of corners and its edge is a
# straight run of half-cell or chamfer templates. Any other slope steps from row to row: the staircase edge.
CLEAN = [np.array(d, float) / np.hypot(*d) for d in
         ((1, 0), (1, 0.5), (0, 1), (-1, 0.5), (-1, 0), (-1, -0.5), (0, -1), (1, -0.5))]


# The cell axes only. A boundary along them crosses the transition templates through two adjacent corners, the
# half-cell templates, so it draws one straight edge. Screen-horizontal and screen-vertical boundaries alternate
# one-corner and three-corner templates: fine under a wide road, a sawtooth along a thin strip of shore.
AXES = [CLEAN[1], CLEAN[3], CLEAN[5], CLEAN[7]]


def clean_path(a, b, dirs=None):
    """The Z from a to b along CLEAN directions: a short leg along the minor direction, the long run along the
    dominant one, then the rest of the minor leg. The two neighbouring directions that bracket b - a span it with
    non-negative lengths. Point reflection and mirroring map the Z onto itself, so symmetric maps stay fair.
    Returns the vertices [a, p1, p2, b]."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    dirs = CLEAN if dirs is None else dirs
    v = b - a
    ang = [math.atan2(d[1], d[0]) % (2 * math.pi) for d in dirs]
    t = math.atan2(v[1], v[0]) % (2 * math.pi)
    for i in range(len(dirs)):
        lo, hi = ang[i], ang[(i + 1) % len(dirs)]
        span = (hi - lo) % (2 * math.pi)
        if (t - lo) % (2 * math.pi) <= span + 1e-9:
            d1, d2 = dirs[i], dirs[(i + 1) % len(dirs)]
            break
    k1, k2 = np.linalg.solve(np.stack([d1, d2], 1), v)
    (major, kM), (minor, km) = ((d1, k1), (d2, k2)) if k1 >= k2 else ((d2, k2), (d1, k1))
    p1 = a + minor * km / 2
    p2 = p1 + major * kM
    return [a, p1, p2, b]


def clean_polyline(points, dirs=None):
    """Waypoints joined by clean Zs: the vertex list of one path."""
    out = [np.asarray(points[0], float)]
    for a, b in zip(points, points[1:]):
        out += clean_path(a, b, dirs)[1:]
    return out


def poly_dist(P, verts):
    d = np.full(P.shape[:2], np.inf)
    for s, e in zip(verts, verts[1:]):
        if np.hypot(*(e - s)) > 1e-6:
            d = np.minimum(d, seg_dist(P, s, e))
    return d


def road_mask(P, a, b, half_width=1.1):
    """A road from a to b along a clean Z (see clean_path)."""
    return poly_dist(P, clean_path(a, b)) < half_width


def cell_xy(P):
    """Plane coordinates (px = x - y, py = (x + y) / 2) -> cell coordinates (x, y); lines of constant x or y run
    along the cell axes, which are clean directions."""
    return P[..., 1] + P[..., 0] / 2, P[..., 1] - P[..., 0] / 2


def coast_line(xs, ys):
    """An x-monotonic coastline through waypoints (xs ascending) along the two cell axes only (slopes +-0.5 in the
    plane): between waypoints a rising run then a falling one (or the reverse), sized so the pair spans the step.
    Returns (vx, vy) vertices for np.interp. A step steeper than the axes is clamped to them."""
    vx, vy = [xs[0]], [ys[0]]
    for i, (x0, y0, x1, y1) in enumerate(zip(xs, ys, xs[1:], ys[1:])):
        dx = x1 - x0
        dy = float(np.clip(y1 - y0, -0.5 * dx, 0.5 * dx))
        up = dx / 2 + dy             # run at slope +0.5; the rest (dx / 2 - dy) at -0.5
        if i % 2:                    # alternate the order so the line zigzags instead of drifting
            vx += [x0 + (dx - up), x1]
            vy += [y0 - 0.5 * (dx - up), y0 + dy]
        else:
            vx += [x0 + up, x1]
            vy += [y0 + 0.5 * up, y0 + dy]
    return np.array(vx), np.array(vy)


def smooth_noise(px, py, seed, scale):
    r = np.random.default_rng(seed)
    s = 0
    for k in range(5):
        w = r.normal(size=2) * (k + 1) / scale
        s = s + np.sin(px * w[0] + py * w[1] + r.uniform(0, 6.3)) / (k + 1)
    return s / 2.3


class MapBuilder:
    def __init__(self, w: int, h: int):
        self.w, self.h = w, h
        # corner grid in CPos space covering every cell of the MPos rectangle
        cells = [mpos_to_cpos(u, v) for u in range(w) for v in range(h)]
        xs, ys = [c[0] for c in cells], [c[1] for c in cells]
        self.x0, self.y0 = min(xs), min(ys)
        self.cx, self.cy = max(xs) - self.x0 + 2, max(ys) - self.y0 + 2
        X, Y = np.meshgrid(np.arange(self.cx) + self.x0, np.arange(self.cy) + self.y0, indexing="xy")
        # isotropic plane coordinates in 30 px units: px = x - y, py = (x + y) / 2
        self.px, self.py = (X - Y).astype(float), (X + Y) / 2.0   # cell centres (corner average): (x + y + 1) / 2
        self.cls = np.full(X.shape, "grass", dtype=object)

    def paint(self, mask, cls):
        self.cls[mask] = cls

    def cell_center(self, x, y):
        return x - y, (x + y) / 2.0

    def tiles(self):
        out = {}
        for u in range(self.w):
            for v in range(self.h):
                x, y = mpos_to_cpos(u, v)
                i, j = x - self.x0, y - self.y0
                corners = [self.cls[j, i], self.cls[j, i + 1], self.cls[j + 1, i + 1], self.cls[j + 1, i]]   # tl tr br bl
                present = [c for c in PRIORITY if c in corners]
                if not present:
                    out[(u, v)] = (GRASS, 0)
                    continue
                c = present[0]
                mask = sum(1 << k for k, cc in enumerate(corners) if cc == c)
                out[(u, v)] = (tid(c, mask), 0)
        return out


def terrain_types():
    """template id -> (terrain type of tile 0, (min colour, max colour)), and terrain type -> colour, from the tileset."""
    text = TILESET.read_text(encoding="utf-8")
    types = {}
    for b in re.split(r"(?m)^(?=\tTemplate@)", text)[1:]:
        t = int(re.search(r"^\t\tId: (\d+)", b, re.M)[1])
        m = re.search(r"^\t\t\t0: (\S+)\n\t\t\t\tMinColor: (\w+)\n\t\t\t\tMaxColor: (\w+)", b, re.M)
        if m:
            types[t] = (m[1], tuple(int(m[2][k:k + 2], 16) for k in (0, 2, 4)), tuple(int(m[3][k:k + 2], 16) for k in (0, 2, 4)))
    tcol = {m[1]: tuple(int(m[2][k:k + 2], 16) for k in (0, 2, 4))
            for m in re.finditer(r"TerrainType@\w+:\n\t\tType: (\w+)\n(?:\t\t.*\n)*?\t\tColor: (\w+)", text)}
    return types, tcol


def write_map(name: str, title: str, mb: MapBuilder, spawns, resources, description: str, mines=()):
    types, tcol = terrain_types()
    for m in mines:                       # a mine is a building: no ore under it
        resources.pop(m, None)
    tiles = mb.tiles()
    w, h = mb.w, mb.h
    res = {}
    for (x, y), (rtype, dens) in resources.items():
        u, v = cpos_to_mpos(x, y)
        if not (1 <= u < w - 1 and 1 <= v < h - 1):
            continue
        ttype = types[tiles[(u, v)][0]][0]
        if ttype in ("Clear", "Rough", "Road"):
            res[(u, v)] = (rtype, dens)
    area = w * h
    data = bytearray(17 + area * 3 + area + area * 2)
    struct.pack_into("<BHHIII", data, 0, 2, w, h, 17, 17 + area * 3, 17 + area * 4)
    for u in range(w):
        for v in range(h):
            i = u * h + v
            t, idx = tiles[(u, v)]
            struct.pack_into("<HB", data, 17 + i * 3, t, idx)
            r = res.get((u, v), (0, 0))
            struct.pack_into("<BB", data, 17 + area * 4 + i * 2, *r)
    d = MAPS / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "map.bin").write_bytes(bytes(data))
    players = ("\tPlayerReference@Neutral:\n\t\tName: Neutral\n\t\tOwnsWorld: True\n\t\tNonCombatant: True\n\t\tFaction: china\n"
               "\tPlayerReference@Creeps:\n\t\tName: Creeps\n\t\tNonCombatant: True\n\t\tFaction: china\n\t\tEnemies: Multi0, Multi1\n")
    for k in range(2):
        players += (f"\tPlayerReference@Multi{k}:\n\t\tName: Multi{k}\n\t\tPlayable: True\n\t\tFaction: Random\n"
                    f"\t\tEnemies: Creeps\n")
    actors = "".join(f"\tSpawn{k}: mpspawn\n\t\tOwner: Neutral\n\t\tLocation: {x},{y}\n" for k, (x, y) in enumerate(spawns))
    actors += "".join(f"\tMine{k}: oremine\n\t\tOwner: Neutral\n\t\tLocation: {x},{y}\n" for k, (x, y) in enumerate(mines))
    yaml = (f"MapFormat: 12\n\nRequiresMod: rtsai\n\nTitle: {title}\n\nAuthor: RTS AI (generated by tools/standalone-maps.py)\n\n"
            f"Tileset: TEMPERATE\n\nMapSize: {w},{h}\n\nBounds: 1,1,{w - 2},{h - 2}\n\nVisibility: Lobby\n\nCategories: Conquest\n\n"
            f"Players:\n{players}\nActors:\n{actors}")
    (d / "map.yaml").write_text(yaml, encoding="utf-8", newline="\n")
    # preview, as Map.SavePreview: two pixels per cell, odd rows shifted right by one
    bw, bh = 2 * (w - 2) - 1, h - 2
    img = np.zeros((bh, bw, 4), np.uint8)
    for yy in range(bh):
        for xx in range(w - 2):
            u, v = xx + 1, yy + 1
            if (u, v) in res:
                c = tcol.get("Ore" if res[(u, v)][0] == 1 else "Gems", (150, 128, 96))
                left = right = c
            else:
                _, lo, hi = types[tiles[(u, v)][0]]
                left, right = lo, hi
            dx = v & 1
            xo = 2 * xx + dx
            if xx + dx > 0:
                img[yy, xo - 1] = (*left, 255)
            if xo < bw:
                img[yy, xo] = (*right, 255)
    Image.fromarray(img, "RGBA").save(d / "map.png")
    print(f"{name}: {w}x{h}, {sum(1 for t in tiles.values() if t[0] != GRASS)} non-grass cells, {len(res)} resource cells, "
          f"spawns {spawns} - {description}")


# ------------------------------------------------------------------------------------------------ the maps
def twin_fords():
    """Two bases split by a winding river with two fords and a central crossing; ore at home, gems by the two fords.
    Point-symmetric. (The central crossing came in after a balance measurement: with two fords only, 37% of bot
    games ended in a draw at the 40-minute cap, a grind at the two chokepoints.)"""
    mb = MapBuilder(64, 128)
    P = np.stack([mb.px, mb.py], -1)
    cxy = np.array([64.0, 32.0])
    a, b = np.array([0.0, 4.0]), np.array([128.0, 60.0])
    d_ab = b - a
    L = np.linalg.norm(d_ab)
    n = np.array([-d_ab[1], d_ab[0]]) / L
    fords = [0.21, -0.21]

    def centre(tt):                                  # the meander the river follows (t in [-0.5, 0.5])
        return a + (tt + 0.5) * d_ab + n * (5.0 * np.sin(3 * np.pi * tt))

    # Waypoints on the meander (point-symmetric set, fords included), joined by clean Zs: the banks are straight
    # runs along clean directions instead of a one-cell staircase.
    ts = sorted({-0.5, -0.36, -0.21, -0.1, 0.0, 0.1, 0.21, 0.36, 0.5})
    river = clean_polyline([centre(tt) for tt in ts], AXES)
    dist = poly_dist(P, river)
    X, Y = cell_xy(P)
    in_ford = np.zeros(dist.shape, bool)
    # the two gem fords (half-width 3.9 cells, widened 50% after the balance agent's draw measurements) and the
    # central crossing (2.6), each cut along the y axis: straight ford edges
    for f, half in [(f, 3.9) for f in fords] + [(0.0, 2.6)]:
        fx, fy = cell_xy(centre(f))
        in_ford |= np.abs(X - fx) < half
    water = (dist < 3.4) & ~in_ford
    sand = (dist < 3.4) & in_ford
    noise = smooth_noise(P[..., 0], P[..., 1], 3, 9.0)
    noise = (noise + smooth_noise(2 * cxy[0] - P[..., 0], 2 * cxy[1] - P[..., 1], 3, 9.0)) / 2
    rough = (noise > 0.45) & (dist > 6)
    spawns_p = [np.array([26.0, 47.0]), 2 * cxy - np.array([26.0, 47.0])]
    ford_p = [centre(f) for f in fords]
    road = np.zeros(dist.shape, bool)
    for s in spawns_p:
        for q in ford_p:                             # the central crossing has no road: one would cross the home ore
            road |= road_mask(P, s, q)
    for s in spawns_p:
        rough &= np.hypot(P[..., 0] - s[0], P[..., 1] - s[1]) > 10
    mb.paint(rough, "rough")
    mb.paint(road & ~water, "dirt")
    mb.paint(sand, "sand")
    mb.paint(water, "water")
    spawns = [cell_at(mb, s) for s in spawns_p]
    resources, mines = {}, []
    for s, sign in zip(spawns_p, (1, -1)):
        for c in (s + sign * np.array([12.0, -2.0]), s + sign * np.array([-8.0, 7.0])):
            field(resources, mb, c, 4.2, 1)
            mines.append(cell_at(mb, c))
    for q, sign in zip(ford_p, (1, -1)):
        field(resources, mb, q + sign * np.array([0.0, 9.0]), 3.0, 2)
        field(resources, mb, q - sign * np.array([0.0, 9.0]), 3.0, 2)
    write_map("twin-fords", "Twin Fords", mb, spawns, resources,
              "river with two gem fords and a central crossing, point-symmetric", mines)


def harbor_line():
    """A sea along the north edge for naval play, a central lake with gems on its shore, ore at home. Mirror-symmetric."""
    mb = MapBuilder(64, 128)
    P = np.stack([mb.px, mb.py], -1)
    mx = 64.0
    ax = np.abs(P[..., 0] - mx)

    def coast_fn(x):
        return 11.0 + 3.0 * np.cos(2 * np.pi * np.abs(x - mx) / 44.0) + 1.5 * np.cos(2 * np.pi * np.abs(x - mx) / 17.0)

    # Coastline waypoints every 8 px, mirror-symmetric about mx, joined by flat runs and cell-axis slopes.
    wx = np.concatenate([mx - np.arange(80, 0, -8), [mx], mx + np.arange(8, 88, 8)])
    vx, vy = coast_line(wx, coast_fn(wx))
    coast = np.interp(P[..., 0], vx, vy)
    sea = P[..., 1] < coast
    # The lake: an octagon with clean sides (screen horizontal and vertical, both cell axes) instead of an ellipse.
    lx, ly = P[..., 0] - mx, P[..., 1] - 33.0
    lake = (np.abs(lx) <= 8.6) & (np.abs(ly) <= 5.4) & (np.abs(ly + lx / 2) <= 7.2) & (np.abs(ly - lx / 2) <= 7.2)
    noise = smooth_noise(ax, P[..., 1], 11, 8.0)
    rough = (noise > 0.4) & (P[..., 1] > coast + 4) & ~lake
    spawns_p = [np.array([mx - 40.0, 46.0]), np.array([mx + 40.0, 46.0])]
    road = road_mask(P, spawns_p[0], np.array([mx, 52.0]))
    road |= road_mask(P, spawns_p[1], np.array([mx, 52.0]))
    for sgn in (-1, 1):
        road |= road_mask(P, np.array([mx + sgn * 40.0, 46.0]), np.array([mx + sgn * 26.0, coast.min() + 2]))
    for s in spawns_p:
        rough &= np.hypot(P[..., 0] - s[0], P[..., 1] - s[1]) > 10
    shore = (P[..., 1] < coast + 1.6) & ~sea
    mb.paint(rough, "rough")
    mb.paint(shore, "sand")
    mb.paint(road & ~sea, "dirt")
    mb.paint(lake | sea, "water")
    spawns = [cell_at(mb, s) for s in spawns_p]
    resources, mines = {}, []
    for s, sgn in zip(spawns_p, (1, -1)):
        for c, r in ((s + np.array([sgn * 11.0, -6.0]), 4.0), (s + np.array([sgn * 3.0, 9.0]), 3.6)):
            field(resources, mb, c, r, 1)
            mines.append(cell_at(mb, c))
    field(resources, mb, np.array([mx - 9.0, 40.0]), 2.6, 2)
    field(resources, mb, np.array([mx + 9.0, 40.0]), 2.6, 2)
    write_map("harbor-line", "Harbor Line", mb, spawns, resources, "north sea, central lake, mirror-symmetric", mines)


def cell_at(mb: MapBuilder, p):
    """CPos of the cell whose centre is nearest to plane point p."""
    px, py = p
    # px = x - y, py = (x + y + 1) / 2 at the cell centre (x + .5, y + .5)
    s = 2 * py - 1
    x = round((px + s) / 2)
    y = round((s - px) / 2)
    return int(x), int(y)


def field(resources, mb: MapBuilder, centre, radius, rtype):
    cx, cy = cell_at(mb, centre)
    r = int(math.ceil(radius * 1.6))
    for x in range(cx - r, cx + r + 1):
        for y in range(cy - r, cy + r + 1):
            px, py = x - y, (x + y + 1) / 2
            d = math.hypot(px - centre[0], py - centre[1])
            if d < radius:
                resources[(x, y)] = (rtype, max(1, min(12, int(round(12 * (1 - d / radius) + 2)))))


if __name__ == "__main__":
    twin_fords()
    harbor_line()
