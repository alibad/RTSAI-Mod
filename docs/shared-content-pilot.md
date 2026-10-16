# Shared content pilot — 16 October 2026

One reviewed source (`content/shared-content.json`) compiles a build-cost override
for four explicit targets. The current pilot changes the Engineer to **625**.
Classic desktop's inherited value is 400; the other three bindings inherit 500.
The original rule files, resources and review history remain intact.

| Target | Manifest | Actor |
| --- | --- | --- |
| Classic desktop | rtsai-classic-core | E6 |
| Classic web adapter | rtsai-topdown | engineer |
| RA2 desktop | rtsai-ra2 | engineer |
| RA2 web | rtsai | engineer |

**The browser Classic adapter is not the recovered desktop Classic foundation.**
This pilot proves an explicit shared edit across today's four runtimes. It does
not establish identical rosters, artwork, missions or simulation between the two
Classic implementations. That foundation port remains separate work. RA2 here is
the existing OpenRA modification, not the original Westwood executable.

## Edit and restore

`python tools/shared-content.py show` prints the current revision. The owner can
then run `python tools/shared-content.py edit --base-revision <revision> --cost 625`.
`--inherit` instead of `--cost` restores each foundation's own value. Every edit
checks the prior revision, takes an exclusive lock and preserves both source
revisions in `content/revisions`. Only this pilot entity and cost field are writable;
arbitrary paths, bindings, YAML and executable code are not accepted.

`compile` regenerates the four overlays and manifest. `check` rejects stale outputs
and manifests that omit their overlay. Desktop and web input builders run that check.
`--check-shared-content` in the native utility verifies actual merged engine cost
and the included overlay's SHA-256 against the compiled manifest.

An edit changes local source, not already-running games, public builds or campaigns
that intentionally override that actor. Compile, commit and build the reviewed
revision; never label a saved draft as installed. Player handicap/production
multipliers may affect actual prices; the proof uses ordinary, unmodified players.

## Acceptance evidence

Shared revision: `87ddd775e4df5f942deb535a6e8d50a84bce958e193156799243978277c838ca`.

The native Classic and RA2 test maps each train one Engineer through the real
production queue and deduct 625 credits (5000 → 4375). The actual Chromium WASM
games each expose that revision and price, train one Engineer through the HUD,
and deduct 625 (10000 → 9375). The test uses disposable maps and support directories.

Evidence lives in sibling `artifacts/shared-content-pilot-20261016`: native Lua
logs, actual build-menu screenshots, `web-receipt.json`, production access checks,
source/input identities and the local report. `tools/stage-shared-content-proof.py`
creates native fixtures; `RTSAI-WebGame/tools/shared-content-browser-test.mjs`
checks real browser production. No artwork generation or new asset distribution
was performed. No public release or deployment was run by this task.

The web runtime uses the local user .NET SDK with wasm-tools. Pass both
`--runtime browser-wasm` and `-p:DefineConstants=BROWSER` as the existing release
tool does, so desktop Kestrel code is excluded from the embedded build.

## Next increment

Expand only after this boundary is accepted: replace the Classic web adapter with
the actual Classic foundation, add more reviewed editable fields, and then add
durable online admin drafts/private assets and a build queue. Keep AI generation
for a later increment. Experimental content and the third launcher entry remain
preserved; this pilot does not remove them.
