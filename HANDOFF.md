# HANDOFF — OohWoo

Last updated: 2026-10-03 (SGT)

## Where things stand (2026-10-03)

- **All 22 songs now have a Full song chart and a separate Quick play excerpt**, rebuilt from each
  recording by the corrected pipeline (brief: `docs/CLAUDE-CATALOGUE-CORRECTION-HANDOFF.md`, plan:
  `docs/CATALOGUE-CORRECTION-PLAN.md`). 4,613 notes in total (was 1,371 in single-language excerpts).
- The game has a **Full song / Quick play** choice on the song screen (Full is the default, remembered).
- **Listening-verified so far: Twinkle only** (both verses, on the listening page, singer only, 2026-10-03;
  not yet confirmed by playing it in the game). The other 21 songs are `owner-listening-pending`. Per-song
  before/after table, what was implemented, and the regions to listen to first:
  `docs/CATALOGUE-CORRECTION-REVIEW.md`. Listening page: <http://localhost:8080/tools/catalogue-listening.html>.
- **Game published 2026-10-03 (commit `651e2fc`, Galvin's go-ahead)**: `index.html` (Full song / Quick play,
  scoring lab, full screen, keep screen awake), `manifest.webmanifest`, `assets/icons/`, game tests and
  `CLAUDE.md`. Live at <https://gosubay.github.io/oohwoo/> (checked: new code, manifest and icons served).
- **Still uncommitted on purpose**: the chart-builder pipeline, `charts.json`, caches, review docs and
  `.gitignore`. Another session was rebuilding them during the push (`charts.json` was newer than the
  game's chart block; `validate_charts.py` said "generated chart block is out of date"). Whoever finishes
  that rebuild runs `apply_to_game.py`, validates, then commits and pushes.
- Automatic checks, all passing: `validate_charts.py` OK; `build_charts.py --check` = no differences on
  re-run; `python tests/chart-builder.py` (57 fixtures); all 14 `tests/*.cjs` including
  `scoring-lab.cjs`, `catalogue.cjs` (every song, both modes, simulated start to finish) and the new
  `play-modes.cjs`. Browser check: Five Little Monkeys Quick play started 16.8 s into the recording and
  completed; Twinkle Full song loads over 1:29 (now 84 notes).

## Full screen mode (added and published 2026-10-03)

- Button top-right of every screen except gameplay. Android/iPad: real full screen + portrait lock.
  iPhone: shows "Add to Home Screen" steps (no full-screen button exists for web pages on iPhone).
  New files: `manifest.webmanifest`, `assets/icons/`, `tests/fullscreen.cjs`. Spec: `CLAUDE.md` "Full screen".
- Checked: `tests/fullscreen.cjs` and all other `tests/*.cjs` pass; button, iPhone help panel and layout
  seen in the preview browser; a refused request shows the help panel and logs `[fullscreen] refused`.
- **Not checked: actually entering full screen.** The preview pane never answers the request and the
  Chrome window was in the background (browsers refuse then). Needs one tap on a real Android phone, and
  the Add to Home Screen route on a real iPhone (including that the mic still works from the icon).
- Keep screen awake (added 2026-10-03 after Galvin confirmed the dimming): wake lock held on the gameplay
  screen only. `tests/screen-awake.cjs` passes. Not seen granted for real: the preview pane counts as a
  hidden page, where the game (correctly) does not ask. Needs a real phone through a full song, which
  needs the published https site (wake lock, like the mic, does not work over the plain Wi-Fi address).
- Flagged, not done: no "rotate your phone" hint on iPhone in landscape; no pause
  button on phones (pause is the Esc key only).

## Waiting on Galvin

1. **Listen** (listening page, then in the game with "Hear my guide melody" ticked) and say per song or
   section "good" or what is off. Start with the regions listed in the review doc.
2. Test full screen and keep-awake on a real phone at <https://gosubay.github.io/oohwoo/> (Android: tap the
   top-right button; iPhone: Add to Home Screen, then check the mic still works from the icon).
