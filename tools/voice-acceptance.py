#!/usr/bin/env python3
"""Non-destructive audio integrity / fresh forced-language ASR review.

Run in the existing voice environment. Writes evidence only, never replaces
shipped audio or treats ASR agreement as native pronunciation approval.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
AUDIO = ROOT / "mods/rtsai/modern-factions/audio"
REVISION = "edaa852ec7e145841d8ffdb056a99866b5f0a478"


def main():
    import numpy as np
    import soundfile as sf
    from faster_whisper import WhisperModel
    from huggingface_hub import snapshot_download
    sys.path.insert(0, str(ROOT.parent / "OpenRA-AI/scripts"))
    import voice_engines as ve
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--device", choices=["cpu", "cuda"], default="cuda")
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    provenance = json.loads((AUDIO / "PROVENANCE.json").read_text(encoding="utf-8"))
    with (ROOT / "docs/voice-review.csv").open(encoding="utf-8-sig", newline="") as f:
        prior = {r["file"]: r for r in csv.DictReader(f)}
    local = snapshot_download("Systran/faster-whisper-large-v3", revision=REVISION, local_files_only=True)
    model = WhisperModel(local, device=args.device, compute_type="int8_float16" if args.device == "cuda" else "int8", cpu_threads=4)
    records = [r for r in provenance["voice_lines"] if not r["language"].startswith("en")]
    rows = []
    for index, record in enumerate(records):
        path = AUDIO / record["filename"]
        row = dict(prior.get(path.name, {}))
        row.update(file=path.name, language=record["language"], intended_text=record["text"],
                   audio_uri=path.resolve().as_uri(), sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        data, rate = sf.read(path, dtype="float32", always_2d=True)
        row.update(sample_rate=rate, channels=data.shape[1], seconds=round(len(data) / rate, 3),
                   peak=round(float(np.max(np.abs(data))), 6), rms=round(float(np.sqrt(np.mean(data * data))), 6),
                   clipped_samples=int(np.sum(np.abs(data) >= 0.999)), finite=bool(np.isfinite(data).all()))
        lang = ve.base_language(record["language"])
        segments, info = model.transcribe(str(path), language=lang, beam_size=5, word_timestamps=True,
                                          condition_on_previous_text=False, vad_filter=False)
        segments = list(segments)
        text = "".join(s.text for s in segments).strip()
        row["fresh_asr"] = text
        row["fresh_cer"] = round(ve.character_error_rate(ve.normalize_for_cer(record["text"], lang), ve.normalize_for_cer(text, lang)), 4)
        row["fresh_low_confidence"] = [w.word.strip() for s in segments for w in (s.words or []) if w.probability < .65]
        row["technical_pass"] = row["finite"] and row["seconds"] > .2 and row["rms"] > .001 and row["clipped_samples"] == 0
        row["native_approved"] = bool(row.get("native_speaker", "").strip()) and row.get("verdict") == "ok"
        row["priority"] = "high" if not row["technical_pass"] or row["fresh_cer"] > .2 else "review" if row.get("verdict") != "ok" or row["fresh_low_confidence"] else "routine"
        rows.append(row)
        (args.output / "voices.json").write_text(json.dumps({"model": "Systran/faster-whisper-large-v3", "revision": REVISION,
                   "device": args.device, "scope": "126 non-English faction voice lines; fresh forced-language ASR is a screening aid", "rows": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[{index + 1}/{len(records)}] {path.name} CER={row['fresh_cer']:.3f} priority={row['priority']}", flush=True)
    summary = {"total": len(rows), "technical_pass": sum(r["technical_pass"] for r in rows),
               "native_approved": sum(r["native_approved"] for r in rows), "priority_high": sum(r["priority"] == "high" for r in rows)}
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary), flush=True)
    # Existing CTranslate2/CUDA environment can crash at DLL unload on Windows.
    # All durable output above is flushed before exiting, as in voice-review.py.
    import os
    os._exit(0)


if __name__ == "__main__":
    main()
