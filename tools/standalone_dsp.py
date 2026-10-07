"""Small, deterministic DSP kit for the standalone sound effects (numpy only).

Everything here is computed from sine waves, seeded noise and filters; no recording or sample library is involved.
Used by tools/standalone-sfx.py. Sample rate 22.05 kHz mono, like the sounds the rules expected.
"""
from __future__ import annotations

import hashlib

import numpy as np

SR = 22050


def n_of(sec: float) -> int:
    return max(1, int(round(sec * SR)))


def tt(n: int) -> np.ndarray:
    return np.arange(n) / SR


class Rand:
    """Seeded randomness. The seed is derived from the sound's name and a variant tag, so each file is reproducible."""

    def __init__(self, *tags):
        h = hashlib.sha256("/".join(map(str, tags)).encode()).digest()
        self.seed = int.from_bytes(h[:8], "little")
        self.g = np.random.Generator(np.random.PCG64(self.seed))

    def u(self, a=0.0, b=1.0):
        return float(self.g.uniform(a, b))

    def i(self, a, b):
        return int(self.g.integers(a, b + 1))

    def noise(self, n):
        return self.g.standard_normal(n)

    def exp(self, mean):
        return float(self.g.exponential(mean))

    def sub(self, tag):
        return Rand(self.seed, tag)


# ------------------------------------------------------------------------------------------------- envelopes
def env(n, attack=0.002, t60=0.5, delay=0.0, hold=0.0, shape=1.0):
    """Linear (shape=1) or curved attack, optional hold, then exponential decay reaching -60 dB after t60."""
    t = tt(n) - delay
    a = max(attack, 1e-5)
    rise = np.clip(t / a, 0, 1) ** shape
    dec = np.exp(-6.91 * np.clip(t - a - hold, 0, None) / max(t60, 1e-4))
    e = rise * dec
    e[t < 0] = 0
    return e


def env_pts(n, pts):
    """Piecewise-linear envelope in dB through (seconds, dB) points; -inf-ish below -90 dB."""
    ts = np.array([p[0] for p in pts])
    db = np.array([p[1] for p in pts], dtype=float)
    return 10 ** (np.interp(tt(n), ts, db) / 20) * (np.interp(tt(n), ts, db) > -90)


def fade(x, fin=0.0, fout=0.0):
    x = x.copy()
    if fin > 0:
        k = min(len(x), n_of(fin))
        x[:k] *= np.linspace(0, 1, k)
    if fout > 0:
        k = min(len(x), n_of(fout))
        x[-k:] *= np.linspace(1, 0, k)
    return x


def smooth_noise(R: Rand, n, rate, depth=1.0):
    """Band-limited random control signal (cubic-ish interpolation of random knots at `rate` Hz), mean 0."""
    k = int(n / SR * rate) + 4
    knots = R.noise(k)
    x = np.interp(tt(n) * rate, np.arange(k), knots)
    return depth * lp1(x, rate)


# ------------------------------------------------------------------------------------------------- oscillators
def phase(freq):
    return 2 * np.pi * np.cumsum(np.asarray(freq, dtype=float)) / SR


def sweep(n, f0, f1, tau=None, kind="exp"):
    """Frequency track from f0 to f1: exponential approach with time constant tau, or linear/log over the length."""
    t = tt(n)
    if kind == "exp":
        return f1 + (f0 - f1) * np.exp(-t / max(tau, 1e-4))
    if kind == "log":
        return f0 * (f1 / f0) ** (t / t[-1] if n > 1 else 0)
    return f0 + (f1 - f0) * t / max(t[-1], 1e-9)


def sine(freq, ph0=0.0):
    return np.sin(phase(freq) + ph0)


def additive(freq, partials, decays=None, tilt=1.0, n=None):
    """Harmonic stack below Nyquist: sum of sin(k*phase)/k**tilt for k in partials."""
    f = np.asarray(freq, dtype=float)
    if f.ndim == 0:
        f = np.full(n, float(f))
    ph = phase(f)
    out = np.zeros(len(f))
    for k in partials:
        mask = (k * f) < SR * 0.45
        out += np.sin(k * ph) / (k ** tilt) * mask
    return out


def saw(freq, n=None, harmonics=24):
    return additive(freq, range(1, harmonics + 1), tilt=1.0, n=n)


