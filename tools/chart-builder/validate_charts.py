"""Check the built charts before they reach the game. Usage (repository root):
  python tools/chart-builder/validate_charts.py
Exits non-zero on any problem. Checks: correction files still match their recordings (hashes), note
timing/order/pitch/ids, explicit sections, Full song and Quick play bounds, Quick play inside the full song,
Twinkle's approved verse unchanged, and that index.html holds exactly what charts.json says.
These are structural checks; they never mark a song as listening-verified.
"""
import json, math, os, re, sys

sys.path.insert(0, os.path.dirname(__file__))
from catalogue import ROOT, SONGS, sha256
import apply_to_game

problems = []
def check(ok, song, message):
    if not ok: problems.append(f'{song}: {message}')

def main():
    charts = json.load(open(os.path.join(ROOT, 'docs', 'catalogue-analysis', 'charts.json'), encoding='utf-8'))
    check(sorted(charts) == sorted(SONGS), 'catalogue', f'songs {sorted(set(SONGS) ^ set(charts))} missing or extra')
    html = open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()
    twinkle = json.loads(re.search(r'<script id="twinkle-chart" type="application/json">([\s\S]*?)</script>', html).group(1))
    for key, c in charts.items():
        spec = json.load(open(os.path.join(ROOT, 'tools', 'chart-builder', 'songs', f'{key}.json'), encoding='utf-8'))
        for role, asset in spec['assets'].items():
            check(sha256(asset['path']) == asset['sha256'], key, f'{role} recording changed since its correction file was written')
        check(sha256(spec['lyricReference']['path']) == spec['lyricReference']['sha256'], key, 'lyric reference changed')
        check('owner-listening-approved' not in c['status'] or spec.get('review', {}).get('song') == 'owner-listening-approved',
              key, 'status claims approval the correction file does not record')
        notes = c['notes']
        ids = [n['id'] for n in notes]
        check(len(set(ids)) == len(ids), key, 'duplicate note ids')
        sections = {s['id']: s for s in c['sections']}
        for i, n in enumerate(notes):
            where = f"note {n['id']} at {n['t']}s"
            check(all(math.isfinite(n[f]) for f in ('t', 'end', 'midi', 'ratio')), key, f'{where}: non-numeric value')
            check(n['end'] > n['t'], key, f'{where}: ends before it starts')
            check(36 <= n['midi'] <= 96, key, f"{where}: pitch {n['midi']} outside a singing range")
            check(not i or n['t'] >= notes[i - 1]['end'] - 1e-6, key, f'{where}: overlaps the previous note')
            check(n['section'] in sections, key, f"{where}: section {n['section']} not listed")
            check(n['end'] <= c['playableSeconds'] + 1e-6, key, f'{where}: after the end of the recording')
        for s in c['sections']:
            if s.get('firstNote') is None: continue
            inside = notes[s['firstNote']:s['lastNote'] + 1]
            check(all(n['section'] == s['id'] for n in inside), key, f"section {s['id']}: note range mixes sections")
        covered = [k for p in c['phrases'] for k in range(p['firstNote'], p['lastNote'] + 1)]
        check(covered == list(range(len(notes))), key, 'phrases do not cover every note exactly once')
        full, quick = c['modes']['full'], c['modes']['quick']
        check(full['firstNote'] == 0 and full['lastNote'] == len(notes) - 1, key, 'Full song does not hold every note')
        check(full['level']['start'] == 0 and full['level']['end'] <= c['recordingSeconds'] + 1e-6, key, 'Full song bounds')
        for name, m in (('full', full), ('quick', quick)):
            L = m['level']
            part = notes[m['firstNote']:m['lastNote'] + 1] if not (key == 'twinkle' and name == 'quick') else None
            check(L['start'] <= L.get('melodyStart', L['start']) and L['fadeStart'] < L['end'], key, f'{name}: level order')
            if part:
                check(part[0]['t'] >= L['start'] and part[-1]['end'] <= L['end'] + 1e-6, key, f'{name}: notes outside the part')
                check(m['noteCount'] == len(part), key, f'{name}: note count')
                ph = [k for a, b in m['phrases'] for k in range(a, b + 1)]
                check(ph == list(range(m['firstNote'], m['lastNote'] + 1)), key, f'{name}: phrases do not cover the part')
                langs = {n_lang for s in c['sections'] if s['id'] in m['sections'] for n_lang in [s['language']]}
                check(set(m['languages']) <= langs | {'en', 'zh', 'ms'}, key, f'{name}: languages')
        check(0 <= quick['firstNote'] <= quick['lastNote'] <= full['lastNote'], key, 'Quick play is not inside the full song')
        check(quick['level']['end'] - quick['level']['start'] < full['level']['end'] - full['level']['start'], key,
              'Quick play is not shorter than the full song')
        if key == 'twinkle':
            for n, a in zip(notes, twinkle['notes']):
                check((n['id'], n['t'], n['end'], n['midi']) == (a['id'], a['onset'], a['end'], a['midi']), key,
                      f"approved verse note {a['id']} changed")
            check(quick['level'] == twinkle['level'], key, 'Quick play is not the approved reference level')
    # the game must hold exactly the generated block for this charts.json
    block = re.search(re.escape(apply_to_game.START) + r'[\s\S]*?' + re.escape(apply_to_game.END), html).group(0)
    check(block.replace('\r\n', '\n') == '\n'.join(apply_to_game.block(charts)), 'index.html',
          'generated chart block is out of date: run python tools/chart-builder/apply_to_game.py')
    if problems:
        print(f'{len(problems)} problem(s):'); print('\n'.join('  ' + p for p in problems)); sys.exit(1)
    print(f"OK: {len(charts)} songs, {sum(len(c['notes']) for c in charts.values())} notes; structure, hashes, both modes and "
          'game block checked (listening review is separate)')

if __name__ == '__main__':
    main()
