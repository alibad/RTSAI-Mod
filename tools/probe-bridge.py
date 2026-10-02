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
    bridge.close()
    return 0


def _status_kwargs(bridge) -> dict:
    import inspect

    params = inspect.signature(bridge.update_companion_status).parameters
    values = {"state": "ready", "message": "probe from RTSAI-Mod spike", "detail": "spike"}
    return {k: v for k, v in values.items() if k in params}


if __name__ == "__main__":
    raise SystemExit(main())
