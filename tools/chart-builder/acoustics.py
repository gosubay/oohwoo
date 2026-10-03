"""Audio evidence used by the builder: loudness envelope for syllable attacks, and an independent pitch
estimator for cross-checking notes.

The YIN-style estimator is the one used by tools/catalogue-audit/review-placement.py (2026-10-03 audit):
64 ms unwindowed frames, 20 ms hop, no melody input, no octave folding, no key snapping. It is a second
opinion, not ground truth.
"""
import os, subprocess
import numpy as np

SR = 16000

def decode(path, sr=SR):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-ac', '1', '-ar', str(sr), '-f', 'f32le', '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32)

# ---------------------------------------------------------------- loudness envelope
ENV_HOP = 0.005; ENV_WIN = 0.025

def envelope(x, sr=SR):
    """RMS every 5 ms over 25 ms windows. Returns (times, rms)."""
    hop = int(sr * ENV_HOP); win = int(sr * ENV_WIN)
    n = max(0, (len(x) - win) // hop)
    idx = np.arange(win)[None, :] + hop * np.arange(n)[:, None]
    rms = np.sqrt((x[idx].astype(np.float64) ** 2).mean(axis=1))
    return (np.arange(n) * hop + win / 2) / sr, rms

def dips(times, rms, a, b, edge=0.07, spacing=0.10, reach=0.15):
    """Loudness dips strictly inside (a, b): local minima with a recovery on both sides.
    Each dip: {'t', 'depth'} where depth = dip level / min(peak before, peak after) (lower = clearer).
    A consonant or re-attack between two syllables on one pitch normally shows as such a dip."""
    sel = np.flatnonzero((times > a + edge) & (times < b - edge))
    if len(sel) < 3: return []
    smooth = np.convolve(rms, np.ones(3) / 3, 'same')
    k_reach = int(reach / ENV_HOP)
    out = []
    for i in sel:
        lo, hi = max(0, i - 4), min(len(smooth), i + 5)
        if smooth[i] > smooth[lo:hi].min() + 1e-12: continue
        left = smooth[max(0, i - k_reach):i]; right = smooth[i + 1:i + 1 + k_reach]
        if not len(left) or not len(right): continue
        depth = smooth[i] / max(1e-9, min(left.max(), right.max()))
        if depth < 0.9: out.append({'t': float(times[i]), 'depth': float(depth)})
    out.sort(key=lambda d: d['depth'])
    kept = []
    for d in out:                                          # deepest first, at least `spacing` apart
        if all(abs(d['t'] - k['t']) >= spacing for k in kept): kept.append(d)
    return sorted(kept, key=lambda d: d['t'])

# ---------------------------------------------------------------- independent pitch (YIN)
YIN_WIN, YIN_HOP = 1024, 320

def yin_track(x, sr=SR):
    times, pitches, energies, confidences = [], [], [], []
    lo, hi = int(sr / 1100), int(sr / 75)
    for offset in range(0, max(0, len(x) - YIN_WIN + 1), YIN_HOP * 512):
        starts = np.arange(offset, min(len(x) - YIN_WIN + 1, offset + YIN_HOP * 512), YIN_HOP)
        frames = x[starts[:, None] + np.arange(YIN_WIN)[None, :]].astype(np.float64)
        frames -= frames.mean(axis=1, keepdims=True)
        ac = np.fft.irfft(np.abs(np.fft.rfft(frames, 2 * YIN_WIN, axis=1)) ** 2, axis=1)
        energy = np.concatenate([np.zeros((len(frames), 1)), np.cumsum(frames ** 2, axis=1)], axis=1)
        lags = np.arange(1, hi + 1)
        diff = np.maximum(0, energy[:, YIN_WIN - lags] + energy[:, YIN_WIN, None] - energy[:, lags] - 2 * ac[:, lags])
        cmnd = diff * lags / np.maximum(np.cumsum(diff, axis=1), 1e-12)
        for i, start in enumerate(starts):
            curve = np.r_[1., cmnd[i]]
            choices = np.where(curve[lo:hi] < .15)[0]
            lag = lo + int(choices[0]) if len(choices) else lo + int(np.argmin(curve[lo:hi]))
            while lag < hi - 1 and curve[lag + 1] < curve[lag]: lag += 1
            a, b, c = curve[lag - 1:lag + 2]
            delta = .5 * (a - c) / (a - 2 * b + c) if abs(a - 2 * b + c) > 1e-12 else 0
            hz = sr / (lag + np.clip(delta, -.5, .5))
            times.append((start + YIN_WIN / 2) / sr)
            pitches.append(69 + 12 * np.log2(hz / 440))
            energies.append(np.sqrt(np.mean(frames[i] ** 2)))
            confidences.append(1 - curve[lag])
    t, m, r, c = map(np.asarray, (times, pitches, energies, confidences))
    voiced = (c > .80) & (r > max(.008, float(np.percentile(r, 95)) * .08)) & (m > 38) & (m < 90)
    return t, m, voiced

def interval_pitch(track, a, b, tune=0.0):
    """Median pitch of a track inside (a, b), ignoring 20% at each edge (scoops and releases)."""
    t, m, v = track
    d = b - a
    mask = (t >= a + min(.05, d * .2)) & (t < b - min(.04, d * .2)) & v
    if mask.sum() < 3: return None, int(mask.sum()), 0.0
    obs = m[mask] - tune
    med = float(np.median(obs))
    stable = float(np.mean(np.abs(obs - med) < 0.4))
    return med, int(mask.sum()), stable

# ---------------------------------------------------------------- vowel-colour change
SPEC_HOP = 0.005

def band_energies(x, sr=SR, win=1024, bands=40, lo=100.0, hi=5000.0):
    """Log energy in 40 log-spaced bands every 5 ms (64 ms Hann window). Returns (times, matrix)."""
    hop = int(sr * SPEC_HOP)
    n = max(0, (len(x) - win) // hop)
    edges = np.geomspace(lo, hi, bands + 1)
    freqs = np.fft.rfftfreq(win, 1 / sr)
    which = np.digitize(freqs, edges) - 1
    window = np.hanning(win).astype(np.float32)
    out = np.zeros((n, bands), dtype=np.float32)
    for a in range(0, n, 4000):
        idx = np.arange(win)[None, :] + hop * np.arange(a, min(n, a + 4000))[:, None]
        spec = np.abs(np.fft.rfft(x[idx] * window, axis=1)) ** 2
        for k in range(bands):
            sel = which == k
            out[a:a + len(idx), k] = spec[:, sel].sum(axis=1) if sel.any() else 0
    return (np.arange(n) * hop + win / 2) / sr, np.log(out + 1e-10)

def colour_change(spec, t, side=0.06, guard=0.015):
    """1 - correlation between the average spectral shape just before and just after t
    (0 = same vowel colour, larger = a different sound starts)."""
    times, bands = spec
    before = bands[(times >= t - guard - side) & (times < t - guard)]
    after = bands[(times > t + guard) & (times <= t + guard + side)]
    if len(before) < 3 or len(after) < 3: return 0.0
    a = before.mean(axis=0); b = after.mean(axis=0)
    a = a - a.mean(); b = b - b.mean()
    return float(1 - (a @ b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-12))
