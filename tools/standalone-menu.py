#!/usr/bin/env python3
"""The standalone main menu's backdrop: one flagship vehicle per faction, rendered from the project's own models.

  1. render (tools/menu/blender_lineup.py): the seven GLB meshes from RTSAI-Art (units/<actor>/candidates/
     mesh-v1-role-rebuild/web.glb) on a procedural desert at golden hour, Cycles on the CPU.
  2. grade (here): a darker left third behind the menu panel, a soft vignette.
  3. write mods/rtsai/standalone/art/menu-backdrop.png: the 1920x1080 picture at 0,0 of a power-of-two sheet (the
     `rtsai-menu` chrome collection; OpenRA.Mods.RTSAI/Widgets/CoverImageWidget.cs draws it to cover the window).

usage: python tools/standalone-menu.py [--quick] [--samples 128] [--threads 20] [--work DIR]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ART_ROOT = ROOT.parent / "RTSAI-Art"
BLENDER = Path(r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe")
SCRIPT = ROOT / "tools" / "menu" / "blender_lineup.py"
OUT = ROOT / "mods" / "rtsai" / "standalone" / "art" / "menu-backdrop.png"
METRES_PER_VOXEL = 0.14   # the voxel route's length class (units/<actor>/voxel-route.json "fit") in metres

# One flagship per faction: (actor, screen x in [-1, 1], row, yaw jitter). An RTS-style raised camera looks along
# +Y; the front row stands at FRONT metres, the back row at BACK metres, laterally between the front vehicles, so
# nothing hides a neighbour. All face the camera turned FACING degrees toward screen-left.
LINEUP = [
    ("r2ymlr", -0.25, "back", -3.0),       # Yemen
    ("r2merkava", 0.11, "back", 2.0),      # Israel
    ("r2hzrockets", 0.465, "back", -2.0),   # Hezbollah
    ("r2qilin", 0.79, "back", 3.0),        # China
    ("r2karrar", -0.07, "front", 2.0),     # Iran
    ("r2bozkir", 0.285, "front", -3.0),     # Türkiye
    ("r2m1a2s", 0.625, "front", 3.0),       # Saudi Arabia
]
# Safe area: the menu draws the picture to cover the window (cropping 16:10 and 4:3 at the sides) with a 340 px menu
# band on the left, so the vehicles stay between about x = 600 and x = 1850 of the 1920 px frame.
FRONT, BACK, FACING = 28.0, 37.0, 35.0
LENS_MM = 30.0
CAMERA_HEIGHT = 7.0


def job(work: Path, args) -> dict:
    vehicles = []
    half = 18.0 / LENS_MM                          # tan(horizontal half field of view), 36 mm sensor
    for actor, sx, row, jitter in LINEUP:
        y = FRONT if row == "front" else BACK
        x, yaw = sx * y * half, -FACING + jitter
        unit = ART_ROOT / "units" / actor
        glb = unit / "candidates" / "mesh-v1-role-rebuild" / "web.glb"
        route = json.loads((unit / "voxel-route.json").read_text(encoding="utf-8"))
        vehicles.append({"name": actor, "glb": str(glb), "x": x, "y": y, "yaw_deg": yaw,
                         "length_m": route["fit"]["voxels"] * METRES_PER_VOXEL, "faction": route["faction"]})
    w, h = (480, 270) if args.quick else (1920, 1080)
    return {
        "out": str(work / ("lineup-quick.png" if args.quick else "lineup.png")),
        "width": w, "height": h, "samples": 16 if args.quick else args.samples, "threads": args.threads,
        "exposure": 0.0,
        "vehicles": vehicles,
        "camera": {"location": [0.0, 0.0, CAMERA_HEIGHT], "target": [0.0, BACK + 40.0, 0.0], "lens_mm": LENS_MM},
        "sun": {"azimuth_deg": -40.0, "elevation_deg": 24.0, "strength": 4.5, "color": [1.0, 0.74, 0.5],
                "angle_deg": 1.5},
        "sky": {"strength": 0.9, "glow_power": 6.0, "glow_strength": 0.9, "glow_color": [1.0, 0.62, 0.32],
                "stops": [[-0.05, [0.5, 0.36, 0.26]], [0.0, [0.95, 0.6, 0.34]], [0.03, [0.8, 0.52, 0.38]],
                          [0.08, [0.4, 0.4, 0.5]], [0.16, [0.14, 0.22, 0.4]], [0.5, [0.04, 0.08, 0.2]]]},
        "haze_color": [0.86, 0.6, 0.4], "haze_distance": 900.0, "haze_max": 0.9, "haze_strength": 1.0,
        "ground": {"centre": [0.0, 1200.0], "half_size": 1800.0, "cells": 360, "pad": [6.0, 35.0], "pad_radius": 30.0,
                   "pad_falloff": 45.0, "dunes": [[0.6, 45.0], [2.2, 160.0]], "ridges": [[70.0, 800.0], [45.0, 360.0]],
                   "ridge_start": 550.0, "ridge_falloff": 700.0, "tint_scale": 0.02, "grain_scale": 3.0,
                   "sand_dark": [0.26, 0.16, 0.09], "sand_light": [0.5, 0.34, 0.2]},
        "scatter": {"rocks": 320, "shrubs": 0, "near": 14.0, "far": 160.0, "spread": 0.75, "clearance": 6.5,
                    "rock_size": [0.1, 0.45], "shrub_size": [0.3, 0.6], "rock_color": [0.17, 0.12, 0.085],
                    "shrub_color": [0.11, 0.085, 0.045]},
    }


def grade(src: Path, dst: Path):
    """Darker left third (the menu panel sits there) and a soft vignette; no other change to the render."""
    im = np.asarray(Image.open(src).convert("RGB")).astype(np.float32) / 255.0
    h, w = im.shape[:2]
    x = np.linspace(0, 1, w)[None, :]
    y = np.linspace(0, 1, h)[:, None]
    t = np.clip(x / 0.42, 0, 1)
    left = 0.42 + 0.58 * (t * t * (3 - 2 * t))
    r = np.hypot((x - 0.55) / 0.75, (y - 0.5) / 0.62)
    vig = 1.0 - 0.35 * np.clip(r - 0.55, 0, 1) ** 1.6
    out = im * (left * vig)[..., None]
    dst.parent.mkdir(parents=True, exist_ok=True)
    pic = Image.fromarray(np.clip(out * 255 + 0.5, 0, 255).astype(np.uint8))
    # a chrome sheet is one texture and must be power-of-two sized: the picture sits at 0,0 of a black canvas
    side = 1 << (max(w, h) - 1).bit_length()
    sheet = Image.new("RGB", (side, side if h > side // 2 else side // 2))
    sheet.paste(pic, (0, 0))
    sheet.save(dst, optimize=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="480x270, 16 samples, to the work dir only")
    ap.add_argument("--samples", type=int, default=128)
    ap.add_argument("--threads", type=int, default=20)
    ap.add_argument("--work", type=Path, default=Path(tempfile.gettempdir()) / "rtsai-menu")
    ap.add_argument("--grade-only", action="store_true", help="re-grade the cached render")
    args = ap.parse_args()
    args.work.mkdir(parents=True, exist_ok=True)
    j = job(args.work, args)
    if not args.grade_only:
        jp = args.work / "job.json"
        jp.write_text(json.dumps(j, indent=1), encoding="utf-8")
        t = time.time()
        r = subprocess.run([str(BLENDER), "-b", "--factory-startup", "-noaudio", "-P", str(SCRIPT), "--", str(jp)],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        if "LINEUP_DONE" not in r.stdout:
            sys.exit(r.stdout[-3000:] + r.stderr[-3000:])
        print(f"rendered {j['width']}x{j['height']} in {time.time() - t:.0f} s")
    if args.quick:
        grade(Path(j["out"]), args.work / "lineup-quick-graded.png")
        print(args.work / "lineup-quick-graded.png")
        return
    grade(Path(j["out"]), OUT)
    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size // 1024} KiB)")


if __name__ == "__main__":
    main()
