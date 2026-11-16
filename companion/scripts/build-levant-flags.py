#!/usr/bin/env python3
"""Import the four approved original-country SVG flags without changing any other native atlas pixels.

Requires Pillow; imports also require rsvg-convert. --check is read-only and uses
sealed pixel/source hashes, so package verification does not require an SVG renderer.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import subprocess

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
ATLAS = ROOT / "mods/rtsai/modern-factions/ui"
CHROME = ROOT / "mods/rtsai/chrome.yaml"
SOURCES = ROOT / "tools/flag-sources"
MANIFEST = SOURCES / "native-imports.json"
IMPORTS = ("korea", "cuba", "libya", "iraq")
FACTIONS = ("america", "germany", "england", "france", "korea", "cuba", "libya", "iraq", "russia",
            "china", "iran", "turkey", "saudi", "yemen", "israel", "lebanon")
DENSITIES = ((1, ""), (2, "-2x"), (3, "-3x"))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def regions(path):
    block = re.search(r"(?ms)^flags:\n(.*?)(?=^\S|\Z)", path.read_text(encoding="utf-8"))
    if not block:
        raise ValueError("Missing native flags chrome collection")
    found = {m[0]: tuple(map(int, m[1:])) for m in re.findall(
        r"(?m)^\t\t([^:]+): (\d+), *(\d+), *(\d+), *(\d+)\s*$", block[1])}
    missing = set(FACTIONS) - found.keys()
    if missing:
        raise ValueError("Missing native faction flag regions: " + ", ".join(sorted(missing)))
    return {key: found[key] for key in FACTIONS}


def chrome_images(path):
    block = re.search(r"(?ms)^flags:\n(.*?)(?=^\S|\Z)", path.read_text(encoding="utf-8"))
    return dict(re.findall(r"(?m)^\t(Image(?:2x|3x)?): (.+)$", block[1]))


def box(rect, density):
    x, y, w, h = rect
    return x * density, y * density, (x + w) * density, (y + h) * density


def outside_digest(image, rects, density):
    rest = image.copy()
    for key in IMPORTS:
        rest.paste((0, 0, 0, 0), box(rects[key], density))
    return digest(rest.tobytes())


def rasterize(source):
    renderer = shutil.which("rsvg-convert")
    if not renderer:
        raise ValueError("Flag import requires rsvg-convert; --check does not")
    view = re.search(r'viewBox="([\d.\s-]+)"', source.read_text(encoding="utf-8"))
    _, _, width, height = map(float, view[1].split())
    data = subprocess.run([renderer, "--width", str(round(900 * width / height)), "--height", "900",
                           "--format", "png", str(source)], check=True, capture_output=True).stdout
    return Image.open(io.BytesIO(data)).convert("RGB").convert("RGBA")


def fit_slot(image, width, height):
    big_width = max(image.width, round(image.height * width / height))
    big = Image.new("RGBA", (big_width, image.height))
    left = (big_width - image.width) // 2
    right = big_width - left - image.width
    if left:
        big.paste(image.crop((0, 0, 1, image.height)).resize((left, image.height), Image.Resampling.NEAREST), (0, 0))
    if right:
        big.paste(image.crop((image.width - 1, 0, image.width, image.height)).resize(
            (right, image.height), Image.Resampling.NEAREST), (left + image.width, 0))
    big.paste(image, (left, 0))
    return big.resize((width, height), Image.Resampling.LANCZOS)


def inspect(atlas=ATLAS, chrome=CHROME, manifest=MANIFEST):
    expected = json.loads(manifest.read_text(encoding="utf-8"))
    rects = regions(chrome)
    errors = []
    if chrome_images(chrome) != expected["chrome_images"]:
        errors.append("Native flag image bindings changed to an unchecked atlas")
    if {key: list(value) for key, value in rects.items()} != expected["regions"]:
        errors.append("Native flag region geometry changed")
    for key, recorded in expected["svg_sources"].items():
        if digest((SOURCES / (key + ".svg")).read_bytes()) != recorded["sha256"]:
            errors.append("Approved SVG source changed: " + key)
    coverage = []
    for density, suffix in DENSITIES:
        name = "faction-flags" + suffix + ".png"
        image = Image.open(atlas / name).convert("RGBA")
        recorded = expected["atlases"][str(density)]
        if list(image.size) != recorded["size"]:
            errors.append("Atlas geometry changed: " + name)
        if outside_digest(image, rects, density) != recorded["outside_imports_rgba_sha256"]:
            errors.append("Pixels outside the four imported flags changed: " + name)
        for key, rect in rects.items():
            crop = image.crop(box(rect, density))
            correct = digest(crop.tobytes()) == recorded["tiles"][key]
            opaque = crop.getextrema()[3] == (255, 255)
            if not correct or not opaque:
                errors.append(f"Flag {key} at {density}x is missing, altered or an abbreviation tile")
            coverage.append({"faction": key, "density": density, "opaque": opaque, "pixel_hash_matches": correct})
    return {"passed": not errors, "atlas_directory": str(atlas), "faction_count": len(rects),
            "density_count": len(DENSITIES), "coverage": coverage, "errors": errors}


def repair():
    rects = regions(CHROME)
    if MANIFEST.exists():
        existing = inspect()
        non_import_errors = [e for e in existing["errors"] if not any(
            f"Flag {key} at" in e or e == "Approved SVG source changed: " + key for key in IMPORTS)]
        if non_import_errors:
            raise ValueError("Refusing to rewrite unrelated flag changes: " + "; ".join(non_import_errors))
    vectors = {key: rasterize(SOURCES / (key + ".svg")) for key in IMPORTS}
    manifest = {"schema": 1, "source": "Approved flag-icons SVGs copied byte-for-byte from RTSAI-WebGame/web/public/flags; MIT",
                "generator": "companion/scripts/build-levant-flags.py (rsvg-convert + Pillow)",
                "chrome_images": chrome_images(CHROME),
                "regions": {key: list(value) for key, value in rects.items()},
                "svg_sources": {key: {"file": key + ".svg", "sha256": digest((SOURCES / (key + ".svg")).read_bytes())} for key in IMPORTS},
                "atlases": {}}
    for density, suffix in DENSITIES:
        path = ATLAS / ("faction-flags" + suffix + ".png")
        image = Image.open(path).convert("RGBA")
        before = outside_digest(image, rects, density)
        for key in IMPORTS:
            x, y, w, h = rects[key]
            image.paste(fit_slot(vectors[key], w * density, h * density), (x * density, y * density))
        if outside_digest(image, rects, density) != before:
            raise ValueError("Import changed pixels outside the four approved flag regions")
        image.save(path, optimize=True)
        manifest["atlases"][str(density)] = {"size": list(image.size), "outside_imports_rgba_sha256": before,
            "tiles": {key: digest(image.crop(box(rect, density)).tobytes()) for key, rect in rects.items()}}
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return inspect()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Read-only check of all sixteen faction flags at every density")
    parser.add_argument("--installed-app", type=Path, help="Check an installed macOS app against approved native flag pixels")
    parser.add_argument("--receipt", type=Path, help="Write the complete verification receipt")
    args = parser.parse_args()
    if args.installed_app and not args.check:
        parser.error("--installed-app requires --check")
    atlas, chrome = ATLAS, CHROME
    if args.installed_app:
        game = args.installed_app / "Contents/Resources/mods/rtsai"
        atlas, chrome = game / "modern-factions/ui", game / "chrome.yaml"
    result = inspect(atlas, chrome) if args.check else repair()
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key != "coverage"}, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
