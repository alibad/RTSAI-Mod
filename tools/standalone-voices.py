#!/usr/bin/env python3
"""Voices for the shared stock units the standalone build keeps (engineer, spy, MCVs and ore trucks, the naval
transports, and the generic infantry death cries), made with the same licensed engines as the faction sets.

Speech comes from OpenRA-AI's scripts/voice_engines.py: Kokoro-82M (Apache-2.0) at the pinned revision, the same
QA (Whisper large-v3 transcript and character error rate) and a radio chain in the style of the faction sets
(ffmpeg band-pass, compression, loudness, squelch tone, noise floor, fades). These units are shared by several
factions (the Allied-side or the Soviet-side voice set), so every line is English, as the faction sets' English lines
are. Speakers are new blends of the voicepacks the factions already use; no real person is imitated.

The death cries come from Chatterbox (MIT), the faction sets' cloning engine, cloned from the speaker's Kokoro English
reference at exaggeration 1.0: Kokoro reads interjections as words. Of ten seeds, the take Whisper hears as a bare
interjection and closest to the expected length is kept. Melted, Zapped and PsyCrush add a procedural layer from
tools/standalone_dsp.py.

  python tools/standalone-voices.py build [FILE ...] [--openra-ai ../OpenRA-AI] [--device cuda]
  python tools/standalone-voices.py list

Run it in the voice environment described in OpenRA-AI scripts/voice_engines.py (kokoro 0.9.4, faster-whisper
1.2.1, torch). Output: mods/rtsai/standalone/audio/voices/*.wav (44.1 kHz mono 16-bit, like the faction sets),
records in mods/rtsai/standalone/audio/PROVENANCE.json and rows in docs/voice-review.csv.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import standalone_dsp as D  # noqa: E402

AUDIO = ROOT / "mods" / "rtsai" / "standalone" / "audio"
OUT = AUDIO / "voices"
PROV = AUDIO / "PROVENANCE.json"
SHEET = ROOT / "docs" / "voice-review.csv"
GENERATOR = "tools/standalone-voices.py"
VERSION = "rtsai-standalone-voices-1"
RATE = 44100
REF_SECONDS = {k: v["seconds"] for k, v in json.loads(
    (ROOT / "tools" / "standalone-audio" / "reference-metrics.json").read_text())["sounds"].items()}

ALLIED = "shared, Allied side (China, Türkiye, Saudi Arabia, Israel)"
SOVIET = "shared, Soviet side (Iran, Yemen, Hezbollah)"
ALL = "shared, all seven factions"

# speaker id -> (Kokoro voicepacks, G2P accent). Blends of the packs the faction sets use.
SPEAKERS = {
    "shared-engineer-allied": (("am_adam", "am_puck"), "a"),
    "shared-engineer-soviet": (("bm_george", "am_michael"), "b"),
    "shared-spy": (("bm_fable",), "b"),
    "shared-crew-allied": (("am_michael", "am_fenrir"), "a"),
    "shared-crew-soviet": (("bm_lewis", "am_fenrir"), "b"),
    "shared-naval-allied": (("am_puck", "bm_fable"), "a"),
    "shared-naval-soviet": (("am_michael", "bm_lewis"), "a"),
    "shared-infantry": (("am_fenrir", "am_puck"), "a"),
}

# chain id -> (ffmpeg filters, squelch tone Hz or 0, noise amplitude, character)
CHAINS = {
    "radio": ("highpass=f=200,lowpass=f=5600,acompressor=threshold=-21dB:ratio=3:attack=5:release=80,"
              "loudnorm=I=-18:TP=-2:LRA=7", 1050, 60, "shared tactical radio"),
    "crew": ("highpass=f=220,lowpass=f=5000,acompressor=threshold=-21dB:ratio=3.5:attack=4:release=70,"
             "loudnorm=I=-18:TP=-2:LRA=7", 950, 75, "vehicle intercom radio"),
    "cry": ("highpass=f=110,lowpass=f=7500,acompressor=threshold=-20dB:ratio=2.5:attack=3:release=60,"
            "loudnorm=I=-16:TP=-1.5:LRA=7", 0, 0, "in-world cry, no radio"),
}


@dataclass(frozen=True)
class Line:
    file: str
    speaker: str
    text: str          # what is spoken (and checked)
    role: str
    side: str
    unit_set: str
    chain: str = "radio"
    tempo: float = 1.0
    cry: str = ""      # "", "plain", "melt", "zap", "crush"


def lines() -> list[Line]:
    L = []

    def add(prefix, speaker, side, unit_set, chain, table, tempo=1.0):
        for kind, entries in table.items():
            for suffix, text in entries:
                cry = "plain" if kind == "die" else ""
                L.append(Line(f"{prefix}{suffix}.wav", speaker, text,
                              f"{unit_set} {kind}", side, unit_set, "cry" if cry else chain,
                              1.0 if cry else tempo, cry))

    add("iena", "shared-engineer-allied", ALLIED, "engineer (EngineerVoice, iena)", "radio", {
        "select": [("sea", "Engineer ready."), ("seb", "Tools ready. What's the job?"),
                   ("sec", "What needs fixing?"), ("sed", "Engineer on the net.")],
        "move": [("moa", "Moving."), ("mob", "On my way."), ("moc", "Heading there now.")],
        "action": [("ata", "I'll take that building."), ("atb", "Going in."), ("atc", "Securing the site.")],
        "feedback": [("fea", "Taking fire!"), ("feb", "I need cover!"), ("fec", "Get me out of here!")],
        "die": [("dia", "Aaaargh!"), ("dib", "Augh!"), ("dic", "Nooo!"), ("did", "Ungh!")],
    })
    add("iens", "shared-engineer-soviet", SOVIET, "engineer (EngineerVoice, iens)", "radio", {
        "select": [("sea", "Engineer standing by."), ("seb", "Ready to work."), ("sec", "Give me a job."),
                   ("sed", "Field engineer here.")],
        "move": [("moa", "Moving out."), ("mob", "Going."), ("moc", "Right away.")],
        "action": [("ata", "Taking over the building."), ("atb", "Wiring it up now."), ("atc", "I'm going inside.")],
        "feedback": [("fea", "They're shooting at me!"), ("feb", "Cover me!"), ("fec", "I need support!")],
        "die": [("dia", "Arrgh!"), ("dib", "Aaah!"), ("dic", "Ohhh!"), ("did", "Ugh!")],
    })
    add("ispy", "shared-spy", ALLIED, "spy (SpyVoice)", "radio", {
        "select": [("sea", "Yes?"), ("seb", "Listening."), ("sec", "Quietly now."), ("sed", "Agent ready.")],
        "move": [("ata", "On my way."), ("mob", "Blending in."), ("moc", "Nobody will notice."),
                 ("mod", "Moving discreetly."), ("moe", "Consider it done.")],
        "action": [("atb", "Getting inside."), ("atd", "Let's see what they know.")],
        "feedback": [("fea", "My cover is blown!"), ("feb", "They're onto me.")],
        "die": [("dia", "Aaargh!"), ("dib", "Ungh!"), ("dic", "Aaah!")],
    }, tempo=0.95)
    add("vgra", "shared-crew-allied", ALLIED, "MCV and ore truck (AlliedConstructionVehicleVoice, ChronoMinerVoice)",
        "crew", {
            "select": [("sea", "Vehicle ready."), ("seb", "Driver here."), ("sec", "Systems green."),
                       ("sed", "Awaiting orders."), ("see", "Standing by.")],
            "move": [("mob", "Rolling."), ("mod", "Moving out."), ("moe", "On the way."), ("mof", "Route set.")],
            "attack": [("ata", "Understood."), ("atb", "Copy that."), ("atc", "Will do."), ("atd", "Acknowledged."),
                       ("ate", "Right away.")],
        })
    add("vgrs", "shared-crew-soviet", SOVIET, "MCV, ore truck and AA track (SovietVehicleVoice)", "crew", {
        "select": [("sea", "Crew here."), ("seb", "Engine running."), ("sec", "Ready to move.")],
        "move": [("moa", "Moving."), ("mob", "Heading out."), ("moc", "Rolling forward.")],
        "attack": [("ata", "Engaging."), ("atb", "Target acquired."), ("atc", "Opening fire."),
                   ("atd", "Weapons free.")],
    })
    add("vwaa", "shared-naval-allied", ALLIED, "landing craft (AlliedNavalVoice)", "crew", {
        "select": [("sea", "Boat ready."), ("seb", "Helm here."), ("sec", "Ready to load."),
                   ("sed", "Landing craft standing by.")],
        "move": [("moa", "Underway."), ("mob", "Setting course."), ("moc", "Heading for the beach."),
                 ("mod", "Full ahead."), ("moe", "Course laid in.")],
        "attack": [("ata", "Engaging."), ("atb", "Target in sight."), ("atc", "Firing.")],
    })
    add("vwas", "shared-naval-soviet", SOVIET, "amphibious transport (SovietNavalVoice)", "crew", {
        "select": [("sea", "Transport ready."), ("seb", "Hatch is open."), ("sec", "Amphibious crew here.")],
        "move": [("moa", "Into the water."), ("mob", "Moving."), ("moc", "Crossing now."), ("mod", "Heading to shore.")],
        "attack": [("ata", "Engaging."), ("atb", "Target spotted."), ("atc", "Opening fire.")],
    })
    # generic infantry death cries (every modern infantry voice set's Die, and the dog/spy death types)
    for f, text, cry, role in [
        ("igidia", "Aaaargh!", "plain", "infantry death cry (all modern infantry Die)"),
        ("igidib", "Augh!", "plain", "infantry death cry (all modern infantry Die)"),
        ("igidic", "Ungh!", "plain", "infantry death cry (all modern infantry Die)"),
        ("igenmela", "Aaaaah!", "melt", "death by acid or radiation (Melted)"),
        ("igenmelb", "Arrgh!", "melt", "death by acid or radiation (Melted)"),
        ("igenmelc", "Aaah!", "melt", "death by acid or radiation (Melted)"),
        ("igenzapa", "Aaargh!", "zap", "death by electric shock (Zapped)"),
        ("igenexpa", "Ugh!", "crush", "death by crushing force (PsyCrush)"),
    ]:
        L.append(Line(f"{f}.wav", "shared-infantry", text, role, ALL, "generic infantry deaths", "cry", 1.0, cry))
    return L


# ------------------------------------------------------------------------------------------------ processing
def read_wav(path: Path) -> np.ndarray:
    with wave.open(str(path), "rb") as w:
        return np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float64) / 32768.0


def write_wav(path: Path, x: np.ndarray, rate: int = RATE):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(np.clip(np.round(x * 32767), -32768, 32767).astype("<i2").tobytes())


def radio_finish(x: np.ndarray, name: str, tone: int, noise: int) -> np.ndarray:
    """Squelch tone, a low noise floor and fades (as the faction generators), deterministic per file."""
    R = D.Rand(VERSION, "radio", name)
    out = []
    if tone:
        k = int(RATE * 0.04)
        out.append(1100 / 32768 * np.sin(2 * np.pi * tone * np.arange(k) / RATE))
        out.append(np.zeros(int(RATE * 0.025)))
    n = len(x)
    i = np.arange(n)
    fade = np.minimum(1.0, np.minimum(i / max(1, int(RATE * 0.015)), (n - i) / max(1, int(RATE * 0.025))))
    hiss = R.g.integers(-noise, noise + 1, n) / 32768 if noise else 0
    out.append((x + hiss) * np.maximum(0.0, fade))
    y = np.concatenate(out)
    peak = np.max(np.abs(y)) * 32768
    return y * min(1.0, 26000 / max(peak, 1))


def cry_layer(x: np.ndarray, kind: str, name: str) -> np.ndarray:
    """Procedural layer under a death cry: acid sizzle and bubbling, electric arcs, or a crunch."""
    R = D.Rand(VERSION, "cry", name)
    sr = D.SR
    # work at 22.05 kHz with the dsp kit, then resample to 44.1 kHz by linear interpolation
    n = int(len(x) / RATE * sr) + int(0.5 * sr)
    if kind == "melt":
        siz = D.hp(R.noise(n) * (1 + 2.5 * np.abs(D.smooth_noise(R, n, 80))), 2500) * D.env(n, 0.05, 1.2)
        bub = D.bubbles(R.sub("b"), n, 90, 0.05, n / sr * 0.9, f_lo=300, f_hi=1500, amp=1.0)
        fx = 0.6 * D.norm(siz) + 0.5 * D.norm(bub)
        gain = 0.45
    elif kind == "zap":
        fx = D.arcs(R, n, 0.0, n / sr * 0.8, rate=35) + 0.4 * D.norm(
            D.additive(np.full(n, 120.0), (1, 2, 3, 5, 7), tilt=0.6)) * D.env(n, 0.005, 0.9)
        gain = 0.55
    elif kind == "crush":
        fx = D.explosion(R, n, size=0.35, crack=0.8, body=0.6, sub=0.8, rumble=0.0, debris_amt=0.2, t60=0.4,
                         fc0=2500, fc1=300, metallic=0.0)
        fx = fx + 0.5 * D.norm(D.bubbles(R.sub("w"), n, 30, 0.02, 0.3, f_lo=200, f_hi=700, amp=1.0))
        gain = 0.5
    else:
        return x
    t_src = np.arange(n) / sr
    t_dst = np.arange(max(len(x), int(n / sr * RATE))) / RATE
    fx44 = np.interp(t_dst, t_src, D.norm(fx))
    y = np.zeros(len(t_dst))
    y[: len(x)] += x
    y += gain * fx44 * np.max(np.abs(x))
    return y


def ffmpeg_chain(src: Path, dst: Path, filters: str, extra: str = ""):
    af = ",".join(f for f in (extra, filters) if f)
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(src), "-af", af, "-ar",
                    str(RATE), "-ac", "1", "-c:a", "pcm_s16le", str(dst)], check=True)


CRY_SEEDS = 10
CRY_EXAGGERATION = 1.0
CRY_WORDS = re.compile(r"^(a+r*g*h*|ar+g+h*|ah+|aw+|ark|augh|ugh+|ung+h*|uh+|oh+|no+|ow+)$")


def cry_take(ve, synth, ln: Line, raw: Path):
    """A death cry from Chatterbox (MIT), cloned from the speaker's Kokoro English reference at a high exaggeration.
    Kokoro reads interjections as words ("I egg", "oh yeah"), so the cries use the faction sets' second engine.
    Seeds 1..CRY_SEEDS; a take is usable when Whisper hears only an interjection and it lasts 0.3-1.4 s; the usable
    take closest to the expected length wins (ties: lower seed)."""
    import soundfile as sf
    ref = synth.reference(ln.speaker, "en")
    target = REF_SECONDS.get(ln.file, 0.8)
    takes = []
    for seed in range(1, CRY_SEEDS + 1):
        try:
            audio, rate = synth.chatterbox(ln.text, "en", ref.path, seed, exaggeration=CRY_EXAGGERATION)
        except RuntimeError as error:
            print(f"  seed {seed} failed: {error}", flush=True)
            continue
        audio = ve.fade(ve.trim_silence(audio, rate), rate)
        heard, _ = synth.transcribe(audio, rate, "en")
        words = re.sub(r"[^a-z ]", " ", heard.lower()).split()
        ok = bool(words) and len(words) <= 2 and all(CRY_WORDS.match(w) for w in words)
        dur = len(audio) / rate
        takes.append((not (ok and 0.3 <= dur <= 1.4), abs(dur - target), seed, audio, rate, heard))
    if not takes:
        raise RuntimeError(f"no cry take for {ln.file}")
    bad, _, seed, audio, rate, heard = min(takes, key=lambda t: (t[0], t[1], t[2]))
    sf.write(raw, audio * (0.89 / (np.max(np.abs(audio)) or 1)), rate, subtype="FLOAT")
    spec = ve.ENGINES["chatterbox"]
    speaker = ve.SPEAKERS[ln.speaker]
    rec = {"engine": spec["engine"], "engine_id": "chatterbox", "model": spec["model"],
           "model_revision": spec["revision"], "license": spec["license"],
           "voice": {"speaker": ln.speaker, "kokoro_voicepacks": list(speaker.voicepacks),
                     "method": f"Chatterbox clone (exaggeration {CRY_EXAGGERATION}) of the speaker's Kokoro English "
                               "reference clip; no real person", "reference": ref.record},
           "language": "en-US", "text": ln.text, "tempo": 1.0, "seed": seed, "takes": len(takes),
           "exaggeration": CRY_EXAGGERATION,
           "qa": {"asr_transcript": heard, "cer": None, "usable": not bad,
                  "note": "non-verbal cry: picked by an interjection-only transcript and the expected length"},
           "generated_at": dt.date.today().isoformat(), "generator_version": ve.GENERATOR_VERSION}
    print(f"  {ln.file}: seed {seed} of {len(takes)}, {len(audio) / rate:.2f} s, heard '{heard}'"
          + ("" if not bad else " (no take passed; closest kept)"), flush=True)
    return rec, rate


# ------------------------------------------------------------------------------------------------ build
def load_engines(openra_ai: Path):
    sys.path.insert(0, str(openra_ai / "scripts"))
    import voice_engines as ve  # noqa: E402
    for sid, (packs, accent) in SPEAKERS.items():
        ve.SPEAKERS[sid] = ve.Speaker(packs, accent)
    return ve


def build(a):
    ve = load_engines(Path(a.openra_ai).resolve())
    synth = ve.Synthesizer(device=a.device, verify=True)
    model = synth._asr()
    todo = [ln for ln in lines() if not a.files or ln.file in a.files]
    OUT.mkdir(parents=True, exist_ok=True)
    records, rows = {}, []
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        for ln in todo:
            raw = td / f"{ln.file}.raw.wav"
            filters, tone, noise, character = CHAINS[ln.chain]
            if ln.cry:
                rec, rate = cry_take(ve, synth, ln, raw)
                extra = ""
            else:
                rec = synth.render(ln.text, "en-US", ln.speaker, raw, rate=ln.tempo)
                extra = ""
            dst = OUT / ln.file
            ffmpeg_chain(raw, dst, filters, extra)
            x = read_wav(dst)
            if ln.cry in ("melt", "zap", "crush"):
                x = cry_layer(x, ln.cry, ln.file)
                x = x / max(np.max(np.abs(x)), 1e-9) * 0.79
                x = D.fade(x, 0.0, 0.03) if len(x) > 2000 else x
            if tone or noise:
                x = radio_finish(x, ln.file, tone, noise)
            elif not ln.cry or ln.cry == "plain":
                x = x / max(np.max(np.abs(x)), 1e-9) * 0.79
            write_wav(dst, x)
            data = dst.read_bytes()
            # language ID of the shipped file, for the review sheet
            segs, info = model.transcribe(str(dst), beam_size=5, condition_on_previous_text=False, vad_filter=False)
            heard = "".join(s.text for s in segs).strip()
            top = sorted(info.all_language_probs or [], key=lambda p: -p[1])[:3]
            cer = None if ln.cry else ve.character_error_rate(ve.normalize_for_cer(ln.text, "en"),
                                                              ve.normalize_for_cer(heard, "en"))
            records[f"voices/{ln.file}"] = {
                "category": "voice", "role": ln.role, "unit_set": ln.unit_set, "side": ln.side,
                "generator": GENERATOR, **rec,
                "license_evidence": ve.ENGINES["kokoro"]["license_evidence"],
                "processing": f"ffmpeg {(extra + ',') if extra else ''}{filters}; {character}"
                              + ("; squelch tone, noise floor and fades" if tone else "")
                              + (f"; procedural {ln.cry} layer (tools/standalone_dsp.py, seed "
                                 f"sha256('{VERSION}/cry/{ln.file}'))" if ln.cry in ("melt", "zap", "crush") else ""),
                "shipped_check": {"asr_transcript": heard, "cer": None if cer is None else round(cer, 3)},
                "sample_rate": RATE, "channels": 1, "sample_width_bits": 16,
                "duration_seconds": round(len(x) / RATE, 3),
                "synthetic_voice_disclosed": True, "real_person_imitation": False,
                "sha256": hashlib.sha256(data).hexdigest(),
            }
            rows.append({
                "file": f"standalone/voices/{ln.file}", "faction": ln.side, "language": "en-US", "engine": rec["engine_id"],
                "role": ln.role, "intended_text": ln.text, "english_line": ln.text, "asr_transcript": heard,
                "cer": "" if cer is None else f"{cer:.3f}",
                "detected_language": " ".join(f"{c}:{p:.2f}" for c, p in top), "whisper_translation": "",
                "low_confidence_words": "", "literal_meaning": "",
                "verdict": ("non-verbal cry: check by ear" if ln.cry else ("ok" if cer <= 0.05 else "check by ear")),
                "action": "none", "notes": "shared stock unit, standalone build", "native_speaker": "",
            })
            print(f"voices/{ln.file}: '{ln.text}' heard '{heard}'" + ("" if cer is None else f" CER {cer:.3f}"),
                  flush=True)
    save(records, rows)
    sys.stderr.flush()
    sys.stdout.flush()
    os._exit(0)   # see tools/voice-review.py: releasing a CTranslate2 model on Windows/CUDA can crash the process


def save(records: dict, rows: list[dict]):
    prov = json.loads(PROV.read_text(encoding="utf-8")) if PROV.exists() else {"files": {}}
    prov["files"].update(records)
    PROV.write_text(json.dumps(prov, indent=1, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8",
                    newline="\n")
    with SHEET.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames
        existing = list(reader)
    mine = {r["file"]: r for r in rows}
    human = ("literal_meaning", "verdict", "action", "notes", "native_speaker")
    out = []
    for r in existing:
        if r["file"] in mine:
            fresh = mine.pop(r["file"])
            fresh.update({k: r[k] for k in human if r.get(k) and k in ("literal_meaning", "native_speaker")})
            out.append(fresh)
        else:
            out.append(r)
    out += list(mine.values())
    with SHEET.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["build", "list"])
    ap.add_argument("files", nargs="*")
    ap.add_argument("--openra-ai", default=str(ROOT.parent / "OpenRA-AI"))
    ap.add_argument("--device", default=None)
    a = ap.parse_args()
    if a.cmd == "list":
        for ln in lines():
            print(f"{ln.file:14s} {ln.speaker:24s} {ln.chain:5s} {ln.text}")
        print(len(lines()), "lines")
    else:
        build(a)


if __name__ == "__main__":
    main()
