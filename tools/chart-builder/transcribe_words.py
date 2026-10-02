"""Word timings for each separated vocal, using the locally cached Whisper model.
Usage: python tools/chart-builder/transcribe_words.py   (run from the repository root)
Output: docs/catalogue-analysis/words/<song>.json  — a lyric-labelling draft, not ground truth.
"""
import glob, json, os, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT = os.path.join(ROOT, 'docs', 'catalogue-analysis', 'words')
os.makedirs(OUT, exist_ok=True)

# Windows: make the pip-installed CUDA libraries visible before loading the model.
for pkg in ('cublas', 'cudnn', 'cuda_nvrtc'):
    for d in glob.glob(os.path.join(sys.prefix, 'Lib', 'site-packages', 'nvidia', pkg, 'bin')):
        os.add_dll_directory(d); os.environ['PATH'] = d + os.pathsep + os.environ['PATH']

from faster_whisper import WhisperModel
try:
    model = WhisperModel('large-v3', device='cuda', compute_type='float16')
    list(model.transcribe(os.path.join(ROOT, 'separated', 'vocals', '9. Row Row Row Your Boat.mp3'), clip_timestamps=[0, 5])[0])
    print('device: cuda', flush=True)
except Exception as error:
    print('cuda unavailable, using cpu:', error, flush=True)
    model = WhisperModel('large-v3', device='cpu', compute_type='int8')

for path in sorted(glob.glob(os.path.join(ROOT, 'separated', 'vocals', '*.mp3'))):
    name = os.path.splitext(os.path.basename(path))[0]
    target = os.path.join(OUT, name + '.json')
    if os.path.exists(target) and '--force' not in sys.argv:
        continue
    segments, info = model.transcribe(path, word_timestamps=True, multilingual=True, vad_filter=False,
                                      condition_on_previous_text=False, beam_size=5)
    words = []
    for seg in segments:
        for w in seg.words or []:
            words.append({'start': round(w.start, 3), 'end': round(w.end, 3), 'word': w.word.strip(),
                          'p': round(w.probability, 3), 'segment': seg.id})
    json.dump({'language': info.language, 'duration': info.duration, 'words': words},
              open(target, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    print(name, info.language, len(words), 'words', flush=True)
