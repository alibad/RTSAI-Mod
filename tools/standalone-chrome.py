#!/usr/bin/env python3
"""Redraw the inherited UI chrome in code: chrome.png, dialog.png, buttons.png, strategic.png, musicplayer.png and
loadscreen.png (mods/rtsai/uibits). The originals came from the upstream OpenRA RA2 mod without a provenance record
and copied RA2's sidebar look, including the Allied eagle and Soviet hammer-and-sickle emblems.

The atlas layout stays as it is, so chrome.yaml and every chrome layout keep working: each rectangle that chrome.yaml
names is redrawn in place, chosen by its collection and region name (button states, sidebar panels, production tabs,
command and stance icons, the radar insignia, power meter, dialog frames...). The style is our own: dark gunmetal
panels with bevels, an accent per side (teal for the Allied-side factions, amber for the Soviet side), and a small
vector glyph set. Everything is drawn with PIL at 4x and downsampled.

usage: python tools/standalone-chrome.py [--preview <dir>]
"""
from __future__ import annotations

import argparse
import math
import re
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "mods" / "rtsai"
UI = MOD / "uibits"
SS = 4

ACCENT = {"allies": (64, 200, 214), "soviets": (238, 164, 58), None: (96, 184, 230)}
STEEL = [(58, 64, 72), (40, 45, 52), (26, 30, 35)]
INK = (8, 10, 12)
GLYPH = (226, 232, 238)
GLYPH_DIS = (110, 116, 124)
ALERT = (238, 70, 58)


# ------------------------------------------------------------------------------------------------ chrome.yaml
def collections():
    text = (MOD / "chrome.yaml").read_text(encoding="utf-8").replace("\r\n", "\n")
    raw = {}
    for b in re.split(r"(?m)^(?=[^\s#])", text):
        if not b.strip():
            continue
        name = b.split(":")[0].strip()
        img = re.search(r"^\tImage: (\S+)", b, re.M)
        inh = re.search(r"^\tInherits: (\S+)", b, re.M)
        pr = re.search(r"^\tPanelRegion: ([\d, ]+)", b, re.M)
        regs = {k: tuple(map(int, v.split(","))) for k, v in re.findall(r"^\t\t([\w\-]+): (\d+, *\d+, *\d+, *\d+)", b, re.M)}
        raw[name] = {"image": img[1] if img else None, "inherits": inh[1] if inh else None,
                     "panel": tuple(map(int, pr[1].split(","))) if pr else None, "regions": regs}

    def resolve(n, depth=0):
        c = dict(raw[n])
        if c["inherits"] and depth < 8 and c["inherits"] in raw:
            p = resolve(c["inherits"], depth + 1)
            c["image"] = c["image"] or p["image"]
            c["panel"] = c["panel"] or p["panel"]
            c["regions"] = {**p["regions"], **c["regions"]}
        return c
    return {n: resolve(n) for n in raw}


def state_of(name: str):
    s = {"hover": "hover" in name, "pressed": "pressed" in name or "active" in name, "disabled": "disabled" in name,
         "highlighted": "highlighted" in name, "alert": "alert" in name or "critical" in name or "danger" in name}
    return s


def side_of(name: str):
    return "allies" if "allies" in name else "soviets" if "soviets" in name else None


# ------------------------------------------------------------------------------------------------ drawing primitives
def lerp(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(len(a)))


def gradient(w, h, top, bottom, noise=6, seed=0):
    t = np.linspace(0, 1, h)[:, None, None]
    img = np.array(top, float)[None, None, :] * (1 - t) + np.array(bottom, float)[None, None, :] * t
    img = np.repeat(img, w, axis=1)
    rng = np.random.default_rng(seed)
    img += rng.normal(0, noise, (h, w, 1))
    a = np.full((h, w, 1), 255.0)
    return Image.fromarray(np.clip(np.concatenate([img, a], 2), 0, 255).astype(np.uint8), "RGBA")


