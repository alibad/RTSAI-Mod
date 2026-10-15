# Frontline native desktop menu — 15 October 2026

The owner selected the first displayed visual proposal. The native OpenRA shell
now uses its cinematic battlefield, distressed wordmark, cream Play control,
compact Classic/RA2 switch and text navigation. No browser or webview is involved.

`RTSAIFrontlineMainMenuLogic` adapts the existing OpenRA `MainMenuLogic` state
machine. Play and Skirmish use the real local lobby, Campaign uses the established
mission browser, and Multiplayer uses the established connection/browser flow.
Their existing on-start and on-exit callbacks still own the game lifecycle.
Settings returns to the same main menu rather than revealing a second launcher.

Experience opens each mode's existing composer. Tools retains saved games,
replays, music, map editing, asset browsing and credits; Classic also exposes the
native Mission Studio. Game packs retains the compatibility-reviewed library.
The current settings, lobby and authoring panels are preserved; this selection
implements the main-menu design rather than claiming every panel was restyled.

The two real foundations, their rules, sprites, HUDs, custom content and saved
preferences remain independent. There is no new engine or replacement game.
Mode changes clear the previous shell lobby-return state before reinitializing
the selected foundation, so the menu does not inherit the other mode's lobby.

The layout scales from the selected 1672x941 design coordinates. UI assets remain
separate from actual controls, including hotkeys, hit targets, disabled states,
hover colors and the selected-mode underline. A left-anchored crop protects
menu readability in narrower aspect ratios. The new font and texture resources
are packaged locally, with source images, generation prompts and font licenses.

Build and launch through the existing canonical paths:

```
powershell -NoProfile -ExecutionPolicy Bypass -File tools/build-desktop-recovery.ps1
launch-game.cmd
```

`recovery.local.json` selects the exact local runtime. The RTS AI desktop shortcut
already uses this launcher. No web release, deployment, push or engine repin was
performed. New upstream campaign, civilian and sound commits were merged into
local main before implementation; the existing recovery work was retained.

Acceptance evidence is in `../artifacts/frontline-native-20261015/`. Tests use
isolated support directories, call the real menu handlers and capture real native
windows. Settings/profile isolation and all eight rule profiles passed. Strict
standalone checking passed without warnings. RA2 lint passed; Classic lint kept
the same 44 pre-existing warnings. A live older Classic match was left running.

See `../design-qa.md` for comparison evidence and remaining minor differences.
