#!/usr/bin/env python3
"""Put a real flag (an SVG) into the lobby/tooltip flag atlases at its faction's chrome.yaml region.

The flag atlases hold one 2:1 region per faction (chrome collection `flags`). Most flags are drawn by
companion/scripts/build-levant-flags.py; a faction whose real flag is shipped instead is rendered here from its SVG
source in tools/flag-sources/:

  1. headless Chrome rasterizes the SVG large (no network: the SVG is a local file with no external references);
  2. the picture is fitted into the region without distortion and the rest of the region is filled by extending the
     flag's own left and right edge columns sideways, so a 4:3 flag fills a 2:1 slot the way its field or its
     horizontal stripes would extend;
  3. downsampled per density (1x, 2x, 3x) and pasted into the three atlases; nothing else in them changes.

    python tools/faction-flag.py lebanon            # source: tools/flag-sources/lebanon.svg
    python tools/faction-flag.py lebanon --classic  # the Classic pack's atlases (mods/rtsai-classic-core/uibits)

Lebanon's flag is the national flag from lipis/flag-icons v7.3.2 (flags/4x3/lb.svg, MIT), the set the website's
national flags come from (see docs/art-provenance.md). The engine's mods/ra/uibits atlases are byte copies of the
Classic pack's: copy the three files there after a --classic run.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import tempfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "tools" / "flag-sources"
# (atlas folder, the chrome.yaml that holds the `flags` regions)
MODERN = (ROOT / "mods" / "rtsai" / "modern-factions" / "ui", ROOT / "mods" / "rtsai" / "chrome.yaml")
CLASSIC = (ROOT / "mods" / "rtsai-classic-core" / "uibits", ROOT / "mods" / "rtsai-classic-core" / "chrome.yaml")
CHROME_EXE = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")


def region(faction: str, chrome_yaml: Path) -> tuple[int, int, int, int]:
    text = chrome_yaml.read_text(encoding="utf-8")
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


def fill_slot(hi: Image.Image, rw: int, rh: int) -> Image.Image:
    """The flag at full slot height, centred; its edge columns are stretched sideways over the rest of the slot.
    Built at the large size and downsampled once, so the sides and the flag get the same resampling."""
    bh = hi.height
    bw = max(hi.width, round(bh * rw / rh))
    big = Image.new("RGBA", (bw, bh))
    left = (bw - hi.width) // 2
    right = bw - left - hi.width
    if left > 0:
        big.paste(hi.crop((0, 0, 1, bh)).resize((left, bh), Image.NEAREST), (0, 0))
    if right > 0:
        big.paste(hi.crop((hi.width - 1, 0, hi.width, bh)).resize((right, bh), Image.NEAREST), (left + hi.width, 0))
    big.paste(hi, (left, 0))
    return big.resize((rw, rh), Image.LANCZOS)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("faction")
    ap.add_argument("--classic", action="store_true", help="write the Classic pack's atlases instead of the modern ones")
    a = ap.parse_args()
    ui, chrome_yaml = CLASSIC if a.classic else MODERN
    svg = SOURCES / f"{a.faction}.svg"
    vb = re.search(r'viewBox="([\d.\s-]+)"', svg.read_text(encoding="utf-8"))
    vw, vh = (float(v) for v in vb[1].split()[2:4])
    x, y, w, h = region(a.faction, chrome_yaml)
    big_h = 900
    with tempfile.TemporaryDirectory() as tmp:
        hi = rasterize(svg, Path(tmp), round(big_h * vw / vh), big_h)
    for density, suffix in ((1, ""), (2, "-2x"), (3, "-3x")):
        rw, rh = w * density, h * density
        slot = fill_slot(hi, rw, rh)
        sheet_path = ui / f"faction-flags{suffix}.png"
        sheet = Image.open(sheet_path).convert("RGBA")
        sheet.paste(slot, (x * density, y * density))
        sheet.save(sheet_path, optimize=True)
        print(f"{sheet_path.relative_to(ROOT)}: {a.faction} at {x * density},{y * density} ({rw}x{rh})")


if __name__ == "__main__":
    main()
