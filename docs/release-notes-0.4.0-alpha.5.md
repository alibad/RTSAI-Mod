# RTS AI 0.4.0-alpha.5 — sharper battles and a stronger adviser (Windows)

The same three-game Library as 0.4.0-alpha.4 (Classic, RA2 and RTS, with Lebanon as the seventh modern faction), with
these changes:

- **Explosions**: the 38 blast effects are redrawn, softer and brighter.
- **Bots**: they now build Terror Drones, Demolition Trucks and Terrorists, and the original countries open with a
  second refinery, like the modern ones.
- **Selection boxes** fit each of 96 vehicles, ships and aircraft.
- **Modern factions' weapons**: blasts sized by their damage, missiles that reach their full range, and the Qilin Battle Tank's
  coax gun flash.
- **Flags**: the four original countries that lacked one in the game's flag sheets now have their approved national
  flag.
- **The local AI adviser** (with "Full local AI" chosen at install) builds a base that holds, spends its money,
  attacks in waves, scouts one unit at a time and remembers where the enemy base is.

Since 0.4.0-alpha.4 (14 November): 24 commits on the mod.

**Saved games from 0.4.0-alpha.4 are not listed at first.** Each version keeps its own save folder. To carry a save
over, copy its `.orasav` file from `%APPDATA%\OpenRA\Saves\rtsai\0.4.0-alpha.4\` into
`%APPDATA%\OpenRA\Saves\rtsai\0.4.0-alpha.5\` (create the folder if it is not there). Saved games are loaded from
**Tools > Load Game**.

The EXE installer is per-user; a portable ZIP is also available. No AI is the safe first choice. Full local AI needs an
optional model download (about 1.8 GB) and suitable hardware. This alpha is **unsigned**, so Windows SmartScreen will
warn; SHA-256 checksums are published for every file. No macOS package is included.

Tested on the build machine (not a fresh Windows install):

- Silent install, then a bot skirmish in each of the three games, started from the installed `RTSAI.exe`, then
  uninstall.
- From the portable ZIP: Lebanon against Israel (both bases grow), Lebanon's chapter map, and the scripted mission
  "Relay Under Siege" (its objectives load and the first enemy wave arrives).
- Full local AI installed from the offline model pack: the game reaches the local AI and the adviser answers in game.
  Microphone and voice were not checked.
- A skirmish saved in 0.4.0-alpha.4, copied over as above, loads and plays.
- No file in the package names the faction's previous name.

Broader clean-OS, microphone and network acceptance remain open.

Build input: mod `9f61027` (alibad/RTSAI-Mod main); engine `89285fdeb7fd5efda31a665054675e7b44a76634`; AI companion
frozen from the same mod commit (`BUILD-INPUTS.json` beside the downloads).

Website: https://rtsai.net · Browser: https://rtsai.net/play/
