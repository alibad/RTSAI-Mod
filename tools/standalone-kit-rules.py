#!/usr/bin/env python3
"""Wire the Phase 3 base kit (mods/rtsai/standalone/base, by the art agent) into the standalone game's rules.

Writes mods/rtsai/standalone/base-kit.yaml, a standalone-only rules overlay (the classic add-on keeps the original
buildings with the player's own RA2 files):
  - the kit palette (kitbase.pal) and its player-colour remap;
  - each of the 22 stock buildings the modern factions use renders its kit role, painted per faction;
  - render traits that name sequences the kit does not have are swapped or removed, as agreed with the art agent
    (construction yard crane = full-body "build" animation, no air-factory roof, no airfield "idle-mid", the EW array
    plays its full-body "active" when its power fires);
  - the Soviet-side power plant, barracks, service depot and tech centre take the Allied footprints the kit is
    drawn for (Building, HitShape, exits and rally point copied from the Allied counterparts);
  - the 8 stock buildings the kit does not replace leave the modern rosters (owner decision, 7 October 2026);
  - the two superweapon slots get standalone names (standalone/standalone.ftl);
  - economy compensation for the cuts (coordinator, 7 October 2026): the Soviet side gets a heavy power plant (the
    reactor's 2000 power for 1000 credits, kit role `hpwr`), the Allied side a refinery upgrade (a plug placed on a
    refinery: +25% on the ore it processes, the ore purifier's bonus). Until the kit ships `hpwr` and the purifier
    pieces, interim images reuse the kit's power-plant and refinery art with badge icons drawn here
    (standalone/art/econ/, standalone/kit-extra-sequences.yaml);
  - the shared vehicles (standalone/units, kit v2): MCV, harvester, AA track, amphibious APC and landing craft render
    the kit's 32-facing sprites instead of the stock voxels, painted per faction; their images inherit the stock
    effect sequences their traits play (mind control, muzzle, harvest, chrono-miner warps).

usage: python tools/standalone-kit-rules.py
"""
from __future__ import annotations

import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "mods" / "rtsai" / "standalone" / "base-kit.yaml"
KIT = ROOT / "mods" / "rtsai" / "standalone" / "base"
UNITS_DIR = ROOT / "mods" / "rtsai" / "standalone" / "units"
EXTRA_SEQ = ROOT / "mods" / "rtsai" / "standalone" / "kit-extra-sequences.yaml"
ECON_ART = ROOT / "mods" / "rtsai" / "standalone" / "art" / "econ"
FONT = ROOT / "engine" / "mods" / "common" / "FreeSansBold.ttf"
FACTIONS = ["china", "iran", "turkey", "saudi", "israel", "yemen", "hezbollah"]

ROLE = {
    "gacnst": "cnst", "nacnst": "cnst", "gapowr": "powr", "napowr": "powr", "garefn": "refn", "narefn": "refn",
    "gapile": "barr", "nahand": "barr", "gaweap": "weap", "naweap": "weap", "naradr": "radr", "gaairc": "airf",
    "gayard": "yard", "nayard": "yard", "gadept": "dept", "nadept": "dept", "gatech": "tech", "natech": "tech",
    "gacsph": "sw1", "nairon": "sw2", "gawall": "wall", "nawall": "wall",
    "nanrct": "hpwr",       # the heavy power plant (economy compensation)
}

# Render traits to adjust per actor (raw MiniYaml, tab-indented under the actor).
EXTRA = {
    "gacnst": "\t-WithBuildingPlacedOverlay:\n\tWithBuildingPlacedAnimation:\n",
    "nacnst": "\t-WithIdleOverlay@normal:\n",
    "gaweap": "\t-WithIdleOverlay@air-open:\n\t-WithIdleOverlay@air-inside:\n",
    "naweap": "\t-WithIdleOverlay@air-open:\n\t-WithIdleOverlay@air-inside:\n",
    "gaairc": "\t-WithIdleOverlay@mid:\n",
    "nahand": "\tWithIdleOverlay@flag:\n\t\tSequence: idle-flag\n",
    "natech": "\tWithIdleOverlay@lights:\n\t\tSequence: idle-lights\n",
    # the EW array turns and its panels light up when its power fires (full-body "active", then back to idle)
    "nairon": "\tWithSupportPowerActivationAnimation:\n\t\tSequence: active\n",
}

