# First launch, installer and AI runtime

Branch `rtsai/runtime` (RTSAI-Mod and OpenRA-AI), 2 October 2026. Nothing is pushed or published.
**[ran]** means a command or UI action was performed and its result observed; **[inferred]** means it was
reasoned from code and not run.

## What the player does

1. Runs `RTSAI-0.2.0-alpha.1-win-x64-setup.exe`. No administrator rights; it installs to
   `%LOCALAPPDATA%\Programs\RTS AI` and asks one question: how the co-commander should think.
2. Starts **RTS AI** from the Start menu or desktop.
3. The content installer finds the Red Alert 2 they own (Steam, EA app/Origin or disc) and imports it
   (Advanced Install > Detect Disc or Installation > Continue).
4. The main menu opens. The co-commander is already running: hosted thinking on rtsai.net, Whisper and
   Kokoro on the PC. No key, account or settings.
5. Skirmish: the HUD strip shows advice, the voice reads it, `Ctrl+Space` asks a question.

## How it works

```text
RTSAI.exe ─ OpenRA + mods/rtsai ─ RTSAILoadScreen.StartGame ─> CompanionHost (OpenRA.Mods.RTSAI)
                                                                 │ picks free loopback ports
                                                                 │ runs companion\rtsai-companion.exe in a Windows job
                                                                 ▼
   CompanionBridge (gRPC, game) <── watch ── rtsai-companion.exe ── runtime serve (gateway) ──> rtsai.net/api/ai/v1
                                                │                     ├─ whisper-server (voice in)
                                                │                     └─ Kokoro (voice out)
                                     settings, provider.json, token: {SupportDir}\ai-companion
                                     logs: {SupportDir}\Logs\ai-companion.*.log, ai-runtime.*.log, companion.log
```

- **Start and stop.** `RTSAILoadScreen` (the upstream logo load screen plus two hooks) calls
  `CompanionHost.Initialize` before the first world and `CompanionHost.Shutdown` when the mod is disposed.
  The sidecar and everything it starts (gateway, whisper-server, llama-server) are in a job object with
  kill-on-close, so they also end if the game crashes or is killed. `--parent-pid` is a second guard.
- **No console windows.** `CreateNoWindow`, stdout/stderr redirected to the log files. Sidecar logs start
  fresh each game session.
- **Ports.** Bridge, console, world studio, gateway, local chat and transcription ports are taken from
  the OS per launch; 4000 is never used.
- **Data.** `OPENRA_AI_DATA_DIR={SupportDir}\ai-companion` holds `host.json` (mode), `settings.json`,
  `provider.json` (hosted install token or External key, both DPAPI-encrypted), feedback drafts and the
  brain journal. The sidecar's TEMP is `ai-companion\tmp`, emptied at every start and stop (the speech
  stack copies `espeak-ng.dll` into a temp folder it cannot delete). `%APPDATA%\OpenRA-AI` is not used.
- **Failure handling.** If `companion\rtsai-companion.exe` is missing, the game runs and the HUD says
  `AI CO-COMMANDER UNAVAILABLE • COMPANION FILES MISSING • GAME UNAFFECTED`. If it exits, it is restarted
  after 2, 4 and 6 s; after three failed restarts in a row the HUD says
  `AI CO-COMMANDER STOPPED • SEE LOGS/AI-COMPANION.ERR.LOG • GAME UNAFFECTED`.
- **Launchers keep working.** With `OPENRA_AI_COMPANION=1` (launch-game.ps1, `tools/run-headless.sh`,
  probes) the host stays out of the way; headless runs never start it. Developers can point the host at a
  frozen bundle (`OPENRA_AI_COMPANION_DIR`) or an OpenRA-AI checkout with a `.venv` (`OPENRA_AI_ROOT`).
  `OPENRA_AI_HOSTED_ENDPOINT` still overrides `https://rtsai.net/api/ai/v1` for rehearsals.

### AI modes (Settings > AI > Assistant > AI mode)

