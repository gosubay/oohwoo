"""Shared catalogue facts for the chart tools: song keys, recording names, asset hashes, cached note reads."""
import hashlib, json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from notes_from_vocal import analyse

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SONGS = {  # game key -> recording name (same file name in songs/, audio/ and separated/vocals/)
    'twinkle': '1. Twinkle Twinkle Little Star',
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
CACHE = os.path.join(ROOT, 'docs', 'catalogue-analysis', 'note-cache')

def asset_paths(key):
    name = SONGS[key]
    return {'source': f'songs/{name}.mp3', 'backing': f'audio/{name}.mp3', 'vocal': f'separated/vocals/{name}.mp3'}

_hashes = {}
def sha256(rel):
    if rel not in _hashes:
        _hashes[rel] = hashlib.sha256(open(os.path.join(ROOT, rel), 'rb').read()).hexdigest()
    return _hashes[rel]

def note_cache(key):
    """Full-recording note read of the vocal stem, cached per vocal hash (the reader is deterministic)."""
    vocal = asset_paths(key)['vocal']; digest = sha256(vocal)
    path = os.path.join(CACHE, key + '.json')
    if os.path.exists(path):
        data = json.load(open(path, encoding='utf-8'))
        if data.get('vocalSha256') == digest: return data
    os.makedirs(CACHE, exist_ok=True)
    data = {'vocalSha256': digest, **analyse(os.path.join(ROOT, vocal))}
    json.dump(data, open(path, 'w', encoding='utf-8'), indent=0)
    return data
