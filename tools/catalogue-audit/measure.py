import json, subprocess, sys, os
import numpy as np
SP = sys.argv[1]
SR = 11025; WIN = 2048; HOP = 110  # ~186 ms window, ~10 ms hop (same as the Twinkle analysis)
charts = json.load(open(os.path.join(SP, 'charts.json'), encoding='utf-8'))

def decode(path):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32)

def track(x):
    n = (len(x) - WIN) // HOP
    idx = np.arange(WIN)[None, :] + HOP * np.arange(n)[:, None]
    fr = x[idx] * np.hanning(WIN)[None, :]
    rms = np.sqrt((x[idx] ** 2).mean(axis=1))
    spec = np.fft.rfft(fr, 2 * WIN, axis=1)
    ac = np.fft.irfft(np.abs(spec) ** 2, axis=1)[:, :WIN]
    ac /= ac[:, :1] + 1e-12
    lo, hi = int(SR / 1000), int(SR / 120)   # 120-1000 Hz
    seg = ac[:, lo:hi]
    # prefer the shortest lag whose peak is near the max (reduces octave-down errors)
    mx = seg.max(axis=1)
    lag = np.empty(n)
    for i in range(n):
        cand = np.where(seg[i] >= 0.9 * mx[i])[0]
        k = cand[0]
        while k + 1 < seg.shape[1] and seg[i, k + 1] > seg[i, k]:
            k += 1
        k += lo
        a, b, c = ac[i, k - 1], ac[i, k], ac[i, k + 1]
        d = a - 2 * b + c
        lag[i] = k + (0.5 * (a - c) / d if d else 0)
    f = SR / lag
    thr = max(0.02, 0.15 * np.percentile(rms, 95))
    voiced = (rms > thr) & (mx > 0.5)
    midi = 69 + 12 * np.log2(f / 440)
    t = (np.arange(n) * HOP + WIN / 2) / SR
    return t, midi, voiced, rms

rows = []
for key, c in charts.items():
    voc = 'separated/vocals/' + os.path.basename(c['audio'])
    x = decode(voc)
    t, midi, voiced, rms = track(x)
    dur = len(x) / SR
    first_voice = None
    # first sustained singing: 0.3 s of mostly voiced frames
    run = np.convolve(voiced.astype(float), np.ones(30) / 30, 'same')
    w = np.where(run > 0.8)[0]
    if len(w): first_voice = float(t[w[0]]) - 0.15

    def score(shift, transpose=0):
        exact = octave = silent = 0; errs = []
        for nte in c['notes']:
            m = (t >= nte['t'] + shift) & (t < nte['end'] + shift)
            v = m & voiced
            if m.sum() == 0 or v.sum() < 0.3 * m.sum() or v.sum() < 5:
                silent += 1; continue
            d = float(np.median(midi[v])) - (nte['midi'] + transpose)
            errs.append(d)
            if abs(d) <= 0.6: exact += 1
            dd = (d + 6) % 12 - 6
            if abs(dd) <= 0.6: octave += 1
        return exact, octave, silent, errs

    N = len(c['notes'])
    ex, oc, si, errs = score(0)
    # best case: allow one global time shift (+-3 s) and one global key change
    best = (oc, 0.0, 0)
    for sh in np.arange(-3, 3.01, 0.05):
        for tr in range(-6, 6):
            _, o, _, _ = score(sh, tr)
            if o > best[0]: best = (o, float(sh), tr)
    # how often the singer starts a note: onsets = unvoiced->voiced or pitch change >0.8 st
    chart_end = c['notes'][-1]['end']
    rows.append(dict(key=key, N=N, exact=ex, octave=oc, silent=si, dur=round(dur, 1),
                     chart_start=round(c['notes'][0]['t'], 2), first_voice=None if first_voice is None else round(first_voice, 2),
                     chart_end=round(chart_end, 1), best=best,
                     med_err=None if not errs else round(float(np.median(np.abs([(e + 6) % 12 - 6 for e in errs]))), 2)))
    r = rows[-1]
    print(f"{key:14s} notes {N:3d} | right pitch {oc:3d} ({100*oc//N:3d}%) exact-octave {ex:3d} | singer silent {si:3d} | "
          f"chart starts {r['chart_start']:6.2f}s voice starts {r['first_voice']}s | chart ends {r['chart_end']:5.1f}s of {r['dur']:5.1f}s | "
          f"best w/ shift {best[1]:+.2f}s key {best[2]:+d}: {best[0]} ({100*best[0]//N}%)", flush=True)
json.dump(rows, open(os.path.join(SP, 'results.json'), 'w'), indent=1)
