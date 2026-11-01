# companion/: the RTS AI co-commander

The AI companion that ships inside the desktop game, plus the tools that build it. It came here from the
OpenRA-AI repository on 1 Nov 2026 (copied from OpenRA-AI `c4aa56d`). That repository is archived; its full history,
the retired OpenRA AI Classic installers and their art stay readable there.

| Folder | What it is |
|---|---|
| `services/companion` | The companion (Python): advice, reviewed orders, voice, the local AI runtime, the natural-language order benchmark (`evals/nl_orders`) |
| `services/worldgen` | The Earth-to-battlefield world generator the companion carries |
| `apps/launcher` | Entry points PyInstaller freezes (`companion_entry.py`, `local_ai_entry.py`) |
| `scripts` | Setup, packaging and voice tools (`setup.ps1`, `package-rtsai-companion.ps1`, `ai_pack.py`, `voice_engines.py`, `generate-rtsai-mod-audio.py`, `build-companion-tech-tree.py`). Many other scripts are generators for the retired Classic product, kept for reference |
| `packaging` | Locks and notices for the local AI pack and runtimes |
| `catalog/factions.json` | The copy the frozen companion carries. The master is `../catalog/factions.json`; `python tools/sync-faction-catalog.py` writes this copy and `--check` guards it |

Not in git (local only): `.venv/`, `ai/` (local models and runtimes), `.env` (keys for the AI Arena), `.artifacts/`,
`generated/`, `artifacts/`.

## Use

- Set up: `powershell -File companion/scripts/setup.ps1` creates `companion/.venv` with the companion installed in
  editable mode.
- Play with it from source: `tools/launch-desktop.ps1` sets `OPENRA_AI_ROOT` to this folder; `CompanionHost` runs
  `.venv` + `apps/launcher/companion_entry.py`.
- Build the frozen companion for the Windows installer: `companion/scripts/package-rtsai-companion.ps1
  -OutputDirectory <dir>`, then `packaging/windows/build-release.ps1 -CompanionDirectory <dir>/companion`.
- Tests: `companion/.venv/Scripts/python -m pytest companion/services/companion/tests companion/services/worldgen/tests companion/tests`.

Development tools that need an engine use `engine/openra` if present, otherwise the canonical `../../OpenRA`
checkout.

Other repositories find this folder as `../RTSAI-Mod/companion`: the web game's local companion and AI Arena
(`RTSAI_OPENRA_AI`), the local Studio and Sound Desk (its Python), and the /play release (`tools/prepare-inputs.py`
snapshots `missions/` from RTSAI-Mod).