| Mode | Thinking | Voice | Download |
|---|---|---|---|
| Hosted AI + local voice (default) | rtsai.net proxy, Claude Haiku 4.5 | Whisper + Kokoro on the PC | 268,539,880 bytes, SHA-256 verified |
| Full local AI | Qwen3-VL 2B on the PC | Whisper + Kokoro | 1.82 GB ("recommended" profile) |
| External endpoint | any OpenAI-compatible URL with your key | Whisper + Kokoro | voice pack |
| Off | none; no sidecar, no HUD | none | none |

The selector works without the companion. Changing it saves `host.json`, runs the companion's own
`runtime configure` (the External key goes into the DPAPI-protected `provider.json`, never into the game's
settings) and restarts the sidecar. In hosted mode a missing voice pack (portable zip, offline install)
is downloaded on first launch in the background; the HUD idle line shows
`DOWNLOADING LOCAL VOICE nn%` and alerts stay on screen until it is ready.

### Multiplayer policy

The lobby has an **AI co-commander** checkbox (`CompanionLobbyOption`, in `rules/companion.yaml`) that every
player sees and only the host can change. The server trait `CompanionLobbyPolicy` (listed first in
`ServerTraits`) keeps it on with one human and turns it off while two or more humans are in the lobby,
until the host sets it; `reset_options` hands it back to the policy. When it is off for a match, the bridge:

- refuses `Observe` and `CaptureCompanionFrame` (`FAILED_PRECONDITION`), reports `GetState` phase `ai_disabled`;
- rejects confirmed actions and ignores status updates, so AUTO cannot engage;
- shows `AI co-commander disabled for this match` on the HUD, with AUTO and VOICE greyed out;
- the AI hotkeys do nothing.

When the host leaves it on in a multiplayer match, actions are allowed for every player (the old
"single-player only" rule is replaced by this visible option). AUTO still needs the game host, as before.

## Installer options

`RTSAI-<version>-win-x64-setup.exe` (NSIS 3, per-user, lzma solid):

- Pages: welcome, GPLv3, folder, **AI co-commander** (Hosted AI + local voice / Full local AI / No AI),
  components (desktop shortcut), install, finish with "Launch RTS AI".
- Hosted: `rtsai-companion.exe pack install --profile voice-only` runs inside the installer; every
  progress line appears in the details list. A `RTSAI-VoicePack-<version>.zip` next to the setup is used
  first (offline), then the pinned Hugging Face/GitHub URLs. Files are SHA-256 checked before they are
  renamed into place. If the download fails, setup still finishes and the game completes it on first launch.
- Full local: the same with `--profile recommended` (about 1.8 GB). On failure: retry from Settings > AI > Models.
- No AI: no download; the co-commander stays off until chosen in Settings.
- Silent: `setup.exe /S [/AI=hosted|local|none] [/D=<folder>]` (default hosted).
- The choice is written to `<install>\rtsai-install.json` and applied once by the game (`installer_stamp`).
- Start menu `RTS AI` folder (game + uninstall), optional desktop shortcut, per-user
  `openra-rtsai-<version>` join-link protocol, uninstall entry under HKCU with icon, size and version.

**Uninstall** removes exactly the files setup installed (a generated list), the `companion` folder
including downloaded packs, shortcuts, the protocol and the uninstall entry. It schedules removal of
NSIS's own `%TEMP%\~nsuN.tmp` copy. It keeps player data in the OpenRA support folder
(`%APPDATA%\OpenRA` unless `Engine.SupportDir` is set or a `Support` folder sits next to `RTSAI.exe`):

| Kept | Contents |
|---|---|
| `Content\ra2` | the imported RA2 files (`ra2.mix`, `language.mix`, optional `theme.mix`) |
| `ai-companion` | AI mode, companion settings, DPAPI-protected hosted install token (keeps the daily allowance identity) or External key, feedback drafts |
| `settings.yaml`, `Logs`, `Replays`, `maps`, `ModMetadata`, `GeneratedMissions` | normal OpenRA user data |

Delete that folder by hand to remove everything. The portable zip has no uninstaller; delete the folder.

## Building a release (Windows host)

```powershell
# 1. Companion bundle and offline voice pack (OpenRA-AI checkout with .venv + PyInstaller)
..\OpenRA-AI\scripts\package-rtsai-companion.ps1 -OutputDirectory C:\rtsai\payload `
    -VoicePackOutput C:\rtsai\inputs\RTSAI-VoicePack-0.2.0-alpha.1.zip
