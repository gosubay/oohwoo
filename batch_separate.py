"""
batch_separate.py — run Demucs vocal separation on all MP3s in a folder.
Outputs vocals-only MP3s (WAV is intermediate, deleted after conversion).
Skips files that already have a vocals MP3 in the output directory.
Usage: python batch_separate.py
"""
import os
import subprocess
import torch
import soundfile as sf
import numpy as np
from demucs.pretrained import get_model
from demucs.apply import apply_model
import librosa

MUSIC_DIR = r"C:\Users\Admin\Desktop\Galvin\Children's Songs\Music"
OUT_DIR   = r"C:\Claude\Code\OohWoo\separated\vocals"

os.makedirs(OUT_DIR, exist_ok=True)

mp3_files = sorted([f for f in os.listdir(MUSIC_DIR) if f.endswith('.mp3')])

print(f"Found {len(mp3_files)} MP3 files")
print("Loading Demucs model...")
model = get_model("htdemucs")
model.eval()
vocals_idx = model.sources.index("vocals")
print(f"Model ready. Sources: {model.sources}\n")

for i, fname in enumerate(mp3_files):
    song_name = os.path.splitext(fname)[0]
    out_mp3   = os.path.join(OUT_DIR, song_name + ".mp3")
    tmp_wav   = os.path.join(OUT_DIR, song_name + ".wav")

    if os.path.exists(out_mp3):
        print(f"[{i+1}/{len(mp3_files)}] SKIP (already done): {song_name}")
        continue

    mp3_path = os.path.join(MUSIC_DIR, fname)
    print(f"[{i+1}/{len(mp3_files)}] Processing: {song_name} ...")

    try:
        y, sr = librosa.load(mp3_path, mono=False, sr=model.samplerate)
        if y.ndim == 1:
            y = np.stack([y, y])

        wav = torch.tensor(y, dtype=torch.float32).unsqueeze(0)

        with torch.no_grad():
            sources = apply_model(model, wav, progress=False)[0]

        vocals = sources[vocals_idx].numpy()
        vocals_stereo = vocals.T
        sf.write(tmp_wav, vocals_stereo, model.samplerate)

        # Convert WAV -> MP3, remove tmp WAV
        subprocess.run([
            "ffmpeg", "-y", "-i", tmp_wav,
            "-q:a", "3", out_mp3
        ], check=True, capture_output=True)
        os.remove(tmp_wav)

        print(f"  -> Saved: {out_mp3}")

    except Exception as e:
        print(f"  ERROR: {e}")

print("\nAll done!")
