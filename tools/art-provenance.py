#!/usr/bin/env python3
"""Build mods/rtsai/modern-factions/ART-PROVENANCE.json: the origin of every modern-faction art file.

Covers every file under mods/rtsai/modern-factions except rules/text (*.yaml, *.ftl), audio and this record
itself. Each file gets its SHA-256, how it was made, the RTSAI-Art candidate it was installed from (route,
candidate id, the commit that holds those bytes), the project 3D model it was rendered from, and whether the
game references it.

    python tools/art-provenance.py [--art ../RTSAI-Art] [--product ../OpenRA-AI] [--check]

Re-run it after every install (vehicle_install.py, infantry_install.py, building_sprites.py install,
cameo_render.py install): the web's sync:art publishes only files recorded here, with matching SHA-256.

Sources (since the owner-approved art preview was promoted on 2026-10-06):
  * vehicles/  prerendered vehicle, ship and aircraft sprites   RTSAI-Art units/<actor>/candidates/sprite-v6-prerender
  * infantry/  GLB-rigged infantry sprites and palettes          RTSAI-Art units/<actor>/candidates/sprite-v3-glb
  * buildings/ building and defense sprites and palettes         RTSAI-Art units/<actor>/candidates/sprite-v3-glb
  * icons/     build-menu cameos with a name bar                 RTSAI-Art units/<actor>/candidates/cameo-v3-render
  * ui/        lobby flag atlases drawn by OpenRA-AI scripts/build-levant-flags.py (PIL primitives); the Hezbollah
               region is its real flag, rendered by tools/faction-flag.py from tools/flag-sources/hezbollah.svg
Each candidate's file must match the installed file byte for byte, and its bytes must be committed in RTSAI-Art.

--check exits non-zero when a file is uncovered, of unknown origin, unreferenced by the game, or differs from
the hash in the JSON on disk. The pre-promotion art (procedural voxels and SHPs, Qwen-Image cameos) left the mod
and is archived with manifests in RTSAI-Art history/.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MF = ROOT / "mods/rtsai/modern-factions"
OUT = MF / "ART-PROVENANCE.json"
ART_REPO = "RTSAI-Art (local)"

ROUTES = {  # folder -> (candidate id, file type)
    "vehicles": ("sprite-v6-prerender", "prerendered vehicle, ship or aircraft sprite (TS/RA2 SHP: 32 facings, turret, "
                                        "spin and reload variants, sun-shadow frames)"),
    "infantry": ("sprite-v3-glb", "infantry sprite (TS/RA2 SHP: stand, run, fire, prone, idle and death, 8 facings, "
                                  "shadow frames)"),
    "buildings": ("sprite-v3-glb", "building or defense sprite (TS/RA2 SHP: idle, damaged, build-up, turret and fire "
                                   "where armed, shadow frames)"),
    "icons": ("cameo-v3-render", "build-palette cameo, 60x48 RGB PNG with a name bar"),
}
FONT = "tools/fonts/kenney/kenpixel.ttf"
FONT_LICENSE = "tools/fonts/kenney/LICENSE.txt"

GENERATORS = {
    "project-geometry": {
        "kind": "renders of the project's own 3D models, made on the CPU by RTSAI-Art tools",
        "license": "GPL-3.0-or-later (project code and its output)",
        "inputs": "Each unit's GLB mesh, generated locally (TRELLIS.2 image-to-3D, local trellis-cli, no paid API) from "
                  "the project's own concept picture of that unit, then split, scaled and painted in Blender with "
                  "project material classes and faction colours. Renders: Blender Cycles (CPU), lit with OpenRA's voxel "
                  "light formula. Original RA2 files were used only on this machine to measure target statistics "
                  "(value range, local contrast, size), never as input pixels.",
        "routes": {
            "sprite-v6-prerender": "tools/glb_prerender.py: the GLB rendered as a pre-lit 32-facing sprite with turret, "
                                   "spin, reload and sun-shadow frames; muzzles measured on the renders",
            "sprite-v3-glb (infantry)": "tools/infantry_blender.py + tools/infantry_sprite_post.py: the GLB rigged, "
                                        "posed and animated in Blender, rendered per facing",
            "sprite-v3-glb (buildings)": "tools/building_sprites.py: the GLB rendered isometrically with damage, "
                                         "build-up, turret and fire frames",
            "cameo-v3-render": "tools/cameo_render.py: a perspective render of the installed model, 60x48 post, name bar",
        },
    },
    "procedural-flag": {
        "kind": "flag atlases drawn with PIL primitives (rectangles, lines, ellipses, polygons)",
        "license": "GPL-3.0-or-later (project code); national flags are public symbols; the Hezbollah region is "
                   "non-free artwork shipped by owner decision (7 October 2026, docs/art-provenance.md)",
        "inputs": "Drawn by OpenRA-AI scripts/build-levant-flags.py, except the Hezbollah region: its real flag "
                  "(tools/flag-sources/hezbollah.svg, from Wikipedia, the website's copy), rasterized by "
                  "tools/faction-flag.py. The EA chrome is never copied.",
    },
}
FLAG_DEFINITIONS = {
    "unclear-origin": "No matching candidate or builder was found.",
    "unreferenced": "Shipped in the mod, but no rule, sequence or chrome file uses it.",
    "candidate-mismatch": "The installed bytes differ from the candidate they were installed from.",
    "uncommitted-source": "The candidate's bytes are not committed in RTSAI-Art.",
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True, encoding="utf-8").strip()


def referenced_paths() -> set[str]:
    text = "\n".join(p.read_text(encoding="utf-8") for p in MF.glob("*.yaml"))
    text += (ROOT / "mods/rtsai/chrome.yaml").read_text(encoding="utf-8")
    return set(re.findall(r"ra2\|modern-factions/([\w./-]+)", text))


class Art:
    """The RTSAI-Art checkout: candidate files, their metadata and the commit that holds their bytes."""

    def __init__(self, repo: Path):
        self.repo = repo
        self.head = git(repo, "rev-parse", "HEAD")
        self._index: dict[tuple[str, str], list[Path]] = {}

    def meta(self, cdir: Path) -> dict:
        try:
            return json.loads((cdir / "meta.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def committed(self, path: Path) -> dict | None:
        """{commit, date} of the last commit of `path` when the working file equals that commit's bytes."""
        rel = path.relative_to(self.repo).as_posix()
        out = git(self.repo, "log", "-1", "--format=%H %ad", "--date=short", "--", rel)
        if not out:
            return None
        commit, date = out.split()
        blob = subprocess.run(["git", "-C", str(self.repo), "show", f"{commit}:{rel}"], capture_output=True).stdout
        return {"commit": commit, "date": date} if sha256(blob) == sha256(path.read_bytes()) else None

    def find(self, cid: str, name: str, digest: str) -> Path | None:
        """A candidate file of route `cid` named `name` with these bytes (shared palettes live in many candidates)."""
        key = (cid, name)
        if key not in self._index:
            self._index[key] = sorted(self.repo.glob(f"units/*/candidates/{cid}/{name}"))
        return next((p for p in self._index[key] if sha256(p.read_bytes()) == digest), None)

    def geometry(self, actor: str, meta: dict) -> dict | None:
        mesh_id = meta.get("fromMesh")
        if not mesh_id:
            return None
        mdir = self.repo / "units" / actor / "candidates" / mesh_id
        mm = self.meta(mdir)
        out = {"mesh": f"units/{actor}/candidates/{mesh_id}/{(mm.get('files') or {}).get('mesh', 'mesh.glb')}",
               "sha256": (mm.get("geometry") or {}).get("sha256") or meta.get("sourceMeshSha256")}
        i3d = mm.get("imageTo3d") or {}
        if i3d:
            out["madeBy"] = f"{i3d.get('model', 'image-to-3D')} ({i3d.get('service', 'local')}), seed {i3d.get('seed')}"
            out["fromImage"] = i3d.get("source")
        elif mm.get("model"):
            out["madeBy"] = mm["model"]          # hand-authored meshes (e.g. tools/hz_doctrine_models.py)
        concept = mm.get("fromConcept") or meta.get("fromConcept")
        if concept:
            cm = self.meta(self.repo / "units" / actor / "candidates" / concept)
            out["concept"] = {"candidate": f"units/{actor}/candidates/{concept}", "model": cm.get("model"),
                              "costUsd": cm.get("costUsd", 0)}
        return out