# Soviet-side footprints -> the Allied ones the kit is drawn for (values from the resolved Allied rules).
FOOTPRINT = {
    "napowr": "\tBuilding:\n\t\tDimensions: 2,2\n\t\tFootprint: xx xx\n"
              "\tHitShape:\n\t\tTopLeft: -1024, -1024\n\t\tBottomRight: 1024, 1024\n",
    "nahand": "\tBuilding:\n\t\tDimensions: 3,2\n\t\tFootprint: xxx xxx\n"
              "\tHitShape:\n\t\tTopLeft: -1536, -1024\n\t\tBottomRight: 1536, 1024\n"
              "\tRallyPoint:\n\t\tPath: 2,3\n"
              "\tExit@0_2:\n\t\tSpawnOffset: -900,220,0\n\t\tExitCell: 0, 2\n"
              "\tExit@0_n1:\n\t\tSpawnOffset: 170,-810,0\n\t\tExitCell: 0, -1\n"
              "\tExit@2_2:\n\t\tSpawnOffset: -170,810,0\n\t\tExitCell: 2, 2\n"
              "\tExit@2_n1:\n\t\tSpawnOffset: 900,-220,0\n\t\tExitCell: 2, -1\n"
              + "".join(f"\t-Exit@{e}:\n" for e in ["1_2", "1_n1", "2_0", "2_1", "n1_0", "n1_1", "n1_2", "n1_n1"]),
    "nadept": "\tBuilding:\n\t\tDimensions: 3,3\n\t\tFootprint: x== x== x==\n"
              "\tHitShape:\n\t\tTopLeft: -1536, -1536\n\t\tBottomRight: 1536, 1536\n",
    "natech": "\tBuilding:\n\t\tDimensions: 3,2\n\t\tFootprint: xx xx xx\n"
              "\tHitShape:\n\t\tTopLeft: -1536, -1024\n\t\tBottomRight: 1536, 1024\n",
}

# Not in the kit, so not in the standalone game (they stay in the classic add-on). The reactor's role returns as the
# heavy power plant and the purifier's as the refinery upgrade (economy() below).
CUT = {
    "gaorep": "Ore Purifier: +25% ore income (the refinery upgrade gapurifier replaces it)",
    "gagap": "Gap Generator: shroud over a 10-cell radius",
    "gaspysat": "Spy Satellite: reveals the whole map",
    "gaweat": "Weather Control: Allied-side damage superweapon (lightning storm, 15000-tick charge)",
    "napsis": "Psychic Sensor: detects cloaked units within 6 cells",
    "naclon": "Cloning Vats: a free copy of every infantry unit produced",
    "namisl": "Nuclear Missile Silo: Soviet-side damage superweapon (15000-tick charge)",
}

TEXT = {
    "gacsph": ("Tooltip", "ChronoshiftPower@chronoshift", "sw1"),
    "nairon": ("Tooltip", "GrantExternalConditionPower@IRONCURTAIN", "sw2"),
}

