# Frontline native menu QA — 15 October 2026

final result: passed

**Comparison target and evidence**

- Source visual truth: `C:/Users/Admin/Code/hq/games/RTSAI-Mod/docs/frontline-menu-assets/selected-reference.png`, the first displayed proposal selected by the owner; 1672x941 pixels.
- Native implementation: `C:/Users/Admin/Code/hq/games/artifacts/frontline-native-20261015/live-game-window.png`; 1942x1136 window capture, including Windows chrome. Client content is 1920x1080, from a 1280x720 logical window at Windows display scale 1.5 and game UI scale 1.
- Normalized content: `C:/Users/Admin/Code/hq/games/artifacts/frontline-native-20261015/game-menu.png`. The 11px side/bottom borders and 45px title area were removed. A comparison-only copy was downsampled to 1672x941; the application assets were not stretched or retouched for QA.
- State: RA2 selected, main menu, enabled Play, idle pointer. Source and implementation were opened together in the same comparison image.
- Full-view evidence: `C:/Users/Admin/Code/hq/games/artifacts/frontline-native-20261015/comparison-live.png`.
- Focused controls evidence: `C:/Users/Admin/Code/hq/games/artifacts/frontline-native-20261015/comparison-controls-final.png`.
- Focused pack-control evidence: `C:/Users/Admin/Code/hq/games/artifacts/frontline-native-20261015/comparison-packs.png`.
- Narrow-screen evidence: `C:/Users/Admin/Code/hq/games/artifacts/frontline-native-20261015/home-4x3-final/window-020.png`; 1024x768 logical window, requested game UI scale 1.5, 1536x1152 client pixels.
- This is a C# OpenRA application. Browser CSS size, browser console and phone breakpoints do not apply. Native stdout/stderr and real window captures were inspected instead.

**Required fidelity surfaces**

- Fonts/typography: the distressed wordmark is a separate generated raster asset. Actual controls use bundled OFL Black Ops One and Chakra Petch Bold, with discrete font sizes chosen for the effective UI scale. The Play hierarchy, navigation weight, tracking and single-line labels match the selected direction. Native font rasterization and letter shapes differ slightly from the generated reference. No clipping or unintended wrapping in the checked viewports.
- Spacing/layout: logo, compact mode selector, primary plate, secondary actions and lower pack access retain the reference proportions and alignment. Authored coordinates reflow from a fixed baseline rather than accumulating rounding errors. A left-anchored backdrop crop protects dark texture behind controls at 4:3. Tools and Experience are intentional quiet additions to retain custom workflows.
- Colors/tokens: ivory text and button, warm battlefield, dark rocky left side and amber selected-mode underline replace the teal dashboard treatment. Hover uses amber text/marker; Play has an amber hover edge. Disabled tools retain a distinct dim state.
- Image quality: battlefield, wordmark, plate, chevron and puzzle are actual generated raster assets, not HTML, SVG, text-symbol or code-drawn art substitutes. Original source PNGs are preserved. Engine texture packaging adds only transparent padding. No broken image, visible transparency halo or distorted vehicle appeared in native captures. Slight generated-art variation from the approved image remains P3.
- Copy/content: primary labels are PLAY, CAMPAIGN, SKIRMISH, MULTIPLAYER, SETTINGS, QUIT, CLASSIC and RA2. Technical provenance and recovery explanations were removed from the main menu. The optional slogan in the mock was intentionally omitted. Existing product content remains in its own settings, composer and tools screens.
- Icons: the generated chevron and puzzle match the target's material and optical weight. The puzzle is drawn inside the Game packs button, so the icon and text share one hit target. The extra tiny trailing pack chevron in the mock is omitted as redundant, P3.

**Comparison history**

1. Initial comparison: `comparison-main.png` and `comparison-controls.png`. P2: Play lettering was too small relative to its plate. Fixed the authored display size from 56 to 72 and added larger native font sizes. Post-fix evidence: `comparison-final.png` and `comparison-controls-final.png`.
2. Narrow-screen review: `classic-tools-4x3/window-016.png`. P2: centering the battlefield crop removed too much of the dark left region. Changed the cover focus to the left edge. Post-fix evidence: `home-4x3-final/window-020.png`; labels remain readable and all main actions fit.
3. Control review: P2: puzzle icon had been a separate non-interactive sibling outside the pack button. Integrated the icon into the button and expanded its hit target. Post-fix evidence: `comparison-packs.png` and `live-game-window.png`; unchanged visual position with a unified native button.
4. Final full-view and focused comparisons above: no actionable P0/P1/P2 visual findings remain.

**Native behavior and validation**

- Successful local Release builds, zero compiler warnings/errors.
- Actual Play handler opens the real skirmish lobby; Campaign opens the actual mission browser; Multiplayer opens its established browser.
- Native display settings, composer and Tools render successfully. The selected main-menu design does not claim to restyle those panels.
- Settings, Campaign and Game packs return through their real Back/Close callbacks to Frontline. Explicit native return assertions passed.
- Both real foundation reloads passed: RA2 to `rtsai-classic-core`, and Classic to `rtsai`. Selected-mode treatment appears in the rendered windows.
- Classic Tools retains Mission Studio; its existing native panel opened. Earth/companion service availability is separate from menu navigation and was not established by that UI smoke test.
- All eight mode/profile rule sets and independent settings/profile/voice round trips passed.
- Strict standalone checking: zero warnings. RA2 YAML lint: no errors/warnings. Classic YAML lint: no errors, 44 existing warnings.
- Reports/logs/screenshots: `C:/Users/Admin/Code/hq/games/artifacts/frontline-native-20261015/`.
- Native game buttons are used throughout this menu; there is no HTML select. No dropdown popup was redesigned here. Existing settings pickers retain their existing native behavior; this QA does not label their expanded menus as newly polished.
- Review window uses a copy of player preferences and a separate support directory. The existing Classic match was left running. Companion autostart is disabled only for the concurrent review window to avoid competing with that match. The canonical desktop launcher retains its normal companion behavior.

**Open questions and follow-up polish**

- P3: optional refinement of the generated wordmark edge texture, exact font letter shapes and pack chevron.
- Existing settings/lobby/workbench visual systems are outside this selected main-menu frame and remain candidates for a later explicitly selected design pass.
- Gameplay balance, campaign completion, external multiplayer connectivity, neural voice quality and full Arabic localization were not retested by this menu change. No such coverage is claimed.

**Implementation checklist**

- [x] Selected visual mapped to real native controls and local assets.
- [x] Main actions, settings, composer and custom tools retained.
- [x] Both mode switches and return paths checked in real native windows.
- [x] Full-view and focused comparisons inspected; P2 findings corrected.
- [x] Assets, original images, prompts and font licenses saved in the project.
- [x] Local-only delivery; no web release or deployment.
