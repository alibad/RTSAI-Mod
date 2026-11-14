# RTS AI 0.4.0-alpha.4 — Lebanon (Windows)

The seventh modern faction is now **Lebanon**, the "Cedar Guard": a new name, Lebanon's national flag, a new identity
story and rewritten rival lines, in all three games of the Library. Its units, costs and rules are unchanged.

Everything else is the 0.4.0-alpha.3 Library:

- **Classic**: the original, with your additions. On its first start it downloads the freeware Red Alert content
  from the OpenRA mirrors (nothing from EA is in this download).
- **RA2**: the isometric game, expanded, with the nine original countries.
- **RTS**: the seven modern factions and new ideas, on project-made art.

Since 0.4.0-alpha.3 (1 November): 14 commits on the mod. Besides the rename they are release tooling, documentation
and the AI companion moving into this repository; no gameplay change.

The EXE installer is per-user; a portable ZIP is also available. Select **No AI** for the first gameplay test. Local
AI requires optional model downloads and appropriate hardware. This alpha is **unsigned**, with SHA-256 checksums
published for every artifact. No macOS package is included.

Tested on the build machine (not a fresh Windows install): silent install into a folder with a space, a bot skirmish
in each of the three games started from the installed `RTSAI.exe`, uninstall, and from the portable ZIP a bot skirmish
with Lebanon in the RTS game and in Classic. No file in the package names the faction's previous name. Broader
clean-OS, microphone and network acceptance remain open.

Build input: mod `0f5314f` (alibad/RTSAI-Mod main); engine `f2059fdcabefc4bb04183028e4833373294a71d7`; AI companion
frozen from the same mod commit (`BUILD-INPUTS.json` beside the downloads).

Website: https://rtsai.net · Browser: https://rtsai.net/play/
