#!/usr/bin/env python3
"""Safety regressions for no-overwrite, tamper detection and current-source freeze."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('build_inputs',Path(__file__).with_name('build-inputs.py'))
inputs=importlib.util.module_from_spec(spec);spec.loader.exec_module(inputs)

class FrozenInputs(unittest.TestCase):
    def test_detects_changed_missing_and_extra_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); (root/'source.cs').write_text('current main source')
            (root/'nested').mkdir();(root/'nested/INPUTS.json').write_text('nested source must also be hashed')
            value=inputs.manifest(root,{'kind':'fixture'})
            self.assertEqual(len(value['files']),2);inputs.check(root)
            (root/'source.cs').write_text('changed')
            with self.assertRaises(ValueError): inputs.check(root)
            (root/'source.cs').write_text('current main source');inputs.check(root)
            (root/'new.cs').write_text('extra')
            with self.assertRaises(ValueError): inputs.check(root)
            (root/'new.cs').unlink();(root/'source.cs').unlink()
            with self.assertRaises(ValueError): inputs.check(root)

    def test_refuses_existing_source_and_archive(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); source=root/'source';source.mkdir()
            with self.assertRaises(ValueError):inputs.new_destination(source,source)
            with self.assertRaises(ValueError):inputs.new_destination(root,source)
            dest=root/'engine';dest.with_suffix('.tar').write_bytes(b'preserve old verified archive')
            with self.assertRaises(ValueError):inputs.new_destination(dest,source)
            self.assertEqual(dest.with_suffix('.tar').read_bytes(),b'preserve old verified archive')

    def test_freezes_current_main_source_without_git_metadata(self):
        with tempfile.TemporaryDirectory() as temp:
            dest=Path(temp)/'snapshot'
            value=inputs.snapshot(inputs.ROOT,dest,['mod.config','tools/build-inputs.py'])
            inputs.check(dest)
            self.assertIn(value['branch'],['main','master'])
            self.assertEqual((dest/'mod.config').read_bytes(),(inputs.ROOT/'mod.config').read_bytes())
            self.assertFalse((dest/'.git').exists())
            self.assertEqual(len(value['files']),2)

if __name__=='__main__':unittest.main()
