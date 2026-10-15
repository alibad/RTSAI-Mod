# Convoy Shield

`Convoy Shield` is a fictional maritime-security campaign mission. Its events,
forces, leaders, and attacks are invented and are not presented as a real-world
incident.

## Naval Systems compatibility

The mission uses stock Red Alert actors and mission-local role actors only. A
future Naval Systems integration should adapt these isolated names inside this
map instead of changing shared actor definitions:

- `CONVOYSHIELD.RADAR-PICKET`
- `CONVOYSHIELD.RESCUE-TENDER`
- `CONVOYSHIELD.CARGO` and `CONVOYSHIELD.CARGO.DISABLED`
- `CONVOYSHIELD.TANKER`
- `CONVOYSHIELD.RECON-DRONE`, `CONVOYSHIELD.MISSILE`, and
  `CONVOYSHIELD.USV`

An adapter may inherit a future branch actor under any of these map-local
names, while keeping this map's script API unchanged. No shared unit, faction,
or sprite definition is modified by this mission.

## Deterministic validation

The hidden `convoy-validation` lobby option supports short- and safe-route
autoplay plus forced cargo, tanker, escort, and survivor failures. It defaults
to `off` and exists only to exercise objective transitions and replay outcomes.

## Arabic UI text

The RA UI fonts use `FreeSansArabic.ttf` and `FreeSansArabicBold.ttf`, which
combine the existing FreeSans Latin glyphs with Noto Sans Arabic glyphs from
the official Google Fonts repository. Noto Sans Arabic is distributed under
the SIL Open Font License included at `mods/common/NotoSansArabic-OFL.txt`.
Arabic radio strings are stored as visual-order presentation forms because the
current OpenRA sprite-font renderer draws individual glyphs without bidirectional
layout or contextual shaping.
