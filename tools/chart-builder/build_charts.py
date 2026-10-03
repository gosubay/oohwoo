"""Build Full-song and Quick-play charts for all 22 songs from their recordings and correction files.

Usage (repository root):
  python tools/chart-builder/build_charts.py [song keys...]       rebuild and write charts.json
  python tools/chart-builder/build_charts.py --check [keys...]    rebuild in memory, print what would change

Inputs (all hash-checked):
  tools/chart-builder/songs/<key>.json             asset hashes, language blocks, reference verses, Quick-play
                                                   choice, section overrides, note edits (the correction layer)
  docs/catalogue-analysis/section-words/<key>.json language-forced Whisper words (transcribe_sections.py)
  separated/vocals/<recording>.mp3                 the sung line the notes are measured from
  index.html twinkle-chart                         the approved Twinkle verse, copied note for note
Output: docs/catalogue-analysis/charts.json (then apply_to_game.py writes the game block).

Every chart is a recording-based draft: status stays 'owner-listening-pending' until Galvin approves a
section or song by ear in the song file. Numerical flags are review leads; no pitch is changed because of
them. Pitch edits happen only through noteEdits / measuredNoteEdits in the song file, each with its evidence.
"""
import argparse, copy, hashlib, json, os, re, sys
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from catalogue import ROOT, SONGS, asset_paths, sha256, note_cache
from notes_from_vocal import decode as decode_11k, pitch_track
from acoustics import decode, envelope, dips, yin_track, interval_pitch, band_energies, colour_change
from lyrics import reference_tokens, heard_tokens, reconcile, relation, CJK
from atoms import atom_cache

BUILDER = 'chart-builder 2026-10-03'
SONG_DIR = os.path.join(os.path.dirname(__file__), 'songs')
WORDS = os.path.join(ROOT, 'docs', 'catalogue-analysis', 'section-words')
OUT = os.path.join(ROOT, 'docs', 'catalogue-analysis', 'charts.json')
NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
SCALE = [0, 2, 4, 5, 7, 9, 11, 12]; LANES = [0, .14, .29, .43, .57, .71, .86, 1]
MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
KEY_OVERRIDES = {'headshoulders': 'C', 'xiaoyanzi': 'A', 'fingerfamily': 'A'}   # tonic/dominant ties, by melody shape
BREATH = 0.45            # silence that starts a new sung line
STRETCH_GAP = 1.2        # silence that separates sung stretches inside a block
WORDLESS_MIN_NOTES = 6   # a wordless stretch needs this many notes, covering half its span, to be charted
BOUNDARY_LATE = 1.2     # a verse boundary may sit this long after the next verse's first transcript time (those run early)
QUICK_MIN_SPAN = 12.0    # Quick play adds the next sung section while its singing spans less than this
QUICK_END_GAP = 0.6      # with less silence than this after Quick play's last note, the fade runs over that note
# A note that the lyric alignment says carries several syllables is split only at a measured attack:
# a loudness dip to <= 60% of both neighbouring peaks, or <= 85% together with a vowel-colour change
# >= 0.10. Calibrated 2026-10-03 on the approved Twinkle verse: 28/36 approved syllable boundaries pass,
# word-final consonants inside one syllable can also pass, so the lyric alignment must ask first.
SPLIT_DEPTH, SOFT_DEPTH, SOFT_COLOUR = 0.60, 0.85, 0.10
MIN_PIECE = 0.10         # shortest note created by an acoustic split
QUICK_LEAD = 4.0         # Quick play starts this long before its first note when the intro is longer than
QUICK_TRIM_AFTER = 6.0   # ...this many seconds

USE_ATOMS = os.environ.get('CHART_ALIGN', 'atoms') == 'atoms'
USE_SISTERS = os.environ.get('CHART_SISTERS', '1') == '1'

class StaleSource(Exception):
    pass

