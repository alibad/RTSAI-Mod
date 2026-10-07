# Art provenance: the modern factions

Date: 2026-10-06, when the owner-approved art preview was promoted into `main`. The per-file record is
`mods/rtsai/modern-factions/ART-PROVENANCE.json`, written by `tools/art-provenance.py`. This page explains how the art
is made and where each record comes from.

**[ran]** means a command was run and its output observed. **[inferred]** means it was reasoned from code, commit
messages or notes and not run.

## Scope and summary

Every art file under `mods/rtsai/modern-factions` is covered: 307 files, none flagged [ran:
`tools/art-provenance.py --check`]. Rules, Fluent text, audio (see [audio-provenance.md](audio-provenance.md)) and the
record itself are out of scope.

| Art | Files | Size | Made by (RTSAI-Art) | Candidate |
|---|---:|---:|---|---|
| Vehicles, ships, aircraft (`vehicles/`) | 69 SHP + 7 faction palettes | 7.5 MB | `tools/glb_prerender.py` | `sprite-v6-prerender` |
| Infantry (`infantry/`) | 28 SHP + 28 palettes | 10.0 MB | `tools/infantry_blender.py`, `infantry_sprite_post.py` | `sprite-v3-glb` |
| Buildings and defenses (`buildings/`) | 25 SHP + 25 palettes | 5.7 MB | `tools/building_sprites.py` | `sprite-v3-glb` |
| Build-menu cameos (`icons/`) | 122 PNG, 60x48 | 0.6 MB | `tools/cameo_render.py` | `cameo-v3-render` |
| Lobby flags (`ui/`) | 3 PNG atlases | 0.03 MB | OpenRA-AI `scripts/build-levant-flags.py`; Hezbollah: `tools/faction-flag.py` | (drawn from code; Hezbollah: its real flag, see below) |

The owner approved all of it on 2026-10-06 ("I approve all the changes"). RTSAI-Art `review.json` records a "use"
decision for each of the 122 units' battlefield model and build icon (RTSAI-Art 88a31bf, authored "owner bulk approval
in chat, 2026-10-06"). Every installed file matches its candidate byte for byte, and every candidate is committed in
RTSAI-Art [ran].

## One chain for every unit

All 122 units come through the same chain [ran: every chosen candidate's `meta.json`]:

1. **Concept picture.** One picture per unit, made by the coding agent's built-in image generation (no paid API; the
   tool does not report its model ID). The prompt describes the role and the shared finish: pale lit armour, dark
   mechanical recesses, a restrained faction hue. Candidate `units/<actor>/candidates/cameo-v1-role-rebuild/`.
2. **3D model.** TRELLIS.2 image-to-3D, run locally (`trellis-cli`, seed 42, BiRefNet background removal), on that
   picture: `units/<actor>/candidates/mesh-v1-role-rebuild/mesh.glb`. Its SHA-256 is in each record's `geometry`.
3. **Route.** Blender (CPU) splits, scales and paints the GLB with the project's material classes and faction colours
   and renders it for the game. The routes below differ only in what they render.
4. **Install.** RTSAI-Art's installer copies the candidate's files into `modern-factions/` and writes that route's
   `art-*.yaml` block. `tools/art-provenance.py` then records the file, its candidate, the RTSAI-Art commit that holds
   the same bytes, and the GLB.

Original Red Alert 2 files were never an input to any of these steps. The routes read stock RA2 art only on this
machine (RTSAI-Art `reference-local/`, ignored by git) to measure targets: value range, local contrast, silhouette rim
and on-screen size [ran: `glb_prerender.py` and `cameo_render.py` gates]. At run time the vehicle effects layer names
stock RA2 effect sprites (gun flash, launch puff, smoke, fire, explosions). They load from the player's own RA2
install and are not shipped.

### Vehicles, ships and aircraft: GLB to prerendered sprite

