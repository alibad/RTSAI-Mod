import runpy
from pathlib import Path
import shutil
import tempfile
import unittest

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
flags = runpy.run_path(str(ROOT / "companion/scripts/build-levant-flags.py"), run_name="flag_import_helpers")


class NativeFlagTest(unittest.TestCase):
    def test_all_sixteen_flags_resolve_at_all_densities(self):
        report = flags["inspect"]()
        self.assertTrue(report["passed"], report["errors"])
        self.assertEqual(report["faction_count"], 16)
        self.assertEqual(len(report["coverage"]), 48)

    def test_legacy_atlas_binding_fails_even_when_new_pngs_are_present(self):
        with tempfile.TemporaryDirectory() as temporary:
            chrome = Path(temporary) / "chrome.yaml"
            chrome.write_text(flags["CHROME"].read_text().replace(
                "Image2x: ra2|modern-factions/ui/faction-flags-2x.png", "Image2x: legacy-flags.png"))
            report = flags["inspect"](chrome=chrome)
            self.assertFalse(report["passed"])
            self.assertTrue(any("image bindings changed" in error for error in report["errors"]))

    def test_legacy_abbreviation_tiles_fail_the_gate(self):
        for faction in flags["IMPORTS"]:
            with self.subTest(faction=faction), tempfile.TemporaryDirectory() as temporary:
                atlas = Path(temporary)
                for name in flags["ATLAS"].glob("faction-flags*.png"):
                    shutil.copy2(name, atlas / name.name)
                image = Image.open(atlas / "faction-flags.png").convert("RGBA")
                x, y, w, h = flags["regions"](flags["CHROME"])[faction]
                tile = Image.new("RGBA", (w, h), "#4c6157")
                ImageDraw.Draw(tile).text((2, 1), faction[:2].upper(), fill="#e9ecd8")
                image.paste(tile, (x, y))
                image.save(atlas / "faction-flags.png")
                report = flags["inspect"](atlas=atlas)
                self.assertFalse(report["passed"])
                self.assertTrue(any(f"Flag {faction} at 1x" in error for error in report["errors"]))

    def test_unrelated_atlas_pixels_cannot_silently_change(self):
        with tempfile.TemporaryDirectory() as temporary:
            atlas = Path(temporary)
            for name in flags["ATLAS"].glob("faction-flags*.png"):
                shutil.copy2(name, atlas / name.name)
            image = Image.open(atlas / "faction-flags.png").convert("RGBA")
            image.putpixel((400, 400), (255, 255, 0, 255))
            image.save(atlas / "faction-flags.png")
            report = flags["inspect"](atlas=atlas)
            self.assertFalse(report["passed"])
            self.assertTrue(any("outside the four imported flags" in error for error in report["errors"]))


if __name__ == "__main__":
    unittest.main()