def pitch_name(m): return NAMES[m % 12] + str(m // 12 - 1)

def lane(semitones):                      # same mapping as pitchLane() in the game
    octave = int(np.floor(semitones / 12)); local = semitones - octave * 12; i = 0
    while i < 6 and local > SCALE[i + 1]: i += 1
    return octave + LANES[i] + (local - SCALE[i]) / (SCALE[i + 1] - SCALE[i]) * (LANES[i + 1] - LANES[i])

def file_sha(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()

# ---------------------------------------------------------------- inputs
def load_spec(key):
    path = os.path.join(SONG_DIR, key + '.json')
    spec = json.load(open(path, encoding='utf-8'))
    for role, asset in spec['assets'].items():
        if sha256(asset['path']) != asset['sha256']:
            raise StaleSource(f"{key}: {asset['path']} changed since the song file was written; re-review before rebuilding")
    if sha256(spec['lyricReference']['path']) != spec['lyricReference']['sha256']:
        raise StaleSource(f"{key}: lyric reference changed; review the verses in {path}")
    return spec, file_sha(path)

def load_words(key, spec):
    path = os.path.join(WORDS, key + '.json')
    words = json.load(open(path, encoding='utf-8'))
    if words['vocalSha256'] != spec['assets']['vocal']['sha256']:
        raise StaleSource(f'{key}: section words were made from a different vocal file; rerun transcribe_sections.py')
    for block in spec['blocks']:
        if block['id'] not in words['blocks']:
            raise StaleSource(f"{key}: block {block['id']} has no transcription; rerun transcribe_sections.py")
    return words, file_sha(path)

def approved_twinkle():
    html = open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()
    return json.loads(re.search(r'<script id="twinkle-chart" type="application/json">([\s\S]*?)</script>', html)[1])

# ---------------------------------------------------------------- lyric units
def section_units(tokens):
    """Reconciled tokens (one per Mandarin character / Latin syllable) -> lyric units for note alignment."""
    units = []
    for k, tok in enumerate(tokens):
        weak = tok['status'] in ('not-heard', 'unscripted-single') or tok.get('anchor') in ('interpolated', 'none', 'section-even')
        units.append({'text': tok['text'], 'language': tok['language'], 'token': k, 'status': tok['status'],
                      'start': tok.get('start'), 'end': tok.get('end'), 'weak': weak, 'lineStart': tok['lineStart'],
                      'wordEnd': tok.get('wordEnd', True), 'line': (tok['verse'], tok['line'])})
    return units

def absorb_glides(notes, raw, tune):
    """A very short note that is only the voice sliding into the next note is part of that next note:
    <= 0.12 s and pitched between its neighbours, or <= 0.18 s, 1-2 semitones from the next note, with the
    frame pitch moving toward it. The absorbed glide is recorded on the note it joins."""
    t, m, v = raw
    out = []
    for i, n in enumerate(notes):
        nxt = notes[i + 1] if i + 1 < len(notes) else None
        prev = out[-1] if out else None
        dur = n['end'] - n['onset']
        if nxt and nxt['onset'] - n['end'] <= 0.03 and nxt['end'] - nxt['onset'] >= 2.5 * dur:
            between = prev is not None and n['onset'] - prev['end'] <= 0.03 and \
                min(prev['midi'], nxt['midi']) < n['midi'] < max(prev['midi'], nxt['midi'])
            sel = (t >= n['onset']) & (t < n['end']) & v
            frames = m[sel] - tune
            toward = False
            if len(frames) >= 3:
                third = max(1, len(frames) // 3)
                toward = abs(np.median(frames[-third:]) - nxt['midi']) + 0.15 < abs(np.median(frames[:third]) - nxt['midi'])
            if (dur <= 0.12 and between) or (dur <= 0.18 and 1 <= abs(nxt['midi'] - n['midi']) <= 2 and toward):
                nxt['onset'] = n['onset']
                nxt.setdefault('absorbedGlides', []).append({'t': round(n['onset'], 2), 'midi': n['midi'], 'seconds': round(dur, 2)})
                continue
        out.append(n)
    return out

def apply_measured_note_edits(key, spec, notes):
    """Reviewed corrections to the measured notes, from the song file, applied before the words are
    placed. Each names one measured note by its start time and gives its evidence:
      split  the note is two sung notes; cut it at 'at' (optionally 'midi': [first, second])
      join   the note is part of a neighbour ('into': 'next' or 'previous'), e.g. a slide
      midi   the note's pitch, 'old' -> 'new'
    A locator that matches no note is an error, never a guess."""
    for edit in spec.get('measuredNoteEdits', []):
        hits = [i for i, n in enumerate(notes) if abs(n['onset'] - edit['onset']) < 0.006]
        if len(hits) != 1:
            raise StaleSource(f"{key}: measured-note edit at {edit['onset']} s matches {len(hits)} notes; re-review the edit")
        i = hits[0]; n = notes[i]
        record = {k: edit[k] for k in ('op', 'onset', 'at', 'into', 'old', 'new', 'midi', 'reason', 'confidence', 'review') if k in edit}
        if edit['op'] == 'split':
            if not n['onset'] + 0.07 <= edit['at'] <= n['end'] - 0.07:
                raise StaleSource(f"{key}: split at {edit['at']} s is not inside the note at {edit['onset']} s")
            first, second = dict(n), dict(n)
            first['end'] = second['onset'] = edit['at']
            second.pop('absorbedGlides', None)
            if 'midi' in edit:
                for piece, m in zip((first, second), edit['midi']):
                    if m != piece['midi']: piece['midi'] = m; piece['median'] = float(m)
            first['measuredEdits'] = n.get('measuredEdits', []) + [record]; second['measuredEdits'] = [record]
            notes[i:i + 1] = [first, second]
        elif edit['op'] == 'join':
            other = notes[i + 1] if edit['into'] == 'next' else notes[i - 1]
            if edit['into'] == 'next': other['onset'] = n['onset']
            else: other['end'] = n['end']
            other.setdefault('measuredEdits', []).append({**record, 'joinedMidi': n['midi']})
            del notes[i]
        elif edit['op'] == 'midi':
            if n['midi'] != edit['old']:
                raise StaleSource(f"{key}: measured note at {edit['onset']} s is midi {n['midi']}, edit expects {edit['old']}")
            n['midi'] = edit['new']; n['median'] = float(edit['new'])
            n.setdefault('measuredEdits', []).append(record)
            k = i + 1                                # the same held pitch, cut at loudness dips, changes with it
            while k < len(notes) and notes[k].get('cut') and notes[k]['midi'] == edit['old']:
                notes[k]['midi'] = edit['new']; notes[k]['median'] = float(edit['new']); k += 1
        else:
            raise StaleSource(f"{key}: unknown measured-note edit {edit['op']!r}")
    return notes

def shift_anchors(units, notes):
    """Whisper word times run early or late by a fairly constant amount within a section. Measure it
    (median distance from each anchored unit to the nearest note onset within 1 s) and remove it, so
    the note alignment compares like with like. Records the shift on each unit."""
    onsets = np.array([n['onset'] for n in notes])
    if not len(onsets): return 0.0
    deltas = []
    for u in units:
        if u['start'] is None or u['weak']: continue
        d = onsets - u['start']; k = int(np.argmin(np.abs(d)))
        if abs(d[k]) <= 1.0: deltas.append(d[k])
    shift = float(np.median(deltas)) if len(deltas) >= 3 else 0.0
    for u in units:
        if u['start'] is not None:
            u['start'] += shift; u['end'] += shift; u['anchorShift'] = round(shift, 3)
    return shift

SCOOP_MAX = 0.20         # a note this short, running straight into a longer note 1-4 semitones away, may be
SCOOP_RATIO = 1.5        # ...the voice sliding into that note (the next note must be this many times longer)

def is_scoop(notes, i):
    """Could note i be the singer sliding into note i+1 rather than a syllable of its own? Only the lyric
    count decides: align() prefers to leave such a note without a syllable, but still gives it one when
    the line needs every note."""
    if i + 1 >= len(notes) or 'midi' not in notes[i]: return False
    n, nxt = notes[i], notes[i + 1]
    dur = n['end'] - n['onset']
    if not (dur <= SCOOP_MAX and nxt['onset'] - n['end'] <= 0.03 and nxt['end'] - nxt['onset'] >= SCOOP_RATIO * dur):
        return False
    step = nxt['midi'] - n['midi']
    if 1 <= step <= 2: return True                       # sliding up into the note from just below
    prev = notes[i - 1] if i else None                   # or passing between two notes on the way
    return bool(prev) and n['onset'] - prev['end'] <= 0.03 and abs(step) <= 4 and \
        min(prev['midi'], nxt['midi']) < n['midi'] < max(prev['midi'], nxt['midi'])

HELD_GAP = 0.06          # same pitch again within this silence may be the same held note

def merge_held(notes, owned):
    """A note with no syllable, at the pitch of the note it follows without a silence, is that note still sounding."""
    out_notes, out_owned = [], []
    for i, n in enumerate(notes):
        prev = out_notes[-1] if out_notes else None
        if prev is not None and not owned[i] and out_owned[-1] and n.get('midi') == prev.get('midi') and n['onset'] - prev['end'] <= HELD_GAP:
            prev.setdefault('heldParts', []).append({'t': round(n['onset'], 2), 'end': round(n['end'], 2)})
            prev['end'] = n['end']
            continue
        out_notes.append(n); out_owned.append(owned[i])
    return out_notes, out_owned

def merge_scoops(notes, owned):
    """A possible scoop joins the note it slides into when the two have one syllable between them."""
    out_notes, out_owned = [], []
    for i, n in enumerate(notes):
        # the slide and the note it lands on carry one syllable between them, whichever of the two got it
        if i + 1 < len(notes) and bool(owned[i]) != bool(owned[i + 1]) and is_scoop(notes, i):
            nxt = notes[i + 1]
            if owned[i]: owned[i + 1] = owned[i]
            nxt.setdefault('absorbedGlides', []).insert(0, {'t': round(n['onset'], 2), 'midi': n['midi'],
                                                           'seconds': round(n['end'] - n['onset'], 2), 'why': 'one syllable for the slide and its note'})
            nxt['absorbedGlides'] = n.get('absorbedGlides', []) + nxt['absorbedGlides']
            nxt['onset'] = n['onset']
            continue
        out_notes.append(n); out_owned.append(owned[i])
    return out_notes, out_owned

def align(notes, units):
    """Monotonic match of lyric units to notes. One unit may span several notes (melisma); several units may
    share one note (resolved later from the audio). Unheard reference units carry weak anchors and are cheap
    to drop, so they are never forced onto unrelated notes."""
    n, m = len(notes), len(units); INF = 1e9
    breath = [i == 0 or notes[i]['onset'] - notes[i - 1]['end'] >= BREATH for i in range(n)]
    scoop = [is_scoop(notes, i) for i in range(n)]
    for i in range(n - 1):                 # a slide that opens a line: the note it lands on is the line's first note
        if scoop[i] and breath[i]: breath[i + 1] = True
    # the same pitch struck again with no silence is usually one held note that the note reader cut in two
    held = [i > 0 and notes[i].get('midi') is not None and notes[i].get('midi') == notes[i - 1].get('midi')
            and notes[i]['onset'] - notes[i - 1]['end'] <= HELD_GAP for i in range(n)]
    def tcost(i, j):
        s = units[j]; onset = notes[i]['onset']
        if s['start'] is None: return 0.0
        c = 3.0 * max(0.0, onset - (s['end'] + 0.45), (s['start'] - 0.25) - onset) + 0.3 * max(0.0, onset - s['end'], s['start'] - onset)
        return c * (0.15 if s['weak'] else 1.0)
    def mcost(i, j):
        line = units[j]['lineStart']
        return tcost(i, j) + (1.5 if breath[i] and not line else 0.8 if line and not breath[i] else 0)
    cost = np.full((n + 1, m + 1), INF); move = np.zeros((n + 1, m + 1), dtype=int); cost[0, 0] = 0
    for i in range(n + 1):
        for j in range(m + 1):
            c = cost[i, j]
            if c >= INF: continue
            if i < n and j < m and c + mcost(i, j) < cost[i + 1, j + 1]:
                cost[i + 1, j + 1] = c + mcost(i, j); move[i + 1, j + 1] = 1          # note takes unit
            if i < n:
                k = c + (0.45 if scoop[i] else 0.7 if held[i] else 2.5 if breath[i] else 0.7)
                if k < cost[i + 1, j]: cost[i + 1, j] = k; move[i + 1, j] = 2          # melisma / wordless
            if j < m:
                k = c + (1.2 if units[j]['weak'] else 5.0)                             # unit not sung / unheard
                if i > 0:
                    dur = notes[i - 1]['end'] - notes[i - 1]['onset']
                    share = c + (0.5 if dur >= 0.9 else 1.0 if dur >= 0.6 else 2.0 if dur >= 0.4 else 4.0) + \
                        tcost(i - 1, j) + (1.5 if units[j]['lineStart'] else 0)
                    if share < k and share < cost[i, j + 1]:
                        cost[i, j + 1] = share; move[i, j + 1] = 3; continue          # unit shares previous note
                if k < cost[i, j + 1]: cost[i, j + 1] = k; move[i, j + 1] = 4
    i, j = n, m; owned = [[] for _ in notes]; dropped = []
    while i or j:
        mv = move[i, j]
        if mv == 1: owned[i - 1].insert(0, j - 1); i -= 1; j -= 1
        elif mv == 2: i -= 1
        elif mv == 3: owned[i - 1].insert(0, j - 1); j -= 1
        elif mv == 4: dropped.append(j - 1); j -= 1
        else: break
    return owned, sorted(dropped)

# ---------------------------------------------------------------- lyric-aware notes from atoms
CLEAR_EDGE = 0.60        # a pitch change across a loudness dip at least this deep starts a syllable (slides measured 0.68-1.0)
SISTER_COST = 0.5        # a syllable landing on a pitch that the same line's syllable has in no other verse
PASSING_MAX = 0.12       # a pitch this short between two notes is the voice passing through
TAIL_MAX = 0.12          # a piece this short at the end of a syllable is its release, not a note
JOIN_GAP = 0.15          # the same pitch again after a shorter silence, inside one syllable, is one held note

def atom_boundary(atoms, i):
    """What the recording shows between atom i-1 and atom i: a silence, a pitch change, or a loudness dip."""
    if i == 0: return 'silence', 9.0
    gap = atoms[i]['onset'] - atoms[i - 1]['end']
    if gap > 0.05: return 'silence', gap
    if atoms[i]['midi'] != atoms[i - 1]['midi']: return 'pitch', 0.0
    return 'dip', atoms[i].get('cut') or {'depth': 0.3, 'colour': 0.0}      # a hole in the voicing is a clear re-attack

def align_atoms(atoms, units):
    """Decide which atoms start a syllable and which continue one, for a whole section at once.
    The syllable count, the transcript times and an even-rhythm preference choose among the boundaries the
    recording offers; a boundary is never invented. Returns (notes, owned, dropped) like align()."""
    n, m = len(atoms), len(units); INF = 1e9
    if not n: return [], [], list(range(m))
    bound = [atom_boundary(atoms, i) for i in range(n)]
    breath = [b[0] == 'silence' and b[1] >= BREATH for b in bound]
    dur = [a['end'] - a['onset'] for a in atoms]
    def landing(i):                                  # atom i with every same-pitch piece that follows without a silence
        j = i
        while j + 1 < n and bound[j + 1][0] == 'dip': j += 1
        return {**atoms[i], 'end': atoms[j]['end']}
    clear = [b[0] == 'pitch' and atoms[i].get('edge', {}).get('depth', 1.0) <= CLEAR_EDGE for i, b in enumerate(bound)]
    def slides_into_next(i):
        if i + 1 >= n or clear[i + 1] or bound[i + 1][0] != 'pitch': return False
        land = landing(i + 1)
        if is_scoop(atoms[:i + 1] + [land], i): return True
        step = land['midi'] - atoms[i]['midi']; toward = atoms[i].get('glide', 0.0) * step
        # as long as the note it reaches, but the pitch is moving toward that note the whole time
        if dur[i] <= SCOOP_MAX and 1 <= abs(step) <= 2 and land['end'] - land['onset'] >= dur[i] and toward >= 0.3: return True
        # a very short pitch on the way from one note to another, whatever the interval
        return dur[i] <= PASSING_MAX and bound[i][0] == 'pitch' and \
            min(atoms[i - 1]['midi'], land['midi']) < atoms[i]['midi'] < max(atoms[i - 1]['midi'], land['midi'])
    scoop = [slides_into_next(i) for i in range(n)]
    landing_midi = [atoms[i + 1]['midi'] if scoop[i] else atoms[i]['midi'] for i in range(n)]
    for i in range(n - 1):
        if scoop[i] and breath[i]: breath[i + 1] = True
    typical = min(0.7, max(0.2, sum(dur) / max(1, m)))    # a usual syllable length in this section
    def cont(i):                                     # atom i continues the syllable before it (or is wordless)
        kind, v = bound[i]
        if kind == 'silence': return 2.5 if v >= BREATH else 1.6 if v >= 0.10 else 0.8
        if kind == 'dip': return 0.15 + 1.1 * (1 - v['depth']) + (0.3 if v['colour'] >= SOFT_COLOUR else 0)
        if scoop[i - 1]: return 0.15                 # the atom before slid into this one
        if clear[i]: return 1.1                      # the pitch changes across a clear loudness dip: a new syllable
        if dur[i] <= TAIL_MAX: return 0.3
        return 0.7 + (0.3 if dur[i] >= 0.4 else 0)
    def tcost(i, j):
        s = units[j]; onset = atoms[i]['onset']
        if s['start'] is None: return 0.0
        c = 3.0 * max(0.0, onset - (s['end'] + 0.45), (s['start'] - 0.25) - onset) + 0.3 * max(0.0, onset - s['end'], s['start'] - onset)
        return c * (0.15 if s['weak'] else 1.0)
    def take(i, j, c):                               # atom i starts syllable j; the syllable before it began c atoms back
        line = units[j]['lineStart']; kind, v = bound[i]
        k = tcost(i, j) + (1.5 if breath[i] and not line else 0.8 if line and not breath[i] else 0)
        if kind == 'dip': k += max(0.0, 0.5 * v['depth'] - (0.2 if v['colour'] >= SOFT_COLOUR else 0))
        if dur[i] < 0.10 and not scoop[i]: k += 1.0  # too short to be a syllable of its own
        want = units[j].get('expect')                # the other verses sing this syllable of the line on another pitch
        if want is not None and (landing_midi[i] - want) % 12 != 0: k += SISTER_COST
        if c and not breath[i]:                      # the syllable before would be much shorter than usual
            before = atoms[i]['onset'] - atoms[i - c]['onset']
            if before < 0.6 * typical: k += 0.8 * np.log2(0.6 * typical / max(0.03, before)) + 0.2
        return k
    C = 12
    cost = np.full((n + 1, m + 1, C + 1), INF); back = {}; cost[0, 0, 0] = 0
    for i in range(n + 1):
        for j in range(m + 1):
            for c in range(C + 1):
                v = cost[i, j, c]
                if v >= INF: continue
                if i < n and j < m:
                    k = v + take(i, j, c)
                    if k < cost[i + 1, j + 1, 1]: cost[i + 1, j + 1, 1] = k; back[i + 1, j + 1, 1] = (1, c)
                if i < n:
                    c2 = min(C, c + 1) if c else 0
                    k = v + cont(i)
                    if k < cost[i + 1, j, c2]: cost[i + 1, j, c2] = k; back[i + 1, j, c2] = (2, c)
                if j < m:
                    k = v + (1.2 if units[j]['weak'] else 5.0); mv = 4
                    if i > 0 and c:
                        d = dur[i - 1]
                        share = v + (0.8 if d >= 0.9 else 1.3 if d >= 0.6 else 2.2 if d >= 0.4 else 4.0) + \
                            tcost(i - 1, j) + (1.5 if units[j]['lineStart'] else 0)
                        want = units[j].get('expect')
                        if want is not None and (atoms[i - 1]['midi'] - want) % 12 != 0: share += SISTER_COST
                        if share < k: k = share; mv = 3
                    if k < cost[i, j + 1, c]: cost[i, j + 1, c] = k; back[i, j + 1, c] = (mv, c)
    i, j, c = n, m, int(np.argmin(cost[n, m])); own = [[] for _ in atoms]; started = [False] * n; dropped = []
    while (i, j, c) in back:
        mv, pc = back[i, j, c]
        if mv == 1: own[i - 1].insert(0, j - 1); started[i - 1] = True; i -= 1; j -= 1
        elif mv == 2: i -= 1
        elif mv == 3: own[i - 1].insert(0, j - 1); j -= 1
        else: dropped.append(j - 1); j -= 1
        c = pc
    for i in range(n - 1):                           # a slide belongs to the syllable of the note it lands on
        if scoop[i] and not started[i] and started[i + 1]:
            started[i], own[i], started[i + 1], own[i + 1] = True, own[i + 1], False, []
    # syllable groups -> notes
    groups = []
    for i, a in enumerate(atoms):
        if started[i] or not groups or bound[i][0] == 'silence' and bound[i][1] >= JOIN_GAP: groups.append([[], []])
        groups[-1][0].append({**a, 'slides': scoop[i]}); groups[-1][1] += own[i]
    notes, owned = [], []
    for members, group_units in groups:
        pieces = []
        for a in members:                            # one pitch held through dips and short holes is one piece
            if pieces and pieces[-1]['midi'] == a['midi'] and a['onset'] - pieces[-1]['end'] <= JOIN_GAP:
                p = pieces[-1]; w0, w1 = p['end'] - p['onset'], a['end'] - a['onset']
                p['median'] = round((p['median'] * w0 + a['median'] * w1) / (w0 + w1), 2); p['end'] = a['end']
                p.setdefault('heldParts', []).append({'t': round(a['onset'], 2), 'end': round(a['end'], 2)})
            else: pieces.append(a)
        k = 0
        while k + 1 < len(pieces):                   # a slide joins the note it lands on
            if pieces[k]['slides'] and pieces[k + 1]['onset'] - pieces[k]['end'] <= 0.05:
                g = pieces[k]; nxt = pieces[k + 1]
                nxt['absorbedGlides'] = g.get('absorbedGlides', []) + [{'t': round(g['onset'], 2), 'midi': g['midi'],
                                         'seconds': round(g['end'] - g['onset'], 2), 'why': 'slide into the note of the same syllable'}] + nxt.get('absorbedGlides', [])
                nxt['onset'] = g['onset']; del pieces[k]
            else: k += 1
        k = 1
        while k < len(pieces):                       # a very short piece after a longer one is its release
            p = pieces[k]; prev = pieces[k - 1]
            if p['end'] - p['onset'] <= TAIL_MAX and p['onset'] - prev['end'] <= 0.05 and prev['end'] - prev['onset'] > p['end'] - p['onset']:
                prev.setdefault('absorbedTails', []).append({'t': round(p['onset'], 2), 'midi': p['midi'], 'seconds': round(p['end'] - p['onset'], 2)})
                prev['end'] = p['end']; del pieces[k]
            else: k += 1
        for k, p in enumerate(pieces):
            for field in ('cut', 'edge', 'glide', 'slides'): p.pop(field, None)
            notes.append(p); owned.append(group_units if k == 0 else [])
    return notes, owned, sorted(dropped)

def unit_pitches(notes, owned, units):
    """Pitch of the note each lyric unit starts on, grouped by lyric line: {(verse, line): [midi or None, ...]}."""
    pitch = {}
    for n, own in zip(notes, owned):
        for u in own: pitch[u] = n['midi']
    lines = {}
    for u, unit in enumerate(units): lines.setdefault(unit['line'], []).append(pitch.get(u))
    return lines

def sister_expectations(first_pass):
    """Repeated musical phrases as evidence. For every lyric line, the pitch each syllable has in the
    other verses that sing the same line position with the same number of syllables (any language, any
    key, octaves ignored). An expectation exists only where at least two other verses agree and they are
    the clear majority; it is soft evidence for where a syllable starts and never changes a measured pitch.
    first_pass: {section id: {(verse, line): [midi, ...]}} -> {section id: {(verse, line): [pitch class or None]}}"""
    from selfcheck import distance
    ids = [k for k in first_pass if first_pass[k]]
    if len(ids) < 3: return {}
    flat = {k: [m for line in sorted(first_pass[k]) for m in first_pass[k][line] if m is not None] for k in ids}
    ref = max(ids, key=lambda k: len(flat[k]))
    shift = {k: (distance(flat[k], flat[ref])[1] if flat[k] and k != ref else 0) for k in ids}
    out = {}
    for k in ids:
        out[k] = {}
        for (verse, line), mine in first_pass[k].items():
            votes = [[] for _ in mine]
            for o in ids:
                if o == k: continue
                for (v2, l2), theirs in first_pass[o].items():
                    if l2 == line and len(theirs) == len(mine):
                        for q, m in enumerate(theirs):
                            if m is not None: votes[q].append((m + shift[o]) % 12)
            want = []
            for v in votes:
                best = max(set(v), key=v.count) if v else None
                ok = best is not None and v.count(best) >= 2 and v.count(best) >= 0.6 * len(v)
                want.append((best - shift[k]) % 12 if ok else None)
            out[k][verse, line] = want
    return out

def display(units_here, all_units):
    """Lyric text for one note: units of one word join without a space; an unfinished word ends in '-'."""
    text = ''
    for q, u in enumerate(units_here):
        unit = all_units[u]
        text += unit['text']
        last = q == len(units_here) - 1
        if not unit['wordEnd']: text += '-' if last else ''
        elif not last and unit['language'] != 'zh': text += ' '
    return text

# ---------------------------------------------------------------- acoustic splitting
def choose_cuts(expected, candidates):
    """Pair expected unit boundaries with measured attacks in order. Transcript times are rough (often
    0.3-0.5 s early), so any measured attack inside the note may be used; nearer and clearer is preferred.
    Unpaired boundaries stay unsplit."""
    B, D = len(expected), len(candidates); INF = 1e9; MISS = 0.6
    cost = np.full((B + 1, D + 1), INF); cost[0, :] = 0; back = {}
    for b in range(1, B + 1):
        for d in range(0, D + 1):
            best = cost[b - 1, d] + MISS; how = ('miss', d)
            if d > 0:                                          # boundary b takes dip d-1
                v = cost[b - 1, d - 1] + 0.5 * abs(candidates[d - 1]['t'] - expected[b - 1]) + 0.5 * candidates[d - 1]['depth']
                if v < best: best, how = v, ('take', d - 1)
            if d > 0 and cost[b, d - 1] < best: best, how = cost[b, d - 1], ('skip', d - 1)
            cost[b, d] = best; back[b, d] = how
    b, d = B, D; picks = [None] * B
    while b > 0:
        how, k = back[b, d]
        if how == 'take': picks[b - 1] = candidates[k]; b -= 1; d -= 1
        elif how == 'miss': b -= 1
        else: d -= 1
    return picks

def split_note(note, owned, units, env, spec):
    """A note that carries k > 1 lyric units is split only where the audio shows a new attack."""
    k = len(owned)
    if k <= 1: return [(note['onset'], note['end'], owned, None)]
    a, b = note['onset'], note['end']
    found = []
    for d in dips(env[0], env[1], a, b):
        d['colour'] = colour_change(spec, d['t'])
        if d['depth'] <= SPLIT_DEPTH or (d['depth'] <= SOFT_DEPTH and d['colour'] >= SOFT_COLOUR): found.append(d)
    expected = []
    for q in range(1, k):
        u = units[owned[q]]
        guess = u['start'] if (u['start'] is not None and not u['weak']) else a + (b - a) * q / k
        expected.append(min(max(guess, a + 0.07), b - 0.07))
    picks = choose_cuts(expected, found)
    pieces = []; start = a; group = [owned[0]]; attack = None
    for q in range(1, k):
        cut = picks[q - 1]
        if cut and cut['t'] - start >= MIN_PIECE and b - cut['t'] >= MIN_PIECE:
            pieces.append((start, cut['t'], group, attack)); start = cut['t']; group = [owned[q]]
            attack = {'source': 'measured attack', 't': round(cut['t'], 3), 'dipDepth': round(cut['depth'], 2),
                      'colourChange': round(cut['colour'], 3)}
        else:
            group.append(owned[q])
    pieces.append((start, b, group, attack))
    return pieces

# ---------------------------------------------------------------- sections
def snap_boundary(notes, lo, hi, fallback):
    """Widest silence between notes inside [lo, hi]; the boundary sits in its middle."""
    gaps = [(b['onset'] - a['end'], (a['end'] + b['onset']) / 2) for a, b in zip(notes, notes[1:])
            if lo <= (a['end'] + b['onset']) / 2 <= hi]
    return round(max(gaps)[1], 2) if gaps else round(fallback, 2)

def find_sections(key, spec, notes, words):
    """Verses located from the reconciled lyric anchors, plus wordless/unscripted stretches.
    Returns sections in time order, each with its reconciled tokens."""
    overrides = spec.get('sectionOverrides', {})
    sections = []
    for block in spec['blocks']:
        bnotes = [n for n in notes if block['start'] <= n['onset'] < block['end']]
        if block.get('unscripted'):
            parts = []
            for n in bnotes:
                if parts and n['onset'] - parts[-1][-1]['end'] < block['unscripted']['partGap']: parts[-1].append(n)
                else: parts.append([n])
            for k, part in enumerate(parts):
                a = round(part[0]['onset'] - 0.05, 2); b = round(part[-1]['end'] + 0.05, 2)
                sid = f"{block['id']}-{k + 1}"
                sections.append({'id': sid, 'block': block['id'], 'label': f"{block['unscripted']['label']} part {k + 1}",
                                 'language': block['language'], 'kind': 'unscripted', 'start': a, 'end': b,
                                 'tokens': unscripted_tokens(words, block, a, b),
                                 'located': block['unscripted']['reason'], 'lyricEvidence': {}})
            continue
        pieces = words['blocks'][block['id']]['pieces']
        hinted = heard_tokens([w for p in pieces for w in p['hinted']], block['language'])
        plain = heard_tokens([w for p in pieces for w in p['plain']], block['language'])
        ref = reference_tokens(block['verses'], block['language'])
        legacy = heard_tokens([w for w in words['legacy'] if block['start'] <= w['start'] < block['end']], block['language'])
        windows = {vi: (overrides[f"{block['id']}-{vi + 1}"]['start'], overrides[f"{block['id']}-{vi + 1}"]['end'])
                   for vi in range(len(block['verses'])) if 'start' in overrides.get(f"{block['id']}-{vi + 1}", {})}
        for vi in range(len(block['verses'])):
            for line, span in overrides.get(f"{block['id']}-{vi + 1}", {}).get('lines', {}).items():
                windows[vi, int(line)] = tuple(span)
        tokens = reconcile(ref, hinted, plain, legacy, windows)
        found = []
        for vi, verse in enumerate(block['verses']):
            vt = [t for t in tokens if t['verse'] == vi]
            sid = f"{block['id']}-{vi + 1}"
            ov = overrides.get(sid, {})
            anchored = [t for t in vt if t['status'] in ('heard', 'reference-spelling', 'sung-variant')]
            entry = {'id': sid, 'block': block['id'], 'label': verse['label'], 'language': block['language'],
                     'kind': ov.get('kind', 'sung'), 'tokens': vt, 'verse': vi,
                     'lyricEvidence': {s: sum(t['status'] == s for t in vt) for s in
                                       ('heard', 'reference-spelling', 'sung-variant', 'not-heard', 'extra-sung')}}
            if ov.get('absent'):
                entry.update(absent=True, reason=ov['reason']); sections.append(entry); continue
            if 'start' in ov:
                entry.update(start=ov['start'], end=ov['end'], located='song-file override: ' + ov['reason'])
            elif len(anchored) >= max(3, 0.3 * len(vt)):
                entry.update(anchorStart=min(t['start'] for t in anchored), anchorEnd=max(t['end'] for t in anchored),
                             located=f'{len(anchored)}/{len(vt)} reference words anchored by transcription')
            else:
                entry.update(absent=True, reason=f'only {len(anchored)}/{len(vt)} words anchored; not located in this recording')
                sections.append(entry); continue
            found.append(entry); sections.append(entry)
        # boundaries between consecutive located verses fall in the widest silence between them
        for idx, entry in enumerate(found):
            nxt = found[idx + 1] if idx + 1 < len(found) else None
            if idx == 0 and 'start' not in entry: entry['start'] = block['start']
            if nxt is None:
                entry.setdefault('end', block['end']); continue
            if 'start' in nxt: boundary = nxt['start']
            else:
                lo = entry.get('anchorEnd', entry.get('end', nxt['anchorStart'])) - 0.3
                boundary = snap_boundary(bnotes, lo, nxt['anchorStart'] + BOUNDARY_LATE, (lo + nxt['anchorStart']) / 2)
            entry['end'] = nxt['start'] = boundary
        # a stretch of singing in a located verse's range with no anchored word may be a wordless hook
        for entry in found:
            vnotes = [n for n in bnotes if entry['start'] <= n['onset'] < entry['end']]
            stretches = []
            for n in vnotes:
                if stretches and n['onset'] - stretches[-1][-1]['end'] < STRETCH_GAP: stretches[-1].append(n)
                else: stretches.append([n])
            lead = []
            for st in stretches:
                a, b = st[0]['onset'], st[-1]['end']
                if 'anchorStart' in entry and b < entry['anchorStart'] - 0.6: lead.append(st)
            if lead and 'anchorStart' in entry:
                split_at = snap_boundary(vnotes, lead[-1][-1]['end'] - 0.1, entry['anchorStart'] + 0.1, entry['anchorStart'] - 0.3)
                sections.append({'id': entry['id'] + '-lead', 'block': block['id'], 'label': 'Wordless lead-in before ' + entry['label'],
                                 'language': block['language'], 'kind': 'wordless', 'tokens': [], 'start': entry['start'],
                                 'end': split_at, 'located': 'singing before the first anchored word of the verse',
                                 'lyricEvidence': {}})
                entry['start'] = split_at
        # singing in the block outside every located verse
        covered = [(s['start'], s['end']) for s in sections if s.get('block') == block['id'] and not s.get('absent')]
        loose = [n for n in bnotes if not any(a <= n['onset'] < b for a, b in covered)]
        stretches = []
        for n in loose:
            if stretches and n['onset'] - stretches[-1][-1]['end'] < STRETCH_GAP: stretches[-1].append(n)
            else: stretches.append([n])
        for k, st in enumerate(stretches):
            sid = f"{block['id']}-x{k + 1}"
            ov = overrides.get(sid, {})
            sections.append({'id': sid, 'block': block['id'], 'label': ov.get('label', 'Unscripted singing'),
                             'language': block['language'], 'kind': ov.get('kind', 'unscripted'), 'tokens': [],
                             'start': round(st[0]['onset'] - 0.05, 2), 'end': round(st[-1]['end'] + 0.05, 2),
                             'located': 'singing outside the located verses', 'lyricEvidence': {}})
    for s in sections:
        ov = overrides.get(s['id'], {})
        if ov.get('exclude'): s['excluded'] = ov['exclude']
        snotes = [n for n in notes if s.get('start', 0) <= n['onset'] < s.get('end', 0)]
        # wordless stretches are charted only when they are sustained singing, not a few stray sounds
        if s['kind'] == 'wordless' and not s.get('excluded') and not ov.get('include'):
            sung = sum(n['end'] - n['onset'] for n in snotes); span = (snotes[-1]['end'] - snotes[0]['onset']) if snotes else 0
            if len(snotes) < WORDLESS_MIN_NOTES or sung < 0.5 * span:
                s['excluded'] = (f'{len(snotes)} notes covering {sung:.1f} s of {span:.1f} s: stray sounds, not a sung hook '
                                 f'(needs {WORDLESS_MIN_NOTES}+ notes covering half the stretch)')
        # a word whose transcript time lies outside its own section was matched to a neighbouring repeat;
        # its time is not evidence here, so it becomes a weak anchor between its in-section neighbours
        toks = s.get('tokens') or []
        if toks and 'start' in s and s['kind'] == 'sung':
            inside = [k for k, t in enumerate(toks) if t.get('start') is not None and s['start'] - 0.5 <= t['start'] <= s['end'] + 0.5
                      and t.get('anchor') not in ('interpolated', 'none')]
            for k, t in enumerate(toks):
                if k in inside: continue
                before = max([j for j in inside if j < k], default=None); after = min([j for j in inside if j > k], default=None)
                lo = toks[before]['end'] if before is not None else s['start']
                hi = toks[after]['start'] if after is not None else s['end']
                kb = before if before is not None else -1; ka = after if after is not None else len(toks)
                t['start'] = lo + (hi - lo) * (k - kb) / (ka - kb); t['end'] = t['start'] + 0.15
                if t['status'] != 'not-heard': t['movedFrom'] = t['status']
                t['anchor'] = 'interpolated'
        # a verse placed by the song file (transcription failed) gets its reference words spread evenly
        # over its own notes as weak anchors; the note alignment may still leave words out
        toks = s.get('tokens') or []
        if toks and snotes and s.get('located', '').startswith('song-file override'):
            a, b = snotes[0]['onset'], snotes[-1]['end']
            for k, t in enumerate(toks):
                if t['status'] in ('heard', 'reference-spelling', 'sung-variant') and a <= t.get('start', -1) <= b: continue
                t['start'] = a + (b - a) * k / len(toks); t['end'] = t['start'] + (b - a) / len(toks)
                t['anchor'] = 'section-even'
    live = sorted([s for s in sections if not s.get('absent')], key=lambda s: s['start'])
    return live, [s for s in sections if s.get('absent')]

VOCABLE = re.compile(r'^(o+h*|u+h*|a+h*|la+|da+|do+|du+|na+|m+|hm+|mm+|哦|啊|啦|呀|嗯|哼|喔|噢|呜)$', re.I)

def wordless_units(section, words, block_id, start, end):
    """Plain vocables heard in a wordless stretch ('ooh', '哦', 'la') label its notes; scat syllables such
    as 'atararara' are left unlabelled rather than spelt out."""
    pieces = words['blocks'][block_id]['pieces']
    heard = heard_tokens([w for p in pieces for w in p['plain']], section['language'])
    units = []
    for k, tok in enumerate(t for t in heard if start - 0.2 <= t['start'] < end + 0.2):
        if not VOCABLE.match(tok['text']): continue
        units.append({'text': tok['text'], 'language': section['language'], 'token': k, 'status': 'heard-vocable',
                      'start': tok['start'], 'end': tok['end'], 'weak': True, 'lineStart': False, 'wordEnd': True,
                      'line': (0, 0)})
    return units

def unscripted_tokens(words, block, start, end):
    """Lyrics for unscripted singing (no reference text): units heard by at least two passes at the same
    moment. Each is 'unscripted-heard'; single-pass words are dropped."""
    pieces = words['blocks'][block['id']]['pieces']
    passes = [heard_tokens([w for p in pieces for w in p[name]], block['language']) for name in ('hinted', 'plain')]
    passes.append(heard_tokens([w for w in words['legacy'] if start <= w['start'] < end], block['language']))
    base = [t for t in passes[1] if start - 0.2 <= t['start'] < end + 0.2]
    out = []; line = 0
    for t in base:
        support = sum(any(relation(t['text'], o['text']) in ('exact', 'homophone') and abs(o['start'] - t['start']) < 0.6
                          for o in other) for other in (passes[0], passes[2]))
        if not support: continue
        if out and t['start'] - out[-1]['end'] > 1.0: line += 1
        out.append({'text': t['text'], 'language': 'zh' if CJK.match(t['text']) else block['language'],
                    'status': 'unscripted-heard', 'start': t['start'], 'end': t['end'], 'verse': 0, 'line': line,
                    'lineStart': not out or out[-1]['line'] != line, 'wordEnd': t.get('wordEnd', True)})
    return out

# ---------------------------------------------------------------- build one song
def build(key):
    spec, spec_sha = load_spec(key)
    words, words_sha = load_words(key, spec)
    legacy_path = os.path.join(ROOT, 'docs', 'catalogue-analysis', 'words', spec['recording'] + '.json')
    words['legacy'] = json.load(open(legacy_path, encoding='utf-8'))['words']   # 2026-10-02 whole-file pass
    legacy_sha = file_sha(legacy_path)
    cache = note_cache(key)
    tune = cache['tuning']
    vocal = os.path.join(ROOT, spec['assets']['vocal']['path'])
    x16 = decode(vocal); env = envelope(x16); yin = yin_track(x16); spec_bands = band_energies(x16)
    t11, m11, v11, _ = pitch_track(decode_11k(vocal))
    raw = (t11, m11, v11)                  # unfolded builder-style pitch frames
    backing = decode(os.path.join(ROOT, spec['assets']['backing']['path']))
    playable = round(min(len(backing), len(x16)) / 16000 - 0.02, 2)
    bt, br = envelope(backing)
    audible = bt[br > max(1e-4, 0.003 * br.max())]
    natural_end = round(min(playable, float(audible[-1]) + 0.5), 2) if len(audible) else playable

    notes = absorb_glides([dict(n) for n in cache['notes']], raw, tune)
    atoms = apply_measured_note_edits(key, spec, [dict(a) for a in atom_cache(key)['atoms']])
    sections, absent = find_sections(key, spec, notes, words)
    events = []; excluded = []; dropped_units = []; issues = []
    twinkle = approved_twinkle() if key == 'twinkle' else None
    section_out = []
    # first pass: every lyric-aware section on its own, to learn what each line's syllables are sung on
    prepared = {}; first_pass = {}
    for sec in sections:
        if sec.get('excluded') or not (sec['tokens'] and sec['kind'] == 'sung' and USE_ATOMS): continue
        if twinkle and sec['id'] == 'en-1':
            first_pass[sec['id']] = {(0, k): [n['midi'] for n in twinkle['notes'] if n['phrase'] == p]
                                     for k, p in enumerate(dict.fromkeys(n['phrase'] for n in twinkle['notes']))}
            continue
        units = section_units(sec['tokens'])
        if not units: continue
        shift_anchors(units, [n for n in notes if sec['start'] <= n['onset'] < sec['end']])
        satoms = [a for a in atoms if sec['start'] <= a['onset'] < sec['end']]
        n1, o1, _ = align_atoms(satoms, units)
        prepared[sec['id']] = (units, satoms); first_pass[sec['id']] = unit_pitches(n1, o1, units)
    expectations = sister_expectations(first_pass) if USE_SISTERS else {}
    for sid, (units, satoms) in prepared.items():
        for line, want in expectations.get(sid, {}).items():
            members = [u for u in units if u['line'] == line]
            for u, w in zip(members, want): u['expect'] = w
    for sec in sections:
        snotes = [n for n in notes if sec['start'] <= n['onset'] < sec['end']]
        if sec.get('excluded'):
            excluded += [{'t': round(n['onset'], 2), 'end': round(n['end'], 2), 'midi': n['midi'], 'section': sec['id'],
                          'reason': sec['excluded']} for n in snotes]
            section_out.append({**{k: v for k, v in sec.items() if k != 'tokens'}, 'noteCount': 0}); continue
        first = len(events)
        if twinkle and sec['id'] == 'en-1':
            # the approved reference verse is copied unchanged (owner-approved by ear as close)
            for n in twinkle['notes']:
                events.append({'id': n['id'], 't': n['onset'], 'end': n['end'], 'midi': n['midi'], 'lyric': n['lyric'],
                               'section': sec['id'], 'line': f"approved-{n['phrase']}", 'source': 'approved twinkle-reference-v1'})
            sec = {**sec, 'start': twinkle['level']['melodyStart'] - 0.3, 'end': twinkle['level']['end']}
        else:
            if sec['id'] in prepared:
                units = prepared[sec['id']][0]
            elif sec['tokens']:
                units = section_units(sec['tokens'])
                shift_anchors(units, snotes)
            else:
                units = wordless_units(sec, words, sec['block'], sec['start'], sec['end'])
            if sec['tokens'] and sec['kind'] == 'sung' and units and USE_ATOMS:
                snotes, owned, dropped = align_atoms([a for a in atoms if sec['start'] <= a['onset'] < sec['end']], units)
            else:
                owned, dropped = align(snotes, units) if units else ([[] for _ in snotes], [])
                snotes, owned = merge_scoops(snotes, owned)
                snotes, owned = merge_held(snotes, owned)
            dropped_units += [{'section': sec['id'], 'text': units[d]['text'], 'status': units[d]['status'],
                               'anchor': None if units[d]['start'] is None else round(units[d]['start'], 2)} for d in dropped]
            for n, own in zip(snotes, owned):
                for a, b, group, attack in split_note(n, own, units, env, spec_bands):
                    ev = {'t': round(a, 2), 'end': round(b, 2), 'midi': n['midi'], 'median': n['median'],
                          'lyric': display(group, units) if group else '', 'section': sec['id']}
                    if group:
                        ev['line'] = '%s-%d-%d' % ((sec['id'],) + units[group[0]]['line'])
                        ev['lineStart'] = units[group[0]]['lineStart']
                        statuses = sorted({units[u]['status'] for u in group})
                        ev['lyricStatus'] = statuses[0] if len(statuses) == 1 else '+'.join(statuses)
                        if len(group) > 1: ev['sharedUnits'] = len(group)
                        want = units[group[0]].get('expect')
                        if want is not None: ev['sisterVerses'] = 'agree' if (n['midi'] - want) % 12 == 0 else 'differ'
                    if attack: ev['attack'] = attack
                    if len(own) > 1: ev['fromNote'] = round(n['onset'], 2)
                    if n.get('absorbedGlides') and a == n['onset']: ev['absorbedGlides'] = n['absorbedGlides']
                    if n.get('measuredEdits'): ev['edits'] = n['measuredEdits']
                    if n.get('heldParts') and b == n['end']: ev['heldParts'] = n['heldParts']
                    if n.get('absorbedTails') and b == n['end']: ev['absorbedTails'] = n['absorbedTails']
                    events.append(ev)
        for k in range(first, len(events)):
            ev = events[k]
            ev['id'] = ev.get('id') or f"{key}-{sec['id']}-{int(round(ev['t'] * 100)):05d}"
        section_out.append({**{k: v for k, v in sec.items() if k not in ('tokens',)},
                            'firstNote': first if len(events) > first else None,
                            'lastNote': len(events) - 1 if len(events) > first else None,
                            'noteCount': len(events) - first,
                            'review': spec.get('review', {}).get('sections', {}).get(sec['id'], 'owner-listening-pending'),
                            'lyricStatusCounts': {s: sum(t['status'] == s for t in sec['tokens']) for s in
                                                  ('heard', 'reference-spelling', 'sung-variant', 'not-heard', 'extra-sung')} if sec['tokens'] else {},
                            'variants': [{'reference': t['reference'], 'sung': t['text'], 'anchor': round(t['start'], 2)}
                                         for t in sec['tokens'] if t['status'] == 'sung-variant'] if sec['tokens'] else []})
    # notes outside every charted section are listed, never silently dropped
    in_sections = [(s['start'], s['end']) for s in section_out if s.get('noteCount')]
    listed = {x['t'] for x in excluded}
    for n in notes:
        if not any(a <= n['onset'] < b for a, b in in_sections) and round(n['onset'], 2) not in listed:
            excluded.append({'t': round(n['onset'], 2), 'end': round(n['end'], 2), 'midi': n['midi'], 'section': None,
                             'reason': 'outside every charted section (interlude, ad-lib or stem bleed); not scored'})
    events.sort(key=lambda e: e['t'])
    # ids must be unique and stable; a repeated id means two notes start in the same centisecond
    seen = {}
    for e in events:
        if e['id'] in seen: e['id'] += 'b'
        seen[e['id']] = True
    # very short blips get a singable length, never past the next note
    for a, b in zip(events, events[1:] + [None]):
        limit = b['t'] if b else a['end'] + 1
        if a['end'] - a['t'] < 0.16 and not a.get('source'):
            a['playedEnd'] = round(min(a['t'] + 0.16, limit), 2)
            a['measuredEnd'] = a['end']; a['end'] = a['playedEnd']; del a['playedEnd']
        if a['end'] > limit: a['end'] = round(limit, 2)
    apply_note_edits(key, spec, events)
    check_pitch(events, yin, raw, tune)
    phrases = make_phrases(events)
    # key and lanes from the whole chart
    hist = np.zeros(12)
    for e in events: hist[e['midi'] % 12] += e['end'] - e['t']
    scores = [np.corrcoef(np.roll(MAJOR, t), hist)[0, 1] + (0.25 if events[-1]['midi'] % 12 == t else 0) for t in range(12)]
    tonic_pc = NAMES.index(KEY_OVERRIDES[key]) if key in KEY_OVERRIDES else int(np.argmax(scores))
    if twinkle: tonic_pc = twinkle['tonicMidi'] % 12
    lo = min(e['midi'] for e in events)
    base = twinkle['tonicMidi'] if twinkle else max(b for b in range(lo - 11, lo + 1) if b % 12 == tonic_pc)
    for e in events:
        e['note'] = pitch_name(e['midi']); e['ratio'] = round(float(lane(e['midi'] - base)), 3)
    section_quality(section_out, events)
    modes = make_modes(key, spec, events, section_out, phrases, base, natural_end, twinkle)
    for s in section_out:
        for k in ('anchorStart', 'anchorEnd'):
            if k in s: s[k] = round(s[k], 2)
    return {
        'key': key, 'recording': spec['recording'], 'schema': 2, 'builder': BUILDER,
        'status': 'recording-drafted; ' + spec.get('review', {}).get('song', 'owner-listening-pending'),
        'sources': {'songFile': {'path': f'tools/chart-builder/songs/{key}.json', 'sha256': spec_sha},
                    'sectionWords': {'path': f'docs/catalogue-analysis/section-words/{key}.json', 'sha256': words_sha},
                    'wholeFileWords': {'path': 'docs/catalogue-analysis/words/' + spec['recording'] + '.json', 'sha256': legacy_sha},
                    'assets': spec['assets'], 'lyricReference': spec['lyricReference'],
                    **({'approvedTwinkle': twinkle['id']} if twinkle else {})},
        'recordingSeconds': round(cache['duration'], 2), 'playableSeconds': playable, 'naturalEnd': natural_end,
        'tuningSemitones': round(tune, 2), 'keyTonic': NAMES[tonic_pc], 'keySetByHand': key in KEY_OVERRIDES or bool(twinkle),
        'displayBaseMidi': int(base), 'sections': section_out, 'absentSections': [
            {k: v for k, v in s.items() if k not in ('tokens',)} for s in absent],
        'modes': modes, 'phrases': phrases, 'notes': events, 'excludedNotes': excluded, 'droppedLyricUnits': dropped_units,
    }

def apply_note_edits(key, spec, events):
    """Reviewed corrections from the song file. A stale locator is an error, never a guess."""
    by_id = {e['id']: e for e in events}
    for edit in spec.get('noteEdits', []):
        e = by_id.get(edit['id'])
        if e is None:
            raise StaleSource(f"{key}: note edit for {edit['id']} matches no note; the chart changed, re-review the edit")
        if edit['field'] == 'delete':
            events.remove(e); continue
        if e.get(edit['field']) != edit['old']:
            raise StaleSource(f"{key}: note {edit['id']} {edit['field']} is {e.get(edit['field'])!r}, edit expects {edit['old']!r}")
        e[edit['field']] = edit['new']
        e.setdefault('edits', []).append({k: edit[k] for k in ('field', 'old', 'new', 'reason', 'confidence', 'review') if k in edit})

def check_pitch(events, yin, raw, tune):
    """Independent second opinion per note. Labels only; never changes a pitch."""
    for e in events:
        flags = []
        med, frames, stable = interval_pitch(yin, e['t'], e.get('measuredEnd', e['end']), tune)
        e['yinMidi'] = None if med is None else round(med, 2)
        if med is None or frames < 4:
            flags.append('weak-independent-voicing')
        else:
            diff = med - e['midi']
            if abs(diff) > 0.65:
                rmed, rframes, _ = interval_pitch(raw, e['t'], e.get('measuredEnd', e['end']), tune)
                octave = int(round(diff / 12)) * 12
                if octave and abs(diff - octave) <= 0.65 and rmed is not None and abs(rmed - e['midi'] - octave) <= 0.65:
                    flags.append('octave-fold-suspect')          # both unfolded readings sit an octave away
                    e['octaveCandidate'] = e['midi'] + octave
                elif stable >= 0.6:
                    flags.append('estimators-disagree')
                else:
                    flags.append('unstable-pitch')
        if e.get('sharedUnits'): flags.append('syllables-share-note')
        if e.get('lyric') == '' and not e.get('source'): flags.append('no-lyric')
        if flags: e['flags'] = flags

PITCH_FLAGS = ('estimators-disagree', 'octave-fold-suspect', 'unstable-pitch', 'weak-independent-voicing')

def section_quality(sections, events):
    """Per section: how much of its melody the two pitch readers agree on, how jumpy it is, how much of
    its lyric is supported. 'pitch-unreliable' marks sections to listen to first (e.g. several voices)."""
    for s in sections:
        ev = [e for e in events if e['section'] == s['id']]
        if not ev: continue
        flagged = sum(bool(set(e.get('flags', [])) & set(PITCH_FLAGS)) for e in ev)
        jumps = [abs(b['midi'] - a['midi']) for a, b in zip(ev, ev[1:]) if b['t'] - a['end'] < 0.3]
        s['quality'] = {'pitchFlaggedShare': round(flagged / len(ev), 2),
                        'medianStep': float(np.median(jumps)) if jumps else 0.0,
                        'largeLeapShare': round(sum(j >= 9 for j in jumps) / max(1, len(jumps)), 2),
                        'lyricLabelledShare': round(sum(bool(e.get('lyric')) for e in ev) / len(ev), 2),
                        'sharedSyllableNotes': sum(bool(e.get('sharedUnits')) for e in ev)}
        q = s['quality']
        if q['pitchFlaggedShare'] >= 0.35 or q['largeLeapShare'] >= 0.15:
            s['qualityFlag'] = 'pitch-unreliable'
        elif q['lyricLabelledShare'] < 0.6 and s['kind'] == 'sung':
            s['qualityFlag'] = 'lyrics-sparse'

def make_phrases(events):
    """Karaoke lines: a new line where a reference lyric line starts or after a breath in wordless singing;
    lines longer than 12 notes break at their widest silence."""
    groups = []
    for i, e in enumerate(events):
        prev = events[i - 1] if i else None
        new = prev is None or prev['section'] != e['section']
        if prev and not new:
            if e.get('line') and e.get('line') != prev.get('line') and (e.get('lineStart') or str(e['line']).startswith('approved')):
                new = True
            elif e['t'] - prev['end'] >= BREATH and (not e.get('line') or len(groups[-1]) >= 6):
                new = True
        (groups.append([i]) if new else groups[-1].append(i))
    changed = True
    while changed:
        changed = False
        for gi, g in enumerate(groups):
            if len(g) > 12:
                gaps = [events[g[k]]['t'] - events[g[k - 1]]['end'] for k in range(3, len(g) - 2)]
                k = 3 + int(np.argmax(gaps)); groups[gi:gi + 1] = [g[:k], g[k:]]; changed = True; break
    for pid, g in enumerate(groups):
        for i in g: events[i]['phrase'] = pid + 1
    return [{'id': pid + 1, 'firstNote': g[0], 'lastNote': g[-1], 'section': events[g[0]]['section']} for pid, g in enumerate(groups)]

def window_for(notes, base):
    lo = min(n['midi'] for n in notes); hi = max(n['midi'] for n in notes)
    w0, w1 = lane(lo - base), lane(hi - base); pad = max(0.0, 1.0 - (w1 - w0)) / 2
    return [round(w0 - pad, 3), round(w1 + pad, 3)], hi - lo

def make_modes(key, spec, events, sections, phrases, base, natural_end, twinkle):
    def mode(first, last, level, label, choice):
        notes = events[first:last + 1]
        window, span = window_for(notes, base)
        secs = [s for s in sections if s.get('noteCount') and s['firstNote'] is not None and first <= s['firstNote'] <= last]
        langs = []
        for s in secs:
            if s['kind'] == 'sung' and s['language'] not in langs: langs.append(s['language'])
        return {'label': label, 'firstNote': first, 'lastNote': last, 'noteCount': last - first + 1,
                'level': level, 'laneWindow': window, 'rangeSemitones': span, 'languages': langs,
                'sections': [s['id'] for s in secs], 'durationSeconds': round(level['end'] - level['start'], 2),
                'phrases': [[p['firstNote'], p['lastNote']] for p in phrases if first <= p['firstNote'] <= last],
                'choice': choice}
    full_level = {'start': 0, 'melodyStart': events[0]['t'], 'melodyEnd': events[-1]['end'],
                  'fadeStart': round(max(events[-1]['end'] + 0.05, natural_end - 0.4), 2), 'end': natural_end,
                  'ending': 'recording plays to its own ending; 0.4 s guard fade'}
    if full_level['fadeStart'] >= full_level['end']: full_level['fadeStart'] = round(full_level['end'] - 0.05, 2)
    modes = {'full': mode(0, len(events) - 1, full_level, 'Full song', 'every located sung section; see sections')}
    quick = spec.get('quick') or {}
    if twinkle:
        level = dict(twinkle['level']); last = len(twinkle['notes']) - 1
        modes['quick'] = mode(0, last, level, 'Quick play', 'approved reference verse, unchanged')
        return modes
    ids = quick.get('sections')
    reason = quick.get('reason')
    if not ids:
        sung = [s for s in sections if s.get('noteCount') and s['kind'] == 'sung']
        ids = [sung[0]['id']]; k = 1
        def span(sel):
            sel_events = [e for e in events if e['section'] in sel]
            return sel_events[-1]['end'] - sel_events[0]['t']
        while span(ids) < QUICK_MIN_SPAN and k < len(sung):
            ids.append(sung[k]['id']); k += 1
        reason = (f"first sung section{'s' if len(ids) > 1 else ''} ({', '.join(ids)}): automatic rule, singing "
                  f"spanning at least {QUICK_MIN_SPAN:.0f} s")
    chosen = [s for s in sections if s['id'] in ids and s.get('noteCount')]
    first = min(s['firstNote'] for s in chosen); last = max(s['lastNote'] for s in chosen)
    t0 = events[first]['t']
    start = round(t0 - QUICK_LEAD, 2) if t0 > QUICK_TRIM_AFTER else 0
    following = events[last + 1]['t'] if last + 1 < len(events) else natural_end
    last_end = events[last]['end']
    if following - last_end >= QUICK_END_GAP:
        end = round(min(last_end + 1.4, following - 0.05, natural_end), 2)
        fade = round(min(max(last_end + 0.05, end - 0.6), end - 0.05), 2)
        ending = 'deliberate fade after the last Quick-play note'
    else:
        # the next verse follows straight on: the music fades over the held last note and stops before
        # the next verse's first sung note
        end = round(max(last_end, min(following - 0.02, natural_end)), 2)
        fade = round(max(events[last]['t'] + 0.1, end - 0.5), 2)
        ending = 'fades out over the held last note; the next verse follows straight on in the recording'
    level = {'start': start, 'fadeIn': 0.4 if start > 0 else 0, 'melodyStart': t0, 'melodyEnd': last_end,
             'fadeStart': fade, 'end': end, 'ending': ending}
    modes['quick'] = mode(first, last, level, 'Quick play', reason)
    return modes

# ---------------------------------------------------------------- main
def summary_line(c):
    f, q = c['modes']['full'], c['modes']['quick']
    flags = {}
    for n in c['notes']:
        for fl in n.get('flags', []): flags[fl] = flags.get(fl, 0) + 1
    return (f"{c['key']:13s} full {f['noteCount']:4d} notes {f['durationSeconds']:6.1f}s {'/'.join(f['languages']):9s} "
            f"quick {q['noteCount']:3d} notes {q['level']['start']:5.1f}-{q['level']['end']:5.1f}s  "
            f"sections {len([s for s in c['sections'] if s.get('noteCount')])} absent {len(c['absentSections'])} "
            f"flags {flags}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('keys', nargs='*'); ap.add_argument('--check', action='store_true')
    args = ap.parse_args()
    old = json.load(open(OUT, encoding='utf-8')) if os.path.exists(OUT) else {}
    charts = dict(old) if args.keys else {}
    if old and not all(v.get('schema') == 2 for v in old.values()): charts = {} if not args.keys else charts
    for key in SONGS:
        if args.keys and key not in args.keys: continue
        charts[key] = build(key)
        print(summary_line(charts[key]), flush=True)
    charts = {k: charts[k] for k in SONGS if k in charts}
    if args.check:
        changed = [k for k in charts if json.dumps(charts[k], sort_keys=True) != json.dumps(old.get(k), sort_keys=True)]
        for k in changed:
            a = old.get(k, {}); b = charts[k]
            print(f"CHANGED {k}: notes {len(a.get('notes', []))} -> {len(b['notes'])}")
            ai = {n['id']: n for n in a.get('notes', [])}; bi = {n['id']: n for n in b['notes']}
            gone = [i for i in ai if i not in bi]; new = [i for i in bi if i not in ai]
            moved = [i for i in bi if i in ai and json.dumps(ai[i], sort_keys=True) != json.dumps(bi[i], sort_keys=True)]
            print(f'   removed {len(gone)} added {len(new)} changed {len(moved)} ' + ' '.join((gone + new + moved)[:8]))
        print('no differences' if not changed else f'{len(changed)} chart(s) would change; nothing written (--check)')
        return
    json.dump(charts, open(OUT, 'w', encoding='utf-8', newline='\n'), ensure_ascii=False, indent=1)
    print('wrote', OUT)

if __name__ == '__main__':
    try:
        main()
    except StaleSource as error:
        sys.exit('STOPPED: ' + str(error))
