# Step 9 (catalogue) — 21 songs re-charted from their recordings, owner listening pending

2026-10-02. Galvin asked for all other songs to be fixed the way Twinkle was. Every song except Twinkle now has a chart drafted from its own recording. These are **numerical drafts**: nobody has listened to them yet. Twinkle's approved chart, its audio and the gameplay systems were not changed.

## What changed, in plain language

Before, the 21 songs used note lists typed from memory on a metronome beat. Only the first note was lined up with the recording, so the coins drifted away from the singer straight after it. Now each song's coins, guide melody and lyrics come from what the singer on that recording actually sings: when each note starts and stops, and which pitch it is.

## How each chart was made (`tools/chart-builder/`)

1. `notes_from_vocal.py` reads the singer-only track in `separated/vocals/`, measures pitch every 10 ms and cuts it into notes (start, end, pitch including octave). No major scale or tempo is assumed.
2. `transcribe_words.py` and `transcribe_openings.py` get the sung words and rough word times from the local Whisper speech model (results in `docs/catalogue-analysis/words/`).
3. `build_charts.py` matches the words to the notes, groups notes into lyric lines at breaths, picks one excerpt per song, estimates the key (for Do-Re-Mi labels only) and writes `docs/catalogue-analysis/charts.json`.
4. `apply_to_game.py` writes those charts into the marked block in `ooh-woo-game.html`. The old hand-typed lists are deleted.

The excerpt for each song starts at the first sung lyric and stops at the first natural break after at least 15 seconds of singing: an interlude of 2.5 s or more, a switch to a different singer's register, or wordless humming. If none of those comes, it stops at the longest breath between 24 and 45 seconds of singing. The backing fades out there, as Twinkle's does. Full-length songs remain a later decision.

## Evidence

| Check | Result | What it does and does not show |
| --- | --- | --- |
| Builder run on Twinkle vs the owner-approved Twinkle chart | 42 of 42 notes: same pitch, same lyric; note starts differ by 0.09 s typically, 0.21 s at most | The method reproduces a chart Galvin approved by ear. The builder's settings were tuned on this song, so it is a weaker test for the others. |
| `tools/catalogue-audit` (chart note vs pitch in the vocal track) | 91–100% per song, was 0–28% | The coins sit on sung pitch. It reads the same audio the builder used, so it is a consistency check, not a second opinion. |
| `node tests/catalogue.cjs` | PASS | Every song loads, a perfect singer scores every note with no misses, the song ends at its fade. |
| All other tests in `tests/` | PASS (`chart.cjs` updated: 21 songs now report `recording-drafted; owner-listening-pending`) | Twinkle chart, timing, scoring, comfort, pitch detector unchanged. |
| Browser | Game loads without errors; Humpty Dumpty plays with coins and lyrics on screen | Display works. The in-app browser has no microphone or speakers for me, so nothing was heard. |
| Owner listening | **Pending for all 21** | Required by the plan before any song is called verified. |

## Per-song summary

| Song | Sung section charted | Notes | Key | Range | Pitch match before → now | Notes without a lyric |
| --- | --- | --- | --- | --- | --- | --- |
| Brother John | 17.3–33.7s of 107s | 32 | D | 14 semitones | 28% → 100% | 0 |
| Humpty Dumpty | 14.2–38.4s of 84s | 68 | C | 17 semitones | 8% → 98% | 3 |
| Head Shoulders Knees & Toes | 15.7–31.7s of 87s | 40 | C (set by hand) | 14 semitones | 13% → 97% | 5 |
| London Bridge | 11.4–43.8s of 95s | 75 | D | 9 semitones | 25% → 100% | 2 |
| Itsy Bitsy Spider | 4.5–21.8s of 95s | 46 | C | 14 semitones | 15% → 97% | 0 |
| Baa Baa Black Sheep | 12.2–27.5s of 98s | 40 | A | 12 semitones | 10% → 92% | 1 |
| Mary Had a Little Lamb | 10.1–39.5s of 98s | 84 | C# | 12 semitones | 23% → 92% | 0 |
| Row Row Row Your Boat | 0.5–20.1s of 53s | 47 | D | 14 semitones | 20% → 95% | 2 |
| The More We Get Together | 10.6–36.7s of 79s | 57 | D | 16 semitones | 23% → 94% | 8 |
| Little Bunny | 12.5–41.7s of 88s | 75 | D | 12 semitones | 9% → 96% | 11 |
| Rain Rain Go Away | 13.6–37.3s of 180s | 47 | C | 9 semitones | 10% → 100% | 3 |
| Finger Family | 8.9–25.2s of 105s | 38 | A (set by hand) | 12 semitones | 15% → 100% | 13 |
| Wheels on the Bus | 11.1–43.7s of 135s | 79 | C | 17 semitones | 13% → 94% | 11 |
| Old McDonald | 5.6–26.6s of 235s | 60 | G | 11 semitones | 12% → 91% | 0 |
| If You're Happy | 7.4–51.6s of 107s | 141 | G | 17 semitones | 13% → 97% | 0 |
| Five Little Monkeys | 20.8–61.2s of 166s | 100 | D# | 12 semitones | 20% → 95% | 0 |
| Baby Shark | 15.6–54.1s of 138s | 114 | G | 6 semitones | 8% → 99% | 11 |
| Ba Luo Bo | 8.4–37.8s of 140s | 68 | F | 12 semitones | 15% → 97% | 0 |
| Xiao Yan Zi | 12.8–35.1s of 438s | 43 | A (set by hand) | 16 semitones | 0% → 100% | 11 |
| Rasa Sayang | 10.3–35.8s of 59s | 53 | B | 13 semitones | 20% → 100% | 7 |
| Chan Mali Chan | 9.3–36.6s of 136s | 64 | G | 19 semitones | 12% → 93% | 5 |

