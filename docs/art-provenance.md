# Art provenance: the five modern factions

Date: 2026-10-02. The per-file record is `mods/rtsai/modern-factions/ART-PROVENANCE.json`, written by
`tools/art-provenance.py`. This page explains it and lists what needs the owner's attention.

**[ran]** means a command was run and its output observed. **[inferred]** means it was reasoned from code, commit
messages or notes and not run.

## Scope

The review covers 307 files [ran]:

- 87 build-palette cameos (`modern-factions/icons`);
- 42 files in the five `*-art` folders: 35 SHP sprites and 7 palettes;
- 173 voxel files (`modern-factions/voxels`): 86 VXL/HVA model pairs and `modern.pal`;
- the 5 modern-faction flag regions of `mods/rtsai/uibits/buttons.png`.

Rules, Fluent text and audio are out of scope (the voices have their own provenance). Every file in scope is
referenced by the mod's rules, sequences or chrome [ran: `art-provenance.py --check`].

## Summary

| Art | Files | Origin | Status |
|---|---|---|---|
| Cameos | 87 | Qwen-Image, text-to-image, run locally | Prompt, seed, model revision, runtime, crop and hashes recorded |
| Infantry and defence SHP sprites | 35 | Rendered from meshes written in Python | Clean |
| Palettes (`*-art/*.pal`, `voxels/modern.pal`) | 8 | Computed by the same builders | Clean |
| Voxel models (VXL/HVA) | 172 | Exported from the same meshes | Clean |
| Lobby flags | 5 | Drawn with PIL primitives | Clean; redrawn pixel-identical [ran] |

**No file was found to contain, embed or derive from Red Alert 2 game data** (method below). No file is flagged
in the record [ran].

## 1. Cameos (`icons/`, 60×48 RGB PNG)

The sidebar draws cameos at `IconSize: 60, 48` (`chrome/ingame-player.yaml`). Every one of the 87 buildable modern
actors has its own cameo, and every cameo is used. The Saudi `strike` support power reuses `r2f15sa.png` [ran].

### What they replaced

All 87 were painted on 2026-10-02 with `tools/paint-cameos.py` [ran]. Each icon's `replaced` field in the JSON
says what was there before.

- **75 placeholders.** These were single renders of the same meshes as the battlefield sprites and voxels.
  - 44 came from China, Iran and Türkiye (`scripts/ra2_{china,iran,turkey}_assets.py`, OpenRA-AI main).
  - 31 were every Saudi and Yemeni cameo (`scripts/ra2_red_sea_assets.py`, codex/ra2-red-sea d96247a).

  [ran: hash match, commit log]
- **12 painted cameos.** Qilin, Lynx, Mantis, Cloud, Karrar, Raad, Fajr, Mohajer, Bozkır, Yıldırım, Sancak and Kuzgun
  were cut from `OpenRA-AI/assets/ra2-modern-factions/{china,iran,turkey}-portraits-v1.png`.
  - Those portraits were made on 2026-09-03 with Codex's built-in OpenAI image tool.
  - Their model, seed and per-image prompts were never recorded. The prompt cited
    `assets/china-faction/icon-sources/china-unit-cameo-atlas-v1.png`, which has no provenance note of its own.
  - In the palette they were darker, smaller in frame and padded with side bars, so the China, Iran and Türkiye
    tabs mixed two looks [ran: windowed captures].
  - Repainting them makes every cameo traceable and the set uniform.
- **Missing:** none [ran].

### How they are painted

- **Prompt.** One shared style wraps a per-unit identity from `tools/cameo-subjects.json`.
  - Each identity was written from the unit's rules, Fluent name and description, and its catalog entry where it
    has one.
  - For the 12 repaints, the identities also use the descriptions in `OpenRA-AI/assets/ra2-modern-factions/README.md`.
  - Examples: the Bradley's 25 mm turret with its TOW box, CAESAR's truck-mounted 155 mm gun with rear spade, Fajr's
    tilted grid rocket rack, Cloud as a tailless flying wing, and Sahaab as an uncrewed explosive boat.
- **Style.** A painted three-quarter view under a warm key light and cool rim light, on a dark teal-charcoal studio
  background. The prompt never names a game or a publisher.
