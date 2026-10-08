#!/usr/bin/env python3
"""Standalone boot smoke test: run the rendered client with an EMPTY support dir (no RA2 content anywhere).

  menu       start normally, wait, grab the window: does the main menu come up without the content installer?
  skirmish   Launch.Map + Launch.Bots: a local skirmish between two bots on one shipped map, host spectating.

The run takes the shared `game-window` lock (RTSAI-Art/tools/route_lock.py) and announces itself in
C:/Users/Admin/Code/AI/logs/gpu-yield.txt, with the companion host off (OPENRA_AI_HOST=0). Window grabs and the
engine logs land in --out. The support dir is a fresh scratch folder with no Content junction, so nothing EA can
be resolved even by accident.

usage: python tools/standalone-smoke.py menu --out <scratch>/menu
       python tools/standalone-smoke.py skirmish --map tournament-2B --bots Multi0:normal:china,Multi1:normal:iran \
           --seconds 300 --out <scratch>/skirmish
"""
from __future__ import annotations

import argparse
import contextlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART_TOOLS = ROOT.parent / "RTSAI-Art" / "tools"
YIELD = Path(r"C:\Users\Admin\Code\AI\logs\gpu-yield.txt")


def game_lock():
    if (ART_TOOLS / "route_lock.py").exists():
        sys.path.insert(0, str(ART_TOOLS))
        import route_lock
        return route_lock.lock("game-window", timeout=4 * 3600, agent="standalone-smoke")
    return contextlib.nullcontext()


