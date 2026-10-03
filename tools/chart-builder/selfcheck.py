"""Automatic self-check of the built charts, to find slips before anyone has to listen.
Usage (repository root): python tools/chart-builder/selfcheck.py [--json]

Children's songs repeat one tune verse after verse (often in another language, key or octave). For every
sung verse this compares its note sequence with every other verse of the same song, in any key, and
reports how far it is from its closest match, plus the notes with no word and the notes holding several
words. A high figure is a lead to investigate in the recording, never a correction and never approval.
"""
import json, os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
CHARTS = os.path.join(ROOT, 'docs', 'catalogue-analysis', 'charts.json')
SUSPECT = 0.12           # share of a verse's notes that differ from its closest sister verse

def distance(a, b):
    """Fewest note insertions/deletions/changes turning tune a into tune b, best of all transpositions."""
    best = None
    for shift in range(-14, 15):
        prev = list(range(len(b) + 1))
        for i, x in enumerate(a, 1):
            cur = [i]
            for j, y in enumerate(b, 1):
                cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (x + shift != y)))
            prev = cur
        if best is None or prev[-1] < best[0]: best = (prev[-1], shift)
    return best

def check(chart):
    secs = [s for s in chart['sections'] if s.get('noteCount') and s['kind'] == 'sung']
    tunes = {s['id']: [n['midi'] for n in chart['notes'][s['firstNote']:s['lastNote'] + 1]] for s in secs}
    rows = []
    for s in secs:
        notes = chart['notes'][s['firstNote']:s['lastNote'] + 1]
        others = [(distance(tunes[s['id']], tunes[o['id']]), o['id']) for o in secs if o['id'] != s['id']]
        (edits, shift), sister = min(others) if others else ((0, 0), None)
        rows.append({'section': s['id'], 'label': s['label'], 'language': s['language'], 'start': s['start'],
                     'notes': len(notes), 'sister': sister, 'differs': round(edits / max(1, len(notes)), 2), 'keyShift': shift,
                     'noWord': sum(1 for n in notes if not n['lyric']), 'shared': sum(1 for n in notes if n.get('sharedUnits')),
                     'review': s.get('review')})
    return rows

def line_leads(chart):
    """Lyric lines that still show a sign of trouble, each with its time and what the sign is."""
    out = []
    dropped = {}
    for d in chart.get('droppedLyricUnits', []): dropped.setdefault(d['section'], []).append(d['text'])
    for s in chart['sections']:
        if not s.get('noteCount') or s['kind'] != 'sung': continue
        notes = chart['notes'][s['firstNote']:s['lastNote'] + 1]
        for p in chart['phrases']:
            ns = [n for n in notes if n.get('phrase') == p['id']] if 'id' in p else []
        lines = {}
        for n in notes: lines.setdefault(n.get('line') or n.get('phrase'), []).append(n)
        last = None
        for n in notes:                                  # a note with no word belongs to the line before it
            if n.get('line'): last = n['line']
        for key, ns in lines.items():
            signs = []
            nw = sum(1 for n in ns if not n['lyric'])
            sh = sum(1 for n in ns if n.get('sharedUnits'))
            df = sum(1 for n in ns if n.get('sisterVerses') == 'differ')
            if key is None and nw: signs.append(f'{nw} sung notes with no word')
            if sh: signs.append(f'{sh} notes hold several syllables')
            if df: signs.append(f'{df} syllables on a pitch no other verse uses there')
            if signs: out.append({'section': s['id'], 't': ns[0]['t'], 'end': ns[-1]['end'], 'signs': signs,
                                  'text': ' '.join(n['lyric'] or '~' for n in ns)})
        if dropped.get(s['id']):
            out.append({'section': s['id'], 't': s['start'], 'end': s['end'], 'signs': ['words not placed: ' + ' '.join(dropped[s['id']])], 'text': ''})
    return out

def main():
    charts = json.load(open(CHARTS, encoding='utf-8'))
    out = {k: check(c) for k, c in charts.items()}
    if '--json' in sys.argv: print(json.dumps(out, ensure_ascii=False)); return
    if '--lines' in sys.argv:
        total = 0
        for k, c in charts.items():
            for l in line_leads(c):
                total += 1
                print(f"{k:13s} {l['section']:6s} {l['t']:6.1f}-{l['end']:6.1f}s  {'; '.join(l['signs'])}  | {l['text'][:70]}")
        print(total, 'lines with a lead'); return
    bad = 0
    for k, rows in out.items():
        for r in rows:
            lead = r['differs'] > SUSPECT or r['noWord'] or r['shared']
            bad += bool(lead)
            print(f"{'LEAD' if lead else 'ok  '} {k:13s} {r['section']:6s} {r['language']} {r['start']:6.1f}s {r['notes']:3d} notes  "
                  f"differs {r['differs']:.2f} from {r['sister']} (key {r['keyShift']:+d})  no-word {r['noWord']}  several-words {r['shared']}  {r['review']}")
    print(f'{bad} of {sum(len(r) for r in out.values())} sung sections have a lead')

if __name__ == '__main__':
    main()