# 2. Game, installer, portable zip, checksums (NSIS: winget install NSIS.NSIS; rcedit: electron/rcedit releases)
.\make.cmd all
.\packaging\windows\build-release.ps1 -OutputDirectory C:\rtsai\release `
    -CompanionDirectory C:\rtsai\payload\companion -VoicePack C:\rtsai\inputs\RTSAI-VoicePack-0.2.0-alpha.1.zip `
    -RcEdit C:\tools\rcedit-x64.exe
```

`build-release.ps1` is a Windows port of the SDK's `buildpackage.sh` (no wine or ImageMagick): self-contained
win-x64 publish of the pinned engine and the mod, `{DEV_VERSION}` replaced by the release version, the
`RTSAI.exe` launcher built with the RTS AI icon (`packaging/artwork/rtsai.ico`, from the OpenRA-AI brand art)
and stamped with rcedit (product "RTS AI", version 0.2.0-alpha.1 / 0.2.0.1), signing, the portable zip, the
installer and `.sha256` files plus `SHA256SUMS.txt`. The companion bundle is one PyInstaller `--onedir`
folder (about 250 MB) with the pinned llama.cpp/whisper.cpp CPU servers (`ai\runtime`, SHA-256 verified
from `ai-runtime.lock.json`, unused tools removed) and the pack locks. Models are never bundled in it.

Tools used here: NSIS 3.12 (already installed from winget `NSIS.NSIS`), rcedit v2.0.0 from
`github.com/electron/rcedit/releases` (`rcedit-x64.exe`, 1,360,384 bytes, SHA-256 `3e7801db…ade2a`, unsigned).

## Code signing: what the owner sets up

`packaging/windows/sign-windows.ps1` signs every `.exe` in the payload (game, utility, server, companion,
llama-server, whisper-server, `createdump`), the uninstaller (through NSIS `!uninstfinalize`) and the
setup, then checks each signature and timestamp. Without configuration it prints a warning and the build
is unsigned; `RTSAI_REQUIRE_SIGNING=1` (or `-RequireSignatures`) turns that into a failure.
Credentials are read only from the environment or the Windows certificate store; nothing is embedded.

**Option A: Azure Trusted Signing (recommended)**

1. In Azure, create a Trusted Signing account and an identity-validated certificate profile (public trust).
2. Create an app registration (service principal) and give it the role
   **Trusted Signing Certificate Profile Signer** on the account.
3. Install the Windows SDK signtool (`winget install Microsoft.WindowsSDK.10.0.26100`) and download the
   NuGet package `Microsoft.Trusted.Signing.Client`; note the path of `bin\x64\Azure.CodeSigning.Dlib.dll`.
4. Before running `build-release.ps1`, set:

| Variable | Value |
|---|---|
| `AZURE_TRUSTED_SIGNING_ENDPOINT` | the account's region endpoint, e.g. `https://eus.codesigning.azure.net/` |
| `AZURE_TRUSTED_SIGNING_ACCOUNT` | Trusted Signing account name |
| `AZURE_TRUSTED_SIGNING_PROFILE` | certificate profile name |
| `AZURE_TRUSTED_SIGNING_DLIB` | full path to `Azure.CodeSigning.Dlib.dll` |
| `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET` | the service principal (or run `az login` instead) |

Timestamps default to `http://timestamp.acs.microsoft.com`.

**Option B: an OV/EV code-signing certificate**

| Variable | Value |
|---|---|
| `WINDOWS_SIGNING_CERTIFICATE_THUMBPRINT` | SHA-1 thumbprint of a cert with private key in `Cert:\CurrentUser\My` |
| `WINDOWS_SIGNING_CERTIFICATE_STORE` | `CurrentUser` (default) or `LocalMachine` |
| or `WINDOWS_SIGNING_PFX` + `WINDOWS_SIGNING_PFX_PASSWORD` | a `.pfx` file and its password |

Optional for both: `WINDOWS_SIGNTOOL_PATH`, `WINDOWS_SIGNING_TIMESTAMP_URL` (default DigiCert).
Hardware-token EV certificates appear in the certificate store, so option B with the thumbprint works.