def route_entry(rel: str, digest: str, art: Art) -> dict:
    folder, name = rel.split("/", 1)
    cid, kind = ROUTES[folder]
    entry: dict = {"sha256": digest}
    stem = name.rsplit(".", 1)[0]
    if folder == "icons":
        cand = art.repo / "units" / stem / "candidates" / cid / "cameo.png"
    elif name.endswith(".pal") and folder == "vehicles":
        cand = art.find(cid, name, digest)            # one palette per faction, shared by its units
    else:
        cand = art.repo / "units" / stem / "candidates" / cid / name
    if not cand or not cand.exists():
        return {**entry, "origin": "unknown", "flags": ["unclear-origin"]}
    if sha256(cand.read_bytes()) != digest:
        return {**entry, "origin": "unknown", "flags": ["candidate-mismatch"], "candidateFile": cand.relative_to(art.repo).as_posix()}
    actor = cand.relative_to(art.repo).parts[1]
    meta = art.meta(cand.parent)
    ref = art.committed(cand)
    entry["source"] = {"repo": ART_REPO, "path": cand.relative_to(art.repo).as_posix(), **(ref or {})}
    pal = name.endswith(".pal")
    entry["type"] = "palette (index 0 transparent, 1 shadow, 16-31 player remap)" if pal else kind
    entry["origin"] = "procedural" if pal else "rendered-from-project-geometry"
    entry["generator"] = "project-geometry"
    entry["candidate"] = cid
    entry["route"] = meta.get("route") or meta.get("model")
    entry["tool"] = meta.get("createdBy") or meta.get("model")
    entry["date"] = (meta.get("updatedAt") or meta.get("createdAt") or "")[:10] or None
    if pal:
        entry["script"] = "computed by the route from the project's material classes and faction colours"
    geo = art.geometry(actor, meta)
    if folder == "icons":
        src = (meta.get("source") or {}).get("candidate")
        entry["renderedFrom"] = src
        if src:
            geo = art.geometry(actor, art.meta(art.repo / src))
        label = meta.get("label") or {}
        font = art.repo / FONT
        entry["nameBar"] = {"text": label.get("text"), "fluentKey": label.get("fluentKey"),
                            "font": {"name": "Kenney Pixel (kenpixel.ttf) by Kenney, www.kenney.nl", "license": "CC0-1.0",
                                     "file": f"RTSAI-Art {FONT}", "notice": f"RTSAI-Art {FONT_LICENSE}",
                                     "sha256": sha256(font.read_bytes()) if font.exists() else None,
                                     "shipped": False, "note": "only the rendered cameos are in the mod"},
                            "unlabelled": f"{cand.parent.relative_to(art.repo).as_posix()}/cameo-nolabel.png"}
    if geo:
        entry["geometry"] = geo
    if ref is None:
        entry["flags"] = ["uncommitted-source"]
    return entry


