#!/usr/bin/env python3
"""Headless bot-vs-bot balance campaigns for the RTS AI mod.

Ported from the OpenRA-AI ``codex/harness`` branch (scripts/balance_harness.py, eb8f6a1) to the
mod layout: one mod (``rtsai``), the slim engine's ``Launch.Bots`` and Null platform, no
Experience system. One command plans a campaign, runs every match as a private headless
OpenRA process and writes per-match results, a CSV, ``summary.json`` and ``report.md``::

    python tools/balance-harness.py run --campaign round-robin \
        --content <dir holding ra2/ra2.mix and ra2/language.mix> \
        --output <scratch>/round-robin --parallel 8

``plan`` prints the schedule, ``report`` rebuilds the summary from existing results. Matches
that already have a ``result.json`` are skipped, so an interrupted campaign resumes.

What the harness changes, and only in disposable copies:
  * a copy of each map with both combatant slots locked to a faction, spawn and colour, plus a
    telemetry-only Lua script (tools/balance-telemetry.lua) and the World traits it needs;
  * a private copy of mods/rtsai whose top-level files are copied and whose directories are
    links (no game data is copied), with the ``default`` game speed Timestep set to 1 ms.
Every simulated tick is identical to a normal-speed tick: only the wall-clock pacing between
ticks changes, so matches run as fast as the host allows. Durations are reported as
normal-speed game time (25 ticks per second). Replays keep the ``default`` speed id.

Each match runs in its own support directory, with the owned RA2 content linked in (never
copied; ``--standalone`` links nothing), no companion bridge and no network port. Both slots are bots of the same type; the
local client spectates. The engine seeds its RNG from the clock, so replicates are independent
samples, not reruns. Every match records the winner, the end reason (conquest, tick-cap draw,
mutual defeat, crash, hang), the duration and per-side production.
"""
from __future__ import annotations

import argparse
import csv
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, replace
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import re
import shutil
import stat
import statistics
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
MOD = "rtsai"
CAMPAIGNS = ROOT / "tools/balance-campaigns.json"
TELEMETRY = ROOT / "tools/balance-telemetry.lua"
TICKS_PER_SECOND = 25  # Normal game speed (Timestep 40 ms).
HARNESS_TIMESTEP = 1
SCHEMA = "rtsai.balance-harness/v1"
LAUNCH_SPACING = 0.5  # seconds between process starts: the engine seeds its RNGs from the clock
_launch_lock = threading.Lock()
_last_launch = [0.0]


# ---------------------------------------------------------------- planning

@dataclass(frozen=True)
class Match:
    id: str
    suite: str
    map: str
    map_title: str
    factions: tuple[str, str]
    spawns: tuple[int, int]
    bots: tuple[str, str]
    replicate: int
    seed: int
    tick_cap: int
    sample_interval: int
    rules: str = ""
    order: int = 0

    def to_dict(self) -> dict:
        data = asdict(self)
        for key in ("factions", "spawns", "bots"):
            data[key] = list(data[key])
        return data


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower().removesuffix(".oramap")).strip("-")


def derived_seed(seed: int, key: str) -> int:
    return int.from_bytes(hashlib.sha256(f"{seed}:{key}".encode()).digest()[:4], "big")


def load_campaign(name: str, path: Path = CAMPAIGNS) -> dict:
    campaigns = json.loads(path.read_text(encoding="utf-8"))
    if name not in campaigns:
        raise SystemExit(f"Unknown campaign '{name}'. Known: {', '.join(sorted(campaigns))}")
    campaign = dict(campaigns[name])
    campaign["name"] = name
    return campaign


def pairings(suite: dict) -> list[tuple[str, str]]:
    pairs = list(itertools.combinations(suite["factions"], 2))
    focus = set(suite.get("focus", ()))
    return [p for p in pairs if focus & set(p)] if focus else pairs


def suite_rules(suite: dict) -> str:
    """Optional experiment overlay: MiniYAML lines merged into each match's map rules.

    Lets a campaign try a doctrine or stat change, e.g. ["Player:", "\\t-BotDoctrine@china:"], on the
    disposable map copies without editing the mod. World is reserved for the telemetry plumbing.
    """
    lines = suite.get("rules", [])
    text = "\n".join(lines) if isinstance(lines, list) else str(lines)
    if re.search(r"^World:", text, re.MULTILINE):
        raise ValueError("Rule overlays may not redefine World (the telemetry plumbing lives there)")
    return text + "\n" if text else ""


