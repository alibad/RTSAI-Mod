#!/usr/bin/env python3
"""Port the OpenRA AI modern factions into mods/rtsai as plain mod rules.

Round A (China, Iran, Türkiye) came from OpenRA-AI/apps/installer/ra2/modern-factions. Round B
(Saudi Arabia, Yemen) comes from the same directory in the codex/ra2-red-sea worktree, using its
working-tree state (see --product). Original faction voice lines, weapon/naval SFX and flag art
that the product build copies out of the alibad/OpenRA fork (mods/ra/bits, mods/ra/uibits/
glyphs-redsea.png) are read at FORK_COMMIT.

What the Experience system used to do at load time is done here once, statically:
  * every faction file is listed in mod.yaml (no ExperienceCatalog / profiles / gating);
  * the per-faction "~!faction.X" prerequisite exclusions are merged into
    shared-replacements.yaml (same algorithm as prepare-ra2.py:combined_replacements);
  * the fork-only Faction.RandomFactionMemberOf field becomes upstream RandomFactionMembers
    on the random-allies / random-soviets pools;
  * the fork-only bot fields Additional{Defense,AirUnits,NavalUnits}Types are folded into
    bot-types.yaml;
  * flags are appended to the lobby flag atlas, FactionSuffix metrics are added.

The tool is incremental: it ports the requested factions that mod.yaml does not list yet, and
recomputes the shared files (replacements, bot types, pools, flags, manifest) to include them.

--doctrine-ai switches the bots to the role-aware modules in OpenRA.Mods.RTSAI (the fork's
combined-arms AI): stock BaseBuilderBotModule/UnitBuilderBotModule/SquadManagerBotModule become
DoctrineBaseBuilderBotModule/DoctrineUnitBuilderBotModule/DoctrineSquadManagerBotModule, the fork's InitialBuildOrder openings
and combined-arms-ai.yaml (RoleShares and stock StrategicRole tags) are restored from the source.

Needs Pillow (e.g. OpenRA-AI/.venv). Run from the repo root:
  python tools/port-modern-factions.py --factions china,iran,turkey --product ../OpenRA-AI        # round A
  python tools/port-modern-factions.py --factions saudi,yemen \\
      --product ../OpenRA-AI-wt-ra2-red-sea --doctrine-ai                                          # round B
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
    "saudi": ("Allies", "random-allies", (226, 1)),
    "yemen": ("Soviets", "random-soviets", (226, 17)),
}
STOCK_POOLS = {"random-allies": "america, germany, england, france, korea",
               "random-soviets": "cuba, libya, iraq, russia"}
FLAG_SIZE = (30, 15)
SKIP = {"experiences.yaml", "combined-arms-ai.yaml"}
MF = "ra2|modern-factions/"
DOCTRINE_MODULES = {"BaseBuilderBotModule": "DoctrineBaseBuilderBotModule",
                    "UnitBuilderBotModule": "DoctrineUnitBuilderBotModule",
                    "SquadManagerBotModule": "DoctrineSquadManagerBotModule"}


def fork_file(fork: Path, path: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(fork), "show", f"{FORK_COMMIT}:{path}"])


def write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="\n")


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise ValueError(f"Expected one anchor in {path}: {old!r}")
    write(path, text.replace(old, new, 1))


def registered_factions(manifest: Path) -> list[str]:
    text = manifest.read_text(encoding="utf-8")
    return [c for c in FACTIONS if f"\t{MF}{c}.yaml\n" in text]


def faction_files(src: Path, country: str) -> list[Path]:
    files = [src / f"{country}.yaml"] + sorted(src.glob(f"{country}-*.yaml")) + sorted(src.glob(f"{country}-*.ftl"))
    return [f for f in files if f.is_file()]


def combined_replacements(modern: Path, countries: list[str]) -> str:
    prerequisites: dict[str, list[list[str]]] = {}
    for country in countries:
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


def strip_additional_bot_types(path: Path) -> dict[tuple[str, str], list[str]]:
    """Remove the fork-only Additional{Defense,AirUnits,NavalUnits}Types from one faction AI file."""
    extra: dict[tuple[str, str], list[str]] = {}
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
    write(path, "\n".join(out))
    return extra


def fold_additional_bot_types(mod: Path, dest: Path, countries: list[str]) -> None:
    """Fold the fork-only Additional*Types of `countries` into the bot type lists of bot-types.yaml.

    The base lists are the current bot-types.yaml (earlier rounds) or else the upstream rules/ai.yaml.
    Global merging is safe: bots only build what their prerequisites allow, and squad typing of
    units a bot can never own has no effect.
    """
    ai_rules = (mod / "rules/ai.yaml").read_text(encoding="utf-8")
    doctrine = "\tDoctrineBaseBuilderBotModule@" in ai_rules  # --doctrine-ai already applied

    def canonical(module: str) -> str:
        trait, _, name = module.partition("@")
        return f"{DOCTRINE_MODULES.get(trait, trait) if doctrine else trait}@{name}"

    extra: dict[tuple[str, str], list[str]] = {}
    for country in countries:
        for (module, field), values in strip_additional_bot_types(dest / f"{country}-ai.yaml").items():
            extra.setdefault((canonical(module), field), []).extend(values)

    bot_types = dest / "bot-types.yaml"
    current: dict[str, dict[str, list[str]]] = {}
    if bot_types.exists():
        module = None
        for line in bot_types.read_text(encoding="utf-8").splitlines():
            if m := re.match(r"^\t([A-Za-z]+@[\w-]+):$", line):
                module = m.group(1)
            elif m := re.match(r"^\t\t(\w+): (.*)$", line):
                current.setdefault(module, {})[m.group(1)] = [v.strip() for v in m.group(2).split(",")]

    for (module, field), values in sorted(extra.items()):
        if field not in current.get(module, {}):
            block = re.search(rf"^\t{re.escape(module)}:\n((?:\t\t.*\n)+)", ai_rules, re.MULTILINE)
            base = re.search(rf"^\t\t{field}: (.*)$", block.group(1), re.MULTILINE) if block else None
            if base is None:
                raise ValueError(f"rules/ai.yaml has no {module}.{field} to extend")
            current.setdefault(module, {})[field] = [v.strip() for v in base.group(1).split(",")]
        listed = current[module][field]
        listed.extend(v for v in dict.fromkeys(values) if v not in listed)

    write(bot_types, "# Generated by tools/port-modern-factions.py: upstream bot type lists plus the modern factions' types.\nPlayer:\n"
          + "".join(f"\t{m}:\n" + "".join(f"\t\t{f}: {', '.join(v)}\n" for f, v in fields.items())
                    for m, fields in sorted(current.items())))


def copy_faction(src: Path, dest: Path, country: str, fork: Path) -> tuple[int, set[str]]:
    """Copy one faction's rules, messages, art and every asset its files reference."""
    copied = 0
    for path in faction_files(src, country):
        shutil.copy2(path, dest / path.name)
        copied += 1
    art = src / f"{country}-art"
    if art.is_dir():
        shutil.copytree(art, dest / art.name, ignore=shutil.ignore_patterns("source-art-review.png"))

    references: set[str] = set()
    for path in faction_files(dest, country):
        references.update(re.findall(r"ra2\|modern-factions/([\w./-]+)", path.read_text(encoding="utf-8")))
    audio = set()
    for ref in sorted(references):
        if ref.startswith("audio/"):
            audio.add(Path(ref).stem)
        elif ref.startswith("icons/"):
            (dest / "icons").mkdir(exist_ok=True)
            shutil.copy2(src / ref, dest / ref)
        elif ref.startswith("voxels/") and not ref.endswith(".pal"):
            for suffix in (".vxl", ".hva"):
                shutil.copy2(src / (ref + suffix), dest / (ref + suffix))
        elif not (dest / ref).exists():
            raise ValueError(f"{country}: unresolved reference ra2|modern-factions/{ref}")
    return copied, audio


