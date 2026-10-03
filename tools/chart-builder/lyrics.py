"""Language-aware lyric units and reconciliation of reference lyrics with what Whisper heard.

Units: Mandarin = one character; English = rough written syllables; Malay = Malay syllables (CV(C), with
y/w consonants, ng/ny/sy/kh/gh single consonants, vowel hiatus split: di-a, bu-ah; ai/au/oi diphthongs only
word-finally). These are lyric labels. Musical notes are measured separately; one unit may span several
notes and several units may share one note.

Reconciliation compares each reference unit with three transcripts of the same singing: 'hinted' (given
the reference as a prompt), 'plain' (language forced, no prompt) and 'legacy' (2026-10-02 whole-file pass,
automatic language, no prompt). Per word, one heard time is kept so that times run in order and words of
one lyric line stay close together (stops a repeated phrase sliding onto the wrong repeat). Statuses:
  heard               an unprompted pass agrees (exactly, or as a homophone / near-identical spelling)
  reference-spelling  only the prompted pass agrees; the unprompted passes heard something else or nothing
  sung-variant        the prompted and an unprompted pass agree on a different, non-homophone word: the
                      recording is followed and the reference word is kept beside it
  not-heard           no pass supports it; kept only as a weak candidate that the note alignment may drop
Extra words heard by the prompted and an unprompted pass but absent from the reference are 'extra-sung'.
"""
import re
from difflib import SequenceMatcher

try:
    from opencc import OpenCC
    _T2S = OpenCC('t2s')
except Exception:                     # display falls back to the transcript's characters
    _T2S = None
from pypinyin import lazy_pinyin

CJK = re.compile(r'[㐀-鿿]')
LATIN_WORD = re.compile(r"[A-Za-z][A-Za-z'’\-]*")

def simplified(text):
    return _T2S.convert(text) if _T2S else text

# ---------------------------------------------------------------- syllables
# Catalogue words the spelling rule below splits wrongly (checked against the reference lyrics list).
EN_SYLLABLES = {
    'another': 'a-noth-er', 'brother': 'broth-er', 'crocodile': 'croc-o-dile', 'diamond': 'di-a-mond',
    'dumpty': 'dump-ty', 'humpty': 'hump-ty', 'everywhere': 'ev-ery-where', 'grandma': 'grand-ma',
    'grandmother': 'grand-moth-er', 'grandpa': 'grand-pa', 'happier': 'hap-pi-er', 'lives': 'lives',
    'machinery': 'ma-chin-ery', 'people': 'peo-ple', 'prettiest': 'pret-ti-est', 'quickly': 'quick-ly',
    'rule': 'rule', 'surely': 'sure-ly', 'together': 'to-geth-er', "where's": "where's", 'flowers': 'flow-ers',
    'showers': 'show-ers', 'coming': 'com-ing', 'ringing': 'ring-ing', 'falling': 'fall-ing',
    'morning': 'morn-ing', 'sleeping': 'sleep-ing', 'jumping': 'jump-ing', 'greeting': 'greet-ing',
    'darling': 'dar-ling', 'factory': 'fac-to-ry', 'family': 'fam-i-ly', 'beautiful': 'beau-ti-ful',
    'indefinitely': 'in-def-i-nite-ly', 'gently': 'gent-ly', 'hooray': 'hoo-ray', 'hurray': 'hur-ray',
    'donald': 'don-ald', 'macdonald': 'mac-don-ald', 'iron': 'i-ron', 'banyan': 'ban-yan',
}

def english_syllables(word):
    """Rough written syllables of an English word (display only)."""
    core = re.sub(r"[^A-Za-z'\-]", '', word.replace('’', "'"))
    if not re.search(r'[A-Za-z]', core): return []
    known = EN_SYLLABLES.get(core.lower())
    if known:                                              # keep the sung word's own capitalisation
        out, k = [], 0
        for part in known.split('-'):
            out.append(core[k:k + len(part)]); k += len(part)
        return out
    parts = []
    for piece in [p for p in core.split('-') if p]:
        low = piece.lower()
        groups = [m.span() for m in re.finditer(r"[aeiouy]+", low)]
        if len(groups) > 1 and low.endswith('e') and not low.endswith(('le', 'ee', 'ye')) and groups[-1] == (len(low) - 1, len(low)):
            groups.pop()                                   # silent final e
        if len(groups) > 1 and low.endswith('ed') and low[-3] not in 'td' and groups[-1][1] == len(low) - 1:
            groups.pop()                                   # "jumped" is one syllable
        if len(groups) <= 1: parts.append(piece); continue
        cuts = [a1 + (0 if b0 - a1 <= 1 else 1) for (a0, a1), (b0, b1) in zip(groups, groups[1:])]
        edges = [0] + cuts + [len(piece)]
        parts += [piece[a:b] for a, b in zip(edges, edges[1:]) if piece[a:b]]
    return parts