def square(freq, n=None, harmonics=24):
    return additive(freq, range(1, harmonics + 1, 2), tilt=1.0, n=n)


# ------------------------------------------------------------------------------------------------- filters
def lp1(x, fc):
    """One-pole low-pass (fc scalar)."""
    a = 1 - np.exp(-2 * np.pi * fc / SR)
    y = np.empty(len(x))
    s = 0.0
    xl = np.asarray(x, dtype=float).tolist()
    for i, v in enumerate(xl):
        s += a * (v - s)
        y[i] = s
    return y


def hp1(x, fc):
    return np.asarray(x, dtype=float) - lp1(x, fc)


def svf(x, fc, q=0.707, mode="lp"):
    """Topology-preserving state-variable filter (Zavalishin/Cytomic), per-sample cutoff and Q allowed."""
    x = np.asarray(x, dtype=float)
    n = len(x)
    fc = np.clip(np.broadcast_to(np.asarray(fc, dtype=float), (n,)), 5.0, SR * 0.45)
    q = np.broadcast_to(np.asarray(q, dtype=float), (n,))
    g = np.tan(np.pi * fc / SR)
    k = 1.0 / q
    a1 = 1.0 / (1.0 + g * (g + k))
    a2 = g * a1
    a3 = g * a2
    xl, a1l, a2l, a3l, kl = x.tolist(), a1.tolist(), a2.tolist(), a3.tolist(), k.tolist()
    out = [0.0] * n
    ic1 = ic2 = 0.0
    m = {"lp": 0, "bp": 1, "hp": 2, "notch": 3}[mode]
    for i in range(n):
        v3 = xl[i] - ic2
        v1 = a1l[i] * ic1 + a2l[i] * v3
        v2 = ic2 + a2l[i] * ic1 + a3l[i] * v3
        ic1 = 2 * v1 - ic1
        ic2 = 2 * v2 - ic2
        if m == 0:
            out[i] = v2
        elif m == 1:
            out[i] = v1
        elif m == 2:
            out[i] = xl[i] - kl[i] * v1 - v2
        else:
            out[i] = xl[i] - kl[i] * v1
    return np.array(out)


def lp(x, fc, q=0.707, order=2):
    y = svf(x, fc, q, "lp")
    return svf(y, fc, q, "lp") if order >= 4 else y


def hp(x, fc, q=0.707, order=2):
    y = svf(x, fc, q, "hp")
    return svf(y, fc, q, "hp") if order >= 4 else y


def bp(x, fc, q=1.0):
    return svf(x, fc, q, "bp")


def fft_shape(x, gain_fn):
    """Zero-phase spectral shaping, for noise beds and IRs only (never for transients)."""
    n = len(x)
    F = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1 / SR)
    return np.fft.irfft(F * gain_fn(f), n)


def pink(R: Rand, n):
    w = R.noise(n)
    y = fft_shape(w, lambda f: 1 / np.sqrt(np.maximum(f, 20.0)))
    return y / (np.std(y) + 1e-12)


def brown(R: Rand, n):
    w = R.noise(n)
    y = fft_shape(w, lambda f: 1 / np.maximum(f, 15.0))
    return y / (np.std(y) + 1e-12)


# ------------------------------------------------------------------------------------------------- dynamics, space
def sat(x, drive=2.0):
    return np.tanh(drive * x) / np.tanh(drive)


def norm(x, peak=1.0):
    m = np.max(np.abs(x))
    return x * (peak / m) if m > 0 else x


def shift(x, sec, n=None):
    n = len(x) if n is None else n
    d = n_of(sec) if sec > 0 else 0
    y = np.zeros(n)
    if d < n:
        k = min(len(x), n - d)
        y[d:d + k] = x[:k]
    return y


def place(buf, x, at):
    d = n_of(at) if at > 0 else 0
    if d >= len(buf):
        return buf
    k = min(len(x), len(buf) - d)
    buf[d:d + k] += x[:k]
    return buf


def convolve(x, ir):
    n = len(x) + len(ir) - 1
    N = 1 << (n - 1).bit_length()
    return np.fft.irfft(np.fft.rfft(x, N) * np.fft.rfft(ir, N), N)[: len(x)]


