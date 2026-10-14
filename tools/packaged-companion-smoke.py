"""Exercise native game -> frozen companion -> cached local models in a fresh support directory.

The caller seeds the installed companion's verified AI pack and selects local mode first.
No public service, microphone, model download or gameplay order is used.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import time
import urllib.request


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--install", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    install, out = args.install.resolve(), args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    support = out / "support"
    support.mkdir()
    env = {k: v for k, v in os.environ.items() if not k.startswith(("OPENRA_AI_", "RTSAI_"))}
    env.update(OPENRA_AI_TTS_VOICE="onyx", OPENRA_AI_AUTO_INSTALL_VOICE="0")
    binary = install / "RTSAI.exe"
    command = [str(binary), f"Engine.LaunchPath={binary}", f"Engine.EngineDir={install}",
               f"Engine.ModSearchPaths={install / 'mods'}", f"Engine.SupportDir={support}", "Game.Mod=rtsai",
               "Game.FetchNews=false", "Graphics.Mode=Windowed", "Graphics.WindowedSize=1280,800", "Sound.Mute=true",
               "Game.IntroductionPromptVersion=99", "Debug.SystemInformationVersionPrompt=99",
               "Launch.Map=twin-fords", "Launch.Faction=china", "Launch.Bots=Multi1:normal:iran"]
    result = {"scope": "Installed desktop game with offline-seeded local AI pack and fresh support directory", "passed": False}
    with (out / "stdout.log").open("w", encoding="utf-8") as log:
        process = subprocess.Popen(command, cwd=install, env=env, stdout=log, stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic() + 150
            console = None
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError("Installed game exited before companion readiness")
                companion_log = support / "Logs/companion.log"
                text = companion_log.read_text(encoding="utf-8", errors="replace") if companion_log.exists() else ""
                ports = re.search(r"bridge (\d+), console (\d+), gateway (\d+)", text)
                if ports:
                    console = f"http://127.0.0.1:{ports[2]}"
                    try:
                        with urllib.request.urlopen(console + "/health", timeout=2) as response:
                            health = json.load(response)
                        if health.get("control_ready") and health.get("has_snapshot") and health.get("router", {}).get("reachable"):
                            break
                    except (OSError, ValueError):
                        pass
                time.sleep(1)
            else:
                raise TimeoutError("Native companion did not become ready with a live game snapshot")

            def post(path, body):
                req = urllib.request.Request(console + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=90) as response:
                    return json.load(response)

            post("/v1/control", {"enabled": True, "muted": True, "auto_act_enabled": False})
            response = post("/v1/ask", {"question": "What should I build first?"})
            assert response.get("text"), response
            result.update(control_ready=True, live_snapshot=True, local_router_reachable=True,
                          reply=response["text"], source=response.get("source"), passed=True)
            capture = Path(__file__).resolve().parents[2] / "RTSAI-Art/tools/capture_window.ps1"
            if capture.exists():
                subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(capture),
                                "-ProcessId", str(process.pid), "-OutFile", str(out / "native-companion.png")], capture_output=True, timeout=30)
        except Exception as error:
            result["failure"] = str(error)
            raise
        finally:
            if process.poll() is None:
                subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            (out / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
            print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
