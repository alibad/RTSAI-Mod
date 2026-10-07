#!/usr/bin/env python3
"""Put a real flag (an SVG) into the lobby/tooltip flag atlases at its faction's chrome.yaml region.

The flag atlases (mods/rtsai/modern-factions/ui/faction-flags{,-2x,-3x}.png, chrome collection `flags`) hold one
2:1 region per faction. Most flags are drawn by OpenRA-AI scripts/build-levant-flags.py; a faction whose real flag
is shipped instead (owner decision) is rendered here from its SVG source in tools/flag-sources/:

  1. headless Chrome rasterizes the SVG large (no network: the SVG is a local file with no external references);
  2. the picture is fitted into the region without distortion and the rest of the region is filled with the flag's
     own field colour (sampled at its corner), so a 3:2 flag fills a 2:1 slot the way its field would extend;
  3. downsampled per density (1x, 2x, 3x) and pasted into the three atlases; nothing else in them changes.

    python tools/faction-flag.py hezbollah            # source: tools/flag-sources/hezbollah.svg

Hezbollah's flag is non-free artwork (see docs/art-provenance.md); the owner decided on 7 October 2026 that the
game shows it like the public website does.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import tempfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "mods" / "rtsai" / "modern-factions" / "ui"
SOURCES = ROOT / "tools" / "flag-sources"
CHROME_YAML = ROOT / "mods" / "rtsai" / "chrome.yaml"
CHROME_EXE = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")


def region(faction: str) -> tuple[int, int, int, int]:
    text = CHROME_YAML.read_text(encoding="utf-8")
    block = re.search(r"(?ms)^flags:\n(.*?)(?=^\S|\Z)", text)[1]
    m = re.search(rf"(?m)^\t\t{re.escape(faction)}: (\d+), *(\d+), *(\d+), *(\d+)\s*$", block)
    if not m:
        raise SystemExit(f"no `{faction}` region in chrome.yaml flags")
    return tuple(int(v) for v in m.groups())


def rasterize(svg: Path, work: Path, width: int, height: int) -> Image.Image:
    (work / "flag.svg").write_bytes(svg.read_bytes())
    (work / "flag.html").write_text(
        "<!doctype html><html><head><style>html,body{margin:0;padding:0;background:transparent}"
        f"img{{display:block;width:{width}px;height:{height}px}}</style></head><body><img src=\"flag.svg\"></body></html>",
        encoding="utf-8")
    out = work / "flag.png"
    subprocess.run([str(CHROME_EXE), "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
                    f"--user-data-dir={work / 'profile'}", f"--screenshot={out}", f"--window-size={width},{height}",
                    "--default-background-color=00000000", (work / "flag.html").as_uri()],
                   check=True, capture_output=True, timeout=120)
    return Image.open(out).convert("RGBA")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("faction")
    a = ap.parse_args()
    svg = SOURCES / f"{a.faction}.svg"
    vb = re.search(r'viewBox="([\d.\s-]+)"', svg.read_text(encoding="utf-8"))
    vw, vh = (float(v) for v in vb[1].split()[2:4])
    x, y, w, h = region(a.faction)
    big_h = 900
    with tempfile.TemporaryDirectory() as tmp:
        hi = rasterize(svg, Path(tmp), round(big_h * vw / vh), big_h)
    field = hi.getpixel((2, 2))
    for density, suffix in ((1, ""), (2, "-2x"), (3, "-3x")):
        rw, rh = w * density, h * density
        fh = rh
        fw = min(rw, round(fh * vw / vh))
        slot = Image.new("RGBA", (rw, rh), field)
        slot.paste(hi.resize((fw, fh), Image.LANCZOS), ((rw - fw) // 2, 0))
        sheet_path = UI / f"faction-flags{suffix}.png"
        sheet = Image.open(sheet_path).convert("RGBA")
        sheet.paste(slot, (x * density, y * density))
        sheet.save(sheet_path, optimize=True)
        print(f"{sheet_path.relative_to(ROOT)}: {a.faction} at {x * density},{y * density} ({rw}x{rh})")


if __name__ == "__main__":
    main()
