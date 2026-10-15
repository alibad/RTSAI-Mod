"""Pack original generated pixels into engine-compatible power-of-two sheets.

This only adds transparent padding. No source pixel is resized, retouched or lost;
chrome regions retain the original coordinates. Keep sources and prompts together.
"""
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]

for name in ("backdrop", "controls", "icons"):
    source = ROOT / "docs/frontline-menu-assets" / f"{name}-source.png"
    with Image.open(source) as image:
        width, height = image.size
        sheet = Image.new("RGBA", (1 << (width - 1).bit_length(), 1 << (height - 1).bit_length()))
        sheet.paste(image.convert("RGBA"), (0, 0))
        destination = ROOT / "mods/rtsai/uibits/frontline" / f"{name}.png"
        sheet.save(destination)
        print(f"{name}: {width}x{height} in {sheet.width}x{sheet.height}")
