import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('unit_content', Path(__file__).with_name('unit-content.py'))
unit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(unit)


class UnitContentTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / 'content').mkdir()
        for name in ['unit-bindings.json', 'shared-content.json']:
            shutil.copyfile(unit.ROOT / 'content' / name, self.root / 'content' / name)
        (self.root / unit.SOURCE).write_text(json.dumps({'schema': 1, 'units': {}}))
        for mod in set(unit.MODS.values()):
            targets = [t for t, m in unit.MODS.items() if m == mod]
            path = self.root / 'mods' / mod / 'mod.yaml'
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('Metadata:\n\tTitle: fixture\nRules:\n' + ''.join(f'\tra2|unit-overrides/{target}.yaml\n' for target in targets) + '\nSequences:\n')
        unit.compile_content(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def edit(self, key, values, revision=None):
        return unit.edit(self.root, {'unit': key, 'values': values, 'baseRevision': revision or unit.state(self.root)[2]})

    def test_mode_isolation_three_stats_and_reversible_history(self):
        before = unit.state(self.root)[2]
        result = self.edit('ra2:engineer', {'cost': 700, 'health': 12000, 'speed': 72})
        self.assertEqual(result['targets']['ra2-desktop']['effective'], dict(cost=700, health=12000, speed=72))
        self.assertEqual(result['targets']['ra2-web']['effective'], result['targets']['ra2-desktop']['effective'])
        self.assertEqual(unit.view(self.root, 'classic:e6')['targets']['classic-desktop']['effective']['cost'], 625)
        self.assertTrue((self.root / f'content/unit-revisions/{before}.json').is_file())
        self.assertNotIn('Cost:', (self.root / unit.OUTPUT / 'classic-desktop.yaml').read_text())
        result = self.edit('ra2:engineer', {})
        self.assertEqual(result['revision'], before)
        self.assertEqual(result['targets']['ra2-web']['effective']['cost'], 625)

    def test_every_classic_unit_has_identical_native_and_web_bindings(self):
        result = self.edit('classic:e6', {'cost': 650, 'health': 14000})
        self.assertEqual(result['targets']['classic-desktop']['effective']['cost'], 650)
        self.assertEqual(result['targets']['classic-web']['effective']['health'], 14000)
        other = next(key for key in unit.load(self.root / unit.REGISTRY)['units'] if key.startswith('classic:') and key != 'classic:e6')
        for key, entry in unit.load(self.root / unit.REGISTRY)['units'].items():
            if key.startswith('classic:'):
                self.assertEqual(entry['bindings']['classic-desktop'], entry['bindings']['classic-web'], key)
        self.assertEqual(self.edit(other, {'cost': 375})['targets']['classic-web']['effective']['cost'], 375)

    def test_invalid_fields_units_values_and_stale_writes_preserve_source(self):
        before = (self.root / unit.SOURCE).read_bytes()
        for key, values in [('ra2:../bad', {'cost': 700}), ('ra2:engineer', {'path': 1}),
                            ('ra2:engineer', {'cost': True}), ('ra2:engineer', {'health': 0}),
                            ('ra2:engineer', {'speed': 1.5}), ('ra2:engineer', {'speed': 1001})]:
            with self.assertRaises(ValueError):
                self.edit(key, values)
            self.assertEqual((self.root / unit.SOURCE).read_bytes(), before)
        with self.assertRaises(ValueError):
            self.edit('ra2:engineer', {'cost': 700}, '0' * 64)
        path = self.root / 'mods/rtsai/mod.yaml'
        path.write_text('Rules:\n\nSequences:\n')
        with self.assertRaises(ValueError):
            self.edit('ra2:engineer', {'cost': 700})
        self.assertEqual((self.root / unit.SOURCE).read_bytes(), before)

    def test_inherited_classic_stats_follow_real_rules_and_child_override_wins(self):
        result = self.edit('classic:e1', {'health': 6000, 'speed': 60})
        child = unit.view(self.root, 'classic:trrifle')
        self.assertEqual(child['targets']['classic-web']['effective']['speed'], 60)
        self.assertEqual(child['targets']['classic-web']['effective']['health'], 6200)
        self.assertIn('classic:trrifle', [u['key'] for u in result['relatedUnits']])
        self.assertEqual(self.edit('classic:trrifle', {'speed': 67})['targets']['classic-web']['effective']['speed'], 67)
        self.edit('classic:e1', {})
        self.assertEqual(unit.view(self.root, 'classic:trrifle')['targets']['classic-web']['effective']['speed'], 67)

    def test_all_classic_roster_stats_compile_to_both_targets_without_touching_rules(self):
        registry = unit.load(self.root / unit.REGISTRY)['units']
        edits = {key: {field: value + 1 for field, value in entry['bindings']['classic-desktop']['baseline'].items() if value is not None}
                 for key, entry in registry.items() if key.startswith('classic:')}
        unit.atomic(self.root / unit.SOURCE, json.dumps({'schema': 1, 'units': edits}))
        files, _ = unit.compiled(self.root)
        self.assertEqual(files[unit.OUTPUT / 'classic-desktop.yaml'], files[unit.OUTPUT / 'classic-web.yaml'])
        self.assertGreater(len(edits), 0)
        for key in edits:
            self.assertIn(registry[key]['bindings']['classic-web']['actor'] + ':\n', files[unit.OUTPUT / 'classic-web.yaml'])

    def test_full_rules_clone_weapons_and_keep_other_units_and_modes(self):
        detail = {'actor':'Armor:\n\tType: Light\nBuildable:\n\tBuildDuration: 90\n',
          'weapons':{'Armament@PRIMARY':{'base':'M1Carbine','rules':'Range: 6c0\nReloadDelay: 16\nWarhead@1Dam: SpreadDamage\n\tDamage: 18\n'}}}
        before = unit.state(self.root)[2]
        with patch.object(unit.details, 'check_engine'):
            result = unit.edit(self.root, {'unit':'classic:e1','values':{'cost':105},'details':detail,'baseRevision':before})
        files, manifest = unit.compiled(self.root)
        self.assertNotEqual(before, manifest['revision'])
        self.assertIn('Weapon: studio_classic_e1_armament_primary',files[unit.OUTPUT/'classic-web.yaml'])
        self.assertIn('Inherits: M1Carbine', files[unit.OUTPUT/'classic-web-weapons.yaml'])
        self.assertNotIn('Range: 6c0', files[unit.OUTPUT/'ra2-web-weapons.yaml'])
        self.assertEqual(manifest['details']['classic:e1'],detail)
        # The old stat API must retain the full rule edits.
        self.edit('classic:e1', {'cost':110})
        self.assertEqual(unit.details.load(self.root)['units']['classic:e1'],detail)
        rows=unit.details.history(self.root,'classic:e1')
        self.assertTrue(any(r['values']=={'cost':105} and r['details']==detail for r in rows))
        self.assertTrue(any(r['values']=={} and r['details']=={'actor':'','weapons':{}} for r in rows))

    def test_engine_rejection_rolls_back_all_sources_and_generated_outputs(self):
        source = (self.root/unit.SOURCE).read_bytes()
        files, _ = unit.compiled(self.root)
        detail = {'actor':'NotARealTrait:\n\tValue: 3\n','weapons':{}}
        with patch.object(unit.details,'check_engine', side_effect=ValueError('Engine rejected rules')):
            with self.assertRaisesRegex(ValueError,'Engine rejected'):
                unit.edit(self.root, {'unit':'ra2:e1','values':{'cost':220},'details':detail,'baseRevision':unit.state(self.root)[2]})
        self.assertEqual((self.root/unit.SOURCE).read_bytes(),source)
        self.assertEqual(unit.details.load(self.root)['units'],{})
        for path,text in files.items(): self.assertEqual((self.root/path).read_text(),text)

    def test_advanced_rule_validation_blocks_ambiguous_and_core_stat_overrides(self):
        registry=unit.load(self.root/unit.REGISTRY)
        for actor in ['Inherits: ^SOLDIER\n','Health:\n\tHP: 1\n','Armor:\n\tType: Light\nArmor:\n\tType: Heavy\n','Armor:\n  Type: Light\n']:
            with self.assertRaises(ValueError):
                unit.details.validate({'schema':1,'units':{'classic:e1':{'actor':actor,'weapons':{}}}},registry)


if __name__ == '__main__':
    unittest.main()
