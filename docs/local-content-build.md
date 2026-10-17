# One local content build

Faction Studio is the owner editor; `content/unit-modifications.json` and the reviewed
bindings remain the source for unit edits. Each mode keeps its own rules, settings
and custom content. Cost, health and applicable movement speed are shared between
that mode's desktop and web builds.

Run `npm run preview:art` in sibling RTSAI-Web and use `/art/review`. Save changes,
then choose **Build & test locally**. This invokes `tools/build-unit-preview.py`:

1. Fetch canonical main, freeze committed code and copy the saved mod content.
2. Build/reuse a matching runtime, pack both modes and validate every bound native stat.
3. Train an Engineer through real native production in Classic and RA2.
4. Check all 392 browser unit bindings and representative stock/custom production.
5. Only after success, atomically select `.recovery/content-current.json` and the
   Studio receipt. A failed build keeps the last tested candidate and all saved edits.

The selected receipt records saved revision, code commits, native checks, browser
acceptance, hashes, build time and verification time. It is local, not a release.
Studio shows **Saved / Built / Verified** separately. Its new web sessions use `/play/`,
which resolves to the selected build's immutable `/local-builds/<id>/` address.
The normal `launch-game.cmd` and Studio's Desktop button use the selected native
folder. `RTSAI-WebGame/tools/local-game.mjs start` also selects that content build;
the old accepted-release registration remains preserved (`--accepted` is a diagnostic
override, not the normal owner flow).

New edits make the current build outdated. New local launches require a matching
saved revision. Existing matches retain their initial rules and immutable asset URLs.
Older preview servers/folders are preserved; use the current Studio entry rather than
an old bookmarked build URL when testing new edits. The launchers never kill a port owner.

Native menus show the loaded content revision and verified/local status. The local
web menu shows built revision, saved revision match and desktop/web verification.
These labels do not claim full campaign, multiplayer, art or feature parity.

All editing stays behind the existing loopback owner boundary. No public editing,
cloud drafts, publishing, installer update, release pin or deployment is changed.