def bevel(im, light=(120, 128, 140), dark=INK, accent=None, radius=0):
    d = ImageDraw.Draw(im)
    w, h = im.size
    d.rectangle([0, 0, w - 1, h - 1], outline=(*dark, 255))
    if w > 3 and h > 3:
        d.line([(1, 1), (w - 2, 1)], fill=(*light, 255))
        d.line([(1, 1), (1, h - 2)], fill=(*lerp(light, dark, 0.35), 255))
        d.line([(1, h - 2), (w - 2, h - 2)], fill=(*lerp(dark, light, 0.25), 255))
    if accent and w > 6 and h > 6:
        d.line([(2, h - 3), (w - 3, h - 3)], fill=(*accent, 255))
    return im


def panel(w, h, side=None, seed=0, accent_line=True, rivets=True):
    if w <= 0 or h <= 0:
        return Image.new("RGBA", (max(w, 1), max(h, 1)), (0, 0, 0, 0))
    im = gradient(w, h, STEEL[0], STEEL[2], seed=seed)
    bevel(im, accent=ACCENT[side] if accent_line else None)
    if rivets and w > 40 and h > 40:
        d = ImageDraw.Draw(im)
        for x, y in ((5, 5), (w - 7, 5), (5, h - 7), (w - 7, h - 7)):
            d.ellipse([x, y, x + 2, y + 2], fill=(150, 156, 166, 255), outline=(12, 14, 16, 255))
    return im


def button(w, h, st, side=None, seed=0):
    if w <= 0 or h <= 0:
        return Image.new("RGBA", (max(w, 1), max(h, 1)), (0, 0, 0, 0))
    acc = ACCENT[side]
    top, bot = (66, 73, 82), (36, 40, 46)
    if st["hover"]:
        top, bot = lerp(top, acc, 0.22), lerp(bot, acc, 0.12)
    if st["pressed"]:
        top, bot = (28, 31, 36), (46, 51, 58)
    if st["highlighted"]:
        top, bot = lerp(top, acc, 0.45), lerp(bot, acc, 0.25)
    if st["disabled"]:
        top, bot = (44, 46, 50), (34, 36, 40)
    im = gradient(w, h, top, bot, noise=3, seed=seed)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, w - 1, h - 1], outline=(*INK, 255))
    if w > 4 and h > 4:
        hi = lerp(top, (255, 255, 255), 0.25) if not st["pressed"] else lerp(top, INK, 0.3)
        d.line([(1, 1), (w - 2, 1)], fill=(*hi, 255))
        edge = acc if (st["hover"] or st["highlighted"]) and not st["disabled"] else lerp(bot, INK, 0.4)
        d.rectangle([1, 1, w - 2, h - 2], outline=(*edge, 255) if (st["hover"] or st["highlighted"]) else None)
    return im


