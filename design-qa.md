# Native Library, Customize and Community QA — 16 October 2026

final result: passed

This is native OpenRA C#, following the owner's accepted three-screen direction. Browser CSS, console, phone and RTL tests do not apply. Original game lobbies/HUD/settings are retained as requested. Previous main-menu QA is preserved in docs/frontline-menu-qa-20261015.md.

## Comparison evidence

Evidence root: C:/Users/Admin/Code/hq/games/artifacts/desktop-three-games-design-20261016/.

| Screen | Source visual truth | Native implementation | Paired comparison |
| --- | --- | --- | --- |
| Library | game-library.png | actual-library.png | compare-library.jpg |
| Customize | customize-game.png | actual-customize-classic.png | compare-customize.jpg |
| Community | community-install.png | actual-community.png | compare-community.jpg |

Source images are 1672×941. Library/Community native windows are 1443×841; Customize Classic/RTS windows are 1283×831; RA2/fullscreen captures are 2560×1440 logical pixels. Windows scale is 150%, game UI scale 1. Comparisons remove the Windows title/border (30px top, 1px sides), normalize content to 1280×720, and place source and implementation in one image. The 16:10 Customize native window includes canvas letterboxing; this is not a pixel-identical viewport. Full views and paired 1600×630 focus crops were inspected, covering controls and typography. Real catalog rows differ from illustrative examples. Additional screenshots include actual-customize-ra2.png, actual-customize-rts.png, actual-import-targets.png, actual-fullscreen-confirm.png, actual-ra2-campaigns.png, actual-classic-production.png and actual-ra2-deployed.png.

## Findings, fixes and comparison history

1. P1 fixed: native Settings panels required a concrete Common controller and crashed with the mod's controller. Seven constructors now use the existing ISettingsLogic interface. All seven tabs opened; fullscreen Apply/Keep and timed rollback were tested.
2. P1 fixed: duplicate SupportsMapsFrom root keys disabled authored RA2 campaigns. Each manifest now has one compatible map list. Native campaign list is visible in actual-ra2-campaigns.png and recording 11-ra2.mp4.
3. P2 fixed: Community search was unlabelled. Added Search beside the field, recaptured actual-community.png and repeated full/focused paired comparison. Empty searches now clear selection, detail and the install action; native no-result state was checked separately.
4. P1 fixed during build acceptance: poster dimensions violated the engine atlas contract. Source pixels are preserved with transparent padding to 2048²; visible regions retain original coordinates. Strict standalone validation and rendered posters pass.
5. P2 fixed in final input QA: typed search used the small default game font. Text fields now use the same dynamically scaled Frontline face/color and proportional padding as Library controls. The post-fix native empty-result capture is actual-community-empty.png.

No actionable P0/P1/P2 visual issue remains in the checked desktop states. Native adaptations below are intentional design-system/content constraints, not a claim of exact screenshot reproduction.

## Required fidelity surfaces

- Fonts/typography: reused bundled Frontline Black Ops One display and Chakra Petch Bold controls. Native text is heavier and more stencil-like than the concept. The hierarchy remains readable, without clipped headings or unintended wrapping in checked views. Lighter body weight is P3 follow-up.
- Spacing/layout: three equal poster columns and one main action per game; Customize separates additions from explanation and Save; Community separates a list from requirements/actions. Native presets omit decorative thumbnail strips. Four rows/page fit real catalog content. Rectangular ON/OFF buttons replace illustrated pill switches with explicit selected/focus states. These are intentional native adaptations.
- Colors/tokens: Frontline charcoal, ivory and amber carry background, primary action, selection and focus. Original blue/metal HUD/settings remain inside games, explicitly requested by the owner.
- Image quality: source PNG illustrations/provenance are preserved, padded for native textures. Poster crops match their three subjects; backdrop/wordmark reuse real raster assets. No SVG/CSS/glyph substitute replaces imagery. No distortion/halo appeared. Decorative preset and list thumbnails are omitted to keep real names readable. Community labels illustration NOT GAMEPLAY; actual gameplay is recorded separately.
- Copy/content: real catalog replaces imaginary examples: Classic 17 player rows, RA2/RTS eight each. Authoring contracts remain in Creator Tools. Two verified complete games replace fictional packs. Seven source checkouts have a separate list and no fake Install action. Save applies to new matches; imports name the target game. Technical paths stay outside normal game choice.
- Controls/states: selected/hover/focus/disabled, segmented filters, expanded native faction dropdown, import targets, download requirements and installed actions were inspected. No screen-reader or mobile behavior claim is made.

## Behavior and acceptance

Library launches Classic, RA2 and RTS with independent settings/save roots. Original/Custom round trips retain choices and AI preference. Classic MCV deployment, AI review/apply, construction sidebar and Power Plant placement were exercised. RA2 original-country picker, authored campaigns, China/combined-arms saved setup, MCV deployment and production were exercised. RTS opens its separate setup and retained Creator Tools. Display Keep persists; unattended confirmation reverts; Classic settings stay independent.

OpenHV and Combined Arms were installed through the native utility worker and launched with separate compatible engines. OpenHV's settings were inspected. Combined Arms reaches its first-run setup; telemetry consent is left to the owner. Full utility verification covers identities/settings, profiles, dependency closure, safe extraction, strict standalone art and all four mod/map checks. Missing-Fluent-key warnings use readable fallback text and remain recorded in logs.

## Implementation checklist

- [x] Native entry, three independent game identities, settings and saved custom choices.
- [x] Preserve base menus, controls, custom catalogs and authoring workflows.
- [x] Community install worker, add-on targeting and source-checkout distinction.
- [x] Local build, paired visual comparisons, real native capture and neural-narrated walkthrough.
- [x] Initial acceptance used local builds with no push, deployment, hosted CI or new worktree. Subsequent owner-authorized source publication is recorded in docs/main-publication-20261016.md.

P3 polish: consider lighter body typography and optional preset illustrations if warranted by feedback. Remaining test scope: full multiplayer sessions, every mission/module combination and arbitrary external add-ons are not exhaustively playtested. This work does not restore retail RA2 assets/campaigns or port every Classic module to RA2.