## Known weak spots (expect to hear some of these)

- **Lyrics are the least reliable part.** Word timing from the speech model is rough, so a word can sit one note early or late, and some notes have no word. Chinese and Malay words may be misheard (for example 把萝卜 where the song says 拔萝卜). Pitch and timing do not depend on the lyrics.
- **Two syllables held on one pitch** can come out as one long note, or be split in the wrong place. The game lets a held pitch collect repeated notes, so this affects how it looks more than scoring.
- **Occasional wrong octave or stray note**, mostly on very short notes. 7 notes were auto-corrected by an octave; If You're Happy has the most octave doubt (11 notes where two readings disagree).
- **Long intros.** Five Little Monkeys starts its coins at 20.8 s: the vocal track carries the tune from 7 s but no words were detected there, so it was treated as introduction. Little Bunny and The More We Get Together open with wordless "ooh/la" lines that are skipped the same way.
- **Wide melodies.** Nine songs span more than one octave (up to 19 semitones). The screen now fits each song's whole range, so the lanes are closer together on those songs, and they may be hard for one voice to sing. The plan calls for a narrower arrangement in that case; none was made.
- **Key changes.** These songs still play in their recorded key; the arrows move the singer by whole octaves only. Twinkle is the only song with re-keyed backing tracks.
- **Keyboard practice keys** cover one octave plus the top note, so the highest coins on wide songs cannot be reached from the keyboard.
- **Keys for Do-Re-Mi labels** were estimated; three were set by hand from the melody's shape. A wrong key gives wrong Do-Re-Mi names but does not move any note.

## Game changes outside the chart data

- Each song draws its own pitch range on screen (`laneWindow`); Twinkle keeps exactly one octave as before.
- Do-Re-Mi names repeat every octave, so notes above the first octave are named correctly.
- Song cards say "Charted from recording · Listening review pending".
- `SONG_TONICS` (the old estimated key table) and all 21 hand-typed note lists were removed.

## Galvin's listening procedure (about 1 minute per song)

1. Double-click `start-game.bat`. Use headphones.
2. Press Play, pick a song, tick **Hear my guide melody**, press Play.
3. You do not need to sing. Listen: the guide beeps should follow the tune the backing track is playing, and each coin should reach the yellow line as its beep sounds.
4. Tell me per song: "good", or what is off and roughly where (for example "Humpty: guide goes wrong at 'all the king's horses'", "Baby Shark: lyrics one word late").
5. A song counts as verified only after you say so. Until then every card keeps its "Listening review pending" label.

## Departures from the written plan

Step 9 in `TASK-BRIEFS.md` says to finish full-length Twinkle first, work in small agreed batches, and do the independent review (Step 8) beforehand. Galvin asked for all songs now, so all 21 were drafted in one pass as excerpts. Approval still happens song by song, and full-length versions are not started.

## Re-running

From the repository root, with numpy, ffmpeg and faster-whisper available:

1. `python tools/chart-builder/transcribe_words.py` then `python tools/chart-builder/transcribe_openings.py` (only needed for new audio; results are cached)
2. `python tools/chart-builder/build_charts.py` (optionally followed by song keys, e.g. `humptydumpty`)
3. `python tools/chart-builder/apply_to_game.py`
4. Run every file in `tests/` with `node`, then the audit: `node tools/catalogue-audit/dump.cjs <folder>/charts.json` and `python tools/catalogue-audit/measure.py <folder>`

Corrections from listening should go into `docs/catalogue-analysis/charts.json` or the builder, never into the generated block in the game file.
