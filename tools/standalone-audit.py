#!/usr/bin/env python3
"""Standalone-dependency audit: which files the RA2-mode mod loads from EA content, measured by the engine itself.

Compiles tools/standalone-audit/StandaloneAudit.cs (an OpenRA utility command) against this worktree's engine,
builds a disposable sandbox (a copy of mod.yaml with the extra assembly; directory junctions for everything else)
and runs `OpenRA.Utility rtsai --standalone-audit`. Every reference is resolved through the engine's own file
system, so mount order, explicit package prefixes and mod overrides are exactly what the game sees.

  --content DIR   mount the player's installed RA2 content (e.g. ../OpenRA/Support/Content) to MEASURE where each
                  file comes from. Only names, frame counts and frame sizes are read from it; nothing is copied.
  (no --content)  the standalone check: the same audit with no EA content at all.

The raw JSON goes to --out; `--summary` prints the per-category tables used in docs/standalone.md.
Sandbox junctions are unlinked (never deleted recursively) when the run ends.

usage: python tools/standalone-audit.py --content ../OpenRA/Support/Content --out <scratch>/audit.json --summary
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "tools" / "standalone-audit" / "StandaloneAudit.cs"
MODERN = ["china", "iran", "turkey", "saudi", "israel", "yemen", "hezbollah"]


def link_dir(link: Path, target: Path):
    import _winapi
    _winapi.CreateJunction(str(target.resolve()), str(link)) if os.name == "nt" else link.symlink_to(target.resolve())


def is_link(p: Path) -> bool:
    st = os.lstat(p)
    return p.is_symlink() or bool(getattr(st, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def unlink_tree_links(root: Path):
    """Remove every junction/symlink under root (links only, never their targets), then the emptied dirs."""
    for dirpath, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        for d in list(dirnames):
            p = Path(dirpath) / d
            if is_link(p):
                os.rmdir(p) if os.name == "nt" else p.unlink()
                dirnames.remove(d)
    for dirpath, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        assert not any(is_link(Path(dirpath) / d) for d in dirnames), "a link survived; refusing to delete"
    # nothing left links outside root now: the rest is our own scratch files
    for dirpath, dirnames, filenames in os.walk(root, topdown=False):
        for f in filenames:
            os.unlink(Path(dirpath) / f)
        for d in dirnames:
            os.rmdir(Path(dirpath) / d)
    os.rmdir(root)


def compile_command(engine: Path, cache: Path) -> Path:
    stamp = hashlib.sha256(SRC.read_bytes() + (engine / "bin/OpenRA.Game.dll").read_bytes()).hexdigest()[:16]
    d = cache / f"build-{stamp}"
    dll = d / "out" / "OpenRA.Mods.RTSAIAudit.dll"
    if dll.exists():
        return dll
    d.mkdir(parents=True, exist_ok=True)
    refs = "".join(f'<Reference Include="{n}"><HintPath>{escape(str(engine / "bin" / (n + ".dll")))}</HintPath>'
                   f'<Private>false</Private></Reference>' for n in ["OpenRA.Game", "OpenRA.Mods.Common"])
    (d / "Audit.csproj").write_text(
        '<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net10.0</TargetFramework>'
        '<AssemblyName>OpenRA.Mods.RTSAIAudit</AssemblyName><EnableDefaultCompileItems>false</EnableDefaultCompileItems>'
        '<LangVersion>latest</LangVersion><Nullable>disable</Nullable></PropertyGroup>'
        f'<ItemGroup><Compile Include="{escape(str(SRC))}" />{refs}</ItemGroup></Project>', encoding="utf-8")
    r = subprocess.run(["dotnet", "build", str(d / "Audit.csproj"), "-c", "Release", "-o", str(dll.parent), "--nologo",
                        "-v:q"], capture_output=True, text=True, timeout=300)
    if r.returncode:
        print(r.stdout + r.stderr)
        raise SystemExit("audit assembly did not compile")
    return dll


def run_audit(worktree: Path, content: Path | None, out: Path, cache: Path, utility_args: list[str] | None = None,
              mod_yaml: Path | None = None, mod: str = "rtsai"):
    engine = worktree / "engine"
    dll = compile_command(engine, cache)
    sandbox = Path(tempfile.mkdtemp(prefix="sa-audit-", dir=cache))
    try:
        eng = sandbox / "engine"
        eng.mkdir()
        for name in ["bin", "mods", "glsl"]:
            link_dir(eng / name, engine / name)
        for f in engine.iterdir():
            if f.is_file():
                shutil.copy2(f, eng / f.name)   # VERSION, "global mix database.dat" (XCC name table, not EA data)
        (eng / "Support").mkdir()
        if content:
            link_dir(eng / "Support" / "Content", content)
        mods = sandbox / "mods"
        mods.mkdir()
        for entry in (worktree / "mods").iterdir():
            if not entry.is_dir():
                continue
            if entry.name != mod:
                link_dir(mods / entry.name, entry)
                continue
            (mods / mod).mkdir()
            for item in entry.iterdir():
                if item.is_dir():
                    link_dir(mods / mod / item.name, item)
                elif item.name == "mod.yaml":
                    # --mod-yaml: measure with another manifest (e.g. main's, which mounts the RA2 content)
                    text = (mod_yaml or item).read_text(encoding="utf-8").replace("\r\n", "\n")
                    text = re.sub(r"^(Assemblies: .+)$", lambda m: m[1] + ", " + str(dll), text, flags=re.M)
                    (mods / mod / "mod.yaml").write_text(text, encoding="utf-8")
                else:
                    shutil.copy2(item, mods / mod / item.name)
        env = {k: v for k, v in os.environ.items() if not k.startswith(("OPENRA_AI_", "RTSAI_"))}
        env.update(ENGINE_DIR=str(eng), MOD_SEARCH_PATHS=str(mods), OPENRA_AI_HOST="0", OPENRA_AI_COMPANION="0",
                   OPENRA_AI_DISABLE_AUTOSTART="1")
        args = utility_args or ["--standalone-audit", str(out)]
        r = subprocess.run(["dotnet", str(engine / "bin" / "OpenRA.Utility.dll"), mod, *args],
                           cwd=engine / "bin", env=env, capture_output=True, text=True, timeout=1800)
        if utility_args:
            out.write_text(r.stdout + r.stderr, encoding="utf-8")
            print(f"exit {r.returncode}; output in {out}")
            return
        if r.returncode or not out.exists():
            log = eng / "Support" / "Logs" / "utility.log"
            print(r.stdout[-4000:], r.stderr[-4000:], log.read_text(errors="replace")[-4000:] if log.exists() else "")
            raise SystemExit("audit run failed")
        print(r.stdout.strip())
    finally:
        unlink_tree_links(sandbox)
        if content:
            assert content.exists(), "content target vanished"


# ------------------------------------------------------------------------------------------------ summary
def summarize(a: dict) -> dict:
    files = a["sprites"]["files"]
    src = a["sprites"]["imageSources"]
    image_files = a["sprites"]["imageFiles"]

    def image_status(img):
        bys = {files[f]["by"] for f in image_files.get(img, []) if f in files}
        if not bys:
            return "nofiles"
        if bys <= {"mod", "engine"}:
            return "project"
        if bys <= {"ea"}:
            return "ea"
        if "ea" in bys:
            return "mixed"
        return "missing" if bys == {"missing"} else "other"

    def sprite_group(img):
        files_ = src.get(img, ["?"])
        first, last = files_[0], files_[-1]
        g = first.split("|")[-1].replace("sequences/", "").replace(".yaml", "")
        if first.startswith("ra2|modern-factions") or first.startswith("ra2|art-preview"):
            g = "modern-factions (new actors)"
        return g, last.split("|")[-1]

    images = {}
    for img in image_files:
        g, last = sprite_group(img)
        images[img] = {"group": g, "override": last, "status": image_status(img)}

    model_src = a["models"]["imageSources"]
    models = {}
    for img, seqs in a["models"]["images"].items():
        bys = {r["by"] for pair in seqs.values() for r in pair}
        first = model_src.get(img, ["?"])[0]
        models[img] = {"status": "project" if bys <= {"mod", "engine"} else ("ea" if bys == {"ea"} else "mixed"),
                       "new": first.startswith("ra2|modern-factions") or first.startswith("ra2|art-preview")}
    return {"images": images, "models": models}


def table(rows, header):
    w = [max(len(str(r[i])) for r in rows + [header]) for i in range(len(header))]
    line = lambda r: "| " + " | ".join(str(c).ljust(w[i]) for i, c in enumerate(r)) + " |"
    return "\n".join([line(header), "|" + "|".join("-" * (x + 2) for x in w) + "|"] + [line(r) for r in rows])


def print_summary(a: dict):
    s = summarize(a)
    pk = Counter((p["class"], p["type"]) for p in a["packages"])
    print("\n## Mounted packages\n")
    print(table([[c, t, n, sum(p["entries"] for p in a["packages"] if p["class"] == c and p["type"] == t)]
                 for (c, t), n in sorted(pk.items())], ["class", "type", "packages", "entries"]))

    # sprite files by provider
    files = a["sprites"]["files"]
    byc = Counter(f["by"] for f in files.values())
    print("\n## Sprite files referenced by sequences (all tilesets)\n")
    print(table([[k, v] for k, v in byc.most_common()], ["provider", "files"]))

    groups = defaultdict(Counter)
    for img, d in s["images"].items():
        groups[d["group"]][d["status"]] += 1
    print("\n## Sprite images by defining sequence file\n")
    rows = [[g, sum(c.values()), c["project"], c["mixed"], c["ea"], c["nofiles"]] for g, c in sorted(groups.items())]
    print(table(rows, ["group", "images", "project", "mixed", "EA only", "no files"]))

    mc = Counter((m["new"], m["status"]) for m in s["models"].values())
    print("\n## Voxel model images\n")
    print(table([["new actor" if n else "stock actor", st, c] for (n, st), c in sorted(mc.items())],
                ["defined for", "status", "images"]))

    print("\n## Terrain\n")
    rows = []
    for ts, t in a["terrain"].items():
        fc = Counter(r["by"] for r in t["files"].values())
        rows.append([ts, len(t["templates"]), len(t["files"]), fc["ea"], fc["mod"] + fc["engine"], fc["missing"]])
    print(table(rows, ["tileset", "templates", "tile files", "EA", "project", "missing"]))

    print("\n## Palettes and Filename fields in rules\n")
    pc = Counter((p["actor"], p["resolve"]["by"]) for p in a["palettes"])
    print(table([[k[0], k[1], v] for k, v in sorted(pc.items())], ["actor", "provider", "fields"]))

    for key in ["cursors", "chrome"]:
        c = Counter(x["resolve"]["by"] for x in a[key] if x["resolve"])
        print(f"\n## {key}: " + ", ".join(f"{k} {v}" for k, v in c.items()))
    print("fonts: " + ", ".join(f"{r['file']}={r['by']}" for r in a["fonts"] if r))
    print("load screen: " + ", ".join(f"{r['file']}={r['by']}" for r in a["loadScreen"] if r))

    au = a["audio"]
    print("\n## Audio\n")
    rows = []
    for kind in ["voices", "notifications"]:
        src = au["voiceSources" if kind == "voices" else "notificationSources"]
        for set_name, variants in au[kind].items():
            origin = src.get(set_name, ["?"])[0].split("|")[-1]
            for variant, lst in variants.items():
                c = Counter(x["r"]["by"] for x in lst)
                if variant != "_default" and json.dumps(lst) == json.dumps(variants["_default"]):
                    continue
                rows.append([kind, set_name, origin, variant, len(lst), c["ea"], c["mod"] + c["engine"], c["missing"]])
    print(f"(voice/notification set x faction rows: {len(rows)}; aggregated below)")
    agg = defaultdict(Counter)
    for kind, set_name, origin, variant, n, ea, pr, mi in rows:
        modern_v = variant in MODERN
        stock_v = variant not in MODERN and variant != "_default"
        key = (kind, "modern-factions" in origin or "levant" in origin, "modern" if modern_v else ("stock" if stock_v else "default"))
        agg[key]["sets"] += 1
        agg[key]["files"] += n
        agg[key]["ea"] += ea
        agg[key]["project"] += pr
        agg[key]["missing"] += mi
    print(table([[k[0], "new" if k[1] else "stock", k[2], c["sets"], c["files"], c["ea"], c["project"], c["missing"]]
                 for k, c in sorted(agg.items())], ["kind", "set defined", "variant", "rows", "refs", "EA", "project", "missing"]))
    mu = Counter(m["r"]["by"] for m in au["music"])
    print("music: " + ", ".join(f"{k} {v}" for k, v in mu.items()))
    rs = Counter(r["by"] for r in au["ruleSounds"].values())
    print("rule/weapon sound refs: " + ", ".join(f"{k} {v}" for k, v in rs.items()))

    print("\n## Maps\n")
    rows = []
    for m in a["maps"]:
        if "error" in m:
            rows.append([m["folder"], "ERROR " + m["error"][:60], "", "", "", ""])
            continue
        rows.append([m["folder"], m["tileset"], m["players"], len(m["templates"]), sum(m["actors"].values()),
                     sum(m["resources"].values())])
    print(table(rows, ["map", "tileset", "players", "templates used", "actors", "resource cells"]))


def is_new(acts, x):
    s = acts[x]["sources"]
    return bool(s) and (s[0].startswith("ra2|modern-factions") or s[0].startswith("ra2|art-preview"))


def inventory(a: dict) -> dict:
    """Per-category EA dependency counts for the standalone plan (docs/standalone.md)."""
    acts, reach = a["actors"], a["reachable"]
    files, imf = a["sprites"]["files"], a["sprites"]["imageFiles"]
    isrc = a["sprites"]["imageSources"]
    models = a["models"]["images"]
    stock_factions = [f for f in reach if f not in MODERN and reach[f]["actors"]]

    def group(img):
        s = isrc.get(img, ["?"])[0]
        return "new" if (s.startswith("ra2|modern-factions") or s.startswith("ra2|art-preview")) else \
            s.split("|")[-1].replace("sequences/", "").replace(".yaml", "")

    def actor_images(x, with_weapons=True):
        imgs = set(i for i in acts[x]["images"] if i in imf)
        if with_weapons:
            imgs |= set(i for i in acts[x]["weaponImages"] if i in imf)
        return imgs

    def ea_files(imgs, only=None):
        out = set()
        for i in imgs:
            if only and group(i) not in only:
                continue
            out |= {f for f in imf.get(i, []) if files.get(f, {}).get("by") == "ea"}
        return out

    def model_files(imgs):
        out = Counter()
        for i in imgs:
            for pair in models.get(i, {}).values():
                for r in pair:
                    out[r["by"]] += 1
        return out

    modern_reach = set().union(*(reach[f]["actors"] for f in MODERN))
    stock_reach = set().union(*(reach[f]["actors"] for f in stock_factions))
    new = {x for x in modern_reach if is_new(acts, x)}
    proxies = {x for x in modern_reach if not actor_images(x) and not any(i in models for i in acts[x]["images"])}
    shared = modern_reach - new - proxies
    originals = stock_reach - modern_reach
    map_actors = Counter()
    for m in a["maps"]:
        for t, n in m.get("actors", {}).items():
            map_actors[t] += n
    map_only = {t for t in map_actors if t in acts and t not in modern_reach | stock_reach and t not in ("mpspawn",)}

    misc_groups = {"misc"}
    inv = {}

    # buildings vs units among the shared stock actors
    def is_building(x):
        return any(s.split("|")[-1].endswith("structures.yaml") for s in acts[x]["sources"][:1])

    sb = {x for x in shared if is_building(x)}
    su = shared - sb
    for key, group_actors in [("shared_buildings", sb), ("shared_units", su), ("new_actors", new),
                              ("original_faction_actors", originals), ("map_only_actors", map_only)]:
        imgs = set().union(*(actor_images(x) for x in group_actors)) if group_actors else set()
        own = {i for i in imgs if group(i) not in misc_groups}
        inv[key] = {
            "actors": sorted(group_actors),
            "count": len(group_actors),
            "ea_sprite_files": len(ea_files(own)),
            "project_sprite_files": len({f for i in own for f in imf.get(i, []) if files.get(f, {}).get("by") in ("mod", "engine")}),
            "model_refs": dict(model_files(imgs)),
        }

    # effects: misc.yaml images reachable from modern actors (incl. weapons) + EA files inside new-actor sequences
    fx_imgs = set().union(*(actor_images(x) for x in modern_reach)) if modern_reach else set()
    fx = ea_files(fx_imgs, only=misc_groups)
    residue = ea_files({i for i in fx_imgs if group(i) == "new"})
    inv["effects"] = {"misc_images": sorted(i for i in fx_imgs if group(i) in misc_groups),
                      "ea_files_misc": len(fx), "ea_files_in_new_sequences": sorted(residue)}
    all_misc = {i for i in imf if group(i) in misc_groups}
    inv["effects"]["misc_images_total"] = len(all_misc)
    inv["effects"]["ea_files_misc_total"] = len(ea_files(all_misc))

    # sounds written in rules/weapons, attributed to modern-reachable actors and their weapons
    def rule_sounds(actor_set):
        weapons = set().union(*(set(acts[x]["weapons"]) for x in actor_set)) if actor_set else set()
        out = {}
        for k, r in a["audio"]["ruleSounds"].items():
            kind, name = k.split(":")[0], k.split(":")[1]
            if (kind == "actor" and name in actor_set) or (kind == "weapon" and name in weapons):
                out[r["file"]] = r["by"]
        return out

    for key, s in [("sfx_modern", rule_sounds(modern_reach)), ("sfx_new_only", rule_sounds(new)),
                   ("sfx_all", {r["file"]: r["by"] for r in a["audio"]["ruleSounds"].values()})]:
        inv[key] = dict(Counter(s.values()))
    inv["sfx_new_only_ea_files"] = sorted(f for f, b in rule_sounds(new).items() if b == "ea")

    # unit voices per faction (variant = faction), only for actors that faction can reach; unique files per side
    voices = {k.lower(): v for k, v in a["audio"]["voices"].items()}
    vo = defaultdict(dict)
    for f in MODERN + stock_factions:
        side = "modern" if f in MODERN else "original"
        for x in reach[f]["actors"]:
            who = "new actors" if is_new(acts, x) else "stock actors"
            for vs in acts[x]["voiceSets"]:
                for e in voices.get(vs.lower(), {}).get(f, []):
                    vo[f"{side}/{who}"][e["r"]["file"]] = e["r"]["by"]
    inv["voices"] = {k: dict(Counter(v.values())) for k, v in vo.items()}

    # announcer / UI notifications: unique files per side
    no = defaultdict(dict)
    for set_name, variants in a["audio"]["notifications"].items():
        for f in MODERN + stock_factions:
            for e in variants.get(f, []):
                no[f"{set_name}/{'modern' if f in MODERN else 'original'}"][e["r"]["file"]] = e["r"]["by"]
    inv["notifications"] = {k: dict(Counter(v.values())) for k, v in no.items()}
    inv["ui_sounds_ea"] = sorted(f for f, b in no.get("sounds/modern", {}).items() if b == "ea")
    inv["music"] = dict(Counter(m["r"]["by"] for m in a["audio"]["music"]))

    # UI
    inv["chrome"] = dict(Counter(x["resolve"]["by"] for x in a["chrome"]))
    inv["chrome_files"] = sorted({x["resolve"]["file"] for x in a["chrome"]})
    inv["cursors"] = [(x["resolve"]["file"], x["resolve"]["by"], x["sequences"]) for x in a["cursors"]]
    pal = {}
    for p in a["palettes"]:
        if p["actor"] == "world":
            pal[p["resolve"]["file"]] = p["resolve"]["by"]
    inv["palettes"] = dict(Counter(pal.values()))
    inv["palettes_ea"] = sorted(f for f, b in pal.items() if b == "ea")
    inv["fonts"] = sorted({f"{r['file']}={r['by']}" for r in a["fonts"] if r})
    inv["load_screen"] = [f"{r['file']}={r['by']}" for r in a["loadScreen"] if r]

    # terrain and maps
    inv["terrain"] = {ts: {"templates": len(t["templates"]), "tile_files": len(t["files"]),
                           "ea": sum(r["by"] == "ea" for r in t["files"].values())} for ts, t in a["terrain"].items()}
    inv["maps"] = {"count": len(a["maps"]),
                   "playable": sum(1 for m in a["maps"] if m.get("players", 0) > 0),
                   "by_tileset": dict(Counter(m.get("tileset") for m in a["maps"])),
                   "actor_instances": sum(map_actors.values()),
                   "actor_instances_map_only": sum(n for t, n in map_actors.items() if t in map_only),
                   "maps_with_resources": sum(1 for m in a["maps"] if m.get("resources"))}

    # packages
    inv["packages"] = dict(Counter(f"{p['class']}:{p['type']}" for p in a["packages"]))
    inv["ea_entries_mounted"] = sum(p["entries"] for p in a["packages"] if p["class"] == "ea")
    inv["all_sprite_files"] = dict(Counter(f["by"] for f in files.values()))
    inv["all_models"] = dict(Counter(r["by"] for seqs in models.values() for pair in seqs.values() for r in pair))
    inv["factions"] = {"modern": MODERN, "original": stock_factions}
    return inv


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--worktree", type=Path, default=ROOT)
    ap.add_argument("--content", type=Path, help="installed RA2 content dir to measure against (never copied)")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--cache", type=Path, default=Path(tempfile.gettempdir()) / "rtsai-standalone-audit")
    ap.add_argument("--summary", action="store_true")
    ap.add_argument("--mod-yaml", type=Path, help="use this manifest for mods/rtsai instead of the worktree's")
    ap.add_argument("--mod", default="rtsai", help="mod id to audit (e.g. rtsai-classic)")
    ap.add_argument("--summary-only", action="store_true", help="summarize an existing --out without running")
    ap.add_argument("--utility", nargs=argparse.REMAINDER,
                    help="run another utility command in the same sandbox instead (e.g. --check-yaml); output to --out")
    a = ap.parse_args()
    a.cache.mkdir(parents=True, exist_ok=True)
    if a.utility:
        run_audit(a.worktree.resolve(), a.content.resolve() if a.content else None, a.out.resolve(), a.cache, a.utility,
                  a.mod_yaml, a.mod)
        return
    if not a.summary_only:
        run_audit(a.worktree.resolve(), a.content.resolve() if a.content else None, a.out.resolve(), a.cache,
                  None, a.mod_yaml, a.mod)
    if a.summary or a.summary_only:
        data = json.loads(a.out.read_text(encoding="utf-8"))
        print_summary(data)
        inv = inventory(data)
        inv_path = a.out.with_name(a.out.stem + "-inventory.json")
        inv_path.write_text(json.dumps(inv, indent=1), encoding="utf-8")
        print(f"\ninventory: {inv_path}")


if __name__ == "__main__":
    main()
