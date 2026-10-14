"""
transcribe_song.py — extract melody from MP3 and output OohWoo game note data.

Usage:
  python transcribe_song.py "path/to/song.mp3"

Detects key automatically, snaps to diatonic scale, outputs JS note array.
"""
import sys
import numpy as np
import librosa

MP3_PATH = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\Admin\Desktop\Galvin\Children's Songs\Music\2. Brother John - Two Tigers.mp3"

NOTE_NAMES  = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
MAJOR_STEPS = [0, 2, 4, 5, 7, 9, 11]  # semitone offsets for major scale degrees 1–7

def freq_to_midi(freq):
    return 12 * np.log2(freq / 440.0) + 69 if freq > 0 else None

def detect_key(f0, voiced_flag):
    """Return tonic semitone (0=C, 1=C#, ..., 11=B) using chroma profile."""
    voiced = f0[voiced_flag & ~np.isnan(f0)]
    if len(voiced) == 0:
        return 0
    chroma = np.zeros(12)
    for freq in voiced:
        midi = freq_to_midi(freq)
        if midi:
            chroma[int(round(midi)) % 12] += 1
    # Score each key by how well the chroma fits a major scale
    best_key, best_score = 0, -1
    for tonic in range(12):
        scale_pcs = set((tonic + s) % 12 for s in MAJOR_STEPS)
        score = sum(chroma[pc] for pc in scale_pcs)
        if score > best_score:
            best_score, best_key = score, tonic
    return best_key

def snap_to_diatonic(midi_float, tonic):
    """Snap a MIDI note to the nearest note in the major scale of `tonic`."""
    scale_pcs = [(tonic + s) % 12 for s in MAJOR_STEPS]
    midi_round = round(midi_float)
    pc = midi_round % 12
    octave = midi_round // 12

    if pc in scale_pcs:
        return midi_round  # already diatonic

    # Find nearest diatonic pitch class
    best_pc, best_dist = pc, 999
    for s in scale_pcs:
        d = min(abs(s - pc), 12 - abs(s - pc))
        if d < best_dist:
            best_dist, best_pc = d, s

    # Reconstruct MIDI in same octave (handle wrap)
    candidate = octave * 12 + best_pc
    if abs(candidate - midi_round) > 6:
        candidate += (12 if candidate < midi_round else -12)
    return candidate

def midi_to_name(midi):
    pc = midi % 12
    oct_ = midi // 12 - 1
    return f"{NOTE_NAMES[pc]}{oct_}"

def scale_degree(midi, tonic):
    """Return 0-based scale degree (0=Do, 1=Re, ..., 6=Ti) or None if not diatonic."""
    pc = midi % 12
    scale_pcs = [(tonic + s) % 12 for s in MAJOR_STEPS]
    if pc in scale_pcs:
        return scale_pcs.index(pc)
    return None

DEGREE_RATIOS = [0.00, 0.14, 0.29, 0.43, 0.57, 0.71, 0.86]  # Do Re Mi Fa Sol La Ti
DEGREE_NAMES  = ['Do','Re','Mi','Fa','Sol','La','Ti']

# ── Load audio ──────────────────────────────────────────────────────────────
print(f"Loading: {MP3_PATH}")
y, sr = librosa.load(MP3_PATH, mono=True)
duration = len(y) / sr
print(f"Duration: {duration:.1f}s  Sample rate: {sr}Hz")

# ── Tempo & beats ────────────────────────────────────────────────────────────
tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr, units='frames')
beat_times = librosa.frames_to_time(beat_frames, sr=sr)
bpm = float(np.atleast_1d(tempo)[0])
print(f"Detected BPM: {bpm:.1f}")

# ── Pitch track (vocal/melody range only) ────────────────────────────────────
f0, voiced_flag, voiced_prob = librosa.pyin(
    y,
    fmin=librosa.note_to_hz('C4'),
    fmax=librosa.note_to_hz('C6'),
    sr=sr, frame_length=2048, hop_length=512
)
times = librosa.times_like(f0, sr=sr, hop_length=512)

# ── Key detection ────────────────────────────────────────────────────────────
tonic = detect_key(f0, voiced_flag)
tonic_name = NOTE_NAMES[tonic]
print(f"Detected key: {tonic_name} major  (tonic semitone={tonic})\n")

# ── Per-beat melody extraction ───────────────────────────────────────────────
note_events = []
for i in range(len(beat_times)):
    t_start = beat_times[i]
    t_end   = beat_times[i+1] if i+1 < len(beat_times) else t_start + 60/bpm

    mask = (times >= t_start) & (times < t_end) & voiced_flag
    if mask.sum() == 0:
        note_events.append({'beat': i, 't': t_start, 'note': 'REST', 'degree': None, 'ratio': -1})
        continue

    freqs = f0[mask]
    freqs = freqs[~np.isnan(freqs)]
    if len(freqs) == 0:
        note_events.append({'beat': i, 't': t_start, 'note': 'REST', 'degree': None, 'ratio': -1})
        continue

    median_freq = float(np.median(freqs))
    raw_midi    = freq_to_midi(median_freq)
    snapped     = snap_to_diatonic(raw_midi, tonic)
    note_name   = midi_to_name(snapped)
    deg         = scale_degree(snapped, tonic)
    ratio       = DEGREE_RATIOS[deg] if deg is not None else 0.0

    # Clamp ratio to playable range 0–1
    # Notes above Do+octave (degree 0 in next octave) → cap at 1.0
    # Notes below Do → floor at 0.0
    # Detect octave jump: if snapped midi is >= tonic+12 above base octave → high
    base_do = snapped - (MAJOR_STEPS[deg] if deg is not None else 0)
    # Simple: if ratio maps fine use it; high notes clamp to 1, low to 0
    ratio_clamped = max(0.0, min(1.0, ratio))

    note_events.append({
        'beat': i, 't': round(t_start, 2),
        'note': note_name, 'degree': deg,
        'ratio': ratio_clamped,
        'deg_name': DEGREE_NAMES[deg] if deg is not None else '?'
    })

# ── Print beat table ─────────────────────────────────────────────────────────
print(f"Beat | Time  | Note | Degree | Ratio")
print(f"-----|-------|------|--------|------")
for e in note_events:
    deg_str = e.get('deg_name', '?')
    print(f"  {e['beat']:3d} | {e['t']:5.2f}s | {e['note']:4s} | {deg_str:6s} | {e['ratio']:.2f}")

# ── Merge consecutive identical notes ────────────────────────────────────────
merged = []
i = 0
while i < len(note_events):
    e = note_events[i]
    count = 1
    while i + count < len(note_events) and note_events[i+count]['note'] == e['note']:
        count += 1
    merged.append({**e, 'beats': count})
    i += count

# ── Output JS ────────────────────────────────────────────────────────────────
print(f"\n\n// ============================================================")
print(f"// SONG DATA — [Song Name Here]  (key: {tonic_name} major, BPM: {bpm:.0f})")
print(f"// Do=0.00  Re=0.14  Mi=0.29  Fa=0.43  Sol=0.57  La=0.71  Ti=0.86  Do(hi)=1.00")
print(f"// ============================================================")
print(f"const SONG_NOTES = [")
for e in merged:
    deg_str = e.get('deg_name', '?')
    print(f"  {{note:'{e['note']}', ratio:{e['ratio']:.2f}, beats:{e['beats']}, lyric:''}},  // {deg_str}")
print(f"];")
print(f"\n// BPM for buildPipes call: {bpm:.0f}/60")
