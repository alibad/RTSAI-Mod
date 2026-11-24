# RTS AI 0.4.0-alpha.6 — the original countries look and sound like Red Alert 2 (Windows)

The same three-game Library as 0.4.0-alpha.5 (Classic, RA2 and RTS, with Lebanon as the seventh modern faction), with
these changes:

- **Original art for the nine original countries** (America, Korea, France, Germany, Great Britain, Libya, Iraq,
  Cuba and Russia): their units and buildings now use Red Alert 2's own art in the RA2 and RTS games, as the browser
  game at rtsai.net/play already does. The modern factions keep their own art.
- **Original unit voices and sounds**: the units those countries field answer with their Red Alert 2 voices, and their
  weapons, deaths, building placement, selling and cloaking play the original sounds. The Attack Dog barks for every
  faction. Only the sounds change: a build check refuses any change to hit points, damage, range or any other rule.
  No Command & Conquer music, EVA announcer lines or videos are included.
- **The AI adviser's order card**: press **J** to apply the recommended order at once, with no second confirmation box.
  The card is redrawn flat, like the browser game's.
- **EA's notice in the game**: the start-up notice says "EA has not endorsed and does not support this product.", and
  the Credits screen credits Westwood Studios and Electronic Arts for the original art, unit voices and sounds.

Since 0.4.0-alpha.5 (22 November): 5 commits on the mod.

Red Alert 2's art and sounds are © Electronic Arts, used under EA's Command & Conquer modding guidelines. RTS AI is free
and non-commercial. EA has not endorsed and does not support this product. No owned copy of Red Alert 2 is needed.

**Saved games from 0.4.0-alpha.5 are not listed at first.** Each version keeps its own save folder. To carry a save
over, copy its `.orasav` file from `%APPDATA%\OpenRA\Saves\rtsai\0.4.0-alpha.5\` into
`%APPDATA%\OpenRA\Saves\rtsai\0.4.0-alpha.6\` (create the folder if it is not there). Saved games are loaded from
**Tools > Load Game**.

The EXE installer is per-user; a portable ZIP is also available. No AI is the safe first choice. Full local AI needs an
optional model download (about 1.8 GB) and suitable hardware; on a PC without a supported graphics card it runs as a
text adviser without map vision. This alpha is **unsigned**, so Windows SmartScreen will warn; SHA-256 checksums are
published for every file. No macOS package is included.

Tested on the build machine (not a fresh Windows install):

- Silent install, then a bot skirmish in each of the three games, started from the installed `RTSAI.exe`, then
  uninstall. In the RA2 game, America and Russia build with Red Alert 2's original art.
- From the portable ZIP: America against Russia in the RA2 game, and Lebanon against Israel in the RTS game (both
  bases grow; the modern factions keep their own art).
- The build's own check: 810 original-country image bindings load and the 4,921 modern ones are unchanged. Every one
  of the 568 original sound clips the rules name is in the package. Nobody has listened to them on this build yet.
- Full local AI installed from the offline model pack: the game reaches the local AI and the adviser answers in game.
  Microphone and voice were not checked.
- No file in the package names the faction's previous name.

Broader clean-OS, microphone and network acceptance remain open.

Build input: mod `185db7d` (alibad/RTSAI-Mod main); engine `89285fdeb7fd5efda31a665054675e7b44a76634`; AI companion
frozen from the same mod commit; original art and sound generator RTSAI-WebGame `c751d20` (`BUILD-INPUTS.json` beside
the downloads).

Website: https://rtsai.net · Browser: https://rtsai.net/play/