MALAY_DIGRAPHS = ('ng', 'ny', 'sy', 'kh', 'gh')
MALAY_VOWELS = 'aeiou'

def malay_syllables(word):
    """Malay syllables: sa-yang, sa-ya, di-a, bu-ah, ke-ti-pung, pa-yung, kam-bing, ba-gai."""
    w = re.sub(r"[^A-Za-z]", '', word)
    if not w: return []
    low = w.lower()
    # consonant units, so digraphs never split
    units = []; i = 0
    while i < len(low):
        if low[i:i + 2] in MALAY_DIGRAPHS: units.append((i, i + 2)); i += 2
        else: units.append((i, i + 1)); i += 1
    vowel = [low[a:b] in MALAY_VOWELS for a, b in units]
    nuclei = []                                            # index ranges of units forming each nucleus
    k = 0
    while k < len(units):
        if vowel[k]:
            end = k + 1
            pair = low[units[k][0]] + (low[units[k + 1][0]] if k + 1 < len(units) and vowel[k + 1] else '')
            if pair in ('ai', 'au', 'oi') and k + 2 == len(units):
                end = k + 2                                # word-final diphthong: ba-gai, pu-lau, am-boi
            nuclei.append((k, end)); k = end
        else: k += 1
    if len(nuclei) <= 1: return [w]
    cuts = []
    for (a0, a1), (b0, b1) in zip(nuclei, nuclei[1:]):
        between = b0 - a1                                  # consonant units between two nuclei
        cut_unit = a1 if between == 0 else (b0 - 1 if between == 1 else a1 + 1)
        cuts.append(units[cut_unit][0])
    edges = [0] + cuts + [len(w)]
    return [w[a:b] for a, b in zip(edges, edges[1:])]

def units_of(word, language):
    """Lyric units of one written word in a given language."""
    if CJK.search(word):
        return [simplified(c) for c in word if CJK.match(c)]
    return malay_syllables(word) if language == 'ms' else english_syllables(word)

# ---------------------------------------------------------------- comparison
def _latin_key(word):
    return re.sub(r"[^a-z0-9]", '', word.lower().replace('’', "'"))

_SOUND = str.maketrans({'b': 'p', 'd': 't', 'g': 'k', 'v': 'f', 'z': 's', 'c': 'k', 'q': 'k'})

def _skeleton(a):
    """Consonant outline of a Latin syllable: voicing merged, h dropped, doubles collapsed."""
    out = ''
    for ch in a.translate(_SOUND):
        if ch in 'aeiouh': continue
        if not out or out[-1] != ch: out += ch
    return out

def _latin_similar(a, b):
    """Spellings of the same sung sound: beep/peep, dikubas/dikupas, payung/peyang, do/doo, oi/hoi."""
    if a == b: return True
    if not a or not b: return False
    if a.translate(_SOUND) == b.translate(_SOUND): return True
    ka, kb = _skeleton(a), _skeleton(b)
    if ka == kb and (ka or a.lstrip('h')[:1] == b.lstrip('h')[:1]): return True
    return max(len(a), len(b)) >= 4 and SequenceMatcher(None, a, b).ratio() >= 0.8

def _pinyin(char):
    return lazy_pinyin(char)[0] if char else ''

def relation(ref, heard):
    """'exact', 'homophone' (or near-identical spelling) or 'different'."""
    if CJK.match(ref or '') or CJK.match(heard or ''):
        a, b = simplified(ref), simplified(heard)
        if a == b: return 'exact'
        return 'homophone' if CJK.match(a) and CJK.match(b) and _pinyin(a) == _pinyin(b) else 'different'
    a, b = _latin_key(ref), _latin_key(heard)
    if a == b: return 'exact'
    return 'homophone' if _latin_similar(a, b) else 'different'

