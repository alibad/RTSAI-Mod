#!/usr/bin/env python3
"""Standalone audio: reference measurement and the provenance check.

  measure --content DIR --names FILE --out FILE   coarse numbers (length, loudness, envelope, brightness) of the
                                                  sounds the rules name, decoded in memory by the engine from the
                                                  player's own RA2 content; no samples are written anywhere
  measure --files a.wav b.wav --out FILE          the same numbers for project files, with the same code
  check                                           fail if any audio file under mods/rtsai has no provenance entry,
                                                  or if an entry's SHA-256 no longer matches the file

Provenance records the check reads (no loose text matching):
  mods/rtsai/standalone/audio/PROVENANCE.json        "files": {path below audio/: record with generator, license,
                                                     sha256 of the shipped bytes}; standalone SFX, UI, voices, music
  mods/rtsai/modern-factions/audio/PROVENANCE.json   "voice_lines", "announcers", "sound_effects": [{filename, ...}];
                                                     naval-*.wav must also be reproduced by tools/naval-sfx.py
Audio anywhere else under mods/rtsai fails, and so does a record whose file is gone. `check` also fails when the
per-file tables in docs/audio-provenance.md (written by `doc`) no longer match PROVENANCE.json.

usage: python tools/standalone-audio.py check [--verbose]
       python tools/standalone-audio.py doc            # regenerate the per-file tables in docs/audio-provenance.md
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "mods" / "rtsai"
AUDIO_EXT = {".wav", ".aud", ".ogg", ".mp3", ".voc", ".flac"}


# ------------------------------------------------------------------------------------------------ measure
def measure(a):
    spec = importlib.util.spec_from_file_location("sa_audit", ROOT / "tools" / "standalone-audit.py")
    sa = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sa)
    sa.SRC = ROOT / "tools" / "standalone-audio" / "MeasureAudio.cs"
    cache = Path(a.cache)
    cache.mkdir(parents=True, exist_ok=True)
    engine = ROOT / "engine"
    dll = sa.compile_command(engine, cache)
    names = Path(a.names).resolve() if a.names else None
    if a.files:
        names = cache / "names.txt"
        names.write_text("\n".join(str(Path(f).resolve()) for f in a.files) + "\n")
    out = Path(a.out).resolve()
    content = Path(a.content).resolve() if a.content else None
    # with --content, measure through a manifest that mounts the RA2 packages (the pre-standalone one)
    mod_yaml = None
    if content:
        mod_yaml = cache / "content-mod.yaml"
        mod_yaml.write_text(subprocess.run(["git", "show", f"{a.content_manifest}:mods/rtsai/mod.yaml"], cwd=ROOT,
                                           capture_output=True, text=True, check=True).stdout, encoding="utf-8")
    sandbox = Path(tempfile.mkdtemp(prefix="sa-measure-", dir=cache))
    try:
        eng = sandbox / "engine"
        eng.mkdir()
        for n in ["bin", "mods", "glsl"]:
            sa.link_dir(eng / n, engine / n)
        for f in engine.iterdir():
            if f.is_file():
                shutil.copy2(f, eng / f.name)
        (eng / "Support").mkdir()
        if content:
            sa.link_dir(eng / "Support" / "Content", content)
        mods = sandbox / "mods"
        mods.mkdir()
        (mods / "rtsai").mkdir()
        for item in MOD.iterdir():
            if item.is_dir():
                sa.link_dir(mods / "rtsai" / item.name, item)
            elif item.name == "mod.yaml":
                t = (mod_yaml or item).read_text(encoding="utf-8").replace("\r\n", "\n")
                t = re.sub(r"^(Assemblies: .+)$", lambda m: m[1] + ", " + str(dll), t, flags=re.M)
                (mods / "rtsai" / "mod.yaml").write_text(t, encoding="utf-8")
            else:
                shutil.copy2(item, mods / "rtsai" / item.name)
        for entry in (ROOT / "mods").iterdir():
            if entry.is_dir() and entry.name != "rtsai":
                sa.link_dir(mods / entry.name, entry)
        env = {k: v for k, v in os.environ.items() if not k.startswith(("OPENRA_AI_", "RTSAI_"))}
        env.update(ENGINE_DIR=str(eng), MOD_SEARCH_PATHS=str(mods), OPENRA_AI_HOST="0", OPENRA_AI_COMPANION="0",
                   OPENRA_AI_DISABLE_AUTOSTART="1")
        r = subprocess.run(["dotnet", str(engine / "bin" / "OpenRA.Utility.dll"), "rtsai", "--audio-measure", str(names),
                            str(out)], cwd=engine / "bin", env=env, capture_output=True, text=True, timeout=1800)
        print(r.stdout.strip(), r.stderr.strip()[-2000:])
        if r.returncode:
            sys.exit(r.returncode)
    finally:
        sa.unlink_tree_links(sandbox)
        if content:
            assert content.exists(), "content target vanished"


# ------------------------------------------------------------------------------------------------ provenance check
def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def check(a) -> int:
    """Every audio file under mods/rtsai needs a structured provenance record; nothing is matched by loose text."""
    problems, covered = [], {}
    sa_prov_path = MOD / "standalone" / "audio" / "PROVENANCE.json"
    sa_prov = json.loads(sa_prov_path.read_text(encoding="utf-8"))["files"] if sa_prov_path.exists() else {}
    mf_prov_path = MOD / "modern-factions" / "audio" / "PROVENANCE.json"
    mf = json.loads(mf_prov_path.read_text(encoding="utf-8")) if mf_prov_path.exists() else {}
    mf_files = {}
    for section in ("voice_lines", "announcers", "sound_effects"):
        for rec in mf.get(section, []):
            if rec.get("filename"):
                mf_files[rec["filename"].replace("\\", "/")] = (section, rec)
    naval_tool = ROOT / "tools" / "naval-sfx.py"
    naval = naval_tool.read_text(encoding="utf-8") if naval_tool.exists() else ""

    for p in sorted(MOD.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in AUDIO_EXT:
            continue
        rel = p.relative_to(MOD).as_posix()
        if rel.startswith("standalone/audio/"):
            key = rel[len("standalone/audio/"):]
            rec = sa_prov.get(key)
            if rec is None:
                problems.append(f"{rel}: no entry in standalone/audio/PROVENANCE.json")
            elif rec.get("sha256") != sha(p):
                problems.append(f"{rel}: PROVENANCE.json sha256 does not match the file")
            elif not rec.get("license") or not rec.get("generator"):
                problems.append(f"{rel}: entry lacks generator or license")
            else:
                covered[rel] = "standalone/audio/PROVENANCE.json"
        elif rel.startswith("modern-factions/audio/"):
            sub = rel[len("modern-factions/audio/"):]
            hit = mf_files.get(sub)
            if hit is None:
                problems.append(f"{rel}: no record in modern-factions/audio/PROVENANCE.json")
                continue
            section, rec = hit
            if section == "sound_effects":
                if not rec.get("source"):
                    problems.append(f"{rel}: sound_effects record has no source")
                    continue
                # the naval sounds are additionally reproduced byte for byte by tools/naval-sfx.py
                if p.name.startswith("naval-") and f'"{p.name}"' not in naval and p.stem[len("naval-"):] not in naval:
                    problems.append(f"{rel}: naval sound not covered by tools/naval-sfx.py")
                    continue
            elif not rec.get("license") and not rec.get("engine_id") and not rec.get("engine"):
                problems.append(f"{rel}: {section} record has no engine/license")
                continue
            covered[rel] = f"modern-factions/audio/PROVENANCE.json ({section})"
        else:
            problems.append(f"{rel}: audio outside the provenance-tracked folders (standalone/audio, modern-factions/audio)")
    for k in sa_prov:
        if not (MOD / "standalone" / "audio" / k).exists():
            problems.append(f"standalone/audio/PROVENANCE.json: entry {k} has no file")
    for k in mf_files:
        if not (MOD / "modern-factions" / "audio" / k).exists():
            problems.append(f"modern-factions/audio/PROVENANCE.json: record {k} has no file")
    if a.verbose:
        for rel, src in covered.items():
            print(f"ok  {rel}  <- {src}")
    by = {}
    for s_ in covered.values():
        by[s_] = by.get(s_, 0) + 1
    print(f"{len(covered)} audio files with provenance: " + ", ".join(f"{v} via {k}" for k, v in sorted(by.items())))
    for pr in problems:
        print("FAIL " + pr)
    return 1 if problems else 0


# ------------------------------------------------------------------------------------------------ doc tables
DOC = ROOT / "docs" / "audio-provenance.md"
BEGIN = "<!-- standalone-audio-files: generated by tools/standalone-audio.py doc; do not edit by hand -->"
END = "<!-- /standalone-audio-files -->"


def md(text) -> str:
    return str(text if text is not None else "").replace("|", "\\|").replace("\n", " ")


def doc_tables() -> str:
    prov = json.loads((MOD / "standalone" / "audio" / "PROVENANCE.json").read_text(encoding="utf-8"))["files"]
    out = [BEGIN, ""]
    music = {k: r for k, r in prov.items() if k.startswith("music/")}
    voices = {k: r for k, r in prov.items() if k.startswith("voices/") and r.get("engine_id")}
    synth = {k: r for k, r in prov.items() if k not in music and k not in voices}
    out += ["#### Music", "", "Generator `tools/standalone-music.py`; ACE-Step 1.5, MIT. Request = caption below, "
            "instrumental, the bpm/key/length in the record, 8 turbo steps.", "",
            "| File | Title | Seed | Prompt (caption) | Licence |", "|---|---|---|---|---|"]
    for k, r in sorted(music.items()):
        out.append(f"| `{k}` | {md(r.get('title'))} | {r.get('seed')} | {md(r.get('prompt'))} | MIT (ACE-Step 1.5) |")
    out += ["", "#### Sound effects, UI sounds and the dog", "",
            "Generator `tools/standalone-sfx.py` (procedural; no recordings or samples). Seed: the first 8 bytes of "
            "`sha256('rtsai-standalone-sfx-1/<file>')`. Licence: the project's own code (GPL-3.0); the output carries "
            "no third-party rights.", "", "| File | Role | Seed | Licence |", "|---|---|---|---|"]
    for k, r in sorted(synth.items()):
        out.append(f"| `{k}` | {md(r.get('role'))} | {md(r.get('seed'))} | GPL-3.0 code, no third-party rights |")
    out += ["", "#### Shared-unit voices", "",
            "Generator `tools/standalone-voices.py` with OpenRA-AI `scripts/voice_engines.py`. Spoken lines: "
            "Kokoro-82M `hexgrad/Kokoro-82M@f3ff357` (Apache-2.0), deterministic, so no seed. Death cries: Chatterbox "
            "`ResembleAI/chatterbox@5bb1f6e` (MIT), cloned from the speaker's Kokoro English reference, with the seed "
            "shown. The prompt is the text.",
            "", "| File | Unit set | Speaker (voicepacks) | Text | Engine, seed | Licence |", "|---|---|---|---|---|---|"]
    for k, r in sorted(voices.items()):
        v = r.get("voice", {})
        eng = "Kokoro" if r.get("engine_id") == "kokoro" else f"Chatterbox, seed {r.get('seed')}"
        out.append(f"| `{k}` | {md(r.get('unit_set'))} | {md(v.get('speaker'))} ({md('+'.join(v.get('kokoro_voicepacks', [])))}) "
                   f"| {md(r.get('text'))} | {eng} | {md(r.get('license'))} |")
    out += ["", END]
    return "\n".join(out)


def doc(a) -> int:
    text = DOC.read_text(encoding="utf-8")
    if BEGIN not in text:
        raise SystemExit(f"{DOC} has no {BEGIN} marker")
    new = text[:text.index(BEGIN)] + doc_tables() + text[text.index(END) + len(END):]
    if a.check:
        if new != text:
            print("FAIL docs/audio-provenance.md: the standalone file tables are stale (run tools/standalone-audio.py doc)")
            return 1
        return 0
    DOC.write_text(new, encoding="utf-8", newline="\n")
    print(f"updated {DOC}")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("measure")
    m.add_argument("--content", help="installed RA2 content dir (e.g. ../OpenRA/Support/Content); never copied")
    m.add_argument("--content-manifest", default="cda3ced", help="commit whose mod.yaml mounts the RA2 packages")
    m.add_argument("--names", help="file with one sound name per line")
    m.add_argument("--files", nargs="*", help="project audio files to measure instead")
    m.add_argument("--out", required=True)
    m.add_argument("--cache", default=str(Path(tempfile.gettempdir()) / "rtsai-standalone-audit"))
    c = sub.add_parser("check")
    c.add_argument("--verbose", action="store_true")
    d = sub.add_parser("doc")
    d.add_argument("--check", action="store_true", help="only report whether the doc tables are current")
    a = ap.parse_args()
    if a.cmd == "measure":
        measure(a)
    elif a.cmd == "doc":
        sys.exit(doc(a))
    else:
        a.check = True
        sys.exit(check(a) | doc(a))


if __name__ == "__main__":
    main()