- **Negative prompt.** It excludes text, logos, insignia and flags.
- **Generation.** 800×640 master, 28 steps, true CFG 4.0, seed `crc32(actor) mod 1e9 + variant − 1`.
  - 27 masters came from the shared Qwen-Image server, with whole-model offload.
  - Another job then filled most of the GPU, and the server slowed to minutes per step. The other 60 were made by
    `paint-cameos.py --backend local`, which loads the same model, revision and fp8 quantization in-process with
    block-level group offload.
  - Each cameo records its `runtime`.
- **Review [ran].** Every master and cameo was checked by eye for a correct unit type and for text or logos.
- **Rerolls.** 14 first masters were rejected and rerolled with a new seed: 10 once and 4 twice. Some subjects were
  reworded for the rerolls. The faults were:
  - two submarines drawn with cloth sails;
  - the Guard Tower drawn as a medieval castle;
  - the Toufan drawn with an Apache's mast radar;
  - the Yemeni coastal battery drawn as a tracked vehicle;
  - the Mantis drawn with a tank gun;
  - the Cloud drawn with tail fins;
  - six masters framed as rounded "app icons", and one with a UI badge.

  Rerolled cameos carry `variant` > 1 in the record.
- **Post-processing, to 60×48.** A deterministic subject-aware 5:4 crop keeps 55–92% of the master width. It is
  followed by a Lanczos downscale, then a light contrast and unsharp pass so the silhouette reads at native size.
- **Records.** For each cameo, `tools/cameo-generation.json` and the JSON hold:
  - the exact prompt and negative prompt;
  - the seed, steps, CFG and master size;
  - the model, its revision and the runtime;
  - the master's SHA-256, the crop box and the cameo's SHA-256.

  The masters themselves are not in the repository.

### Qwen-Image licence: Apache-2.0 [ran]

- **Model.** `Qwen/Qwen-Image`, revision `75e0b4be04f60ec59a75f475837eced720f823b6`, recorded for every
  generation: from the server's `/health`, or from the local snapshot for in-process runs.
- **Model card.** The local snapshot's `README.md` (sha256 `c70f9851…`) has the front matter `license: apache-2.0`
  and the section "License Agreement: Qwen-Image is licensed under Apache 2.0."
- **LICENSE file.** The snapshot's `LICENSE` (sha256 `832dd9e0…`) is the Apache License 2.0 text.
- **Hub.** The model card on huggingface.co/Qwen/Qwen-Image has the same front matter, read on 2026-10-02.
- **Not the same as two other local models.** Qwen-Image-2512 is a different checkpoint. `qwen-image-2.1` on this
  machine is non-commercial only. Neither was used.
- **Runtime.** Both runtimes use diffusers with the transformer and text encoder quantized to fp8 weight-only
  (torchao): the shared server `hq/quote-forge/server/qwen_image.py` and `paint-cameos.py --backend local`.
- **Input.** Text only: no reference, init or control image was given to the model.

## 2. Sprites, palettes and voxels

- **Sources.** Every file matches, byte for byte, a file in the product's `apps/installer/ra2/modern-factions` [ran].
  - China, Iran and Türkiye match OpenRA-AI main at e1a43fa.
  - Saudi Arabia and Yemen match codex/ra2-red-sea at b3b0ebd. Their art is committed there, in d96247a.
- **Commits.** The JSON records the last commit that touched each file.
- **How the builders work.** They build each unit from boxes, cylinders and polygons written in Python
  (`scripts/*_directional_assets.py`, `red_sea_directional_vehicle.py` and the `ra2_*_assets.py` files). They then
  render 48×48 infantry and 96×96 defence SHPs, or voxelize the same meshes into RA2 VXL/HVA.
- **Palettes.** They are computed from the project's material colours. They reserve the RA2 remap ramp 16–31.
- **External data.** The builders read no image, SHP, VXL, HVA, palette or MIX file [ran]. A grep of the ten
  builder modules and the modules they import finds no such reads:
  - `ra2_faction_voxels`, `ra2_{china,iran,turkey,red_sea}_assets`;
  - `{china,iran,turkey}_directional_assets`, `red_sea_directional_vehicle` and `red_sea_infantry`.

  The only external data is the RA2 voxel normal-vector table. It is parsed from OpenRA's own GPL source
  `VoxelNormalsPalette.cs`; it is format data, not art.
- **Font.** `FreeSansBold.ttf` is used only for the faction preview sheets, which are not in the mod.
- **Manifests.** The build manifests (`*-art/manifest.json`, `voxel-manifest.json`, `red-sea-voxel-manifest.json`)
  stay in the product checkouts; `art-provenance.py` reads the voxel manifests from there. Their SHA-256 values
  matched the shipped files before the manifests were removed from the mod [ran].