def reverb_ir(R: Rand, t60=1.2, damp=3500.0, predelay=0.012, early=6, size=1.0):
    """Synthetic room/outdoor impulse response: early reflections + two-band exponentially decaying noise."""
    n = n_of(min(t60 * 1.1, 6.0) + predelay)
    t = tt(n)
    w = R.noise(n)
    lo = fft_shape(w, lambda f: 1 / np.sqrt(1 + (f / damp) ** 4))
    hi = w - lo
    tail = lo * np.exp(-6.91 * t / t60) + hi * np.exp(-6.91 * t / (t60 * 0.35))
    tail *= np.clip((t - predelay) / 0.03, 0, 1)
    ir = tail / (np.sqrt(np.sum(tail ** 2)) + 1e-12)
    for _ in range(early):
        d = predelay * R.u(0.3, 1.0) * size
        k = n_of(d)
        if k < n:
            ir[k] += R.u(0.15, 0.4) * (1 if R.u() > 0.3 else -1)
    return ir


def reverb(x, R: Rand, t60=1.2, wet=0.2, damp=3500.0, predelay=0.012):
    ir = reverb_ir(R, t60, damp, predelay)
    w = convolve(x, ir)
    w *= np.sqrt(np.mean(x ** 2) / (np.mean(w ** 2) + 1e-12))
    return x + wet * w


def slap(x, R: Rand, delays=(0.09, 0.17, 0.26), gain=0.35, fc=1800.0):
    y = x.copy()
    src = lp1(x, fc)
    for i, d in enumerate(delays):
        y += gain * (0.7 ** i) * shift(src, d * R.u(0.9, 1.1), len(x))
    return y


def limiter(x, ceiling=0.966, look=0.002, release=0.08):
    """Look-ahead peak limiter: smooth gain that keeps |y| <= ceiling."""
    n = len(x)
    need = np.minimum(1.0, ceiling / (np.abs(x) + 1e-12))
    la = max(1, n_of(look))
    pad = np.concatenate([need, np.ones(2 * la)])
    win = np.lib.stride_tricks.sliding_window_view(pad, 2 * la + 1).min(axis=1)[:n]
    rel = 1 - np.exp(-1 / (release * SR))
    g = np.empty(n)
    s = 1.0
    for i, v in enumerate(win.tolist()):
        s = v if v < s else s + rel * (v - s)
        g[i] = s
    # trailing moving average: every sample it covers already saw this sample's peak in its look-ahead window
    kern = np.ones(la) / la
    g = np.convolve(np.concatenate([np.full(la - 1, g[0]), g]), kern, "valid")
    y = x * g
    return np.clip(y, -ceiling, ceiling)


def compress(x, threshold_db=-18.0, ratio=3.0, attack=0.005, release=0.15, makeup=True):
    """Feed-forward RMS compressor (10 ms detector); raises the sustain of explosions the way game mixes do."""
    det = np.sqrt(np.convolve(x ** 2, np.ones(n_of(0.01)) / n_of(0.01), "same") + 1e-12)
    lvl = 20 * np.log10(det)
    over = np.maximum(0, lvl - threshold_db)
    target = -over * (1 - 1 / ratio)
    ga, gr = 1 - np.exp(-1 / (attack * SR)), 1 - np.exp(-1 / (release * SR))
    g = np.empty(len(x))
    s_ = 0.0
    for i, v in enumerate(target.tolist()):
        s_ += (ga if v < s_ else gr) * (v - s_)
        g[i] = s_
    y = x * 10 ** (g / 20)
    return norm(y, np.max(np.abs(x))) if makeup else y


# ------------------------------------------------------------------------------------------------- building blocks
def burst(R: Rand, n, fc, q=0.8, t60=0.05, attack=0.0005, mode="bp"):
    return svf(R.noise(n), fc, q, mode) * env(n, attack, t60)


def metal(R: Rand, n, f0, t60=0.6, delay=0.0, partials=(1.0, 2.76, 5.40, 8.93, 13.34), amps=(1, .55, .35, .22, .12),
          detune=0.012, strike=0.6):
    """Struck bar / plate: inharmonic decaying partials (higher ones decay faster) plus a short noise strike."""
    t = tt(n) - delay
    out = np.zeros(n)
    for p, a in zip(partials, amps):
        f = f0 * p * (1 + R.u(-detune, detune))
        if f > SR * 0.45:
            continue
        out += a * np.sin(2 * np.pi * f * t + R.u(0, 6.28)) * np.exp(-6.91 * np.clip(t, 0, None) / (t60 / p ** 0.5))
    out[t < 0] = 0
    out += strike * shift(burst(R, n_of(0.02), min(f0 * 4, 8000), 0.7, 0.01), delay, n)
    return out