def grab(pid: int, out: Path):
    ps1 = ART_TOOLS / "capture_window.ps1"
    if ps1.exists():
        subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps1),
                        "-ProcessId", str(pid), "-OutFile", str(out)], capture_output=True, timeout=30)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["menu", "skirmish"])
    ap.add_argument("--worktree", type=Path, default=ROOT)
    ap.add_argument("--map", default="tournament-2B")
    ap.add_argument("--bots", default="Multi0:normal:china,Multi1:normal:iran")
    ap.add_argument("--faction", help="the host plays this faction (leave Multi0 out of --bots)")
    ap.add_argument("--seconds", type=int, default=60)
    ap.add_argument("--grab-every", type=float, default=15)
    ap.add_argument("--look", help="X,Y: hold the camera on this cell (look.lua)")
    ap.add_argument("--map-rules", type=Path, help="a MiniYaml rules overlay for this run only (e.g. a showcase)")
    ap.add_argument("--lua", help="like --observe, with another script from tools/standalone-smoke/ (e.g. deploy.lua)")
    ap.add_argument("--observe", action="store_true",
                    help="skirmish on a scratch copy of --map (in the run's support dir) with tools/standalone-smoke/"
                         "observe.lua: camera pans between bot bases, lua.log gets a per-bot actor census")
    ap.add_argument("--set", action="append", default=[], help="extra engine setting, e.g. Game.IntroductionPromptVersion=99")
    ap.add_argument("--mod", default="rtsai", help="mod id to launch (rtsai-classic needs content: not run here)")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()

    engine = a.worktree / "engine"
    out = a.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    support = out / "support"
    if support.exists():
        shutil.rmtree(support)   # our own scratch: created below, never contains links
    support.mkdir()
    assert not (support / "Content").exists()

    args = ["dotnet", str(engine / "bin" / "OpenRA.dll"), f"Engine.EngineDir={engine}",
            f"Engine.ModSearchPaths={a.worktree / 'mods'}", f"Engine.SupportDir={support}", f"Game.Mod={a.mod}",
            "Game.FetchNews=false", "Game.ViewportEdgeScroll=false", "Graphics.Mode=Windowed",
            "Graphics.WindowedSize=1280,800", "Graphics.UIScale=1", "Sound.Mute=true", *a.set]
    launch_map = a.map
    script = a.lua or ("observe.lua" if a.observe else None) or ("look.lua" if a.look else None)
    if a.mode == "skirmish" and script:
        import re
        version = re.search(r"^\s*Version: (.+)$", (a.worktree / "mods/rtsai/mod.yaml").read_text(encoding="utf-8"), re.M)[1]
        dst = support / "maps" / "rtsai" / version.strip() / "sa-observe"
        src = next(d / a.map for d in (a.worktree / "mods/rtsai/maps", a.worktree / "mods/rtsai/standalone/maps", a.worktree / "mods/rtsai-classic/maps") if (d / a.map).exists())
        shutil.copytree(src, dst)   # a classic (Westwood) map only ever lands in this scratch support dir
        lua = (ROOT / "tools/standalone-smoke" / script).read_text(encoding="utf-8")
        if a.look:
            lx, ly = a.look.split(",")
            lua = lua.replace("__LOOK_X__", lx.strip()).replace("__LOOK_Y__", ly.strip())
        (dst / "observe.lua").write_text(lua, encoding="utf-8")
        y = (dst / "map.yaml").read_text(encoding="utf-8").replace("\r\n", "\n").rstrip("\n")
        y = re.sub(r"\nRules:.*\Z", "", y, flags=re.S)   # the shipped maps end with an empty Rules: block
        y += "\nRules:\n\tWorld:\n\t\tLuaScript:\n\t\t\tScripts: observe.lua\n"
        if a.map_rules:
            extra = a.map_rules.read_text(encoding="utf-8").replace("\r\n", "\n").strip("\n")
            y += "".join(f"\t{line}\n" for line in extra.split("\n"))
        (dst / "map.yaml").write_text(y, encoding="utf-8")
        launch_map = "sa-observe"
    if a.mode == "skirmish":
        args += [f"Launch.Map={launch_map}", f"Launch.Bots={a.bots}"]
        if a.faction:
            args.append(f"Launch.Faction={a.faction}")
    env = {k: v for k, v in os.environ.items() if not k.startswith(("OPENRA_AI_", "RTSAI_"))}
    env.update(OPENRA_AI_HOST="0", OPENRA_AI_COMPANION="0", OPENRA_AI_DISABLE_AUTOSTART="1", OPENRA_DISPLAY_SCALE="1")

    report = {"mode": a.mode, "args": args[2:], "grabs": []}
    with game_lock():
        if YIELD.parent.exists():
            with YIELD.open("a", encoding="utf-8") as y:
                y.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S%z')} RTS AI standalone boot test ({a.mode}): short windowed "
                        f"OpenRA run, up to {max(1, round(a.seconds / 60))} min, display rendering only\n")
        t0 = time.time()
        with (out / "stdout.log").open("w", encoding="utf-8") as log:
            p = subprocess.Popen(args, cwd=engine / "bin", env=env, stdout=log, stderr=subprocess.STDOUT)
            k, nxt = 0, a.grab_every
            while p.poll() is None and time.time() - t0 < a.seconds:
                time.sleep(0.5)
                if time.time() - t0 >= nxt:
                    k += 1
                    nxt += a.grab_every
                    f = out / f"window-{k:02d}-{int(time.time() - t0):03d}s.png"
                    grab(p.pid, f)
                    if f.exists():
                        report["grabs"].append(f.name)
            report["exited_early"] = p.poll() is not None
            report["exit_code"] = p.poll()
            if p.poll() is None:
                p.kill()
                p.wait(timeout=20)
        report["seconds"] = round(time.time() - t0, 1)

    logs = support / "Logs"
    report["logs"] = sorted(f.name for f in logs.glob("*")) if logs.exists() else []
    for name in ["exception.log", "debug.log", "perf.log", "client.log", "server.log"]:
        f = logs / name
        if f.exists():
            text = f.read_text(encoding="utf-8", errors="replace")
            report[name] = {"lines": len(text.splitlines()), "tail": text.splitlines()[-25:]}
    lua = logs / "lua.log"
    if lua.exists():
        lines = lua.read_text(encoding="utf-8", errors="replace").splitlines()
        report["lua"] = [ln.split("] ", 1)[-1] for ln in lines if "CENSUS|" in ln or "PLAYER|" in ln or "rror" in ln]
    snd = logs / "sound.log"
    if snd.exists():
        report["missing_sounds"] = sorted({ln.split(": ", 1)[-1] for ln in snd.read_text(errors="replace").splitlines()
                                           if "does not exist" in ln})
    reps = list((support / "Replays").rglob("*.orarep")) if (support / "Replays").exists() else []
    report["replays"] = [{"file": r.name, "bytes": r.stat().st_size} for r in reps]
    (out / "report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("mode", "seconds", "exited_early", "exit_code", "grabs", "logs", "replays")},
                     indent=1))


if __name__ == "__main__":
    main()