def plan(campaign: dict, seed: int | None = None, suites: set[str] | None = None) -> list[Match]:
    """Expand a campaign into matches, deterministically ordered by ``seed``.

    Every unordered faction pairing is played from both slot/spawn orientations on every map,
    bot type and replicate, so the spawn advantage cancels within a pairing. Execution order is
    shuffled per replicate, so a partial (``--limit``) run is an unbiased subset that completes
    whole replicates first.
    """
    seed = campaign.get("seed", 0) if seed is None else seed
    matches: list[Match] = []
    for suite in campaign["suites"]:
        if suites and suite["id"] not in suites:
            continue
        for map_entry, bot, replicate, (a, b) in itertools.product(
                suite["maps"], suite["bots"], range(suite.get("replicates", 1)), pairings(suite)):
            for first, second in ((a, b), (b, a)):
                key = f"{suite['id']}.{slug(map_entry['map'])}.{bot}.{first}-{second}.r{replicate}"
                matches.append(Match(
                    id=key, suite=suite["id"], map=map_entry["map"], map_title=map_entry.get("title", map_entry["map"]),
                    factions=(first, second), spawns=tuple(map_entry.get("spawns", (1, 2))), bots=(bot, bot),
                    replicate=replicate, seed=derived_seed(seed, key), tick_cap=int(suite.get("tick_cap", 45000)),
                    sample_interval=int(suite.get("sample_interval", 250)), rules=suite_rules(suite)))
    ordered = sorted(matches, key=lambda m: (m.replicate, derived_seed(seed, "order:" + m.id)))
    return [replace(m, order=i) for i, m in enumerate(ordered)]


# -------------------------------------------------------------- resources

def absolute_path(path: Path | str) -> Path:
    r"""Absolute path without the ``\\?\`` prefix ``Path.resolve()`` can return on Windows.

    The engine appends forward-slash paths to the support directory; extended-length paths are
    not normalized, so a prefixed support dir silently hides its map folder (fork 1aa28ab).
    """
    text = os.path.abspath(os.fspath(path))
    if os.name == "nt" and text.startswith("\\\\?\\") and not text.startswith("\\\\?\\UNC\\"):
        text = text[4:]
    return Path(text)


def is_link(path: Path) -> bool:
    """Symlink or NTFS junction (Path.is_junction needs Python 3.12)."""
    try:
        info = os.lstat(path)
    except OSError:
        return False
    if stat.S_ISLNK(info.st_mode):
        return True
    return getattr(info, "st_reparse_tag", 0) == getattr(stat, "IO_REPARSE_TAG_MOUNT_POINT", -1)


def link_directory(link: Path, target: Path) -> None:
    """Expose ``target`` at ``link`` without copying it (symlink, else an NTFS junction)."""
    target = absolute_path(target)
    try:
        Path(link).symlink_to(target, target_is_directory=True)
    except OSError:
        if os.name != "nt":
            raise
        import _winapi  # CPython's documented-internal junction helper.

        _winapi.CreateJunction(str(target), str(link))


def clear_tree(path: Path) -> None:
    """Delete a harness directory without ever following links into game data or the repo."""
    path = Path(path)
    if is_link(path):
        os.unlink(path) if path.is_symlink() else os.rmdir(path)
        return
    if not path.exists():
        return
    for child in list(path.iterdir()):
        if is_link(child) or child.is_dir():
            clear_tree(child)
        else:
            child.unlink()
    path.rmdir()


def patch_manifest_speed(text: str, timestep: int = HARNESS_TIMESTEP) -> str:
    """Return a mod manifest whose ``default`` game speed has ``timestep`` ms."""
    pattern = re.compile(r"(^GameSpeeds:\n(?:[ \t][^\n]*\n)*?\t\tdefault:\n(?:\t\t\t[^\n]*\n)*?\t\t\tTimestep: )(\d+)",
                         re.MULTILINE)
    patched, count = pattern.subn(lambda m: m.group(1) + str(timestep), text.replace("\r\n", "\n"))
    if count != 1:
        raise ValueError("Manifest has no unique GameSpeeds default Timestep")
    return patched


def prepare_resources(output: Path, mods_source: Path) -> Path:
    """Private mod search path: the mod with a pacing-patched manifest, the content installer linked.

    Rebuilt on every run so it always reflects the current rules (only the manifest is copied;
    rules, maps and art are reached through links).
    """
    mods = output / "resources" / "mods"
    if mods.exists():
        clear_tree(mods)
    mods.mkdir(parents=True)
    for entry in sorted(mods_source.iterdir()):
        if not entry.is_dir():
            continue
        if entry.name != MOD:
            link_directory(mods / entry.name, entry)
            continue
        target = mods / MOD
        target.mkdir()
        for item in sorted(entry.iterdir()):
            if item.is_dir():
                link_directory(target / item.name, item)
            elif item.name == "mod.yaml":
                (target / item.name).write_text(patch_manifest_speed(item.read_text(encoding="utf-8")), encoding="utf-8")
            else:
                shutil.copy2(item, target / item.name)
    return mods


# ------------------------------------------------------------ map fixture

def spawn_points(map_yaml: str) -> list[tuple[int, int]]:
    """mpspawn locations in engine spawn order (map actor order)."""
    points = []
    for block in re.finditer(r"^\t[^\t\n][^\n]*: mpspawn\n((?:\t\t[^\n]*\n)+)", map_yaml, re.MULTILINE):
        loc = re.search(r"Location: (-?\d+),\s*(-?\d+)", block.group(1))
        if loc:
            points.append((int(loc.group(1)), int(loc.group(2))))
    return points