def bubbles(R: Rand, n, count, start, end, f_lo=350, f_hi=1600, amp=0.5, dur=(0.008, 0.04)):
    """Minnaert-style bubbles: decaying sines whose pitch rises as they leave the surface."""
    out = np.zeros(n)
    for _ in range(count):
        at = start + (end - start) * R.u() ** 1.6
        d = R.u(*dur)
        k = n_of(d * 4)
        f0 = np.exp(R.u(np.log(f_lo), np.log(f_hi)))
        t = tt(k)
        f = f0 * (1 + 2.5 * t / d)
        b = np.sin(phase(f)) * np.exp(-t / d) * R.u(0.3, 1.0) * amp
        place(out, b, at)
    return out


def debris(R: Rand, n, start, end, rate0=40, rate1=4, fc=(1500, 6000), amp=0.35, metallic=0.3):
    """Falling debris: sparse short clicks and rattles, rate falling from rate0 to rate1 per second."""
    out = np.zeros(n)
    t = start
    while t < end:
        frac = (t - start) / max(end - start, 1e-6)
        rate = rate0 + (rate1 - rate0) * frac
        t += R.exp(1 / max(rate, 0.5))
        if t >= end:
            break
        k = n_of(R.u(0.006, 0.03))
        g = amp * (1 - 0.7 * frac) * R.u(0.2, 1.0)
        if R.u() < metallic:
            c = metal(R, n_of(0.12), R.u(1200, 4200), t60=R.u(0.04, 0.12), strike=0.3)
        else:
            c = burst(R, k * 3, R.u(*fc), R.u(0.6, 2.0), R.u(0.004, 0.02))
        place(out, g * c, t)
    return out


def explosion(R: Rand, n, delay=0.0, size=1.0, crack=0.5, body=1.0, sub=1.0, rumble=0.5, debris_amt=0.35,
              t60=1.4, fc0=4500, fc1=220, sweep_t=0.35, sub_f=(75, 32), drive=2.2, turbulence=0.35,
              debris_end=None, metallic=0.25, body_attack=0.004, cluster=0, crackle=0.0, rumble_t60=None):
    """Layered explosion: crack, filtered-noise blast with a falling cutoff (plus `cluster` follow-up blasts that make
    it swell), pitch-dropping sub, long rumble, fire crackle and debris."""
    t = np.clip(tt(n) - delay, 0, None)
    cr = hp(R.noise(n), 1800, 0.7) * env(n, 0.0003, 0.035 * size, delay)
    fc = fc1 + (fc0 - fc1) * np.exp(-t / max(sweep_t / 3, 1e-3))
    turb = 1 + turbulence * smooth_noise(R, n, 14)
    bo = svf(R.noise(n), fc, 0.55, "lp") * env(n, body_attack, t60, delay, shape=0.6) * turb
    bo = norm(bo)
    for i in range(cluster):
        d = delay + R.u(0.03, 0.32)
        k = n - n_of(d)
        if k <= 0:
            continue
        tk = tt(k)
        fck = fc1 + (fc0 * 0.7 - fc1) * np.exp(-tk / max(sweep_t / 4, 1e-3))
        b2 = svf(R.noise(k), fck, 0.55, "lp") * env(k, 0.003, t60 * 0.6)
        place(bo, R.u(0.45, 0.8) * norm(b2), d)
    sb = np.sin(phase(sub_f[1] + (sub_f[0] - sub_f[1]) * np.exp(-t / 0.09))) * env(n, 0.003, t60 * 0.45, delay)
    ru = lp(brown(R, n), 160) * env(n, 0.05 * size, rumble_t60 or t60 * 1.5, delay)
    x = crack * norm(cr) + body * norm(bo) + sub * 0.9 * sb + rumble * norm(ru) * 0.6
    if crackle > 0:
        c = hp(R.noise(n) ** 3, 1500) * (1 + 0.8 * smooth_noise(R, n, 20)) * env(n, 0.05, t60 * 0.8, delay + 0.05)
        x += crackle * norm(c) * 0.5
    if debris_amt > 0:
        de = debris(R, n, delay + 0.08, debris_end or (delay + t60 * 0.8), 45, 5, amp=1.0, metallic=metallic)
        x += debris_amt * norm(de) * 0.6
    return sat(norm(x), drive)


