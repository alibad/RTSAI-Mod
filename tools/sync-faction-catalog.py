#!/usr/bin/env python3
"""The faction catalog has one home, catalog/factions.json in this repository; every other copy is made from it.

Writes the copies this repository owns (the desktop engine and AI companion's copy in the sibling OpenRA-AI checkout,
and the loading-screen tips), then checks every copy, including the website's and the web game's, which change only
through their own release steps. See catalog/README.md.

  python tools/sync-faction-catalog.py          # write owned copies, then check all
  python tools/sync-faction-catalog.py --check  # change nothing; exit 1 if any copy differs from the master
"""
import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

MOD = Path(__file__).resolve().parents[1]
GAMES = MOD.parent
MASTER = MOD / "catalog" / "factions.json"
DESKTOP_COPY = GAMES / "OpenRA-AI" / "catalog" / "factions.json"
TIPS_TOOL = MOD / "tools" / "faction-loading-tips.py"
TIPS = MOD / "mods" / "rtsai" / "modern-factions" / "loading-tips.ftl"
WEBSITE = GAMES / "RTSAI-Web" / "data"
WEB_GAME_COPY = GAMES / "RTSAI-WebGame" / "web" / "src" / "data" / "factions.json"


def lf(path: Path) -> bytes:
    # Checkouts with autocrlf store CRLF on disk; every consumer hashes LF text.
    return path.read_bytes().replace(b"\r\n", b"\n")


def tips_tool():
    spec = importlib.util.spec_from_file_location("faction_loading_tips", TIPS_TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def tip_lines(text: str) -> list[str]:
    # The tips themselves, after the message line; the header above it also records the catalog hash it was made from.
    lines = text.replace("\r\n", "\n").split("\n")
    return lines[next(i for i, line in enumerate(lines) if line.startswith("loadscreen-faction-tips")):]


def without_flavour(catalog: dict) -> dict:
    # The website never carries faction.flavour (loading lines and voice notes are for the game).
    trimmed = json.loads(json.dumps(catalog))
    for faction in trimmed["factions"]:
        faction.pop("flavour", None)
    return trimmed


def checks(master: bytes) -> list[tuple[str, str, bool | None]]:
    """(copy, detail, ok); ok is None when the sibling checkout is absent."""
    sha = hashlib.sha256(master).hexdigest()
    catalog = json.loads(master)
    rows = []
    if DESKTOP_COPY.exists():
        rows.append(("OpenRA-AI/catalog/factions.json", "desktop engine and AI companion", lf(DESKTOP_COPY) == master))
    else:
        rows.append(("OpenRA-AI/catalog/factions.json", "no OpenRA-AI checkout", None))
    rendered = tips_tool().render(master)
    shipped = TIPS.read_text(encoding="utf-8")
    exact = shipped.replace("\r\n", "\n") == rendered
    rows.append(("mods/rtsai/modern-factions/loading-tips.ftl",
                 "loading screen, desktop and web" + ("" if exact else "; same tips, header records an older catalog hash"),
                 tip_lines(shipped) == tip_lines(rendered)))
    if (WEBSITE / "factions.generated.json").exists():
        site = json.loads((WEBSITE / "factions.generated.json").read_text(encoding="utf-8"))
        inputs = json.loads((WEBSITE / "content-inputs.generated.json").read_text(encoding="utf-8"))
        base = json.loads((WEBSITE / "catalog-base.generated.json").read_text(encoding="utf-8"))
        rows.append(("RTSAI-Web data/catalog-base.generated.json", "rtsai.net and the Faction Studio",
                     base == without_flavour(catalog) and inputs.get("sourceCatalogSha256") == sha))
        rows.append(("RTSAI-Web data/factions.generated.json", "rtsai.net; source of the web game's copy", site.get("sha256") == sha))
    else:
        rows.append(("RTSAI-Web data/", "no RTSAI-Web checkout", None))
    if WEB_GAME_COPY.exists():
        rows.append(("RTSAI-WebGame web/src/data/factions.json", "web game page (made at each release)",
                     json.loads(WEB_GAME_COPY.read_text(encoding="utf-8")).get("sha256") == sha))
    else:
        rows.append(("RTSAI-WebGame web/src/data/factions.json", "not generated in this checkout (a release makes it)", None))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="change nothing; exit 1 if any copy differs")
    args = parser.parse_args()
    master = lf(MASTER)
    catalog = json.loads(master)
    if not args.check:
        if DESKTOP_COPY.parent.exists() and (not DESKTOP_COPY.exists() or lf(DESKTOP_COPY) != master):
            DESKTOP_COPY.write_bytes(master)
            print(f"wrote {DESKTOP_COPY}")
        # Rewritten only when the tips themselves change: the file ships in both games, and a header-only refresh would
        # change shipped bytes for nothing (it waits for the next approved data release).
        rendered = tips_tool().render(master)
        if tip_lines(TIPS.read_text(encoding="utf-8")) != tip_lines(rendered):
            TIPS.write_text(rendered, encoding="utf-8", newline="\n")
            print(f"wrote {TIPS}")
    print(f"catalog/factions.json  revision {catalog['revision']}  sha256 {hashlib.sha256(master).hexdigest()[:12]}")
    behind = 0
    for copy, detail, ok in checks(master):
        mark = "same" if ok else ("skipped" if ok is None else "BEHIND")
        behind += ok is False
        print(f"  {mark:8} {copy}  ({detail})")
    if behind:
        print(f"{behind} copy(ies) differ from the master. Owned copies: run this tool without --check. Website and web "
              "game: their own release steps (catalog/README.md).")
    return 1 if behind else 0


if __name__ == "__main__":
    sys.exit(main())