def flag_entry(rel: str, digest: str, product: Path) -> dict:
    script = "scripts/build-levant-flags.py"
    commit = git(product, "log", "-1", "--format=%H", "--", script) if (product / script).exists() else None
    return {"sha256": digest, "type": "lobby flag atlas (PNG; 2x and 3x copies for high-DPI)", "origin": "procedural",
            "generator": "procedural-flag", "script": f"OpenRA-AI {script}" + (f" @ {commit}" if commit else ""),
            "chain": "drawn by the script into modern-factions/ui/, padded to power-of-two sheets by RTSAI-Mod fa92525; "
                     "the Hezbollah region replaced with the real flag by tools/faction-flag.py hezbollah"}


def build(args) -> dict:
    art = Art(args.art)
    referenced = referenced_paths()
    files = {}
    for path in sorted(MF.rglob("*")):
        rel = path.relative_to(MF).as_posix()
        if path.is_dir() or path.suffix in (".yaml", ".ftl") or rel.startswith("audio/") or path == OUT:
            continue
        digest = sha256(path.read_bytes())
        folder = rel.split("/", 1)[0]
        if folder in ROUTES:
            entry = route_entry(rel, digest, art)
        elif folder == "ui":
            entry = flag_entry(rel, digest, args.product)
        else:
            entry = {"sha256": digest, "origin": "unknown", "flags": ["unclear-origin"]}
        used = rel in referenced
        entry["runtime"] = ("referenced by chrome.yaml (flags)" if folder == "ui" else "referenced by rules/sequences") \
            if used else "not referenced"
        if not used:
            entry.setdefault("flags", []).append("unreferenced")
        files[rel] = entry

    counts: dict[str, int] = {}
    flagged: dict[str, int] = {}
    for entry in files.values():
        key = f"{entry['origin']}/{entry.get('generator', '-')}"
        counts[key] = counts.get(key, 0) + 1
        for flag in entry.get("flags", []):
            flagged[flag] = flagged.get(flag, 0) + 1
    used_generators = {e.get("generator") for e in files.values()}
    return {
        "schemaVersion": 1,
        "scope": "Every art file under mods/rtsai/modern-factions (vehicles, infantry, buildings, icons, ui). Rules, "
                 "Fluent text, audio and this record are out of scope.",
        "generatedBy": "tools/art-provenance.py",
        "sources": {ART_REPO: {"repo": args.art.name, "head": art.head}},
        "generators": {k: v for k, v in GENERATORS.items() if k in used_generators},
        "commercialRa2Data": "None found. Every unit sprite and cameo is a render of the project's own 3D model (a GLB "
                             "generated locally from the project's concept picture), installed from a committed RTSAI-Art "
                             "candidate with the same bytes; original RA2 files were read only locally to measure target "
                             "statistics, never as input pixels; the flags are drawn from code. See docs/art-provenance.md.",
        "removed": "2026-10-06: the pre-promotion placeholder art left the mod (procedural voxels and infantry/defense "
                   "SHPs, faction palettes, Qwen-Image cameos, Levant previews). RTSAI-Art history/ keeps every superseded "
                   "file with a manifest (what it was, which release used it, its generator) and the old record "
                   "(history/_records/ART-PROVENANCE.json).",
        "summary": {"files": len(files), "byOrigin": dict(sorted(counts.items())), "flags": dict(sorted(flagged.items()))},
        "flagDefinitions": {k: v for k, v in FLAG_DEFINITIONS.items() if k in flagged},
        "files": files,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--art", type=Path, default=ROOT.parent / "RTSAI-Art")
    parser.add_argument("--product", type=Path, default=ROOT.parent / "OpenRA-AI")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    data = build(args)
    problems = sorted(rel for rel, e in data["files"].items() if e.get("flags"))
    if args.check:
        recorded = json.loads(OUT.read_text(encoding="utf-8"))["files"] if OUT.exists() else {}
        stale = sorted(set(recorded) ^ set(data["files"]) |
                       {k for k in recorded.keys() & data["files"].keys() if recorded[k]["sha256"] != data["files"][k]["sha256"]})
        if stale or problems:
            print(f"ART-PROVENANCE.json is stale for {stale[:20]} ({len(stale)}); flagged: {problems[:20]} ({len(problems)})")
            return 1
        print(f"ART-PROVENANCE.json covers all {len(recorded)} files; none flagged")
        return 0
    OUT.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(data["summary"], indent=1))
    if problems:
        print(f"flagged: {problems[:20]}", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
