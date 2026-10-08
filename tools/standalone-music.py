#!/usr/bin/env python3
"""Original soundtrack for the standalone build: generate, master and check (no EA audio involved).

Every track is made by ACE-Step 1.5 running locally (the BeTenshi music service on :8014; MIT code and weights,
"Generated music can be used for commercial purposes" on the model cards). This script records the exact request
for each track (caption, tempo, key, length, seed, steps) and the service's reply metadata, then masters the take:

  1. loop: the take is cut to a whole number of bars and its first bars are crossfaded with the bars that follow
     the cut; of the cuts whose onset envelopes line up best, the one whose wrap brings the smallest onset wins;
  2. loudness: one static gain to -14 LUFS integrated (EBU R128, ffmpeg's meter) and a stereo look-ahead
     limiter for the peaks (run circularly on loops, so the seam stays continuous); true peak <= -1 dBTP;
  3. Ogg Vorbis (q4, 44.1 kHz stereo), which the engine's OggLoader plays.

  python tools/standalone-music.py generate [--only KEY ...] [--seed-offset N]   # needs the music service
  python tools/standalone-music.py master   [--only KEY ...]                     # raw takes -> music/*.ogg
  python tools/standalone-music.py check                                         # seam, loudness, provenance

Raw takes stay outside the repository (--cache, default %TEMP%/rtsai-standalone-music); only the masters ship.
`picks.json` in the cache names the take to master when a track was generated more than once.
Needs numpy and ffmpeg (with libvorbis) on PATH.
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import urllib.request
import uuid
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
AUDIO = ROOT / "mods" / "rtsai" / "standalone" / "audio"
OUT = AUDIO / "music"
YAML = AUDIO / "music.yaml"
PROV = AUDIO / "PROVENANCE.json"
SERVICE = os.environ.get("RTSAI_MUSIC_URL", "http://127.0.0.1:8014")
RATE = 44100
TARGET_LUFS, TARGET_TP = -14.0, -1.5

ENGINE = {
    "engine": "ACE-Step 1.5 text2music (XL turbo DiT + 5Hz LM planner), local BeTenshi music service",
    "code": "github.com/ace-step/ACE-Step-1.5@ca1e85fe9430179831e6bc6be790c332190a3866 (MIT)",
    "model": "ACE-Step/acestep-v15-xl-turbo DiT (int8 weight-only as served), ACE-Step/Ace-Step1.5 "
             "(5Hz LM planner 1.7B, VAE; MIT), Qwen/Qwen3-Embedding-0.6B text encoder (Apache-2.0); the exact "
             "DiT, LM and quantization of each take are in its record",
    "license": "MIT (code and weights); the output carries no third-party rights",
    "license_evidence": "Model cards shipped with the checkpoints (license: mit) and "
                        "https://huggingface.co/ACE-Step/acestep-v15-xl-turbo: 'Commercial-Ready: Trained on legally "
                        "compliant datasets. Generated music can be used for commercial purposes.' Training data per "
                        "the card: licensed music, royalty-free/public domain and synthetic (MIDI-to-audio) data.",
}

# key, title, caption, bpm, key/scale, seconds, theatre. Captions describe style and instruments only: no artist,
# song or anthem names, no lyrics (instrumental), nothing political or religious.
TRACKS = [
    ("rtsai-iron-foundry", "Iron Foundry",
     "industrial rock instrumental, chugging distorted guitar riffs, pounding live drums, gritty synth bass, "
     "metallic percussion hits, driving and aggressive, real-time strategy battle music", 140, "E minor", 180, "all"),
    ("rtsai-grid-assault", "Grid Assault",
     "electronic industrial drum and bass instrumental, fast breakbeats, heavy reese bass, sharp synth stabs, "
     "glitchy arpeggios, tense and relentless, futuristic military", 172, "F minor", 170, "all"),
    ("rtsai-yangtze-steel", "Yangtze Steel",
     "cinematic industrial electronic instrumental, erhu lead melody, guzheng ostinato, Chinese war drums, "
     "heavy synth bass, distorted guitar layer, epic and determined", 128, "D minor", 180, "East Asia"),
    ("rtsai-plateau-engines", "Plateau Engines",
     "dark electronic industrial instrumental, santur arpeggios, tombak and daf hand drums, kamancheh melody, "
     "deep pulsing bass, metallic hits, tense and driving", 124, "A minor", 180, "Persian plateau"),
    ("rtsai-anatolian-armor", "Anatolian Armor",
     "energetic rock and electronic fusion instrumental, baglama saz riffs, davul and darbuka percussion, "
     "zurna reed lead, distorted guitars, powerful drums, heroic and driving", 136, "G minor", 175, "Anatolia"),
    ("rtsai-desert-convoy", "Desert Convoy",
     "big beat electronic instrumental, oud riffs, darbuka and riq percussion, cinematic brass stabs, "
     "synth bass, marching energy, wide desert atmosphere", 126, "C minor", 180, "Arabian peninsula"),
    ("rtsai-cedar-signal", "Cedar Signal",
     "dark electronic instrumental, oud and ney melody, darbuka groove, pulsing analog synth bass, "
     "radio static textures, tense and brooding, steady build", 122, "E minor", 180, "Levant"),
    ("rtsai-coastline-watch", "Coastline Watch",
     "synthwave industrial instrumental, qanun arpeggios, driving electronic drums, gated synth pads, "
     "punchy bass, vigilant and determined", 130, "F# minor", 175, "Levant coast"),
    ("rtsai-black-ore", "Black Ore",
     "heavy industrial metal groove instrumental, down-tuned guitars, machine-like drums, anvil hits, "
     "grinding synths, menacing and powerful", 100, "D minor", 180, "all"),
    ("rtsai-pressure-front", "Pressure Front",
     "tense cinematic industrial electronic instrumental, ticking percussion, low drones, slowly building "
     "synth arpeggio, distant war drums, suspenseful", 96, "C# minor", 180, "all"),
    ("rtsai-final-push", "Final Push",
     "fast industrial techno instrumental, pounding four-on-the-floor kick, distorted acid bassline, metallic "
     "percussion, alarm-like synth leads, intense and triumphant", 145, "A minor", 170, "all"),
    ("score", "Debrief",
     "short cinematic electronic outro instrumental, steady military snare, warm synth pads, low brass, "
     "reflective and resolved", 90, "D major", 75, "score screen"),
]
SEED_BASE = 7300


def cache_dir(a) -> Path:
    d = Path(a.cache)
    d.mkdir(parents=True, exist_ok=True)
    return d


def multipart(fields: dict) -> tuple[bytes, str]:
    b = uuid.uuid4().hex
    parts = [f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode() for k, v in fields.items()]
    parts.append(f"--{b}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={b}"


def generate(a):
    cd = cache_dir(a)
    for i, (key, title, caption, bpm, keyscale, secs, theatre) in enumerate(TRACKS):
        if a.only and key not in a.only:
            continue
        seed = SEED_BASE + i * 10 + a.seed_offset
        raw = cd / f"{key}.seed{seed}.flac"
        if raw.exists() and not a.force:
            print(f"{key}: cached {raw.name}")
            continue
        fields = {"task": "text2music", "caption": caption, "instrumental": "true", "duration": str(secs),
                  "seed": str(seed), "bpm": str(bpm), "keyscale": keyscale, "timesignature": "4",
                  "thinking": "true", "rewrite_caption": "false", "format": "flac"}
        with urllib.request.urlopen(f"{SERVICE}/health", timeout=10) as r:
            health = json.loads(r.read())
        body, ctype = multipart(fields)
        req = urllib.request.Request(f"{SERVICE}/v1/music/generate", data=body, headers={"Content-Type": ctype})
        with urllib.request.urlopen(req, timeout=900) as r:
            data = r.read()
            meta = json.loads(base64.b64decode(r.headers["X-Music-Meta"]))
        raw.write_bytes(data)
        meta.pop("peaks", None)
        side = {"request": fields, "reply": meta, "generated": dt.date.today().isoformat(),
                "service": {k: health.get(k) for k in ("model", "dit", "lm", "lm_backend", "offload", "quantization")}}
        raw.with_suffix(".json").write_text(json.dumps(side, indent=1))
        res = meta.get("resolved") or {}
        print(f"{key}: seed {seed}, {meta.get('audio_seconds')} s in {meta.get('latency_ms')} ms, "
              f"planner {res.get('bpm')} bpm {res.get('keyscale')}", flush=True)


def decode(path: Path) -> np.ndarray:
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "2", "-ar", str(RATE), "-"],
                       capture_output=True, check=True)
    return np.frombuffer(r.stdout, dtype=np.float32).reshape(-1, 2).copy()


def onset_env(x: np.ndarray, hop: int = 512) -> np.ndarray:
    m = x.mean(axis=1)
    n = len(m) // hop
    e = np.log1p(100 * np.sqrt((m[: n * hop].reshape(n, hop) ** 2).mean(axis=1)))
    return np.maximum(0, np.diff(e, prepend=e[0]))


def make_loop(x: np.ndarray, bpm: float) -> tuple[np.ndarray, dict]:
    """Loop of L samples: y = x[0:L] with y[0:xf] = x[0:xf] faded in over x[L:L+xf] faded out (equal power).

    y[-1] = x[L-1] is followed on repeat by y[0] ~ x[L], so the wrap is continuous. Candidates: L a whole number of
    bars, nudged by up to 60 ms; the 12 whose onset envelopes of x[0:xf] and x[L:L+xf] correlate best are built with a
    2- and a 4-bar crossfade, and the loop whose wrap brings the smallest onset (spectral flux ranked against the
    whole take, as `check` measures it) wins.
    """
    bar = 4 * 60.0 / bpm * RATE
    hop = 512
    env = onset_env(x, hop)
    # stay inside the body of the take: the composed ending (fade or silence) is dropped, so both the cut and the
    # crossfade source lie before the last second that is within 20 dB of the loudest one
    sec = len(x) // RATE
    prof = 20 * np.log10(np.sqrt((x[: sec * RATE].mean(axis=1).reshape(sec, RATE) ** 2).mean(axis=1)) + 1e-9)
    body_end = min(len(x), (int(np.nonzero(prof >= prof.max() - 20)[0][-1]) + 1) * RATE)
    f_track = np.sort(flux(x[:body_end].mean(axis=1)))
    xf4 = int(round(4 * bar))
    nbars = int((body_end - xf4) // bar)
    cands = []
    for bars in range(nbars, max(nbars - 8, 8), -1):
        L0 = int(round(bars * bar))
        for d in range(-int(0.06 * RATE), int(0.06 * RATE) + 1, hop // 4):
            L = L0 + d
            if L + xf4 > body_end:
                continue
            a_ = env[: xf4 // hop]
            b_ = env[L // hop: L // hop + xf4 // hop]
            if len(b_) < len(a_):
                continue
            a0, b0 = a_ - a_.mean(), b_ - b_.mean()
            score = float(np.dot(a0, b0) / (np.linalg.norm(a0) * np.linalg.norm(b0) + 1e-9))
            cands.append((score - 0.01 * (nbars - bars), score, L))
    cands.sort(reverse=True)
    picked = []
    for c in cands:   # 12 best, at least a quarter bar apart
        if all(abs(c[2] - q[2]) > bar / 4 for q in picked):
            picked.append(c)
        if len(picked) == 12:
            break
    best = None
    for _, score, L in picked:
        for xbars in (2, 4):
            xf = int(round(xbars * bar))
            t = np.linspace(0, np.pi / 2, xf)[:, None]
            head = x[:xf] * np.sin(t) + x[L:L + xf] * np.cos(t)
            w = 4096
            wrap = np.concatenate([x[L - w:L].mean(axis=1), head[:w].mean(axis=1)])
            fw = flux(wrap)
            mid = len(fw) // 2
            pct = float(np.searchsorted(f_track, fw[max(0, mid - 3): mid + 3].max()) / len(f_track) * 100)
            key = (round(pct), -score, -L)
            if best is None or key < best[0]:
                best = (key, pct, score, L, xf, xbars)
    _, pct, score, L, xf, xbars = best
    t = np.linspace(0, np.pi / 2, xf)[:, None]
    y = x[:L].copy()
    y[:xf] = x[:xf] * np.sin(t) + x[L:L + xf] * np.cos(t)
    return y, {"loop_seconds": round(len(y) / RATE, 2), "crossfade_seconds": round(xf / RATE, 2),
               "crossfade_bars": xbars, "loop_bars": round(L / bar, 2), "onset_alignment": round(score, 3),
               "wrap_flux_percentile_estimate": round(pct, 1), "source_seconds": round(len(x) / RATE, 2)}


def last_json(text: str) -> dict:
    return json.loads(text[text.rindex("{"):text.rindex("}") + 1])


def lufs(x: np.ndarray, tmp: Path) -> tuple[float, float]:
    """Integrated loudness and true peak (ffmpeg's EBU R128 meter)."""
    src = tmp / "m.f32"
    src.write_bytes(x.astype(np.float32).tobytes())
    r = subprocess.run(["ffmpeg", "-hide_banner", "-f", "f32le", "-ac", "2", "-ar", str(RATE), "-i", str(src), "-af",
                        "loudnorm=print_format=json", "-f", "null", "-"], capture_output=True, text=True, check=True)
    m = last_json(r.stderr)
    return float(m["input_i"]), float(m["input_tp"])


def limit(x: np.ndarray, ceiling_db: float, loop: bool, look: float = 0.0015, release: float = 0.12) -> np.ndarray:
    """Stereo-linked look-ahead peak limiter. For loops it runs on the circularly padded signal, so the gain is
    continuous across the wrap."""
    ceil = 10 ** (ceiling_db / 20)
    pad = int(RATE) if loop else 0
    z = np.concatenate([x[-pad:], x, x[:pad]]) if loop else x
    need = np.minimum(1.0, ceil / (np.abs(z).max(axis=1) + 1e-12))
    la = max(1, int(look * RATE))
    win = np.lib.stride_tricks.sliding_window_view(np.concatenate([need, np.ones(2 * la)]), 2 * la + 1).min(axis=1)
    win = win[: len(need)]
    rel = 1 - np.exp(-1 / (release * RATE))
    g = np.empty(len(win))
    s_ = 1.0
    for i, v in enumerate(win.tolist()):
        s_ = v if v < s_ else s_ + rel * (v - s_)
        g[i] = s_
    g = np.convolve(np.concatenate([np.full(la - 1, g[0]), g]), np.ones(la) / la, "valid")
    y = z * g[:, None]
    y = y[pad: pad + len(x)] if loop else y
    return np.clip(y, -ceil, ceil)


def loudnorm(x: np.ndarray, out: Path, tmp: Path, loop: bool) -> dict:
    """Static gain to TARGET_LUFS, a gentle look-ahead limiter for the peaks, then Ogg Vorbis. No dynamic
    normalisation, so the music keeps its own dynamics and a loop keeps its seam."""
    i0, tp0 = lufs(x, tmp)
    y = x * 10 ** ((TARGET_LUFS - i0) / 20)
    for _ in range(3):
        y = limit(y, TARGET_TP - 1.2, loop)
        i1, _tp = lufs(y, tmp)
        if abs(i1 - TARGET_LUFS) <= 0.2:
            break
        y = y * 10 ** ((TARGET_LUFS - i1) / 20)
    src = tmp / "in.f32"
    src.write_bytes(y.astype(np.float32).tobytes())
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-v", "error", "-f", "f32le", "-ac", "2", "-ar", str(RATE),
                    "-i", str(src), "-c:a", "libvorbis", "-q:a", "4", "-map_metadata", "-1", "-fflags", "+bitexact",
                    "-flags:a", "+bitexact", str(out)], check=True)
    i2, tp2 = lufs(decode(out), tmp)
    return {"input_lufs": i0, "input_true_peak": tp0, "output_lufs": i2, "output_true_peak": tp2,
            "normalization": f"static gain {TARGET_LUFS - i0:+.2f} dB, look-ahead limiter at {TARGET_TP - 1.2} dBFS"}


