#!/usr/bin/env python3
"""Exercise shipped campaign conditions in the actual engine, without owned content.

Assisted fixtures seed required units/buildings, transfer capture targets and
remove combat pressure. They test outcome logic and real convoy pathfinding;
they do not certify human playability, combat difficulty or entertainment value.
Never calls MarkCompleted/MarkFailed. Preserves each map's production Rules.
"""
import argparse
import concurrent.futures
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("balance", ROOT / "tools/balance-harness.py")
balance = importlib.util.module_from_spec(spec)
import sys
sys.modules[spec.name] = balance
spec.loader.exec_module(balance)


def lua(value):
    if isinstance(value, dict):
        return "{" + ",".join("[" + lua(k) + "]=" + lua(v) for k, v in value.items()) + "}"
    if isinstance(value, list):
        return "{" + ",".join(lua(v) for v in value) + "}"
    if isinstance(value, bool):
        return "true" if value else "false"
    return json.dumps(value, ensure_ascii=False)


def cases(mission, difficulty="normal"):
    yield {"id": "win", "expected": "won"}
    yield {"id": "army-wipe", "expected": "lost", "wipe": True}
    for name in mission.get("protect", []):
        yield {"id": "base-" + name, "expected": "lost", "kill": name}
    for i, obj in enumerate(mission["objectives"]):
        if obj["kind"] in ("capture", "protect"):
            for name in obj["targets"]:
                yield {"id": f"objective-{i}-{name}", "expected": "won" if obj.get("secondary") else "lost", "kill": name}
        if obj["kind"] in ("escort", "shipping"):
            yield {"id": f"convoy-{i}", "expected": "lost", "convoy": i + 1}
        if obj["kind"] == "disperse":
            yield {"id": f"disperse-{i}", "expected": "lost", "exposed": True}
    first_convoy = next((i for i, o in enumerate(mission["objectives"]) if o["kind"] in ("escort", "shipping")), None)
    if first_convoy is not None:
        shipping = mission["objectives"][first_convoy]["kind"] == "shipping"
        yield {"id": "boundary-one-survivor", "expected": "won" if difficulty == "easy" and not shipping else "lost",
               "convoy": first_convoy + 1, "keep_one": True}
    if any(o["kind"] == "reach" for o in mission["objectives"]):
        yield {"id": "boundary-undeployed", "expected": "lost", "undeployed": True, "fail_at": 1000}
        yield {"id": "boundary-one-amphibian", "expected": "won" if difficulty == "easy" else "lost",
               "reach_limit": 1, "fail_at": 1000}


def fixture_yaml(text):
    text = text.replace("\r\n", "\n")
    if "LuaScript:" in text:
        raise ValueError("Existing Lua scripting needs an explicit merge")
    if "\nRules:\n\tWorld:\n" not in text or "RTSAICampaign:" not in text:
        raise ValueError("Expected inline production campaign rules")
    text = text.replace("\nRules:\n\tWorld:\n", "\nRules:\n\tWorld:\n\t\tScriptTriggers:\n\t\tLuaScript:\n\t\t\tScripts: acceptance.lua\n", 1)
    return text.replace("\n\tPlayer:\n", "\n\tPlayer:\n\t\tScriptTriggers:\n", 1)


def objective_statuses_pass(mission, case, events):
    if case["expected"] != "won":
        return True
    completed = {int(e.split("|")[1]) for e in events if e.startswith("complete|")}
    failed = {int(e.split("|")[1]) for e in events if e.startswith("failed|")}
    expected_completed = {i for i, o in enumerate(mission["objectives"])
                          if not (case.get("kill") in o.get("targets", []) and o.get("secondary"))}
    expected_failed = set(range(len(mission["objectives"]))) - expected_completed
    return expected_completed <= completed and expected_failed <= failed