def copy_audio(src: Path, dest: Path, fork: Path, names: set[str]) -> None:
    """Voice lines and SFX: the source overlay's own audio first, else the fork's generated bits."""
    (dest / "audio").mkdir(exist_ok=True)
    for name in sorted(names):
        target = dest / "audio" / f"{name}.wav"
        if target.exists():
            continue
        own = src / "audio" / f"{name}.wav"
        if own.exists():
            shutil.copy2(own, target)
        elif name.startswith("naval-"):
            target.write_bytes(fork_file(fork, f"mods/ra/bits/naval/{name.removeprefix('naval-')}.wav"))
        else:
            target.write_bytes(fork_file(fork, f"mods/ra/bits/{name}.wav"))


def extend_random_pools(mod: Path, dest: Path, countries: list[str]) -> None:
    # Faction.RandomFactionMemberOf is a fork-only field: drop it, extend the upstream pools instead.
    for country in countries:
        path = dest / f"{country}.yaml"
        text, n = re.subn(r"^\t\tRandomFactionMemberOf: .*\n", "", path.read_text(encoding="utf-8"), flags=re.MULTILINE)
        if n != 1:
            raise ValueError(f"{path}: expected one RandomFactionMemberOf")
        write(path, text)
    world = mod / "rules/world.yaml"
    text = world.read_text(encoding="utf-8")
    for pool in STOCK_POOLS:
        m = re.search(rf"^\t\tInternalName: {pool}\n\t\tRandomFactionMembers: (.*)\n", text, re.MULTILINE)
        members = [v.strip() for v in m.group(1).split(",")]
        members += [c for c in countries if FACTIONS[c][1] == pool and c not in members]
        text = text[:m.start(1)] + ", ".join(members) + text[m.end(1):]
    write(world, text)


