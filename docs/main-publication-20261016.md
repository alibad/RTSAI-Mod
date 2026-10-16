# Main publication and category index — 16 October 2026

The owner authorized all product repositories to be pushed, including the website main deployment. Existing focused commits and recovery merges are preserved; no shared history was squashed or rewritten. New dependency publication and documentation changes are separate commits.

## Repository boundaries

| Repository | Canonical target | Reviewed main tip | First-parent commits in this publication |
| --- | --- | --- | --- |
| OpenRA | alibad/OpenRA:main | cf2976ffd595 | 15 |
| RTSAI-Mod | alibad/RTSAI-Mod:main | a225e4662110 | 26 |
| OpenRA-AI | alibad/OpenRA-AI:main | b1825e19b1c5 | 5 |
| OpenRA-RL | alibad/OpenRA-RL:main | e7adf2a3a4ec | 5 |
| RTSAI-Art | alibad/RTSAI-Art:main | 5372a9d04cea | 2 |
| RTSAI-Film | alibad/RTSAI-Film:main | ef2c08f0cf88 | 1 |
| RTSAI-WebGame | alibad/RTSAI-WebGame:main | f3979cf76146 | 20 |
| RTSAI-Web | alibad/RTSAI-Web:main | 527cbb2d320d | 4 |

All canonical checkouts were on main and clean at audit, after safe fetch/fast-forward. No local branch or live worktree HEAD was outside its canonical main ancestry, and no live worktree contained nonignored uncommitted files. One RTSAI-WebGame worktree registration points to a missing directory; its release branch is contained in main and the registration was retained. Recovery refs/archive resources remain preserved. No branch/worktree was deleted.

The OpenRA engine is published first; RTSAI-Mod mod.config and both companion/training engine gitlinks then point to cf2976ffd59587d6efb1faaf5d0b00089eb7a052. Accepted browser payloads remain selected by their existing receipt; publishing source does not replace the accepted local game or release rtsai.net/play.

## Commits by category

### Artwork and audio

