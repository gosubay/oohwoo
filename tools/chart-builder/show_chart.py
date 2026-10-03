"""Print one built chart section by section (notes, lyrics, evidence) for review.
Usage (repository root): python tools/chart-builder/show_chart.py <key> [section id ...]
"""
import json, os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
c = json.load(open(os.path.join(ROOT, 'docs', 'catalogue-analysis', 'charts.json'), encoding='utf-8'))[sys.argv[1]]
only = sys.argv[2:]
print(c['key'], c['recording'], 'key', c['keyTonic'], 'tuning', c['tuningSemitones'], 'natural end', c['naturalEnd'])
for m, v in c['modes'].items():
    print(f"  {m}: notes {v['firstNote']}-{v['lastNote']} level {v['level']} langs {v['languages']} range {v['rangeSemitones']}")
for s in c['absentSections']:
    print('  ABSENT', s['id'], s['label'], s.get('reason'))
for s in c['sections']:
    if only and s['id'] not in only: continue
    print(f"--- {s['id']} {s['label']} [{s['language']}/{s['kind']}] {s['start']}-{s['end']} notes {s.get('noteCount')} "
          f"{s.get('located', '')} lyric {s.get('lyricStatusCounts')} variants {s.get('variants')}")
    if s.get('firstNote') is None: continue
    line = None; out = []
    for n in c['notes'][s['firstNote']:s['lastNote'] + 1]:
        if n.get('phrase') != line:
            if out: print('   ', ' '.join(out))
            out = [f"[{n.get('phrase')}]"]; line = n.get('phrase')
        mark = ''.join(['*' if n.get('sharedUnits') else '', '^' if n.get('attack') else '',
                        '!' if set(n.get('flags', [])) & {'estimators-disagree', 'octave-fold-suspect', 'unstable-pitch'} else '',
                        '?' if n.get('lyricStatus') in ('not-heard', 'reference-spelling') else ''])
        out.append(f"{n['t']:.2f}{n['note']}:{n['lyric'] or '·'}{mark}")
    print('   ', ' '.join(out))
dropped = [d for d in c['droppedLyricUnits'] if not only or d['section'] in only]
if dropped: print('  dropped units:', ' '.join(f"{d['section']}:{d['text']}({d['status'][:5]})" for d in dropped))
print('  excluded notes:', len(c['excludedNotes']), ' '.join(f"{x['t']}" for x in c['excludedNotes'][:30]))