def add_faction_prerequisites(dest: Path, countries: list[str]) -> None:
    """common.yaml grants faction.X for every modern country (the source adds one block per pack)."""
    path = dest / "common.yaml"
    text = path.read_text(encoding="utf-8")
    blocks = "".join(f"\tProvidesPrerequisite@{c}:\n\t\tPrerequisite: faction.{c}\n\t\tFactions: {c}\n"
                     for c in countries if f"ProvidesPrerequisite@{c}:" not in text)
    matches = list(re.finditer(r"^\tProvidesPrerequisite@\w+:\n(?:\t\t.*\n)+", text, re.MULTILINE))
    write(path, text[:matches[-1].end()] + blocks + text[matches[-1].end():])


def extend_flags(mod: Path, fork: Path, countries: list[str]) -> None:
    """Lobby flags: extend the RA2 button atlas (prepare-ra2.py:extend_flag_atlas)."""
    buttons = mod / "uibits/buttons.png"
    chrome = mod / "chrome.yaml"
    text = chrome.read_text(encoding="utf-8")
    flags = Image.open(io.BytesIO(fork_file(fork, "mods/ra/uibits/glyphs-redsea.png")))
    width, height = FLAG_SIZE
    existing = [(int(x), int(y)) for c, x, y in re.findall(r"^\t\t(\w+): (\d+), (\d+), 30, 15$", text, re.MULTILINE) if c in FACTIONS]
    with Image.open(buttons) as original:
        if existing:  # a previous round appended a flag row at the bottom of the atlas
            row = existing[0][1]
            x0 = max(x for x, _ in existing) + width
            atlas = original.convert("RGBA")
        else:
            row, x0 = original.height, 0
            required = (max(original.width, len(countries) * width), original.height + height)
            atlas = Image.new("RGBA", tuple(1 << (size - 1).bit_length() for size in required))
            atlas.paste(original.convert("RGBA"), (0, 0))
        if x0 + len(countries) * width > atlas.width or row + height > atlas.height:
            raise ValueError("flag row of buttons.png is full")
        regions = []
        for i, country in enumerate(countries):
            x, y = FACTIONS[country][2]
            atlas.paste(flags.crop((x, y, x + width, y + height)).convert("RGBA"), (x0 + width * i, row))
            regions.append(f"\t\t{country}: {x0 + width * i}, {row}, {width}, {height}\n")
    atlas.save(buttons)
    anchor = "flags:\n\tImage: buttons.png\n\tRegions:\n"
    last = re.search(r"(?:^\t\t(?:" + "|".join(FACTIONS) + r"): \d+, \d+, 30, 15\n)+", text, re.MULTILINE)
    if last:
        write(chrome, text[:last.end()] + "".join(regions) + text[last.end():])
    else:
        replace_once(chrome, anchor, anchor + "".join(regions))


