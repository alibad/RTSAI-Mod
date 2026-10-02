#!/usr/bin/env python3
"""Port the OpenRA AI modern factions (China, Iran, Türkiye) into mods/rtsai as plain mod rules.

Source (read-only): OpenRA-AI/apps/installer/ra2/modern-factions (working tree) plus the
original faction voice lines and flag art that the product build copies out of the
alibad/OpenRA fork (mods/ra/bits, mods/ra/uibits/glyphs-redsea.png) at FORK_COMMIT.

What the Experience system used to do at load time is done here once, statically:
  * every faction file is listed in mod.yaml (no ExperienceCatalog / profiles / gating);
  * the per-faction "~!faction.X" prerequisite exclusions are merged into
    shared-replacements.yaml (same algorithm as prepare-ra2.py:combined_replacements);
  * the fork-only Faction.RandomFactionMemberOf field becomes upstream RandomFactionMembers
    on the random-allies / random-soviets pools;
  * flags are appended to the lobby flag atlas, FactionSuffix metrics are added.
Not ported: ra2-combined-arms-ai (needs the fork's bot-module changes), experience previews.

Needs Pillow (e.g. OpenRA-AI/.venv). Run from the repo root:
  python tools/port-modern-factions.py [--product ../OpenRA-AI] [--fork ../OpenRA]
"""
from __future__ import annotations

import argparse
import io
import re
import shutil
import subprocess
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
FORK_COMMIT = "5ddc34cb91e52953d4844c169075a0dbbd79e139"
FACTIONS = {  # internal name -> (side, random pool, flag crop origin in glyphs-redsea.png)
    "china": ("Allies", "random-allies", (192, 128)),
    "iran": ("Soviets", "random-soviets", (226, 33)),
    "turkey": ("Allies", "random-allies", (226, 113)),
}
FLAG_SIZE = (30, 15)
SKIP = {"experiences.yaml", "combined-arms-ai.yaml"}


def fork_file(fork: Path, path: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(fork), "show", f"{FORK_COMMIT}:{path}"])


def combined_replacements(modern: Path) -> str:
    prerequisites: dict[str, list[list[str]]] = {}
    for country in FACTIONS:
        actor = None
        for line in (modern / f"{country}-replacements.yaml").read_text(encoding="utf-8").splitlines():
            if line and not line[0].isspace() and not line.startswith("#"):
                actor = line.removesuffix(":")
            elif line.startswith("\t\tPrerequisites: "):
                items = line.split(": ", 1)[1].split(", ")
                base = [i for i in items if not i.startswith("~!faction.")]
                previous = prerequisites.setdefault(actor, [base, []])
                if previous[0] != base:
                    raise ValueError(f"Inconsistent prerequisites for {actor}")
                previous[1].append("~!faction." + country)
    return "".join(f"{a}:\n\tBuildable:\n\t\tPrerequisites: {', '.join(b + e)}\n\n" for a, (b, e) in sorted(prerequisites.items()))


ADDITIONAL_FIELDS = {"AdditionalDefenseTypes": "DefenseTypes",
                     "AdditionalAirUnitsTypes": "AirUnitsTypes",
                     "AdditionalNavalUnitsTypes": "NavalUnitsTypes"}


