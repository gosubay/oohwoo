# OohWoo - Roadmap

> 2026-10-01: The current staged plan and approval ledger are in
> [TASK-BRIEFS.md](docs/TASK-BRIEFS.md), with requirements in
> [GAMEPLAY-SPEC.md](docs/GAMEPLAY-SPEC.md). The roadmap below is historical context
> and contains stale implementation descriptions. See the ledger for current approvals.

## Current State

OohWoo is a playable single-file browser rhythm game with:

- 22 selectable songs with English and Chinese titles where available
- MP3 backing tracks and 10-second song previews
- Absolute note timestamps (`t` in seconds) aligned to vocal onset
- Microphone pitch detection with personal voice calibration
- Keyboard, touch, and mouse fallback controls
- Karaoke lyrics, note hints, coins, scoring, and combo tiers
- Pause, retry, song-complete, and microphone status screens

Gameplay currently uses collectible note coins. The pipe schedule and collision
code still exist, but pipe spawning is disabled in `buildPipes()`.

---

## Completed: Timestamp-Anchored Gameplay

- The selected MP3 finishes loading before gameplay starts.
- Music and gameplay are scheduled from the same `AudioContext` clock.
- Coin and pipe positions are calculated from their timestamps every frame.
- Combo tiers increase points and visual glow without changing target speed.
- Frame drops no longer accumulate timing drift.

Future score-zoom or space-warp effects must preserve this rule: visual distance
may stretch, but every target remains anchored to its musical timestamp.

---

## Priority 2: Playtest and Tune All 22 Songs

For each song, record:

- Whether the first vocal and first note coin align
- Whether alignment remains accurate near the middle and end
- Notes that feel early, late, too dense, or impossible to reach
- Whether the displayed lyric matches the sung syllable
- Whether microphone control feels slower than keyboard control

Fine-tune `introOffset` only when the whole song has a consistent offset.
Correct individual `t` values when only particular notes are mistimed.

---

## Priority 3: Bird Response and Silence

**Current:** Singing and keyboard input move the bird toward a target height
with a fixed lerp rate. `GRAVITY` is currently `0`, so silence does not glide
the bird down even though that is part of the intended game design.

Planned work:

- Restore a gentle, predictable fall during silence
- Test faster vertical response for dense note passages
- Avoid adding smoothing that creates noticeable microphone lag
- Compare microphone, keyboard, and touch behavior separately

---

## Priority 4: Three Lives

**Current:** Pipe collision would cause instant game over, although pipes are
currently disabled.

Planned behavior:

- Start each song with three lives
- Lose one life on collision
- Briefly flash and grant invincibility after a hit
- Show remaining lives in the HUD
- End the run only after the last life is lost
- Reset lives between songs

---

## Priority 5: Practice Mode

A no-death mode for learning a song:

- Keep music and notes at normal speed initially
- Continue after misses
- Show whether the player was too high or too low
- Show note accuracy and longest combo at the end
- Consider slower playback only after synchronized speed control is reliable

---

## Priority 6: Mobile Browser Testing

Test on iPhone Safari and Android Chrome:

- Microphone permission and AudioContext startup
- Audio resuming after pause, app switching, or screen locking
- Bluetooth and wired-headphone latency
- Portrait layout, safe areas, and orientation changes
- Touch fallback and performance over a complete song

---

## Later Ideas

### Difficulty Levels

- **Easy:** Wider targets and forgiving scoring
- **Normal:** Current target spacing and response
- **Hard:** Narrower targets or a larger visible pitch range

Difficulty should change tolerance and presentation without breaking timestamp
alignment.

### Trance Mode

Combo-driven visual effects may include motion blur, colour shifts, speed lines,
edge glow, and brighter coins. Do not change gameplay speed until audio and
visual timing can share one reliable clock.

### Song Authoring Pipeline

The current pipeline is:

1. Add an MP3 backing track.
2. Create note entries with `{ note, ratio, t, lyric }`.
3. Measure the vocal `introOffset`.
4. Add the song to `SONG_DATA` and the carousel catalogue.
5. Playtest the beginning, middle, and end for drift.

Future work may add a JSON format or browser editor, but the existing timestamp
format already supports mixed rhythms and tempos.

---

## Decisions Made

- Absolute timestamps are the source of truth for note timing.
- The library currently contains 22 songs.
- Personal vocal calibration is saved in `localStorage`.
- Lives reset between songs.
- Note density matters more than a song's headline BPM.
- Timing accuracy takes priority over combo speed effects.

## Open Questions

- How should score zoom and space-warp effects visualize dense musical passages?
- Should pipes return, or should collectible note coins remain the main mechanic?
- Should Practice Mode have separate records or no leaderboard?
- Is hand-authored song data sufficient, or is a browser editor needed?

*Last updated: 2026-06-11*