def _set_field(block: str, key: str, value: str) -> str:
    line = f"\t\t{key}: {value}\n"
    if re.search(rf"^\t\t{key}:[^\n]*\n", block, re.MULTILINE):
        return re.sub(rf"^\t\t{key}:[^\n]*\n", line, block, count=1, flags=re.MULTILINE)
    return block + line


def patch_map_yaml(text: str, factions: tuple[str, str], spawns: tuple[int, int], title: str) -> str:
    """Lock both combatant slots' faction, spawn and colour, and add the telemetry rules."""
    text = text.replace("\r\n", "\n")
    if "LuaScript" in text:
        raise ValueError("Map already defines a LuaScript; choose a map without mission scripting")
    count = len(spawn_points(text))
    for spawn in spawns:
        if not 1 <= spawn <= count:
            raise ValueError(f"Spawn {spawn} outside 1..{count}")
    colors = ("E04444", "4477EE")
    for slot, (faction, spawn) in enumerate(zip(factions, spawns)):
        pattern = re.compile(rf"(^\tPlayerReference@Multi{slot}:\n)((?:\t\t[^\n]*\n)+)", re.MULTILINE)
        found = pattern.search(text)
        if not found:
            raise ValueError(f"Map has no Multi{slot} slot")
        block = found.group(2)
        if "Playable: True" not in block:
            raise ValueError(f"Multi{slot} is not playable")
        for key, value in (("Faction", faction), ("LockFaction", "True"), ("LockSpawn", "True"),
                           ("Spawn", str(spawn)), ("LockColor", "True"), ("Color", colors[slot])):
            block = _set_field(block, key, value)
        text = text[:found.start(2)] + block + text[found.end(2):]
    text = re.sub(r"^Title: [^\n]*$", f"Title: {title}", text, count=1, flags=re.MULTILINE)
    text = re.sub(r"^Visibility: [^\n]*$", "Visibility: Lobby", text, count=1, flags=re.MULTILINE)
    rules = re.search(r"^Rules:([^\n]*)\n", text, re.MULTILINE)
    if rules is None:
        text = text.rstrip("\n") + "\n\nRules: balance-rules.yaml\n"
    else:
        files = [f.strip() for f in rules.group(1).split(",") if f.strip()] + ["balance-rules.yaml"]
        text = text[:rules.start()] + "Rules: " + ", ".join(files) + "\n" + text[rules.end():]
    return text


def write_fixture(match: Match, maps_dir: Path, target: Path) -> None:
    source = maps_dir / match.map
    files = {p.name: p.read_bytes() for p in source.iterdir() if p.is_file()}
    if "map.yaml" not in files:
        raise ValueError(f"{match.map} has no map.yaml")
    target.mkdir(parents=True)
    for name, content in files.items():
        if name != "map.yaml":
            (target / name).write_bytes(content)
    map_yaml = patch_map_yaml(files["map.yaml"].decode("utf-8-sig"), match.factions, match.spawns, "Balance " + match.id)
    (target / "map.yaml").write_text(map_yaml, encoding="utf-8", newline="\n")
    # The RA2 World has neither trait; both are passive plumbing for the telemetry script.
    (target / "balance-rules.yaml").write_text(
        "World:\n\tScriptTriggers:\n\tLuaScript:\n\t\tScripts: balance-telemetry.lua\n\n" + match.rules,
        encoding="utf-8", newline="\n")
    script = TELEMETRY.read_text(encoding="utf-8")
    script = (script.replace("__MATCH_ID__", match.id).replace("__SAMPLE_INTERVAL__", str(match.sample_interval))
              .replace("__TICK_CAP__", str(match.tick_cap)))
    (target / "balance-telemetry.lua").write_text(script, encoding="utf-8", newline="\n")


# --------------------------------------------------------------- running

def user_map_dir(mod_dir: Path) -> str:
    manifest = (mod_dir / "mod.yaml").read_text(encoding="utf-8")
    found = re.search(rf"^\t~\^SupportDir\|(maps/{MOD}/[^:\n]+): User$", manifest, re.MULTILINE)
    if not found:
        raise ValueError(f"{MOD} manifest has no user map folder")
    return found.group(1)


def engine_seed(replay: Path) -> int | None:
    found = re.search(rb"RandomSeed: (-?\d+)", replay.read_bytes()) if replay.is_file() else None
    return int(found.group(1)) if found else None