3. **Xiao Yan Zi**: the recording is 7:18 and about 4.5 minutes of it is an unscripted, ornamented coda.
   Full song currently includes it (432 notes). Keep it, or end Full song after the English verses (~2:35)?
4. **Chan Mali Chan**: the English and Mandarin choruses have a second, low voice; the melody notes there
   are unreliable (flagged, not replaced). Options: leave for listening, or leave those choruses out.
5. Still open from before: keep/retire the scoring lab; live singing review of Steps 6 and 7; the songs
   wider than one octave.

## Known weak spots (implemented, not resolved)

- Fixed 2026-10-03 after Galvin's screenshot: Twinkle's Mandarin words sat on the wrong notes in lines 2, 4
  and 6. Cause was not punctuation (the "·" boxes were notes with no word) but short slides into a note
  being counted as notes, pushing later words one note late. Rule now in `build_charts.py`
  (`is_scoop` / `merge_scoops`): inside a line, a note of 0.18 s or less that runs straight into a longer
  note (rising 1-2 semitones, or passing between its neighbours) joins that note unless the line needs
  it for a syllable. Twinkle's 42 Mandarin words now sit on the 42 melody notes. The same rule changed
  9 lines in six other songs (Brother John, More We Get Together, Wheels on the Bus, Five Monkeys,
  Xiao Yan Zi, Chan Mali Chan). The listening page now shows a no-word note as ♪.
- Twinkle Mandarin: Galvin heard no voice at the low A3 after 睛 (69.4-70.0 s); removed by a `noteEdits`
  delete in `songs/twinkle.json`. Galvin then called Twinkle correct -> both sections and the song are
  `owner-listening-approved`.
