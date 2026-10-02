"""Turn a separated vocal recording into note events (start, end, pitch with octave).
Numerical draft only: an automatic reading cannot hear consonants and must be checked by ear.
"""
import subprocess
import numpy as np

SR = 11025; WIN = 2048; HOP = 110          # ~186 ms window, ~10 ms hop (as docs/twinkle-analysis.json)
FRAME = HOP / SR
LOW_MIDI, HIGH_MIDI = 45, 88               # A2..E6 search range

def decode(path):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32)

def pitch_track(x):
    """Per-frame time, MIDI pitch, voiced flag, loudness."""
    n = (len(x) - WIN) // HOP
    idx = np.arange(WIN)[None, :] + HOP * np.arange(n)[:, None]
    window = np.hanning(WIN)[None, :]
    # short loudness window (46 ms) so syllable dips stay visible
    c = WIN // 2
    short = x[idx[:, c - 256:c + 256]]
    rms = np.sqrt((short ** 2).mean(axis=1))
    midi = np.full(n, np.nan); conf = np.zeros(n)
    lo, hi = int(SR / 1000), int(SR / 105)
    for a in range(0, n, 2000):
        fr = x[idx[a:a + 2000]] * window
        ac = np.fft.irfft(np.abs(np.fft.rfft(fr, 2 * WIN, axis=1)) ** 2, axis=1)[:, :WIN]
        ac /= ac[:, :1] + 1e-12
        seg = ac[:, lo:hi]; mx = seg.max(axis=1)
        for i in range(seg.shape[0]):
            k = int(np.argmax(seg[i] >= 0.8 * mx[i]))      # shortest strong period: avoids octave-down errors
            while k + 1 < seg.shape[1] and seg[i, k + 1] > seg[i, k]:
                k += 1
            k += lo
            p, q, r = ac[i, k - 1], ac[i, k], ac[i, k + 1]
            d = p - 2 * q + r
            lag = k + (0.5 * (p - r) / d if d else 0)
            midi[a + i] = 69 + 12 * np.log2(SR / lag / 440); conf[a + i] = mx[i]
    t = (np.arange(n) * HOP + WIN / 2) / SR
    floor = max(0.01, 0.12 * np.percentile(rms, 95))
    voiced = (rms > floor) & (conf > 0.5) & (midi > LOW_MIDI) & (midi < HIGH_MIDI)
    return t, midi, voiced, rms

def fix_octaves(midi, voiced):
    """Pull isolated octave slips back toward the surrounding melody."""
    out = midi.copy(); v = np.where(voiced)[0]
    if not len(v): return out
    for i in v:
        near = v[(v > i - 60) & (v < i + 60)]
        ref = np.median(midi[near])
        while out[i] - ref > 7.5: out[i] -= 12
        while ref - out[i] > 7.5: out[i] += 12
    return out

def tuning_offset(midi, voiced):
    """How far the recording sits from concert pitch, in semitones (-0.5..0.5)."""
    frac = midi[voiced] % 1.0
    ang = np.angle(np.exp(2j * np.pi * frac).mean())
    return float(ang / (2 * np.pi))

