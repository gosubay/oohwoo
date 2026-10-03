# HANDOFF — OohWoo

Last updated: 2026-10-03 evening (SGT)

## Where things stand

- Galvin's rule (CLAUDE.md, "Chart review is Claude's job"): he does not audit songs one by one. Claude
  runs the audio-based review and repair across all 22 songs and brings him only specific unresolved
  passages. "Not listening-verified" is an honest status, not a blocker.
- **Second pass done 2026-10-03**: the note-and-word builder was rebuilt around the root causes found
  (not per-song patches). All 22 songs regenerated: 5,028 notes (was 4,613). Notes that held several
  syllables fell from 275 to 42; verse-boundary slips fixed in 14 songs; Two Tigers and
  Twinkle now come out right with no hand corrections.
- Root causes fixed: (1) a verse's last note was handed to the next verse (transcript times run early);
  (2) the note reader treated real short notes as slides and merged repeated syllables on one pitch, before
  it knew the words; (3) words were placed from transcript times alone, which are often a syllable off.
- **Listening-verified: Twinkle only** (Galvin, listening page, 2026-10-03; its Mandarin verse is unchanged
  by the second pass apart from one note starting 0.1 s later). Everything else is `owner-listening-pending`.
- The game (Full song / Quick play, full screen, keep-awake) was committed and pushed by another session
  as `651e2fc`, with the first-pass charts. The second-pass charts are in `index.html`'s generated block.
- Automatic checks, all passing: `validate_charts.py` OK; `build_charts.py --check` no differences;
  `python tests/chart-builder.py` 65 fixtures; all `tests/*.cjs`.
- Listening page <http://localhost:8080/tools/catalogue-listening.html> now plays **Singer + music** by
  default (it used to play the game's music-only track, which is why Galvin heard no singer).

## Unresolved passages for Galvin (each with a recommendation)

1. **Xiao Yan Zi, 2:58 to the end (7:18)**: about 4.5 minutes of unscripted, ornamented singing after the
   English verses (242 notes with no words). Recommend ending Full song at about 2:35.
2. **Chan Mali Chan choruses (0:27-0:45, 1:04-1:30, 1:50-2:15)**: two voices at once; the melody reading
   is unreliable. Recommend leaving the choruses out of scoring (music keeps playing, no notes to hit).
3. **Baby Shark "Let's go hunt" (0:54-1:03) and the Mandarin 爸爸 / 爷爷 verses (1:28-1:36, 1:47-1:59)**:
   sung in a low growl an octave down, pitch unsteady. Recommend leaving these out of scoring too.
4. **Baby Shark Mandarin (1:11-2:08)**: the transcriber cannot hear the words, so about 60 syllables are
   not placed on notes. Notes are charted; the words shown are approximate. Recommend accepting for now.
5. **If You're Happy**: the lyric sheet's English verse 4 and Mandarin verse 8 are not in the recording.
   Recommend removing them from the lyric sheet.
6. **Two Tigers, 1:35**: the first 奇 of verse 4 is sung sharp while sliding up; charted as A3 like the
   other three. Recommend keeping.
7. **Twinkle, 1:09**: the low wordless note after 睛 is the singer's voice dipping to A3 (measured, steady
   for 0.4 s). It was briefly removed on a misreading of Galvin's remark and restored. Recommend keeping
   it out of scoring if it feels odd to play.

## Still imperfect, no decision needed (leads, not blockers)

- `python tools/chart-builder/selfcheck.py --lines` lists about 200 lyric lines where one or two syllables
  sit on a pitch no other verse uses there. Many are the singer really varying the tune or a short note
  read a semitone off; none is corrected automatically (pitch flags are leads, never replacements).
- Wordless "ooh / da da" hooks at the start of More We Get Together (0:00-0:12, 0:43-0:49) and Little Bunny
  (0:46-0:55) are charted as wordless notes inside the verse that follows them.
- Mary Had a Little Lamb is sung fast with a tune that differs from the standard one; words may sit one
  note off inside a line.

## Waiting on Galvin

- Normal playtesting feedback, and the seven decisions above (each has a default if he says nothing).
- Still open from before: keep/retire the scoring lab; live singing review of Steps 6 and 7.

## How it is built (2026-10-03 pipeline)

- `tools/chart-builder/songs/<key>.json` — the correction layer per song: recording hashes, language
  blocks and reference verses, section overrides, Quick play choice, note edits, review status. The
  builder refuses a file whose hashes no longer match the audio.
- `transcribe_sections.py` (Whisper, language-forced, cached) -> `build_charts.py` (atoms from `atoms.py`,
  lyric-aware notes, sister-verse evidence, independent pitch check, sections, both modes) -> `apply_to_game.py` (generated
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
