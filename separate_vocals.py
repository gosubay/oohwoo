"""
separate_vocals.py — extract vocals from MP3 using Demucs, save as WAV using soundfile.
Usage: python separate_vocals.py "path/to/song.mp3"
Output: separated/vocals/<songname>.wav
"""
import sys
import os
import torch
import soundfile as sf
import numpy as np
from demucs.pretrained import get_model
from demucs.apply import apply_model
import librosa

mp3_path = sys.argv[1] if len(sys.argv) > 1 else None
if not mp3_path:
    print("Usage: python separate_vocals.py <path_to_mp3>")
    sys.exit(1)

out_dir = os.path.join(os.path.dirname(__file__), "separated", "vocals")
os.makedirs(out_dir, exist_ok=True)

song_name = os.path.splitext(os.path.basename(mp3_path))[0]
out_path = os.path.join(out_dir, song_name + ".wav")

print(f"Loading model...")
model = get_model("htdemucs")
model.eval()

print(f"Loading audio: {mp3_path}")
y, sr = librosa.load(mp3_path, mono=False, sr=model.samplerate)
if y.ndim == 1:
    y = np.stack([y, y])  # mono → stereo

wav = torch.tensor(y, dtype=torch.float32).unsqueeze(0)  # (1, 2, T)

print(f"Separating vocals (this takes ~20s)...")
with torch.no_grad():
    sources = apply_model(model, wav, progress=True)[0]  # (sources, 2, T)

vocals_idx = model.sources.index("vocals")
vocals = sources[vocals_idx].numpy()  # (2, T)

# Save stereo WAV
vocals_stereo = vocals.T  # (T, 2)
sf.write(out_path, vocals_stereo, model.samplerate)
print(f"\nVocals saved to: {out_path}")
print(f"Now run: python transcribe_song.py \"{out_path}\"")
