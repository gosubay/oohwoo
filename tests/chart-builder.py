"""Fixtures for the recording-based chart builder (language-aware lyrics, audio-checked splits).
Run from the repository root:  python tests/chart-builder.py
Synthetic fixtures test the rules; the recording fixtures re-measure the real audio behind charts.json.
None of this is listening verification.
"""
import json, os, re, statistics, sys
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'chart-builder'))
from lyrics import malay_syllables, relation, reference_tokens
from acoustics import decode, envelope, dips
from build_charts import align, align_atoms, sister_expectations, split_note, merge_scoops, apply_measured_note_edits, StaleSource, SPLIT_DEPTH
from atoms import atom_cache
from catalogue import asset_paths

CHARTS = json.load(open(os.path.join(ROOT, 'docs', 'catalogue-analysis', 'charts.json'), encoding='utf-8'))
passed = []
def ok(cond, name):
    assert cond, name
    passed.append(name)

# ---- Malay is split into sung syllables, not English ones
for word, want in {'sayang': ['sa', 'yang'], 'saya': ['sa', 'ya'], 'dia': ['di', 'a'], 'buah': ['bu', 'ah'],
                   'dikupas': ['di', 'ku', 'pas'], 'payung': ['pa', 'yung'], 'ketipung': ['ke', 'ti', 'pung'],
                   'kambing': ['kam', 'bing'], 'bagai': ['ba', 'gai']}.items():
    ok(malay_syllables(word) == want, f'malay {word}')
ok([t['text'].lower() for t in reference_tokens([{'label': 'v', 'lines': ['Rasa sayang hey']}], 'ms')] == ['ra', 'sa', 'sa', 'yang', 'hey'],
   'malay reference line')

# ---- Mandarin homophones and Latin spellings of one sung sound
for a, b in [('拔', '把'), ('拔', '巴'), ('年', '念')]:
    ok(relation(a, b) == 'homophone', f'homophone {a}/{b}')
for a, b in [('dikupas', 'dikubas'), ('payung', 'peyang'), ('do', 'doo'), ('oi', 'hoi')]:
    ok(relation(a, b) != 'different', f'same sound {a}/{b}')
ok(relation('小', '大') == 'different', 'different characters stay different')

# ---- in the built charts, misheard words are shown with the reference spelling
def joined(key):
    return ''.join(re.sub(r'[-\s]', '', n['lyric'] or '') for n in CHARTS[key]['notes']).lower()
for key, good, bad in [('baluobo', '拔萝卜', ['把萝卜', '巴萝卜', '抱萝卜']), ('xiaoyanzi', '穿花衣', ['春花一']),
                       ('xiaoyanzi', '年年', ['念念']), ('chanmalichan', 'dikupas', ['dikubas']),
                       ('chanmalichan', 'payung', ['peyang']), ('chanmalichan', 'oioi', ['ohboy'])]:
    text = joined(key)
    ok(good in text and not any(b in text for b in bad), f'{key} shows {good}')

# ---- a note with two syllables is split only where the audio shows a new attack, never at equal times
times = np.arange(0, 1.0, 0.005)
rms = np.ones_like(times); rms -= 0.75 * np.exp(-((times - 0.30) / 0.02) ** 2)       # clear re-attack at 0.30 s
flat = (times, np.zeros((len(times), 40)))
units = [{'start': 0.0, 'end': 0.2, 'weak': False}, {'start': 0.42, 'end': 0.6, 'weak': False}]
pieces = split_note({'onset': 0.0, 'end': 1.0}, [0, 1], units, (times, rms), flat)
ok(len(pieces) == 2 and abs(pieces[0][1] - 0.30) < 0.011, 'split at the measured attack (0.30 s), not the midpoint')
ok(pieces[1][3]['source'] == 'measured attack' and pieces[1][3]['dipDepth'] <= SPLIT_DEPTH, 'split records its evidence')
pieces = split_note({'onset': 0.0, 'end': 1.0}, [0, 1], units, (times, np.ones_like(times)), flat)
ok(len(pieces) == 1 and pieces[0][2] == [0, 1], 'no attack in the audio: the syllables share one note')

# ---- notes without transcribed words keep their own pitches; a melisma keeps its notes
def note(t, d=0.3): return {'onset': t, 'end': t + d}
weak = lambda text, line=False: {'text': text, 'start': None, 'end': None, 'weak': True, 'lineStart': line, 'language': 'zh'}
owned, dropped = align([note(0), note(0.35), note(0.7)], [weak('a', True), weak('b'), weak('c')])
ok(owned == [[0], [1], [2]] and not dropped, 'unheard words still take one same-length note each, nothing merged')
heard = lambda text, s, line=False: {'text': text, 'start': s, 'end': s + 0.2, 'weak': False, 'lineStart': line, 'language': 'zh'}
owned, _ = align([note(0), note(0.31, 0.2), note(0.52, 0.2), note(0.9)], [heard('a', 0.0, True), heard('b', 0.9)])
ok(owned == [[0], [], [], [1]], 'melisma: one syllable over several notes, the extra notes stay as unlabelled notes')