- **Re-running the builders.** This was not part of the review [inferred: deterministic code].

## 3. Lobby flags

- **Builder.** `OpenRA-AI/scripts/build-red-sea-ui.py` draws the China, Iran, Türkiye, Saudi and Yemen flags with
  rectangles, lines, ellipses and star polygons.
- **How they reached the mod.** The script drew them into the fork's `glyphs-redsea.png`.
  `tools/port-modern-factions.py` then copied them into the bottom row of `uibits/buttons.png`.
- **Redraw check [ran].** A fresh draw of all five matches the mod's regions pixel for pixel. Every pixel of each
  region is drawn by the script, so nothing underneath leaks through. The Saudi shahada is an abstract two-line
  mark, not lettering.

## 4. Commercial Red Alert 2 check

- **Cameos.** They are text-to-image, the prompts never name a game or a publisher, and the model received no image
  input.
- **Sprites and voxels.** They come from code-defined meshes, and their builders read no game files.
- **Flags.** They redraw identically from code.
- **Repository.** No `.mix` file is tracked [ran: `git ls-files`].
- **Visual comparison.** A visual comparison against the owned RA2 cameos was not made, because nothing in the
  pipeline could carry them in.

## 5. Removed, kept and notes

- **Removed from the mod.** 23 files that nothing referenced [ran]:
  - 16 developer review sheets (`*-art/*-review.png`, 343 KB);
  - the five `*-art/manifest.json`;
  - `voxel-manifest.json` and `red-sea-voxel-manifest.json`.

  A full re-port with `tools/port-modern-factions.py` would copy them back from the product. Delete them again,
  or teach the port to skip them.
- **Kept although the game does not load them.**
  - The five `*-replacements.yaml` files are inputs that `port-modern-factions.py` merges into
    `shared-replacements.yaml` on every run [ran: `combined_replacements` reads them from the mod].
  - `ART-PROVENANCE.json` itself.
- **Small marks in the masters.**
  - Some infantry masters show a national-flag patch on a sleeve or launcher, despite the negative prompt.
  - A few have a pseudo-signature scribble in a corner. The crop keeps at most 92% of the master, which drops most
    corners.
  - Neither is legible at 60×48, and neither is a real logo or text.

## 6. Acceptance [ran]

- **Build and lint.** `make all` exits 0 with 0 warnings and 0 errors. `make test` exits 0 with no warnings.
- **Provenance check.** `tools/art-provenance.py --check` reports that all 307 files are covered and none are
  flagged.
- **Windowed matches.**
  - Setup: the dev build at 1280×800, with owned RA2 data copied into an isolated support dir and deleted
    afterwards. Each match was a scratch copy of DEFCON 6 that gives the player a production base without a
    construction yard.
  - Each match ran 170 s with 0 exceptions.
  - `CaptureCompanionFrame` recorded the build palette for all five factions with the 75 first cameos, and the
    China Vehicle tab again after the 12 repaints. The frames contain RA2 UI, so they are not in the repository.

## 7. Outside this scope (seen in passing, not reviewed)

- The stock maps carry `Author: Westwood Studios` (converted RA2 maps inherited from the upstream OpenRA RA2 mod).
- The rest of `uibits/buttons.png` is upstream RA2-mod chrome.

## Reproduce

```
# needs Pillow, numpy and requests (e.g. ../OpenRA-AI/.venv) and the Qwen-Image server on :8021
python tools/paint-cameos.py generate --work <dir>                     # masters, variant 1
python tools/paint-cameos.py generate --work <dir> --only r2x --variant 2
# or in-process (torch, diffusers, transformers, torchao; the model in the local HF cache):
python tools/paint-cameos.py generate --backend local --work <dir>
python tools/paint-cameos.py install  --work <dir> --pick r2x=2         # 60x48 icons + tools/cameo-generation.json
python tools/art-provenance.py                                          # rebuild ART-PROVENANCE.json
python tools/art-provenance.py --check                                  # covered, referenced, unflagged, current
# art-provenance.py reads ../OpenRA-AI and ../OpenRA-AI-wt-ra2-red-sea (--product, --red-sea) to match sources
```

Seeded generation on the same model revision reproduces closely. It may not reproduce byte for byte across GPUs,
drivers or library versions [inferred]. The recorded master hash is what the installed cameo was made from.