def run_match(match: Match, *, engine: Path, mods: Path, content: Path | None, output: Path, guard: float,
              keep_support: bool = False, bot_log: bool = False, dotnet: str = "dotnet") -> dict:
    match_dir = output / "matches" / match.id
    if match_dir.exists():
        clear_tree(match_dir)
    support = match_dir / "support"
    support.mkdir(parents=True)
    if content is not None:
        link_directory(support / "Content", content)
    fixture = "balance-" + slug(match.id)
    maps_rel = user_map_dir(mods / MOD)
    maps_dir = next((d for d in (mods / MOD / "maps", mods / MOD / "standalone" / "maps") if (d / match.map).is_dir()),
                    mods / MOD / "maps")
    write_fixture(match, maps_dir, support / maps_rel / fixture)
    env = {k: v for k, v in os.environ.items() if not k.startswith(("OPENRA_AI_", "RTSAI_"))}
    env["DOTNET_ROLL_FORWARD"] = env.get("DOTNET_ROLL_FORWARD", "Major")
    if bot_log:
        env["RTSAI_BOT_LOG"] = "1"
    command = [dotnet, str(engine / "bin" / "OpenRA.dll"), f"Engine.EngineDir={engine}",
               f"Engine.ModSearchPaths={mods},{engine / 'mods'}", f"Engine.SupportDir={support}", f"Game.Mod={MOD}",
               "Game.Platform=Null", "Game.FetchNews=false", f"Launch.Map={fixture}",
               f"Launch.Bots=Multi0:{match.bots[0]},Multi1:{match.bots[1]}", "Launch.Benchmark=benchmark-"]
    with _launch_lock:  # Simultaneous starts were seen to share the server's RandomSeed.
        time.sleep(max(0.0, _last_launch[0] + LAUNCH_SPACING - time.monotonic()))
        _last_launch[0] = time.monotonic()
    started = time.monotonic()
    status = "complete"
    with (match_dir / "game.log").open("w", encoding="utf-8", errors="replace") as log:
        process = subprocess.Popen(command, cwd=engine / "bin", env=env, stdout=log, stderr=subprocess.STDOUT)
        try:
            exit_code = process.wait(timeout=guard)
        except subprocess.TimeoutExpired:
            process.kill()
            exit_code = process.wait(timeout=30)
            status = "hang"
    wall = round(time.monotonic() - started, 1)
    logs = support / "Logs"
    for name, target in (("lua.log", "telemetry.log"), ("bot-doctrine.log", "bot-doctrine.log")):
        if (logs / name).is_file():
            shutil.copy2(logs / name, match_dir / target)
    exceptions = sorted(logs.glob("exception-*.log")) if logs.is_dir() else []
    for exception in exceptions:
        shutil.copy2(exception, match_dir / exception.name)
    replays = sorted((support / "Replays").rglob("*.orarep")) if (support / "Replays").is_dir() else []
    replay = None
    if replays:
        replay = match_dir / "replay.orarep"
        shutil.copy2(replays[-1], replay)
    text = (match_dir / "telemetry.log").read_text(encoding="utf-8", errors="replace") \
        if (match_dir / "telemetry.log").is_file() else ""
    telemetry = parse_telemetry(text, match.id)
    lua_errors = [line for line in text.splitlines() if "Fatal Lua Error" in line or "Lua error" in line]
    outcome = decide_outcome(telemetry, exit_code, status, exceptions, lua_errors)
    result = {
        "schema": SCHEMA, "match": match.to_dict(), "status": outcome["status"], "outcome": outcome,
        "exit_code": exit_code, "wall_seconds": wall, "exceptions": [p.name for p in exceptions],
        "lua_errors": lua_errors[:5], "replay": replay.name if replay else None,
        "engine_random_seed": engine_seed(replay) if replay else None,
        "harness_timestep_ms": HARNESS_TIMESTEP, "telemetry": telemetry,
    }
    (match_dir / "result.json").write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    if not keep_support and outcome["status"] == "complete":
        clear_tree(support)
    return result


# ------------------------------------------------------------- telemetry

SAMPLE_FIELDS = ("cash", "resources", "kills_cost", "deaths_cost", "units_killed", "units_lost",
                 "buildings_killed", "buildings_lost", "army_value", "armed_units", "unit_spend",
                 "building_spend", "actors", "veteran_value", "elite_value")


def parse_telemetry(text: str, match_id: str) -> dict:
    players: dict[str, dict] = {}
    samples: dict[str, list] = {}
    produced: list = []
    placed: list = []
    lost: list = []
    events: dict = {"won": [], "defeated": [], "cap": None}
    malformed = 0
    prefix = f"BALANCE|{match_id}|"
    for line in text.splitlines():
        start = line.find(prefix)
        if start < 0:
            continue
        parts = line[start:].strip().split("|")
        try:
            kind, tick, fields = parts[2], int(parts[3]), parts[4:]
            if kind == "player":
                players[fields[0]] = {"faction": fields[1], "spawn": int(fields[2]), "bot": fields[3] == "true"}
            elif kind == "sample":
                samples.setdefault(fields[0], []).append([tick] + [int(v) for v in fields[1:]])
            elif kind == "produced":
                produced.append([tick, fields[0], fields[1], fields[2], int(fields[3])])
            elif kind == "starting":
                produced.append([tick, fields[0], fields[1], "Starting", int(fields[2])])
            elif kind == "placed":
                placed.append([tick, fields[0], fields[1], int(fields[2])])
            elif kind == "lost":  # owner, type, role, cost, killer player[, killer type]
                lost.append([tick, fields[0], fields[1], fields[2], int(fields[3]), fields[4],
                             fields[5] if len(fields) > 5 else ""])
            elif kind in ("won", "defeated"):
                events[kind].append([tick, fields[0]])
            elif kind == "cap":
                events["cap"] = tick
        except (IndexError, ValueError):
            malformed += 1
    return {"players": players, "sample_fields": ["tick", *SAMPLE_FIELDS], "samples": samples,
            "produced": produced, "placed": placed, "lost": lost, "events": events, "malformed_lines": malformed}


