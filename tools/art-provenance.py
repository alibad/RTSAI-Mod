#!/usr/bin/env python3
"""Build mods/rtsai/modern-factions/ART-PROVENANCE.json: the origin of every modern-faction art file.

Covers every file under mods/rtsai/modern-factions except rules/text (*.yaml, *.ftl) and audio, plus
the five modern-faction flag regions of mods/rtsai/uibits/buttons.png. Each file gets its SHA-256,
how it was made (generated, rendered from project geometry, procedural) and where it came from.

    python tools/art-provenance.py [--product ../OpenRA-AI] [--red-sea ../OpenRA-AI-wt-ra2-red-sea] [--check]

Sources:
  * cameos painted by tools/paint-cameos.py are read from tools/cameo-generation.json (prompt, seed,
    model, revision, crop) and must still match the installed icon byte for byte;
  * everything ported from OpenRA AI is matched by SHA-256 against the product checkouts
    (--product: China/Iran/Türkiye, OpenRA-AI main; --red-sea: Saudi Arabia/Yemen, codex/ra2-red-sea)
    and attributed to the last commit that touched the file there;
  * the flag regions are compared pixel for pixel against a fresh draw by the product's
    scripts/build-red-sea-ui.py.

--check exits non-zero when a file is not covered or the JSON on disk is out of date.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MF = ROOT / "mods/rtsai/modern-factions"
OUT = MF / "ART-PROVENANCE.json"
CAMEOS = ROOT / "tools/cameo-generation.json"
PRODUCT_DIR = "apps/installer/ra2/modern-factions"
FORK_COMMIT = "5ddc34cb91e52953d4844c169075a0dbbd79e139"  # tools/port-modern-factions.py
FLAG_ORIGINS = {"china": (192, 128), "iran": (226, 33), "turkey": (226, 113), "saudi": (226, 1), "yemen": (226, 17)}

# The 12 cameos cut from the 2x2 portrait atlases (OpenRA-AI scripts/build-ra2-faction-art.py ROSTERS).
PORTRAITS = {
    "china": ("r2qilin", "r2lynx", "r2mantis", "r2cloud"),
    "iran": ("r2karrar", "r2raad", "r2fajr", "r2mohajer"),
    "turkey": ("r2bozkir", "r2yildirim", "r2sancak", "r2kuzgun"),
}
ART_SCRIPTS = {
    "china": ("product", "scripts/ra2_china_assets.py", "scripts/china_directional_assets.py"),
    "iran": ("product", "scripts/ra2_iran_assets.py", "scripts/iran_directional_assets.py"),
    "turkey": ("product", "scripts/ra2_turkey_assets.py", "scripts/turkey_directional_assets.py"),
    "saudi": ("red-sea", "scripts/ra2_red_sea_assets.py", "scripts/red_sea_directional_vehicle.py"),
    "yemen": ("red-sea", "scripts/ra2_red_sea_assets.py", "scripts/red_sea_directional_vehicle.py"),
}

GENERATORS = {
    "qwen-image": {
        "kind": "text-to-image diffusion model, run locally",
        "model": "Qwen/Qwen-Image",
        "revision": "75e0b4be04f60ec59a75f475837eced720f823b6",
        "license": "Apache-2.0",
        "licenseEvidence": [
            "Model card (README.md) of the local snapshot 75e0b4be04f60ec59a75f475837eced720f823b6: front matter "
            "'license: apache-2.0' and section 'License Agreement': 'Qwen-Image is licensed under Apache 2.0.' "
            "README.md sha256 c70f9851b364e5d6209305d6f07e065086126132ecc24805c652de45d3d92ca8",
            "LICENSE file of the same snapshot: Apache License, Version 2.0 "
            "(sha256 832dd9e00a68dd83b3c3fb9f5588dad7dcf337a0db50f7d9483f310cd292e92e)",
            "huggingface.co/Qwen/Qwen-Image README.md front matter 'license: apache-2.0', read 2026-10-02",
        ],
        "runtime": "diffusers DiffusionPipeline, transformer and text encoder quantized to fp8 weight-only with "
                   "torchao, bf16, RTX 5090, driven by tools/paint-cameos.py. Either through the shared server "
                   "hq/quote-forge/server/qwen_image.py (model CPU offload) or loaded in-process by "
                   "`paint-cameos.py --backend local` (block-level group offload). Each cameo records which.",
        "inputs": "Text prompt and negative prompt only. No reference, init or control image.",
        "notConfusedWith": "Not Qwen-Image-2512 and not qwen-image-2.1 (the latter is licensed for non-commercial use only).",
    },
    "openai-image-tool": {
        "kind": "text-to-image model behind the Codex built-in image-generation tool",
        "model": "not recorded",
        "license": "not recorded in the project; OpenAI's terms assign output rights to the user (not re-verified here)",
        "evidence": [
            "OpenRA-AI/assets/ra2-modern-factions/README.md: 'original project unit portraits made with the built-in "
            "image-generation tool on 2026-09-03', shared prompt and per-faction unit descriptions",
            "Sibling project notes name the same tool 'Codex's built-in OpenAI image-generation tool' "
            "(OpenRA-AI/assets/red-sea-2026/icon-sources/production-icon-prompts.md)",
        ],
        "inputs": "Text prompt; the README lists project concept images as references (see flags).",
    },
    "project-geometry": {
        "kind": "deterministic renders and exports of hand-authored 3D meshes defined in Python",
        "license": "GPL-3.0-or-later (project code and its output; OpenRA-AI/assets/ra2-modern-factions/README.md)",
        "inputs": "Mesh boxes/cylinders/polygons written in code and project-defined material colours. The builders "
                  "read no image, SHP, VXL, HVA, palette or MIX file. The only external data is the RA2 voxel "
                  "normal-vector table, parsed from OpenRA's GPL-3.0 source "
                  "OpenRA.Mods.Cnc/Traits/World/VoxelNormalsPalette.cs (format data, not art).",
    },
    "procedural-flag": {
        "kind": "flags drawn with PIL primitives (rectangles, lines, ellipses, star polygons)",
        "license": "GPL-3.0-or-later (project code); national flags are public symbols",
        "inputs": "None. Every pixel of each 30x15 region is drawn by the script.",
    },
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


class Source:
    def __init__(self, name: str, repo: Path):
        self.name, self.repo = name, repo
        self.head = git(repo, "rev-parse", "HEAD")
        self.branch = git(repo, "rev-parse", "--abbrev-ref", "HEAD")
        self._log: dict[str, str] = {}

    def matches(self, rel: str, digest: str) -> bool:
        path = self.repo / PRODUCT_DIR / rel
        return path.is_file() and sha256(path.read_bytes()) == digest

    def commit(self, rel: str) -> str:
        if rel not in self._log:
            self._log[rel] = git(self.repo, "log", "-1", "--format=%H %ad", "--date=short", "--", f"{PRODUCT_DIR}/{rel}")
        return self._log[rel]

    def ref(self, rel: str) -> dict:
        commit, date = self.commit(rel).split()
        return {"repo": self.name, "path": f"{PRODUCT_DIR}/{rel}", "commit": commit, "date": date}


def referenced_paths() -> set[str]:
    text = "\n".join(p.read_text(encoding="utf-8") for p in MF.glob("*.yaml"))
    return set(re.findall(r"ra2\|modern-factions/([\w./-]+)", text))


def classify(rel: str, digest: str, sources: dict[str, Source], cameos: dict, voxel_owner: dict) -> dict:
    folder, name = rel.split("/", 1) if "/" in rel else ("", rel)
    stem = Path(name).stem
    entry: dict = {"sha256": digest}
    origin = next((s for s in sources.values() if s.matches(rel, digest)), None)

    if folder == "icons":
        entry["type"] = "build-palette cameo, 60x48 RGB PNG"
        if stem in cameos:
            c = cameos[stem]
            if c["icon_sha256"] != digest:
                raise ValueError(f"icons/{name} no longer matches tools/cameo-generation.json; rerun paint-cameos install")
            entry.update(origin="generated", generator="qwen-image", date=c["generated_at"][:10], tool="tools/paint-cameos.py",
                         generation={k: c[k] for k in ("subject", "prompt", "negative_prompt", "seed", "steps", "cfg",
                                                       "master_size", "model", "model_revision", "runtime", "master_sha256",
                                                       "crop_box", "postprocess")},
                         replaced="model-render placeholder from the faction port")
            return entry
        country = next((k for k, v in PORTRAITS.items() if stem in v), None)
        if country and origin:
            cell = PORTRAITS[country].index(stem)
            entry.update(origin="generated", generator="openai-image-tool", date="2026-09-03",
                         derivation=f"cell {cell} (row-major) of the 2x2 atlas OpenRA-AI/assets/ra2-modern-factions/"
                                    f"{country}-portraits-v1.png, padded to 60x48 with RGB (10, 22, 26) by "
                                    f"scripts/build-ra2-faction-art.py", source=origin.ref(rel),
                         flags=["generator-model-and-seed-unrecorded"])
            return entry
        entry.update(origin="rendered-from-project-geometry", generator="project-geometry",
                     source=origin.ref(rel) if origin else None, flags=["placeholder-render"])
        return entry

    if not origin:
        entry.update(origin="unknown", flags=["unclear-origin"])
        return entry
    entry["source"] = origin.ref(rel)
    if folder == "voxels":
        script = voxel_owner.get(stem)
        if name == "modern.pal":
            entry.update(type="voxel palette", origin="procedural", generator="project-geometry",
                         script="scripts/ra2_faction_voxels.py palette()")
        else:
            entry.update(type="RA2 voxel model" if name.endswith(".vxl") else "RA2 voxel animation/transform (HVA)",
                         origin="rendered-from-project-geometry", generator="project-geometry", script=script)
        return entry
    country = folder.removesuffix("-art")
    repo_key, script, geometry = ART_SCRIPTS[country]
    if name.endswith(".shp"):
        entry.update(type="SHP sprite (infantry 112 frames, 48x48; defence 41 frames, 96x96)",
                     origin="rendered-from-project-geometry", generator="project-geometry", script=script, geometry=geometry)
    elif name.endswith("-review.png"):
        entry.update(type="review contact sheet of the SHP frames", origin="rendered-from-project-geometry",
                     generator="project-geometry", script=script, flags=["unreferenced-review-sheet"])
    elif name.endswith(".pal"):
        entry.update(type="palette", origin="procedural", generator="project-geometry",
                     script=f"{script} ({'voxel_palette' if 'voxels' in name else 'sprite_palette'})")
    elif name == "manifest.json":
        entry.update(type="build manifest (frame counts, sizes, SHA-256)", origin="procedural", script=script)
    else:
        entry.update(origin="unknown", flags=["unclear-origin"])
    return entry


def flag_entries(product: Path) -> dict:
    from PIL import Image, ImageDraw

    spec = importlib.util.spec_from_file_location("red_sea_ui", product / "scripts/build-red-sea-ui.py")
    ui = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ui)
    canvas = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    ui.draw_saudi_flag(draw, 1)
    ui.draw_yemen_flag(draw, 1)
    ui.draw_turkey_flag(draw, 1)
    ui.draw_iran_flag(draw, 1)
    ui.draw_china_flag(draw, 1, FLAG_ORIGINS["china"])
    chrome = (ROOT / "mods/rtsai/chrome.yaml").read_text(encoding="utf-8")
    buttons = Image.open(ROOT / "mods/rtsai/uibits/buttons.png").convert("RGBA")
    out = {}
    script_commit = git(product, "log", "-1", "--format=%H", "--", "scripts/build-red-sea-ui.py")
    for country, (x, y) in FLAG_ORIGINS.items():
        bx, by = map(int, re.search(rf"^\t\t{country}: (\d+), (\d+), 30, 15$", chrome, re.MULTILINE).groups())
        region = buttons.crop((bx, by, bx + 30, by + 15))
        drawn = canvas.crop((x, y, x + 30, y + 15))
        identical = region.tobytes() == drawn.tobytes()
        out[f"../uibits/buttons.png#{country}"] = {
            "sha256": sha256(region.tobytes()), "type": "lobby flag, 30x15 region of the RA2 button atlas",
            "region": [bx, by, 30, 15], "origin": "procedural", "generator": "procedural-flag",
            "script": f"OpenRA-AI scripts/build-red-sea-ui.py draw_{country}_flag @ {script_commit}",
            "chain": f"drawn into alibad/OpenRA mods/ra/uibits/glyphs-redsea.png @ {FORK_COMMIT}, cropped at "
                     f"{x},{y} by tools/port-modern-factions.py extend_flags()",
            "verifiedRedraw": identical,
            **({} if identical else {"flags": ["redraw-mismatch"]}),
        }
    return out


def build(args) -> dict:
    sources = {"OpenRA-AI": Source("OpenRA-AI", args.product), "OpenRA-AI codex/ra2-red-sea": Source("OpenRA-AI codex/ra2-red-sea", args.red_sea)}
    cameos = json.loads(CAMEOS.read_text(encoding="utf-8")) if CAMEOS.exists() else {}
    voxel_owner = {}
    for manifest, script in (("voxel-manifest.json", "scripts/ra2_faction_voxels.py"),
                             ("red-sea-voxel-manifest.json", "scripts/ra2_red_sea_assets.py")):
        for model in json.loads((MF / manifest).read_text(encoding="utf-8"))["models"]:
            voxel_owner[model] = script
    referenced = referenced_paths()
    files = {}
    for path in sorted(MF.rglob("*")):
        rel = path.relative_to(MF).as_posix()
        if path.is_dir() or path.suffix in (".yaml", ".ftl") or rel.startswith("audio/") or path == OUT:
            continue
        digest = sha256(path.read_bytes())
        if rel in ("voxel-manifest.json", "red-sea-voxel-manifest.json"):
            origin = next(s for s in sources.values() if s.matches(rel, digest))
            files[rel] = {"sha256": digest, "type": "voxel build manifest", "origin": "procedural", "source": origin.ref(rel)}
            continue
        entry = classify(rel, digest, sources, cameos, voxel_owner)
        used = rel in referenced or (path.suffix in (".vxl", ".hva") and rel[: -len(path.suffix)] in referenced)
        entry["runtime"] = "referenced by rules/sequences" if used else "not referenced at runtime"
        files[rel] = entry
    files.update(flag_entries(args.product))

    counts: dict[str, int] = {}
    for entry in files.values():
        key = f"{entry['origin']}/{entry.get('generator', '-')}"
        counts[key] = counts.get(key, 0) + 1
    flagged = {}
    for rel, entry in files.items():
        for flag in entry.get("flags", []):
            flagged.setdefault(flag, []).append(rel)
    return {
        "schemaVersion": 1,
        "scope": "Every art file under mods/rtsai/modern-factions (icons, *-art SHP/PAL/review sheets, voxels, "
                 "manifests) and the five modern-faction flag regions of mods/rtsai/uibits/buttons.png. Rules, Fluent "
                 "text and audio are out of scope.",
        "generatedBy": "tools/art-provenance.py",
        "sources": {name: {"repo": str(s.repo.name), "branch": s.branch, "head": s.head} for name, s in sources.items()},
        "generators": GENERATORS,
        "commercialRa2Data": "None found. No file matches, embeds or was built from Red Alert 2 game data; the art "
                             "builders read no MIX/SHP/VXL/HVA/PAL/image input, the cameos are text-to-image, and the "
                             "flags are redrawn identically from code. See docs/art-provenance.md for the method.",
        "summary": {"files": len(files), "byOrigin": dict(sorted(counts.items())),
                    "flags": {k: len(v) for k, v in sorted(flagged.items())}},
        "flagDefinitions": {
            "generator-model-and-seed-unrecorded": "Generated with the Codex built-in OpenAI image tool; the exact model, "
                "seed and per-image prompt were not recorded. The prompt names project concept images as references, "
                "and assets/china-faction/icon-sources/china-unit-cameo-atlas-v1.png has no provenance note of its own. "
                "No sign of RA2-derived content, but the origin cannot be reproduced.",
            "unreferenced-review-sheet": "Developer review sheet copied with the faction art; no rule or sequence uses it.",
            "placeholder-render": "Model-render placeholder cameo, not painted.",
            "unclear-origin": "No matching source file was found.",
            "redraw-mismatch": "The flag region differs from a fresh procedural draw.",
        },
        "files": files,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--product", type=Path, default=ROOT.parent / "OpenRA-AI")
    parser.add_argument("--red-sea", type=Path, default=ROOT.parent / "OpenRA-AI-wt-ra2-red-sea")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    data = build(args)
    text = json.dumps(data, indent=1, ensure_ascii=False) + "\n"
    unknown = [rel for rel, e in data["files"].items() if e["origin"] == "unknown"]
    if args.check:
        recorded = json.loads(OUT.read_text(encoding="utf-8"))["files"] if OUT.exists() else {}
        stale = sorted(set(recorded) ^ set(data["files"]) |
                       {k for k in recorded.keys() & data["files"].keys() if recorded[k]["sha256"] != data["files"][k]["sha256"]})
        if stale or unknown:
            print(f"ART-PROVENANCE.json is stale for {stale}; unknown origin: {unknown}")
            return 1
        print(f"ART-PROVENANCE.json covers all {len(recorded)} files")
        return 0
    OUT.write_text(text, encoding="utf-8", newline="\n")
    print(json.dumps(data["summary"], indent=1))
    return 1 if unknown else 0


if __name__ == "__main__":
    sys.exit(main())