# Shared vehicles on the kit (standalone/units): actor -> kit image role, voxel render traits to switch off, extra
# rules. Conditional voxel traits are switched off (RequiresCondition: false) rather than removed, because other
# actors inherit these and remove them themselves (r2kunlun from lcrf, amcv.colorpicker from amcv); RenderVoxels
# stays and draws nothing. WithVoxelUnloadBody is not conditional and nothing inherits the harvesters: removed.
VOXEL_OFF = "false"   # a constant-false condition: the voxel trait never enables
UNITS = {
    "amcv": ("mcv", ["WithVoxelBody"], [], ""),
    "smcv": ("mcv", ["WithVoxelBody"], [], ""),
    "cmin": ("harv", [], ["WithVoxelUnloadBody"], ""),
    "harv": ("harv", ["WithVoxelTurret"], ["WithVoxelUnloadBody"], ""),
    "htk": ("htk", ["WithVoxelTurret", "WithVoxelBody"], [],
            "\tWithSpriteTurret:\n\tTurreted:\n\t\tOffset: 0,0,582\n"
            "\tArmament@primary:\n\t\tLocalOffset: 489,-244,212, 489,244,212\n"
            "\tArmament@secondary:\n\t\tLocalOffset: 489,-244,212, 489,244,212\n"),
    "sapc": ("sapc", ["WithVoxelBody"], [], ""),
    "lcrf": ("lcrf", ["WithVoxelBody"], [], ""),
}
# Actors that inherit a converted unit but keep their own look.
UNIT_INHERITORS = {
    # China's Kunlun landing ship inherits lcrf and renders its own prerendered sprite.
    "r2kunlun": "\tRenderSprites:\n\t\tImage: r2kunlun\n\t\tFactionImages:\n" + "".join(
        f"\t\t\t{f}: r2kunlun\n" for f in ["china", "iran", "turkey", "saudi", "israel", "yemen", "hezbollah"]),
    # The lobby colour picker's preview: the kit MCV on the kit palette, remapped live to the picked colour.
    "amcv.colorpicker": "\tRenderSprites:\n\t\tPalette: kitcolorpicker\n",
}
# The stock images whose effect sequences each kit unit image inherits (all name their own files).
UNIT_SEQUENCE_LINKS = {"mcv": ["amcv"], "harv": ["cmin", "harv"], "htk": ["htk"], "sapc": ["sapc"], "lcrf": ["lcrf"]}


def units() -> str:
    out = ["# Shared vehicles on the kit (standalone/units): sprites instead of the stock voxels.\n"]
    done = set()
    for actor, (role, off, drop, extra) in UNITS.items():
        if not kit_has(f"{role}-china", units=True):
            continue
        done.add(actor)
        out.append(f"{actor}:\n" + "".join(f"\t{t}:\n\t\tRequiresCondition: {VOXEL_OFF}\n" for t in off)
                   + "".join(f"\t-{t}:\n" for t in drop)
                   + f"\tRenderSprites:\n\t\tImage: unit-{role}-china\n\t\tPlayerPalette: kitplayer\n\t\tFactionImages:\n"
                   + "".join(f"\t\t\t{f}: unit-{role}-{f}\n" for f in FACTIONS)
                   + "\tBodyOrientation:\n\t\tQuantizedFacings: 32\n\tWithFacingSpriteBody:\n" + extra + "\n")
    parents = {"r2kunlun": "lcrf", "amcv.colorpicker": "amcv"}
    for actor, text in UNIT_INHERITORS.items():
        if parents[actor] in done:
            out.append(f"{actor}:\n{text}\n")
    return "".join(out)


# Economy compensation. The heavy plant keeps the reactor's numbers (Power 2000, Cost 1000, needs the tech centre) on
# the kit footprint; it dies like any building (the reactor's nuclear blast was EA art and is not the kit's look).
HPWR_FOOTPRINT = {True: ("3,3", "xxx xxx xxx", "-1536, -1536", "1536, 1536"),     # the kit's hpwr (3x3)
                  False: ("2,2", "xx xx", "-1024, -1024", "1024, 1024")}           # interim: powr art
PURIFIER_COST = 1000         # per refinery; the purifier was 2500 for every refinery
PURIFIER_MODIFIER = 125      # percent of the ore value this refinery pays out
PURIFIER_POWER = -50
BOTS = ("normal", "medium", "rush", "turtle", "naval")


def kit_has(image: str, sequence: str | None = None, units: bool = False) -> bool:
    path = UNITS_DIR / "units-sequences.yaml" if units else KIT / "kit-sequences.yaml"
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    block = re.search(rf"(?ms)^{re.escape(image)}:\n(.*?)(?=^\S|\Z)", text)
    if block is None:
        return False
    return sequence is None or re.search(rf"(?m)^\t{re.escape(sequence)}:", block[1]) is not None