def run_one(mod, mission, case, resources, output, guard, difficulty):
    ident = mod + "--" + mission["id"] + "--" + case["id"]
    out = output / "cases" / ident
    out.mkdir(parents=True, exist_ok=False)
    support = out / "support"
    target = support / balance.user_map_dir(resources / mod) / "acceptance"
    source = ROOT / "mods" / mod / "campaigns/maps" / mission["id"]
    shutil.copytree(source, target)
    path = target / "map.yaml"
    text = fixture_yaml(path.read_text(encoding="utf-8-sig"))
    if "ScriptLobbyDropdown@difficulty:" not in text:
        raise ValueError("Campaign must expose its difficulty option")
    text = text.replace("\t\t\tDefault: normal", "\t\t\tDefault: " + difficulty)
    path.write_text(text, encoding="utf-8")
    script = (ROOT / "tools/campaign-acceptance.lua").read_text(encoding="utf-8")
    script = "Mission = " + lua(mission) + "\nCase = " + lua(case) + "\n" + script
    (target / "acceptance.lua").write_text(script, encoding="utf-8")
    engine = ROOT / "engine"
    command = ["dotnet", str(engine / "bin/OpenRA.dll"), f"Engine.EngineDir={engine}",
               f"Engine.ModSearchPaths={resources},{engine / 'mods'}", f"Engine.SupportDir={support}",
               f"Game.Mod={mod}", "Game.Platform=Null", "Game.FetchNews=false", "Launch.Map=acceptance", "Launch.Benchmark=benchmark-"]
    env = {k: v for k, v in os.environ.items() if not k.startswith(("OPENRA_AI_", "RTSAI_"))}
    start = time.monotonic()
    with (out / "game.log").open("w", encoding="utf-8") as log:
        process = subprocess.Popen(command, cwd=engine / "bin", env=env, stdout=log, stderr=subprocess.STDOUT)
        try:
            code = process.wait(timeout=guard)
        except subprocess.TimeoutExpired:
            process.kill()
            code = process.wait()
    log = support / "Logs/lua.log"
    lines = log.read_text(encoding="utf-8", errors="replace").splitlines() if log.exists() else []
    events = [line.split("ACCEPT|", 1)[1] for line in lines if "ACCEPT|" in line]
    outcomes = [line.split("|")[1] for line in events if line.startswith("outcome|")]
    result = {"id": ident, "mod": mod, "difficulty": difficulty, "mission": mission["id"], "case": case,
              "actual": outcomes[-1] if outcomes else "timeout-or-error", "events": events,
              "exit_code": code, "wall_seconds": round(time.monotonic() - start, 2),
              "fixture": "assisted-condition-coverage", "support": str(support)}
    result["objective_statuses_pass"] = objective_statuses_pass(mission, case, events)
    result["passed"] = result["actual"] == case["expected"] and code == 0 and result["objective_statuses_pass"]
    (out / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(ident, result["actual"], "PASS" if result["passed"] else "FAIL", flush=True)
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--mod", choices=["rtsai", "rtsai-topdown"], default="rtsai")
    ap.add_argument("--mission")
    ap.add_argument("--case")
    ap.add_argument("--boundary", action="store_true", help="Only count/deployment threshold fixtures")
    ap.add_argument("--difficulty", choices=["easy", "normal", "hard"], default="normal")
    ap.add_argument("--parallel", type=int, default=2)
    ap.add_argument("--guard", type=int, default=100)
    args = ap.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    balance.MOD = args.mod
    resources = balance.prepare_resources(output, ROOT / "mods")
    missions = json.loads((ROOT / "mods/rtsai/campaigns/missions.json").read_text(encoding="utf-8"))
    jobs = [(m, c) for m in missions if not args.mission or m["id"] == args.mission
            for c in cases(m, args.difficulty) if (not args.case or c["id"] == args.case)
            and (not args.boundary or c["id"].startswith("boundary-"))]
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.parallel) as pool:
        futures = [pool.submit(run_one, args.mod, m, c, resources, output, args.guard, args.difficulty) for m, c in jobs]
        results = [f.result() for f in futures]
    summary = {"mod": args.mod, "cases": len(results), "passed": sum(r["passed"] for r in results), "results": results,
               "limitations": "Assisted conditions; native-speaker review and human campaign difficulty acceptance remain separate."}
    (output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0 if all(r["passed"] for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
