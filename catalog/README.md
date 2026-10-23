# The faction catalog

`factions.json` is the one master copy of the faction catalog: every faction's name, title, tagline, accent and
strengths, each unit's story and counterplay, rival views and the loading-screen flavour. Edit it here and nowhere else.
Unit numbers (cost, health, speed) are not in it: they are the mod's rules (`content/unit-modifications.json` and
`mods/rtsai`).

Everything else is a copy made from it:

| Copy | Read by | Made by |
| --- | --- | --- |
| `OpenRA-AI/catalog/factions.json` | the desktop engine (`SharedFactionCatalog`) and the AI companion | `tools/sync-faction-catalog.py` |
| `mods/rtsai/modern-factions/loading-tips.ftl` | the loading screen, desktop and web | `tools/sync-faction-catalog.py` (via `tools/faction-loading-tips.py`) |
| RTSAI-Web `data/catalog-base.generated.json`, `data/factions.generated.json` | rtsai.net and the Faction Studio | the website's own reviewed refresh (`scripts/standalone-facts.ts --catalog=<this file>`, then `npm run sync:content`) |
| RTSAI-WebGame `web/src/data/factions.json` | the web game's page (names, taglines, unit stories) | `tools/sync-catalog.mjs` from the website copy, at every release |

After editing:

```sh
python tools/sync-faction-catalog.py          # writes the copies this repository owns, then checks every copy
python tools/sync-faction-catalog.py --check  # changes nothing; exits 1 if any copy differs from this master
```

The website and web game copies change only through their own release steps, so a catalog edit reaches rtsai.net and
rtsai.net/play only when you approve those releases. Until then `--check` lists them as behind.

The generated copies still name `OpenRA-AI/catalog/factions.json` as their source: that text is inside files the web
game ships, and changing it would change those files. It moves with the next approved release.