def badge_icon(src: Path, dst: Path, label: str, colour):
    """A kit cameo with a corner badge: the interim icon for an economy piece the kit has not drawn yet."""
    im = Image.open(src).convert("RGB")
    d = ImageDraw.Draw(im)
    font = ImageFont.truetype(str(FONT), 11)
    w = d.textlength(label, font=font)
    x1, y1 = im.width - 2, im.height - 2
    x0, y0 = x1 - int(w) - 6, y1 - 14
    d.rounded_rectangle((x0, y0, x1, y1), radius=3, fill=(12, 16, 22), outline=colour)
    d.text((x0 + 3, y0 + 1), label, font=font, fill=colour)
    dst.parent.mkdir(parents=True, exist_ok=True)
    im.save(dst, optimize=True)


EFFECTS_DIR = ROOT / "mods" / "rtsai" / "standalone" / "effects"
SEQUENCE_SOURCES = [ROOT / "mods" / "rtsai" / "sequences", ROOT / "mods" / "rtsai" / "modern-factions"]


def effect_png_overrides() -> str:
    """The effects batch delivers some images as palette-free PNG sheets under the stock stems (parach.png for
    parach.shp...). Every sequence node that names <stem>.shp gets the same path with <stem>.png. SHPs delivered under
    the stock names need nothing: the effects folder is mounted after the placeholders."""
    if not EFFECTS_DIR.exists():
        return ""
    stems = {p.stem for p in EFFECTS_DIR.glob("*.png")}
    tree = {}                                        # nested keys -> {..., "Filename": "x.png"}
    files = [f for d in SEQUENCE_SOURCES for f in sorted(d.glob("*.yaml")) if "sequences" in f.name or d.name == "sequences"]
    for f in files:
        path = []                                    # (indent, key) stack
        for line in f.read_text(encoding="utf-8").replace("\r\n", "\n").split("\n"):
            body = line.split("#", 1)[0].rstrip()
            if not body.strip():
                continue
            indent = len(body) - len(body.lstrip("\t"))
            key, _, value = body.strip().partition(":")
            while path and path[-1][0] >= indent:
                path.pop()
            path.append((indent, key))
            m = re.fullmatch(r"(\S+)\.shp", value.strip())
            if key == "Filename" and m and m[1] in stems:
                node = tree
                for _, k in path[:-1]:
                    node = node.setdefault(k, {})
                node["Filename"] = f"{m[1]}.png"
    if not tree:
        return ""

    def emit(node, depth):
        return "".join("\t" * depth + (f"{k}: {v}\n" if isinstance(v, str) else f"{k}:\n" + emit(v, depth + 1))
                       for k, v in node.items())

    return ("# 3. Effects delivered as PNG sheets under the stock stems (standalone/effects).\n"
            + "".join(f"{k}:\n{emit(v, 1)}\n" for k, v in tree.items()))


