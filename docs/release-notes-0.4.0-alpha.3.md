# RTS AI 0.4.0-alpha.3 — the desktop Library (Windows)

**Draft, not published.** Release candidate built and tested on 1 November 2026; publishing needs the owner's word.

The Windows download now opens the **RTS AI Library**: one window from which you start three games.

- **Classic**: the original, with your additions. On its first start it downloads the freeware Red Alert content
  from the OpenRA mirrors (nothing from EA is in this download).
- **RA2**: the isometric game, expanded, with the nine original countries.
- **RTS**: the seven modern factions and new ideas, on project-made art.

Since 0.4.0-alpha.2 (9 October): about 190 commits on the mod, including the three-game Library, the campaign v2
story, random maps and the map editor, and bots that train the original countries' own units. The engine is
canonical OpenRA main.

The EXE installer is per-user; a portable ZIP is also available. Select **No AI** for the first gameplay test. Local
AI requires optional model downloads and appropriate hardware. This alpha is **unsigned**, with SHA-256 checksums
published for every artifact. No macOS package is included.

Tested on the build machine (not a fresh Windows install): silent install into a folder with a space, a bot skirmish
in each of the three games started from the installed `RTSAI.exe`, the Library listing all three games and a game reopening the Library, and uninstall.
Broader clean-OS, microphone and network acceptance remain open.

Build input: mod `4c55d2e` (alibad/RTSAI-Mod main); engine `f158a224d52b16359ed3c0d643f0f0f5ec53f2c5`
(`BUILD-INPUTS.json` beside the downloads).

Download: https://rtsai.net/download · Browser: https://rtsai.net/play/
