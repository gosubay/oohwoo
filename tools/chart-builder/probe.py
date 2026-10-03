"""Evidence probe for chart review. Usage (repository root):
  python tools/chart-builder/probe.py <key>                 every sung section line by line, with its sister verse
  python tools/chart-builder/probe.py <key> raw A B         measured notes (before words) between A and B seconds
  python tools/chart-builder/probe.py <key> pitch A B       frame-by-frame pitch of the singer stem
  python tools/chart-builder/probe.py <key> dips A B        loudness dips (possible new attacks) and loudness curve
  python tools/chart-builder/probe.py <key> words A B       transcript words (hinted / plain / whole-file pass)
Prints measurements only; it changes nothing.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from catalogue import ROOT, asset_paths, note_cache
NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
def nm(m): return NAMES[m % 12] + str(m // 12 - 1)

def main():
    key = sys.argv[1]; mode = sys.argv[2] if len(sys.argv) > 2 else 'lines'
    a, b = (float(sys.argv[3]), float(sys.argv[4])) if len(sys.argv) > 4 else (0, 1e9)
    vocal = os.path.join(ROOT, asset_paths(key)['vocal'])
    if mode == 'raw':
        prev = None
        for n in note_cache(key)['notes']:
            if a <= n['onset'] < b:
                gap = '' if prev is None else f"gap {n['onset'] - prev:.2f}"
                print(f"{n['onset']:7.2f}-{n['end']:7.2f} {n['end'] - n['onset']:.2f}s {nm(n['midi']):4s} median {n['median']:.2f} {gap}")
                prev = n['end']
    elif mode == 'pitch':
        from notes_from_vocal import decode, pitch_track
        t, m, v, _ = pitch_track(decode(vocal))
        sel = (t >= a) & (t < b)
        print(' '.join(f"{x:.2f}:{(y if z else float('nan')):.1f}" for x, y, z in list(zip(t[sel], m[sel], v[sel]))[::2]))
    elif mode == 'dips':
        from acoustics import decode, envelope, dips, band_energies, colour_change
        x = decode(vocal); t, e = envelope(x); sb = band_energies(x)
        print('dips', [(round(d['t'], 2), round(d['depth'], 2), round(colour_change(sb, d['t']), 3)) for d in dips(t, e, a, b)])
        sel = (t >= a) & (t < b)
        print(' '.join(f"{x_:.2f}:{y / e.max():.2f}" for x_, y in list(zip(t[sel], e[sel]))[::3]))
    elif mode == 'words':
        w = json.load(open(os.path.join(ROOT, 'docs', 'catalogue-analysis', 'section-words', key + '.json'), encoding='utf-8'))
        for bid, blk in w['blocks'].items():
            for kind in ('hinted', 'plain'):
                ws = [x for p in blk['pieces'] for x in p[kind] if a <= x['start'] < b]
                if ws: print(bid, kind, ' '.join(f"{x['start']:.2f}:{x['word'].strip()}" for x in ws))
        name = json.load(open(os.path.join(ROOT, 'docs', 'catalogue-analysis', 'charts.json'), encoding='utf-8'))[key]['recording']
        lw = json.load(open(os.path.join(ROOT, 'docs', 'catalogue-analysis', 'words', name + '.json'), encoding='utf-8'))['words']
        print('whole-file', ' '.join(f"{x['start']:.2f}:{x['word'].strip()}" for x in lw if a <= x['start'] < b))
    else:
        from selfcheck import check
        c = json.load(open(os.path.join(ROOT, 'docs', 'catalogue-analysis', 'charts.json'), encoding='utf-8'))[key]
        rows = {r['section']: r for r in check(c)}
        for s in c['sections']:
            if not s.get('noteCount'): print(f"--- {s['id']} {s['label']} {s['kind']} {s['start']}-{s['end']} no notes: {s.get('excluded')}"); continue
            r = rows.get(s['id'], {})
            print(f"--- {s['id']} {s['label']} [{s['language']}/{s['kind']}] {s['start']}-{s['end']} {s['noteCount']} notes; differs {r.get('differs')} from {r.get('sister')} key {r.get('keyShift')}")
            line = None; out = []; prev = None
            for n in c['notes'][s['firstNote']:s['lastNote'] + 1]:
                if n.get('phrase') != line:
                    if out: print('   ', ' '.join(out))
                    out = []; line = n.get('phrase')
                gap = '' if prev is None or n['t'] - prev < 0.04 else f"_{n['t'] - prev:.1f}_ "
                out.append(f"{gap}{n['t']:.2f}{n['note']}({n['end'] - n['t']:.2f}){n['lyric'] or '♪'}{'*' if n.get('sharedUnits') else ''}"); prev = n['end']
            print('   ', ' '.join(out))
        for d in c['droppedLyricUnits']: print('dropped', d)
        print('excluded notes', [(x['t'], nm(x['midi'])) for x in c['excludedNotes']][:60])

if __name__ == '__main__':
    main()