# ---------------------------------------------------------------- tokens
HALLUCINATIONS = ('请不吝点赞订阅转发打赏支持明镜与点点栏目', '中文字幕由Amara.org社群提供', '字幕由Amara', '词曲李宗盛',
                  '作词李宗盛', '作曲李宗盛', '优优独播剧场', 'YoYoTelevisionSeriesExclusive', 'Thankyou', '감사합니다',
                  'TekstingavNicolaiWinther', '明镜与点点栏目', 'Amara.org')

def drop_hallucinations(words):
    """Remove Whisper's well-known stock phrases (channel credits, 'Thank you.', subtitle credits) that it
    produces over music or silence. Matching is on the joined text, so split characters are caught too."""
    keep = [True] * len(words)
    texts = [re.sub(r'\s+', '', simplified(w['word'])) for w in words]
    for phrase in HALLUCINATIONS:
        target = simplified(phrase)
        for i in range(len(words)):
            acc = ''
            for j in range(i, min(len(words), i + 40)):
                acc += re.sub(r'[^\w.]', '', texts[j])
                if not target.startswith(acc[:len(target)]) and not acc.startswith(target): break
                if acc.startswith(target) or (len(acc) >= 6 and target.startswith(acc) and j + 1 == len(words)):
                    for k in range(i, j + 1): keep[k] = False
                    break
    return [w for w, k in zip(words, keep) if k]

def _latin_units(word, language):
    """Syllable units of one written Latin word; hyphens and inner capitals (MacDonald) separate words."""
    out = []
    for part in re.split(r"[-\s]+|(?<=[a-z])(?=[A-Z])", word):
        if not re.search(r'[A-Za-z]', part): continue
        sy = malay_syllables(part) if language == 'ms' else english_syllables(part)
        out.append(sy or [part])
    return out

def reference_tokens(verses, language):
    """verses: [{'label', 'lines': [...]}] -> lyric units (Mandarin characters, Latin syllables) with
    verse/line position and word boundaries."""
    out = []
    for vi, verse in enumerate(verses):
        for li, line in enumerate(verse['lines']):
            first = True
            for m in re.finditer(r"[㐀-鿿]|[A-Za-z][A-Za-z'’\-]*", line):
                word = m.group(0)
                if CJK.match(word):
                    out.append({'text': simplified(word), 'language': 'zh', 'verse': vi, 'line': li,
                                'lineStart': first, 'wordEnd': True})
                    first = False; continue
                lang = 'ms' if language == 'ms' else 'en'
                for syl in _latin_units(word, lang):
                    for q, unit in enumerate(syl):
                        out.append({'text': unit, 'language': lang, 'verse': vi, 'line': li,
                                    'lineStart': first, 'wordEnd': q == len(syl) - 1})
                        first = False
    return out

def heard_tokens(words, language):
    """Whisper words -> units on the same scale as reference tokens, each with a rough time."""
    out = []
    for w in drop_hallucinations(words):
        pieces = re.findall(r"[㐀-鿿]|[A-Za-z][A-Za-z'’]*", w['word'])
        if not pieces: continue
        # Whisper sometimes splits one Latin word ("Tw inkle"); rejoin fragments without vowels
        if out and not CJK.match(pieces[0]) and out[-1].get('word') and not w['word'].startswith((' ', '-')) and \
                out[-1]['end'] >= w['start'] - 0.02 and not re.search(r'[aeiouy]', out[-1]['word'].lower()):
            prev = out.pop(); pieces[0] = prev['word'] + pieces[0]; w = {**w, 'start': prev['start']}
        units = []
        for piece in pieces:
            if CJK.match(piece): units.append((simplified(piece), True, None))
            else:
                for syl in _latin_units(piece, language):
                    for q, unit in enumerate(syl): units.append((unit, q == len(syl) - 1, piece))
        span = (w['end'] - w['start']) / len(units)
        for q, (unit, word_end, word) in enumerate(units):
            out.append({'text': unit, 'start': w['start'] + span * q, 'end': w['start'] + span * (q + 1),
                        'p': w.get('p', 1.0), 'wordEnd': word_end, **({'word': word} if word and len(units) == 1 else {})})
    return out

