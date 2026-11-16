# Native original-country art

The Mac package uses the shared `RTSAI-WebGame/tools/ea_originals.py` generator's
`native-render-only` target. The web target remains the default. The native target
does not apply the browser's retail gameplay conversion. A separate allowlist and
fresh native-rule comparison reject simulation changes in the emitted overlay.

Build prerequisites include Python with Pillow for the flag gate. Select it with
`RTSAI_MAC_PYTHON`. Set `RTSAI_MAC_ORIGINAL_ART` to an approved loose-art cache
outside every Git repository, containing `EA-INPUTS.json` with the attribution,
file names and SHA-256 hashes. The packager refuses a missing cache, unapproved
file, changed hash or identical stand-in models. `RTSAI_MAC_WEBGAME` defaults to
the canonical sibling checkout. All three repositories must be current committed
main branches before packaging.

Only the planned `.shp`, `.vxl`, `.hva` and `.pal` files are copied, with a generated
transparent pixel and render rules. No original archives, music, EVA, video or
audio are bundled by this step. Players need no owned game installation. Original
unit voices and browser gameplay differences remain separate work.

The payload records provenance in `native-original-art.json`; `BUILD-INPUTS-macos.json`
includes its digest, generator identity, approved manifest hash and gate identity.
The attribution appears in the native prerelease notice and a NOTICE file.

Local checks:

```sh
python3 packaging/macos/test-original-art.py
python3 packaging/macos/prepare-original-art.py --resources /path/to/Resources --verify
```

The build also runs native `--check-original-art` against both isometric profiles.
That loads all nine original-country image bindings, all seven preserved modern
image bindings, voxel images and support-power icon sequences. The installed-DMG
smoke repeats these checks and validates all sixteen faction flags at three
densities before exercising Library buttons and matches.

The native support-power widget inherits all engine controls and changes only
prepared sprite/palette pairs. Its one private dictionary bridge is explicitly
type-checked by the release gate; an engine layout change fails packaging for
review. `RTSAI_ORIGINAL_ART_VERIFY=1` enables local diagnostic provenance lines.