def gunshot(R: Rand, body_fc=1300, body_q=0.9, crack=0.9, thump_f=(150, 60), thump=0.6, t60=0.08, mech=0.12,
            drive=2.5, bright=3500, length=0.3):
    """One rifle or cannon report (before echoes): crack, band-passed blast, low thump, mechanical click."""
    n = n_of(length)
    w = R.noise(n)
    c = hp(w, bright, 0.7) * env(n, 0.0002, 0.012)
    b = svf(R.noise(n), body_fc * R.u(0.92, 1.08), body_q, "bp") * env(n, 0.0004, t60)
    th = np.sin(phase(sweep(n, thump_f[0], thump_f[1], 0.025))) * env(n, 0.001, t60 * 1.6)
    x = crack * norm(c) + norm(b) * 1.2 + thump * th
    if mech > 0:
        x += mech * norm(metal(R, n, R.u(2600, 4200), t60=0.05, delay=R.u(0.03, 0.06), strike=0.4))
    return sat(norm(x), drive)


def burst_fire(R: Rand, n, shots, interval, start=0.0, jitter=0.08, decay=0.0, **kw):
    out = np.zeros(n)
    t = start
    for s in range(shots):
        g = R.u(0.85, 1.0) * (1 - decay * s / max(shots - 1, 1))
        place(out, g * gunshot(R.sub(f"shot{s}"), **kw), t)
        t += interval * R.u(1 - jitter, 1 + jitter)
    return out


def whoosh(R: Rand, n, f0, f1, q=1.5, attack=0.05, t60=0.8, delay=0.0, kind="log"):
    f = sweep(n, f0, f1, kind=kind)
    return svf(R.noise(n), f, q, "bp") * env(n, attack, t60, delay, shape=0.7)


def rocket(R: Rand, n, delay=0.0, ignite=0.8, roar=1.0, f0=900, f1=2600, t60=0.7, doppler=True):
    """Missile launch: ignition pop, a hissing roar whose band sweeps up then down, crackle."""
    t = np.clip(tt(n) - delay, 0, None)
    pop = explosion(R.sub("pop"), n, delay, size=0.3, crack=1.0, body=0.6, sub=0.5, rumble=0.1, debris_amt=0,
                    t60=0.15, fc0=6000, fc1=900, sweep_t=0.05, drive=2.5)
    fpath = f0 + (f1 - f0) * (1 - np.exp(-t / 0.08))
    if doppler:
        fpath *= 1 - 0.35 * np.clip((t - 0.15) / 0.8, 0, 1)
    hiss = svf(R.noise(n), fpath, 0.9, "bp") * (1 + 0.5 * smooth_noise(R, n, 60))
    crackle = R.noise(n) ** 3
    crackle = hp(crackle, 2000) * 0.15
    body = (norm(hiss) + norm(crackle) * 0.4) * env(n, 0.02, t60, delay + 0.01, shape=0.6)
    return ignite * pop + roar * norm(body)


def arcs(R: Rand, n, start, end, rate=25, amp=1.0):
    """Electrical discharge: bursts of crackling, buzzing arcs."""
    out = np.zeros(n)
    t = start
    while t < end:
        t += R.exp(1 / rate)
        k = n_of(R.u(0.02, 0.09))
        tk = tt(k)
        f = R.u(90, 160)
        buzz = np.sign(np.sin(2 * np.pi * f * tk)) * 0.5 + R.noise(k) * 0.8
        z = hp(buzz, R.u(1500, 3500)) * env(k, 0.001, R.u(0.02, 0.07)) * R.u(0.3, 1.0)
        place(out, amp * z, t)
    return out


def thunder(R: Rand, n, crack_amt=1.0, roll_amt=1.0, delay=0.0, t60=1.6, rolls=7):
    t = tt(n)
    crack = hp(R.noise(n) * (1 + 3 * np.abs(smooth_noise(R, n, 220))), 1500) * env(n, 0.0005, 0.25, delay)
    roll = np.zeros(n)
    for i in range(rolls):
        d = delay + R.u(0.0, 0.5) * (t[-1] - delay) ** 0.8
        k = n - n_of(d)
        if k <= 0:
            continue
        r = lp(R.noise(k), R.u(90, 320)) * env(k, R.u(0.02, 0.2), R.u(0.4, t60))
        place(roll, R.u(0.4, 1.0) * norm(r), d)
    return crack_amt * norm(crack) + roll_amt * norm(roll)