def fold_additional_bot_types(mod: Path, dest: Path) -> None:
    """The fork-only bot fields Additional{Defense,AirUnits,NavalUnits}Types append per-faction types.

    Fold them into the upstream DefenseTypes/AirUnitsTypes/NavalUnitsTypes of every bot profile
    (bot-types.yaml). Global merging is safe: bots only build what their prerequisites allow, and
    squad typing of units a bot can never own has no effect.
    """
    extra: dict[tuple[str, str], list[str]] = {}
    for country in FACTIONS:
        path = dest / f"{country}-ai.yaml"
        lines = path.read_text(encoding="utf-8").split("\n")
        out, module, i = [], None, 0
        while i < len(lines):
            line = lines[i]
            m = re.match(r"^\t([A-Za-z]+@[\w-]+):", line)
            if m:
                module = m.group(1)
            f = re.match(r"^\t\t(Additional\w+Types):$", line)
            if f and f.group(1) in ADDITIONAL_FIELDS:
                i += 1
                while i < len(lines) and lines[i].startswith("\t\t\t"):
                    values = lines[i].split(":", 1)[1]
                    extra.setdefault((module, ADDITIONAL_FIELDS[f.group(1)]), []).extend(
                        v.strip() for v in values.split(",") if v.strip())
                    i += 1
                continue
            out.append(line)
            i += 1
        path.write_text("\n".join(out), encoding="utf-8", newline="\n")

    ai_rules = (mod / "rules/ai.yaml").read_text(encoding="utf-8")
    merged: dict[str, list[str]] = {}
    for (module, field), values in sorted(extra.items()):
        block = re.search(rf"^\t{re.escape(module)}:\n((?:\t\t.*\n)+)", ai_rules, re.MULTILINE)
        base = re.search(rf"^\t\t{field}: (.*)$", block.group(1), re.MULTILINE) if block else None
        if base is None:
            raise ValueError(f"rules/ai.yaml has no {module}.{field} to extend")
        current = [v.strip() for v in base.group(1).split(",")]
        merged.setdefault(module, []).append(
            f"\t\t{field}: {', '.join(current + [v for v in dict.fromkeys(values) if v not in current])}\n")
    (dest / "bot-types.yaml").write_text(
        "# Generated by tools/port-modern-factions.py: upstream bot type lists plus the modern factions' types.\nPlayer:\n"
        + "".join(f"\t{m}:\n" + "".join(v) for m, v in merged.items()), encoding="utf-8", newline="\n")


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise ValueError(f"Expected one anchor in {path}: {old!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--product", type=Path, default=ROOT.parent / "OpenRA-AI")
    parser.add_argument("--fork", type=Path, default=ROOT.parent / "OpenRA")
    args = parser.parse_args()

    src = args.product / "apps/installer/ra2/modern-factions"
    mod = ROOT / "mods/rtsai"
    dest = mod / "modern-factions"
    if dest.exists():
        raise SystemExit(f"{dest} exists; this is a one-shot port")
    shutil.copytree(src, dest, ignore=shutil.ignore_patterns(*SKIP, "previews", "source-art-review.png"))

    # Faction.RandomFactionMemberOf is a fork-only field: drop it, extend the upstream pools instead.
    for country in FACTIONS:
        path = dest / f"{country}.yaml"
        text = path.read_text(encoding="utf-8")
        text, n = re.subn(r"^\t\tRandomFactionMemberOf: .*\n", "", text, flags=re.MULTILINE)
        if n != 1:
            raise ValueError(f"{path}: expected one RandomFactionMemberOf")
        path.write_text(text, encoding="utf-8", newline="\n")
    world = mod / "rules/world.yaml"
    for pool, members in (("random-allies", "america, germany, england, france, korea"),
                          ("random-soviets", "cuba, libya, iraq, russia")):
        extra = [c for c, (_, p, _) in FACTIONS.items() if p == pool]
        replace_once(world, f"\t\tInternalName: {pool}\n\t\tRandomFactionMembers: {members}\n",
                     f"\t\tInternalName: {pool}\n\t\tRandomFactionMembers: {members}, {', '.join(extra)}\n")

    (dest / "shared-replacements.yaml").write_text(combined_replacements(dest), encoding="utf-8", newline="\n")
    fold_additional_bot_types(mod, dest)

    # BaseBuilderBotModule.InitialBuildOrder (deterministic openings) is a fork-only bot feature;
    # upstream bots still follow the BuildingFractions that remain.
    aircraft_ai = dest / "aircraft-ai.yaml"
    text, n = re.subn(r"^\t\tInitialBuildOrder: .*\n", "", aircraft_ai.read_text(encoding="utf-8"), flags=re.MULTILINE)
    if n == 0:
        raise ValueError("aircraft-ai.yaml: expected InitialBuildOrder entries")
    aircraft_ai.write_text(text, encoding="utf-8", newline="\n")

    # Original bilingual voice lines referenced by the faction voice/notification rules.
    names = set()
    for path in dest.glob("*.yaml"):
        names.update(re.findall(r"ra2\|modern-factions/audio/([\w-]+)", path.read_text(encoding="utf-8")))
    (dest / "audio").mkdir()
    for name in sorted(names):
        (dest / "audio" / f"{name}.wav").write_bytes(fork_file(args.fork, f"mods/ra/bits/{name}.wav"))

    # Lobby flags: extend the RA2 button atlas (prepare-ra2.py:extend_flag_atlas).
    buttons = mod / "uibits/buttons.png"
    flags = Image.open(io.BytesIO(fork_file(args.fork, "mods/ra/uibits/glyphs-redsea.png")))
    with Image.open(buttons) as original:
        width, height = FLAG_SIZE
        required = (max(original.width, len(FACTIONS) * width), original.height + height)
        atlas = Image.new("RGBA", tuple(1 << (size - 1).bit_length() for size in required))
        atlas.paste(original.convert("RGBA"), (0, 0))
        regions = []
        for i, (country, (_, _, (x, y))) in enumerate(FACTIONS.items()):
            atlas.paste(flags.crop((x, y, x + width, y + height)).convert("RGBA"), (width * i, original.height))
            regions.append(f"\t\t{country}: {width * i}, {original.height}, {width}, {height}\n")
    atlas.save(buttons)
    replace_once(mod / "chrome.yaml", "flags:\n\tImage: buttons.png\n\tRegions:\n", "flags:\n\tImage: buttons.png\n\tRegions:\n" + "".join(regions))

    replace_once(mod / "metrics.yaml", "Metrics:\n",
                 "Metrics:\n" + "".join(f"\tFactionSuffix-{c}: {s.lower()}\n" for c, (s, _, _) in FACTIONS.items()))

    # Upstream carrier declares RevealsShroud twice; the Türkiye exclusion merge makes it ambiguous.
    replace_once(mod / "rules/allied-naval.yaml",
                 "\tMobile:\n\t\tTurnSpeed: 4\n\t\tSpeed: 60\n\tRevealsShroud:\n\t\tRange: 7c0\n\tAttackFrontal:",
                 "\tMobile:\n\t\tTurnSpeed: 4\n\t\tSpeed: 60\n\tAttackFrontal:")

    # Register everything statically in the manifest.
    manifest = mod / "mod.yaml"
    mf = "ra2|modern-factions/"
    rules = ["common.yaml", "aircraft-ai.yaml", "shared-replacements.yaml", "bot-types.yaml"]
    sequences, voices, weapons, models, messages = [], [], ["weapons.yaml"], ["voxels.yaml"], ["messages.ftl"]
    for c in FACTIONS:
        rules += [f"{c}.yaml", f"{c}-roster.yaml", f"{c}-ai.yaml", f"{c}-audio.yaml"]
        if (dest / f"{c}-roles.yaml").exists():
            rules.append(f"{c}-roles.yaml")
        sequences += [f"{c}-sequences.yaml", f"{c}-roster-sequences.yaml"]
        voices.append(f"{c}-voices.yaml")
        weapons.append(f"{c}-weapons.yaml")
        models.append(f"{c}-voxels.yaml")
        messages.append(f"{c}-messages.ftl")
    text = manifest.read_text(encoding="utf-8")

    def append_to(section: str, files: list[str]) -> None:
        nonlocal text
        m = re.search(rf"^{section}:\n((?:\t.*\n)+)", text, re.MULTILINE)
        if m is None:
            raise ValueError(f"No {section} section")
        text = text[:m.end()] + "".join(f"\t{mf}{f}\n" for f in files) + text[m.end():]

    append_to("Rules", rules)
    append_to("Sequences", sequences)
    append_to("ModelSequences", models)
    append_to("Voices", voices)
    append_to("Weapons", weapons)
    append_to("FluentMessages", messages)
    manifest.write_text(text, encoding="utf-8", newline="\n")
    print(f"Ported {len(FACTIONS)} factions, {len(names)} voice lines into {dest}")


if __name__ == "__main__":
    main()
