#!/usr/bin/env python3
"""Procedural weapon, impact, explosion, UI and dog sounds for the standalone build (no EA audio, no samples).

Each file the rules name gets a recipe below: sine waves, seeded noise, filters, envelopes and a synthetic reverb from
tools/standalone_dsp.py. The noise is seeded from the file name, so a rebuild reproduces every file. Length and
loudness follow coarse numbers measured from the sound the rules expected (tools/standalone-audio/
reference-metrics.json): the file is cut or padded to that length, and its loudest 50 ms is brought to the same level
under a -0.3 dBFS look-ahead limiter (at most 12 dB of limiting). Output: 22.05 kHz mono 16-bit PCM WAV (chrono2.aud: Westwood IMA ADPCM, the name the rules use).

  python tools/standalone-sfx.py build [NAME ...]     # write mods/rtsai/standalone/audio/{sfx,ui,voices}
  python tools/standalone-sfx.py compare [NAME ...]   # measured numbers of the new files vs the reference
  python tools/standalone-sfx.py verify               # rebuild in memory, compare with the shipped files

Needs numpy only. The code is the project's own (GPL-3.0); its output carries no third-party rights.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.util
import io
import json
import struct
import sys
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from standalone_dsp import *  # noqa: E402,F401,F403
import standalone_dsp as D  # noqa: E402

AUDIO = ROOT / "mods" / "rtsai" / "standalone" / "audio"
PROV = AUDIO / "PROVENANCE.json"
REF = json.loads((ROOT / "tools" / "standalone-audio" / "reference-metrics.json").read_text())["sounds"]
GENERATOR = "tools/standalone-sfx.py"
VERSION = "rtsai-standalone-sfx-1"
MAX_BOOST = 12.0   # dB of look-ahead limiting allowed to reach the reference loudness

RECIPES: dict[str, tuple] = {}   # name -> (folder, role, fn, reference name or explicit metrics)


def recipe(name, folder, role, ref=None):
    def deco(fn):
        RECIPES[name] = (folder, role, fn, ref or name)
        return fn
    return deco


def ref_of(name):
    r = RECIPES[name][3]
    return r if isinstance(r, dict) else REF[r]


# ================================================================================================ explosions
def building_die(R, n, variant):
    v = {
        "a": dict(t60=2.2, fc0=4200, fc1=380, debris_amt=0.55, crack=0.35, cluster=2, crackle=0.5, body_attack=0.12),
        "b": dict(t60=2.0, fc0=3000, fc1=260, sub=1.2, debris_amt=0.4, crack=0.25, cluster=2, body_attack=0.15),
        "c": dict(t60=1.9, fc0=3600, fc1=300, debris_amt=0.5, crack=0.3, cluster=1, crackle=0.3, body_attack=0.08),
        "d": dict(t60=2.6, fc0=5200, fc1=450, debris_amt=0.8, crack=0.6, metallic=0.5, crackle=0.7, cluster=1),
        "e": dict(t60=2.2, fc0=2400, fc1=200, sub=1.3, rumble=0.9, debris_amt=0.25, crack=0.15, cluster=2,
                  body_attack=0.1),
        "f": dict(t60=1.8, fc0=2800, fc1=260, sub=1.2, debris_amt=0.35, crack=0.2, cluster=2, body_attack=0.12),
    }[variant]
    x = explosion(R, n, size=1.2, rumble_t60=4.0, **v)
    if variant == "c":   # secondary blast from inside the building
        x = x + 0.7 * explosion(R.sub("2nd"), n, delay=0.34, size=0.8, t60=1.2, fc0=3000, fc1=260, debris_amt=0.2)
    if variant in ("a", "d"):   # structure giving way: groaning metal and a late collapse rumble
        groan = metal(R.sub("groan"), n, R.u(180, 260), t60=1.6, delay=0.25, strike=0.0) * (1 + 0.5 * smooth_noise(R, n, 5))
        x = x + 0.3 * norm(groan)
        x = x + 0.55 * norm(lp(brown(R.sub("col"), n), 260)) * env(n, 0.25, 2.0, 0.45)
    return compress(reverb(norm(x), R.sub("rev"), t60=1.8, wet=0.25, damp=2800), -20, 3.0)


for _v in "abcdef":
    recipe(f"bgendie{_v}.wav", "sfx", "building destroyed: large explosion and collapse")(
        lambda R, n, _v=_v: building_die(R, n, _v))


def power_die(R, n, variant):
    x = explosion(R, n, size=1.1, t60=2.0, fc0=4200, fc1=380, debris_amt=0.45, crack=0.35, cluster=2,
                  body_attack=0.1, crackle=0.5, rumble_t60=3.5)
    hum_f = sweep(n, 100.0 if variant == "a" else 120.0, 18.0, kind="lin")
    hum = additive(hum_f, (1, 2, 3, 5, 7, 9), tilt=0.7) * env_pts(n, [(0, -10), (0.2, -6), (1.4, -24), (2.2, -60)])
    z = arcs(R.sub("arcs"), n, 0.05, 1.5 if variant == "a" else 1.2, rate=30)
    x = norm(x) + 0.35 * norm(hum) + 0.55 * norm(z)
    return compress(reverb(norm(x), R.sub("rev"), t60=1.6, wet=0.22), -20, 3.0)


recipe("bpowdiea.wav", "sfx", "power plant destroyed: explosion, arcing and a dying transformer hum")(
    lambda R, n: power_die(R, n, "a"))
recipe("bpowdieb.wav", "sfx", "power plant destroyed: explosion, arcing and a dying transformer hum")(
    lambda R, n: power_die(R, n, "b"))


def damage(R, n, variant):
    short = variant in ("c", "d")
    x = explosion(R, n, size=0.8, t60=1.0 if short else 1.8, fc0=2600, fc1=240, debris_amt=0.5, crack=0.3,
                  sub=0.9, rumble=0.5, metallic=0.5, cluster=1, body_attack=0.05, crackle=0.25,
                  rumble_t60=1.6 if short else 3.0)
    if variant in ("a", "e", "b"):
        x = norm(x) + 0.3 * norm(metal(R.sub("m"), n, R.u(150, 320), t60=1.2, delay=0.12, strike=0.2))
    if variant == "b":
        x = x + 0.6 * explosion(R.sub("2"), n, delay=0.28, size=0.6, t60=0.9, debris_amt=0.3)
    return compress(reverb(norm(x), R.sub("rev"), t60=1.3, wet=0.22, damp=2500), -20, 2.5)


for _v in "abcde":
    recipe(f"gdamag1{_v}.wav", "sfx", "building heavily damaged: smaller blast, metal stress and debris")(
        lambda R, n, _v=_v: damage(R, n, _v))


@recipe("gexp10a.wav", "sfx", "air-defence hit: two quick airbursts high up")
def _flak(R, n):
    x = explosion(R, n, size=0.5, crack=0.8, body=0.8, sub=0.6, rumble=0.3, debris_amt=0, t60=0.7, fc0=4000, fc1=400)
    x = 0.6 * x + explosion(R.sub("2"), n, delay=0.17, size=0.7, crack=0.6, sub=0.8, rumble=0.4, debris_amt=0.15,
                            t60=1.0, fc0=3500, fc1=300, body_attack=0.02)
    return reverb(norm(x), R.sub("rev"), t60=1.2, wet=0.3, damp=3500)


@recipe("gexp14a.wav", "sfx", "general shell and rocket impact: medium explosion")
def _gexp14a(R, n):
    x = explosion(R, n, size=0.8, t60=1.3, fc0=2200, fc1=180, sub=1.1, crack=0.2, debris_amt=0.25, rumble=0.5,
                  cluster=2, body_attack=0.08, rumble_t60=2.0)
    return compress(reverb(x, R.sub("rev"), t60=1.0, wet=0.18, damp=2200), -20, 2.5)


@recipe("gexpapoa.wav", "sfx", "heavy bomb impact: deep double blast")
def _gexpapoa(R, n):
    x = 0.5 * explosion(R, n, size=0.6, t60=0.6, fc0=2200, fc1=200, debris_amt=0.1, crack=0.2)
    x = x + explosion(R.sub("2"), n, delay=0.3, size=1.3, t60=1.2, fc0=1800, fc1=110, sub=1.4, rumble=0.9,
                      crack=0.2, debris_amt=0.2, sub_f=(70, 28), body_attack=0.03, rumble_t60=2.0)
    return compress(reverb(norm(x), R.sub("rev"), t60=1.2, wet=0.18, damp=1800), -20, 2.5)


@recipe("gexpifva.wav", "sfx", "light bomb impact: deep medium explosion")
def _gexpifva(R, n):
    x = explosion(R, n, size=0.9, t60=1.3, fc0=1800, fc1=140, sub=1.3, rumble=0.7, crack=0.15, debris_amt=0.15,
                  body_attack=0.03, cluster=1, rumble_t60=2.2)
    return compress(reverb(x, R.sub("rev"), t60=1.0, wet=0.16, damp=1800), -20, 2.5)


def splash(R, n, delay=0.0, size=1.0, t60=0.9):
    t = np.clip(tt(n) - delay, 0, None)
    w = R.noise(n) * (1 + 0.8 * np.abs(smooth_noise(R, n, 45)))
    sp = svf(w, 2200 + 1800 * np.exp(-t / 0.3), 0.6, "bp") * env(n, 0.025 * size, t60, delay, shape=0.6)
    b = bubbles(R.sub("b"), n, int(70 * size), delay + 0.05, delay + t60 * 0.9, amp=1.0)
    drops = debris(R.sub("d"), n, delay + 0.25, delay + t60 * 1.2, 30, 6, fc=(2500, 7000), amp=1.0, metallic=0)
    return norm(sp) + 0.35 * norm(b) + 0.25 * norm(drops)


@recipe("gexpwala.wav", "sfx", "large water impact: underwater blast and a tall splash")
def _gexpwala(R, n):
    x = 0.7 * explosion(R, n, size=0.9, t60=1.0, fc0=1600, fc1=120, sub=1.0, crack=0.2, debris_amt=0, rumble=0.6)
    x = x + splash(R.sub("s"), n, delay=0.04, size=1.4, t60=1.5)
    return reverb(norm(x), R.sub("rev"), t60=1.0, wet=0.15)


@recipe("gexpwasa.wav", "sfx", "small water impact: splash")
def _gexpwasa(R, n):
    th = lp(R.noise(n), 300) * env(n, 0.005, 0.25)
    return reverb(splash(R, n, size=0.8, t60=0.9) + 0.25 * norm(th), R.sub("rev"), t60=0.8, wet=0.12)


@recipe("gexpwasb.wav", "sfx", "torpedo or depth hit: muffled thump and splash")
def _gexpwasb(R, n):
    th = lp(explosion(R, n, size=0.7, t60=0.5, fc0=900, fc1=100, crack=0, debris_amt=0), 500)
    return reverb(0.35 * norm(th) + splash(R.sub("s"), n, delay=0.03, size=1.0, t60=1.0), R.sub("rev"), t60=0.9, wet=0.12)


@recipe("expnew09.wav", "sfx", "large vehicle or missile explosion",
        ref={"seconds": 1.4, "active_rms_dbfs": -14.0, "max50_rms_dbfs": -7.5})
def _expnew09(R, n):
    x = explosion(R, n, size=1.1, t60=1.5, fc0=3600, fc1=220, sub=1.2, crack=0.35, debris_amt=0.45, rumble=0.6,
                  cluster=2, body_attack=0.06, crackle=0.3, rumble_t60=2.5)
    return reverb(x, R.sub("rev"), t60=1.2, wet=0.2)


@recipe("expnew13.wav", "sfx", "medium explosion with burning debris",
        ref={"seconds": 1.25, "active_rms_dbfs": -15.0, "max50_rms_dbfs": -7.8})
def _expnew13(R, n):
    x = explosion(R, n, size=0.9, t60=1.2, fc0=3200, fc1=220, sub=1.0, crack=0.3, debris_amt=0.4, cluster=1,
                  body_attack=0.04, crackle=0.6, rumble_t60=2.0)
    return reverb(x, R.sub("rev"), t60=1.0, wet=0.18)


# ================================================================================================ guns and cannons
RIFLE = dict(body_fc=2300, body_q=0.9, crack=1.0, thump_f=(170, 80), thump=0.25, t60=0.05, mech=0.12, bright=3500)


def rifle_burst(R, n, shots, interval=0.1, echo=0.18, tail=0.4):
    x = burst_fire(R, n, shots, interval, start=0.0, **RIFLE)
    x = slap(x, R.sub("slap"), delays=(0.07, 0.15), gain=echo, fc=2500)
    return reverb(x, R.sub("rev"), t60=tail, wet=0.12, damp=4500)


recipe("iconatta.wav", "sfx", "rifle: three-round burst")(lambda R, n: rifle_burst(R, n, 3, 0.1))
recipe("iconattb.wav", "sfx", "rifle: double tap")(lambda R, n: rifle_burst(R, n, 2, 0.13))
recipe("iconattc.wav", "sfx", "rifle: five-round burst with echo")(lambda R, n: rifle_burst(R, n, 5, 0.1, 0.3, 0.6))
recipe("iconattd.wav", "sfx", "rifle: single shot")(lambda R, n: rifle_burst(R, n, 1, echo=0.25))
recipe("iconatte.wav", "sfx", "rifle: two quick shots")(lambda R, n: rifle_burst(R, n, 2, 0.11, 0.25))

MG = dict(body_fc=2000, body_q=0.8, crack=1.0, thump_f=(160, 70), thump=0.4, t60=0.06, mech=0.1, bright=3200)


def mg_burst(R, n, shots, interval=0.075):
    x = burst_fire(R, n, shots, interval, **MG)
    x = slap(x, R.sub("slap"), delays=(0.08, 0.16), gain=0.22, fc=2200)
    return reverb(x, R.sub("rev"), t60=0.5, wet=0.14, damp=4000)


recipe("igiat1a.wav", "sfx", "machine gun: five-round burst")(lambda R, n: mg_burst(R, n, 5))
recipe("igiat1b.wav", "sfx", "machine gun: six-round burst")(lambda R, n: mg_burst(R, n, 6, 0.072))
recipe("igiat1c.wav", "sfx", "machine gun: three-round burst")(lambda R, n: mg_burst(R, n, 3, 0.08))

CANNON = dict(body_fc=520, body_q=0.7, crack=1.0, thump_f=(110, 38), thump=1.0, t60=0.22, mech=0.0, bright=2400,
              length=0.9, drive=2.8)


def cannon(R, n, size=1.0, tail=0.9, clank=0.25, tight=False, echo=None):
    kw = dict(CANNON)
    kw["t60"] = 0.1 if tight else 0.25 * size
    kw["body_fc"] = 560 / size ** 0.5
    x = gunshot(R, **kw)
    buf = np.zeros(n)
    place(buf, x, 0)
    if clank > 0:   # breech and recoil
        buf += clank * norm(metal(R.sub("breech"), n, R.u(700, 1100), t60=0.2, delay=R.u(0.1, 0.18), strike=0.3))
    if not tight:
        buf = slap(buf, R.sub("slap"), delays=(0.11, 0.24, 0.4), gain=echo if echo is not None else 0.3, fc=900)
        return reverb(buf, R.sub("rev"), t60=tail, wet=0.22, damp=2000)
    return reverb(buf, R.sub("rev"), t60=0.3, wet=0.06, damp=2000)


recipe("vgriatta.wav", "sfx", "main battle tank gun")(lambda R, n: cannon(R, n, 1.0))
recipe("vgriattb.wav", "sfx", "main battle tank gun")(lambda R, n: cannon(R, n, 1.1))
recipe("vgriattc.wav", "sfx", "main battle tank gun")(lambda R, n: cannon(R, n, 0.9, clank=0.35))
recipe("vrhiatta.wav", "sfx", "light cannon: tight report")(lambda R, n: cannon(R, n, 0.8, clank=0.1, tight=True))
recipe("vrhiattb.wav", "sfx", "light cannon: tight report")(lambda R, n: cannon(R, n, 0.7, clank=0.12, tight=True))
recipe("vrhiattc.wav", "sfx", "light cannon: report with echo")(lambda R, n: cannon(R, n, 0.85, 0.7, 0.15, echo=0.2))
recipe("vrhiattd.wav", "sfx", "light cannon: tight report")(lambda R, n: cannon(R, n, 0.75, clank=0.15, tight=True))
recipe("vdesatta.wav", "sfx", "heavy gun and howitzer: deep boom")(lambda R, n: cannon(R, n, 1.5, 1.6, 0.2, echo=0.45))
recipe("vdesattb.wav", "sfx", "heavy gun and howitzer: deep boom")(lambda R, n: cannon(R, n, 1.4, 1.5, 0.25, echo=0.45))

AUTO = dict(body_fc=1100, body_q=0.8, crack=1.0, thump_f=(120, 50), thump=0.8, t60=0.07, mech=0.15, bright=2800,
            length=0.35, drive=2.6)


def autocannon(R, n, shots, interval, low=1.0, echo=0.2, bright=1.0):
    kw = dict(AUTO)
    kw["body_fc"] = 1100 * bright / low
    kw["thump_f"] = (120 / low, 50 / low)
    x = burst_fire(R, n, shots, interval, **kw)
    x = slap(x, R.sub("slap"), delays=(0.09, 0.19), gain=echo, fc=1500)
    return reverb(x, R.sub("rev"), t60=0.45, wet=0.12, damp=3000)


recipe("vflaat1a.wav", "sfx", "tracked autocannon: two heavy rounds")(lambda R, n: autocannon(R, n, 2, 0.16, 1.3))
recipe("vflaat1b.wav", "sfx", "tracked autocannon: two heavy rounds")(lambda R, n: autocannon(R, n, 2, 0.14, 1.3))
recipe("vflaat2a.wav", "sfx", "twin anti-aircraft cannon: burst")(lambda R, n: autocannon(R, n, 4, 0.1, 1.8, 0.12, 0.7))
recipe("vflaat2b.wav", "sfx", "twin anti-aircraft cannon: burst")(lambda R, n: autocannon(R, n, 3, 0.11, 2.0, 0.12, 0.6))
recipe("vflaat2c.wav", "sfx", "twin anti-aircraft cannon: burst")(lambda R, n: autocannon(R, n, 4, 0.095, 1.8, 0.12, 0.7))
recipe("vflaat2d.wav", "sfx", "twin anti-aircraft cannon: burst")(lambda R, n: autocannon(R, n, 3, 0.1, 2.0, 0.12, 0.6))
recipe("vwaratta.wav", "sfx", "20 mm cannon: burst")(lambda R, n: autocannon(R, n, 3, 0.085, 1.0, 0.2, 2.0))
recipe("vwarattb.wav", "sfx", "20 mm cannon: burst")(lambda R, n: autocannon(R, n, 4, 0.09, 1.0, 0.25, 2.0))


def rotary(R, n, spin_up):
    """Rotary cannon: rounds accelerating to a buzz, then an abrupt stop."""
    out = np.zeros(n)
    t, i = 0.0, 0
    stop = n / D.SR - 0.07
    while t < stop:
        rate = 14 + 46 * min(1.0, t / spin_up)
        g = min(1.0, 0.35 + t / spin_up)
        place(out, g * gunshot(R.sub(f"r{i}"), body_fc=1800, crack=0.7, thump_f=(130, 70), thump=0.4, t60=0.025,
                                mech=0, bright=3200, length=0.06, drive=2.0), t)
        t += 1 / rate
        i += 1
    whirr = motor(R.sub("m"), n, 60, 160, harmonics=6) * env_pts(n, [(0, -40), (spin_up, -14), (stop, -14), (stop + 0.03, -70)])
    x = norm(out) + 0.15 * norm(whirr)
    return x + 0.05 * convolve(x, reverb_ir(R.sub("rev"), 0.25, 3000, 0.005))


recipe("vblhatta.wav", "sfx", "helicopter rotary cannon: spin-up burst")(lambda R, n: rotary(R, n, 0.4))
recipe("vblhattb.wav", "sfx", "helicopter rotary cannon: spin-up burst")(lambda R, n: rotary(R, n, 0.22))


@recipe("irocatta.wav", "sfx", "infantry-carrier cannon and launcher: heavy round with a short whoosh")
def _irocatta(R, n):
    x = gunshot(R, body_fc=1400, body_q=0.8, crack=1.0, thump_f=(120, 55), thump=0.8, t60=0.12, mech=0.15,
                bright=3000, length=0.5, drive=2.6)
    buf = np.zeros(n)
    place(buf, x, 0)
    w = whoosh(R.sub("w"), n, 3500, 1200, q=1.2, attack=0.02, t60=0.6, delay=0.02)
    buf = norm(buf) + 0.4 * norm(w)
    return reverb(slap(buf, R.sub("s"), delays=(0.1, 0.2), gain=0.25, fc=1800), R.sub("rev"), t60=0.7, wet=0.15)


# ================================================================================================ missiles, aircraft, naval
def launch(R, n, delay=0.0, f0=900, f1=2400, t60=1.2, ignite=0.8, low=0.6):
    x = rocket(R, n, delay=delay, ignite=ignite, roar=1.0, f0=f0, f1=f1, t60=t60)
    roar = lp(R.noise(n) * (1 + 0.5 * smooth_noise(R, n, 30)), 450) * env(n, 0.03, t60 * 0.9, delay + 0.01, shape=0.6)
    return reverb(norm(x) + low * norm(roar), R.sub("rev"), t60=1.0, wet=0.2)


recipe("vintatta.wav", "sfx", "missile launch: ignition and hiss")(lambda R, n: launch(R, n, f0=1100, f1=2600, t60=1.6, low=0.4))
recipe("vapoat2a.wav", "sfx", "anti-aircraft missile launch")(lambda R, n: launch(R, n, delay=0.05, f0=900, f1=2200, t60=1.0, low=0.8))
recipe("vapoat2c.wav", "sfx", "anti-aircraft missile launch")(lambda R, n: launch(R, n, f0=850, f1=2000, t60=1.2, low=0.8))
recipe("vapoar2b.wav", "sfx", "anti-aircraft missile launch (the second of three variants)",
       ref={"seconds": 1.08, "active_rms_dbfs": -16.0, "max50_rms_dbfs": -9.0})(
    lambda R, n: launch(R, n, delay=0.02, f0=950, f1=2300, t60=1.1, low=0.8))


def turbine(R, n, up):
    """Small VTOL drone: turbine whine and rotor buzz rising (take-off) or falling (landing), with air rush."""
    L = n / D.SR
    f0, f1 = (110, 230) if up else (230, 100)
    base = motor(R, n, f0, f1, harmonics=16, tilt=0.8, buzz=0.6)
    whine_f = sweep(n, f0 * 14, f1 * 14, kind="log")
    wh = np.sin(phase(whine_f)) + 0.5 * np.sin(phase(whine_f * 1.5))
    wind = bp(R.noise(n), sweep(n, 800 if up else 1700, 1700 if up else 800, kind="log"), 0.7)
    pts = [(0, -30), (0.45, -4), (L * 0.75, 0), (L, -40)] if up else [(0, -20), (0.45, 0), (L * 0.7, -8), (L, -45)]
    return (0.5 * norm(base) + 0.35 * norm(wh) + 0.8 * norm(wind)) * env_pts(n, pts)


recipe("vhortaka.wav", "sfx", "drone take-off")(lambda R, n: turbine(R, n, True))
recipe("vhortakb.wav", "sfx", "drone take-off")(lambda R, n: turbine(R, n, True))
recipe("vhorlana.wav", "sfx", "drone landing")(lambda R, n: turbine(R, n, False))
recipe("vhorlanb.wav", "sfx", "drone landing")(lambda R, n: turbine(R, n, False))


@recipe("vospatta.wav", "sfx", "bomb release: latch clunk and a low thud")
def _vospatta(R, n):
    c1 = metal(R, n, R.u(500, 700), t60=0.15, strike=0.8)
    th = np.sin(phase(sweep(n, 90, 45, 0.05))) * env(n, 0.002, 0.6, 0.03)
    c2 = metal(R.sub("2"), n, R.u(300, 420), t60=0.3, delay=0.07, strike=0.6)
    return 0.4 * norm(c1) + norm(th) + 0.35 * norm(c2)


@recipe("vsubatta.wav", "sfx", "torpedo launch: compressed-air thunk, bubbles and a fading motor")
def _vsubatta(R, n):
    thunk = lp(explosion(R, n, size=0.4, t60=0.4, fc0=1500, fc1=150, crack=0.2, debris_amt=0), 900)
    hiss = lp(R.noise(n), 2400) * env(n, 0.03, 1.4, 0.03)
    b = bubbles(R.sub("b"), n, 160, 0.04, 1.6, f_lo=250, f_hi=1400, amp=1.0)
    mot = np.sin(phase(sweep(n, 420, 380, kind="lin"))) * env_pts(n, [(0, -60), (0.3, -12), (1.4, -18), (2.2, -60)])
    x = norm(thunk) + 0.6 * norm(hiss) + 0.5 * norm(b) + 0.2 * mot
    return reverb(norm(x), R.sub("rev"), t60=1.2, wet=0.2, damp=1500)


@recipe("vnavupa.wav", "sfx", "submarine diving or surfacing: venting air, bubbles, hull groan")
def _vnavupa(R, n):
    vent = bp(R.noise(n), sweep(n, 1500, 600, kind="log"), 0.7) * env_pts(n, [(0, -60), (0.09, -20), (0.45, 0), (1.1, -10), (1.48, -50)])
    b = bubbles(R.sub("b"), n, 160, 0.1, 1.35, f_lo=250, f_hi=1100, amp=1.0)
    groan = metal(R.sub("g"), n, 95, t60=1.4, delay=0.3, strike=0) * (1 + 0.4 * smooth_noise(R, n, 4))
    return norm(vent) + 0.5 * norm(b) + 0.35 * norm(groan)


# ================================================================================================ base, construction, misc
@recipe("uplace.wav", "sfx", "structure placed: heavy thud, metal ring and settling debris")
def _uplace(R, n):
    th = np.sin(phase(sweep(n, 95, 48, 0.05))) * env(n, 0.002, 0.6)
    dust = lp(R.noise(n), 1800) * env(n, 0.004, 1.0)
    ring = metal(R.sub("r"), n, R.u(330, 420), t60=1.6, strike=0.5)
    rattle = debris(R.sub("d"), n, 0.06, 1.1, 40, 6, amp=1.0, metallic=0.6)
    x = norm(th) + 0.5 * norm(dust) + 0.6 * norm(ring) + 0.4 * norm(rattle)
    return reverb(sat(norm(x), 1.6), R.sub("rev"), t60=1.0, wet=0.18)


@recipe("uselbuil.wav", "sfx", "structure sold or packed up: servo whine, ratchet and a closing clank")
def _uselbuil(R, n):
    L = n / D.SR
    servo = motor(R, n, 520, 300, harmonics=14, tilt=0.9, buzz=0.5) * env_pts(n, [(0, -40), (0.1, -6), (L - 0.5, -8), (L - 0.3, -40)])
    ratchet = np.zeros(n)
    t, i = 0.1, 0
    while t < L - 0.5:
        place(ratchet, metal(R.sub(f"k{i}"), n_of(0.05), R.u(2600, 3400), t60=0.03, strike=0.6), t)
        t += 0.055
        i += 1
    clank = metal(R.sub("c"), n, R.u(250, 320), t60=0.8, delay=L - 0.45, strike=0.8)
    thud = np.sin(phase(sweep(n, 80, 45, 0.04))) * env(n, 0.002, 0.3, L - 0.45)
    unlock = metal(R.sub("u"), n, R.u(380, 460), t60=0.5, strike=0.9) + np.sin(phase(sweep(n, 90, 50, 0.04))) * env(n, 0.002, 0.35)
    low = additive(sweep(n, 70, 50, kind="lin"), (1, 2, 3), tilt=1.0) * env_pts(n, [(0, -30), (0.1, -4), (L - 0.5, -6), (L - 0.3, -40)])
    x = norm(servo) + 0.6 * norm(ratchet) + 0.45 * norm(clank) + 0.4 * thud + norm(unlock) + 0.8 * norm(low)
    return reverb(norm(x), R.sub("rev"), t60=0.8, wet=0.12)


@recipe("igensqua.wav", "sfx", "infantry run over: crunch and a wet squelch")
def _igensqua(R, n):
    crunch = debris(R, n, 0.0, 0.12, 300, 100, fc=(1800, 5000), amp=1.0, metallic=0)
    sq = bp(R.noise(n) * (1 + 1.5 * np.abs(smooth_noise(R, n, 60))), sweep(n, 1800, 600, kind="log"), 1.5) * env(n, 0.01, 0.35)
    gl = bubbles(R.sub("b"), n, 18, 0.03, 0.3, f_lo=300, f_hi=900, amp=1.0, dur=(0.01, 0.03))
    th = lp(R.noise(n), 250) * env(n, 0.003, 0.12)
    return norm(crunch) + 0.7 * norm(sq) + 0.3 * norm(gl) + 0.4 * norm(th)


# ================================================================================================ time, force field, superweapons
def teleport(R, n, big=False):
    L = n / D.SR
    whomp = np.sin(phase(sweep(n, 160, 45, 0.25))) * env(n, 0.06, L * 0.7, 0.02)
    rise = scifi(R, n, 180, 2400, voices=5, spread=0.02, fm=0.3, kind="log") * env_pts(n, [(0, -50), (0.08, -10), (0.25, 0), (L * 0.6, -12), (L, -60)])
    fall = scifi(R.sub("f"), n, 1800, 120, voices=3, fm=0.6, kind="log") * env_pts(n, [(0, -40), (0.2, -6), (L * 0.5, -12), (L, -60)])
    sweep_n = whoosh(R.sub("w"), n, 300, 5000, q=2.0, attack=0.2, t60=L * 0.8, kind="log")
    pop = explosion(R.sub("p"), n, delay=0.18, size=0.5, crack=0.6, body=0.7, sub=1.0, rumble=0.4, debris_amt=0,
                    t60=L * 0.6, fc0=2000, fc1=150)
    x = 0.8 * norm(whomp) + 0.45 * norm(rise) + 0.4 * norm(fall) + 0.35 * norm(sweep_n) + 0.7 * pop
    if big:
        x = x + 0.35 * norm(arcs(R.sub("a"), n, 0.15, L * 0.6, rate=20))
    return reverb(norm(x), R.sub("rev"), t60=1.6, wet=0.3, damp=5000)


recipe("schrmov.wav", "sfx", "unit shifted through space: low whomp, chorus sweep and arrival pop")(lambda R, n: teleport(R, n, True))
recipe("vchrtele.wav", "sfx", "ore carrier teleports home: short whomp and shimmer")(lambda R, n: teleport(R, n))
recipe("chrono2.aud", "sfx", "shift device effect (Westwood AUD, the name the rules use)",
       ref={"seconds": 2.0, "active_rms_dbfs": -13.0, "max50_rms_dbfs": -6.5})(lambda R, n: teleport(R, n, True))


@recipe("schropen.wav", "sfx", "space-shift device powering up: deep hum swelling into a charged shimmer")
def _schropen(R, n):
    L = n / D.SR
    hum = additive(sweep(n, 45, 80, kind="log"), (1, 2, 3, 4, 6, 8, 11), tilt=0.7) * env_pts(n, [(0, -30), (0.4, 0), (L * 0.8, -3), (L, -60)])
    shimmer = scifi(R, n, 400, 2400, voices=6, spread=0.015, fm=0.3, kind="log") * env_pts(n, [(0, -40), (0.4, -6), (L * 0.5, 0), (L, -60)])
    z = arcs(R.sub("a"), n, 0.3, L * 0.8, rate=18)
    x = norm(hum) + 0.6 * norm(shimmer) + 0.45 * norm(z)
    return reverb(norm(x), R.sub("rev"), t60=2.0, wet=0.3)


@recipe("siroon.wav", "sfx", "protective field switched on: electric surge and metallic shimmer")
def _siroon(R, n):
    L = n / D.SR
    surge = additive(sweep(n, 55, 110, kind="log"), (1, 2, 3, 5, 8, 12), tilt=0.6) * env_pts(n, [(0, -40), (0.06, -10), (0.4, 0), (L, -40)])
    sh = metal(R, n, 900, t60=1.5, delay=0.05, strike=0.3, partials=(1, 1.51, 2.27, 3.41, 5.1)) * (1 + 0.5 * np.sin(2 * np.pi * 9 * tt(n)))
    z = arcs(R.sub("a"), n, 0.05, 0.9, rate=30)
    return reverb(norm(surge) + 0.6 * norm(sh) + 0.5 * norm(z), R.sub("rev"), t60=1.4, wet=0.25)


@recipe("siroread.wav", "sfx", "protective field ready: low swelling drone")
def _siroread(R, n):
    L = n / D.SR
    d = additive(sweep(n, 48, 55, kind="lin"), (1, 2, 3, 4, 5, 6), tilt=1.0) * (1 + 0.15 * np.sin(2 * np.pi * 3 * tt(n)))
    return reverb(d * env_pts(n, [(0, -50), (0.75, 0), (L * 0.75, -4), (L, -60)]), R.sub("rev"), t60=1.0, wet=0.15)


@recipe("snukexpl.wav", "sfx", "strategic missile detonation: enormous blast and a long rolling roar")
def _snukexpl(R, n):
    L = n / D.SR
    x = explosion(R, n, size=2.5, t60=5.5, fc0=3500, fc1=160, sweep_t=1.5, sub=1.6, rumble=1.4, debris_amt=0.35,
                  crack=0.5, sub_f=(60, 22), drive=2.8, turbulence=0.6, debris_end=L * 0.7, cluster=3,
                  body_attack=0.15, crackle=0.6, rumble_t60=8.0)
    roar = lp(R.noise(n) * (1 + 0.6 * smooth_noise(R, n, 6)), sweep(n, 1600, 220, kind="log")) * env(n, 0.3, 7.0)
    return compress(reverb(norm(x) + 0.6 * norm(roar), R.sub("rev"), t60=3.0, wet=0.25, damp=1800), -22, 4.0, release=0.4)


@recipe("snukintr.wav", "sfx", "strategic missile incoming: rising roar and a falling shriek")
def _snukintr(R, n):
    L = n / D.SR
    f = sweep(n, 2200, 700, kind="log")
    shriek = (np.sin(phase(f)) * 0.4 + norm(bp(R.noise(n), f, 4.0))) * env_pts(n, [(0, -40), (1.3, -4), (L - 0.05, -2), (L, -60)])
    roar = lp(R.noise(n) * (1 + 0.4 * smooth_noise(R, n, 12)), 220) * env_pts(n, [(0, -50), (1.36, 0), (L, -10)])
    sub = np.sin(phase(sweep(n, 40, 60, kind="lin"))) * env_pts(n, [(0, -60), (1.36, -3), (L, -8)])
    return 0.45 * norm(shriek) + norm(roar) + 0.5 * sub


@recipe("snuklaun.wav", "sfx", "strategic missile launch: ignition and a deep rocket roar")
def _snuklaun(R, n):
    L = n / D.SR
    ign = explosion(R, n, size=1.4, t60=1.0, fc0=1800, fc1=100, sub=1.4, crack=0.2, debris_amt=0.1, body_attack=0.08)
    roar = lp(R.noise(n) * (1 + 0.5 * smooth_noise(R, n, 25)), sweep(n, 500, 180, kind="log"))
    roar *= env_pts(n, [(0, -60), (0.3, -8), (0.7, 0), (L * 0.7, -4), (L, -40)])
    rumble = lp(brown(R.sub("b"), n), 90) * env(n, 0.5, 4.0)
    return reverb(0.6 * norm(ign) + norm(roar) + 0.6 * norm(rumble), R.sub("rev"), t60=2.0, wet=0.2, damp=1200)


@recipe("snukread.wav", "sfx", "missile silo ready: hydraulic doors and a two-tone warning")
def _snukread(R, n):
    L = n / D.SR
    hyd = lp(R.noise(n), 1500) * env_pts(n, [(0, -50), (0.3, -10), (1.1, 0), (3.6, -6), (4.0, -40), (L, -60)])
    door = motor(R, n, 90, 60, harmonics=12, buzz=0.4) * env_pts(n, [(0, -60), (0.4, -8), (3.6, -8), (3.9, -60), (L, -70)])
    clank = metal(R.sub("c"), n, 210, t60=0.8, delay=3.7, strike=0.8) * 0.4
    tone = np.zeros(n)
    for i in range(6):
        f = 520 if i % 2 == 0 else 390
        k = n_of(0.32)
        b = additive(np.full(k, f), (1, 2, 3, 4), tilt=1.0) * env_pts(k, [(0, -40), (0.02, 0), (0.28, -2), (0.32, -60)])
        place(tone, b, 1.0 + i * 0.4)
    x = norm(hyd) * 0.6 + 0.6 * norm(door) + 0.7 * norm(clank) + 0.55 * norm(tone)
    return reverb(norm(x), R.sub("rev"), t60=1.4, wet=0.2)


@recipe("sweaintr.wav", "sfx", "storm brewing: rising wind and distant thunder")
def _sweaintr(R, n):
    L = n / D.SR
    wind = bp(pink(R, n), np.clip(380 + 250 * smooth_noise(R.sub("w"), n, 0.6) + 200 * tt(n) / L, 120, 2000), 0.9)
    wind *= (1 + 0.5 * smooth_noise(R.sub("g"), n, 1.5)) * env_pts(n, [(0, -50), (0.6, -6), (L * 0.6, 0), (L, -40)])
    th = thunder(R.sub("t"), n, crack_amt=0.15, roll_amt=1.0, delay=0.6, t60=3.0, rolls=7)
    return reverb(0.8 * norm(wind) + norm(lp(th, 300)), R.sub("rev"), t60=2.5, wet=0.2, damp=1500)


def strike(R, n, crack, roll, sizzle=0.0):
    L = n / D.SR
    t = tt(n)
    bright = sizzle > 0
    boom = explosion(R.sub("b"), n, size=1.0, crack=crack, body=0.8, sub=0.3 if bright else 1.0,
                     rumble=0.3 if bright else 0.8, debris_amt=0, t60=1.6, fc0=6000 if bright else 1600,
                     fc1=700 if bright else 140, rumble_t60=3.0)
    rolls = thunder(R, n, crack_amt=0.0, roll_amt=1.0, delay=0.05, t60=1.8, rolls=6) * env_pts(n, [(0, 0), (L, -6)])
    x = norm(boom) + roll * norm(lp(rolls, 600))
    if sizzle > 0:
        s = hp(R.noise(n) * (1 + 3 * np.abs(smooth_noise(R.sub("z"), n, 300))), 2500) * np.exp(-t / 0.5)
        x = x + sizzle * norm(s)
    return compress(reverb(norm(x), R.sub("rev"), t60=2.0, wet=0.25, damp=2500), -20, 3.0)


recipe("sweastra.wav", "sfx", "lightning strike: rolling thunder")(lambda R, n: strike(R, n, 0.4, 0.8))
recipe("sweastrb.wav", "sfx", "lightning strike: sharp crack")(lambda R, n: strike(R, n, 1.0, 0.25, 0.9))
recipe("sweastrc.wav", "sfx", "lightning strike: crack and roll")(lambda R, n: strike(R, n, 1.0, 0.5, 0.6))
recipe("sweastrd.wav", "sfx", "lightning strike: rolling thunder")(lambda R, n: strike(R, n, 0.3, 1.0))


# ================================================================================================ dog (non-verbal voice set)
DOG = dict(formants=(1000, 2100, 3300))


@recipe("idogatca.wav", "sfx", "dog attack: growl rising into a bark and a bite")
def _idogatca(R, n):
    g = growl(R, n, 120, 0.0, 0.42, formants=(700, 1500, 2800))
    b = bark(R.sub("b"), n, 640, length=0.16, delay=0.38, growl=0.4, **DOG)
    snap = burst(R.sub("s"), n, 3000, 1.0, 0.03) * env(n, 0.001, 0.05, 0.56)
    return 0.6 * g + b + 0.5 * norm(snap)


@recipe("idogatta.wav", "sfx", "dog attack: two barks and a bite")
def _idogatta(R, n):
    x = bark(R, n, 680, length=0.13, **DOG) * 0.7 + bark(R.sub("2"), n, 620, length=0.18, delay=0.2, growl=0.3, **DOG)
    snap = burst(R.sub("s"), n, 3000, 1.0, 0.03) * env(n, 0.001, 0.05, 0.45)
    return x + 0.5 * norm(snap)


recipe("idogsela.wav", "voices", "dog selected: one alert bark")(lambda R, n: bark(R, n, 700, length=0.2, rough=0.6, **DOG))
recipe("idogmova.wav", "voices", "dog moving: panting and a short bark")(
    lambda R, n: 0.7 * pant(R, n, 5, 6.0, 0.05) + bark(R.sub("b"), n, 650, length=0.15, delay=0.78, **DOG))
recipe("idogfea.wav", "voices", "dog feedback: snarl and bark")(
    lambda R, n: 0.5 * growl(R, n, 110, 0.0, 0.3, formants=(800, 1700, 3000)) + bark(R.sub("b"), n, 720, length=0.17, delay=0.3, rough=0.7, **DOG))
recipe("idogfeb.wav", "voices", "dog feedback: whimper then a sharp bark")(
    lambda R, n: 0.4 * whine(R, n, 1100, 1500, 0.0, 0.4) + bark(R.sub("2"), n, 760, length=0.12, delay=0.45, rough=0.7, **DOG))
recipe("idogfec.wav", "voices", "dog feedback: whine")(lambda R, n: whine(R, n, 1000, 1500, 0.0, n / D.SR * 0.9))
recipe("idogdiea.wav", "voices", "dog dies: sharp yelp")(
    lambda R, n: bark(R, n, 1000, length=0.25, rough=0.4, formants=(1100, 2400, 3500)))


# ================================================================================================ UI
def tone(n, f, harm=(1,), tilt=1.0, attack=0.002, t60=0.3, delay=0.0):
    return additive(np.full(n, float(f)), harm, tilt=tilt) * env(n, attack, t60, delay)


def bell(R, n, f, t60=0.6, delay=0.0, ratio=1.41, index=2.0):
    t = np.clip(tt(n) - delay, 0, None)
    e = np.exp(-6.91 * t / t60)
    m = index * e * np.sin(2 * np.pi * f * ratio * t)
    y = np.sin(2 * np.pi * f * t + m) * e * np.clip(t / 0.002, 0, 1)
    y[tt(n) < delay] = 0
    return y


def click(R, n, f_body, f_noise, t60=0.035, q=1.5, tilt=1.2):
    """A UI click: a short tuned body plus a noise tick, dense enough to read at a low volume."""
    body = additive(np.full(n, float(f_body)), (1, 2, 3, 4), tilt=tilt) * env(n, 0.0005, t60)
    tick = bp(R.noise(n), f_noise, q) * env(n, 0.0003, t60 * 0.6)
    return norm(body) + 0.7 * norm(tick)


recipe("umenucl1.wav", "ui", "menu click: crisp tick")(lambda R, n: click(R, n, 2600, 4500, 0.06))
recipe("utab.wav", "ui", "tab click: bright tick")(lambda R, n: click(R, n, 3200, 5200, 0.07))
recipe("ugamclos.wav", "ui", "disabled click: dull knock")(lambda R, n: click(R, n, 520, 1100, 0.12, tilt=1.0))
recipe("ucredup.wav", "ui", "credits counting up: tiny bright tick")(lambda R, n: click(R, n, 3600, 6000, 0.15, tilt=1.5))
recipe("ucreddn.wav", "ui", "credits counting down: tiny low tick")(lambda R, n: click(R, n, 1500, 2600, 0.1, tilt=1.3))


@recipe("umessage.wav", "ui", "chat message: two-tone blip")
def _umessage(R, n):
    return tone(n, 520, (1, 2, 3), tilt=1.4, attack=0.003, t60=0.3) + tone(n, 690, (1, 2, 3), tilt=1.4, attack=0.003, t60=0.35, delay=0.08)


@recipe("gupgrad1.wav", "ui", "unit promoted: rising three-note chime")
def _gupgrad1(R, n):
    return sum(bell(R, n, f, t60=1.0, delay=d, index=1.8) for f, d in ((1046, 0.0), (1318, 0.07), (1568, 0.14)))


@recipe("ubeacon.wav", "ui", "beacon placed: sonar-like ping with echoes")
def _ubeacon(R, n):
    x = bell(R, n, 1700, t60=1.4, ratio=2.0, index=0.8) + 0.5 * bell(R, n, 2550, t60=1.0, ratio=2.0, index=0.5)
    return slap(x, R.sub("e"), delays=(0.18, 0.36, 0.54), gain=0.55, fc=6000)


@recipe("uradaron.wav", "ui", "radar online: power-up sweep, scanning tone and acknowledgement beeps")
def _uradaron(R, n):
    L = n / D.SR
    sw = scifi(R, n, 500, 2200, voices=3, fm=0.15, kind="log") * env_pts(n, [(0, -40), (0.05, 0), (0.6, -4), (1.2, -14), (L, -60)])
    scan = np.sin(phase(np.full(n, 1300.0))) * (0.5 + 0.5 * np.sin(2 * np.pi * 2.5 * tt(n))) * env_pts(n, [(0, -60), (0.4, -10), (L * 0.9, -16), (L, -60)])
    beeps = sum(tone(n, 1700, (1, 2), tilt=2, attack=0.002, t60=0.12, delay=0.9 + 0.2 * i) for i in range(3))
    stat = hp(R.noise(n), 3000) * env_pts(n, [(0, -40), (0.05, -16), (1.0, -26), (1.4, -70)])
    return norm(sw) + 0.4 * norm(scan) + 0.5 * beeps + 0.4 * stat


@recipe("uradarof.wav", "ui", "radar offline: descending power-down and fading static")
def _uradarof(R, n):
    L = n / D.SR
    sw = scifi(R, n, 1800, 200, voices=3, fm=0.2, kind="log") * env_pts(n, [(0, -30), (0.01, 0), (L * 0.75, -10), (L, -60)])
    stat = hp(R.noise(n), 2500) * env_pts(n, [(0, -6), (0.4, -14), (L, -50)])
    return norm(sw) + 0.5 * norm(stat)


@recipe("gpowon.wav", "ui", "power restored: click, rising generator hum and electric buzz")
def _gpowon(R, n):
    L = n / D.SR
    click_ = metal(R, n, 1400, t60=0.1, strike=0.8)
    hum = additive(sweep(n, 60, 240, kind="log"), range(1, 18), tilt=0.8) * env_pts(n, [(0, -50), (0.6, 0), (L * 0.7, -3), (L, -60)])
    whine = np.sin(phase(sweep(n, 600, 2600, kind="log"))) * env_pts(n, [(0, -60), (0.6, -10), (L * 0.6, -14), (L, -60)])
    buzz = bp(R.noise(n), 3000, 1.0) * (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 120 * tt(n)))) * env_pts(n, [(0, -60), (0.6, -16), (L, -60)])
    return 0.5 * norm(click_) + norm(hum) + 0.6 * whine + 0.5 * norm(buzz)


@recipe("gpowof.wav", "ui", "power lost: clunk and a generator winding down")
def _gpowof(R, n):
    L = n / D.SR
    clunk = metal(R, n, 480, t60=0.4, strike=0.8) + np.sin(phase(sweep(n, 90, 45, 0.05))) * env(n, 0.002, 0.3)
    hum = additive(sweep(n, 240, 30, kind="log"), range(1, 16), tilt=0.8) * env_pts(n, [(0, -6), (0.15, 0), (L * 0.8, -18), (L, -60)])
    zap = arcs(R.sub("a"), n, 0.0, 0.4, rate=25)
    return 0.7 * norm(clunk) + norm(hum) + 0.4 * norm(zap)


def slide(R, n, close):
    L = n / D.SR
    rail = bp(R.noise(n) * (1 + 0.5 * smooth_noise(R, n, 30)), 1800, 0.8)
    mot = motor(R.sub("m"), n, 220 if close else 180, 160 if close else 240, harmonics=12, buzz=0.4)
    shape = [(0, -40), (0.05, -6), (L * 0.5, 0), (L * 0.6, -20), (L, -60)]
    latch_at = L * 0.5
    latch = metal(R.sub("l"), n, 620 if close else 820, t60=1.0 if close else 0.4, delay=latch_at, strike=0.7)
    thud = np.sin(phase(sweep(n, 85, 45, 0.04))) * env(n, 0.002, 0.3, latch_at)
    return (norm(rail) * 0.7 + norm(mot)) * env_pts(n, shape) + 0.6 * norm(latch) + 0.5 * thud


recipe("uslide1.wav", "ui", "build palette opens: mechanical slide and latch")(lambda R, n: slide(R, n, False))
recipe("uslide2.wav", "ui", "build palette closes: slide back and a thunk")(lambda R, n: slide(R, n, True))


# ================================================================================================ render, write, provenance
def fit_and_level(x: np.ndarray, ref: dict) -> tuple[np.ndarray, dict]:
    n = n_of(ref["seconds"])
    x = np.asarray(x, dtype=float)
    if len(x) >= n:
        x = x[:n].copy()
    else:
        x = np.concatenate([x, np.zeros(n - len(x))])
    x = x - np.mean(x)
    x = hp1(x, 18.0)
    x = fade(x, 0.0, min(0.03, ref["seconds"] * 0.2))
    x = norm(x, 0.966)
    key = "max50_rms_dbfs" if "max50_rms_dbfs" in ref else "active_rms_dbfs"
    target = ref[key]
    y = level(x, key, target)
    for drive in (2.0, 3.0, 4.5, 6.5):   # still too peaky to reach the level: soft-clip harder, then level again
        if target - metrics(y)[key] <= 1.5:
            break
        y = level(sat(norm(x), drive) * 0.966, key, target)
    x = y
    m = metrics(x)
    return x, m


def level(x: np.ndarray, key: str, target: float) -> np.ndarray:
    boost = 0.0
    for _ in range(6):
        cur = metrics(x)[key]
        gain = target - cur
        if abs(gain) < 0.3:
            break
        if gain < 0:
            x = x * 10 ** (gain / 20)
            break
        step = min(gain + 0.5, 6.0, MAX_BOOST - boost)   # limiting eats a little of each step
        if step <= 0.05:
            break
        boost += step
        x = limiter(x * 10 ** (step / 20), ceiling=0.966)
    return x


def pcm16(x: np.ndarray) -> np.ndarray:
    return np.clip(np.round(x * 32767), -32768, 32767).astype("<i2")


def wav_bytes(x: np.ndarray) -> bytes:
    bio = io.BytesIO()
    with wave.open(bio, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(D.SR)
        w.writeframes(pcm16(x).tobytes())
    return bio.getvalue()


STEPS = [7, 8, 9, 10, 11, 12, 13, 14, 16, 17, 19, 21, 23, 25, 28, 31, 34, 37, 41, 45, 50, 55, 60, 66, 73, 80, 88,
         97, 107, 118, 130, 143, 157, 173, 190, 209, 230, 253, 279, 307, 337, 371, 408, 449, 494, 544, 598, 658, 724,
         796, 876, 963, 1060, 1166, 1282, 1411, 1552, 1707, 1878, 2066, 2272, 2499, 2749, 3024, 3327, 3660, 4026,
         4428, 4871, 5358, 5894, 6484, 7132, 7845, 8630, 9493, 10442, 11487, 12635, 13899, 15289, 16818, 18500,
         20350, 22385, 24623, 27086, 29794, 32767]
IDX = [-1, -1, -1, -1, 2, 4, 6, 8]


def aud_bytes(x: np.ndarray) -> bytes:
    """Westwood AUD, IMA ADPCM (format 99), 512-byte chunks, matching OpenRA's ImaAdpcmReader."""
    s = pcm16(x).astype(int).tolist()
    if len(s) % 2:
        s.append(0)
    index, cur = 0, 0
    nib = []
    for v in s:
        step = STEPS[index]
        best = None
        for code in range(16):
            b = code & 7
            d = step * b // 4 + step // 8
            c = cur - d if code & 8 else cur + d
            c = max(-32768, min(32767, c))
            e = abs(v - c)
            if best is None or e < best[0]:
                best = (e, code, c)
        _, code, cur = best
        index = max(0, min(88, index + IDX[code & 7]))
        nib.append(code)
    data = bytes((nib[i] & 15) | ((nib[i + 1] & 15) << 4) for i in range(0, len(nib), 2))
    body = b""
    for i in range(0, len(data), 512):
        c = data[i:i + 512]
        body += struct.pack("<HHI", len(c), len(c) * 4, 0xDEAF) + c
    out_size = len(s) * 2
    return struct.pack("<HiiBB", D.SR, len(body), out_size, 0x2, 99) + body