def align_tokens(ref, heard):
    """Monotonic text alignment. Returns a list of (ref index or None, heard index or None, relation).
    Timing is checked afterwards by _chain(); text alone can slide onto the wrong repeat of a phrase."""
    n, m = len(ref), len(heard)
    GAP_REF, GAP_HEARD = 0.8, 0.8
    cost = [[0.0] * (m + 1) for _ in range(n + 1)]; move = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1): cost[i][0] = i * GAP_REF; move[i][0] = 2
    for j in range(1, m + 1): cost[0][j] = j * GAP_HEARD; move[0][j] = 3
    rel = {}
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            r = relation(ref[i - 1]['text'], heard[j - 1]['text']); rel[i, j] = r
            sub = cost[i - 1][j - 1] + (0 if r == 'exact' else 0.3 if r == 'homophone' else 1.0)
            best, mv = sub, 1
            if cost[i - 1][j] + GAP_REF < best: best, mv = cost[i - 1][j] + GAP_REF, 2
            if cost[i][j - 1] + GAP_HEARD < best: best, mv = cost[i][j - 1] + GAP_HEARD, 3
            cost[i][j] = best; move[i][j] = mv
    out = []; i, j = n, m
    while i or j:
        mv = move[i][j]
        if mv == 1: out.append((i - 1, j - 1, rel[i, j])); i -= 1; j -= 1
        elif mv == 2: out.append((i - 1, None, None)); i -= 1
        else: out.append((None, j - 1, None)); j -= 1
    return out[::-1]

def _options(ref, passes, windows=None):
    """Per reference token: every pass that heard it (exactly or as a homophone), with its time.
    windows: {verse index: (start, end)} or {(verse, line): (start, end)} placed by the song file;
    heard words outside a placed window cannot belong to that verse or line."""
    opts = [[] for _ in ref]; subs = [[] for _ in ref]; extras = {}
    def allowed(ri, tok):
        for w in ((windows or {}).get(ref[ri]['verse']), (windows or {}).get((ref[ri]['verse'], ref[ri]['line']))):
            if w is not None and not (w[0] - 0.5 <= tok['start'] <= w[1] + 0.5): return False
        return True
    for name, heard in passes.items():
        last_ref = -1
        for ri, hi, r in align_tokens(ref, heard):
            if ri is not None:
                last_ref = ri
                if hi is None or not allowed(ri, heard[hi]): continue
                if r in ('exact', 'homophone'): opts[ri].append({'pass': name, 'tok': heard[hi], 'rel': r})
                else: subs[ri].append({'pass': name, 'tok': heard[hi]})
            elif hi is not None:
                extras.setdefault(name, []).append((last_ref, heard[hi]))
    # a different word that the hinted pass and an unprompted pass agree on, at the same moment
    for ri, cands in enumerate(subs):
        if opts[ri]: continue
        for a in cands:
            for b in cands:
                if a['pass'] == 'hinted' and b['pass'] != 'hinted' and abs(a['tok']['start'] - b['tok']['start']) < 1.2 and \
                        relation(a['tok']['text'], b['tok']['text']) in ('exact', 'homophone') and min(a['tok']['p'], b['tok']['p']) >= 0.4:
                    if not any(o['rel'] == 'variant' for o in opts[ri]):
                        opts[ri].append({'pass': b['pass'], 'tok': {**b['tok'], 'text': a['tok']['text']}, 'rel': 'variant'})
    return opts, subs, extras

def _chain(ref, opts, lookback=60):
    """Choose at most one heard time per reference token so that times run in order and words of one
    lyric line stay close together. Maximises supported tokens (unprompted evidence slightly preferred)."""
    order = sorted((i, k) for i, o in enumerate(opts) for k in range(len(o)))
    best = {}; back = {}
    def ok(j, kj, i, ki):
        tj = opts[j][kj]['tok']['start']; ti = opts[i][ki]['tok']['start']
        if ti < tj - 0.25: return False
        same_verse = ref[i]['verse'] == ref[j]['verse']
        if same_verse and ref[i]['line'] == ref[j]['line']: return ti - tj <= 2.5 * (i - j) + 0.5
        if same_verse: return ti - tj <= 2.5 * (i - j) + 3.0
        return True
    for idx, (i, k) in enumerate(order):
        o = opts[i][k]
        gain = 1.0 + (0.2 if o['pass'] != 'hinted' else 0) - (0.3 if o['rel'] == 'variant' else 0)
        best[i, k] = gain; back[i, k] = None
        for jdx in range(idx - 1, -1, -1):
            j, kj = order[jdx]
            if j == i: continue
            if i - j > lookback: break
            if best[j, kj] + gain > best[i, k] and ok(j, kj, i, k):
                best[i, k] = best[j, kj] + gain; back[i, k] = (j, kj)
    if not best: return {}
    node = max(best, key=lambda n: best[n]); chosen = {}
    while node:
        chosen[node[0]] = node[1]; node = back[node]
    return chosen

