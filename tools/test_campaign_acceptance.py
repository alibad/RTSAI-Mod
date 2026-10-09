"""Regression checks for the campaign acceptance fixtures and outcome gate."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("acceptance", Path(__file__).with_name("campaign-acceptance.py"))
acceptance = importlib.util.module_from_spec(spec)
spec.loader.exec_module(acceptance)


class CampaignAcceptanceTests(unittest.TestCase):
    def test_importer_preserves_the_validated_controller(self):
        spec = importlib.util.spec_from_file_location("importer", Path(__file__).with_name("import-shared-campaigns.py"))
        importer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(importer)
        outputs = {}
        importer.write = lambda path, text: outputs.update({path: text})
        importer.controller()
        path = acceptance.ROOT / "OpenRA.Mods.RTSAI/Traits/RTSAICampaign.cs"
        self.assertEqual(outputs[path].replace("\r\n", "\n"), path.read_text(encoding="utf-8").replace("\r\n", "\n"))

    def test_preserves_production_rules_and_adds_observer(self):
        text = "Rules:\n\tWorld:\n\t\tRTSAICampaign:\n\t\t\tMission: test\n\tPlayer:\n\t\t-ConquestVictoryConditions:\n"
        result = acceptance.fixture_yaml("MapFormat: 11\n" + text)
        self.assertIn("\t\tRTSAICampaign:\n\t\t\tMission: test", result)
        self.assertIn("\t\t-ConquestVictoryConditions:", result)
        self.assertEqual(result.count("\t\tScriptTriggers:"), 2)

    def test_rejects_existing_script_instead_of_erasing_it(self):
        with self.assertRaises(ValueError):
            acceptance.fixture_yaml("Rules:\n\tWorld:\n\t\tLuaScript:\n\t\tRTSAICampaign:\n")

    def test_victory_with_unresolved_secondary_is_not_accepted(self):
        mission = {"objectives": [{"kind": "destroy", "targets": ["enemy"]},
                                  {"kind": "protect", "secondary": True, "targets": ["depot"]}]}
        case = {"expected": "won"}
        self.assertFalse(acceptance.objective_statuses_pass(mission, case, ["complete|0|10", "outcome|won|10"]))
        self.assertTrue(acceptance.objective_statuses_pass(mission, case, ["complete|1|10", "complete|0|10"]))
        self.assertTrue(acceptance.objective_statuses_pass(mission, {"expected": "won", "kill": "depot"},
                                                        ["failed|1|10", "complete|0|10"]))


if __name__ == "__main__":
    unittest.main()