def register_in_manifest(manifest: Path, files: dict[str, list[str]]) -> None:
    text = manifest.read_text(encoding="utf-8")
    for section, names in files.items():
        m = re.search(rf"^{section}:\n((?:\t.*\n)+)", text, re.MULTILINE)
        if m is None:
            raise ValueError(f"No {section} section")
        new = [n for n in names if f"\t{MF}{n}\n" not in m.group(1)]
        text = text[:m.end()] + "".join(f"\t{MF}{n}\n" for n in new) + text[m.end():]
    write(manifest, text)


def adopt_doctrine_ai(mod: Path, src: Path) -> None:
    """Switch every bot profile to the role-aware OpenRA.Mods.RTSAI modules (the fork's combined-arms AI)."""
    dest = mod / "modern-factions"
    pattern = re.compile(r"^(\t-?)(" + "|".join(DOCTRINE_MODULES) + r")@", re.MULTILINE)
    for path in [mod / "rules/ai.yaml"] + sorted(dest.glob("*.yaml")):
        text = path.read_text(encoding="utf-8")
        new = pattern.sub(lambda m: m.group(1) + DOCTRINE_MODULES[m.group(2)] + "@", text)
        if new != text:
            write(path, new)

    # InitialBuildOrder (deterministic openings) was dropped in round A; restore it from the source.
    source_orders = re.findall(r"^\tBaseBuilderBotModule@(\w+):\n\t\tInitialBuildOrder: (.*)$",
                               (src / "aircraft-ai.yaml").read_text(encoding="utf-8"), re.MULTILINE)
    aircraft_ai = dest / "aircraft-ai.yaml"
    text = aircraft_ai.read_text(encoding="utf-8")
    for bot, order in source_orders:
        head = f"\tDoctrineBaseBuilderBotModule@{bot}:\n"
        if head + "\t\tInitialBuildOrder:" not in text:
            text = text.replace(head, head + f"\t\tInitialBuildOrder: {order}\n", 1)
    write(aircraft_ai, text)

    # Role shares and stock-actor role tags. The Experience-only formation-size parameter is not
    # ported: bots keep their per-profile SquadSize (rush 3 ... turtle 12), scaled per faction by
    # BotDoctrine.SquadSizeModifier (doctrines.yaml).
    text = (src / "combined-arms-ai.yaml").read_text(encoding="utf-8")
    text = re.sub(r"^\tSquadManagerBotModule@\w+:\n(?:\t\tExperience\w+: .*\n)+", "", text, flags=re.MULTILINE)
    text = pattern.sub(lambda m: m.group(1) + DOCTRINE_MODULES[m.group(2)] + "@", text)
    if "Experience" in text:
        raise ValueError("combined-arms-ai.yaml still references the Experience system")
    write(dest / "combined-arms-ai.yaml", "# Ported by tools/port-modern-factions.py --doctrine-ai from the fork's ra2-combined-arms-ai.\n" + text)
    register_in_manifest(mod / "mod.yaml", {"Rules": ["combined-arms-ai.yaml", "doctrines.yaml"]})