def kit_extra_sequences() -> str:
    """kit-extra-sequences.yaml: the stock effect sequences the shared units' traits play (mind-control overlay,
    muzzle flash, harvest dust, chrono-miner warps) linked into the kit unit images, plus interim images for the
    economy pieces the kit has not drawn yet."""
    out = ["# GENERATED by tools/standalone-kit-rules.py.\n"
           "# 1. The kit unit images (standalone/units) inherit the stock images' effect sequences their traits play.\n"
           "# 2. Interim images for the economy pieces the base kit has not drawn yet (heavy power plant, refinery\n"
           "#    upgrade); each falls away when the kit ships its own.\n\n"]
    for role, stock in UNIT_SEQUENCE_LINKS.items():
        for f in FACTIONS:
            if kit_has(f"{role}-{f}", units=True):
                # a new image: the stock effects first, the kit image last, so the kit's own sequences (icon) win
                out.append(f"unit-{role}-{f}:\n" + "".join(f"\tInherits@{s}: {s}\n" for s in stock)
                           + f"\tInherits@kit: {role}-{f}\n\n")
    written = set()
    for f in FACTIONS:
        if not kit_has(f"hpwr-{f}"):
            written.add(f"hpwr-{f}icon.png")
            badge_icon(KIT / f"powr-{f}icon.png", ECON_ART / f"hpwr-{f}icon.png", "HEAVY", (255, 196, 64))
            out.append(f"hpwr-{f}:\n\tInherits: powr-{f}\n\ticon:\n\t\tFilename: ra2|standalone/art/econ/hpwr-{f}icon.png\n"
                       "\t\tOffset: 0, 0\n\n")
        if kit_has(f"purifier-{f}"):
            continue
        if (KIT / f"purifier-{f}icon.png").exists():      # the kit's icon without an image entry: name it here
            out.append(f"purifier-{f}:\n\ticon:\n\t\tFilename: purifier-{f}icon.png\n\t\tOffset: 0, 0\n\n")
        else:
            written.add(f"purifier-{f}icon.png")
            badge_icon(KIT / f"refn-{f}icon.png", ECON_ART / f"purifier-{f}icon.png", "+25%", (79, 195, 208))
            out.append(f"purifier-{f}:\n\ticon:\n\t\tFilename: ra2|standalone/art/econ/purifier-{f}icon.png\n"
                       "\t\tOffset: 0, 0\n\n")
    if ECON_ART.exists():                               # interim icons the kit has since replaced
        for stale in [p for p in ECON_ART.iterdir() if p.name not in written]:
            stale.unlink()
        if not any(ECON_ART.iterdir()):
            ECON_ART.rmdir()
    out.append(effect_png_overrides())
    return "".join(out).rstrip("\n") + "\n"


def economy_kit_blocks() -> dict:
    """Economy compensation on kit buildings, merged into their kit blocks: the reactor's rules as the heavy power
    plant, and the refinery's purifier socket."""
    dims, foot, tl, br = HPWR_FOOTPRINT[kit_has("hpwr-china")]
    overlay = ""
    if kit_has("refn-china", "idle-purifier"):
        overlay = "\tWithIdleOverlay@purifier:\n\t\tSequence: idle-purifier\n\t\tRequiresCondition: purified && !build-incomplete\n"
    return {
        "nanrct": "\tBuildable:\n\t\tDescription: standalone-hpwr-description\n\tTooltip:\n\t\tName: standalone-hpwr-name\n"
                  f"\tBuilding:\n\t\tDimensions: {dims}\n\t\tFootprint: {foot}\n"
                  f"\tHitShape:\n\t\tTopLeft: {tl}\n\t\tBottomRight: {br}\n"
                  "\tFireWarheadsOnDeath:\n\t\tType: Footprint\n\t\tWeapon: BuildingExplode\n\t\tEmptyWeapon: BuildingExplode\n",
        "garefn": "\tPluggable@purifier:\n\t\tOffset: 1,1\n\t\tConditions:\n\t\t\tpurifier: purified\n"
                  "\t\tRequirements:\n\t\t\tpurifier: !build-incomplete && !purified\n"
                  f"\tResourceValueMultiplier@purifier:\n\t\tModifier: {PURIFIER_MODIFIER}\n\t\tRequiresCondition: purified\n"
                  f"\tPower@purifier:\n\t\tAmount: {PURIFIER_POWER}\n\t\tRequiresCondition: purified\n" + overlay,
    }