# ------------------------------------------------------------------------------------------------ glyphs
def glyph(name: str, size, color, side=None):
    """Vector glyphs on a transparent canvas of `size` (w, h), drawn at 4x."""
    w, h = size
    im = Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = (*color, 255)
    o = (*INK, 255)
    s = min(w, h) * SS
    cx, cy = w * SS / 2, h * SS / 2
    u = s / 24.0       # glyph unit: designs are on a 24x24 grid

    def P(x, y):
        return (cx + (x - 12) * u, cy + (y - 12) * u)

    def poly(pts, fill=c, width=1.2):
        q = [P(*p) for p in pts]
        d.polygon(q, fill=fill, outline=o)
        d.line(q + [q[0]], fill=o, width=max(1, int(width * u)))

    def line(pts, width=2.2, fill=c):
        q = [P(*p) for p in pts]
        d.line(q, fill=o, width=int((width + 1.4) * u), joint="curve")
        d.line(q, fill=fill, width=int(width * u), joint="curve")

    def circle(x, y, r, fill=None, width=2.0):
        a, b = P(x - r, y - r), P(x + r, y + r)
        if fill:
            d.ellipse([a, b], fill=fill, outline=o, width=max(1, int(u)))
        else:
            d.ellipse([a, b], outline=o, width=int((width + 1.4) * u))
            d.ellipse([a, b], outline=c, width=int(width * u))

    n = name
    if n in ("building", "buildings"):
        poly([(4, 12), (12, 5), (20, 12), (20, 20), (4, 20)])
        poly([(10, 14), (14, 14), (14, 20), (10, 20)], fill=o)
    elif n in ("defense", "support"):
        poly([(12, 3), (20, 6), (19, 14), (12, 21), (5, 14), (4, 6)])
    elif n == "infantry":
        circle(12, 6, 3, fill=c)
        poly([(8, 10), (16, 10), (17, 16), (14, 16), (14, 22), (10, 22), (10, 16), (7, 16)])
    elif n in ("vehicle", "vehicles"):
        poly([(3, 14), (21, 14), (19, 19), (5, 19)])
        poly([(7, 10), (16, 10), (17, 14), (6, 14)])
        line([(15, 11), (22, 9)], 1.6)
    elif n in ("aircraft", "aircrafts"):
        poly([(12, 3), (14, 9), (22, 13), (22, 15), (14, 13), (13, 19), (16, 21), (8, 21), (11, 19), (10, 13), (2, 15), (2, 13), (10, 9)])
    elif n in ("ship", "ships"):
        line([(12, 4), (12, 20)])
        line([(8, 8), (16, 8)])
        line([(5, 14), (8, 19), (16, 19), (19, 14)])
        circle(12, 4, 1.6, fill=c)
    elif n == "repair":
        line([(6, 18), (15, 9)], 3.0)
        circle(16.5, 7.5, 3.6, width=2.4)
    elif n == "sell":
        circle(12, 12, 8, width=2.0)
        line([(12, 6), (12, 18)], 1.6)
        line([(15, 9), (10, 9), (9, 11.5), (15, 12.5), (14, 15), (9, 15)], 1.6)
    elif n in ("power", "power-normal", "power-critical", "production-tooltip-power"):
        poly([(13, 2), (6, 13), (11, 13), (9, 22), (18, 10), (13, 10)])
    elif n in ("cash", "cash-normal", "cash-critical", "production-tooltip-cost"):
        line([(12, 4), (12, 20)], 1.8)
        line([(16, 7), (9, 7), (8, 10.5), (16, 13), (15, 17), (8, 17)], 2.0)
    elif n == "production-tooltip-time":
        circle(12, 12, 8, width=1.8)
        line([(12, 12), (12, 7)], 1.6)
        line([(12, 12), (16, 14)], 1.6)
    elif n == "beacon":
        poly([(12, 21), (6, 11), (8, 5), (12, 3), (16, 5), (18, 11)])
        circle(12, 9, 2.4, fill=o)
    elif n == "diplomacy":
        circle(8, 9, 3, fill=c)
        circle(16, 9, 3, fill=c)
        line([(4, 19), (8, 14), (12, 17), (16, 14), (20, 19)], 2.0)
    elif n == "debug":
        line([(6, 6), (18, 18)], 2.0)
        line([(18, 6), (6, 18)], 2.0)
        circle(12, 12, 4, fill=c)
    elif n == "options":
        for k in range(8):
            a = k * math.pi / 4
            line([(12 + 6 * math.cos(a), 12 + 6 * math.sin(a)), (12 + 9 * math.cos(a), 12 + 9 * math.sin(a))], 2.6)
        circle(12, 12, 5.5, width=2.4)
    elif n == "stats":
        for i, hgt in enumerate((6, 11, 8, 15)):
            poly([(4 + i * 4.5, 20), (7.5 + i * 4.5, 20), (7.5 + i * 4.5, 20 - hgt), (4 + i * 4.5, 20 - hgt)])
    elif n == "attack-move":
        circle(10, 12, 6, width=1.8)
        line([(10, 4), (10, 8)], 1.4)
        line([(10, 16), (10, 20)], 1.4)
        line([(16, 12), (22, 12)], 2.0)
        line([(19, 9), (22, 12), (19, 15)], 2.0)
    elif n == "force-move":
        line([(4, 12), (20, 12)], 2.2)
        line([(15, 7), (20, 12), (15, 17)], 2.2)
    elif n == "force-attack":
        circle(12, 12, 7, width=1.8)
        line([(12, 3), (12, 9)], 1.6)
        line([(12, 15), (12, 21)], 1.6)
        line([(3, 12), (9, 12)], 1.6)
        line([(15, 12), (21, 12)], 1.6)
    elif n in ("guard", "defend"):
        poly([(12, 3), (19, 6), (18, 13), (12, 20), (6, 13), (5, 6)])
    elif n == "deploy":
        for sx in (-1, 1):
            for sy in (-1, 1):
                line([(12 + sx * 2, 12 + sy * 2), (12 + sx * 8, 12 + sy * 8)], 1.8)
                line([(12 + sx * 8, 12 + sy * 4), (12 + sx * 8, 12 + sy * 8), (12 + sx * 4, 12 + sy * 8)], 1.8)
    elif n == "scatter":
        for k in range(6):
            a = k * math.pi / 3 + 0.3
            line([(12 + 3 * math.cos(a), 12 + 3 * math.sin(a)), (12 + 9 * math.cos(a), 12 + 9 * math.sin(a))], 1.8)
    elif n == "stop":
        poly([(6, 6), (18, 6), (18, 18), (6, 18)])
    elif n in ("waypoint", "queue-orders"):
        line([(7, 21), (7, 3)], 1.8)
        poly([(8, 3), (19, 7), (8, 11)])
    elif n == "attack-anything":
        circle(12, 12, 8, width=1.8)
        circle(12, 12, 2.5, fill=c)
    elif n == "hold-fire":
        circle(12, 12, 8, width=1.8)
        line([(6, 18), (18, 6)], 2.0, fill=(*ALERT, 255) if color != GLYPH_DIS else c)
    elif n == "return-fire":
        line([(19, 9), (6, 9)], 1.8)
        line([(10, 5), (6, 9), (10, 13)], 1.8)
        line([(5, 15), (18, 15)], 1.8)
        line([(14, 11), (18, 15), (14, 19)], 1.8)
    elif n in ("play",):
        poly([(7, 4), (19, 12), (7, 20)])
    elif n == "pause":
        poly([(6, 5), (10, 5), (10, 19), (6, 19)])
        poly([(14, 5), (18, 5), (18, 19), (14, 19)])
    elif n == "stop-music":
        poly([(6, 6), (18, 6), (18, 18), (6, 18)])
    elif n in ("next", "fastforward"):
        poly([(4, 5), (12, 12), (4, 19)])
        poly([(12, 5), (20, 12), (12, 19)])
    elif n == "prev":
        poly([(20, 5), (12, 12), (20, 19)])
        poly([(12, 5), (4, 12), (12, 19)])
    elif n == "tick":
        line([(5, 13), (10, 18), (19, 6)], 2.8)
    elif n == "cross":
        line([(6, 6), (18, 18)], 2.6)
        line([(18, 6), (6, 18)], 2.6)
    elif n == "mute":
        poly([(4, 9), (8, 9), (13, 4), (13, 20), (8, 15), (4, 15)])
        line([(16, 9), (21, 15)], 1.6)
        line([(21, 9), (16, 15)], 1.6)
    elif n in ("up", "down", "left", "right", "marker"):
        ang = {"up": -90, "down": 90, "left": 180, "right": 0, "marker": 90}[n]
        a = math.radians(ang)
        pts = [(9, 0), (-5, -7), (-5, 7)]
        poly([(12 + x * math.cos(a) - y * math.sin(a), 12 + x * math.sin(a) + y * math.cos(a)) for x, y in pts])
    else:
        circle(12, 12, 5, fill=c)
    return im.resize((w, h), Image.LANCZOS)