def render(name: str) -> tuple[bytes, dict]:
    folder, role, fn, _ = RECIPES[name]
    ref = ref_of(name)
    R = Rand(VERSION, name)
    raw = fn(R, n_of(ref["seconds"]))
    x, m = fit_and_level(raw, ref)
    data = aud_bytes(x) if name.endswith(".aud") else wav_bytes(x)
    return data, m


def load_prov() -> dict:
    return json.loads(PROV.read_text(encoding="utf-8")) if PROV.exists() else {"files": {}}


def save_prov(prov: dict):
    """Merge this run's records into the file as it is now (other generators write to it too)."""
    current = load_prov()
    current["files"].update(prov["files"])
    prov = current
    PROV.write_text(json.dumps(prov, indent=1, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8",
                    newline="\n")


def build(names):
    prov = {"files": {}}   # this run's records only; save_prov merges them into the file
    for name in names:
        folder, role, fn, refname = RECIPES[name]
        data, m = render(name)
        out = AUDIO / folder / name
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
        ref = ref_of(name)
        prov["files"][f"{folder}/{name}"] = {
            "category": "ui" if folder == "ui" else ("dog voice" if folder == "voices" else "sfx"),
            "role": role, "generator": GENERATOR, "recipe": fn.__name__ if not fn.__name__.startswith("<") else name,
            "method": "procedural synthesis (sines, seeded noise, filters, synthetic reverb); no recordings or samples",
            "seed": f"sha256('{VERSION}/{name}')", "license": "GPL-3.0 (project code); output has no third-party rights",
            "format": "Westwood AUD IMA ADPCM 22.05 kHz mono" if name.endswith(".aud") else "WAV PCM 16-bit 22.05 kHz mono",
            "matched_to": {"seconds": ref["seconds"], "max50_rms_dbfs": ref.get("max50_rms_dbfs"),
                           "active_rms_dbfs": ref["active_rms_dbfs"],
                           "reference": refname if isinstance(refname, str) else "none (name missing in RA2 too)"},
            "measured": {k: m[k] for k in ("seconds", "peak_dbfs", "max50_rms_dbfs", "active_rms_dbfs", "decay20_ms",
                                           "low_share", "high_share")},
            "numpy": np.__version__, "generated": dt.date.today().isoformat(),
            "sha256": hashlib.sha256(data).hexdigest(),
        }
        print(f"{folder}/{name}: {m['seconds']} s, loudest 50 ms {m['max50_rms_dbfs']} dBFS "
              f"(target {ref.get('max50_rms_dbfs', ref['active_rms_dbfs'])}), peak {m['peak_dbfs']}", flush=True)
    save_prov(prov)


def compare(names):
    keys = ["max50_rms_dbfs", "active_rms_dbfs", "attack_ms", "decay20_ms", "zcr_hz", "low_share", "high_share"]
    print(f"{'file':14s} " + " ".join(f"{k[:10]:>16s}" for k in keys))
    for name in names:
        folder = RECIPES[name][0]
        p = AUDIO / folder / name
        if not p.exists() or name.endswith(".aud"):
            continue
        with wave.open(str(p)) as w:
            x = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2") / 32768.0
        m = metrics(x)
        ref = ref_of(name)
        print(f"{name:14s} " + " ".join(f"{m.get(k, 0):>7}/{ref.get(k, '-'):>8}" for k in keys))


def verify() -> int:
    """Rebuild every recipe in memory and compare with the shipped file (bit-exact, or within 4 LSB per sample)."""
    prov = load_prov()
    bad = 0
    for name, (folder, *_rest) in RECIPES.items():
        p = AUDIO / folder / name
        if not p.exists():
            continue
        data, _ = render(name)
        shipped = p.read_bytes()
        if data == shipped:
            state = "identical"
        elif name.endswith(".aud") or len(data) != len(shipped):
            state = "DIFFERS"
        else:
            a = np.frombuffer(data[44:], dtype="<i2").astype(int)
            b = np.frombuffer(shipped[44:], dtype="<i2").astype(int)
            state = "within 4 LSB" if np.max(np.abs(a - b)) <= 4 else "DIFFERS"
        if prov["files"].get(f"{folder}/{name}", {}).get("sha256") != hashlib.sha256(shipped).hexdigest():
            state += ", provenance hash stale"
        bad += state not in ("identical", "within 4 LSB")
        print(f"{folder}/{name}: {state}")
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["build", "compare", "verify", "list"])
    ap.add_argument("names", nargs="*")
    a = ap.parse_args()
    names = a.names or list(RECIPES)
    if a.cmd == "build":
        build(names)
    elif a.cmd == "compare":
        compare(names)
    elif a.cmd == "verify":
        sys.exit(verify())
    else:
        for k, (folder, role, *_r) in RECIPES.items():
            print(f"{folder}/{k}: {role}")


if __name__ == "__main__":
    main()
