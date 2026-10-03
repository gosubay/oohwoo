"""Print every sung stretch of each recording next to its transcript, to draft the section inventory.
Usage (repository root): python tools/chart-builder/inventory.py [song keys...]
Reads the separated vocal and docs/catalogue-analysis/words/*.json. Writes nothing; the curated result
belongs in tools/chart-builder/songs/<key>.json. A stretch is singing with no gap of GAP seconds or more.
"""
import json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from notes_from_vocal import analyse
from catalogue import ROOT, SONGS, note_cache

GAP = 1.2
NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

def main(only):
    for key, name in SONGS.items():
        if only and key not in only: continue
        notes = note_cache(key)['notes']
        words = json.load(open(os.path.join(ROOT, 'docs', 'catalogue-analysis', 'words', name + '.json'), encoding='utf-8'))['words']
        stretches = [[notes[0]]]
        for a, b in zip(notes, notes[1:]):
            (stretches.append([b]) if b['onset'] - a['end'] >= GAP else stretches[-1].append(b))
        print(f'===== {key}  ({name})  {note_cache(key)["duration"]:.1f}s')
        for st in stretches:
            a, b = st[0]['onset'], st[-1]['end']
            med = int(np.median([n['midi'] for n in st]))
            text = ' '.join(w['word'] for w in words if w['end'] > a - 0.2 and w['start'] < b + 0.2)
            print(f'  {a:7.2f}-{b:7.2f}  {len(st):3d} notes  median {NAMES[med % 12]}{med // 12 - 1:<2d} | {text[:160]}')

if __name__ == '__main__':
    main(sys.argv[1:])
