# OohWoo — Roadmap & Design Ideas

## 1. 3 Lives (Death Mechanic Rework)

**Current:** One hit = instant game over.

**Idea:** Give the bird 3 lives. When it hits a pipe:
- Bird flashes and briefly becomes invincible (so it doesn't die on the same pipe twice)
- 1 life deducted, shown as hearts (❤️❤️❤️) in the HUD
- Game only ends when all 3 lives are gone

This makes the game much friendlier for beginners and encourages players to keep trying through a song rather than restarting from the first missed pipe.

---

## 2. Octave Difficulty & Karaoke Realism

**Vocal range per difficulty:**
- **Easy:** 1 octave — covers nursery rhymes, kids' songs
- **Normal:** 1.5 octaves — covers most pop songs (current calibration)
- **Hard:** 2–3 octaves — advanced singers, game screen "zooms out" to show a taller play field

**Zoom-out mechanic for hard mode:** Instead of squishing notes closer together, the visible game area expands vertically so the pitch gaps between notes are preserved but the bird has more space to travel.

**Karaoke difficulty philosophy:** A player should NOT be able to complete a song on their first try — just like real karaoke, you need to practice the melody a few times before you can nail it. This is intentional design, not a bug. Difficulty should feel fair after several attempts.

---

## 3. Faster Bird Response (Soaring & Gliding)

**Problem:** At fast BPMs the bird can't move between notes quickly enough.

**Ideas:**
- Make the bird snap to pitch height faster (reduce the smoothing lag)
- Add a "boost" — when pitch changes dramatically, the bird accelerates instead of drifting
- The glide-down (silence = gravity) should also be snappier so the bird drops fast when the singer stops

This probably needs playtesting at different BPMs to find the right feel.

---

## 4. Song-to-Pipes Pipeline

**The problem:** Right now Twinkle Twinkle is hard-coded. We need a way to turn any song into a pipe schedule.

**Proposed pipeline:**
1. **Get the melody** — either by ear, MIDI file, or an AI tool that extracts melody from audio
2. **Convert to note list** — list of `{ note, duration }` pairs (e.g. `C4, 0.5s`)
3. **Map to pipe timestamps** — each note becomes a pipe that spawns at the right time, with its gap positioned at the note's pitch height
4. **Pipe timing** — duration of each note determines how long the player has to hold that pitch before the next pipe arrives

Tools to explore:
- **Basic Pitch** (Spotify) — free AI melody extractor from audio/MP3
- **MuseScore** — manual notation tool that exports MusicXML
- A simple JSON format we define ourselves that anyone can author by hand

---

## 5. Practice / No-Death Mode

**Idea:** A mode where the bird cannot die — it just bounces off pipes instead.

- Only scoring matters — hitting the center of the gap = more points
- Good for learning a new song's melody before attempting a real run
- Could show a "ghost" line of where the bird should be vs. where it actually is

This could be the default mode for first-time players or when a new song is selected for the first time.

---

## Decisions Made

- **Lives reset between songs** (not carried over)
- **Max BPM: 150** — covers nearly all pop songs; 170+ is too fast to pitch-match individual notes. Note density matters more than raw BPM — long held notes at 150 BPM are fine.

## Open Questions

- Do we want a song editor in the browser, or is JSON authoring fine for now?
- Should Practice Mode have a separate leaderboard or no leaderboard at all?
