"""Every game mode loading the shared modern rocket weapon must also load its image."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def entries(text, section):
    inside = False
    for line in text.splitlines():
        if line and not line[0].isspace():
            inside = line.split('#', 1)[0].strip() == section + ':'
        elif inside and line.strip() and not line.lstrip().startswith('#'):
            yield line.strip()


class RocketImageManifest(unittest.TestCase):
    def test_every_modern_weapon_consumer_loads_the_image(self):
        consumers = []
        for manifest in (ROOT / 'mods').glob('*/mod.yaml'):
            text = manifest.read_text(encoding='utf-8')
            if 'ra2|modern-factions/weapons.yaml' not in set(entries(text, 'Weapons')):
                continue
            consumers.append(manifest.parent.name)
            with self.subTest(mod=manifest.parent.name):
                self.assertIn('ra2|modern-factions/rocket-impact-sequences.yaml', set(entries(text, 'Sequences')))
        self.assertEqual(set(consumers), {'rtsai', 'rtsai-ra2', 'rtsai-topdown', 'rtsai-classic'})


if __name__ == '__main__':
    unittest.main()
