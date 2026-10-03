"""Language-forced word timings for each language block of each recording, using the locally cached
Whisper large-v3 model (no download, no network). Two passes per piece of singing:
  'hinted' — the block's reference lyrics are given as the prompt (better spelling, may over-trust the text)
  'plain'  — no prompt (independent evidence of what was sung)
The builder compares both with the reference. Neither pass is ground truth.
Usage (repository root): python tools/chart-builder/transcribe_sections.py [song keys...] [--force]
Output: docs/catalogue-analysis/section-words/<key>.json, reused while vocal hash and block settings match.
"""
import glob, hashlib, json, os, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(__file__))
from catalogue import ROOT, SONGS, asset_paths, sha256, note_cache

OUT = os.path.join(ROOT, 'docs', 'catalogue-analysis', 'section-words')
SONG_DIR = os.path.join(os.path.dirname(__file__), 'songs')
PIECE_MAX = 26.0          # Whisper reads 30 s windows; a prompt only reaches the first window
MODEL = 'large-v3'

for pkg in ('cublas', 'cudnn', 'cuda_nvrtc'):
    for d in glob.glob(os.path.join(sys.prefix, 'Lib', 'site-packages', 'nvidia', pkg, 'bin')):
        os.add_dll_directory(d); os.environ['PATH'] = d + os.pathsep + os.environ['PATH']

def pieces(key, start, end):
    """Cut a block into pieces of at most PIECE_MAX seconds, at the widest silences between notes."""
    notes = [n for n in note_cache(key)['notes'] if n['onset'] >= start and n['end'] <= end + 0.5]
    if not notes: return []
    cuts = [start]
    while end - cuts[-1] > PIECE_MAX:
        gaps = [(b['onset'] - a['end'], (a['end'] + b['onset']) / 2) for a, b in zip(notes, notes[1:])
                if cuts[-1] + 6 < (a['end'] + b['onset']) / 2 < cuts[-1] + PIECE_MAX]
        cuts.append(round(max(gaps)[1], 2) if gaps else cuts[-1] + PIECE_MAX)
    return list(zip(cuts, cuts[1:] + [end]))

def prompt_for(reference, limit=180):
    text = ' '.join(reference)
    return text if len(text) <= limit else text[:limit]

def main(args):
    force = '--force' in args; only = [a for a in args if not a.startswith('--')]
    from faster_whisper import WhisperModel
    try:
        model = WhisperModel(MODEL, device='cuda', compute_type='float16')
    except Exception as error:
        print('cuda unavailable, using cpu:', error, flush=True)
        model = WhisperModel(MODEL, device='cpu', compute_type='int8')
    os.makedirs(OUT, exist_ok=True)
    clip = os.path.join(tempfile.gettempdir(), 'oohwoo-section.wav')
    for key in SONGS:
        if only and key not in only: continue
        spec = json.load(open(os.path.join(SONG_DIR, key + '.json'), encoding='utf-8'))
        vocal = asset_paths(key)['vocal']
        target = os.path.join(OUT, key + '.json')
        old = json.load(open(target, encoding='utf-8')) if os.path.exists(target) else {}
        result = {'vocalSha256': sha256(vocal), 'model': MODEL, 'blocks': {}}
        for block in spec['blocks']:
            block = {**block, 'reference': [line for verse in block['verses'] for line in verse['lines']]}
            settings = hashlib.sha256(json.dumps([block['language'], block['start'], block['end'], block['reference'],
                                                  PIECE_MAX], ensure_ascii=False).encode()).hexdigest()[:16]
            cached = old.get('blocks', {}).get(block['id'])
            if cached and cached.get('settings') == settings and old.get('vocalSha256') == result['vocalSha256'] and not force:
                result['blocks'][block['id']] = cached; continue
            out = {'settings': settings, 'language': block['language'], 'pieces': []}
            for a, b in pieces(key, block['start'], block['end']):
                a0 = max(0.0, a - 0.3); b0 = b + 0.3
                subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{a0:.3f}', '-to', f'{b0:.3f}', '-i',
                                os.path.join(ROOT, vocal), '-ac', '1', '-ar', '16000', clip], check=True)
                piece = {'start': round(a, 2), 'end': round(b, 2)}
                for name, prompt in (('hinted', prompt_for(block['reference'])), ('plain', None)):
                    segments, _ = model.transcribe(clip, language=block['language'], task='transcribe',
                                                   word_timestamps=True, vad_filter=False, beam_size=5,
                                                   condition_on_previous_text=False, initial_prompt=prompt)
                    piece[name] = [{'start': round(w.start + a0, 3), 'end': round(w.end + a0, 3), 'word': w.word.strip(),
                                    'p': round(w.probability, 3), 'segment': seg.id}
                                   for seg in segments for w in (seg.words or [])]
                out['pieces'].append(piece)
                print(f"{key:13s} {block['id']:4s} {a:6.1f}-{b:6.1f}  {' '.join(w['word'] for w in piece['hinted'])[:110]}", flush=True)
            result['blocks'][block['id']] = out
        json.dump(result, open(target, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)

if __name__ == '__main__':
    main(sys.argv[1:])