# ---- a short slide into a note is not given a syllable when the line does not need it (and is when it does)
def pn(t, d, midi): return {'onset': t, 'end': t + d, 'midi': midi}
line = [pn(0, .5, 67), pn(.55, .6, 67), pn(1.15, .17, 65), pn(1.32, .34, 66), pn(1.8, .4, 66), pn(2.4, .4, 64), pn(3.0, .4, 64), pn(3.6, .6, 62)]
words = [heard(c, t, i == 0) for i, (c, t) in enumerate(zip('满天都是小星星', [0, .55, 1.15, 1.8, 2.4, 3.0, 3.6]))]
owned, _ = align(line, words)
notes2, owned2 = merge_scoops([dict(n) for n in line], owned)
ok([n['midi'] for n in notes2] == [67, 67, 66, 66, 64, 64, 62] and owned2 == [[k] for k in range(7)], 'slide joins its note; every word lands on its own note')
ok(notes2[2]['onset'] == 1.15 and notes2[2]['absorbedGlides'][0]['midi'] == 65, 'the joined slide is recorded on the note')
eight = [heard(c, t, i == 0) for i, (c, t) in enumerate(zip('abcdefgh', [0, .55, 1.15, 1.32, 1.8, 2.4, 3.0, 3.6]))]
owned, _ = align(line, eight)
ok(len(merge_scoops([dict(n) for n in line], owned)[0]) == 8 and all(owned), 'eight words: the short note keeps its own syllable')
tw = [n for n in CHARTS['twinkle']['notes'] if n['section'] == 'zh-1' and n['lyric']]
ok([n['midi'] for n in tw] == [62, 62, 69, 69, 71, 71, 69, 67, 67, 66, 66, 64, 64, 62, 69, 69, 67, 67, 66, 66, 64, 69, 69, 67, 67, 66, 66, 64,
                               62, 62, 69, 69, 71, 71, 69, 67, 67, 66, 66, 64, 64, 62], 'Twinkle Mandarin verse: 42 words on the 42 melody notes')

# ---- recording fixtures: the loudness dips that cut one held pitch into atoms are re-measured from the vocal
checked = 0
for key in ('twinkle', 'baluobo', 'chanmalichan'):
    cut_atoms = [a for a in atom_cache(key)['atoms'] if a.get('cut')]
    ok(cut_atoms, f'{key} has pitches cut at loudness dips')
    t, r = envelope(decode(os.path.join(ROOT, asset_paths(key)['vocal'])))
    for a in cut_atoms[:3]:
        found = [d for d in dips(t, r, a['onset'] - 0.3, a['end'] + 0.3) if abs(d['t'] - a['onset']) < 0.006]
        ok(found, f"{key} dip at {a['onset']:.2f} s re-measured in the vocal")
        checked += 1

# ---- lyric-aware notes from atoms: the syllable count chooses among the boundaries the recording offers
def at(t, e, midi, **extra): return {'onset': t, 'end': e, 'midi': midi, 'median': float(midi), 'glide': 0.0, **extra}
def syl(text, start, line=False, n=0): return {'text': text, 'start': start, 'end': start + 0.2, 'weak': False, 'lineStart': line, 'language': 'zh', 'line': (0, n)}
held = [at(0, .5, 62), at(.5, 1.0, 62, cut={'depth': .87, 'colour': .03}), at(1.1, 1.6, 64), at(1.6, 2.0, 66)]
n3, o3, d3 = align_atoms([dict(a) for a in held], [syl('a', 0, True), syl('b', 1.1), syl('c', 1.6)])
ok([(n['onset'], n['end'], n['midi']) for n in n3] == [(0, 1.0, 62), (1.1, 1.6, 64), (1.6, 2.0, 66)] and o3 == [[0], [1], [2]] and not d3,
   'three syllables: a shallow dip inside a held note is not a new note')
n4, o4, d4 = align_atoms([dict(a) for a in held], [syl('a', 0, True), syl('b', .5), syl('c', 1.1), syl('d', 1.6)])
ok([(n['onset'], n['end']) for n in n4] == [(0, .5), (.5, 1.0), (1.1, 1.6), (1.6, 2.0)] and o4 == [[0], [1], [2], [3]],
   'four syllables: the same dip is where the second syllable starts')
slide = [at(0, .5, 62), at(.6, .76, 64, glide=0.8), at(.76, 1.2, 66), at(1.3, 1.8, 67)]
n5, o5, _ = align_atoms([dict(a) for a in slide], [syl('a', 0, True), syl('b', .6), syl('c', 1.3)])
ok([(n['onset'], n['midi']) for n in n5] == [(0, 62), (.6, 66), (1.3, 67)] and n5[1]['absorbedGlides'][0]['midi'] == 64,
   'a short rising slide starts the syllable and takes the pitch of the note it lands on')
