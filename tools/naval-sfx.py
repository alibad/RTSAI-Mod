#!/usr/bin/env python3
"""Reproduce the four procedural naval sound effects the modern factions ship (stdlib only).

The formulas and the synth() routine are copied unchanged from packaging/naval/generate_naval_assets.py in the
alibad/OpenRA fork, commit 1d76c546f1 ("Add Saudi and Yemen naval systems", 12 August 2026), which added both the
generator and its output (mods/ra/bits/naval/*.wav). Each sound is sine waves and/or noise from Python's own
random.Random seeded with the sound's name: no recording or sample library is involved.

    python tools/naval-sfx.py           # check: regenerate in memory and compare with the shipped files
    python tools/naval-sfx.py --write   # rewrite mods/rtsai/modern-factions/audio/naval-*.wav
"""
from __future__ import annotations

import argparse
import hashlib
import io
import math
import random
import struct
import sys
import wave
from pathlib import Path

AUDIO = Path(__file__).resolve().parents[1] / "mods" / "rtsai" / "modern-factions" / "audio"
TAU = math.tau
# name in the fork -> (duration in seconds, formula), from build_audio() at 1d76c546f1
SOUNDS = {
    "radar-sweep": (.82, lambda t, r: .38 * math.sin(TAU * (420 + 720 * t) * t) * (1 - t / .82)),
    "naval-alarm": (1.05, lambda t, r: .42 * math.sin(TAU * (630 if int(t * 6) % 2 else 470) * t)),
    "ciws-burst": (.34, lambda t, r: .52 * (r.random() * 2 - 1) * (1 if int(t * 58) % 2 == 0 else .18)),
    "missile-launch": (.72, lambda t, r: (.48 * (r.random() * 2 - 1) + .24 * math.sin(TAU * (120 - 70 * t) * t))
                       * (1 - t / .72)),
}


def synth(name: str, duration: float, fn) -> bytes:
    """generate_naval_assets.synth(), returning the WAV bytes instead of writing mods/ra/bits/naval/<name>.wav."""
    rate = 22050
    rng = random.Random(name)
    samples = []
    for i in range(round(duration * rate)):
        t = i / rate
        value = fn(t, rng)
        envelope = min(1.0, t / 0.012, max(0.0, (duration - t) / 0.035))
        samples.append(value * envelope)
    peak = max(abs(v) for v in samples) or 1
    gain = 0.70 / peak
    pcm = b"".join(struct.pack("<h", round(max(-1, min(1, v * gain)) * 32767)) for v in samples)
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(rate)
        out.writeframes(pcm)
    return buffer.getvalue()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--write", action="store_true", help="write the files instead of checking them")
    args = parser.parse_args()
    mismatched = 0
    for name, (duration, fn) in SOUNDS.items():
        data = synth(name, duration, fn)
        path = AUDIO / f"naval-{name}.wav"
        if args.write:
            path.write_bytes(data)
            print(f"wrote {path.name} sha256 {hashlib.sha256(data).hexdigest()}")
            continue
        same = path.exists() and path.read_bytes() == data
        mismatched += not same
        print(f"{path.name}: {'identical' if same else 'DIFFERS'} (sha256 {hashlib.sha256(data).hexdigest()})")
    return 1 if mismatched else 0


if __name__ == "__main__":
    sys.exit(main())