- Two Tigers (Brother John) Mandarin, fixed 2026-10-03 after Galvin said it was buggy; **needs his
  re-listen**. Causes: verse 3's last 怪 had been given to verse 4 (boundary now set by `sectionOverrides`
  in `songs/brotherjohn.json`), which put verse 4 one note late; a 1 s held D4 was really 虎 + 两; one
  note was really B4 then A4; two slides (E4 into F#4 on 跑, C4 into 怪) were counted as notes. These are
  `measuredNoteEdits` in the song file (new: split / join / midi on a measured note, each with its
  evidence; a locator that matches no note stops the build). One judgement call to listen for: verse 4's
  first 奇 (1:34.9) is sung sharp of A3 while sliding up; charted as A3 like the other three times.
  Both Mandarin verses are now 32 words on 32 notes with the same tune as the English verses.
- The same "last note of a verse handed to the next verse" slip may exist in other songs; not searched
  song by song. Signs on the listening page: a verse whose last box holds two words, and the next verse's
  words running one note late.
- Head Shoulders: one-note lyric slip in the repeated lines; English verse 2 is placed by hand windows.
- Baby Shark Mandarin: Whisper could not transcribe it; words are spread from the reference by section
  (63 reference syllables not placed). 爸爸/爷爷 verses are an octave lower in the recording itself.
- If You're Happy: English verse 4 and Mandarin verse 8 of the lyric sheet are not in the recording.
- Sung words that differ from the lyric sheet are shown as sung (Old McDonald 小鸡 for 小猪, Finger Family
  爸爸 for 宝宝, ...) — listed in the review doc.
- `CLAUDE.md` calls Twinkle's verse "owner-approved by ear", but the embedded chart's own provenance still
  says `ownerApproved: false` / `listeningVerified: false` (a test asserts it). Left as found; ask Galvin.

## How it is built (2026-10-03 pipeline)

- `tools/chart-builder/songs/<key>.json` — the correction layer per song: recording hashes, language
  blocks and reference verses, section overrides, Quick play choice, note edits, review status. The
  builder refuses a file whose hashes no longer match the audio.
- `transcribe_sections.py` (Whisper, language-forced, cached) -> `build_charts.py` (notes, lyrics, splits
  at measured attacks, independent pitch check, sections, both modes) -> `apply_to_game.py` (generated
  block) -> `validate_charts.py` -> `report.py` (review doc + listening page). Commands are in `CLAUDE.md`.
- To record Galvin's approval: set `review.sections.<id>` or `review.song` to
  `owner-listening-approved` in the song file, rebuild, apply.
- `.gitignore` changed from `songs/` to `/songs/` so the correction files in `tools/chart-builder/songs/`
  are no longer ignored (the root `songs/` source MP3s still are). The builder and validator check those
  source MP3 hashes, so a fresh clone without the root `songs/` folder cannot rebuild until that is relaxed.
- Old builder kept for reference: `tools/chart-builder/legacy/build_charts_2026-10-02.py`; old charts:
  `docs/catalogue-analysis/charts-2026-10-02-excerpts.json`.
- Tests default to Quick play (`tests/game-harness.cjs`, `mode` option) so the Twinkle reference tests
  keep testing the approved 42-note verse; `catalogue.cjs` and `play-modes.cjs` cover both modes.

## Earlier state (2026-10-02 and before)

- Gameplay rebuild steps 1–7 are committed (`41eed79`). Stage gates and approvals live in
  `docs/IMPLEMENTATION-HANDOVER.md` and `docs/TASK-BRIEFS.md` — read those before changing gameplay.
- Twinkle has an owner-approved chart built from its recording (Step 3).
- **The other 21 songs were re-charted from their recordings on 2026-10-02** and are in the game as
  drafts. Full write-up, per-song table, weak spots and the listening procedure:
  `docs/STEP9-CATALOGUE-REVIEW.md`.

## Waiting on Galvin (2026-10-02 list, superseded by the list above)

1. Listen to each of the 21 songs with "Hear my guide melody" ticked and say "good" or what is off
   (procedure in `docs/STEP9-CATALOGUE-REVIEW.md`). No song is verified until he says so.
2. Decide: keep excerpts (about 15–45 s of singing each) or go to full-length songs.
3. Decide what to do with the nine songs whose melody is wider than one octave (may be hard to sing).
4. Still open from before: live singing review of Steps 6 and 7.

## What was done on 2026-10-02 (this session)

- Audit: old hand-typed charts matched the singer on only 0–28% of notes; cause was generic
  melodies on a metronome beat with only the first note aligned.
- Built `tools/chart-builder/` (vocal track -> notes -> lyrics -> chart). Run on Twinkle it
  reproduces the approved chart: 42/42 notes and lyrics, starts within 0.21 s.
- Generated 21 charts (1,371 notes) into the `// <catalogue-charts>` block of `ooh-woo-game.html`;
  deleted the old note lists and the `SONG_TONICS` key table.
- Game: each song now draws its own pitch range on screen (`laneWindow`); Do-Re-Mi names repeat per
  octave; song cards read "Charted from recording · Listening review pending".
- Audit after the change: 91–100% of notes on sung pitch per song. All tests in `tests/` pass.
- Rule recorded in `CLAUDE.md`: charts come from recordings, never typed from memory; the generated
  block is never hand-edited.

## Departures from the written plan (Galvin's instruction)

Step 9 says full Twinkle first, small agreed batches, and Step 8 review beforehand. Galvin asked for
all songs at once, so all 21 were drafted in one pass. Approval is still per song.

## How to re-run

See "Re-running" in `docs/STEP9-CATALOGUE-REVIEW.md`. Needs numpy, ffmpeg and faster-whisper (all
installed on this PC; Whisper large-v3 is cached locally and uses the GPU).

## Not committed on purpose

Pre-existing untracked files from earlier sessions (`batch_transcribe.py`, `transcribe_song.py`,
`separate_vocals.py`, `lyrics_raw.txt`, `transcriptions/`, `tools/catalogue-review.html`) and the
modified `docs/step4-synthetic.json`. The earlier handover says to preserve them, not bulk-stage.
