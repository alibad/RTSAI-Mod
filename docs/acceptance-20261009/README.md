# Native campaign, roster and voice acceptance — 9 October 2026

[Interactive report](index.html) · [Machine-readable evidence](evidence.json).

This is local native acceptance of original-content Classic and RA2. It does
not claim completed human playthroughs, competitive balance, browser acceptance
or fluent pronunciation approval.

- **228/228 campaign conditions passed**: six missions, two modes, three
  difficulties. Covers wins, army wipes, each required protected target,
  destroyed capture targets, convoy losses, surveillance failure, optional
  protection loss, escort survivor thresholds, amphibious counts and undeployed
  specialists. Replay difficulty and final winning objective statuses verified.
  Assisted fixtures seed buildings/units, transfer capture targets and remove
  combat pressure. They use actual movement/timers and never mark objectives
  complete/failed. Deployment fixtures seed the requested state.
- **160/160 bot matches completed without errors**. All sixteen factions
  produced units in both modes. RA2: 128 mirrored games on two project maps,
  two replicates. Classic: 32 mirrored games on one project map, one replicate.
  Normal bots, no owned content, ten-minute simulated cap.
- **140 capped draws** (111 RA2, 29 Classic) limit balance conclusions.
  Each faction faces two opponents, not fifteen. Custom modern factions won
  16 of RA2's 17 decisive games. Review bot economy/production/composition before
  attributing that to unit strength. No balance stats were changed.
- **126/126 non-English clips passed integrity checks** and fresh
  forced-language ASR with pinned Whisper large-v3 revision
  edaa852ec7e145841d8ffdb056a99866b5f0a478.
  Listening priorities: hz-scout-move-ar.wav, il-inf-attack-he.wav,
  il-recon-select-he.wav. Mandarin rcn-air-select-zh.wav differs only in
  traditional/simplified script; raw CER is retained. Another 43 clips have
  existing review notes or low-confidence words. **0/126 fluent approvals**.
  Reviewers are needed for Lebanese/Saudi/Yemeni Arabic, Hebrew, Persian,
  Turkish and Mandarin. The report plays original clips and exports decisions.

Fixes: finalize optional protection before victory; expose campaign difficulty;
use project-generated square Classic shroud/fog masks; preserve production rules
in smoke fixtures; keep generators consistent. Original RA2 masks, voice audio,
custom resources and provenance remain unchanged. No checkout was created or
retired; no public browser bundle, website or Windows installer was redeployed.

Release build passed with zero warnings/errors; make.cmd test, Classic YAML and
strict standalone checks, and ten harness regression tests passed. Rendered
Jizan checks passed in both modes; Classic was rechecked after the mask fix and
its winning fixture passed again. HTML IDs, JavaScript syntax, all audio paths/
hashes and evidence totals were checked. The browser tool blocked file-protocol
inspection, so the report itself lacks browser visual/interaction sign-off.

Human campaign combat/economy/pacing and deploy UI, longer all-pairs/human balance
including air/naval coverage, fluent voice review and browser-specific acceptance
remain open. Public release packaging can be refreshed when requested.

Raw logs, fixtures and replays: D:/rtsai-acceptance-20261009.
The 228 cases combine 33 original cases plus five threshold cases per mode/
difficulty. The runner now includes thresholds in full runs. One early survivor
fixture erroneously attacked the later convoy; its corrected rerun supersedes
it, with original evidence preserved.

From canonical RTSAI-Mod:

    ./make.cmd all
    ./make.cmd test
    python tools/test_campaign_acceptance.py
    python tools/test_balance_harness.py
    python tools/campaign-acceptance.py --mod rtsai --difficulty normal --output D:/rtsai-new-run/ra2-normal
    python tools/campaign-acceptance.py --mod rtsai-topdown --difficulty hard --output D:/rtsai-new-run/classic-hard
    python tools/balance-harness.py run --campaign roster-20261009 --campaigns-file tools/acceptance-campaigns.json --standalone --output D:/rtsai-new-run/roster --keep-support
    python tools/balance-harness.py run --campaign classic-roster-20261009 --mod-id rtsai-topdown --campaigns-file tools/acceptance-campaigns.json --standalone --output D:/rtsai-new-run/classic-roster --keep-support
    python tools/acceptance-report.py

Voice auditing uses tools/voice-acceptance.py in the existing local voice
environment. Human testing uses launch-game.cmd, then the in-game mode choice,
campaign and difficulty.