def chosen(cd: Path, key: str):
    pick = cd / "picks.json"
    picks = json.loads(pick.read_text()) if pick.exists() else {}
    if key in picks:
        return cd / picks[key]
    takes = sorted(cd.glob(f"{key}.seed*.flac"))
    return takes[0] if takes else None


def load_prov() -> dict:
    return json.loads(PROV.read_text(encoding="utf-8")) if PROV.exists() else {"files": {}}


def save_prov(prov: dict):
    """Merge this run's records into the file as it is now (other generators write to it too)."""
    current = load_prov()
    current["files"].update(prov["files"])
    prov = current
    PROV.write_text(json.dumps(prov, indent=1, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8",
                    newline="\n")


def master(a):
    cd = cache_dir(a)
    OUT.mkdir(parents=True, exist_ok=True)
    prov = {"files": {}}   # this run's records only; save_prov merges them into the file
    with tempfile.TemporaryDirectory() as td:
        for key, title, caption, bpm, keyscale, secs, theatre in TRACKS:
            if a.only and key not in a.only:
                continue
            raw = chosen(cd, key)
            if raw is None:
                print(f"{key}: no take yet")
                continue
            meta = json.loads(raw.with_suffix(".json").read_text())
            x = decode(raw)
            bpm_used = float((meta["reply"].get("resolved") or {}).get("bpm") or bpm)
            if key == "score":
                # plays once: keep the composed ending, trim trailing silence below -50 dBFS, short fade
                lvl = np.sqrt(np.convolve(x.mean(axis=1) ** 2, np.ones(2048) / 2048, "same"))
                last = int(np.nonzero(lvl > 10 ** (-50 / 20))[0][-1]) + int(0.25 * RATE)
                y = x[: min(len(x), last)].copy()
                n = int(0.5 * RATE)
                y[-n:] *= np.linspace(1, 0, n)[:, None]
                loop = {"loop_seconds": None, "note": "plays once on the victory/defeat screen; not looped"}
            else:
                y, loop = make_loop(x, bpm_used)
            out = OUT / f"{key}.ogg"
            ln = loudnorm(y, out, Path(td), loop=key != "score")
            prov["files"][f"music/{key}.ogg"] = {
                "category": "music", "title": title, "theatre": theatre, "generator": "tools/standalone-music.py",
                **ENGINE, "prompt": caption, "request": meta["request"], "seed": int(meta["request"]["seed"]),
                "planner": meta["reply"].get("resolved"), "dit": meta["reply"].get("dit"),
                "lm": meta["reply"].get("lm"), "steps": meta["reply"].get("steps"), "service": meta.get("service"),
                "raw_take_sha256": hashlib.sha256(raw.read_bytes()).hexdigest(),
                "mastering": {**loop, **ln, "codec": "Ogg Vorbis q4, 44.1 kHz stereo"},
                "generated": meta.get("generated"), "sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
                "notes": "AI-generated instrumental. A generated track can still resemble existing music by chance.",
            }
            print(f"{key}: {loop.get('loop_seconds')} s, align {loop.get('onset_alignment')}, "
                  f"{ln['input_lufs']} -> {ln['output_lufs']} LUFS, TP {ln['output_true_peak']}", flush=True)
    lines = ["# Original RTS AI soundtrack for the standalone build, made locally with ACE-Step 1.5 (MIT).",
             "# Per-file provenance: PROVENANCE.json next to this file; generator: tools/standalone-music.py.",
             "# 'score' plays on the victory and defeat screens (MusicPlaylist in rules/world.yaml), so it is hidden.",
             "# The tracks are Ogg Vorbis: the manifest's SoundFormats must include Ogg.", ""]
    for key, title, *_ in TRACKS:
        if (OUT / f"{key}.ogg").exists():
            lines += [f"{key}: {title}", f"\tFilename: {key}", "\tExtension: ogg"]
            if key == "score":
                lines.append("\tHidden: true")
    YAML.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    save_prov(prov)


def flux(m: np.ndarray, hop: int = 512, size: int = 2048) -> np.ndarray:
    """Positive log-spectral flux per hop: how much new energy each frame brings, the onset measure."""
    n = (len(m) - size) // hop
    idx = np.arange(size)[None, :] + hop * np.arange(n)[:, None]
    spec = np.log1p(np.abs(np.fft.rfft(m[idx] * np.hanning(size), axis=1)))
    return np.maximum(0, np.diff(spec, axis=0)).sum(axis=1)


def seam(y: np.ndarray) -> dict:
    """Does the file repeat cleanly? The wrap (end followed by start) must not bring a bigger onset than the music
    itself does: its spectral flux is ranked against every frame of the track, and its sample step against the
    track's 99th-percentile step."""
    m = y.mean(axis=1)
    f_track = flux(m)
    w = 4096
    f_wrap = flux(np.concatenate([m[-w:], m[:w]]))
    mid = len(f_wrap) // 2
    wrap = float(f_wrap[max(0, mid - 3): mid + 3].max())
    return {"wrap_flux_percentile": round(float((f_track < wrap).mean() * 100), 1),
            "wrap_step": round(float(np.abs(y[0] - y[-1]).max()), 4),
            "p99_step": round(float(np.percentile(np.abs(np.diff(y, axis=0)), 99)), 4)}


def check(a) -> int:
    prov = load_prov()
    bad = 0
    for key, title, *_ in TRACKS:
        f = OUT / f"{key}.ogg"
        if not f.exists():
            print(f"MISSING {f.name}")
            bad += 1
            continue
        y = decode(f)
        rec = prov["files"].get(f"music/{key}.ogg")
        s = seam(y)
        ok_seam = key == "score" or (s["wrap_flux_percentile"] <= 99.5 and s["wrap_step"] <= 2 * max(s["p99_step"], 1e-3))
        ok_prov = bool(rec) and rec.get("sha256") == hashlib.sha256(f.read_bytes()).hexdigest()
        r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(f), "-af", "loudnorm=print_format=json", "-f", "null",
                            "-"], capture_output=True, text=True)
        lufs = float(last_json(r.stderr)["input_i"])
        ok_lufs = abs(lufs - TARGET_LUFS) <= 1.0
        state = "ok" if ok_seam and ok_prov and ok_lufs else "FAIL"
        bad += state != "ok"
        print(f"{state:4s} {f.name:28s} {len(y) / RATE:6.1f} s {lufs:6.1f} LUFS seam {s} "
              f"provenance {'ok' if ok_prov else 'MISSING/STALE'}")
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["generate", "master", "check"])
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--seed-offset", type=int, default=0)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--cache", default=str(Path(tempfile.gettempdir()) / "rtsai-standalone-music"))
    a = ap.parse_args()
    if a.cmd == "generate":
        generate(a)
    elif a.cmd == "master":
        master(a)
    else:
        sys.exit(check(a))


if __name__ == "__main__":
    main()
