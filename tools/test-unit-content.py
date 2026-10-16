import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

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
        for target, mod in unit.MODS.items():
            path = self.root / 'mods' / mod / 'mod.yaml'
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f'Metadata:\n\tTitle: fixture\nRules:\n\tra2|unit-overrides/{target}.yaml\n\nSequences:\n')
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

    def test_classic_binding_and_unmapped_unit_are_explicit(self):
        result = self.edit('classic:e6', {'cost': 650, 'health': 14000})
        self.assertEqual(result['targets']['classic-desktop']['effective']['cost'], 650)
        self.assertEqual(result['targets']['classic-web']['effective']['health'], 14000)
        other = next(key for key in unit.load(self.root / unit.REGISTRY)['units'] if key.startswith('classic:') and key != 'classic:e6')
        self.assertEqual(list(unit.view(self.root, other)['targets']), ['classic-desktop'])

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


if __name__ == '__main__':
    unittest.main()
