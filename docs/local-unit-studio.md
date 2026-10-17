# Local unit editing in Faction Studio

Browse factions and units in the existing `/art/review` viewer. **Edit unit** opens a separate tab (`view=edit`), preserving the selected model, animation and art/audio review in the viewer.

The editor reads resolved Classic or RA2 rules through OpenRA, including the existing custom traits and experience modules. It does not replace the unit catalog or rewrite the original rules.

## Editing

- Overview: build cost, health and movement speed.
- Combat: individual armaments, weapon range/reload, warheads, damage, targeting, versus values and projectile/effect references. Primary, deployed, elite and garrisoned weapons remain distinct when configured.
- Production, movement/defense, abilities and art/audio: configured properties of the unit's existing traits.
- Advanced rules: add or remove traits and properties using a minimal MiniYaml overlay. Use tabs or groups of four spaces. Cost, health and movement speed use Overview so they have one authoritative override.
- Review changes: inspect the overlay, stage an earlier unit revision or restore original inherited rules. Staging does not save anything until **Save unit changes** is pressed.

Distances use OpenRA notation (`6c0` = six cells); reload values are engine ticks. Art and sound fields reference existing resources. Asset creation/review remains in the existing viewer workflows. This work adds no AI generation.

## Save, build, play

1. Save the unit. OpenRA validates the complete affected rules, and an invalid save rolls back both sources and generated outputs. Browser drafts survive reloads; a stale revision cannot overwrite another tab's edits.
2. Build & verify locally. A new immutable candidate freezes the saved revision, desktop binaries/rules, browser runtime, data packs and interface.
3. Acceptance checks all bound unit stats and edited rule leaves, actual typed combat/production properties, native unit production in both modes, and browser stock/custom Classic and RA2 production.
4. Only a passing candidate becomes the selected build. Saved, Built and Verified revisions must match before launching. The four launch controls use that selected content. Existing matches retain their original rules.

## Storage and preservation

- `content/unit-modifications.json`: original core-stat override source.
- `content/unit-details.json`: actor overlays and unit-specific weapon overlays.
- `content/unit-revisions/`: preserved, unit-restorable snapshots of both sources.
- `mods/rtsai/unit-overrides/`: generated target overlays, bindings and content manifest.
- `.recovery/content-current.json`: checksum-protected pointer to the last passing local build.
- `.recovery/studio-settings.json`: optional `buildRoot` for preview output storage; this machine uses `D:/RTSAI-StudioPreviews`.

Weapons are cloned privately for the edited unit/armament, with collision-resistant names. Other units retain the shared weapon. Actor inheritance still applies to child variants; their own overrides take precedence. No authored art, audio, maps, models or base rule files are replaced.

Owner editing is limited to the loopback local Studio gateway, with its per-launch owner capability and exact-origin checks. Public users do not gain write access. Local builds are never published by this workflow.

This edits existing catalog units and their rules. Adding entirely new units and resources still requires the existing authoring/build workflow. Passing acceptance is not a claim of balance validation, full campaign parity or every possible trait interaction.
