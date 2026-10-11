# Mac alpha — 11 October 2026

The owner authorized publishing the exact locally accepted S07 candidate as a separate Mac prerelease. The existing Windows v0.4.0-alpha.2 assets and version remain unchanged.

Release tag: `v0.4.0-macos-alpha.20261011`. The package's internal version is `s07-native`; no binary was renamed internally or rebuilt for this publication.

Artifact: `RTSAI-s07-native-macos.dmg`, 258,421,906 bytes, SHA-256 `8abe4af498ce6fbfc95b27cb7d4065f877ab57626cb3a79d8fdfa61e902f2199`.

Requirements and limits: macOS 15 or later; universal Apple Silicon/Intel game binaries; bundled companion supports ARM64 Apple Silicon only. The app is ad-hoc signed and not notarized. Another Mac/Gatekeeper and Intel execution remain pending. No local chat, ASR or TTS neural runtime/model is included, hosted requests remain disabled, and microphone conversations were not demonstrated.

Both standalone modes, rendered play, save/load, voice settings, explicit reviewed deploy and 38 assisted campaign cases per mode passed on the development Mac. These do not establish unaided human playthrough, competitive balance, other-device acceptance or fluent listening approval.

The game uses fixed engine `aed51fe4b1c699b487b9f9683dbc79215f3a96be`. Tested Mod/content inventory: `b153198307187e65de2f5019ce44e5d840644e17984baaebcf9974f9dbdb5602`. Subsequent source differences are helper-comment cleanup and this release note, with no packaged gameplay/runtime changes.

Seven accepted aliases retain project-audio provenance in `mods/rtsai/standalone/audio/cue-alias-contract.json`. Pending animal auditions stay outside the package; fluent review remains pending. The native isolation audit records a default app launch that touched normal OpenRA support files; those files were preserved and final acceptance was bound to an explicit private-support launch.

Install the DMG only after comparing its checksum. Copy RTS AI.app to Applications, attempt to open it, then use System Settings > Privacy & Security > Open Anyway if macOS blocks this unnotarized alpha. Test both Game modes, a bot skirmish, save/load, faction/English voice preference persistence and No AI manual play. On Intel, test the game without relying on the ARM64 companion. Record package hash, OS/CPU, mode/map/faction and reproduction steps for any failure. Fresh-device, real-network, human campaign/balance and listening checks remain acceptance work.
