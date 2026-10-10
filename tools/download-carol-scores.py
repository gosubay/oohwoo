"""Download the fixed, public-domain sources used by build-carol-practice.py.

Existing files are preserved. No singer recordings or modern arrangements are used.
"""
import requests
from pathlib import Path
import json

base = 'https://www.hymnsandcarolsofchristmas.com/Hymns_and_Carols/'
sources = {
    'jinglebells': 'https://trillian.mit.edu/~jc/music/abc/program/xmas/Jingle_Bells_VC-A-32-3.abc',
    'deckthehalls': 'https://trillian.mit.edu/~jc/music/book/EverydaySongBook/105_Deck_the_Hall.abc',
    'silentnight': base + 'XML/STILLE_NACHT.xml',
    'wewish': 'https://trillian.mit.edu/~jc/music/abc/xmas/song/We_Wish_You_a_Merry_Christmas-G-16-wW.abc',
    'joytotheworld': 'https://www.mutopiaproject.org/ftp/HandelGF/antioch/antioch.mid',
    'joy-source': 'https://www.mutopiaproject.org/ftp/HandelGF/antioch/antioch.ly',
    'firstnoel': base + 'XML/First_Nowell.xml',
}
folder = Path(__file__).resolve().parents[1] / 'docs' / 'carol-scores'
folder.mkdir(parents=True, exist_ok=True)
for key, url in sources.items():
    if (folder / (key + Path(url).suffix)).exists():
        continue
    response = requests.get(url, timeout=30)
    if response.status_code != 200:
        print('Unavailable', url, response.status_code)
        continue
    target = folder / (key + Path(url).suffix)
    target.write_bytes(response.content)
    print('Saved', target.name, len(response.content))
(folder / 'sources.json').write_text(json.dumps(sources, indent=2), encoding='utf-8')