real = [at(0, .3, 63), at(.3, .47, 65, edge={'depth': .3, 'colour': .12}), at(.47, .8, 63, edge={'depth': .25, 'colour': .1}), at(.8, 1.3, 61, edge={'depth': .2, 'colour': .1})]
n6, o6, _ = align_atoms([dict(a) for a in real], [syl('a', 0, True), syl('b', .3), syl('c', .47), syl('d', .8)])
ok([n['midi'] for n in n6] == [63, 65, 63, 61] and o6 == [[0], [1], [2], [3]], 'a short note across a clear loudness dip is a real note, not a slide')
exp = sister_expectations({'a': {(0, 0): [62, 64, 66]}, 'b': {(0, 0): [62, 64, 66]}, 'c': {(0, 0): [64, 66, 68]}, 'd': {(0, 0): [62, 62, 66]}})
ok(exp['d'][0, 0] == [2, 4, 6] and exp['c'][0, 0] == [4, 6, 8], 'other verses give the expected pitch class per syllable, in the verse own key')
ok(sister_expectations({'a': {(0, 0): [62]}, 'b': {(0, 0): [64]}}) == {}, 'two verses alone give no expectation')

# ---- language and register switches come from the recording
rs = CHARTS['rasasayang']
ok([s['language'] for s in rs['sections'] if s.get('noteCount')] == ['ms', 'en', 'zh'], 'Rasa Sayang: Malay, English, Mandarin in order')
for s in rs['sections']:
    lyr = [n['lyric'] for n in rs['notes'] if n['section'] == s['id'] and n['lyric']]
    cjk = sum(bool(re.search(r'[一-鿿]', x)) for x in lyr)
    ok(cjk == len(lyr) if s['language'] == 'zh' else cjk == 0, f"Rasa Sayang {s['id']} lyrics in its own script")
bs = CHARTS['babyshark']
# ---- reviewed corrections to measured notes (song file), applied before the words are placed
def mn(t, e, midi): return {'onset': t, 'end': e, 'midi': midi, 'median': float(midi)}
raw4 = [mn(0, 1.0, 62), mn(1.2, 1.7, 69), mn(2.0, 2.2, 58), mn(2.2, 2.3, 60), mn(2.5, 2.9, 62)]
fixed = apply_measured_note_edits('fixture', {'measuredNoteEdits': [
    {'op': 'split', 'onset': 0, 'at': 0.55, 'reason': 'r'}, {'op': 'split', 'onset': 1.2, 'at': 1.4, 'midi': [71, 69], 'reason': 'r'},
    {'op': 'join', 'onset': 2.2, 'into': 'previous', 'reason': 'r'}, {'op': 'midi', 'onset': 2.0, 'old': 58, 'new': 57, 'reason': 'r'}]},
    [dict(n) for n in raw4])
ok([(n['onset'], n['end'], n['midi']) for n in fixed] == [(0, .55, 62), (.55, 1.0, 62), (1.2, 1.4, 71), (1.4, 1.7, 69), (2.0, 2.3, 57), (2.5, 2.9, 62)],
   'measured-note edits: split, split with pitches, join a slide, pitch')
ok(all(n.get('measuredEdits') for n in fixed[:5]) and not fixed[5].get('measuredEdits'), 'each edited note carries its edit and reason')
try:
    apply_measured_note_edits('fixture', {'measuredNoteEdits': [{'op': 'join', 'onset': 9.9, 'into': 'next', 'reason': 'r'}]}, [dict(n) for n in raw4])
    ok(False, 'stale measured-note edit must fail')
except StaleSource:
    ok(True, 'a measured-note edit that matches no note is refused')
bj = CHARTS['brotherjohn']
for sec in ('zh-1', 'zh-2'):
    ns = [n for n in bj['notes'] if n['section'] == sec]
    ok(''.join(n['lyric'] for n in ns) == '两只老虎两只老虎跑得快跑得快一只没有耳朵一只没有尾巴真奇怪真奇怪' and len(ns) == 32,
       f'Two Tigers {sec}: one note per Mandarin syllable')
    ok([n['midi'] for n in ns] == [62, 64, 66, 62] * 2 + [66, 67, 69] * 2 + [69, 71, 69, 67, 66, 62] * 2 + [62, 57, 62] * 2, f'Two Tigers {sec}: the tune')
ok([(n['midi'], n['lyric']) for n in CHARTS['twinkle']['notes'] if 69.2 < n['t'] < 70.0] == [(57, '')], 'Twinkle: the low voiced dip after 睛 stays as a wordless note')

def med(sec, field): return statistics.median(n[field] for n in bs['notes'] if n['section'] == sec and n.get(field) is not None)
ok(med('zh-1', 'midi') - med('zh-3', 'midi') == 12, 'Baby Shark 爸爸 verse is an octave below 宝宝')
ok(abs(med('zh-3', 'yinMidi') - med('zh-3', 'midi')) < 1, 'that octave is confirmed by the independent estimator, not by neighbours')

print(f'PASS: {len(passed)} chart-builder fixtures (Malay syllables, homophones/spellings, attack-based splits, '
      f'unheard words, melisma, lyric-aware atoms, sister verses, {checked} real dips re-measured, language and register switches). Not listening-verified.')
