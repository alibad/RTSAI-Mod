# Native companion integration

The two product profiles are `rtsai` (Isometric) and `rtsai-topdown` (Classic). Both use standalone project assets. The legacy `rtsai-classic` owned-RA2 add-on is excluded from the macOS standalone package.

The packaged companion is optional and runs locally. The game remains playable when it is off, unavailable, unsupported or offline. The ARM companion artifact contains deterministic alerts and grounded proposals, but no compatible chat, microphone or speech runtime or model weights. Model and voice capabilities report unsupported; startup must not download them. Hosted access is disabled unless deliberately configured, and hosted proxy authentication/deployment remains separate work. Provider credentials do not belong in the game client.

## Confirmed orders

Native clients read `/v1/state` and capture `pending_action.proposal_id` and its summary. The review dialog shows that captured summary. Apply sends `POST /v1/proposals/confirm` with `{"contract_version":1,"proposal_id":"the reviewed id"}`. Cancel uses `/v1/proposals/cancel` with the same explicit ID. A proposal replaced while the dialog is open cannot be silently substituted. The companion rejects stale or duplicate confirmations. Advice and proposal creation are read-only. Deliberate legacy spoken confirmation is retained by the frozen companion; native apply buttons and hotkeys use the versioned explicit-ID endpoints.

Only loopback HTTP is accepted. Direct native requests can omit Origin. Browser/proxy clients must validate loopback Host and trusted same-origin Origin before forwarding mutations; stripping Origin without that guard is unsafe. Requests to public hosted providers are excluded from local acceptance.

## Portable local launch

Build the frozen Python 3.12 source offline using `packaging/macos/build-companion.sh <frozen-source> <wheelhouse> <python3.12> <private-work> <frozen-engine-vocabulary>`. This requires the verified S04 wheelhouse plus pinned PyInstaller 6.22.3 and setuptools 84.0.0. The output is `<private-work>/dist/rtsai-companion`.

A caller running the standalone sidecar must provide the exact fixed engine vocabulary, including `mods/ra/fluent/rules.ftl`, and a private config/cache/output directory:

```sh
OPENRA_AI_MODEL_ROOT=/private/rtsai-companion \
OPENRA_AI_ENGINE_DIR=/private/frozen-engine-vocabulary \
OPENRA_AI_AUTO_INSTALL_VOICE=0 OPENRA_AI_HOSTED_ENABLED=0 \
OPENRA_AI_DATA_DIR=/private/support/companion \
OPENRA_AI_LOG_DIR=/private/support/logs \
OPENRA_AI_SUPPORT_DIR=/private/support \
OPENRA_AI_CATALOG=/private/rtsai-companion/catalog/factions.json \
OPENRA_AI_PACK_LOCK=/private/rtsai-companion/packaging/ai-pack.lock.json \
OPENRA_AI_BUNDLED_RUNTIME=/private/rtsai-companion/ai/runtime \
OPENRA_AI_RUNTIME_EXECUTABLE=/private/rtsai-companion/rtsai-companion \
OPENRA_AI_DISABLE_AUTOSTART=1 \
OPENRA_AI_ROUTER_URL=http://127.0.0.1:54058/ \
OPENRA_AI_LOCAL_ROUTER_URL=http://127.0.0.1:54058/ \
OPENRA_AI_AGENT_ROUTER_URL=http://127.0.0.1:54058/ \
OPENRA_AI_LOCAL_CHAT_PORT=54059 OPENRA_AI_LOCAL_TRANSCRIBE_PORT=54060 \
/private/rtsai-companion/rtsai-companion watch \
  --bridge 127.0.0.1:54055 --control-port 54056 --worldgen-port 54057 \
  --mission-output /private/support/GeneratedMissions
```

Use free owned ports. Native CompanionHost chooses ports and exports them to its child. Its bundled vocabulary takes precedence over the game resource directory because the standalone app does not ship the historical `ra` mod. For a source development launch, explicitly set `OPENRA_AI_PYTHON` to a compatible Python 3.12 interpreter. The native bridge proto and fixed engine APIs remain unchanged.

The macOS game contains ARM and x64 slices and requires macOS 15 or newer because of .NET 10. An ARM-only companion is rejected before launch on an Intel host; Intel gameplay remains available. Rosetta testing on ARM verifies the x64 game slice, not Intel-host companion availability.

## Unit voice preference

`RTSAI.VoiceLanguage` accepts `faction` or `en`; absent and invalid values fall back to faction. The mode dialog exposes this preference in both profiles. It selects only pools from the actor's existing voice family, before the cosmetic sound choice. Unbound deaths, shared clips, animals and announcers retain inherited behavior. The preference has no synchronized trait field, gameplay tick or order and does not change compatibility identity. Human fluent-language and device/audio acceptance remain separate gates.

## Native campaigns

The six tracked campaigns use the production `RTSAICampaign` ITick objective controller and `campaigns/missions.json`; native MissionObjectives publishes success/failure. Campaign map Rules include the controller, mission panel, briefing and difficulty option. Assisted fixtures in `tools/campaign-acceptance.py` add an observer Lua script only in private copied maps. They drive game conditions and actual convoy movement, never call MarkCompleted/MarkFailed, and do not certify human combat balance or entertainment.

`tools/import-shared-campaigns.py` requires explicit frozen input and output paths. Its Classic candidate mode preserves native objective rules and briefings, verifies the input manifest and objective catalog, and consumes square map geometry without browser-only weapon includes. Set `RTSAI_CAMPAIGN_ENGINE` to a private fixed-engine build when running acceptance.
