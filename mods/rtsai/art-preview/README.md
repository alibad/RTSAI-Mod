# Art preview overlay

Local branch `rtsai/art-preview` only. New Blender-authored faction art is installed here, so the owner can play the whole new look before deciding unit by unit. `main` changes only after the owner's review.

- The rule, sequence and voxel files are loaded last in `mod.yaml`, so they override the faction files.
- Each art route owns its files:
  - vehicles, ships and aircraft: `vehicles*.yaml`, `voxels.yaml`, `voxels/`;
  - infantry: `infantry*.yaml`, `infantry/`;
  - buildings and defenses: `buildings*.yaml`, `buildings/`;
  - cameos: `icons/`.
- Never put original EA RA2 files or anything derived from them here.
