#!/usr/bin/env python3
"""Unit tests for tools/balance-harness.py (no game run). Usage: python tools/test_balance_harness.py"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

spec = importlib.util.spec_from_file_location("balance_harness", Path(__file__).with_name("balance-harness.py"))
bh = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = bh  # dataclasses resolve annotations through sys.modules
spec.loader.exec_module(bh)

MAP_YAML = """MapFormat: 11
RequiresMod: ra2
Title: Test Plains
Tileset: TEMPERATE
MapSize: 64,64
Visibility: Lobby
Players:
\tPlayerReference@Neutral:
\t\tName: Neutral
\t\tOwnsWorld: True
\t\tNonCombatant: True
\t\tFaction: Random
\tPlayerReference@Multi0:
\t\tName: Multi0
\t\tPlayable: True
\t\tFaction: Random
\tPlayerReference@Multi1:
\t\tName: Multi1
\t\tPlayable: True
\t\tFaction: Random
Actors:
\tActor0: mpspawn
\t\tLocation: 10,10
\t\tOwner: Neutral
\tActor1: mpspawn
\t\tLocation: 50,50
\t\tOwner: Neutral
"""

CAMPAIGN = {"name": "test", "seed": 11, "suites": [{
    "id": "rr", "factions": ["china", "iran", "russia"], "bots": ["normal"], "replicates": 2, "tick_cap": 1000,
    "maps": [{"map": "a"}, {"map": "b", "spawns": [2, 1]}]}]}


def sample(tick, player, kills=0, deaths=0):
    return f"sample|{tick}|{player}|0|0|{kills}|{deaths}|0|0|0|0|0|0|0|0|5"


def result_for(match, rows, exit_code=0):
    text = "".join(f"BALANCE|{match.id}|{row}\n" for row in rows)
    telemetry = bh.parse_telemetry(text, match.id)
    outcome = bh.decide_outcome(telemetry, exit_code, "complete", [], [])
    return {"match": match.to_dict(), "status": outcome["status"], "outcome": outcome, "telemetry": telemetry,
            "wall_seconds": 1.0, "exceptions": [], "lua_errors": []}


class HarnessTests(unittest.TestCase):
    def test_plan_is_deterministic_and_orientation_balanced(self):
        matches = bh.plan(CAMPAIGN)
        self.assertEqual(matches, bh.plan(CAMPAIGN))
        self.assertEqual(len(matches), 3 * 2 * 2 * 2)  # pairs x orientations x maps x replicates
        self.assertEqual(len({m.id for m in matches}), len(matches))
        for m in matches:
            twin = [o for o in matches if o.factions == m.factions[::-1] and o.map == m.map and o.replicate == m.replicate]
            self.assertEqual(len(twin), 1)
        self.assertEqual([m.order for m in matches], list(range(len(matches))))
        self.assertTrue(all(m.replicate == 0 for m in matches[:12]))

    def test_map_patch_locks_slots_and_adds_rules(self):
        text = bh.patch_map_yaml(MAP_YAML, ("china", "russia"), (2, 1), "Balance x")
        self.assertIn("\t\tFaction: china\n\t\tLockFaction: True\n\t\tLockSpawn: True\n\t\tSpawn: 2\n", text)
        self.assertIn("\t\tFaction: russia\n\t\tLockFaction: True\n\t\tLockSpawn: True\n\t\tSpawn: 1\n", text)
        self.assertTrue(text.rstrip().endswith("Rules: balance-rules.yaml"))
        self.assertIn("Title: Balance x", text)
        with self.assertRaises(ValueError):
            bh.patch_map_yaml(MAP_YAML, ("china", "russia"), (1, 3), "x")

    def test_manifest_speed_patch_changes_only_default(self):
        manifest = ("GameSpeeds:\n\tDefaultSpeed: default\n\tSpeeds:\n\t\tslower:\n\t\t\tTimestep: 50\n"
                    "\t\tdefault:\n\t\t\tName: n\n\t\t\tTimestep: 40\n\t\t\tOrderLatency: 3\n\t\tfast:\n\t\t\tTimestep: 35\n")
        patched = bh.patch_manifest_speed(manifest)
        self.assertIn("\t\tdefault:\n\t\t\tName: n\n\t\t\tTimestep: 1\n", patched)
        self.assertIn("Timestep: 50", patched)
        self.assertIn("Timestep: 35", patched)

    def test_outcomes_and_summary(self):
        matches = bh.plan(CAMPAIGN)
        m = next(x for x in matches if x.factions == ("china", "russia"))
        header = ["player|0|Multi0|china|1|true", "player|0|Multi1|russia|2|true"]
        win = result_for(m, header + ["produced|300|Multi0|r2cnrifle|Infantry|200", "placed|200|Multi1|napowr|800",
                                      sample(500, "Multi0", 900, 100), "defeated|900|Multi1"])
        self.assertEqual(win["outcome"], {"status": "complete", "result": "win", "winner": "Multi0",
                                          "reason": "conquest", "end_tick": 900})
        draw = result_for(m, header + ["cap|1000|1000"])
        self.assertEqual(draw["outcome"]["reason"], "tick-cap")
        crash = result_for(m, header, exit_code=1)
        self.assertEqual(crash["status"], "crash")
        summary = bh.summarize([win, draw, crash])
        self.assertEqual((summary["complete"], summary["errors"], summary["draws"]["tick-cap"]), (2, 1, 1))
        self.assertEqual(summary["matrix"]["china"]["russia"], {"games": 2, "wins": 1, "draws": 1, "losses": 0, "score": 0.75})
        self.assertEqual(summary["factions"]["china"]["mean_unit_count"], 0.5)
        row = bh.csv_row(win)
        self.assertEqual((row["winner"], row["production_0"], row["structures_1"]), ("china", "r2cnrifle:1", 1))

    def test_rules_overlay(self):
        campaign = {"name": "t", "seed": 1, "suites": [dict(CAMPAIGN["suites"][0], rules=["Player:", "\t-BotDoctrine@china:"])]}
        self.assertTrue(all(m.rules == "Player:\n\t-BotDoctrine@china:\n" for m in bh.plan(campaign)))
        self.assertEqual(bh.plan(CAMPAIGN)[0].rules, "")
        with self.assertRaises(ValueError):
            bh.suite_rules({"rules": ["World:", "\tCrateSpawner:"]})

    def test_wilson_interval(self):
        low, high = bh.wilson(5, 10)
        self.assertAlmostEqual(low, 0.237, places=3)
        self.assertAlmostEqual(high, 0.763, places=3)


if __name__ == "__main__":
    unittest.main()