def economy() -> str:
    out = ["# Economy compensation (coordinator, 7 October 2026): the refinery upgrade that replaces the ore purifier.\n"
           "# The heavy power plant is nanrct above; the refinery's socket is in garefn above.\n"]
    out.append("gapurifier:\n\tInteractable:\n\tBuilding:\n\tFootprintPlaceBuildingPreview:\n\tKillsSelf:\n\t\tRemoveInstead: true\n"
               "\tRenderSprites:\n\t\tImage: purifier-china\n\t\tFactionImages:\n"
               + "".join(f"\t\t\t{f}: purifier-{f}\n" for f in FACTIONS)
               + f"\tValued:\n\t\tCost: {PURIFIER_COST}\n\tTooltip:\n\t\tName: standalone-purifier-name\n"
               "\tBuildable:\n\t\tQueue: Building\n\t\tBuildPaletteOrder: 100\n\t\tPrerequisites: garefn, gatech, ~structures.allies\n"
               "\t\tDescription: standalone-purifier-description\n\tPlug:\n\t\tType: purifier\n\n")
    # bots upgrade refineries once the tech centre is up (the base builder builds a plug only while a host accepts it)
    out.append("Player:\n" + "".join(f"\tDoctrineBaseBuilderBotModule@{b}:\n\t\tBuildingFractions:\n\t\t\tgapurifier: 4\n"
                                       for b in BOTS) + "\n")
    return "".join(out)


def build() -> str:
    out = ["# GENERATED by tools/standalone-kit-rules.py: the base kit in the standalone game's rules. Standalone only.\n\n"]
    out.append("^Palettes:\n\tPaletteFromFile@kitbase:\n\t\tName: kitbase\n\t\tFilename: ra2|standalone/base/kitbase.pal\n"
               "\t\tShadowIndex: 1\n\tPlayerColorPalette@kitbase:\n\t\tBasePalette: kitbase\n\t\tBaseName: kitplayer\n"
               "\t\tRemapIndex: " + ", ".join(str(i) for i in range(16, 32)) + "\n"
               "\tColorPickerPalette@kitcolorpicker:\n\t\tName: kitcolorpicker\n\t\tBasePalette: kitbase\n"
               "\t\tRemapIndex: " + ", ".join(str(i) for i in range(16, 32)) + "\n\t\tAllowModifiers: false\n\n")
    econ = economy_kit_blocks()
    for actor, role in ROLE.items():
        block = [f"{actor}:\n\tRenderSprites:\n\t\tImage: {role}-china\n\t\tPlayerPalette: kitplayer\n\t\tFactionImages:\n"]
        block += [f"\t\t\t{f}: {role}-{f}\n" for f in FACTIONS]
        block.append(EXTRA.get(actor, ""))
        block.append(FOOTPRINT.get(actor, ""))
        block.append(econ.get(actor, ""))
        if actor in TEXT:
            tip, power, key = TEXT[actor]
            block.append(f"\t{tip}:\n\t\tName: standalone-{key}-name\n\tBuildable:\n\t\tDescription: standalone-{key}-description\n"
                         f"\t{power}:\n\t\tName: standalone-{key}-power-name\n\t\tDescription: standalone-{key}-power-description\n")
        out.append("".join(block) + "\n")
    out.append(units())
    out.append(economy())
    out.append("# Not part of the kit: out of the modern rosters in the standalone game (classic keeps them).\n")
    for actor, role in CUT.items():
        out.append(f"{actor}: # {role}\n\tBuildable:\n\t\tPrerequisites: ~disabled\n\n")
    text = "".join(out).rstrip("\n") + "\n"
    # HitShape's rectangle corners live under its Type (the shape), not on the trait itself
    text = re.sub(r"\tHitShape:\n\t\tTopLeft: ([^\n]+)\n\t\tBottomRight: ([^\n]+)\n",
                  r"\tHitShape:\n\t\tType: Rectangle\n\t\t\tLocalYaw: -128\n\t\t\tTopLeft: \1\n\t\t\tBottomRight: \2\n", text)
    return text


def main():
    OUT.write_text(build(), encoding="utf-8", newline="\n")
    EXTRA_SEQ.write_text(kit_extra_sequences(), encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(ROOT)}: {len(ROLE)} buildings on the kit, {len(FOOTPRINT)} footprints moved, "
          f"{len(CUT)} cut; heavy plant on {'the kit hpwr' if kit_has('hpwr-china') else 'interim powr art'}, "
          f"refinery upgrade {'with' if kit_has('refn-china', 'idle-purifier') else 'without'} kit overlay")


if __name__ == "__main__":
    main()
