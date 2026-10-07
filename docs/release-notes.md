# Release notes

## Next: 0.2.0-alpha.2 (not released)

Status: on local `main` only. Nothing is pushed or published yet. The build needs the engine branch pushed first
(see the push order at the top of `MIGRATION.md`). Previous release: 0.2.0-alpha.1 (main `6a39dad`, acceptance in
[first-launch.md](first-launch.md)).

### New factions

- **Israel** and **Hezbollah** join China, Iran, Türkiye, Saudi Arabia and Yemen.
  - Each has its own roster, doctrine, bot, support mechanics and lobby flag.
  - Israel speaks Hebrew and Hezbollah speaks Lebanese Arabic: unit voices, announcers and call signs.

### New art for every modern unit

All seven modern factions now look like they belong in Red Alert 2. Everything is rendered from the project's own 3D
models; details in [art-provenance.md](art-provenance.md).

- **69 vehicles, ships and aircraft** are prerendered sprites. They are lit like RA2 voxels, use one palette per
  faction with player colour on remap 16-31, and draw 32 facings, turrets, spinning rotors and radars, and the empty
  launcher while reloading. Their muzzles are measured on the renders, so shots leave the drawn barrel.
- **28 infantry** are rigged from 3D models and wear faction uniforms with a faction helmet accent. They have standing,
  running, firing, prone, idle and death animations.
- **25 buildings and defenses** carry the faction identity panel. They have damaged states and a build-up animation,
  and the armed ones have turret and firing frames.
- **122 build-menu cameos** are rendered from the same models and carry a name bar (CC0 Kenney Pixel font).
- **Effects.** Damage smoke and fire, death explosions sized by class, gun flashes and launch puffs.
- **What went.** The placeholder voxels, sprites and painted cameos left the game (archived in RTSAI-Art `history/`).
  The mod's content shrinks from 104.3 MB at the merge to 74.6 MB.
- **Fix.** Haiwang's carrier drones now draw the new Cloud sprite.

### Balance and bots

- **Balance rounds 3 and 4** ([balance.md](balance.md)).
  - China, Türkiye and Israel lifted; the Yemen and Hezbollah militia and RPG teams trimmed.
  - The ZBD fixed.
  - Explosive USVs can now reach a ship.
- **Bots** no longer waste money on ships that cannot reach the enemy or on extra airfield jets. Israel and Hezbollah
  bots use the right unit types.

### Engine

`rtsai/engine` 68c1e95557:

- missiles follow raised ground and ramps, so the Yemen and Hezbollah RPGs hit on high ground without a workaround;
- turret depth is consistent;
- a crash when a vehicle crossed between near-equal ramp tilts is fixed;
- faction flag sheets are padded to power-of-two sizes (a rendered-client crash).

### Verification on main

Recorded in `MIGRATION.md` (round C): build and lint, the hit lab, one windowed match per faction, a balance smoke and
the release build with its size.
