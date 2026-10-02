# OohWoo - Design Decisions

> 2026-10-01: The new intended behaviour is specified in
> [the approved gameplay specification](docs/GAMEPLAY-SPEC.md).
> The historical notes below include outdated descriptions of movement, calibration,
> and silence. Use [the implementation handover](docs/IMPLEMENTATION-HANDOVER.md)
> for the current-code audit; do not treat all historical decisions as the new design.

A running log of major design choices, their reasoning, and the current
implementation status.

## Game Concept

**Decision: Control a flying bird by singing**

Pitch maps to vertical position: higher pitch moves the bird up and lower pitch
moves it down. The intended silence behavior is a gentle fall, although gravity
is currently disabled and needs to be restored.

Notes from the melody travel across the screen. Matching the correct pitch at
the correct time collects the note coin. The original vine-pipe drawing and
collision systems remain in the code, but pipe spawning is currently disabled.

## Audio and Pitch Detection

**Decision: Use Web Audio autocorrelation**

The microphone path is `getUserMedia` -> `AnalyserNode` -> autocorrelation pitch
detection. This keeps the game browser-only and avoids external libraries.

**Decision: Detect from 100 Hz to 600 Hz**

The global range covers low voices through high voices. A player's comfortable
range is calibrated separately and saved in `localStorage`.

**Decision: Map personal vocal range to the full play area**

`playerMinFreq` and `playerMaxFreq` let different voice types control the same
game path. Calibration is more accurate and inclusive than asking players to
choose a fixed voice category.

## Navigation

**Decision: Main menu -> song selector -> game**

The song selector uses a carousel so the growing catalogue does not overwhelm
the main menu. Voice setup and microphone controls remain secondary actions.

## Song Library

**Decision: Ship 22 songs in the current library**

Each carousel entry includes a title, optional Chinese title, difficulty label,
estimated number of targets, and duration. Each song has an MP3 backing track
and timestamped note data.

**Decision: Keep bilingual presentation where source material is available**

English and Chinese titles and lyrics are used where available. Two Malay songs
currently use their Malay/English titles without Chinese subtitles.

## Note Timing

**Decision: Use absolute timestamps instead of BPM and beat counts**

*Status: implemented for all 22 songs.*

Each note uses:

```js
{ note: 'C4', ratio: 0.00, t: 0.500, lyric: 'word' }
```

`t` is the note time relative to the first vocal phrase. Each song also has an
`introOffset`, measured from its separated vocal track, which places the note
timeline at the correct position in the full MP3.

`buildPipes()` subtracts the on-screen travel time so a note should arrive at
the hit zone at its absolute audio timestamp.

Why this is durable:

- Mixed note lengths and tempo changes need no special BPM logic.
- Individual notes can be corrected without shifting the whole song.
- Transcription tools already produce timestamps in seconds.

## Timing Clock

**Decision: The backing track clock is authoritative**

*Status: implemented.*

The selected MP3 is fetched and decoded before gameplay begins. The backing
track is then scheduled with a short pre-roll, and `gameTime` is derived from:

```js
backingCtx.currentTime - backingStartTime
```

Each target stores its schedule time. Its horizontal position is recalculated
from the audio clock every frame instead of accumulating animation-frame
movement. This prevents loading delays, frame drops, and combo rewards from
causing musical drift.

**Space-warp rule:** The score may zoom, compress, or stretch visually, but the
mapping from each target to its musical timestamp must remain unchanged.

## Bird Movement

**Decision: Lerp toward detected pitch without spring overshoot**

The current fixed lerp removed overshoot and reduced instability. Microphone
input also uses a small bird-position compensation for pitch-detection latency.

Still to decide:

- Whether response should adapt to the time until the next note
- How quickly silence should lower the bird
- Whether keyboard and microphone need different movement tuning

## Scoring and Combo

**Current behavior**

- Collecting a note coin increases the combo and awards its tier multiplier.
- Missing a coin resets the combo.
- Combo thresholds increase points and coin/HUD glow.
- Combo thresholds never change note speed.
- Passing enabled pipes would award additional points, but pipes are disabled.

This keeps reward intensity separate from the musical timeline.

## Platform

**Decision: Keep a single HTML file with no build step**

All UI, rendering, audio, song data, and game logic live in
`ooh-woo-game.html`. This favors portability and easy local deployment over
modular file organization.

**Decision: Serve through localhost**

Microphone access requires a secure context. The included `start-game.bat`
serves the project at `http://localhost:8080/ooh-woo-game.html`.

## Near-Term Priorities

1. Playtest timestamp alignment across all 22 songs.
2. Design score zoom and visual space-warp effects around fixed timestamps.
3. Restore silence gliding and tune bird response.
4. Add three lives.
5. Add Practice Mode and richer result statistics.
6. Test iPhone Safari and Android Chrome.

*Last updated: 2026-06-11*
*Maintainer: Galvin (gosu/gosubay)*