def glyph_for(region: str):
    base = re.sub(r"-(disabled|alert|active|hover|pressed|highlighted|normal|critical)", "", region)
    return base


# ------------------------------------------------------------------------------------------------ the emblem
def emblem(size, accent=(96, 184, 230)):
    """RTS AI emblem: a radar scope with a sweep and three contacts inside a chamfered ring. Drawn here."""
    S = size * SS
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = S / 2
    r = S * 0.42
    oct_ = [(c + r * 1.08 * math.cos(math.radians(22.5 + 45 * k)), c + r * 1.08 * math.sin(math.radians(22.5 + 45 * k))) for k in range(8)]
    d.polygon(oct_, fill=(30, 36, 44, 255), outline=(*INK, 255))
    d.line(oct_ + [oct_[0]], fill=(150, 160, 172, 255), width=int(S * 0.018))
    d.ellipse([c - r * 0.86, c - r * 0.86, c + r * 0.86, c + r * 0.86], fill=(12, 34, 40, 255))
    sweep = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sweep)
    for k in range(60):
        a0, a1 = -100 + k, -99 + k
        sd.pieslice([c - r * 0.84, c - r * 0.84, c + r * 0.84, c + r * 0.84], a0, a1, fill=(*accent, int(4 + k * 3.2)))
    im.alpha_composite(sweep)
    for rr in (0.28, 0.56, 0.84):
        d.ellipse([c - r * rr, c - r * rr, c + r * rr, c + r * rr], outline=(*lerp(accent, (20, 40, 46), 0.45), 255), width=int(S * 0.008))
    d.line([(c - r * 0.84, c), (c + r * 0.84, c)], fill=(*lerp(accent, (20, 40, 46), 0.5), 255), width=int(S * 0.006))
    d.line([(c, c - r * 0.84), (c, c + r * 0.84)], fill=(*lerp(accent, (20, 40, 46), 0.5), 255), width=int(S * 0.006))
    a = math.radians(-40)
    d.line([(c, c), (c + r * 0.84 * math.cos(a), c + r * 0.84 * math.sin(a))], fill=(*accent, 255), width=int(S * 0.014))
    for (x, y) in ((0.42, -0.30), (-0.38, 0.22), (0.12, 0.52)):
        px, py = c + r * x, c + r * y
        d.ellipse([px - S * 0.018, py - S * 0.018, px + S * 0.018, py + S * 0.018], fill=(230, 250, 255, 255))
    return im.resize((size, size), Image.LANCZOS)


