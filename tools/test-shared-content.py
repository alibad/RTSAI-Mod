import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('shared_content', Path(__file__).with_name('shared-content.py'))
shared = importlib.util.module_from_spec(spec)
spec.loader.exec_module(shared)


class SharedContentTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / shared.SOURCE).parent.mkdir(parents=True)
        shutil.copyfile(shared.ROOT / shared.SOURCE, self.root / shared.SOURCE)
        data = shared.read(self.root)
        data['entities']['engineer']['cost'] = None
        (self.root / shared.SOURCE).write_text(json.dumps(data))
        for key, (mod, _, _) in shared.TARGETS.items():
            path = self.root / 'mods' / mod / 'mod.yaml'
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f'Metadata:\n\tTitle: fixture\nRules:\n\tra2|shared-content/{key}.yaml\n\nSequences:\n')

    def tearDown(self):
        self.temp.cleanup()

    def test_one_edit_compiles_all_targets_and_restores_distinct_baselines(self):
        baseline = shared.compile_content(self.root)
        edited = shared.edit(self.root, baseline['revision'], 625)
        self.assertEqual([t['cost'] for t in edited['targets'].values()], [625] * 4)
        for target in edited['targets']:
            self.assertIn('Cost: 625', (self.root / shared.OUTPUT / f'{target}.yaml').read_text())
        self.assertTrue((self.root / f"content/revisions/{baseline['revision']}.json").exists())
        restored = shared.edit(self.root, edited['revision'], None)
        self.assertEqual(restored['revision'], baseline['revision'])
        self.assertEqual([t['cost'] for t in restored['targets'].values()], [400, 500, 500, 500])

    def test_conflicts_invalid_values_and_lock_do_not_overwrite(self):
        baseline = shared.compile_content(self.root)
        source = (self.root / shared.SOURCE).read_bytes()
        for cost in (True, -1, 0, 1.5, '625', 100001):
            with self.assertRaises(ValueError):
                shared.edit(self.root, baseline['revision'], cost)
            self.assertEqual((self.root / shared.SOURCE).read_bytes(), source)
        with self.assertRaises(ValueError):
            shared.edit(self.root, '0' * 64, 625)
        (self.root / 'content/shared-content.lock').touch()
        with self.assertRaises(ValueError):
            shared.edit(self.root, baseline['revision'], 625)
        self.assertEqual((self.root / shared.SOURCE).read_bytes(), source)

    def test_tampered_outputs_bindings_and_missing_manifest_include_fail(self):
        baseline = shared.compile_content(self.root)
        (self.root / shared.OUTPUT / 'classic-web.yaml').write_text('tampered')
        with self.assertRaises(ValueError):
            shared.compile_content(self.root, check=True)
        shared.compile_content(self.root)
        path = self.root / 'mods/rtsai/mod.yaml'
        path.write_text('Rules:\n\nSequences:\n')
        with self.assertRaises(ValueError):
            shared.edit(self.root, baseline['revision'], 625)
        self.assertEqual(shared.revision(shared.read(self.root)), baseline['revision'])
        bad = shared.read(self.root)
        bad['entities']['engineer']['bindings']['ra2-web']['actor'] = '../anything'
        with self.assertRaises(ValueError):
            shared.compiled(bad)


if __name__ == '__main__':
    unittest.main()
