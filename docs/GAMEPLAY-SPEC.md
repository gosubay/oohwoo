# OohWoo — approved gameplay direction

Prepared 2026-10-01. Owner: Galvin. Step 1 decisions are approved in the coordinating chat. This document describes the intended game, not features already delivered.

## Product goal

A welcoming, arcade-style singing game: follow a melody to guide a bird through a musical flight path. Musical timing must be accurate; the player does not need precise singing technique. Smooth animation must not penalise correct singing.

## Approved choices

| Decision | Required behaviour |
| --- | --- |
| Pitch assistance | Moderate help toward a nearby expected note. The player still supplies the melody's meaningful pitch changes. |
| Bird height | Smoothly settle into the accepted note's lane, rather than expose every fluctuation of raw microphone pitch. |
| Silence | Mostly hold altitude, with a slight drift. Missing required singing affects score and combo, without a sharp fall. |
| Combo forgiveness | One miss weakens an active boost. Another miss before recovery breaks it. |
| Recovery | Three consecutive successful notes restore the weakened boost. Scheduled rests neither reset recovery nor count as successes. |
| Audio | Instrumental backing plus a clear guide melody at a comfortable singing pitch. |
| Voice setup | A short, skippable 10–15-second comfort check, rather than an extreme-range test. |
| Targets | Coins joined by a faint flowing path; held notes have trails. |
| Boost presentation | Noticeable forward acceleration, longer trails, gentle camera changes; readability remains clear. |
| Music during boost | Tempo, note-arrival timestamps, and vertical control responsiveness remain unchanged. |
| Level length | Full songs are the product goal. Validate one clearly bounded Twinkle verse first. |
| Range adjustment | “Too high / Too low” between attempts, followed by a restart in the adjusted key. |
| Results | Arcade score and best combo. |

## Musical source of truth

Use one verified chart tied to the exact audio asset/version. A chart must preserve note pitch including octave, onset, end, lyrics, rests, phrase boundaries, and explicit level start/end. Beat markers are separate from melody-note events: several notes can occupy one beat, and a note can last several beats.

Generate the guide, target positions, note hints, held-note trails, and lyric timing from this chart. Avoid independent copies of musical facts in separate subsystems. Keep chart corrections separate from microphone/device timing adjustment.

The existing transcription output is a draft, not ground truth. Verification must include listening against the actual recording at the beginning, middle, and ending. A partial level must end intentionally rather than abruptly stop the recording after its last coin.

## Voice matching and range

Measure a comfortable register and a small usable range through humming and short echo phrases. Do–Re–Mi alone is insufficient to establish a player's entire comfortable range. Offer a skip path and reversible adjustments. Do not infer ability from gender or age.

Choose a suitable musical key and octave per player/song. Backing, guide, and accepted target pitches must agree. Use roughly one octave or less as a beginner-arrangement target where practical. Support wider charts internally; do not require a player to demonstrate 1.5 or two octaves.

Transposition changes a melody's position, not its span. If a song is wider than a player's comfortable range, use a verified narrower arrangement or offer another song. Do not distort musical intervals by stretching the player's frequency range.

Accept coherent octave-lower/higher performances. Keep octave/register information in the tracking model so an ascending phrase does not wrap downward. Confirm register changes across reliable input, and recenter visual range between phrases when necessary. The expected chart must not make a constant unrelated pitch follow the melody automatically.

Moderate assistance is target-aware but bounded: assist an input already near the target, preserve a clearly different sung note, and avoid rapid switching around note boundaries. Microphone input must include valid voicing/confidence; silence and background leakage must not become free hits.

## Scoring and animation

Evaluate pitch/voicing in the note's scoring window independently of bird animation position. The bird remains visibly connected to the result through smooth settling and a short coin-attraction effect. Avoid scoring based solely on the bird's pixel distance from a coin.

Each note scores at most once. A long note is one musical event with sustain progress; its success/miss must resolve once. Repeated authored notes at the same pitch may be collected by holding that pitch in the beginner version. Distinct-pitch notes must not share one matching input sample as multiple successes.

Marked rests require no sound, cause no miss, and do not break combo. Brief syllable gaps are tolerated. Long silence during required singing is a miss. The first version continues after misses; no lives or instant death are required.

Maintain separate concepts for the literal successful-note streak, best streak, score multiplier, and flight-boost state. A forgiven miss may preserve a weakened flight boost while ending the literal streak; describe that distinction clearly in the UI.

## Combo state transitions

| State | Event | Result |
| --- | --- | --- |
| Normal | Enough successful notes | Enter boost according to the configured activation threshold. |
| Boosted | One note missed | Enter weakened boost; recovery progress is zero. |
| Weakened | Successful note | Increase recovery progress; the third consecutive success restores boost. |
| Weakened | Another missed note before recovery | Break boost; ease back to normal flight. |
| Any state | Scheduled rest | Preserve boost and recovery state; no automatic points. |
| Any state | Restart/new level | Reset run-specific state; preserve user preferences. |

Exact scoring/multiplier arithmetic and activation thresholds remain tuning decisions. Restoring a boost must not resurrect an old best-streak calculation or award duplicate points.

## Starting values to test, not approved final tuning

- Scoring window: approximately 100 ms early / 250 ms late, with explicit device/input latency handling and limits for dense passages.
- Boost activation candidates: five, ten, and twenty successful notes for increasing intensity.
- Smooth response near the current spring's response envelope, adjusted through real voice playtests.
- Small bounded silence drift; define its amount through playtesting rather than retaining the current strong gravity by default.
- Assistance width, voicing confidence, sustain coverage, gap tolerance, camera motion, boost easing, and score values must be measured and tuned.

Do not treat these candidates as user-approved exact constants. If tuning changes the approved behaviour rather than just its degree, bring it back to the coordinating chat.

## First reference-level acceptance

1. The declared Twinkle verse has verified pitches, starts, durations, rests, lyrics, and a deliberate ending against the chosen asset.
2. Targets and guide remain aligned at the start, middle, and end. Pause/resume and frame-rate changes do not accumulate timing drift.
3. Lower and higher comfortable voices can play; low tones are actually detected rather than accepted only by a mocked mapping function.
4. An ascending phrase across an octave boundary stays visually ascending; equivalent lower-register singing works without unintended jumps.
5. Nearby-pitch assistance helps, but clearly wrong sustained notes and silence cannot automatically follow a changing melody.
6. Correct singing can score while the bird is still gliding. Holds, repeated notes, and brief syllable gaps behave consistently.
7. Silence mostly holds altitude; rests protect combo; missed required singing does not stop the song.
8. Boost weakens on one miss, recovers after three successes, and breaks on a second miss before recovery. Audio tempo and target deadlines stay fixed.
9. Score and best combo are correct at the end and reset correctly on retry.
10. Galvin approves an actual voice playtest; include at least one additional comfortable vocal range before treating the design as ready to expand.

Automated checks establish technical behaviour. They do not establish recording accuracy, comfort, or fun without listening and live playtests.
