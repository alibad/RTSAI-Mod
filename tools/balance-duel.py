#!/usr/bin/env python3
"""Unit-value duels without bots: is a modern unit worth its cost against the stock RA2 equivalent?

Each duel spawns two groups of equal build value (``--budget`` credits each, rounded to whole units)
on the flat blank map, for two non-playable players, and orders both to attack-move through the other.
It records the value left on each side (cost x health fraction) when one side is gone or the duel
times out. ``--level 2`` makes both groups elite first, which shows what the veterancy system adds.
Side A starts on the west line in even replicates and on the east line in odd ones, and successive
duels use two separate fields. Uses the same headless, 1 ms-timestep setup as tools/balance-harness.py::

    python tools/balance-duel.py run --content <dir with ra2/> --output <scratch>/duels --parallel 4

Writes duels.csv (one row per duel) and duels.md (per pair: mean value left per side and wins).
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
import importlib.util
import os
from pathlib import Path
import re
import shutil
import statistics
import subprocess
import sys

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("balance_harness", HERE / "balance-harness.py")
bh = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = bh
spec.loader.exec_module(bh)

SCRIPT = HERE / "balance-duel.lua"
BASE_MAP = "blank-shellmap"
STOCK_MBT = ["mtnk", "htnk"]
MODERN_MBT = ["r2qilin", "r2bozkir", "r2m1a2s", "r2karrar"]
STOCK_RIFLE = ["e1", "e2"]
MODERN_RIFLE = ["r2cnrifle", "r2trrifle", "r2sang", "r2basij", "r2ymr"]
ANTI_TANK = ["shk", "r2cnportable", "r2trat", "r2saat", "r2toophan", "r2yrpg"]
GROUPS = {
    "mbt": [(s, m) for s in STOCK_MBT for m in MODERN_MBT],
    "rifle": [(s, m) for s in STOCK_RIFLE for m in MODERN_RIFLE],
    # Anti-tank infantry against the same tank (the Rhino), so the AT units can be compared.
    "at": [(a, "htnk") for a in ANTI_TANK],
    # Anti-air units against America's rocketeers (airborne infantry), stock and modern.
    "air": [(a, b) for b in ("jumpjet", "orca") for a in ("fv", "htk", "flakt", "r2mantis", "r2raad", "r2gokkalkan", "r2sads", "r2yzu")],
    # Stock against stock, to calibrate what "parity" means between the two RA2 sides.
    "ref": [("e1", "e2"), ("mtnk", "htnk")],
}


def duel_specs(group: str, level: int, reps: int) -> list[dict]:
    specs = []
    for rep in range(reps):
        for a, b in GROUPS[group]:
            specs.append({"id": f"{group}.L{level}.{a}-{b}.r{rep}", "a": a, "b": b, "level": level, "west": rep % 2 == 0})
    return specs


def lua_table(specs: list[dict]) -> str:
    return ", ".join(f'{{ id = "{s["id"]}", a = "{s["a"]}", b = "{s["b"]}", level = {s["level"]}, '
                     f'west = {"true" if s.get("west", True) else "false"} }}' for s in specs)


def fixture(maps: Path, target: Path, specs: list[dict], budget: int, timeout: int, rules: str = "",
            weapons: str = "") -> None:
    source = maps / BASE_MAP
    target.mkdir(parents=True)
    for item in source.iterdir():
        if item.is_file() and item.name != "map.yaml":
            shutil.copy2(item, target / item.name)
    text = (source / "map.yaml").read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    text = re.sub(r"^Title: [^\n]*$", "Title: Balance duels", text, count=1, flags=re.MULTILINE)
    text = re.sub(r"^Visibility: [^\n]*$", "Visibility: Lobby", text, count=1, flags=re.MULTILINE)
    text = re.sub(r"^Categories: [^\n]*$", "Categories: Conquest", text, count=1, flags=re.MULTILINE)
    players = ("\tPlayerReference@Multi0:\n\t\tName: Multi0\n\t\tPlayable: True\n\t\tFaction: america\n"
               "\t\tLockFaction: True\n\t\tLockSpawn: True\n\t\tSpawn: 1\n"
               "\tPlayerReference@DuelA:\n\t\tName: DuelA\n\t\tNonCombatant: True\n\t\tFaction: america\n"
               "\t\tColor: E04444\n\t\tEnemies: DuelB\n"
               "\tPlayerReference@DuelB:\n\t\tName: DuelB\n\t\tNonCombatant: True\n\t\tFaction: russia\n"
               "\t\tColor: 4477EE\n\t\tEnemies: DuelA\n")
    text = text.replace("\nActors:\n", "\n" + players + "\nActors:\n\tActor0: mpspawn\n\t\tLocation: 15,-5\n"
                        "\t\tOwner: Neutral\n", 1)
    text = re.sub(r"^Rules:\n(?:\t[^\n]*\n)*", "", text, flags=re.MULTILINE).rstrip("\n") + "\n\nRules: duel-rules.yaml\n"
    if weapons:
        text += "\nWeapons: duel-weapons.yaml\n"
        (target / "duel-weapons.yaml").write_text(weapons, encoding="utf-8", newline="\n")
    (target / "map.yaml").write_text(text, encoding="utf-8", newline="\n")
    (target / "duel-rules.yaml").write_text(
        "World:\n\t-StartGameNotification:\n\tScriptTriggers:\n\tLuaScript:\n\t\tScripts: balance-duel.lua\n\n" + rules,
        encoding="utf-8", newline="\n")
    script = (SCRIPT.read_text(encoding="utf-8").replace("__DUELS__", lua_table(specs))
              .replace("__TIMEOUT__", str(timeout)).replace("__BUDGET__", str(budget)))
    (target / "balance-duel.lua").write_text(script, encoding="utf-8", newline="\n")


def run_set(name: str, specs: list[dict], *, engine: Path, mods: Path, content: Path, output: Path,
            budget: int, timeout: int, keep: bool = False, rules: str = "", weapons: str = "") -> list[dict]:
    work = output / "sets" / name
    if work.exists():
        bh.clear_tree(work)
    support = work / "support"
    support.mkdir(parents=True)
    bh.link_directory(support / "Content", content)
    fixture(mods / bh.MOD / "maps", support / bh.user_map_dir(mods / bh.MOD) / "balance-duels", specs, budget, timeout,
            rules, weapons)
    env = {k: v for k, v in os.environ.items() if not k.startswith(("OPENRA_AI_", "RTSAI_"))}
    env["DOTNET_ROLL_FORWARD"] = env.get("DOTNET_ROLL_FORWARD", "Major")
    command = ["dotnet", str(engine / "bin" / "OpenRA.dll"), f"Engine.EngineDir={engine}",
               f"Engine.ModSearchPaths={mods},{engine / 'mods'}", f"Engine.SupportDir={support}",
               f"Game.Mod={bh.MOD}", "Game.Platform=Null", "Game.FetchNews=false",
               "Launch.Map=balance-duels", "Launch.Benchmark=benchmark-"]
    with (work / "game.log").open("w", encoding="utf-8", errors="replace") as log:
        process = subprocess.Popen(command, cwd=engine / "bin", env=env, stdout=log, stderr=subprocess.STDOUT)
        try:
            process.wait(timeout=3600)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=30)
    lua = support / "Logs" / "lua.log"
    text = lua.read_text(encoding="utf-8", errors="replace") if lua.is_file() else ""
    rows = []
    for line in text.splitlines():
        start = line.find("DUEL|")
        if start < 0:
            continue
        _, duel_id, ticks, a_left, b_left, a_alive, b_alive, a_value, b_value = line[start:].strip().split("|")
        group, level, pair, rep = duel_id.split(".")
        a, b = pair.split("-")
        rows.append({"id": duel_id, "group": group, "level": int(level[1:]), "a": a, "b": b, "rep": int(rep[1:]),
                     "ticks": int(ticks), "a_value": int(a_value), "b_value": int(b_value),
                     "a_left": int(a_left), "b_left": int(b_left), "a_alive": int(a_alive), "b_alive": int(b_alive)})
    if len(rows) == len(specs) and "DUELS|done" in text and not keep:
        bh.clear_tree(work)
    else:
        print(f"{name}: {len(rows)} of {len(specs)} duels recorded; support kept in {work}", flush=True)
    return rows


def report(rows: list[dict]) -> str:
    pairs: dict[tuple, list[dict]] = {}
    for row in rows:
        pairs.setdefault((row["group"], row["level"], row["a"], row["b"]), []).append(row)
    lines = ["| Group | Level | A | B | Value A / B | A value left | B value left | A wins-B wins-timeouts | Mean seconds |",
             "|---|---:|---|---|---:|---:|---:|---:|---:|"]
    for (group, level, a, b), rs in sorted(pairs.items()):
        a_frac = statistics.mean(r["a_left"] / r["a_value"] for r in rs)
        b_frac = statistics.mean(r["b_left"] / r["b_value"] for r in rs)
        a_wins = sum(1 for r in rs if r["b_alive"] == 0 and r["a_alive"] > 0)
        b_wins = sum(1 for r in rs if r["a_alive"] == 0 and r["b_alive"] > 0)
        lines.append(f"| {group} | {level} | {a} | {b} | {rs[0]['a_value']}/{rs[0]['b_value']} | {100 * a_frac:.0f}% | {100 * b_frac:.0f}% | "
                     f"{a_wins}-{b_wins}-{len(rs) - a_wins - b_wins} | {statistics.mean(r['ticks'] for r in rs) / 25:.0f} |")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("run")
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--content", type=Path, required=True)
    p.add_argument("--engine", type=Path, default=bh.ROOT / "engine")
    p.add_argument("--mods", type=Path, default=bh.ROOT / "mods")
    p.add_argument("--groups", default=",".join(GROUPS))
    p.add_argument("--levels", default="0,2", help="Veterancy levels to test (0 rookie, 2 elite)")
    p.add_argument("--reps", type=int, default=4)
    p.add_argument("--budget", type=int, default=6000)
    p.add_argument("--timeout", type=int, default=2250, help="Ticks per duel")
    p.add_argument("--parallel", type=int, default=4)
    p.add_argument("--keep-support", action="store_true")
    p.add_argument("--rules", type=Path, help="MiniYAML file merged into the duel map's rules (try a stat change)")
    p.add_argument("--weapons", type=Path, help="MiniYAML file merged into the duel map's weapons")
    args = parser.parse_args(argv)
    output = bh.absolute_path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    engine, content = bh.absolute_path(args.engine), bh.absolute_path(args.content)
    mods = bh.prepare_resources(output, bh.absolute_path(args.mods))
    rules = args.rules.read_text(encoding="utf-8") if args.rules else ""
    weapons = args.weapons.read_text(encoding="utf-8") if args.weapons else ""
    if re.search(r"^World:", rules, re.MULTILINE):
        raise SystemExit("--rules may not redefine World")
    sets = [(f"{g}-L{lv}", duel_specs(g, int(lv), args.reps)) for g in args.groups.split(",") for lv in args.levels.split(",")]
    with ThreadPoolExecutor(max_workers=args.parallel) as executor:
        results = list(executor.map(lambda s: run_set(s[0], s[1], engine=engine, mods=mods, content=content,
                                                      output=output, budget=args.budget, timeout=args.timeout,
                                                      keep=args.keep_support, rules=rules, weapons=weapons), sets))
    bh.clear_tree(output / "resources")
    rows = [row for rs in results for row in rs]
    with (output / "duels.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, list(rows[0]) if rows else ["id"])
        writer.writeheader()
        writer.writerows(rows)
    (output / "duels.md").write_text(report(rows), encoding="utf-8")
    print(report(rows))
    return 0 if sum(len(s) for _, s in sets) == len(rows) else 2


if __name__ == "__main__":
    raise SystemExit(main())