- RTSAI-Mod [bd2fb98737](https://github.com/alibad/RTSAI-Mod/commit/bd2fb98737c287da3b8e003d9bb8b4f5bd0b1103): Export library artwork on engine-compatible chrome sheets

### Browser game and local launcher

- RTSAI-WebGame [0351008435](https://github.com/alibad/RTSAI-WebGame/commit/0351008435a52a7d0f8bd83f438b785d7e1833f4): Keep the accepted game AI bridge separate from obsolete previews
- RTSAI-WebGame [8eb81516a1](https://github.com/alibad/RTSAI-WebGame/commit/8eb81516a11c0c3ddfc85150fd1ca50bf9d941df): Keep web adviser wording consistent and target browser-only runtime dependencies
- RTSAI-WebGame [a039e70a4d](https://github.com/alibad/RTSAI-WebGame/commit/a039e70a4df36934d211574021eff0b82daec341): Keep the adviser explanation and touch target fully visible on phones

### Community games and add-ons

- RTSAI-Mod [f349196e00](https://github.com/alibad/RTSAI-Mod/commit/f349196e001d808f33c9afa42c10d7b7ae7f1fdb): Build native three-game library, customization and community installation
- RTSAI-Mod [f8ff4df450](https://github.com/alibad/RTSAI-Mod/commit/f8ff4df4507dadb7f55c461941b35e7bc4ba402f): Keep community installations running in an isolated download worker
- RTSAI-Mod [044d8a0626](https://github.com/alibad/RTSAI-Mod/commit/044d8a0626437873868f1317c3ccfbca959ea115): Persist per-game choices and harden display and community recovery
- RTSAI-Mod [63671ff5c9](https://github.com/alibad/RTSAI-Mod/commit/63671ff5c9d8fd4d9a647f4e132aa890f84af766): Launch community games with their own engine paths and support directory
- RTSAI-Mod [91cab962e5](https://github.com/alibad/RTSAI-Mod/commit/91cab962e5726770f5e70ba93efab9f8f50dc187): Reuse installed freeware content for the isolated Combined Arms runtime
- RTSAI-Mod [aa67d276e5](https://github.com/alibad/RTSAI-Mod/commit/aa67d276e52884714ba116a09cbe82cf92b09a8f): Clarify native community search and package import

### Engine and dependency compatibility

- OpenRA [490464b176](https://github.com/alibad/OpenRA/commit/490464b176daf236a7ba98bd93dc5609bab4379e): Use native numerics vector for fitted image dimensions
- OpenRA [27c5038ab9](https://github.com/alibad/OpenRA/commit/27c5038ab9ece4aecb50d7ff5d667cfbe4fee951): Keep the desktop external bot server out of browser WebAssembly builds
- OpenRA [cf2976ffd5](https://github.com/alibad/OpenRA/commit/cf2976ffd59587d6efb1faaf5d0b00089eb7a052): Let native settings panels use the shared settings controller interface
- RTSAI-Mod [a225e46621](https://github.com/alibad/RTSAI-Mod/commit/a225e46621103fdb05ddf20bdc6a3d165753d7f9): build: pin the published canonical engine for native Library settings
- OpenRA-AI [b1825e19b1](https://github.com/alibad/OpenRA-AI/commit/b1825e19b1c503ac0cb46dabbc6c1a30283328de): build: align the engine submodule with published canonical main
- OpenRA-RL [e7adf2a3a4](https://github.com/alibad/OpenRA-RL/commit/e7adf2a3a4ec8b0bc79278846aac1965078dccf8): build: align the engine submodule with published canonical main

### Engine and game systems

- OpenRA [dd599f2233](https://github.com/alibad/OpenRA/commit/dd599f22337e75fc099f94652b277c23e042f066): Unify native Classic and shared desktop-browser engine on main
- OpenRA [21440b9137](https://github.com/alibad/OpenRA/commit/21440b9137bfe13ecaab92355d1482a98b10b1ad): Keep owned-RA2 prompts scoped to the optional legacy content pack

### Game content and recovery

- RTSAI-Mod [4e7799ae90](https://github.com/alibad/RTSAI-Mod/commit/4e7799ae9070a1b396842d74241be14eb397d2d2): Keep owned-RA2 prompts scoped to the optional legacy content pack

### Native Library and per-game customization

- RTSAI-Mod [7abcf935dc](https://github.com/alibad/RTSAI-Mod/commit/7abcf935dc9a43e980cce6eecb51809808ae85d1): Connect RA2 campaigns and make enhanced and experimental presets distinct
- RTSAI-Mod [e2b157837d](https://github.com/alibad/RTSAI-Mod/commit/e2b157837ddb790bc5d86577e816301cce0d1e69): Scale native Library text entry with its controls

### Native settings and game UI

- OpenRA [7e0d952724](https://github.com/alibad/OpenRA/commit/7e0d952724d26715cfa93a87c0f6e160caaa1a90): Restore shared asset-library and Classic AI settings labels
- OpenRA [4447781a96](https://github.com/alibad/OpenRA/commit/4447781a96c408788cbdb6f7c2ef2fd526d7a39e): Fit faction flag sprites within native UI slots
- RTSAI-Mod [923ff48f19](https://github.com/alibad/RTSAI-Mod/commit/923ff48f19cdbf73526b4ef41f48f0a66c8aee77): Recognize the shared RA2 mode label without allowing owned-content requirements
- RTSAI-Mod [75e232cebe](https://github.com/alibad/RTSAI-Mod/commit/75e232cebed215f938a699b7cbe122554ad0fb13): Restore shared asset-library and Classic AI settings labels
- RTSAI-Mod [f9b959c0d4](https://github.com/alibad/RTSAI-Mod/commit/f9b959c0d4e942a42a69070dd0e7a383fa786168): Make paused matches obvious and fix native mode UI feedback
- RTSAI-Mod [748790a497](https://github.com/alibad/RTSAI-Mod/commit/748790a4972b864c798efd85fa2114bf2166b389): Connect the AI and display panels to the native settings controller
- RTSAI-Mod [385406d631](https://github.com/alibad/RTSAI-Mod/commit/385406d6318fdef840a6f14bbdd5c6d786257716): Bind the product AI panel explicitly and remove duplicate map declarations

### Preservation and main-branch policy

- OpenRA [729f9d24cd](https://github.com/alibad/OpenRA/commit/729f9d24cd859a84ff9a2b36ab78ed560b35a754): Require explicit owner request before using worktrees
- OpenRA [6006174b70](https://github.com/alibad/OpenRA/commit/6006174b70a6de02744bcf5415bd829d76b80064): Consolidate codex/upstream-sync without regressing current game systems
- OpenRA [54a15ffc57](https://github.com/alibad/OpenRA/commit/54a15ffc5739ec9ea6649a35279fa0b105d91700): Consolidate rtsai/engine-bakemap without regressing current game systems
- OpenRA [3f84571900](https://github.com/alibad/OpenRA/commit/3f845719005cbf83d327f49a5c8c818a6268ed13): Consolidate bleed without regressing current game systems
- OpenRA [3666554434](https://github.com/alibad/OpenRA/commit/366655443482f4995afd72796b27f10d547045e6): Consolidate refs/recovery/submodules/rl-engine/bleed without regressing current game systems
- OpenRA [8f27de874f](https://github.com/alibad/OpenRA/commit/8f27de874fe79eb194072142e60ee1a0227941bb): Preserve old nested air-warfare variants alongside current integrated systems
- OpenRA [7a38b34572](https://github.com/alibad/OpenRA/commit/7a38b34572bff6b80ece5c9451394809ed32c965): Record preserved historical air-warfare branch after archiving its variants
- OpenRA [58a6753605](https://github.com/alibad/OpenRA/commit/58a6753605c9282d6c82a2bf4e5e637da78347cc): Use canonical main checkouts and preserve recovered engine work
- RTSAI-Mod [1230e42462](https://github.com/alibad/RTSAI-Mod/commit/1230e42462ae21974d7cf6a0f2e6091aba08c9e9): Require explicit owner request before using worktrees
- RTSAI-Mod [a9d8a792c6](https://github.com/alibad/RTSAI-Mod/commit/a9d8a792c672dc87537403f4d0c28eea43b2a779): Consolidate preserved work into canonical main
- RTSAI-Mod [83192629df](https://github.com/alibad/RTSAI-Mod/commit/83192629df85fc7fd833f31cae15a5fa80e1aff2): Use canonical main checkouts and preserve recovered engine work
- RTSAI-Mod [317a762722](https://github.com/alibad/RTSAI-Mod/commit/317a7627228f0bd6212e9b83e4e54364907118e0): Keep product companion and menus authoritative with the consolidated engine
- RTSAI-Mod [85a2cd8ba6](https://github.com/alibad/RTSAI-Mod/commit/85a2cd8ba6f4257789152a08010a7844cf2101bd): Keep the preserved RA2 content addon on the shared native menu
- RTSAI-Mod [bb1482599c](https://github.com/alibad/RTSAI-Mod/commit/bb1482599c664dd4fb1462ecfc500bd06978195d): Preserve legacy game data in independent support folders and fix native UI compilation
- RTSAI-Mod [a496e0704a](https://github.com/alibad/RTSAI-Mod/commit/a496e0704ac0545a06f6841da2d03453ef438ad8): Preserve both RA2 and project campaign compatibility in new game identities
- OpenRA-AI [7e2a9ef194](https://github.com/alibad/OpenRA-AI/commit/7e2a9ef1941f47a859fa212b6538f102f58edc9f): Require explicit owner request before using worktrees
- OpenRA-AI [1cb6e1b415](https://github.com/alibad/OpenRA-AI/commit/1cb6e1b4152c06d1cbc3a3fbd4c56e639813dd28): Align nested engine checkout with consolidated canonical main
- OpenRA-AI [da6e8749e9](https://github.com/alibad/OpenRA-AI/commit/da6e8749e9e3f8393c56b6bd8ad1e30073c3737e): Keep nested engine main in sync after standalone verification fixes
- OpenRA-AI [ea89ae2e70](https://github.com/alibad/OpenRA-AI/commit/ea89ae2e703e71d9f055546c2836850b27e9ec16): Synchronize nested main with final consolidated engine labels
- OpenRA-RL [48d41c1d79](https://github.com/alibad/OpenRA-RL/commit/48d41c1d79c1e1e75c4f2c600a2901b89cf9351d): Require explicit owner request before using worktrees
- OpenRA-RL [7789c60e20](https://github.com/alibad/OpenRA-RL/commit/7789c60e20b2675462d97673b1c2e82867912f2e): Align nested engine checkout with consolidated canonical main
- OpenRA-RL [5617ea5a50](https://github.com/alibad/OpenRA-RL/commit/5617ea5a50fbf89db1794755d560695658c23f10): Keep nested engine main in sync after standalone verification fixes
- OpenRA-RL [49dfd9e9e5](https://github.com/alibad/OpenRA-RL/commit/49dfd9e9e51c45b7c5bb8b10d3b9bb61b24884ba): Synchronize nested main with final consolidated engine labels
- RTSAI-Art [f860e5da61](https://github.com/alibad/RTSAI-Art/commit/f860e5da61c68c65b58d0a3f42297e65ffb13e9c): Require explicit owner request before using worktrees
- RTSAI-Art [5372a9d04c](https://github.com/alibad/RTSAI-Art/commit/5372a9d04ceaf7d0dcc9b3ef9bd2a35cc7020aee): Consolidate preserved work into canonical main
- RTSAI-Film [ef2c08f0cf](https://github.com/alibad/RTSAI-Film/commit/ef2c08f0cf88451520aabd3d4656c81afc7b7bcd): Require explicit owner request before using worktrees
- RTSAI-WebGame [4af7b87ed5](https://github.com/alibad/RTSAI-WebGame/commit/4af7b87ed594833d593dad72f6943313f591d3a5): Require explicit owner request before using worktrees
- RTSAI-WebGame [681fcc583a](https://github.com/alibad/RTSAI-WebGame/commit/681fcc583aea713528eea3ad22b4bf9a0bd5d363): Integrate outstanding feature work into canonical main
- RTSAI-WebGame [003b86ad92](https://github.com/alibad/RTSAI-WebGame/commit/003b86ad9247606754ab66fd6dbc63e279cd2e47): Recover uncommitted terrain and map verification work from old worktrees
- RTSAI-WebGame [a6b4b02f54](https://github.com/alibad/RTSAI-WebGame/commit/a6b4b02f54d0b81137045ee85af48fa3fb5438cc): Preserve complete UI bodies when reconciling feature branches
- RTSAI-WebGame [19e924ed02](https://github.com/alibad/RTSAI-WebGame/commit/19e924ed02b879f4eb05ee4f67b0d0bfec1b0a85): Record already-integrated fix/tesla-sound history on main
- RTSAI-WebGame [8311e63e9a](https://github.com/alibad/RTSAI-WebGame/commit/8311e63e9a6449440f1fca778f736899fcd1e848): Record already-integrated release/web-20261014c history on main
- RTSAI-WebGame [be671d3ae2](https://github.com/alibad/RTSAI-WebGame/commit/be671d3ae280b47f8dea714f90ed529d6c33360d): Record already-integrated codex/preserved-main-20261015 history on main
- RTSAI-WebGame [f4c16b5272](https://github.com/alibad/RTSAI-WebGame/commit/f4c16b527224bbb2a56218f52c662f664342cc3f): Record already-integrated origin/rtsai/vision history on main
- RTSAI-WebGame [a6b904b518](https://github.com/alibad/RTSAI-WebGame/commit/a6b904b51800710f38f424b30b39d53dfa8481d9): Use canonical main checkouts and preserve recovered engine work
- RTSAI-WebGame [e6df42d2c6](https://github.com/alibad/RTSAI-WebGame/commit/e6df42d2c63a7ed8ea842f875b805d966ee14ede): Keep the browser host compatible with consolidated native engine interfaces
- RTSAI-WebGame [87dc711b35](https://github.com/alibad/RTSAI-WebGame/commit/87dc711b35715addd104091468f05cd7a1db0e8a): Launch only the verified local game and preserve complete workspace backups
- RTSAI-WebGame [12a848608e](https://github.com/alibad/RTSAI-WebGame/commit/12a848608eaaabd2974e3d581a7ab7c2ecbcd389): Preserve adviser opt-outs and reject failed local model rechecks
- RTSAI-Web [3a6879a32f](https://github.com/alibad/RTSAI-Web/commit/3a6879a32f5a9f6e373119b52dbac1451968d1ce): Require explicit owner request before using worktrees
- RTSAI-Web [7df4d4cd72](https://github.com/alibad/RTSAI-Web/commit/7df4d4cd7231479f958ac8954689aa2faf556ff8): Integrate outstanding feature work into canonical main
- RTSAI-Web [3e3e7198fd](https://github.com/alibad/RTSAI-Web/commit/3e3e7198fd15f4679716e998b1a70683c82dabf0): Preserve complete UI bodies when reconciling feature branches

### Verification and documentation

- RTSAI-Mod [271c95f5f5](https://github.com/alibad/RTSAI-Mod/commit/271c95f5f5cced520a49d6430420b9563b317753): Verify all three native games and their library together
- RTSAI-Mod [b59393f696](https://github.com/alibad/RTSAI-Mod/commit/b59393f69626c3681946309e8438eece968186b0): Verify display and audio isolation and keep empty searches actionable
- RTSAI-Mod [3b0781a4c6](https://github.com/alibad/RTSAI-Mod/commit/3b0781a4c64faccb4bdc40aa04535b3956c41516): Document native Library acceptance and actual walkthrough coverage
- RTSAI-WebGame [19b5acbd56](https://github.com/alibad/RTSAI-WebGame/commit/19b5acbd565f3a24287feb8353ce10d60fd35381): Freeze accepted scenario files and verify native replay dependencies
- RTSAI-WebGame [c69146dd3f](https://github.com/alibad/RTSAI-WebGame/commit/c69146dd3fd1469465e39cb555a92ea3667bfd5a): Simplify web play to a built-in adviser and verify local model readiness
- RTSAI-WebGame [14e73cc9b9](https://github.com/alibad/RTSAI-WebGame/commit/14e73cc9b9143c4324b2bc01a1924b6f3278c1b1): Verify voxel-only scenes in browser adviser acceptance
- RTSAI-WebGame [8151b3d1c8](https://github.com/alibad/RTSAI-WebGame/commit/8151b3d1c83e01607e19259db6bae86f61622f2f): Exercise adviser settings and touch confirmation in the public game
- RTSAI-WebGame [f3979cf761](https://github.com/alibad/RTSAI-WebGame/commit/f3979cf7614620bd954ecb9e7586ecd4f8aa63ee): Record the simplified accepted web build and matching runtime recipe

### Website and Studio

- RTSAI-Web [527cbb2d32](https://github.com/alibad/RTSAI-Web/commit/527cbb2d320db31f35a2bc9b786af23f9ff277bb): Start Studio play through the verified canonical web-game launcher

## Verification and exclusions

The native desktop build/rules/profile/settings/standalone validation and actual capture evidence are documented in design-qa.md and docs/native-library-walkthrough.md. Website typecheck, lint, build and tests are rerun before its deployment push; deployment status and commit identity are checked afterward. Dependency changes use the same engine tree already built and exercised in the native walkthrough.

Generated runtimes, downloaded community binaries, support data/saves, model weights and raw walkthrough recordings remain local artifacts rather than source commits. The full categorized history is on main; source assets and their provenance remain tracked. This index describes source publication, not a claim that every historical module is ported or every mission/multiplayer combination playtested.

The full snapshot and publication/deployment verification logs are in C:/Users/Admin/Code/hq/games/artifacts/desktop-three-games-design-20261016/. The documentation commit adding this index follows the listed source tips.
