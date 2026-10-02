# HANDOFF — OohWoo

Last updated: 2026-10-02 (SGT)

## Where things stand

- Gameplay rebuild steps 1–7 are committed (`41eed79`). Stage gates and approvals live in
  `docs/IMPLEMENTATION-HANDOVER.md` and `docs/TASK-BRIEFS.md` — read those before changing gameplay.
- Twinkle has an owner-approved chart built from its recording (Step 3).
- **The other 21 songs were re-charted from their recordings on 2026-10-02** and are in the game as
  drafts. Full write-up, per-song table, weak spots and the listening procedure:
  `docs/STEP9-CATALOGUE-REVIEW.md`.

## Waiting on Galvin

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