# ------------------------------------------------------------------------------------------------ dispatcher
def draw_rect(atlas: Image.Image, coll: str, region: str | None, rect, seed: int):
    x, y, w, h = rect
    if w <= 0 or h <= 0 or x >= atlas.width or y >= atlas.height:
        return
    st = state_of(coll + "-" + (region or ""))
    side = side_of(coll)
    base = re.sub(r"-(allies|soviets)", "", coll)
    base = re.sub(r"-(hover|pressed|disabled|highlighted|focused)", "", base)
    acc = ACCENT[side]
    gcol = GLYPH_DIS if st["disabled"] else (ALERT if st["alert"] else (acc if st["highlighted"] or st["pressed"] else GLYPH))
    tile = None
    if base == "sidebar" and region:
        tile = panel(w, h, side, seed)
        if region == "background-top":
            d = ImageDraw.Draw(tile)
            # radar screen window and the power bar slot
            d.rectangle([14, 42, w - 15, h - 62], fill=(10, 22, 26, 255), outline=(*INK, 255))
            d.rectangle([13, 41, w - 14, h - 61], outline=(*acc, 255))
            d.rectangle([20, h - 50, w - 21, h - 30], fill=(18, 21, 25, 255), outline=(*INK, 255))
        elif region == "background-iconrow":
            d = ImageDraw.Draw(tile)
            for i in range(3):
                x0 = 20 + i * 64
                d.rectangle([x0, 1, x0 + 60, h - 2], fill=(14, 16, 19, 255), outline=(*INK, 255))
    elif base == "radar" and region == "insignia":
        tile = Image.new("RGBA", (w, h), (10, 22, 26, 255))
        e = emblem(min(w, h) - 8, acc)
        tile.alpha_composite(e, ((w - e.width) // 2, (h - e.height) // 2))
    elif base in ("power-icons", "cash-icons", "production-icons", "command-icons", "stance-icons", "order-icons"):
        tile = glyph(glyph_for(region), (w, h), gcol, side)
    elif base == "sidebar-bits" and region:
        if region.startswith("production-tooltip"):
            tile = glyph(region, (w, h), GLYPH)
        elif region == "production-iconoverlay":
            tile = Image.new("RGBA", (w, h), (0, 0, 0, 150))
        else:
            tile = panel(w, h, side, seed, rivets=False)
    elif base == "power-meter" and region:
        col = {"power-meter-available": (90, 220, 110), "power-meter-danger": ALERT, "power-meter-disabled": (90, 92, 96),
               "power-meter-none": (30, 34, 38), "power-meter-used": (240, 200, 70)}.get(region, (120, 120, 120))
        tile = gradient(w, h, lerp(col, (255, 255, 255), 0.2), lerp(col, INK, 0.3), noise=2)
    elif base == "reload-icon" and region:
        tile = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(tile)
        k = 12 if region == "enabled" else int(region.split("-")[1])
        d.ellipse([1, 1, w - 2, h - 2], outline=(*INK, 255), width=2)
        d.arc([1, 1, w - 2, h - 2], -90, -90 + 30 * k, fill=(*(GLYPH if region == "enabled" else (150, 150, 150)), 255), width=2)
    elif base == "strategic" and region:
        col = {"player_owned": (90, 220, 110), "enemy_owned": ALERT, "critical_unowned": (240, 200, 70), "unowned": (180, 180, 180)}[region]
        tile = glyph("waypoint", (w, h), col)
    elif base == "music" and region:
        tile = glyph("stop-music" if region == "stop" else region, (w, h), GLYPH)
    elif base in ("checkmark-tick", "checkmark-cross", "checkmark-mute") and region:
        tile = glyph(base.split("-")[1], (w, h), acc if region.startswith("checked") else (90, 96, 104)) \
            if region.startswith("checked") else Image.new("RGBA", (w, h), (0, 0, 0, 0))
    elif base in ("scrollpanel-decorations", "dropdown-decorations") and region:
        tile = glyph(region.split("-")[0], (w, h), GLYPH_DIS if "disabled" in region else GLYPH)
    elif base == "logos":
        tile = emblem(min(w, h))
    elif base == "dropdown-separators" and region:
        tile = gradient(w, h, (70, 76, 86), (40, 44, 50), noise=1)
    elif base == "slider" and region == "tick":
        tile = gradient(w, h, (150, 156, 166), (90, 96, 104), noise=1)
    elif base in ("dialog", "dialog4", "dialog5", "mainmenu-border", "sidebar-observer", "sidebar-button-observer",
                  "observer-scrollpanel-button") or base.startswith("dialog"):
        tile = panel(w, h, None, seed, accent_line=base in ("dialog", "mainmenu-border"))
    elif base in ("progressbar-bg",):
        tile = gradient(w, h, (18, 21, 25), (28, 32, 37), noise=2)
        bevel(tile, light=(50, 54, 60))
    elif base in ("progressbar-thumb",):
        tile = gradient(w, h, lerp(acc, (255, 255, 255), 0.25), lerp(acc, INK, 0.35), noise=2)
        bevel(tile)
    else:
        # every remaining panel collection is a button-like control (sidebar tabs, scroll buttons, checkboxes...)
        tile = button(w, h, st, side, seed)
        icon = {"buildings-button": "building", "support-button": "defense", "infantry-button": "infantry",
                "vehicles-button": "vehicle", "aircrafts-button": "aircraft", "ships-button": "ship",
                "repair-button": "repair", "sell-button": "sell", "beacon-button": "beacon",
                "diplomacy-button": "diplomacy", "debug-button": "debug", "options-button": "options",
                "stats-button": "stats", "scrollup-buttons": "up", "scrollup-button": "up",
                "scrolldown-buttons": "down", "scrolldown-button": "down"}.get(base)
        if icon:
            g = glyph(icon, (min(w, h) - 6, min(w, h) - 6), gcol)
            tile.alpha_composite(g, ((w - g.width) // 2, (h - g.height) // 2))
    # paste, clipped to the atlas
    tile = tile.crop((0, 0, min(w, atlas.width - x), min(h, atlas.height - y)))
    atlas.paste(tile, (x, y))


def build(preview: Path | None):
    cols = collections()
    sizes = {}
    for f in ["chrome.png", "dialog.png", "buttons.png", "strategic.png", "musicplayer.png", "loadscreen.png"]:
        with open(UI / f, "rb") as fh:
            hdr = fh.read(24)
        sizes[f] = (int.from_bytes(hdr[16:20], "big"), int.from_bytes(hdr[20:24], "big"))
    atlases = {f: Image.new("RGBA", s, (0, 0, 0, 0)) for f, s in sizes.items()}
    # draw panels first, then regions, so small regions inside a panel area win
    jobs = []
    for i, (name, c) in enumerate(cols.items()):
        img = c["image"]
        if img not in atlases:
            continue
        if c["panel"]:
            x, y, a, b, cc, d, e, f = c["panel"]
            jobs.append((0, img, name, None, (x, y, a + cc + e, b + d + f), i))
        for rn, r in c["regions"].items():
            jobs.append((1, img, name, rn, r, i))
    for _, img, name, rn, rect, i in sorted(jobs, key=lambda j: (j[0], -(j[4][2] * j[4][3]))):
        draw_rect(atlases[img], name, rn, rect, seed=i)
    # load screen: logo (0,0,256,256) + a horizontal stripe tile (258,0,253,256) used across the screen width
    ls = atlases["loadscreen.png"]
    stripe = gradient(253, 256, (16, 20, 24), (16, 20, 24), noise=4, seed=3)
    sd = ImageDraw.Draw(stripe)
    for k in range(0, 256, 4):
        sd.line([(0, k), (252, k)], fill=(22, 27, 32, 255))
    sd.line([(0, 2), (252, 2)], fill=(*ACCENT[None], 255), width=2)
    sd.line([(0, 253), (252, 253)], fill=(*ACCENT[None], 255), width=2)
    ls.paste(stripe, (258, 0))
    ls.paste(Image.new("RGBA", (256, 256), (16, 20, 24, 255)), (0, 0))
    ls.alpha_composite(emblem(240), (8, 8))
    for f, im in atlases.items():
        im.save(UI / f, optimize=True)
        if preview:
            bg = Image.new("RGBA", im.size, (52, 60, 52, 255))
            bg.alpha_composite(im)
            bg.save(preview / f"new-{f}")
    spare = UI / "spawnpoints.png"
    if spare.exists():
        spare.unlink()   # referenced by nothing
    print("chrome: " + ", ".join(f"{f} {s[0]}x{s[1]}" for f, s in sizes.items()))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--preview", type=Path)
    a = ap.parse_args()
    if a.preview:
        a.preview.mkdir(parents=True, exist_ok=True)
    build(a.preview)


if __name__ == "__main__":
    main()
