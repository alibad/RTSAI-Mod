#!/usr/bin/env python3
"""One-shot port of the OpenRA AI RA2 game data into mods/rtsai (spike provenance).

Reproduces what OpenRA-AI/scripts/prepare-ra2.py builds today, minus the
modern-faction overlay and the Experience system, and re-homes it as an SDK mod:

  1. upstream OpenRA/ra2 @ 61e24e3 (exported with `git archive`, read-only)
  2. + OpenRA-AI/apps/installer/ra2/compatibility.patch (read-only)
  3. + the non-experience subset of prepare-ra2.py:integrate()
  4. + SDK re-homing: mod id rtsai, ContentInstallerFileSystem with the
       rtsai-content installer mod, mod-owned assemblies.

No proprietary data is read or written. Run from the repo root:
  python tools/port-ra2.py [--upstream ../OpenRA-Upstreams/ra2] [--product ../OpenRA-AI]
"""
from __future__ import annotations

import argparse
import io
import re
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM_COMMIT = "61e24e3c1d7b586aa55a86096d29e1559aa9b994"
BOT_PROFILES = ("normal", "medium", "rush", "turtle", "naval")


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise ValueError(f"Expected one anchor in {path}: {old!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8", newline="\n")


def replace_block(text: str, key: str, block: str) -> str:
    """Replace a top-level MiniYAML node (key line + indented children)."""
    pattern = re.compile(rf"^{re.escape(key)}:.*\n(?:(?:\t.*)?\n)*?(?=^\S)", re.MULTILINE)
    if len(pattern.findall(text)) != 1:
        raise ValueError(f"Expected one top-level {key} block")
    return pattern.sub(lambda _: block, text, count=1)


def trim_off_map_fences(text: str) -> str:
    """Copied from prepare-ra2.py: drop fence actors outside the playable bounds."""
    bounds = re.search(r"^Bounds: (\d+),(\d+),(\d+),(\d+)$", text, re.MULTILINE)
    if bounds is None:
        raise ValueError("RA2 map has no rectangular bounds")
    left, top, width, height = map(int, bounds.groups())

    def keep_actor(match: re.Match[str]) -> str:
        block = match.group()
        if not re.match(r"\t[^:\n]+: cafncp\n", block):
            return block
        location = re.search(r"\t\tLocation: (-?\d+),(-?\d+)", block)
        x, y = map(int, location.groups())
        v = x + y
        u = (v - (v & 1)) // 2 - y
        return block if left <= u < left + width and top <= v < top + height else ""

    return re.sub(r"^\t[^\t\n][^\n]*\n(?:\t\t[^\n]*\n)*", keep_actor, text, flags=re.MULTILINE)