def reconcile(ref, hinted, plain, legacy=None, windows=None):
    """Combine reference tokens with the transcripts. Returns tokens with text, status and time anchor.
    hinted: prompted with the reference; plain: language-forced, unprompted; legacy: the 2026-10-02
    whole-file pass (automatic language, unprompted)."""
    passes = {'hinted': hinted, 'plain': plain}
    if legacy: passes['legacy'] = legacy
    opts, subs, extras = _options(ref, passes, windows)
    chosen = _chain(ref, opts)
    out = []
    for i, tok in enumerate(ref):
        t = dict(tok)
        if i in chosen:
            pick = opts[i][chosen[i]]; anchor = pick['tok']
            agree = [o for o in opts[i] if o['pass'] != 'hinted' and o['rel'] != 'variant'
                     and abs(o['tok']['start'] - anchor['start']) < 1.2]
            if pick['rel'] == 'variant':
                t['status'] = 'sung-variant'; t['reference'] = tok['text']; t['text'] = anchor['text']
            elif pick['pass'] != 'hinted' or agree:
                t['status'] = 'heard'
                heard_text = (agree[0]['tok'] if agree else anchor)['text']
                if heard_text != tok['text'] and relation(tok['text'], heard_text) == 'homophone': t['heardAs'] = heard_text
            else:
                t['status'] = 'reference-spelling'
                other = [x for x in subs[i] if x['pass'] != 'hinted']
                if other: t['heardAs'] = other[0]['tok']['text']
            t['start'], t['end'] = anchor['start'], anchor['end']
            t['evidence'] = sorted({o['pass'] for o in opts[i]})
        else:
            t['status'] = 'not-heard'
            if subs[i]: t['heardAs'] = subs[i][0]['tok']['text']
        out.append(t)
    # extra words heard at the same place by the hinted pass and an unprompted pass
    inserted = []
    for after, tok in extras.get('plain', []) + extras.get('legacy', []):
        twin = [x for a, x in extras.get('hinted', []) if relation(x['text'], tok['text']) in ('exact', 'homophone')
                and abs(x['start'] - tok['start']) < 0.35]
        lo = out[after]['start'] if after >= 0 and 'start' in out[after] else -1e9
        nxt = next((o['start'] for o in out[after + 1:] if 'start' in o), 1e9)
        if twin and tok['p'] >= 0.4 and lo - 0.1 <= tok['start'] <= nxt + 0.1 and \
                not any(abs(t['start'] - tok['start']) < 0.2 for _, t in inserted):
            base = ref[max(after, 0)] if ref else {'verse': 0, 'line': 0, 'language': 'en'}
            inserted.append((after, {'text': tok['text'], 'language': 'zh' if CJK.match(tok['text']) else base['language'],
                                     'status': 'extra-sung', 'start': tok['start'], 'end': tok['end'],
                                     'verse': base['verse'], 'line': base['line'], 'lineStart': False,
                                     'wordEnd': tok.get('wordEnd', True)}))
    for after, tok in sorted(inserted, key=lambda x: (-x[0], -x[1]['start'])):
        out.insert(after + 1, tok)
    # interpolate weak anchors for unheard tokens between their heard neighbours
    known = [i for i, t in enumerate(out) if 'start' in t]
    for i, t in enumerate(out):
        if 'start' in t: continue
        before = max([k for k in known if k < i], default=None); after = min([k for k in known if k > i], default=None)
        if before is not None and after is not None:
            a, b = out[before]['end'], out[after]['start']; span = after - before
            t['start'] = a + (b - a) * (i - before - 0.5) / span; t['end'] = t['start'] + 0.15
            t['anchor'] = 'interpolated'
        else:
            t['anchor'] = 'none'
    return out
