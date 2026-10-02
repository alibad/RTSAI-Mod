#!/usr/bin/env python3
"""Probe the mod-hosted companion gRPC bridge with the product's Python client.

Imports OpenRA-AI/services/companion (read-only) and issues real RPCs against a
running `Game.Mod=rtsai` instance started with OPENRA_AI_COMPANION=1.

Usage (with a Python that has grpcio + protobuf, e.g. OpenRA-AI/.venv):
  python tools/probe-bridge.py [--address 127.0.0.1:9998] [--product ../OpenRA-AI] [--wait 90] [--samples 3]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--address", default="127.0.0.1:9998")
    parser.add_argument("--product", type=Path, default=ROOT.parent / "OpenRA-AI")
    parser.add_argument("--wait", type=float, default=90.0, help="seconds to wait for the first observation")
    parser.add_argument("--samples", type=int, default=3)
    parser.add_argument("--interval", type=float, default=5.0)
    parser.add_argument("--deploy-mcv", action="store_true", help="ExecuteCompanionActions: deploy the first MCV, then re-observe")
    parser.add_argument("--frame", type=Path, help="also call CaptureCompanionFrame and save the PNG here")
    args = parser.parse_args()

    sys.path.insert(0, str(args.product / "services/companion/src"))
    from openra_ai_companion.bridge import OpenRABridge  # noqa: E402

    bridge = OpenRABridge(args.address, timeout=5.0)
    deadline = time.monotonic() + args.wait
    started = time.monotonic()
    last_error = None
    while time.monotonic() < deadline:
        try:
            snapshot = bridge.observe()
            break
        except RuntimeError as exc:
            last_error = exc
            time.sleep(1.0)
    else:
        print(json.dumps({"ok": False, "error": str(last_error)}))
        return 1

    print(json.dumps({"rpc": "Observe", "first_response_after_s": round(time.monotonic() - started, 1)}))
    for i in range(args.samples):
        if i:
            time.sleep(args.interval)
            snapshot = bridge.observe()
        print(json.dumps({
            "rpc": "Observe",
            "tick": snapshot.tick,
            "map": snapshot.map_name,
            "cash": snapshot.cash,
            "units": len(snapshot.units),
            "buildings": len(snapshot.buildings),
            "unit_types": sorted({u.kind for u in snapshot.units})[:8],
            "building_types": sorted({b.kind for b in snapshot.buildings})[:8],
        }))

    state = bridge.state()
    print(json.dumps({"rpc": "GetState", "keys": sorted(state)[:12]}))
    accepted = bridge.update_companion_status(**_status_kwargs(bridge))
    print(json.dumps({"rpc": "UpdateCompanionStatus", "accepted": accepted}))
    if args.deploy_mcv:
        from openra_ai_companion.models import ActionCommand  # noqa: E402

        snapshot = bridge.observe()
        mcv = next(u for u in snapshot.units if u.kind.endswith("mcv"))
        receipt = bridge.execute_actions("spike-deploy-1", snapshot.tick, (ActionCommand("deploy", actor_id=mcv.actor_id),))
        print(json.dumps({"rpc": "ExecuteCompanionActions", "accepted": receipt.accepted, "tick": receipt.game_tick,
                          "detail": receipt.detail, "results": list(receipt.results)[:2]}))
        for _ in range(30):
            time.sleep(1.0)
            after = bridge.observe()
            if after.buildings:
                break
        print(json.dumps({"rpc": "Observe", "tick": after.tick, "units": sorted(u.kind for u in after.units),
                          "buildings": sorted(b.kind for b in after.buildings)}))

    if args.frame:
        frame = bridge.capture_frame()
        args.frame.write_bytes(frame.png)
        print(json.dumps({"rpc": "CaptureCompanionFrame", **frame.metadata(), "bytes": len(frame.png), "saved": str(args.frame)}))
    bridge.close()
    return 0


def _status_kwargs(bridge) -> dict:
    import inspect

    params = inspect.signature(bridge.update_companion_status).parameters
    values = {"state": "ready", "message": "probe from RTSAI-Mod spike", "detail": "spike"}
    return {k: v for k, v in values.items() if k in params}


if __name__ == "__main__":
    raise SystemExit(main())