FILESYSTEM = """FileSystem: ContentInstallerFileSystem
\tSystemPackages:
\t\t^EngineDir
\t\t$rtsai: ra2
\t\t^EngineDir|mods/common: common
\t\t~^SupportDir|Content/ra2: content
\t\tra2|uibits
\tContentPackages:
\t\t# Red Alert 2 (original game files installed by rtsai-content)
\t\tcontent|language.mix: lang
\t\tcontent|ra2.mix: ra2mix
\t\t~content|theme.mix
\t\tlang|cameo.mix: cameo
\t\t~lang|audio.mix: audio
\t\t~audio|audio.bag
\t\t~lang|audio.bag
\t\tra2mix|cache.mix: cache
\t\tra2mix|conquer.mix: conquer
\t\tra2mix|generic.mix
\t\tra2mix|isogen.mix
\t\tra2mix|isosnow.mix
\t\tra2mix|isotemp.mix
\t\tra2mix|isourb.mix
\t\tra2mix|load.mix
\t\tra2mix|local.mix: local
\t\tra2mix|neutral.mix
\t\tra2mix|sidec01.mix
\t\tra2mix|sidec02.mix
\t\tra2mix|sno.mix
\t\tra2mix|snow.mix
\t\tra2mix|tem.mix
\t\tra2mix|temperat.mix
\t\tra2mix|urb.mix
\t\tra2mix|urban.mix
\t\t# Mod-provided packages load after content so they can override it.
\t\tra2|bits
\t\tra2|bits/cameos
\t\tra2|bits/structures
\t\tra2|bits/animations
\t\tra2|bits/projectiles
\tContentInstallerMod: rtsai-content

"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--upstream", type=Path, default=ROOT.parent / "OpenRA-Upstreams/ra2")
    parser.add_argument("--product", type=Path, default=ROOT.parent / "OpenRA-AI")
    parser.add_argument("--engine", type=Path, default=ROOT / "engine")
    args = parser.parse_args()

    work = Path(tempfile.mkdtemp(prefix="port-ra2-"))
    archive = subprocess.check_output(["git", "-C", str(args.upstream), "archive", UPSTREAM_COMMIT, "mods/ra2"])
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        tar.extractall(work)

    patch = (args.product / "apps/installer/ra2/compatibility.patch").read_text(encoding="utf-8")
    # Only the data half of the patch; the C# half is superseded by the fork's net10 OpenRA.Mods.RA2.
    data_patch = work / "data.patch"
    chunks = re.split(r"(?m)^(?=--- a/)", patch.replace("\r\n", "\n"))
    data_patch.write_text("".join(c for c in chunks if c.startswith("--- a/mods/")), encoding="utf-8", newline="\n")
    subprocess.check_call(["git", "-c", "core.autocrlf=false", "apply", str(data_patch)], cwd=work)

    mod = work / "mods/ra2"
    manifest = mod / "mod.yaml"

    # --- prepare-ra2.py:integrate() subset (no experiences, no modern factions) ---
    replace_once(manifest, "ra2|chrome/native-mainmenu.yaml", "common|chrome/mainmenu.yaml")
    replace_once(manifest, "ra2|chrome/native-settings.yaml", "common|chrome/settings.yaml\n\tcommon|chrome/settings-ai.yaml")
    replace_once(manifest, "Rules:\n", "Rules:\n\tra2|rules/companion.yaml\n")
    (mod / "rules/companion.yaml").write_text("^BaseWorld:\n\tRTSAICompanionBridge:\n", encoding="utf-8", newline="\n")
    ra_hud = (args.engine / "mods/ra/chrome/ingame-player.yaml").read_text(encoding="utf-8")
    start = ra_hud.index("\t\tBackground@AI_COMPANION_STRIP:")
    end = ra_hud.index("\t\tLogicKeyListener@PLAYER_KEYHANDLER:", start)
    replace_once(mod / "chrome/ingame-player.yaml", "\t\tContainer@CHAT_ROOT:\n", "\t\tContainer@CHAT_ROOT:\n" + ra_hud[start:end])
    ai = (mod / "rules/ai.yaml").read_text(encoding="utf-8").removeprefix("Player:\n")
    profiles = []
    for profile in BOT_PROFILES:
        rules = ai.replace("@testai", "@" + profile).replace("@test", "@" + profile)
        rules = rules.replace("enable-test-ai", f"enable-{profile}-ai")
        rules = rules.replace("Type: test", f"Type: {profile}").replace("Bots: test", f"Bots: {profile}")
        rules = rules.replace("Name: Test AI", f"Name: ra2-bot-{profile}")
        for module in ("HarvesterBotModule", "BuildingRepairBotModule"):
            rules = rules.replace(f"\t{module}:\n", f"\t{module}@{profile}:\n")
        if profile == "rush":
            rules = rules.replace("SquadSize: 5", "SquadSize: 3")
        elif profile == "turtle":
            rules = rules.replace("SquadSize: 5", "SquadSize: 12").replace("gapill: 10", "gapill: 25").replace("nalasr: 10", "nalasr: 25")
        elif profile == "naval":
            rules = rules.replace("dest: 20", "dest: 60").replace("sub: 20", "sub: 60")
        profiles.append(rules)
    (mod / "rules/ai.yaml").write_text("Player:\n" + "".join(profiles), encoding="utf-8", newline="\n")
    (mod / "languages/native-preview.ftl").write_text(
        "ra2-preview-window-title = RTS AI — Red Alert 2\n"
        "ra2-preview-note = Red Alert 2 with the shared AI assistant. Original campaigns and Yuri’s Revenge are not included.\n"
        + "".join(f"ra2-bot-{p} = RA2 {p.title()} AI\n" for p in BOT_PROFILES),
        encoding="utf-8", newline="\n")
    for path in (mod / "maps").glob("*/map.yaml"):
        path.write_text(trim_off_map_fences(path.read_text(encoding="utf-8")), encoding="utf-8", newline="\n")
    replace_once(mod / "chrome.yaml", "common|native-ra2-glyphs.png", "ra2|uibits/native-ra2-glyphs.png")
    shutil.copy2(args.engine / "mods/ts/uibits/glyphs.png", mod / "uibits/native-ra2-glyphs.png")

    # --- SDK re-homing ---
    text = manifest.read_text(encoding="utf-8")
    text = text.replace("\tTitle: Red Alert 2\n", "\tTitle: RTS AI\n", 1)
    text = replace_block(text, "FileSystem", FILESYSTEM)
    text = text.replace("\t~^maps/ra2/{DEV_VERSION}: User", "\t~^SupportDir|maps/rtsai/{DEV_VERSION}: User")
    text = text.replace("Assemblies: OpenRA.Mods.Common.dll, OpenRA.Mods.Cnc.dll, OpenRA.Mods.RA2.dll",
                        "Assemblies: OpenRA.Mods.Common.dll, OpenRA.Mods.Cnc.dll, OpenRA.Mods.RA2.dll, OpenRA.Mods.RTSAI.dll")
    # Content installation moves to the rtsai-content mod.
    text = re.sub(r"(?ms)^ModContent:\n.*?(?=^\S|\Z)", "", text).rstrip("\n") + "\n"
    manifest.write_text(text, encoding="utf-8", newline="\n")
    shutil.rmtree(mod / "installer")

    dest = ROOT / "mods/rtsai"
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(mod, dest)
    if any(dest.rglob("*.mix")):
        raise ValueError("Proprietary RA2 data must not be committed")
    shutil.rmtree(work, ignore_errors=True)
    print(f"Ported RA2 data to {dest}")


if __name__ == "__main__":
    main()