def source_state(product: Path) -> str:
    git = ["git", "-C", str(product)]
    head = subprocess.check_output(git + ["rev-parse", "--short", "HEAD"], text=True).strip()
    branch = subprocess.check_output(git + ["rev-parse", "--abbrev-ref", "HEAD"], text=True).strip()
    dirty = subprocess.check_output(git + ["status", "--short", "--", "apps/installer/ra2/modern-factions"], text=True)
    return f"{branch}@{head}" + ("".join(f"\n  working tree: {line}" for line in dirty.splitlines()) or " (clean)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--product", type=Path, default=ROOT.parent / "OpenRA-AI")
    parser.add_argument("--fork", type=Path, default=ROOT.parent / "OpenRA")
    parser.add_argument("--factions", default=",".join(FACTIONS), help="comma-separated internal names")
    parser.add_argument("--doctrine-ai", action="store_true", help="use the role-aware OpenRA.Mods.RTSAI bot modules")
    args = parser.parse_args()

    src = args.product / "apps/installer/ra2/modern-factions"
    mod = ROOT / "mods/rtsai"
    dest = mod / "modern-factions"
    manifest = mod / "mod.yaml"
    print(f"Source: {source_state(args.product)}")

    if not dest.exists():  # first round: shared files come with it
        shutil.copytree(src, dest, ignore=shutil.ignore_patterns(*SKIP, "previews", "source-art-review.png", "audio"))
        # Upstream carrier declares RevealsShroud twice; the Türkiye exclusion merge makes it ambiguous.
        replace_once(mod / "rules/allied-naval.yaml",
                     "\tMobile:\n\t\tTurnSpeed: 4\n\t\tSpeed: 60\n\tRevealsShroud:\n\t\tRange: 7c0\n\tAttackFrontal:",
                     "\tMobile:\n\t\tTurnSpeed: 4\n\t\tSpeed: 60\n\tAttackFrontal:")
        shared_rules = ["common.yaml", "aircraft-ai.yaml", "shared-replacements.yaml", "bot-types.yaml"]
        register_in_manifest(manifest, {"Rules": shared_rules, "ModelSequences": ["voxels.yaml"],
                                        "Weapons": ["weapons.yaml"], "FluentMessages": ["messages.ftl"]})
        # Round A: BaseBuilderBotModule.InitialBuildOrder was fork-only until --doctrine-ai.
        aircraft_ai = dest / "aircraft-ai.yaml"
        write(aircraft_ai, re.sub(r"^\t\tInitialBuildOrder: .*\n", "", aircraft_ai.read_text(encoding="utf-8"), flags=re.MULTILINE))

    present = registered_factions(manifest)
    new = [c for c in args.factions.split(",") if c and c not in present]
    unknown = [c for c in new if c not in FACTIONS]
    if unknown:
        raise SystemExit(f"Unknown factions: {unknown}")

    audio: set[str] = set()
    for country in new:
        copied, names = copy_faction(src, dest, country, args.fork)
        audio |= names
        print(f"{country}: {copied} rule/message files")
    copy_audio(src, dest, args.fork, audio)
    for manifest_name in ("red-sea-voxel-manifest.json",):
        if (src / manifest_name).exists() and not (dest / manifest_name).exists():
            shutil.copy2(src / manifest_name, dest / manifest_name)

    if new:
        extend_random_pools(mod, dest, new)
        add_faction_prerequisites(dest, new)
        countries = present + new
        write(dest / "shared-replacements.yaml", combined_replacements(dest, countries))
        fold_additional_bot_types(mod, dest, new)
        extend_flags(mod, args.fork, new)
        replace_once(mod / "metrics.yaml", "Metrics:\n",
                     "Metrics:\n" + "".join(f"\tFactionSuffix-{c}: {FACTIONS[c][0].lower()}\n" for c in new))
        files: dict[str, list[str]] = {"Rules": [], "Sequences": [], "ModelSequences": [], "Voices": [],
                                       "Weapons": [], "FluentMessages": []}
        for c in new:
            files["Rules"] += [f"{c}.yaml", f"{c}-roster.yaml", f"{c}-ai.yaml", f"{c}-audio.yaml"]
            if (dest / f"{c}-roles.yaml").exists():
                files["Rules"].append(f"{c}-roles.yaml")
            files["Sequences"] += [f"{c}-sequences.yaml", f"{c}-roster-sequences.yaml"]
            files["ModelSequences"].append(f"{c}-voxels.yaml")
            files["Voices"].append(f"{c}-voices.yaml")
            files["Weapons"].append(f"{c}-weapons.yaml")
            files["FluentMessages"].append(f"{c}-messages.ftl")
        register_in_manifest(manifest, files)

    if args.doctrine_ai:
        adopt_doctrine_ai(mod, src)
    print(f"Ported {len(new)} factions ({', '.join(new) or 'none'}), {len(audio)} audio references into {dest}")


if __name__ == "__main__":
    main()
