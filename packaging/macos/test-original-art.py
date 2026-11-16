#!/usr/bin/env python3
"""Guard native art scope, fresh baselines and repeatable packaging transforms."""
from pathlib import Path
import runpy
import subprocess
import sys
import types
import unittest

HERE = Path(__file__).resolve().parent
HELPER = HERE / 'prepare-original-art.py'
helper = runpy.run_path(str(HELPER))
sys.path.insert(0, str(HERE.parents[2] / 'RTSAI-WebGame/tools'))
import ea_originals as E


class OriginalArtScope(unittest.TestCase):
    def test_simulation_trait_is_rejected(self):
        baseline = E.merge([E.parse('tank:\n\tHealth:\n\t\tHP: 100\n')])
        generator = types.SimpleNamespace(rules_nodes=E.parse('tank:\n\tHealth:\n\t\tHP: 999\n'))
        with self.assertRaisesRegex(ValueError, 'Non-render'):
            helper['render_rules'](generator, E, baseline)

    def test_planning_buildable_does_not_reintroduce_native_production(self):
        baseline = E.merge([E.parse('tank:\n\tHealth:\n\t\tHP: 100\n')])
        generator = types.SimpleNamespace(rules_nodes=E.parse(
            'tank:\n\tBuildable:\n\t\tQueue: Vehicle\n\t\tPrerequisites: planned-only\n\t\tIconPalette: eacameo\n'))
        nodes, _ = helper['render_rules'](generator, E, baseline)
        self.assertEqual(nodes, [])
        self.assertIsNone(baseline['tank'].get('Buildable'))

    def test_native_baseline_does_not_use_mutated_generator_current_rules(self):
        baseline = E.merge([E.parse('tank:\n\tHealth:\n\t\tHP: 100\n\tRenderSprites:\n\t\tImage: project\n')])
        generator = types.SimpleNamespace(
            cur=E.merge([E.parse('tank:\n\tHealth:\n\t\tHP: 999\n')]),
            rules_nodes=E.parse('tank:\n\tRenderSprites:\n\t\tFactionImages:\n\t\t\tamerica: ea-tank\n'))
        nodes, _ = helper['render_rules'](generator, E, baseline)
        self.assertEqual(nodes[0].get('RenderSprites').get('FactionImages').val('america'), 'ea-tank')
        self.assertEqual(baseline['tank'].get('Health').val('HP'), '100')

    def test_missing_native_prism_charge_state_only_changes_render_conditions(self):
        baseline = E.merge([E.parse('sref:\n\tHealth:\n\t\tHP: 150\n')])
        generator = types.SimpleNamespace(rules_nodes=E.parse(
            'sref:\n\tWithVoxelTurret:\n\t\tRequiresCondition: ea-art && (!turretcharge)\n'
            '\tWithVoxelTurret@stage1:\n\t\tRequiresCondition: ea-art && (turretcharge == 1)\n'))
        nodes, _ = helper['render_rules'](generator, E, baseline)
        self.assertEqual(nodes[0].get('WithVoxelTurret').val('RequiresCondition'), 'ea-art')
        self.assertEqual(nodes[0].get('WithVoxelTurret@stage1').val('RequiresCondition'), 'false')
        self.assertEqual(baseline['sref'].get('Health').val('HP'), '150')
        self.assertFalse(any(t.key.startswith('GrantConditionOnAttack') for t in nodes[0].children))

    def test_unused_inherited_crane_render_grant_is_removed(self):
        raw = [E.parse('shad:\n\tHealth:\n\t\tHP: 100\n\tWithFacingSpriteBody:\n\t\tRequiresCondition: airborne\n'
                       'r2crane:\n\tInherits: shad\n\tWithFacingSpriteBody:\n\t\tRequiresCondition: airborne\n')]
        baseline = E.merge(raw)
        generator = types.SimpleNamespace(rules_nodes=E.parse(
            'shad:\n\tGrantConditionOnFaction@ea-art:\n\t\tCondition: ea-art\n\t\tFactions: ' + ', '.join(E.COUNTRIES) +
            '\n\tWithFacingSpriteBody:\n\t\tRequiresCondition: ea-art\n'))
        nodes, _ = helper['render_rules'](generator, E, baseline, raw)
        effective = E.merge(raw + [nodes])
        self.assertIsNone(effective['r2crane'].get('GrantConditionOnFaction@ea-art'))
        self.assertIsNotNone(effective['shad'].get('GrantConditionOnFaction@ea-art'))

    def test_packaging_is_idempotent(self):
        before = '\t\tSupportPowers@SUPPORT_PALETTE:\n\t\t\tX: 10\n'
        once = helper['power_widget_chrome'](before)
        self.assertEqual(helper['power_widget_chrome'](once), once)
        self.assertNotIn('OriginalOriginal', once)
        yaml = 'Rules:\n\ta.yaml\n\nSequences:\n\ts.yaml\n'
        once = helper['append_section'](yaml, 'Rules', 'native.yaml')
        self.assertEqual(helper['append_section'](once, 'Rules', 'native.yaml'), once)

    def test_missing_power_widget_fails_instead_of_shipping_an_unused_adapter(self):
        with self.assertRaisesRegex(ValueError, 'binding is missing'):
            helper['power_widget_chrome']('Container@OTHER_PANEL:\n')

    def test_optimization_cannot_disable_integrity_rejection(self):
        code = f"import runpy; runpy.run_path({str(HELPER)!r})['require'](False, 'integrity-sentinel')"
        result = subprocess.run([sys.executable, '-O', '-c', code], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('ValueError: integrity-sentinel', result.stderr)


if __name__ == '__main__':
    unittest.main()
