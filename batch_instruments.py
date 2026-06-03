"""
batch_instruments.py — extract instruments-only (no vocals) stem for all songs.
Saves as MP3 to audio/ folder, replacing the vocals-based MP3s we made earlier.
"""
import os
import torch
import numpy as np
import soundfile as sf
import librosa
import subprocess
from demucs.pretrained import get_model
from demucs.apply import apply_model

SONGS_DIR = r"C:\Claude\Code\OohWoo\songs"
TMP_DIR   = r"C:\Claude\Code\OohWoo\separated\instruments"
OUT_DIR   = r"C:\Claude\Code\OohWoo\audio"

os.makedirs(TMP_DIR, exist_ok=True)
os.makedirs(OUT_DIR, exist_ok=True)

mp3_files = sorted([f for f in os.listdir(SONGS_DIR) if f.endswith('.mp3')])
print(f"Found {len(mp3_files)} MP3 files")
print("Loading Demucs model (CPU)...")
model = get_model("htdemucs")
model.eval()

vocals_idx = model.sources.index("vocals")
print(f"Model ready. Sources: {model.sources}")
print(f"Will subtract index {vocals_idx} (vocals) and sum the rest.\n")

for i, fname in enumerate(mp3_files):
    song_name = os.path.splitext(fname)[0]
    out_mp3   = os.path.join(OUT_DIR, song_name + ".mp3")
    tmp_wav   = os.path.join(TMP_DIR, song_name + ".wav")

    if os.path.exists(out_mp3):
        print(f"[{i+1}/{len(mp3_files)}] SKIP (already done): {song_name}")
        continue

    mp3_path = os.path.join(SONGS_DIR, fname)
    print(f"[{i+1}/{len(mp3_files)}] Processing: {song_name} ...")

    try:
        y, sr = librosa.load(mp3_path, mono=False, sr=model.samplerate)
        if y.ndim == 1:
            y = np.stack([y, y])

        wav = torch.tensor(y, dtype=torch.float32).unsqueeze(0)

        with torch.no_grad():
            sources = apply_model(model, wav, progress=True)[0]

        # Sum all stems except vocals
        no_vocals = sum(sources[j] for j in range(len(model.sources)) if j != vocals_idx)
        no_vocals_np = no_vocals.numpy().T  # shape: (samples, 2)

        sf.write(tmp_wav, no_vocals_np, model.samplerate)

        # Convert WAV -> MP3
        subprocess.run([
            "ffmpeg", "-y", "-i", tmp_wav,
            "-q:a", "3", out_mp3
        ], check=True, capture_output=True)

        os.remove(tmp_wav)  # clean up tmp WAV
        print(f"  -> Saved: {out_mp3}")

    except Exception as e:
        print(f"  ERROR: {e}")

print("\nAll done!")
