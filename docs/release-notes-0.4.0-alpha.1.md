# RTS AI 0.4.0-alpha.1 — Windows testing release

One standalone game with an in-game **Game modes** chooser: **Classic** and **Isometric**. No owned Red Alert or Red Alert 2 installation is required.

- 16 country choices, including seven authored modern faction packs.
- Six campaign maps with native objectives, civilian convoy orders, enemy waves and difficulty.
- Windows per-user EXE installer and portable ZIP. The local companion and inference runtimes are bundled; models are optional downloads. Choose **No AI** for the first gameplay test, or **Full local AI** to download the optional model pack.
- Classic currently uses the shared modern army on a rectangular grid. It does not yet reproduce every feature or map of the historical Classic fork.

## Test the release

1. Download the Windows installer from https://rtsai.net/download and run it. This alpha is unsigned; the download page lists its SHA-256.
2. Choose **No AI** for a quick install. Launch **RTS AI** from the Start menu.
3. Open **Game modes**, choose a mode, then start a skirmish or campaign.
4. Repeat in the other mode. Settings, replays and maps are kept in the game's support directory.

The portable ZIP is an alternative: extract the complete folder and launch `RTSAI.exe`.

This is a Windows development prerelease. Full historical Classic migration, all campaign outcomes, broader hardware/network acceptance and complete browser/native parity remain open. macOS for this version follows on the owner's Mac. The older release remains available in release history.

Build verification: zero native compiler warnings/errors, strict standalone checks, audio provenance, preserved-resource hashes, packaged mode-switch/render check and portable payload checksums. The release includes `SHA256SUMS.txt` and per-file checksums. Engine pin: `68c1e955578d804921f4907753af932fa7ed0e14`.
