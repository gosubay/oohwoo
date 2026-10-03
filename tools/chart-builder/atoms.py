"""Smallest sung pieces ("atoms") of a vocal recording, for lyric-aware note building.

The note reader in notes_from_vocal.py decides on its own which short sounds are slides and which repeated
pitches are one note, before it knows the words; in fast songs it swallows real short notes and merges
repeated syllables. An atom is cut wherever the recording gives any evidence of a new note: a silence, a
pitch change that lasts, or a loudness dip. build_charts.py then decides, with the syllable count and the
transcript times, which atoms start a syllable and which continue one. Measurements only; nothing here
knows a tune or a lyric.
"""
import json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from catalogue import ROOT, asset_paths, sha256
from notes_from_vocal import decode as decode_11k, pitch_track, fix_octaves, tuning_offset, FRAME, LOW_MIDI, HIGH_MIDI
from acoustics import decode, envelope, dips, band_energies, colour_change

ATOM_VERSION = 4
MIN_RUN = 0.06           # a pitch must last this long to be its own atom
MIN_PIECE = 0.10         # shortest atom made by cutting at a loudness dip
CUT_SPACING = 0.15       # two dips closer than this are one consonant; the clearer one is kept
CACHE = os.path.join(ROOT, 'docs', 'catalogue-analysis', 'atom-cache')

def pitch_runs(t, midi, voiced, tune):
    """Stretches of one semitone inside each voiced stretch (same Viterbi as the note reader)."""
    runs = []; n = len(t); i = 0
    states = np.arange(LOW_MIDI, HIGH_MIDI + 1); SWITCH = 5.0
    while i < n:
        if not voiced[i]: i += 1; continue
        j = i
        while j < n and (voiced[j] or (j + 4 < n and voiced[j:j + 5].any())): j += 1
        while not voiced[j - 1]: j -= 1
        if j - i >= 6:
            fr = np.arange(i, j); obs = midi[fr] - tune; ok = voiced[fr]
            cost = np.minimum((obs[:, None] - states[None, :]) ** 2, 4.0); cost[~ok] = 0.3
            acc = cost[0].copy(); back = np.zeros((len(fr), len(states)), dtype=int)
            for k in range(1, len(fr)):
                best = int(np.argmin(acc)); jump = acc[best] + SWITCH
                use_jump = jump < acc
                back[k] = np.where(use_jump, best, np.arange(len(states)))
                acc = np.where(use_jump, jump, acc) + cost[k]
            path = np.zeros(len(fr), dtype=int); path[-1] = int(np.argmin(acc))
            for k in range(len(fr) - 1, 0, -1): path[k - 1] = back[k, path[k]]
            a = 0
            for k in range(1, len(fr) + 1):
                if k == len(fr) or path[k] != path[a]:
                    runs.append([int(fr[a]), int(fr[k - 1]) + 1, int(states[path[a]])]); a = k
        i = j
    need = int(round(MIN_RUN / FRAME)); changed = True
    while changed:                                   # a blip shorter than MIN_RUN joins a touching neighbour
        changed = False
        for k, (a, b, m) in enumerate(runs):
            if b - a >= need: continue
            if k + 1 < len(runs) and runs[k + 1][0] == b: runs[k + 1][0] = a
            elif k > 0 and runs[k - 1][1] == a: runs[k - 1][1] = b
            del runs[k]; changed = True; break
    merged = []
    for a, b, m in runs:
        if merged and merged[-1][1] == a and merged[-1][2] == m: merged[-1][1] = b
        else: merged.append([a, b, m])
    return merged

def analyse_atoms(path):
    x = decode_11k(path)
    t, midi, voiced, rms = pitch_track(x)
    midi = fix_octaves(midi, voiced)
    tune = tuning_offset(midi, voiced)
    x16 = decode(path); env = envelope(x16); spec = band_energies(x16)
    atoms = []
    smooth = np.convolve(env[1], np.ones(3) / 3, 'same')
    def edge(at):                                    # loudness dip and vowel-colour change at a pitch change
        et = env[0]
        mid = smooth[(et >= at - 0.05) & (et <= at + 0.05)]
        left = smooth[(et >= at - 0.20) & (et < at - 0.05)]; right = smooth[(et > at + 0.05) & (et <= at + 0.20)]
        if not len(mid) or not len(left) or not len(right): return None
        return {'depth': round(float(mid.min() / max(1e-9, min(left.max(), right.max()))), 3), 'colour': round(colour_change(spec, at), 3)}
    previous_end = None
    for a, b, m in pitch_runs(t, midi, voiced, tune):
        on = float(t[a]) - FRAME / 2; end = float(t[b - 1]) + FRAME / 2
        cuts = []
        for d in sorted(dips(env[0], env[1], on, end), key=lambda d: d['depth']):     # clearest first
            if d['t'] - on >= MIN_PIECE and end - d['t'] >= MIN_PIECE and all(abs(d['t'] - c['t']) >= CUT_SPACING for c in cuts):
                cuts.append({'t': d['t'], 'depth': round(d['depth'], 3), 'colour': round(colour_change(spec, d['t']), 3)})
        cuts.sort(key=lambda c: c['t'])
        edges = [on] + [c['t'] for c in cuts] + [end]
        for k, (p, q) in enumerate(zip(edges, edges[1:])):
            sel = (t >= p) & (t < q) & voiced
            obs = midi[sel] - tune
            med = float(np.median(obs)) if len(obs) else float(m)
            third = max(1, len(obs) // 3)
            glide = float(np.median(obs[-third:]) - np.median(obs[:third])) if len(obs) >= 3 else 0.0
            atom = {'onset': round(p, 4), 'end': round(q, 4), 'midi': int(m), 'median': round(med, 2), 'glide': round(glide, 2)}
            if k: atom['cut'] = {'depth': cuts[k - 1]['depth'], 'colour': cuts[k - 1]['colour']}
            elif previous_end is not None and p - previous_end <= 0.03:
                e = edge(p)
                if e: atom['edge'] = e
            atoms.append(atom)
        previous_end = end
    return {'version': ATOM_VERSION, 'tuning': tune, 'atoms': atoms}

def atom_cache(key):
    vocal = asset_paths(key)['vocal']; digest = sha256(vocal)
    path = os.path.join(CACHE, key + '.json')
    if os.path.exists(path):
        data = json.load(open(path, encoding='utf-8'))
        if data.get('vocalSha256') == digest and data.get('version') == ATOM_VERSION: return data
    os.makedirs(CACHE, exist_ok=True)
    data = {'vocalSha256': digest, **analyse_atoms(os.path.join(ROOT, vocal))}
    json.dump(data, open(path, 'w', encoding='utf-8'), indent=0)
    return data