def decide_outcome(telemetry: dict, exit_code: int | None, status: str, exceptions: list, lua_errors: list) -> dict:
    events = telemetry["events"]
    last_tick = max((s[-1][0] for s in telemetry["samples"].values() if s), default=0)
    for group in (events["won"], events["defeated"]):
        last_tick = max([last_tick] + [tick for tick, _ in group])
    if status == "hang":
        return {"status": "hang", "result": "error", "reason": "wall-clock guard", "end_tick": last_tick}
    if exceptions or lua_errors or exit_code not in (0, None) or not telemetry["players"]:
        reason = "exception" if exceptions else "lua-error" if lua_errors else (
            "no-telemetry" if not telemetry["players"] else f"exit {exit_code}")
        return {"status": "crash", "result": "error", "reason": reason, "end_tick": last_tick}
    if events["cap"] is not None:
        return {"status": "complete", "result": "draw", "reason": "tick-cap", "end_tick": events["cap"]}
    winners = sorted({p for _, p in events["won"]})
    losers = sorted({p for _, p in events["defeated"]})
    if len(winners) == 1:
        tick = max(t for t, p in events["won"] if p == winners[0])
        return {"status": "complete", "result": "win", "winner": winners[0], "reason": "conquest", "end_tick": tick}
    if len(losers) == 1 and len(telemetry["players"]) == 2:
        winner = next(p for p in telemetry["players"] if p not in losers)
        return {"status": "complete", "result": "win", "winner": winner, "reason": "conquest",
                "end_tick": max(t for t, _ in events["defeated"])}
    if len(losers) == 2:
        return {"status": "complete", "result": "draw", "reason": "mutual-defeat", "end_tick": last_tick}
    return {"status": "crash", "result": "error", "reason": "ended-without-result", "end_tick": last_tick}


def side_production(result: dict, player: str) -> dict:
    """Per-side production: units by type (excluding starting units), structures and value traded."""
    telemetry = result["telemetry"]
    units: dict[str, int] = {}
    unit_value = 0
    for _, owner, actor, role, cost in telemetry["produced"]:
        if owner == player and role != "Starting":
            units[actor] = units.get(actor, 0) + 1
            unit_value += cost
    structures = [(actor, cost) for _, owner, actor, cost in telemetry["placed"] if owner == player]
    fields = telemetry["sample_fields"]
    samples = telemetry["samples"].get(player) or [[0] * len(fields)]
    return {"units": dict(sorted(units.items(), key=lambda kv: (-kv[1], kv[0]))), "unit_count": sum(units.values()),
            "unit_value": unit_value, "structures": len(structures), "structure_value": sum(c for _, c in structures),
            "value_destroyed": samples[-1][fields.index("kills_cost")], "value_lost": samples[-1][fields.index("deaths_cost")]}


# ------------------------------------------------------------ statistics

