# OohWoo — Design Decisions

A running log of major design choices, the reasoning behind them, and alternatives considered.
For future developers: read this to understand *why* the game works the way it does, not just *how*.

---

## Game Concept

**Decision: Flappy Bird controlled by singing**
The core loop is pitch-to-height mapping: sing higher to fly up, sing lower to fly down, silence = gentle fall. Pipes are timed to melody notes so the "correct" path through the level is the song itself.

Why this works: the game teaches you the melody by making you survive it. Players who know the song do better. Players who don't know the song learn it by playing.

Alternatives not pursued: volume control (too hard to sustain), rhythm tapping (too similar to existing games), speech recognition (too slow/complex).

---

## Audio / Pitch Detection

**Decision: Autocorrelation pitch detection via Web Audio API**
We use `getUserMedia` → `AnalyserNode` → autocorrelation algorithm running in the game loop. No external library.

Why: works in-browser with no install, low latency, sufficient accuracy for a melody game (doesn't need concert-hall precision).

**Decision: Global detection window `MIN_FREQ=100Hz`, `MAX_FREQ=600Hz`**
Covers bass voice to soprano. Notes outside this range are ignored as noise.

**Decision: Personal calibration stored in localStorage**
Players sing their lowest and highest comfortable notes. The game maps that personal range to 0–1 bird height, so a bass and a soprano play identically. Calibration persists across sessions.

Why: without calibration, a soprano's normal speaking voice would fly the bird off-screen, and a bass would never get off the ground. Calibration makes the game accessible to any voice.

Alternatives considered: fixed range per voice type (tenor/soprano presets). Rejected because it still requires the player to self-identify their voice type, and manual calibration is more accurate.

---

## Navigation Structure

**Decision: Main menu → Song selector → Game (3-level hierarchy)**
Main menu has: Play (→ song selector), Set up my voice, Mic On/Off.
Song selector shows all available songs with full bilingual titles.

Why: keeps the main menu clean and uncluttered as the song library grows. Avoids a wall of song cards on the first screen players see.

Previous structure: song selector *was* the main menu. Worked fine with 2 songs, would become unwieldy at 24.

**Decision: "Set up my voice" and "Mic On/Off" are small/subtle controls on main menu**
These are secondary actions — most players won't need them every session. They're styled as a small text link and a small secondary button rather than large primary buttons.

Why: the primary action is Play. Secondary actions should not compete visually.

---

## Pipe / Level Design

**Decision: Pipes timed to melody notes**
Each pipe appears at the pitch height the player should be singing at that moment in the song. Flying through the pipe = singing the right note at the right time.

**Decision: Moving to absolute timestamps (t: seconds) instead of BPM + beats**
*Status: planned, not yet implemented*

Original system: song defines a BPM and each note has a `beats` duration. Pipe timing is calculated by multiplying.

Problem: songs with fast sections (e.g. "morning bells are ringing" in Brother John) have eighth notes that are twice as fast as the rest of the song. Fixed BPM can't represent mixed note durations cleanly.

New system: each pipe entry will have `t: seconds` — the exact time into the song when it should appear. The game loop compares `gameTime >= pipe.t` and spawns accordingly.

Why this is durable: works regardless of BPM, handles mixed tempos, handles any rhythm. The transcription script already outputs timestamps in seconds so the data pipeline supports this naturally.

---

## Bird Movement Speed

**Decision: Dynamic bird speed based on gap to next pipe**
*Status: under discussion, not yet implemented*

The bird's vertical lerp speed should respond to how dense the upcoming notes are. When the next pipe is far away (slow passage, quarter notes), the bird glides gently. When the next pipe is close (fast passage, eighth notes), the bird moves more urgently.

Why: a fixed speed feels either too sluggish on fast songs or too twitchy on slow ones. Tying speed to note density means the game *feels* like the music.

Alternative considered: per-song `birdSpeed` setting. Rejected because it requires manual tuning for every song and breaks down within songs that have mixed tempos.

Alternative considered: fixed speed based on overall song BPM. Rejected for same reason — doesn't handle intra-song variation.

Preferred direction: Option D — bird glides lazily mid-gap, then accelerates as the next pipe approaches. Creates a sense of musical anticipation and urgency at the right moments.

---

## Song Library

**Decision: All songs are bilingual (English + Chinese)**
Song titles and eventually lyrics are shown in both languages. The game is designed for a bilingual audience.

Current songs:
1. Twinkle Twinkle Little Star / 一闪一闪亮晶晶
2. Brother John / Are You Sleeping? — 两只老虎 / 法国民谣

Planned: 22 more songs (lyrics sourced from Children's Song Lyrics.docx).

**Decision: Fast melodic runs become single grouped pipes**
Phrases like "morning bells are ringing" (4 fast notes) become one pipe at a representative pitch rather than 4 rapid-fire pipes.

Why: pipe gaps under ~0.8–1.0 seconds are too fast for a player to physically reposition their pitch. Grouping keeps gameplay comfortable without losing the musical structure of the song.

---

## Platform

**Decision: Single HTML file, no build step**
Everything — game logic, rendering, audio, UI — lives in `ooh-woo-game.html`. No framework, no bundler, no install.

Why: maximum portability. Any developer can open one file and understand the whole game. Deployment is copying one file.

Trade-off: the file will get long. Acceptable for this project size.

**Decision: Must be served over `localhost`, not `file://`**
Chrome blocks microphone access on `file://` URLs. The included `start-game.bat` launches a Python HTTP server automatically.

---

*Last updated: 2026-06-02*
*Maintainer: Galvin (gosu/gosubay)*
