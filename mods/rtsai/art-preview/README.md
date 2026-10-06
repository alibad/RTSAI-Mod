# Art preview overlay

Local branch `rtsai/art-preview` only. New Blender-authored faction art is installed here, so the owner can play the whole new look before deciding unit by unit. `main` changes only after the owner's review.

- The rule, sequence and voxel files are loaded last in `mod.yaml`, so they override the faction files.
- Each art route owns its files:
  - vehicles, ships and aircraft: `vehicles*.yaml`, `voxels.yaml`, `voxels/`;
  - infantry: `infantry*.yaml`, `infantry/`;
  - buildings and defenses: `buildings*.yaml`, `buildings/`;
  - cameos: `icons/`, `icons-sequences.yaml`.
- Never put original EA RA2 files or anything derived from them here.

## Provenance: cameos (`icons/`)

- **Pictures.** Rendered by RTSAI-Art `tools/cameo_render.py` from the project's own 3D models:
  - vehicles, ships and aircraft from their installed prerender candidates;
  - buildings from their building-route jobs;
  - infantry from the infantry-route rigs.

  Candidates and full notes: RTSAI-Art `units/<actor>/candidates/cameo-v3-render/` and `docs/cameos.md`.
- **Name bar.** The text is the unit's in-game English name (Tooltip Fluent string; long names use the short labels
  in RTSAI-Art `tools/cameo_names.json`).
- **Font: Kenney Pixel** (`kenpixel.ttf`) by Kenney (www.kenney.nl), Kenney Fonts.
  - Licence: CC0 1.0 Universal Public Domain Dedication. The licence notice is kept beside the font in RTSAI-Art
    `tools/fonts/kenney/LICENSE.txt`.
  - The font file itself is not shipped here; only the rendered cameos are.
  - No EA font is used.
- **Unlabelled variants.** For localisation, these stay in each candidate folder (`cameo-nolabel.png`).
