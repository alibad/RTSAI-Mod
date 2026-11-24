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
transparent pixel and render rules. No original archives, music, EVA or video are
bundled by this step. Players need no owned game installation. Browser gameplay
differences remain separate work.

**Both desktop builds (24 Nov 2026).** The Windows build runs this same step
(`packaging/windows/build-release.ps1 -OriginalArt <approved folder>`), then
`--check-original-art` on `rtsai-ra2` and `rtsai`. The owner asked for the original
art and audio on web and desktop, with the EA credit.

**Original unit voices and sounds.** The step also runs the web's voice generator
(`RTSAI-WebGame/tools/ea_voices.py`, its desktop path with no retail layer). The 47
units the nine countries field speak with their RA2 voice sets, the Attack Dog barks
for every faction, and the weapons, deaths and building, selling and cloaking sounds
of the original countries play RA2's clips. The clips are the approved `.wav` files
the overlays name, copied into `mods/rtsai/web/ea/audio`. `sound_rules` is a hard gate:
- weapons change only in their sounds;
- every death trait fires a copy of its native weapon that differs only in sounds;
- every actor's rules are unchanged once voices, sounds and the `ea-voice`/`ea-death`
  conditions are set aside.

**EA's notice in the game.** The developer-preview prompt every start shows has
"EA has not endorsed and does not support this product." on its fifth line, and the
Credits screen credits Westwood/EA. `--verify` checks both.

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