def motor(R: Rand, n, f0, f1, harmonics=10, tilt=1.2, buzz=0.25, kind="log"):
    f = sweep(n, f0, f1, kind=kind) * (1 + 0.01 * smooth_noise(R, n, 8))
    x = additive(f, range(1, harmonics + 1), tilt=tilt)
    return norm(x) + buzz * norm(bp(R.noise(n), np.clip(f * 6, 50, 9000), 2.0))


def scifi(R: Rand, n, f0, f1, voices=4, spread=0.03, fm=0.0, fm_ratio=1.5, kind="log"):
    """Chorused sine sweep with optional FM, for the time/space effects."""
    out = np.zeros(n)
    base = sweep(n, f0, f1, kind=kind)
    for v in range(voices):
        det = 1 + R.u(-spread, spread)
        f = base * det
        mod = fm * f * np.sin(phase(f * fm_ratio))
        out += np.sin(phase(f + mod) + R.u(0, 6.28))
    return out / voices


# ------------------------------------------------------------------------------------------------- creature sounds
def formant(src, formants, qs, gains):
    return sum(g * bp(src, f, q) for f, q, g in zip(formants, qs, gains))


def glottal(R: Rand, f0_track, jitter=0.04, shimmer=0.25, subharm=0.0, harmonics=24, tilt=0.8):
    """Pulse-like voiced source: harmonic stack with per-cycle jitter and shimmer and an optional subharmonic
    (period doubling), the rough, irregular voicing of an animal call."""
    k = len(f0_track)
    jit = 1 + jitter * smooth_noise(R, k, 90)
    f = f0_track * jit
    src = additive(f, range(1, harmonics + 1), tilt=tilt)
    src *= 1 + shimmer * smooth_noise(R, k, 120)
    if subharm > 0:
        src += subharm * additive(f / 2, (1, 3, 5), tilt=1.0)
    return src


def bark(R: Rand, n, f0=520.0, length=0.16, delay=0.0, rough=0.4, formants=(750, 1600, 2700), growl=0.0):
    """Dog bark: a noisy plosive onset, then a rough voiced burst whose pitch jumps up and falls, through a mouth
    that opens and closes (first formant sweeping up and back), plus breath noise and period doubling."""
    k = n_of(length)
    t = tt(k)
    u = np.clip(t / length, 0, 1)
    contour = f0 * (0.7 + 0.5 * np.sin(np.pi * np.minimum(1, u * 1.6)) - 0.3 * u)
    src = glottal(R, contour, jitter=0.05, shimmer=0.35, subharm=0.35 * (1 + growl), tilt=0.75)
    src = norm(src) + rough * norm(hp(R.noise(k), 600)) * (0.6 + 0.4 * (1 - u))
    if growl > 0:
        src *= 1 + growl * np.sin(2 * np.pi * R.u(22, 34) * t)
    open_ = np.sin(np.pi * np.minimum(1, u * 1.3)) ** 0.7          # mouth opening
    f1 = formants[0] * (0.55 + 0.6 * open_)
    v = (svf(src, f1, 3.0, "bp") + 0.6 * svf(src, formants[1] * (0.85 + 0.25 * open_), 5.0, "bp")
         + 0.35 * svf(src, formants[2], 5.0, "bp"))
    v = norm(v) + 0.9 * norm(lp(src, 280, order=4))   # chest resonance: the body of the bark
    v *= env_pts(k, [(0, -40), (0.006, 0), (length * 0.35, -2), (length * 0.8, -14), (length, -60)])
    onset = hp(R.noise(n_of(0.02)), 1500) * env(n_of(0.02), 0.0005, 0.012)   # the plosive "w/b" release
    out = np.zeros(n)
    place(out, norm(v), delay)
    place(out, 0.35 * norm(onset), delay)
    return out


