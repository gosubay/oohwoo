"""Draft a recording-based chart for every catalogue song except Twinkle.
Usage (repository root):  python tools/chart-builder/build_charts.py [song keys...]
Reads  separated/vocals/*.mp3 and docs/catalogue-analysis/words/*.json
Writes docs/catalogue-analysis/charts.json  (drafts for listening review; never owner approval)
"""
import hashlib, json, os, re, sys
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from notes_from_vocal import analyse

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT = os.path.join(ROOT, 'docs', 'catalogue-analysis')
SONGS = {  # game key -> recording name
    'brotherjohn': '2. Brother John - Two Tigers', 'humptydumpty': '3. Humpty Dumpty',
    'headshoulders': '4. Head Shoulders Knees Toes', 'londonbridge': '5. London Bridge',
    'itsybitsy': '6. Itsy Bitsy Spider', 'baabaa': '7. Baa Baa Black Sheep',
    'marylamb': '8. Mary Had A Little Lamb', 'rowboat': '9. Row Row Row Your Boat',
    'moretogether': '10. The More We Get Together', 'littlebunny': '11. Little Bunny',
    'rainrain': '12. Rain Rain Go Away', 'fingerfamily': '13. Finger Family',
    'wheelsbus': '14. Wheels On The Bus', 'oldmcdonald': '15. Old McDonald Had a Farm',
    'ifhappy': "16. If you're happy and you know it", 'fivemonkeys': '17. 5 Little Monkeys',
    'babyshark': '18. Baby Shark', 'baluobo': '19. Ba Luo Bo', 'xiaoyanzi': '20. Xiao Yan Zi - Little Bird',
    'rasasayang': '21. Rasa Sayang', 'chanmalichan': '22. Chan Mali Chan',
}
NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
SCALE = [0, 2, 4, 5, 7, 9, 11, 12]; LANES = [0, .14, .29, .43, .57, .71, .86, 1]
MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
# Tonic/dominant ties the estimate got wrong, settled from the melody's shape (still to be confirmed by ear).
KEY_OVERRIDES = {'headshoulders': 'C', 'xiaoyanzi': 'A', 'fingerfamily': 'A'}
MIN_EXCERPT, TARGET_MIN, MAX_EXCERPT, INTERLUDE = 15.0, 24.0, 45.0, 2.5   # seconds of singing

