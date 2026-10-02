#!/usr/bin/env python3
"""Summarise what each player (bot or human) queued and placed in an OpenRA replay.

Reads the StartProduction and PlaceBuilding orders of an .orarep file. Production queues live
on the player actor in RA2, so the order subject identifies the player; each subject is labelled
with the faction its items belong to (modern units are faction-specific). Useful for headless
AI-vs-AI balance runs, where the doctrine log is off or the stock bot modules are used.

Usage: python tools/replay-production.py <replay.orarep> [--top 8]
"""
from __future__ import annotations

import argparse
import collections
import re
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIELDS = {"Target": 0x01, "ExtraActors": 0x02, "TargetString": 0x04, "TargetIsCell": 0x40, "Subject": 0x80}


def read_string(data: bytes, i: int) -> tuple[str, int]:
    length, shift = 0, 0
    while True:  # BinaryWriter 7-bit encoded length
        b = data[i]
        i += 1
        length |= (b & 0x7F) << shift
        if b < 0x80:
            break
        shift += 7
    return data[i:i + length].decode("utf-8", "replace"), i + length


def orders(data: bytes, name: str):
    """(subject actor id, target string) for every Fields order called `name`."""
    for m in re.finditer(re.escape(bytes([len(name)]) + name.encode()), data):
        i = m.end()
        (flags,) = struct.unpack_from("<h", data, i)
        i += 2
        subject = None
        if flags & FIELDS["Subject"]:
            (subject,) = struct.unpack_from("<I", data, i)
            i += 4
        if flags & FIELDS["Target"]:
            kind = data[i]
            i += 1
            if kind == 1:  # Actor: id + generation
                i += 8
            elif kind == 2:  # Terrain
                if flags & FIELDS["TargetIsCell"]:
                    i += 5
                else:
                    i += 12
                    (count,) = struct.unpack_from("<h", data, i)
                    i += 2 + max(count, 0) * 12
            elif kind == 3:  # FrozenActor
                i += 8
        if not flags & FIELDS["TargetString"]:
            continue
        target, _ = read_string(data, i)
        if re.fullmatch(r"[\w.-]+", target):
            yield subject, target


def faction_prefixes() -> dict[str, str]:
    """Actor name -> modern faction, from the mod's roster files."""
    owners = {}
    for path in (ROOT / "mods/rtsai/modern-factions").glob("*-roster.yaml"):
        faction = path.name.removesuffix("-roster.yaml")
        text = path.read_text(encoding="utf-8")
        for actor in re.findall(r"^([a-z0-9]+):$", text, re.MULTILINE):
            owners[actor] = faction
        for actor, prereqs in re.findall(r"^([a-z0-9]+):\n(?:\t.*\n)*?\t\tPrerequisites: (.*)$", text, re.MULTILINE):
            if f"~faction.{faction}" in prereqs:
                owners[actor] = faction
    for path in (ROOT / "mods/rtsai/modern-factions").glob("*.yaml"):
        if path.stem in ("china", "iran", "turkey", "saudi", "yemen"):
            for actor, prereqs in re.findall(r"^([a-z0-9]+):\n(?:\t.*\n)*?\t\tPrerequisites: (.*)$", path.read_text(encoding="utf-8"), re.MULTILINE):
                if f"~faction.{path.stem}" in prereqs:
                    owners[actor] = path.stem
    return owners


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("replay", type=Path)
    parser.add_argument("--top", type=int, default=10)
    args = parser.parse_args()
    data = args.replay.read_bytes()
    owners = faction_prefixes()
    queued: dict[int, collections.Counter] = collections.defaultdict(collections.Counter)
    placed: dict[int, list[str]] = collections.defaultdict(list)
    for subject, item in orders(data, "StartProduction"):
        queued[subject][item] += 1
    for subject, item in orders(data, "PlaceBuilding"):
        placed[subject].append(item)
    for subject in sorted(set(queued) | set(placed)):
        factions = collections.Counter(owners[i] for i in list(queued[subject]) + placed[subject] if i in owners)
        label = factions.most_common(1)[0][0] if factions else "?"
        units = {k: v for k, v in queued[subject].items() if k not in placed[subject]}
        print(f"player actor {subject} ({label}): {sum(queued[subject].values())} queued, {len(placed[subject])} placed")
        print(f"  units  {dict(collections.Counter(units).most_common(args.top))}")
        print(f"  placed {placed[subject][:args.top]}")


if __name__ == "__main__":
    main()