`tools/glb_prerender.py` renders the GLB through OpenRA's own model camera in Blender Cycles as geometry passes and
lights them in Python with OpenRA's voxel light formula. The stock RA2 light is ambient -0.5, diffuse 1.4, on the
voxel light vector. Each faction's sprites therefore light like a voxel unit would. The result is supersampled down and
quantized into one palette per faction (`<faction>-prerender.pal`, remap 16-31 for the player colour).

- **SHP layout.** 32 facings per sequence: body, turret, spinning rotors and radars as extra frames, still variants for
  landed and undeployed states, empty-launcher bodies for the Yemen MLR and Hezbollah rocket truck while they reload,
  and sun-shadow frames for ground units (aircraft use `WithShadow`).
- **Size.** The on-screen area is matched to the unit's class size target, within about 2%.
- **Muzzles.** Every armament's `LocalOffset` is measured on the renders (`tools/muzzle_fit.py`), so shots leave the
  drawn barrel tip.
- **Animation layer.** `tools/anim_fx.py`: damage smoke and fire by damage state, death explosions sized by class
  (effect-only weapons, no damage), gun flashes and launch puffs.
- **Haiwang carrier drones.** They share the Cloud drone's sprite.

### Infantry: rigged GLB

The infantry route rigs each soldier's GLB, poses and animates it in Blender, and renders every action per facing:
stand, run, fire, prone, idle and two deaths. Faction uniforms come from `tools/infantry_factions.json`: camouflage on
arms and legs, gear colour, helmet or head wrap. A faction accent sits on every helmet. Launcher teams fire from the
muzzle flash drawn in their sprites, prone too.

### Buildings and defenses

`tools/building_sprites.py` renders each building's GLB isometrically on the stock cell grid. Every building gets
damaged and critical states and a build-up animation. Armed buildings also get turret facings and firing frames, and
bunkers fire from their slit. Each building carries the faction identity panel in its vehicle route's signature
colours.

### Cameos

`tools/cameo_render.py` renders each unit's installed model (or its building job or infantry rig) in perspective,
reduces it to 60x48 and adds a stock-style name bar.

- **Name bar text.** The unit's in-game English name: its Tooltip Fluent string, or the short labels in RTSAI-Art
  `tools/cameo_names.json` for long names.
- **Font: Kenney Pixel** (`kenpixel.ttf`) by Kenney (www.kenney.nl), **CC0 1.0** Universal Public Domain
  Dedication. The licence notice is kept beside the font in RTSAI-Art `tools/fonts/kenney/LICENSE.txt`. Only the
  rendered cameos ship; the font file does not. No EA font is used.
- **Unlabelled variants.** Kept for localisation in each candidate folder (`cameo-nolabel.png`).
- **Support powers.** Saudi Arabia's and Israel's strike powers reuse the F-15SA and Falcon cameos.

### Faction accents

A unit's faction is shown by restrained, fixed accents. The lobby/player colour is a separate remap (indices 16-31)
and is never baked in.

- **Vehicles.** Flat accent panels and bands from each faction's palette.
- **Buildings.** The identity panel described above.
- **Infantry.** The helmet accent and faction uniforms.
- **Cameos.** Each cameo shows the same model, so the same accents.

### Faction flags

The lobby and tooltip flags (`ui/faction-flags*.png`, chrome collection `flags`) are drawn from code, except
Hezbollah's.
- **Owner decision, 7 October 2026:** Hezbollah shows its real flag everywhere, the game included, as the public
  website already does.
- **Source:** `tools/flag-sources/hezbollah.svg`, the website's copy, from
  https://upload.wikimedia.org/wikipedia/en/0/08/Flag_of_Hezbollah.svg (downloaded 4 October 2026).
- **How it is built:** `tools/faction-flag.py hezbollah` rasterizes it with headless Chrome. It fits the flag
  undistorted into the 2:1 region, extends the yellow field to the sides, and writes the 1x, 2x and 3x atlases.
- **Status: non-free artwork,** not covered by any licence the project holds. The website's `docs/faction-art.md`
  records the known risks, which the owner accepted: Hezbollah's symbols are restricted in Germany, Austria, the UK
  and other countries that list it as a terrorist organisation. This note records that the game now ships the
  flag too; it is not legal advice.
