"""Second pass: Whisper sometimes skips the first sung lines after an instrumental intro.
Where the vocal track has singing before the first transcribed word, transcribe just that
opening and merge the words into docs/catalogue-analysis/words/<song>.json.
Usage (repository root): python tools/chart-builder/transcribe_openings.py
"""
import glob, json, os, subprocess, sys, tempfile

sys.path.insert(0, os.path.dirname(__file__))
from notes_from_vocal import analyse

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT = os.path.join(ROOT, 'docs', 'catalogue-analysis', 'words')
for pkg in ('cublas', 'cudnn', 'cuda_nvrtc'):
    for d in glob.glob(os.path.join(sys.prefix, 'Lib', 'site-packages', 'nvidia', pkg, 'bin')):
        os.add_dll_directory(d); os.environ['PATH'] = d + os.pathsep + os.environ['PATH']
from faster_whisper import WhisperModel
try:
    model = WhisperModel('large-v3', device='cuda', compute_type='float16')
    list(model.transcribe(os.path.join(ROOT, 'separated', 'vocals', '9. Row Row Row Your Boat.mp3'), clip_timestamps=[0, 5])[0])
except Exception as error:
    print('cuda unavailable, using cpu:', error, flush=True)
    model = WhisperModel('large-v3', device='cpu', compute_type='int8')

for path in sorted(glob.glob(os.path.join(ROOT, 'separated', 'vocals', '*.mp3'))):
    name = os.path.splitext(os.path.basename(path))[0]
    target = os.path.join(OUT, name + '.json')
    data = json.load(open(target, encoding='utf-8'))
    if data.get('openingPass') or not data['words']:
        continue
    first_word = data['words'][0]['start']
    early = [n for n in analyse(path)['notes'] if n['onset'] < first_word - 0.6]
    if len(early) < 8:
        data['openingPass'] = 'not needed'
    else:
        a = max(0.0, early[0]['onset'] - 1.0); b = first_word + 0.2
        clip = os.path.join(tempfile.gettempdir(), 'oohwoo-opening.wav')
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(a), '-to', str(b), '-i', path, '-ac', '1', '-ar', '16000', clip], check=True)
        segments, info = model.transcribe(clip, word_timestamps=True, multilingual=True, vad_filter=False,
                                          condition_on_previous_text=False, beam_size=5)
        words = [{'start': round(w.start + a, 3), 'end': round(w.end + a, 3), 'word': w.word.strip(),
                  'p': round(w.probability, 3), 'segment': -1000 + seg.id}
                 for seg in segments for w in (seg.words or [])]
        words = [w for w in words if w['end'] <= first_word + 0.1]
        data['words'] = words + data['words']
        data['openingPass'] = {'from': round(a, 2), 'to': round(b, 2), 'language': info.language, 'words': len(words)}
        print(name, data['openingPass'], ' '.join(w['word'] for w in words), flush=True)
    json.dump(data, open(target, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