def segment(t, midi, voiced, rms, min_note=0.09):
    """Viterbi over semitone states inside each voiced stretch, then split on loudness dips."""
    tune = tuning_offset(midi, voiced)
    notes = []; n = len(t); i = 0
    states = np.arange(LOW_MIDI, HIGH_MIDI + 1)
    SWITCH = 5.0
    while i < n:
        if not voiced[i]: i += 1; continue
        j = i
        while j < n and (voiced[j] or (j + 4 < n and voiced[j:j + 5].any())): j += 1   # bridge <=40 ms holes
        while not voiced[j - 1]: j -= 1
        if j - i >= 6:
            fr = np.arange(i, j); obs = midi[fr] - tune
            ok = voiced[fr]
            cost = np.minimum((obs[:, None] - states[None, :]) ** 2, 4.0); cost[~ok] = 0.3
            acc = cost[0].copy(); back = np.zeros((len(fr), len(states)), dtype=int)
            for k in range(1, len(fr)):
                best = int(np.argmin(acc)); stay = acc; jump = acc[best] + SWITCH
                use_jump = jump < stay
                back[k] = np.where(use_jump, best, np.arange(len(states)))
                acc = np.where(use_jump, jump, stay) + cost[k]
            path = np.zeros(len(fr), dtype=int); path[-1] = int(np.argmin(acc))
            for k in range(len(fr) - 1, 0, -1): path[k - 1] = back[k, path[k]]
            a = 0
            for k in range(1, len(fr) + 1):
                if k == len(fr) or path[k] != path[a]:
                    notes.append([int(fr[a]), int(fr[k - 1]) + 1, int(states[path[a]])]); a = k
        i = j
    # absorb slides and blips shorter than min_note into a neighbour in the same stretch
    need = int(round(min_note / FRAME)); changed = True
    while changed:
        changed = False
        for k, (a, b, m) in enumerate(notes):
            if b - a >= need: continue
            prev_touch = k > 0 and notes[k - 1][1] == a
            next_touch = k + 1 < len(notes) and notes[k + 1][0] == b
            if next_touch: notes[k + 1][0] = a      # a scoop belongs to the note it arrives on
            elif prev_touch: notes[k - 1][1] = b
            del notes[k]; changed = True; break
    # merge touching notes that ended up on the same pitch
    merged = []
    for a, b, m in notes:
        if merged and merged[-1][1] == a and merged[-1][2] == m: merged[-1][1] = b
        else: merged.append([a, b, m])
    # a short glide that lands on the next note is the singer scooping into it, not a separate note
    k = 0
    while k + 1 < len(merged):
        a, b, m = merged[k]; a2, b2, m2 = merged[k + 1]
        if b == a2 and (b - a) * FRAME < 0.26 and 0 < abs(m2 - m) <= 2 and (b2 - a2) >= (b - a):
            seg = (midi[a:b] - tune)[voiced[a:b]]
            third = max(1, len(seg) // 3)
            glide = np.median(seg[-third:]) - np.median(seg[:third]) if len(seg) >= 3 else 0
            off_centre = abs(np.median(seg) - m) if len(seg) else 0
            quick = (b - a) * FRAME < 0.2 and (b2 - a2) >= 2 * (b - a)
            breath_before = k == 0 or merged[k - 1][1] < a - 20      # phrase-initial slide up to the first note
            lead_in = breath_before and (b - a) * FRAME < 0.2 and (b2 - a2) >= 2.5 * (b - a)
            if lead_in or (glide * (m2 - m) > 0 and abs(glide) >= (0.3 if quick else 0.35)) or off_centre >= (0.2 if quick else 0.3):
                merged[k + 1][0] = a; del merged[k]; continue
        k += 1
    # split repeated syllables on one pitch where loudness clearly dips and recovers
    out = []
    for a, b, m in merged:
        cuts = []; e = rms[a:b]
        piece = 2 * need                                   # each side of a split must last ~0.18 s
        if b - a >= 2 * piece:
            sm = np.convolve(e, np.ones(3) / 3, 'same'); k = piece
            while k < len(sm) - piece:
                left = sm[max(0, k - 25):k].max(); right = sm[k + 1:k + 26].max()
                if sm[k] == sm[max(0, k - 6):k + 7].min() and sm[k] < 0.45 * min(left, right):
                    cuts.append(a + k); k += piece
                else: k += 1
        edges = [a] + cuts + [b]
        for p, q in zip(edges, edges[1:]): out.append([p, q, m])
    result = []
    for a, b, m in out:
        v = voiced[a:b]
        med = float(np.median((midi[a:b] - tune)[v])) if v.any() else float(m)
        result.append({'onset': float(t[a]) - FRAME / 2, 'end': float(t[b - 1]) + FRAME / 2, 'midi': int(m),
                       'median': round(med, 2), 'frames': int(v.sum())})
    return result, tune

def analyse(path):
    x = decode(path)
    t, midi, voiced, rms = pitch_track(x)
    midi = fix_octaves(midi, voiced)
    notes, tune = segment(t, midi, voiced, rms)
    return {'duration': len(x) / SR, 'tuning': tune, 'notes': notes}