## Acceptance evidence (2 October 2026, this machine)

Three builds were exercised: build 1 (full flow, UI), build 2 (after the TEMP and logging fixes: fresh first
launch up to the main menu, uninstall), build 3 (the shipped artifacts: install, skirmish, voice, hosted call,
uninstall). All installs went to fresh folders under the scratchpad with fresh support folders
(`Engine.SupportDir=`), never `%APPDATA%\OpenRA`.

| Check | Result |
|---|---|
| Silent install, default hosted, voice pack downloaded from the pinned URLs | [ran] exit 0 in 42 s; 3 files SHA-verified; uninstall entry, Start menu, desktop shortcut, protocol created |
| Silent install with the offline voice pack next to setup | [ran] exit 0 in 43 s; `pack.json` profile `voice-only` |
| First launch, empty support dir: content installer detects Steam RA2 | [ran, UI] "C&C Red Alert 2 and Yuri's Revenge (Steam version, English)"; `install.log` copied `language.mix`, `ra2.mix` (+`THEME.MIX` when music ticked) from `D:\SteamLibrary\…` |
| Companion starts on mod start, no window | [ran] `companion.log`: installer choice applied, hosted configured, sidecar started in a job, ready, "local voice ready"; `whisper-server` running |
| Settings > AI shows the mode | [ran, UI] "Hosted AI + local voice (recommended)", "Co-commander running (hosted AI + local voice)" |
| Skirmish via the UI, co-commander works | [ran, UI] lobby option "AI co-commander" ticked (1 human); in game the HUD read "AI • I suggest deploying your Mobile Construction Vehicle now…" with ACCEPT/CANCEL |
| Local voice | [ran] Kokoro `/v1/speak` 200,748-byte WAV (5.9 s cold), Whisper transcribed it back verbatim in 0.8 s; build 3: 117,804 bytes, transcript exact |
| Hosted call through a local proxy with mocked upstream | [ran] RTSAI-Web `main` (e24642f) exported to the scratchpad, built with the Node preset, `scripts/mock-anthropic.mjs` as `ANTHROPIC_BASE_URL`, memory store; the game's gateway registered (install `1ad85dc5`) and answered a question via the proxy: 4,281 input / 22 output tokens, $0.004391 by the mock's estimate; route `hosted` |
| Proxy returns 503 | [ran] restarted with `RTSAI_AI_KILL_SWITCH=1`: question answered "Hosted AI is paused right now. Critical alerts continue." (`deterministic-fallback`); HUD "AI ALERTS ONLY • HOSTED AI PAUSED"; feed then logged the alert "Power Plant has completed production." while hosted AI was down |
| Game exit stops everything | [ran] closing the window left no `RTSAI`, `rtsai-companion` or `whisper-server` process; the sidecar TEMP folder was emptied |
| Multiplayer default off | [ran, UI] host created a non-advertised server; when a second client joined, every client saw "AI co-commander changed to disabled" and the unticked option (greyed for the non-host) |
| Disabled match refuses everything | [ran] both clients logged the policy; gRPC probe on both bridges: Observe and frame `FAILED_PRECONDITION`, phase `ai_disabled`, AUTO status not accepted, action "AI co-commander disabled for this match."; HUD showed exactly that text with AUTO/VOICE greyed; companion `/v1/ask` had no snapshot |
| Sidecar crash | [ran] killing it 5 times after it was healthy: restarted each time, game kept running; killing it 4 times before it became ready: HUD "AI CO-COMMANDER STOPPED • SEE LOGS/AI-COMPANION.ERR.LOG • GAME UNAFFECTED", game responding |
| Sidecar missing | [ran] dev build without a `companion` folder: HUD "AI CO-COMMANDER UNAVAILABLE • COMPANION FILES MISSING • GAME UNAFFECTED" (frame captured through the bridge), match at tick 7,884 |
| Uninstall | [ran] all three: install folder gone, uninstall key, Start menu folder, desktop shortcut and protocol gone. Build 1 left `espeak-ng.dll` temp copies and NSIS's `~nsu1.tmp\Un.exe` in `%TEMP%` (both fixed and removed); builds 2 and 3 left nothing from the game in `%TEMP%` |
| `%APPDATA%\OpenRA` untouched | [ran] 407 files, newest 2026-08-21, before and after |
| `make all` / `make test` | [ran] 0 warnings, 0 errors; exit 0 |
| Companion tests | [ran] 312 passed (9 new in `tests/test_mod_runtime.py`); 7 fail on `main` the same way (empty `engine/openra` submodule) |

