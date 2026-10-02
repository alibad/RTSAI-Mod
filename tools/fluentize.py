#!/usr/bin/env python3
"""Turn the literal UI strings that `make test` reports as missing Fluent keys into Fluent messages.

Upstream RA2 (and the RTS AI chrome built on it) still writes many player-facing strings as
literals in YAML. The OpenRA lint reports each one ("Missing key `<literal>` in mod ftl files
required by ..."). This tool runs the lint (or reads a saved `make test` log), and for every
reported literal:
  * rules (actor tooltips, buildable descriptions, factions, support powers, resource names,
    tileset names, the mod title): the YAML value becomes a generated key, and the text is
    appended to languages/rules/en.ftl;
  * chrome widgets and hotkey descriptions: the value becomes a key in languages/chrome/en.ftl,
    or an existing engine common|fluent key with exactly the same text is reused;
  * "{0}" widget texts that the logic always overwrites are removed;
  * engine default keys the mod lacks (loadscreen-loading, support-power-timer) are defined:
    the load screen keeps the mod's own lines (the old LoadScreen Text field, which the engine
    no longer reads), the timer format is upstream RA's.
Old "{(Ctrl)}" highlight markup becomes the engine's "<(Ctrl)>" (Fluent reserves braces).

Run from the repo root after `make all`:  python tools/fluentize.py [--log make-test.log]
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "mods/rtsai"
ENGINE = ROOT / "engine"
RULES_FTL = MOD / "languages/rules/en.ftl"
CHROME_FTL = MOD / "languages/chrome/en.ftl"

WARNING = re.compile(r"^Warning: Missing key `(?P<literal>.*)` in mod ftl files required by (?P<context>.*)$")
ACTOR = re.compile(r"^Actor `(?P<actor>[^`]+)` trait (?P<trait>\w+)\.(?P<field>[\w.]+)$")
WIDGET = re.compile(r"^Widget `(?P<widget>[^`]+)` field `(?P<field>\w+)` in ra2\|(?P<file>[^:]+):(?P<line>\d+)$")
TOOLTIP_TRAITS = {"Tooltip", "EditorOnlyTooltip", "MirageTooltip", "DisguiseTooltip"}
FIELD_SLUGS = {"Name": "name", "GenericName": "generic-name", "Description": "description", "Text": "text",
               "TooltipText": "tooltip", "TooltipDesc": "tooltip-desc", "ReadyText": "ready", "HoldText": "hold"}


def slug(value: str) -> str:
    meta = value.startswith("^")
    value = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "-", value.lstrip("^"))  # ProductionTypeBuilding
    value = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return ("meta-" + value) if meta else value


def fluent_text(literal: str) -> str:
    """A MiniYaml literal (\\n escapes) as a Fluent pattern; braces are Fluent syntax."""
    literal = re.sub(r"\{(\([^{}]*\))\}", r"<\1>", literal)
    literal = literal.replace("{", "\x00").replace("}", '{"}"}').replace("\x00", '{"{"}')
    lines = [line.rstrip() for line in literal.replace("\\n", "\n").strip().split("\n")]
    lines = [('{"' + line[0] + '"}' + line[1:]) if line[:1] in "[*." and line else line for line in lines]
    if len(lines) == 1:
        return " " + lines[0]
    return "\n" + "\n".join(("    " + line) if line else "" for line in lines)


def parse_ftl(text: str) -> dict[str, str]:
    """Message (and message.attribute) id -> raw pattern text. Enough for exact-text reuse."""
    messages: dict[str, str] = {}
    current = None
    for line in text.splitlines():
        if m := re.match(r"^([a-zA-Z][\w-]*) =(.*)$", line):
            current = m.group(1)
            messages[current] = m.group(2).strip()
            base = current
        elif current and (m := re.match(r"^\s+\.([\w-]+) =(.*)$", line)):
            current = f"{base}.{m.group(1)}"
            messages[current] = m.group(2).strip()
        elif current and line.startswith(" ") and line.strip():
            messages[current] = (messages[current] + "\n" + line.strip()).strip()
        elif not line.strip() or line.startswith("#"):
            continue
    return messages


def normalise(pattern: str) -> str:
    return "\n".join(line.strip() for line in pattern.strip().splitlines())


def manifest_files(section: str) -> list[Path]:
    text = (MOD / "mod.yaml").read_text(encoding="utf-8")
    block = re.search(rf"^{section}:\n((?:\t.*\n)+)", text, re.MULTILINE).group(1)
    files = []
    for entry in re.findall(r"^\t(\S+)", block, re.MULTILINE):
        package, _, path = entry.partition("|")
        files.append({"ra2": MOD, "common": ENGINE / "mods/common"}[package] / path)
    return files


def run_lint() -> str:
    env = dict(os.environ, MOD_SEARCH_PATHS=f"{MOD.parent},./mods", ENGINE_DIR="..")
    utility = ENGINE / "bin" / ("OpenRA.Utility.exe" if os.name == "nt" else "OpenRA.Utility")
    result = subprocess.run([str(utility), "rtsai", "--check-yaml"], cwd=ENGINE, env=env,
                            capture_output=True, text=True, encoding="utf-8")
    return result.stdout + result.stderr


class Converter:
    def __init__(self, lint: str):
        self.warnings = [m.groupdict() for m in map(WARNING.match, lint.splitlines()) if m]
        existing = {}
        for path in manifest_files("FluentMessages"):
            existing.update(parse_ftl(path.read_text(encoding="utf-8")))
        self.existing = existing
        self.reusable = {}
        for path in (ENGINE / "mods/common/fluent").glob("*.ftl"):
            for key, pattern in parse_ftl(path.read_text(encoding="utf-8")).items():
                self.reusable.setdefault(normalise(pattern), key)
        self.new: dict[Path, dict[str, str]] = {RULES_FTL: {}, CHROME_FTL: {}}
        self.edits = 0

    def define(self, target: Path, key: str, literal: str, reuse: bool = False) -> str:
        text = fluent_text(literal)
        if reuse and (found := self.reusable.get(normalise(text))):
            return found
        candidate, n = key, 1
        while True:
            known = self.new[target].get(candidate) or self.new[RULES_FTL if target == CHROME_FTL else CHROME_FTL].get(candidate)
            if known is None and candidate not in self.existing:
                self.new[target][candidate] = text
                return candidate
            if known == text:
                return candidate
            n += 1
            candidate = f"{key}-{n}"

    # Rules: actor traits (the lint reports every concrete actor; values usually live on templates).
    def convert_rules(self) -> None:
        wanted = {}
        for w in self.warnings:
            if m := ACTOR.match(w["context"]):
                wanted[(m["trait"], m["field"], w["literal"])] = True
        for path in manifest_files("Rules"):
            lines = path.read_text(encoding="utf-8").split("\n")
            stack: list[str] = []
            blocks = self._blocks(lines)
            changed = False
            for i, line in enumerate(lines):
                if not line.strip() or line.lstrip().startswith("#"):
                    continue
                depth = len(line) - len(line.lstrip("\t"))
                key, _, value = line.strip().partition(":")
                stack = stack[:depth] + [key]
                value = value.strip()
                if depth < 2 or not value:
                    continue
                trait = stack[1].lstrip("-").split("@")[0]
                field = ".".join([stack[2], key]) if trait == "ResourceRenderer" and depth == 4 else ".".join(stack[2:depth] + [key])
                if (trait, field, value) not in wanted:
                    continue
                actor, suffix = stack[0], stack[1].partition("@")[2]
                if trait == "Faction":
                    name = f"faction-{slug(blocks.get((actor, stack[1]), {}).get('InternalName', suffix))}-{FIELD_SLUGS[key]}"
                elif trait == "ResourceRenderer":
                    name = f"resource-{slug(stack[3])}-name"
                elif trait in TOOLTIP_TRAITS or trait == "Buildable":
                    name = f"actor-{slug(actor)}-{FIELD_SLUGS[key]}"
                else:
                    name = f"actor-{slug(actor)}-{slug(suffix or trait)}-{FIELD_SLUGS.get(key, slug(key))}"
                lines[i] = line[:len(line) - len(line.lstrip())] + f"{key}: {self.define(RULES_FTL, name, value)}"
                changed = True
                self.edits += 1
            if changed:
                path.write_text("\n".join(lines), encoding="utf-8", newline="\n")

    @staticmethod
    def _blocks(lines: list[str]) -> dict[tuple[str, str], dict[str, str]]:
        blocks: dict[tuple[str, str], dict[str, str]] = {}
        actor = trait = None
        for line in lines:
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            depth = len(line) - len(line.lstrip("\t"))
            key, _, value = line.strip().partition(":")
            if depth == 0:
                actor = key
            elif depth == 1:
                trait = key
            elif depth == 2:
                blocks.setdefault((actor, trait), {})[key] = value.strip()
        return blocks

    def convert_widgets(self) -> None:
        by_file: dict[str, list[dict]] = {}
        for w in self.warnings:
            if m := WIDGET.match(w["context"]):
                by_file.setdefault(m["file"], []).append({**m.groupdict(), "literal": w["literal"]})
        for name, items in by_file.items():
            path = MOD / name
            lines = path.read_text(encoding="utf-8").split("\n")
            drop = set()
            for item in items:
                # The lint reports the widget's line; the field is one of its properties below it.
                start = int(item["line"]) - 1
                indent = len(lines[start]) - len(lines[start].lstrip("\t"))
                found = None
                for i in range(start + 1, len(lines)):
                    depth = len(lines[i]) - len(lines[i].lstrip("\t"))
                    if lines[i].strip() and depth <= indent:
                        break
                    if depth == indent + 1 and lines[i].strip() == f"{item['field']}: {item['literal']}":
                        found = i
                        break
                if found is None:
                    raise ValueError(f"{name}:{item['line']}: {item['field']} not found")
                i = found
                if re.fullmatch(r"\{\d+\}", item["literal"]):
                    drop.add(i)  # placeholder text; the widget logic always sets GetText
                    continue
                widget = slug(item["widget"].partition("@")[2] or item["widget"])
                key = self.define(CHROME_FTL, f"{slug(Path(name).stem)}-{widget}-{FIELD_SLUGS[item['field']]}", item["literal"], reuse=True)
                lines[i] = "\t" * (indent + 1) + f"{item['field']}: {key}"
                self.edits += 1
            lines = [line for i, line in enumerate(lines) if i not in drop]
            self.edits += len(drop)
            path.write_text("\n".join(lines), encoding="utf-8", newline="\n")

    def convert_hotkeys(self) -> None:
        wanted = {w["literal"] for w in self.warnings if w["context"] == "Hotkey HotkeyDefinition.Description"}
        for path in (p for p in manifest_files("Hotkeys") if MOD in p.parents):
            lines = path.read_text(encoding="utf-8").split("\n")
            hotkey = None
            for i, line in enumerate(lines):
                if line and not line[0].isspace():
                    hotkey = line.split(":")[0]
                elif (m := re.match(r"^\tDescription: (.*)$", line)) and m.group(1).strip() in wanted:
                    key = self.define(CHROME_FTL, f"hotkey-description-{slug(hotkey)}", m.group(1).strip(), reuse=True)
                    lines[i] = f"\tDescription: {key}"
                    self.edits += 1
            path.write_text("\n".join(lines), encoding="utf-8", newline="\n")

    def convert_tilesets_and_title(self) -> None:
        contexts = {w["context"]: w["literal"] for w in self.warnings}
        for path in manifest_files("TileSets"):
            text = path.read_text(encoding="utf-8")
            general = re.search(r"^General:\n((?:\t.*\n)+)", text, re.MULTILINE)
            name = re.search(r"^\tName: (.*)$", general.group(1), re.MULTILINE)
            tileset = re.search(r"^\tId: (\w+)$", general.group(1), re.MULTILINE).group(1)
            if contexts.get(f"Tileset {tileset}.Name") == name.group(1):
                key = self.define(RULES_FTL, f"tileset-{slug(tileset)}", name.group(1))
                start = general.start(1) + name.start(1)
                path.write_text(text[:start] + key + text[start + len(name.group(1)):], encoding="utf-8", newline="\n")
                self.edits += 1
        manifest = MOD / "mod.yaml"
        text = manifest.read_text(encoding="utf-8")
        if (title := contexts.get("mod.yaml.Title")) is not None:
            text = text.replace(f"\tTitle: {title}\n", f"\tTitle: {self.define(RULES_FTL, 'mod-title', title)}\n", 1)
            self.edits += 1
        if "LogoStripeLoadScreen.Loading" in contexts:
            m = re.search(r"^LoadScreen: LogoStripeLoadScreen\n(?:\t.*\n)*?(\tText: (.*)\n)", text, re.MULTILINE)
            self.new[CHROME_FTL][contexts["LogoStripeLoadScreen.Loading"]] = " " + m.group(2)
            text = text[:m.start(1)] + text[m.end(1):]
            self.edits += 1
        if "SupportPowerTimerWidget.Format" in contexts:
            upstream = parse_ftl((ENGINE / "mods/ra/fluent/ra.ftl").read_text(encoding="utf-8"))
            key = contexts["SupportPowerTimerWidget.Format"]
            self.new[CHROME_FTL][key] = " " + upstream[key]
            self.edits += 1
        manifest.write_text(text, encoding="utf-8", newline="\n")

    def write(self) -> None:
        for target, messages in self.new.items():
            if not messages:
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            header = "" if target.exists() else "## Generated by tools/fluentize.py from literal chrome strings.\n"
            body = "".join(f"{key} ={text}\n" for key, text in messages.items())
            current = target.read_text(encoding="utf-8") if target.exists() else header
            if target.exists():
                body = "\n## Generated by tools/fluentize.py from literal rules strings.\n" + body
            target.write_text(current.rstrip("\n") + "\n" + body if current.strip() else header + body, encoding="utf-8", newline="\n")
        manifest = MOD / "mod.yaml"
        text = manifest.read_text(encoding="utf-8")
        entry = "\tra2|languages/chrome/en.ftl\n"
        if self.new[CHROME_FTL] and entry not in text:
            text = text.replace("\tra2|languages/rules/en.ftl\n", "\tra2|languages/rules/en.ftl\n" + entry, 1)
            manifest.write_text(text, encoding="utf-8", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", type=Path, help="saved `make test` output instead of running the lint")
    args = parser.parse_args()
    lint = args.log.read_text(encoding="utf-8", errors="replace") if args.log else run_lint()
    converter = Converter(lint)
    print(f"{len(converter.warnings)} missing-key warnings")
    converter.convert_rules()
    converter.convert_widgets()
    converter.convert_hotkeys()
    converter.convert_tilesets_and_title()
    converter.write()
    print(f"{converter.edits} YAML edits; {len(converter.new[RULES_FTL])} rules and {len(converter.new[CHROME_FTL])} chrome messages added")


if __name__ == "__main__":
    main()
