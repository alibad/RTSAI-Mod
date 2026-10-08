#!/usr/bin/env python3
"""First-pass review of the non-English faction voice lines, and regeneration of the ones that fail it.

The voice lines are made by OpenRA-AI (scripts/generate-rtsai-mod-audio.py and voice_engines.py); this tool reuses
that code, so it runs in the same Python environment (see voice_engines.py) with --openra-ai pointing at a checkout.

    transcribe   Transcribe every non-English line in PROVENANCE.json with the pinned Whisper large-v3, three ways:
                 forced to the line's language (the generator's QA settings), with automatic language detection,
                 and translated to English (a hint only; often wrong on clips this short). Writes
                 docs/voice-review.csv. The human columns (literal_meaning, verdict, action, notes, native_speaker)
                 of an existing sheet are kept, so re-running refreshes only the machine columns.
    regenerate   Re-render the named lines with their own generator, speaker, reference clip and processing chain,
                 but with a longer seed range (the documented range already produced the shipped take). Records
                 are merged into PROVENANCE.json. Run it on a scratch copy of the mod, then copy the results in.

    python tools/voice-review.py transcribe --openra-ai ../OpenRA-AI --mod .
    python tools/voice-review.py regenerate --openra-ai ../OpenRA-AI --mod <copy> --seeds 24 iran-naval-attack-fa.wav
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

AUDIO = Path("mods/rtsai/modern-factions/audio")
SHEET = Path("docs/voice-review.csv")
FACTIONS = {"iran": "Iran", "shadow": "Iran", "rcn": "China", "tr": "Türkiye", "rsa": "Saudi Arabia", "rye": "Yemen",
            "il": "Israel", "hz": "Hezbollah"}
MACHINE = ["file", "faction", "language", "engine", "role", "intended_text", "english_line", "asr_transcript", "cer",
           "detected_language", "whisper_translation", "low_confidence_words"]
HUMAN = ["literal_meaning", "verdict", "action", "notes", "native_speaker"]


def load_openra_ai(path: Path):
    scripts = path.resolve() / "scripts"
    sys.path.insert(0, str(scripts))
    import voice_engines  # noqa: E402  (OpenRA-AI)
    return voice_engines


def english_counterpart(record: dict, by_name: dict) -> str:
    stem = record["filename"].rsplit("-", 1)[0]
    english = by_name.get(f"{stem}-en.wav")
    return english["text"] if english else record.get("translation", "")


def transcribe(args) -> int:
    ve = load_openra_ai(args.openra_ai)
    from faster_whisper import WhisperModel
    from huggingface_hub import snapshot_download

    mod = args.mod.resolve()
    provenance = json.loads((mod / AUDIO / "PROVENANCE.json").read_text(encoding="utf-8"))
    by_name = {r["filename"]: r for r in provenance["voice_lines"]}
    lines = [r for r in provenance["voice_lines"] if not r["language"].startswith("en")]
    local = snapshot_download("Systran/faster-whisper-large-v3", revision="edaa852ec7e145841d8ffdb056a99866b5f0a478")
    device = args.device
    model = WhisperModel(local, device=device, compute_type="int8_float16" if device == "cuda" else "int8")

    sheet = mod / SHEET
    kept = {}
    if sheet.exists():
        with sheet.open(encoding="utf-8-sig", newline="") as stream:
            kept = {row["file"]: row for row in csv.DictReader(stream)}

    rows = []
    for record in lines:
        path = str(mod / AUDIO / record["filename"])
        lang = ve.base_language(record["language"])
        segments, _ = model.transcribe(path, language=lang, beam_size=5, word_timestamps=True,
                                       condition_on_previous_text=False, vad_filter=False)
        segments = list(segments)
        text = "".join(s.text for s in segments).strip()
        words = [w for s in segments for w in (s.words or [])]
        _, info = model.transcribe(path, beam_size=5, condition_on_previous_text=False, vad_filter=False)
        top = sorted(info.all_language_probs or [], key=lambda p: -p[1])[:3]
        translated, _ = model.transcribe(path, task="translate", language=lang, beam_size=5,
                                         condition_on_previous_text=False, vad_filter=False)
        cer = ve.character_error_rate(ve.normalize_for_cer(record["text"], lang), ve.normalize_for_cer(text, lang))
        row = {
            "file": record["filename"],
            "faction": FACTIONS[record["filename"].split("-")[0]],
            "language": record["language"],
            "engine": record["engine_id"],
            "role": record.get("role", ""),
            "intended_text": record["text"],
            "english_line": english_counterpart(record, by_name),
            "asr_transcript": text,
            "cer": f"{cer:.3f}",
            "detected_language": " ".join(f"{code}:{p:.2f}" for code, p in top),
            "whisper_translation": "".join(s.text for s in translated).strip(),
            "low_confidence_words": " ".join(f"{w.word.strip()}({w.probability:.2f})" for w in words
                                             if w.probability < 0.5),
        }
        row.update({key: kept.get(record["filename"], {}).get(key, "") for key in HUMAN})
        rows.append(row)
        print(f"{record['filename']}: {text} (CER {cer:.3f}; {row['detected_language']})", flush=True)

    # rows this command does not own (the standalone shared-unit voices, tools/standalone-voices.py) are kept as they are
    rows += [row for name, row in kept.items() if name.startswith("standalone/")]
    sheet.parent.mkdir(parents=True, exist_ok=True)
    with sheet.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=MACHINE + HUMAN)
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(rows)} lines -> {sheet}", flush=True)
    # Exit here, while `model` is still referenced. On Windows with CUDA, releasing a CTranslate2 Whisper model that
    # has run a task="translate" pass kills the process with 0xC0000409, whether the release comes from `del`,
    # unload_model() or interpreter shutdown (bisected on 6 October 2026; transcription and language ID alone exit
    # cleanly). os._exit ends the process without releasing it. The sheet is written and both streams are flushed.
    sys.stderr.flush()
    os._exit(0)


def regenerate(args) -> int:
    ve = load_openra_ai(args.openra_ai)
    import importlib.util

    spec = importlib.util.spec_from_file_location("generate_rtsai_mod_audio",
                                                  args.openra_ai.resolve() / "scripts" / "generate-rtsai-mod-audio.py")
    driver = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = driver
    spec.loader.exec_module(driver)

    mod = args.mod.resolve()
    audio = mod / AUDIO
    provenance_path = audio / "PROVENANCE.json"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    records = {r["filename"]: r for r in provenance["voice_lines"]}
    owners = driver.voice_lines()
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise SystemExit("ffmpeg is required")
    synth = ve.Synthesizer(seeds=args.seeds, moss_seeds=args.seeds)
    try:
        with tempfile.TemporaryDirectory(prefix="rtsai-voice-review-") as temporary:
            for filename in args.files:
                if filename not in records:
                    raise SystemExit(f"{filename} is not a shipped voice line")
                generator, module, line = owners[filename]
                print(f"[voice] {filename}", flush=True)
                record = driver.render_voice(generator, module, line, synth, ffmpeg, audio, Path(temporary))
                record["review"] = {"regenerated": "first-pass voice review (docs/voice-review.csv)",
                                    "seed_range": f"1-{args.seeds}", "replaced_seed": records[filename].get("seed"),
                                    "replaced_asr_transcript": (records[filename].get("qa") or {}).get("asr_transcript")}
                records[filename] = record
                print(f"  seed {record['seed']}, {record['takes']} takes, ASR {record['qa']}", flush=True)
    finally:
        synth.close()
    provenance["voice_lines"] = [records[key] for key in sorted(records)]
    provenance_path.write_text(json.dumps(provenance, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("transcribe", "regenerate"):
        command = sub.add_parser(name)
        command.add_argument("--openra-ai", type=Path, required=True)
        command.add_argument("--mod", type=Path, default=Path(__file__).resolve().parents[1])
    sub.choices["transcribe"].add_argument("--device", default="cuda")
    sub.choices["regenerate"].add_argument("--seeds", type=int, default=24)
    sub.choices["regenerate"].add_argument("files", nargs="+")
    args = parser.parse_args()
    return transcribe(args) if args.command == "transcribe" else regenerate(args)  # transcribe exits via os._exit


if __name__ == "__main__":
    raise SystemExit(main())