- **To withdraw it:** restore the three atlases from git history before this change and re-run
  `tools/art-provenance.py`.

## How main's art is laid out

The art lives in its own canonical files, one block per actor per route. The faction rules (`<faction>-roster.yaml`
and friends) hold gameplay and no art of their own:

| File (in `modern-factions/`) | Contents | Written by (RTSAI-Art) |
|---|---|---|
| `art-vehicles.yaml`, `art-vehicles-sequences.yaml` | prerender palettes, render rules, measured muzzles, sequences | `tools/vehicle_install.py` |
| `art-vehicles-fx*.yaml` | damage, death and muzzle effects, effect-only weapons | `tools/anim_fx.py` |
| `art-infantry.yaml`, `art-infantry-sequences.yaml` | palettes, render rules, sequences | `tools/infantry_install.py` |
| `art-buildings.yaml`, `art-buildings-sequences.yaml` | palettes, render rules, sequences | `tools/building_sprites.py install` |
| `art-icons-sequences.yaml` | every modern cameo | `tools/cameo_render.py install` |
| `art-voxels.yaml` (on first use) | model sequences for a unit installed on the bold voxel fallback | `tools/glb_route_install.py` |

RTSAI-Art `tools/mod_target.py` holds this layout. Reinstalling all 28 infantry, all 25 buildings, all 122 cameos and
the Cloud (with the Haiwang drones) reproduced these files byte for byte, and the effects layer regenerated whole [ran].

## The record and the website guard

Each `ART-PROVENANCE.json` entry has:

- `sha256`, `type`, `origin` (`rendered-from-project-geometry`, or `procedural` for palettes and flags) and
  `generator` (`project-geometry`, `procedural-flag`);
- the candidate id and route;
- `source`: RTSAI-Art path and commit, verified to hold the same bytes;
- `geometry`: the GLB path and SHA-256, the TRELLIS.2 run and the concept candidate;
- for cameos, the name bar and font;
- whether the game references the file.

The website's Art Lab (`RTSAI-Web npm run sync:art`) publishes only files recorded here with a matching SHA-256 [ran:
304 files for 122 actors, `--check` exit 0].

After any install, re-run:

```
python tools/art-provenance.py           # rebuild the record (needs ../RTSAI-Art and ../OpenRA-AI)
python tools/art-provenance.py --check   # non-zero exit: uncovered, unknown origin, unreferenced or stale files
```

## What it replaced

The promotion removed the pre-promotion placeholder art from the mod:

- 114 procedural voxel models (VXL/HVA) and their palettes;
- 53 procedural infantry and defense SHPs with the faction palettes;
- the Israel/Hezbollah animation sheets;
- the 87 Qwen-Image cameos from 2026-10-02 and the 35 Israel/Hezbollah placeholder cameos;
- the unused Levant preview pictures.

The Qilin's jade voxel pilot (2b5218c) went too. RTSAI-Art `history/` archives every one of these files, plus every
intermediate version the art preview installed, with a manifest per unit: what it was, which release used it
(0.2.0-alpha.1 shipped 331 of them), what superseded it, and its generator and provenance record. 1640 entries in all.
Every archived voxel version has its HVA and palette beside it, so it still renders. The previous record and this
page's previous version are in RTSAI-Art `history/_records/` and in this repository's history (`efb197d`).

## Reproduce

```
# RTSAI-Art (OpenRA-AI venv; Blender 5.2 on PATH for the render steps; CPU only)
python tools/glb_prerender.py <actor>                       # a vehicle candidate (sprite-v6-prerender)
python tools/vehicle_install.py install <actor> --route sprite && python tools/anim_audit.py dump && python tools/anim_fx.py write
python tools/infantry_install.py <actor> ...                 # sprite-v3-glb infantry
python tools/building_sprites.py units/<actor>/candidates/sprite-v3-glb --stage install
python tools/cameo_render.py install
# RTSAI-Mod
python tools/art-provenance.py && python tools/art-provenance.py --check
./make.cmd test
```