def wilson(successes: float, total: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval; a draw counts as half a success."""
    if total == 0:
        return (0.0, 1.0)
    p = successes / total
    denominator = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denominator
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    return (max(0.0, centre - half), min(1.0, centre + half))


def minutes(ticks: int) -> float:
    return ticks / TICKS_PER_SECOND / 60


def length_stats(ticks: list[int]) -> dict:
    if not ticks:
        return {}
    values = sorted(minutes(t) for t in ticks)
    return {"median": round(statistics.median(values), 1), "mean": round(statistics.mean(values), 1),
            "p10": round(values[int(0.1 * (len(values) - 1))], 1), "p90": round(values[int(0.9 * (len(values) - 1))], 1),
            "max": round(values[-1], 1)}


def slot_faction(result: dict, player: str) -> str:
    return result["match"]["factions"][int(player.removeprefix("Multi"))]


def summarize(results: list[dict]) -> dict:
    complete = [r for r in results if r["status"] == "complete"]
    errors = [r for r in results if r["status"] != "complete"]
    factions: dict[str, dict] = {}
    matrix: dict[str, dict[str, dict]] = {}
    by_map: dict[str, list] = {}
    for result in complete:
        match, outcome = result["match"], result["outcome"]
        by_map.setdefault(match["map_title"], []).append(result)
        for slot, faction in enumerate(match["factions"]):
            opponent = match["factions"][1 - slot]
            player = f"Multi{slot}"
            prod = side_production(result, player)
            f = factions.setdefault(faction, {"games": 0, "wins": 0, "draws": 0, "losses": 0, "lengths": [],
                                              "unit_count": 0, "unit_value": 0, "structures": 0,
                                              "value_destroyed": 0, "value_lost": 0, "actor_types": {}, "unit_trade": {}})
            cell = matrix.setdefault(faction, {}).setdefault(opponent, {"games": 0, "wins": 0, "draws": 0, "losses": 0})
            key = "draws" if outcome["result"] == "draw" else "wins" if outcome.get("winner") == player else "losses"
            for row in (f, cell):
                row["games"] += 1
                row[key] += 1
            f["lengths"].append(outcome["end_tick"])
            for field in ("unit_count", "unit_value", "structures", "value_destroyed", "value_lost"):
                f[field] += prod[field]
            for actor, count in prod["units"].items():
                f["actor_types"][actor] = f["actor_types"].get(actor, 0) + count
            # Per unit type: [produced value, value lost, enemy value destroyed] (killer type is recorded
            # by the telemetry script since balance-telemetry.lua v2).
            trade = f["unit_trade"]
            for _, owner, actor, role, cost in result["telemetry"]["produced"]:
                if owner == player and role != "Starting":
                    trade.setdefault(actor, [0, 0, 0])[0] += cost
            for row in result["telemetry"]["lost"]:
                _, owner, actor, role, cost, killer = row[:6]
                killer_type = row[6] if len(row) > 6 else ""
                if owner == player and role not in ("Starting", "Building"):
                    trade.setdefault(actor, [0, 0, 0])[1] += cost
                elif killer == player and killer_type:
                    trade.setdefault(killer_type, [0, 0, 0])[2] += cost
    for f in factions.values():
        score = f["wins"] + 0.5 * f["draws"]
        f["win_rate"] = round(f["wins"] / f["games"], 3) if f["games"] else None
        f["win_rate_ci95"] = [round(v, 3) for v in wilson(f["wins"], f["games"])]
        f["score"] = round(score / f["games"], 3) if f["games"] else None
        f["score_ci95"] = [round(v, 3) for v in wilson(score, f["games"])]
        f["cost_efficiency"] = round(f["value_destroyed"] / f["value_lost"], 2) if f["value_lost"] else None
        f["length_minutes"] = length_stats(f.pop("lengths"))
        for field in ("unit_count", "unit_value", "structures"):
            f[f"mean_{field}"] = round(f.pop(field) / f["games"], 1) if f["games"] else None
        f["top_units"] = dict(sorted(f.pop("actor_types").items(), key=lambda kv: -kv[1])[:8])
        f["unit_trade"] = dict(sorted(((k, v) for k, v in f["unit_trade"].items() if v[0]),
                                      key=lambda kv: -kv[1][0])[:10])
    for row in matrix.values():
        for cell in row.values():
            cell["score"] = round((cell["wins"] + 0.5 * cell["draws"]) / cell["games"], 3)
    lengths = [r["outcome"]["end_tick"] for r in complete]
    seeds = [r.get("engine_random_seed") for r in results if r.get("engine_random_seed") is not None]
    return {
        "schema": SCHEMA, "matches": len(results), "complete": len(complete), "errors": len(errors),
        "error_matches": [{"id": r["match"]["id"], "status": r["status"], "reason": r["outcome"]["reason"],
                           "exceptions": r["exceptions"], "lua_errors": r["lua_errors"]} for r in errors],
        "draws": {"tick-cap": sum(1 for r in complete if r["outcome"]["reason"] == "tick-cap"),
                  "mutual-defeat": sum(1 for r in complete if r["outcome"]["reason"] == "mutual-defeat")},
        "length_minutes": length_stats(lengths),
        "duplicate_engine_seeds": len(seeds) - len(set(seeds)),
        "by_map": {name: {"games": len(rs), "draws": sum(1 for r in rs if r["outcome"]["result"] == "draw"),
                          "length_minutes": length_stats([r["outcome"]["end_tick"] for r in rs]),
                          "first_slot_score": round(sum(1.0 if r["outcome"].get("winner") == "Multi0" else
                                                        0.5 if r["outcome"]["result"] == "draw" else 0.0
                                                        for r in rs) / len(rs), 3)}
                   for name, rs in sorted(by_map.items())},
        "factions": dict(sorted(factions.items(), key=lambda kv: -(kv[1]["score"] or 0))),
        "matrix": matrix,
        "wall_seconds": round(sum(r["wall_seconds"] for r in results), 1),
    }


# --------------------------------------------------------------- report

def pct(value: float | None) -> str:
    return "—" if value is None else f"{100 * value:.0f}%"


def render_matrix(summary: dict, order: list[str]) -> list[str]:
    """Row faction's wins-losses (draws) against each column faction."""
    present = [f for f in order if f in summary["matrix"]]
    lines = ["| vs | " + " | ".join(present) + " | Total |", "|---|" + "---:|" * (len(present) + 1)]
    for row in present:
        cells = []
        for column in present:
            cell = summary["matrix"][row].get(column)
            if row == column or cell is None:
                cells.append("—")
            else:
                cells.append(f"{cell['wins']}-{cell['losses']}" + (f" ({cell['draws']}d)" if cell["draws"] else ""))
        f = summary["factions"][row]
        cells.append(f"{f['wins']}-{f['losses']}" + (f" ({f['draws']}d)" if f["draws"] else ""))
        lines.append(f"| **{row}** | " + " | ".join(cells) + " |")
    return lines


def render_report(summary: dict, campaign: dict, planned: int, order: list[str]) -> str:
    lines = [f"# Balance campaign `{campaign['name']}`", "",
             f"Generated by `tools/balance-harness.py` ({SCHEMA}). {summary['complete']} of {planned} planned matches "
             f"complete, {summary['errors']} errors. Draws: {summary['draws']['tick-cap']} tick-cap, "
             f"{summary['draws']['mutual-defeat']} mutual defeat. Match length (game minutes): "
             f"{fmt_lengths(summary['length_minutes'])}.", "",
             "## Win matrix (row wins-losses vs column)", "", *render_matrix(summary, order), "",
             "## Factions", "",
             "Win rate counts draws as non-wins; score counts a draw as half a win. Intervals are 95% Wilson.", "",
             "| Faction | Games | W-D-L | Win rate (95% CI) | Score (95% CI) | Value destroyed/lost | Median min | "
             "Units/game | Structures/game | Top units |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
    for name in [f for f in order if f in summary["factions"]]:
        f = summary["factions"][name]
        wr, sc = f["win_rate_ci95"], f["score_ci95"]
        top = ", ".join(f"{k} {v}" for k, v in list(f["top_units"].items())[:5])
        lines.append(f"| {name} | {f['games']} | {f['wins']}-{f['draws']}-{f['losses']} | {pct(f['win_rate'])} "
                     f"({pct(wr[0])}–{pct(wr[1])}) | {pct(f['score'])} ({pct(sc[0])}–{pct(sc[1])}) | "
                     f"{f['cost_efficiency'] or '—'} | {f['length_minutes'].get('median', '—')} | {f['mean_unit_count']} | "
                     f"{f['mean_structures']} | {top} |")
    lines += ["", "## Unit trade", "",
              "Top unit types by value produced: produced / lost / enemy value destroyed (in thousands), and destroyed "
              "per credit produced.", "", "| Faction | Units |", "|---|---|"]
    for name in [f for f in order if f in summary["factions"]]:
        trade = summary["factions"][name].get("unit_trade", {})
        cells = [f"{actor} {p // 1000}/{lost // 1000}/{d // 1000} ({d / p:.2f})" for actor, (p, lost, d) in list(trade.items())[:6]]
        lines.append(f"| {name} | {'; '.join(cells)} |")
    lines += ["", "## Maps", "", "| Map | Games | Draws | Median min | First-slot score |", "|---|---:|---:|---:|---:|"]
    for name, row in summary["by_map"].items():
        lines.append(f"| {name} | {row['games']} | {row['draws']} | {row['length_minutes'].get('median', '—')} | "
                     f"{pct(row['first_slot_score'])} |")
    if summary["error_matches"]:
        lines += ["", "## Errors", "", "| Match | Status | Reason | Exceptions |", "|---|---|---|---|"]
        for row in summary["error_matches"]:
            lines.append(f"| {row['id']} | {row['status']} | {row['reason']} | {', '.join(row['exceptions']) or '—'} |")
    return "\n".join(lines) + "\n"


def fmt_lengths(stats: dict) -> str:
    if not stats:
        return "—"
    return f"median {stats['median']}, mean {stats['mean']}, p10 {stats['p10']}, p90 {stats['p90']}, max {stats['max']}"


CSV_FIELDS = ["match", "map", "bot", "replicate", "faction_0", "faction_1", "spawn_0", "spawn_1", "status", "result",
              "winner", "end_reason", "end_tick", "game_minutes", "wall_seconds", "engine_seed",
              "units_0", "unit_value_0", "structures_0", "destroyed_0", "lost_0", "production_0",
              "units_1", "unit_value_1", "structures_1", "destroyed_1", "lost_1", "production_1"]


def csv_row(result: dict) -> dict:
    match, outcome = result["match"], result["outcome"]
    row = {"match": match["id"], "map": match["map"], "bot": match["bots"][0], "replicate": match["replicate"],
           "faction_0": match["factions"][0], "faction_1": match["factions"][1], "spawn_0": match["spawns"][0],
           "spawn_1": match["spawns"][1], "status": result["status"], "result": outcome["result"],
           "winner": slot_faction(result, outcome["winner"]) if outcome.get("winner") else "",
           "end_reason": outcome["reason"], "end_tick": outcome["end_tick"],
           "game_minutes": round(minutes(outcome["end_tick"]), 2), "wall_seconds": result["wall_seconds"],
           "engine_seed": result.get("engine_random_seed")}
    for slot in (0, 1):
        prod = side_production(result, f"Multi{slot}")
        row.update({f"units_{slot}": prod["unit_count"], f"unit_value_{slot}": prod["unit_value"],
                    f"structures_{slot}": prod["structures"], f"destroyed_{slot}": prod["value_destroyed"],
                    f"lost_{slot}": prod["value_lost"],
                    f"production_{slot}": " ".join(f"{k}:{v}" for k, v in prod["units"].items())})
    return row


# ------------------------------------------------------------------ CLI

def load_results(output: Path, planned: list[Match]) -> list[dict]:
    ids = {m.id for m in planned}
    results = []
    for path in sorted((output / "matches").glob("*/result.json")):
        result = json.loads(path.read_text(encoding="utf-8"))
        if result["match"]["id"] in ids:
            results.append(result)
    return results


def write_summary(output: Path, campaign: dict, planned: list[Match], seed: int) -> dict:
    results = load_results(output, planned)
    summary = summarize(results)
    summary.update(campaign=campaign["name"], seed=seed, planned=len(planned))
    order = list(dict.fromkeys(f for suite in campaign["suites"] for f in suite["factions"]))
    (output / "summary.json").write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
    (output / "report.md").write_text(render_report(summary, campaign, len(planned), order), encoding="utf-8")
    with (output / "matches.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, CSV_FIELDS)
        writer.writeheader()
        for result in sorted(results, key=lambda r: r["match"]["order"]):
            writer.writerow(csv_row(result))
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("plan", "run", "report"):
        p = sub.add_parser(name)
        p.add_argument("--campaign", default="round-robin")
        p.add_argument("--campaigns-file", type=Path, default=CAMPAIGNS)
        p.add_argument("--seed", type=int)
        p.add_argument("--suite", action="append", help="Limit to these suite ids")
        p.add_argument("--limit", type=int, help="Only the first N matches of the seeded order")
        if name in ("run", "report"):
            p.add_argument("--output", type=Path, required=True)
        if name == "run":
            p.add_argument("--engine", type=Path, default=ROOT / "engine")
            p.add_argument("--mods", type=Path, default=ROOT / "mods", help="Mod source directory (holds rtsai/)")
            p.add_argument("--content", type=Path, help="Directory holding ra2/ra2.mix and ra2/language.mix")
            p.add_argument("--standalone", action="store_true",
                           help="The standalone game (docs/standalone.md): no RA2 content, nothing linked as Content")
            p.add_argument("--parallel", type=int, default=4)
            p.add_argument("--rerun", action="store_true", help="Rerun matches that already have results")
            p.add_argument("--keep-support", action="store_true")
            p.add_argument("--bot-log", action="store_true", help="Set RTSAI_BOT_LOG=1 (doctrine decision log per match)")
    args = parser.parse_args(argv)
    campaign = load_campaign(args.campaign, args.campaigns_file)
    seed = campaign.get("seed", 0) if args.seed is None else args.seed
    matches = plan(campaign, seed, set(args.suite) if args.suite else None)
    if args.limit:
        matches = matches[:args.limit]
    if args.command == "plan":
        for match in matches:
            print(json.dumps(match.to_dict()))
        print(f"{len(matches)} matches", file=sys.stderr)
        return 0
    output = absolute_path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    if args.command == "report":
        summary = write_summary(output, campaign, matches, seed)
        print(json.dumps({k: summary[k] for k in ("matches", "complete", "errors")}))
        return 0
    engine = absolute_path(args.engine)
    content = None if args.standalone else absolute_path(args.content) if args.content else None
    if not (engine / "bin" / "OpenRA.dll").is_file():
        raise SystemExit(f"No engine build at {engine}: run ./fetch-local-engine.sh and make all first")
    if not args.standalone and (content is None or not (content / "ra2" / "ra2.mix").is_file()):
        raise SystemExit(f"{content} has no ra2/ra2.mix (owned Red Alert 2 content); --standalone runs without it")
    mods = prepare_resources(output, absolute_path(args.mods))
    (output / "campaign.json").write_text(json.dumps({"campaign": campaign, "seed": seed, "planned": [
        m.to_dict() for m in matches]}, indent=1) + "\n", encoding="utf-8")
    pending = [m for m in matches if args.rerun or not (output / "matches" / m.id / "result.json").is_file()]
    print(f"{len(matches)} planned, {len(pending)} to run, parallel {args.parallel}", flush=True)
    guard = float(campaign.get("wall_guard_seconds", 1200))
    started = time.monotonic()

    def work(match: Match) -> dict:
        try:
            return run_match(match, engine=engine, mods=mods, content=content, output=output, guard=guard,
                             keep_support=args.keep_support, bot_log=args.bot_log)
        except Exception as exc:  # Harness/fixture failure: record it and keep going.
            failure = {"schema": SCHEMA, "match": match.to_dict(), "status": "harness-error",
                       "outcome": {"status": "harness-error", "result": "error", "reason": str(exc), "end_tick": 0},
                       "exit_code": None, "wall_seconds": 0, "exceptions": [], "lua_errors": [], "replay": None,
                       "telemetry": parse_telemetry("", match.id)}
            path = output / "matches" / match.id
            path.mkdir(parents=True, exist_ok=True)
            (path / "result.json").write_text(json.dumps(failure, indent=1) + "\n", encoding="utf-8")
            return failure

    with ThreadPoolExecutor(max_workers=max(1, args.parallel)) as executor:
        for done, result in enumerate(executor.map(work, pending), 1):
            outcome = result["outcome"]
            winner = slot_faction(result, outcome["winner"]) if outcome.get("winner") else ""
            print(f"[{done}/{len(pending)} {time.monotonic() - started:.0f}s] {result['match']['id']}: "
                  f"{outcome['result']} {winner} {outcome['reason']} @{minutes(outcome['end_tick']):.1f}min "
                  f"wall {result['wall_seconds']}s", flush=True)
    clear_tree(output / "resources")
    summary = write_summary(output, campaign, matches, seed)
    print(json.dumps({k: summary[k] for k in ("matches", "complete", "errors")}))
    return 0 if summary["errors"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