def pitch_name(m): return NAMES[m % 12] + str(m // 12 - 1)

def lane(semitones):                      # same mapping as pitchLane() in the game
    octave = int(np.floor(semitones / 12)); local = semitones - octave * 12; i = 0
    while i < 6 and local > SCALE[i + 1]: i += 1
    return octave + LANES[i] + (local - SCALE[i]) / (SCALE[i + 1] - SCALE[i]) * (LANES[i + 1] - LANES[i])

try:
    from opencc import OpenCC
    T2S = OpenCC('t2s')                    # show Chinese lyrics in simplified characters
except Exception:
    T2S = None
VOCALISE = re.compile(r'^(o+h*|u+h*|a+h*|la+|da+|do+|na+|m+|hm+|)$', re.I)
CJK = re.compile(r'[㐀-鿿]')
def syllables(word):
    """Split one transcribed word into singable chunks (rough, for lyric display only)."""
    w = word.strip()
    if CJK.search(w): return [c for c in w if CJK.match(c)]
    core = re.sub(r"[^A-Za-z'\-]", '', w.replace('’', "'"))
    if not re.search(r'[A-Za-z]', core): return []
    parts = []
    for piece in [p for p in core.split('-') if p]:
        low = piece.lower()
        groups = [m.span() for m in re.finditer(r"[aeiouy]+", low)]
        if len(groups) > 1 and low.endswith('e') and not low.endswith(('le', 'ee', 'ye')) and groups[-1] == (len(low) - 1, len(low)):
            groups.pop()                                   # silent final e
        if len(groups) > 1 and low.endswith('ed') and low[-3] not in 'td' and groups[-1][1] == len(low) - 1:
            groups.pop()                                   # "jumped" is one syllable
        if len(groups) <= 1: parts.append(piece); continue
        cuts = []
        for (a0, a1), (b0, b1) in zip(groups, groups[1:]):
            cuts.append(a1 + (0 if b0 - a1 <= 1 else 1))    # consonants between two vowel groups
        edges = [0] + cuts + [len(piece)]
        chunk = [piece[a:b] for a, b in zip(edges, edges[1:]) if piece[a:b]]
        parts += [c + '-' for c in chunk[:-1]] + [chunk[-1]]
    return parts

def lyric_events(words):
    """Whisper words -> syllables with a rough time each. Sub-word fragments are rejoined.
    lineStart marks where the transcription begins a new line (new segment, after punctuation,
    or a capital letter when the transcript is not written in Title Case)."""
    joined = []
    for w in words:
        text = w['word']
        latin = re.sub(r"[^A-Za-z]", '', text)
        if joined and joined[-1]['glue']:
            joined[-1]['word'] += text.lstrip('-'); joined[-1]['end'] = w['end']
            joined[-1]['glue'] = False; continue
        joined.append({**w, 'glue': bool(latin) and not re.search(r'[aeiouyAEIOUY]', latin) and len(latin) <= 3 and not CJK.search(text)})
    latin_words = [w['word'] for w in joined if re.match(r"[A-Za-z]", w['word'])]
    caps_mean_lines = bool(latin_words) and sum(w[0].isupper() for w in latin_words) / len(latin_words) < 0.45
    out = []
    for k, w in enumerate(joined):
        prev = joined[k - 1] if k else None
        line = (prev is None or prev['segment'] != w['segment'] or prev['word'][-1:] in ',.!?;，。！？' or
                (caps_mean_lines and w['word'][:1].isupper() and w['word'] not in ('I', "I'm", "I'll")))
        parts = syllables(w['word'])
        for q, part in enumerate(parts):
            span = (w['end'] - w['start']) / len(parts)
            out.append({'text': (T2S.convert(part) if T2S else part) + ('' if q < len(parts) - 1 else ' '), 'start': w['start'] + span * q,
                        'end': w['start'] + span * (q + 1), 'lineStart': line and q == 0})
    return out

def align(notes, syls):
    """Monotonic match of syllables to notes. One syllable may span several notes (melisma);
    two syllables may share one held note (the note is then split). Breaths in the singing
    are encouraged to coincide with line starts in the transcription."""
    n, m = len(notes), len(syls); INF = 1e9
    breath = [i == 0 or notes[i]['onset'] - notes[i - 1]['end'] >= 0.45 for i in range(n)]
    def tcost(i, j):
        s = syls[j]; onset = notes[i]['onset']
        return 3.0 * max(0.0, onset - (s['end'] + 0.45), (s['start'] - 0.25) - onset) +                0.3 * max(0.0, onset - s['end'], s['start'] - onset)
    def mcost(i, j):
        line = syls[j]['lineStart']
        return tcost(i, j) + (1.5 if breath[i] and not line else 0.8 if line and not breath[i] else 0)
    cost = np.full((n + 1, m + 1), INF); move = np.zeros((n + 1, m + 1), dtype=int); cost[0, 0] = 0
    for i in range(n + 1):
        for j in range(m + 1):
            c = cost[i, j]
            if c >= INF: continue
            if i < n and j < m and c + mcost(i, j) < cost[i + 1, j + 1]:
                cost[i + 1, j + 1] = c + mcost(i, j); move[i + 1, j + 1] = 1          # note takes syllable
            if i < n:
                k = c + (2.5 if breath[i] else 0.7)
                if k < cost[i + 1, j]: cost[i + 1, j] = k; move[i + 1, j] = 2          # note continues syllable / wordless
            if j < m:
                k = c + 5.0                                                            # syllable not sung / misheard
                if i > 0:
                    dur = notes[i - 1]['end'] - notes[i - 1]['onset']
                    share = c + (0.5 if dur >= 0.9 else 1.0 if dur >= 0.6 else 2.0 if dur >= 0.4 else 4.0) + tcost(i - 1, j) + (1.5 if syls[j]['lineStart'] else 0)
                    if share < k and share < cost[i, j + 1]:
                        cost[i, j + 1] = share; move[i, j + 1] = 3; continue          # syllable shares previous note
                if k < cost[i, j + 1]: cost[i, j + 1] = k; move[i, j + 1] = 4
    i, j = n, m; text = [[] for _ in notes]
    while i or j:
        mv = move[i, j]
        if mv == 1: text[i - 1].insert(0, syls[j - 1]['text']); i -= 1; j -= 1
        elif mv == 2: i -= 1
        elif mv == 3: text[i - 1].insert(0, syls[j - 1]['text']); j -= 1
        elif mv == 4: j -= 1
        else: break
    return text

def build(key, name):
    vocal = os.path.join(ROOT, 'separated', 'vocals', name + '.mp3')
    result = analyse(vocal)
    words = json.load(open(os.path.join(OUT, 'words', name + '.json'), encoding='utf-8'))
    allnotes = result['notes']; ws = words['words']
    # wordless warm-ups ("ooh", "la da da") before the first real lyric are introduction, not chart
    while ws and not CJK.search(ws[0]['word']) and VOCALISE.match(re.sub(r"[^A-Za-z]", '', ws[0]['word'])): ws = ws[1:]
    # singing starts with the first transcribed word; wordless sounds before it are not charted
    start = ws[0]['start'] - 0.6 if ws else 0
    notes = [n for n in allnotes if n['onset'] >= start]
    first = notes[0]['onset']
    syls_all = lyric_events(ws)
    def has_words(a, b):                          # any transcribed syllable inside this stretch of singing
        return any(s['end'] > a - 0.3 and s['start'] < b + 0.3 for s in syls_all)
    # breaths split the singing into stretches; the excerpt is a run of whole stretches
    stretches = [[notes[0]]]
    for a, b in zip(notes, notes[1:]):
        (stretches.append([b]) if b['onset'] - a['end'] >= 0.45 else stretches[-1].append(b))
    cut = None; best = None
    for k, st in enumerate(stretches[:-1]):
        end = st[-1]['end']; gap = stretches[k + 1][0]['onset'] - end; sung = end - first
        nxt = stretches[k + 1]
        so_far = np.median([n['midi'] for g in stretches[:k + 1] for n in g])
        other_voice = abs(np.median([n['midi'] for n in nxt]) - so_far) >= 7
        if sung >= MIN_EXCERPT and (gap >= INTERLUDE or other_voice or not has_words(nxt[0]['onset'], nxt[-1]['end'])):
            cut = end; break                      # interlude, a different singer's register, or wordless humming follows
        if sung > MAX_EXCERPT: break
        if sung >= TARGET_MIN and (best is None or gap > best[0]): best = (gap, end)
    if cut is None: cut = best[1] if best else notes[-1]['end']
    notes = [dict(n) for n in notes if n['end'] <= cut + 1e-6]
    following = [n['onset'] for n in allnotes if n['onset'] > cut]
    syls = [s for s in syls_all if s['end'] < cut + 0.35]
    text = align(notes, syls)
    # a lone note an octave away from both neighbours in its line is a detection slip, not a leap
    for k, nte in enumerate(notes):
        near = [o['midi'] for o in (notes[k - 1] if k else None, notes[k + 1] if k + 1 < len(notes) else None)
                if o and abs(o['onset'] - nte['onset']) < 1.5]
        if not near: continue
        worst = max(abs(nte['midi'] - m) for m in near)
        if worst < 9: continue
        for shift in (12, -12):
            if max(abs(nte['midi'] + shift - m) for m in near) <= worst - 6:
                nte['midi'] += shift; nte['median'] += shift; nte['octaveCorrected'] = True; break
    # a wordless continuation on the same pitch is one held note, not a new one
    k = 1
    while k < len(notes):
        if not text[k] and notes[k]['midi'] == notes[k - 1]['midi'] and notes[k]['onset'] - notes[k - 1]['end'] < 0.06:
            notes[k - 1]['end'] = notes[k]['end']; notes[k - 1]['frames'] += notes[k]['frames']; del notes[k]; del text[k]
        else: k += 1
    # split a held note that carries more than one syllable
    final = []
    for nte, t in zip(notes, text):
        k = len(t)
        if k <= 1 or (nte['end'] - nte['onset']) / k < 0.14:
            final.append({**nte, 'lyric': ''.join(t).strip()}); continue
        step = (nte['end'] - nte['onset']) / k
        for q in range(k):
            final.append({**nte, 'onset': nte['onset'] + step * q, 'end': nte['onset'] + step * (q + 1) - (0.04 if q < k - 1 else 0),
                          'lyric': t[q].strip(), 'split': True})
    # phrases: a breath of 0.45 s or more starts a new line; long lines break at their widest gap
    groups = [[0]]
    for i in range(1, len(final)):
        (groups.append([i]) if final[i]['onset'] - final[i - 1]['end'] >= 0.45 else groups[-1].append(i))
    changed = True
    while changed:
        changed = False
        for gi, g in enumerate(groups):
            if len(g) > 12:
                gaps = [final[g[k]]['onset'] - final[g[k - 1]]['end'] for k in range(3, len(g) - 2)]
                k = 3 + int(np.argmax(gaps)); groups[gi:gi + 1] = [g[:k], g[k:]]; changed = True; break
    # key: duration-weighted pitch classes of the excerpt against a major-key profile, nudged
    # toward the excerpt's final note. Only used for Do-Re-Mi labels and lane spacing.
    hist = np.zeros(12)
    for nte in final: hist[nte['midi'] % 12] += nte['end'] - nte['onset']
    scores = [np.corrcoef(np.roll(MAJOR, t), hist)[0, 1] + (0.25 if final[-1]['midi'] % 12 == t else 0) for t in range(12)]
    tonic_pc = NAMES.index(KEY_OVERRIDES[key]) if key in KEY_OVERRIDES else int(np.argmax(scores))
    lo = min(n['midi'] for n in final); hi = max(n['midi'] for n in final)
    base = max(b for b in range(lo - 11, lo + 1) if b % 12 == tonic_pc)      # "Do" at or just below the lowest note
    # screen window in lane units: the whole melody is visible, never less than one octave tall
    w0, w1 = lane(lo - base), lane(hi - base)
    pad = max(0.0, 1.0 - (w1 - w0)) / 2
    window = [round(w0 - pad, 3), round(w1 + pad, 3)]
    out = []
    for gi, g in enumerate(groups):
        for i in g:
            nte = final[i]
            out.append({'t': round(nte['onset'], 2), 'end': round(nte['end'], 2), 'midi': nte['midi'], 'note': pitch_name(nte['midi']),
                        'ratio': round(float(lane(nte['midi'] - base)), 3), 'lyric': nte['lyric'], 'phrase': gi + 1,
                        'median': round(nte['median'], 2), 'frames': nte['frames'], **({'split': True} if nte.get('split') else {}),
                        **({'octaveCorrected': True} if nte.get('octaveCorrected') else {})})
    for a, b in zip(out, out[1:] + [None]):
        limit = b['t'] if b else a['end'] + 1
        a['end'] = round(min(max(a['end'], a['t'] + 0.16), limit), 2)   # very short blips get a singable length
    end = out[-1]['end']
    fade_end = round(min(end + 1.4, (following[0] - 0.05) if following else result['duration'], result['duration']), 2)
    fade_start = round(max(end + 0.05, fade_end - 0.6), 2)
    sha = lambda p: hashlib.sha256(open(os.path.join(ROOT, p), 'rb').read()).hexdigest()
    return {
        'key': key, 'recording': name, 'status': 'recording-drafted; owner-listening-pending',
        'assets': [{'role': r, 'path': p, 'sha256': sha(p)} for r, p in
                   (('backing', f'audio/{name}.mp3'), ('vocal', f'separated/vocals/{name}.mp3'))],
        'language': words['language'], 'recordingSeconds': round(result['duration'], 2),
        'tuningSemitones': round(result['tuning'], 2), 'keyTonic': NAMES[tonic_pc], 'keySetByHand': key in KEY_OVERRIDES,
        'displayBaseMidi': int(base), 'laneWindow': window, 'rangeSemitones': hi - lo,
        'level': {'start': 0, 'melodyStart': out[0]['t'], 'melodyEnd': end, 'fadeStart': fade_start, 'end': fade_end},
        'phrases': [{'id': gi + 1, 'firstNote': g[0], 'lastNote': g[-1]} for gi, g in enumerate(groups)],
        'notes': out,
    }

if __name__ == '__main__':
    only = sys.argv[1:]
    path = os.path.join(OUT, 'charts.json')
    charts = json.load(open(path, encoding='utf-8')) if os.path.exists(path) and only else {}
    for key, name in SONGS.items():
        if only and key not in only: continue
        c = build(key, name); charts[key] = c
        lv = c['level']
        print(f"{key:14s} {len(c['notes']):3d} notes {len(c['phrases']):2d} lines  {lv['melodyStart']:6.2f}-{lv['melodyEnd']:6.2f}s of {c['recordingSeconds']:5.0f}s  "
              f"key {c['keyTonic']:2s}{'*' if c['keySetByHand'] else ' '} range {c['rangeSemitones']:2d} st base {pitch_name(c['displayBaseMidi'])} "
              f"window {c['laneWindow']} tuning {c['tuningSemitones']:+.2f} lyricless {sum(1 for n in c['notes'] if not n['lyric'])}", flush=True)
    json.dump(charts, open(path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