Not tested:
- The installer's AI options page by mouse (all installs were silent). [inferred: same `$AIMode` path]
- Switching modes in Settings (hosted to local/external/off) and the External key path. [inferred]
- The full local AI install (1.8 GB) and the first-launch voice download for the portable zip. [inferred:
  same `pack_cli` / `LocalAIManager.install` code as tested]
- Push-to-talk with a real microphone (this PC reports no capture device); voice was exercised via HTTP.
- A real rtsai.net or Anthropic call; signing (no certificate here, builds are unsigned).

Observed once, not reproduced: on build 1 the very first launch exited about 10 s after start without a
window, error dialog or log lines; launching again worked, and build 2's first launch on an empty support
folder worked. `%APPDATA%\OpenRA-AI\settings.json` changed at 19:45 local during the session with a
`local` provider; none of these test runs used that folder or that provider.

## Release build 0.2.0-alpha.1 (3 October 2026)

Built from the merged `main` checkouts: RTSAI-Mod `6a39dad` (engine `5523a9907f`; `make all` and `make test`
0 warnings, 0 errors [ran]) and OpenRA-AI `8f8e8c6` (companion frozen with `scripts/package-rtsai-companion.ps1`,
249 MB, no `edge_tts` [ran]). Unsigned. Outputs in the S1 scratchpad `release-final\` [ran]:

| File | Bytes | SHA-256 |
|---|---:|---|
| `RTSAI-0.2.0-alpha.1-win-x64-setup.exe` | 148,223,263 | `2536c1b364b2e35340b91e4aa823a681235130dfc0a88e3ff3bce5d39bda5fbc` |
| `RTSAI-0.2.0-alpha.1-win-x64-portable.zip` | 203,513,064 | `2b0b98c6b339d5ab917f712c69cac04fc5bfeddf594d4288da322339c590f39c` |
| `RTSAI-VoicePack-0.2.0-alpha.1.zip` | 222,741,604 | `55e269c49f7882912c35f31eda6d9dc32903b6857342f3bbd4901ce7db5a5aef` |

The payload has 87 cameos, 555 announcer clips and no `.mix` file [ran].

Acceptance on these exact files, in fresh scratch folders, the game windowed and only while needed:

| Check | Result |
|---|---|
| Silent install (`/S`, default hosted), setup alone | [ran] exit 0 in 40 s; voice pack downloaded from the pinned URLs and verified; uninstall entry, Start menu and desktop shortcut created |
| First launch, empty support folder | [ran] the game started in the content installer (window "OpenRA", responding) and wrote only `ModMetadata` and empty logs. The owner declined screen control, so the import was **not clicked through the UI** |
| RA2 import | [ran, programmatic] a scratch tool hosted the **installed** `OpenRA.Game.dll`/`OpenRA.Mods.Common.dll` (hash-identical) and the installed `rtsai-content` mod, and ran the content installer's own code (sources from `ModContent`, `*SourceResolver.FindSourcePath`, then each package's `*SourceAction`, required packages as the UI preselects). Disc, Origin and TFD not found; Steam found at `D:\SteamLibrary\…\Command & Conquer Red Alert II`; `install.log` copied `language.mix` and `ra2.mix`; base files installed |
| Skirmish as Saudi Arabia | [ran] `Launch.Map` The Alamo, `Launch.Faction=saudi` vs a normal bot. Bridge: `player_faction saudi`, units `r2sang` ×3, `r2saat`, `r2m1a2s`; with AUTO on, a construction yard and power plant by tick 1,770 |
| Skirmish as China | [ran] `Launch.Faction=china`: `player_faction china`, units `r2cnrifle` ×2, `r2cnportable`, `r2qilin` |
| Companion auto-start, local voice | [ran] first mod launch: installer choice applied, hosted configured, sidecar in a job, "co-commander ready", "local voice ready". Kokoro said "Enemy armor spotted near the refinery." (112,684-byte WAV, 5.6 s cold) and Whisper transcribed it verbatim |
| Hosted call through the local proxy | [ran] RTSAI-Web `main` (10a866e) exported to the scratchpad, Node preset, `mock-anthropic.mjs`: a question with two images went through (install `0891a871`, 1,955 / 39 tokens, mock-estimated $0.00215) |
| Proxy answering 503 (`RTSAI_AI_KILL_SWITCH=1`) | [ran] in the China match: "Hosted AI is paused right now. Critical alerts continue." (`deterministic-fallback`), route `none`, HUD "AI ALERTS ONLY • HOSTED AI PAUSED", then the alert "Power Plant has completed production." |
| New icons | [ran] the 87 installed cameos are byte-identical to the repo's painted set. **Not seen in the build palette**: switching to a unit tab needs input, which was not available; the captured Saudi frame shows the structure tab (stock Allied structures) |
| Faction announcer | [ran, logged] in a copy of the portable build with the Saudi announcer folder hidden, a headless Saudi match logged `LoadSound, file does not exist: ra2|modern-factions/audio/eva/saudi/120.wav` (the game-start line from the Saudi announcer); a second headless run from that copy as China logged nothing (its clips loaded). In the real Saudi and China matches `sound.log` stayed empty. Not heard |
| Exit | [ran] closing each window left no game, companion or whisper-server process; the sidecar TEMP folder was emptied |
| Uninstall | [ran] install folder, uninstall entry, Start menu folder, desktop shortcut and join protocol removed. Kept: the support folder (`ai-companion`, `Content`, `GeneratedMissions`, `Logs`, `maps`, `ModMetadata`, `Replays`, `settings.yaml`). `%TEMP%`: nothing from the game; re-running the installer's download step with a private TEMP left nothing either. New entries there came from other work on the machine (puppeteer/remotion, the scratch tool's `dotnet build`) |
| `%APPDATA%\OpenRA*` | [ran] unchanged: OpenRA 407 files (newest 2026-08-21), OpenRA-AI 3 files (newest 2026-10-02T19:35Z) before and after |

Copied RA2 data and every process started for this run were removed or stopped afterwards [ran].

## Files

| Repo | Path | Purpose |
|---|---|---|
| RTSAI-Mod | `OpenRA.Mods.RTSAI/Companion/CompanionHost.cs`, `CompanionProcessJob.cs` | sidecar lifecycle, modes, HUD states |
| RTSAI-Mod | `OpenRA.Mods.RTSAI/LoadScreens/RTSAILoadScreen.cs` | start/stop hooks (`mod.yaml` `LoadScreen`) |
| RTSAI-Mod | `OpenRA.Mods.RTSAI/Traits/World/CompanionLobbyOption.cs`, `ServerTraits/CompanionLobbyPolicy.cs` | multiplayer policy |
| RTSAI-Mod | `Companion/CompanionBridge.cs`, `CompanionService.cs`, `Widgets/Logic/*` | refusal, HUD overlay, AI mode selector |
| RTSAI-Mod | `mods/rtsai/languages/ai-runtime.ftl`, `chrome/settings-ai.yaml`, `rules/companion.yaml` | strings, settings rows, lobby option |
| RTSAI-Mod | `packaging/windows/build-release.ps1`, `rtsai-installer.nsi`, `sign-windows.ps1`, `packaging/artwork/*` | release build |
| OpenRA-AI | `scripts/package-rtsai-companion.ps1`, `apps/launcher/companion_entry.py` | one frozen sidecar (`watch`, `runtime`, `pack`, `game-mcp`) |
| OpenRA-AI | `services/companion/src/openra_ai_companion/pack_cli.py` | verified pack install with progress |
| OpenRA-AI | `settings.py`, `local_runtime.py`, `feedback.py`, `brain.py`, `learning.py`, `model_setup.py` | `OPENRA_AI_DATA_DIR`, `OPENRA_AI_LOG_DIR`, runtime subcommand, first-launch voice download |