def growl(R: Rand, n, f0=95.0, delay=0.0, length=0.6, formants=(520, 1150, 2400)):
    k = n_of(length)
    t = tt(k)
    f = f0 * (1 + 0.08 * smooth_noise(R, k, 6)) * (1 + 0.04 * np.sin(2 * np.pi * 7 * t))
    src = additive(f, range(1, 30), tilt=0.7) * (1 + 0.6 * np.abs(smooth_noise(R, k, 30))) + 0.5 * R.noise(k)
    v = formant(src, formants, (3, 5, 5), (1.0, 0.7, 0.3))
    v *= env_pts(k, [(0, -40), (0.06, 0), (length * 0.7, -4), (length, -60)])
    out = np.zeros(n)
    place(out, norm(v), delay)
    return out


def whine(R: Rand, n, f0=900.0, f1=1300.0, delay=0.0, length=0.5):
    k = n_of(length)
    t = tt(k)
    f = f0 + (f1 - f0) * np.sin(np.pi * t / length) + 25 * np.sin(2 * np.pi * 6 * t)
    src = additive(f, range(1, 6), tilt=1.6) + 0.15 * R.noise(k)
    v = formant(src, (f0 * 1.1, 2200), (3, 4), (1.0, 0.4)) * env_pts(k, [(0, -40), (0.05, 0), (length * 0.8, -6), (length, -60)])
    out = np.zeros(n)
    place(out, norm(v), delay)
    return out


def pant(R: Rand, n, breaths=4, rate=5.5, delay=0.0):
    out = np.zeros(n)
    for b in range(breaths):
        k = n_of(0.11)
        x = bp(R.noise(k), R.u(1100, 1600), 1.2) * env_pts(k, [(0, -40), (0.03, 0), (0.11, -50)])
        place(out, norm(x) * (0.9 if b % 2 == 0 else 0.6), delay + b / rate)
    return out


# ------------------------------------------------------------------------------------------------- measurement
def metrics(x: np.ndarray) -> dict:
    """Same definitions as tools/standalone-audio/MeasureAudio.cs."""
    x = np.asarray(x, dtype=float)
    n = len(x)
    d = {"seconds": round(n / SR, 3)}
    if n == 0:
        return d
    peak = np.max(np.abs(x))
    win = SR // 100
    nw = (n + win - 1) // win
    pad = np.zeros(nw * win)
    pad[:n] = x ** 2
    counts = np.full(nw, win)
    counts[-1] = n - (nw - 1) * win
    envl = np.sqrt(pad.reshape(nw, win).sum(axis=1) / counts)
    emax = envl.max()
    ep = int(np.argmax(envl))
    after = np.where(envl[ep:] >= emax * 0.1)[0]
    dec_end = ep + (after[-1] if len(after) else 0)
    start = int(np.argmax(envl >= emax * 0.1))
    active = envl[envl >= emax * 0.01]
    act = np.sqrt(np.mean(active ** 2)) if len(active) else 0
    zc = int(np.sum((x[1:] >= 0) != (x[:-1] >= 0)))
    a_low = np.exp(-2 * np.pi * 250.0 / SR)
    a_high = np.exp(-2 * np.pi * 2500.0 / SR)
    low = lp1(x, 250.0)
    hp_out = np.empty(n)
    s = 0.0
    prev = 0.0
    for i, v in enumerate(x.tolist()):
        s = a_high * (s + v - prev)
        prev = v
        hp_out[i] = s
    sq = np.sum(x ** 2)

    def db(v):
        return round(20 * np.log10(v), 1) if v > 0 else -120.0

    e2 = np.concatenate([envl ** 2, np.zeros(4)])
    max50 = np.sqrt(max(e2[i:i + 5].sum() / 5 for i in range(nw)))
    d.update(peak_dbfs=db(peak), rms_dbfs=db(np.sqrt(sq / n)), active_rms_dbfs=db(act), max50_rms_dbfs=db(max50),
             onset_ms=start * 10,
             attack_ms=(ep - start) * 10, decay20_ms=(dec_end - ep) * 10, zcr_hz=round(zc * SR / (2.0 * n)),
             low_share=round(float(np.sum(low ** 2) / sq), 3) if sq else 0,
             high_share=round(float(np.sum(hp_out ** 2) / sq), 3) if sq else 0)
    del a_low
    return {k: (float(v) if isinstance(v, (float, np.floating)) else int(v)) for k, v in d.items()}
