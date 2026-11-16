#!/usr/bin/env python3
"""Exercise the installed Mac Library buttons and desktop Library return.

The recovery hook invokes each real native button callback. These checks launch
windows but send no mouse or keyboard events. All support files stay in a fresh
directory; cleanup targets only the processes started by this invocation.
"""

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import tempfile
import time


def process_table():
    output = subprocess.check_output(
        ["ps", "-axo", "pid=,ppid=,stat=,command="], text=True
    )
    result = {}
    for line in output.splitlines():
        fields = line.strip().split(None, 3)
        if len(fields) == 4:
            result[int(fields[0])] = (int(fields[1]), fields[2], fields[3])
    return result


def alive(pid, table):
    return pid in table and not table[pid][1].startswith("Z")


def cleanup(owned, app):
    # Stop Cocoa launchers first, so terminating their test engines does not
    # leave a fatal-error alert. Never signal a pre-existing app instance.
    table = process_table()
    ordered = sorted(owned, key=lambda pid: "apphost-" in table.get(pid, (0, "", ""))[2])
    for pid in ordered:
        if alive(pid, table) and str(app) in table[pid][2]:
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
    deadline = time.monotonic() + 4
    while time.monotonic() < deadline:
        table = process_table()
        if not any(alive(pid, table) for pid in owned):
            return
        time.sleep(0.2)
    for pid in owned:
        if alive(pid, table) and str(app) in table[pid][2]:
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass


def run_case(args, name, source, target, hook, installed=False):
    work = args.output / name
    work.mkdir()
    support = work / "support"
    support.mkdir()
    if installed:
        shutil.copytree(args.classic_content / "ra" / "v2", support / "Content" / "ra" / "v2")
    env = {key: value for key, value in os.environ.items()
           if not key.startswith(("OPENRA_AI_", "RTSAI_LIBRARY_", "RTSAI_RECOVERY_"))}
    env.update({
        "RTSAI_RECOVERY_SCREEN": hook,
        "RTSAI_LIBRARY_SUPPORT": str(support),
        # This test exercises navigation, with no sidecar or model downloads.
        "OPENRA_AI_COMPANION": "1",
        "OPENRA_AI_COMPANION_READY": "0",
        "OPENRA_AI_STARTUP_ENABLED": "0",
    })
    command = [str(args.app / "Contents/MacOS/Launcher"),
               "Game.Mod=" + source, "Engine.SupportDir=" + str(support),
               "Game.IntroductionPromptVersion=99", "Debug.SystemInformationVersionPrompt=99",
               "Game.FetchNews=false", "Sound.Mute=true", "Graphics.Mode=Windowed",
               "Graphics.WindowedSize=1152,720"]
    log = work / "handoff.log"
    receipt = {"case": name, "source": source, "target": target,
               "hook": hook, "command": command, "log": str(log)}
    owned = set()
    process = None
    try:
        with log.open("w") as stream:
            process = subprocess.Popen(command, cwd=args.app / "Contents/Resources",
                                       env=env, stdout=stream, stderr=subprocess.STDOUT)
            owned.add(process.pid)
            deadline = time.monotonic() + args.timeout
            stable_since = None
            child = None
            marker = ("RTSAI_LIBRARY|library" if target == "rtsai-library" else
                      "Loading mod: rtsai-classic-content" if target == "rtsai-classic-content" else
                      "RTSAI_NATIVE_SCREEN|home|" + target)
            while time.monotonic() < deadline:
                table = process_table()
                changed = True
                while changed:
                    descendants = {pid for pid, row in table.items() if row[0] in owned}
                    changed = not descendants.issubset(owned)
                    owned.update(descendants)
                text = log.read_text(errors="replace")
                game_id = "rtsai-classic-core" if target == "rtsai-classic-content" else target
                match = re.search(r"RTSAI_LIBRARY_CHILD\|" + re.escape(game_id) + r"\|(\d+)", text)
                if match:
                    child = int(match.group(1))
                    owned.add(child)
                    receipt["child_pid"] = child
                if "Failed to load Game.Mod=" in text:
                    raise RuntimeError("Mac apphost was invoked without its runtime preamble")
                if child and not alive(child, table):
                    raise RuntimeError("Target game exited before the survival check completed")
                if child and marker in text:
                    stable_since = stable_since or time.monotonic()
                    if time.monotonic() - stable_since >= args.seconds:
                        receipt.update({"passed": True, "marker": marker,
                                        "alive_after_marker_seconds": args.seconds,
                                        "child_command": table[child][2]})
                        break
                if not any(alive(pid, table) for pid in owned):
                    raise RuntimeError("Library and child exited before the target menu was ready")
                time.sleep(0.25)
            else:
                raise RuntimeError("Timed out waiting for child marker: " + marker)
            exceptions = []
            for path in support.rglob("*.log"):
                if "Exception" in path.read_text(errors="replace"):
                    exceptions.append(str(path))
            if exceptions:
                raise RuntimeError("Exception in private logs: " + ", ".join(exceptions))
    except Exception as error:
        receipt.update({"passed": False, "error": str(error)})
    finally:
        cleanup(owned, args.app)
        if process:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass
    (work / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(("PASS " if receipt["passed"] else "FAIL ") + name, flush=True)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("app", type=Path, help="Installed RTS AI.app from the exact release DMG")
    parser.add_argument("--output", type=Path, help="New directory for isolated support files and receipts")
    parser.add_argument("--classic-content", type=Path, help="Content directory holding freeware ra/v2")
    parser.add_argument("--seconds", type=float, default=10, help="Required survival after target menu marker")
    parser.add_argument("--timeout", type=float, default=90)
    args = parser.parse_args()
    args.app = args.app.resolve()
    if not (args.app / "Contents/MacOS/Launcher").is_file():
        parser.error("app must contain Contents/MacOS/Launcher")
    if args.seconds <= 0 or args.timeout <= args.seconds:
        parser.error("timeout must exceed the positive survival duration")
    if args.classic_content:
        args.classic_content = args.classic_content.resolve()
        if not (args.classic_content / "ra/v2").is_dir():
            parser.error("classic-content must hold ra/v2")
    if args.output:
        args.output = args.output.resolve()
        args.output.mkdir(parents=True, exist_ok=False)
    else:
        args.output = Path(tempfile.mkdtemp(prefix="rtsai-library-handoff-"))
    cases = [
        ("classic-fresh-installer", "rtsai-library", "rtsai-classic-content", "library-open-rtsai-classic-core", False),
        ("library-to-ra2", "rtsai-library", "rtsai-ra2", "library-open-rtsai-ra2", False),
        ("library-to-rts", "rtsai-library", "rtsai", "library-open-rtsai", False),
        ("ra2-to-library", "rtsai-ra2", "rtsai-library", "switch-ra2", False),
        ("rts-to-library", "rtsai", "rtsai-library", "switch-ra2", False),
    ]
    if args.classic_content:
        cases.extend([
            ("classic-installed-menu", "rtsai-library", "rtsai-classic-core", "library-open-rtsai-classic-core", True),
            ("classic-to-library", "rtsai-classic-core", "rtsai-library", "switch-ra2", True),
        ])
    results = [run_case(args, *case) for case in cases]
    report = {"app": str(args.app), "gui": True, "cases": results,
              "classic_installed_checks": bool(args.classic_content),
              "passed": all(case["passed"] for case in results)}
    (args.output / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Receipts: " + str(args.output / "results.json"))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
