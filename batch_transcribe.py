"""
batch_transcribe.py — transcribe all isolated vocal WAVs and output note data.
Usage: python batch_transcribe.py
Output: transcriptions/  (one .txt per song)
"""
import os
import sys
import numpy as np
import librosa

VOCALS_DIR = r"C:\Claude\Code\OohWoo\separated\vocals"
OUT_DIR    = r"C:\Claude\Code\OohWoo\transcriptions"
os.makedirs(OUT_DIR, exist_ok=True)

NOTE_NAMES  = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
MAJOR_STEPS = [0, 2, 4, 5, 7, 9, 11]
DEGREE_RATIOS = [0.00, 0.14, 0.29, 0.43, 0.57, 0.71, 0.86]
DEGREE_NAMES  = ['Do','Re','Mi','Fa','Sol','La','Ti']

def freq_to_midi(freq):
    return 12 * np.log2(freq / 440.0) + 69 if freq > 0 else None

def detect_key(f0, voiced_flag):
    voiced = f0[voiced_flag & ~np.isnan(f0)]
    if len(voiced) == 0:
        return 0
    chroma = np.zeros(12)
    for freq in voiced:
        midi = freq_to_midi(freq)
        if midi:
            chroma[int(round(midi)) % 12] += 1
    best_key, best_score = 0, -1
    for tonic in range(12):
        scale_pcs = set((tonic + s) % 12 for s in MAJOR_STEPS)
        score = sum(chroma[pc] for pc in scale_pcs)
        if score > best_score:
            best_score, best_key = score, tonic
    return best_key

def snap_to_diatonic(midi_float, tonic):
    scale_pcs = [(tonic + s) % 12 for s in MAJOR_STEPS]
    midi_round = round(midi_float)
    pc = midi_round % 12
    octave = midi_round // 12
    if pc in scale_pcs:
        return midi_round
    best_pc, best_dist = pc, 999
    for s in scale_pcs:
        d = min(abs(s - pc), 12 - abs(s - pc))
        if d < best_dist:
            best_dist, best_pc = d, s
    candidate = octave * 12 + best_pc
    if abs(candidate - midi_round) > 6:
        candidate += (12 if candidate < midi_round else -12)
    return candidate

def midi_to_name(midi):
    pc = midi % 12
    oct_ = midi // 12 - 1
    return f"{NOTE_NAMES[pc]}{oct_}"

def scale_degree(midi, tonic):
    pc = midi % 12
    scale_pcs = [(tonic + s) % 12 for s in MAJOR_STEPS]
    if pc in scale_pcs:
        return scale_pcs.index(pc)
    return None

def transcribe(wav_path, song_name, out_file):
    out_file.write(f"{'='*60}\n")
    out_file.write(f"SONG: {song_name}\n")
    out_file.write(f"{'='*60}\n")

    y, sr = librosa.load(wav_path, mono=True)
    duration = len(y) / sr
    out_file.write(f"Duration: {duration:.1f}s\n")

    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr, units='frames')
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)
    bpm = float(np.atleast_1d(tempo)[0])
    out_file.write(f"BPM: {bpm:.1f}\n")

    f0, voiced_flag, _ = librosa.pyin(
        y, fmin=librosa.note_to_hz('C3'), fmax=librosa.note_to_hz('C6'),
        sr=sr, frame_length=2048, hop_length=512
    )
    times = librosa.times_like(f0, sr=sr, hop_length=512)

    tonic = detect_key(f0, voiced_flag)
    tonic_name = NOTE_NAMES[tonic]
    out_file.write(f"Key: {tonic_name} major\n\n")

    note_events = []
    for i in range(len(beat_times)):
        t_start = beat_times[i]
        t_end   = beat_times[i+1] if i+1 < len(beat_times) else t_start + 60/bpm
        mask = (times >= t_start) & (times < t_end) & voiced_flag
        if mask.sum() == 0:
            note_events.append({'beat': i, 't': t_start, 'note': 'REST', 'deg_name': 'REST', 'ratio': -1})
            continue
        freqs = f0[mask]
        freqs = freqs[~np.isnan(freqs)]
        if len(freqs) == 0:
            note_events.append({'beat': i, 't': t_start, 'note': 'REST', 'deg_name': 'REST', 'ratio': -1})
            continue
        median_freq = float(np.median(freqs))
        raw_midi    = freq_to_midi(median_freq)
        snapped     = snap_to_diatonic(raw_midi, tonic)
        note_name   = midi_to_name(snapped)
        deg         = scale_degree(snapped, tonic)
        ratio       = DEGREE_RATIOS[deg] if deg is not None else 0.0
        ratio       = max(0.0, min(1.0, ratio))
        deg_name    = DEGREE_NAMES[deg] if deg is not None else '?'
        note_events.append({'beat': i, 't': round(t_start, 2), 'note': note_name,
                            'deg_name': deg_name, 'ratio': ratio})

    # Print beat table
    out_file.write(f"Beat | Time  | Note | Degree | Ratio\n")
    out_file.write(f"-----|-------|------|--------|------\n")
    for e in note_events:
        out_file.write(f"  {e['beat']:3d} | {e['t']:5.2f}s | {e['note']:5s} | {e['deg_name']:6s} | {e['ratio']:.2f}\n")

    # Merge consecutive identical notes
    merged = []
    i = 0
    while i < len(note_events):
        e = note_events[i]
        count = 1
        while i + count < len(note_events) and note_events[i+count]['note'] == e['note']:
            count += 1
        merged.append({**e, 'beats': count})
        i += count

    out_file.write(f"\n// === JS NOTE ARRAY (key: {tonic_name} major, BPM: {bpm:.0f}) ===\n")
    out_file.write(f"// Do=0.00 Re=0.14 Mi=0.29 Fa=0.43 Sol=0.57 La=0.71 Ti=0.86\n")
    out_file.write(f"const SONG_NOTES = [\n")
    for e in merged:
        if e['note'] == 'REST':
            out_file.write(f"  // REST ({e['beats']} beats)\n")
        else:
            out_file.write(f"  {{note:'{e['note']}', ratio:{e['ratio']:.2f}, beats:{e['beats']}, lyric:''}},  // {e['deg_name']}\n")
    out_file.write(f"];\n")
    out_file.write(f"// BPM: {bpm:.0f}\n\n")

wav_files = sorted([f for f in os.listdir(VOCALS_DIR) if f.endswith('.wav')])
print(f"Transcribing {len(wav_files)} vocal tracks...")

for i, fname in enumerate(wav_files):
    song_name = os.path.splitext(fname)[0]
    wav_path  = os.path.join(VOCALS_DIR, fname)
    out_path  = os.path.join(OUT_DIR, song_name + ".txt")

    print(f"[{i+1}/{len(wav_files)}] {song_name}...")
    try:
        with open(out_path, 'w', encoding='utf-8') as f:
            transcribe(wav_path, song_name, f)
        print(f"  -> {out_path}")
    except Exception as e:
        print(f"  ERROR: {e}")

print("\nAll transcriptions done!")
print(f"Results in: {OUT_DIR}")
