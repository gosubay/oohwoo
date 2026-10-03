# Catalogue correction — plan (2026-10-03)

Source brief: [CLAUDE-CATALOGUE-CORRECTION-HANDOFF.md](CLAUDE-CATALOGUE-CORRECTION-HANDOFF.md) and its evidence in
`catalogue-review-2026-10-03/`.

## Goal

Every one of the 22 songs gets a **Full song** chart (every sung section, language and repeat in the
recording, natural ending) and a separately labelled **Quick play** excerpt, built from the recording by a
rebuildable pipeline whose corrections live in versioned files. Nothing is called "verified" until Galvin
has listened.

## Steps

1. **Correction layer** — `tools/chart-builder/songs/<key>.json` per song: asset hashes, section inventory
   (language, verse label, sung/wordless, start/end), Quick-play bounds, lyric corrections, note edits by
   stable note ID, each with old/new value, reason, evidence and confidence, plus review status
   (`automatic` → `contributor-reviewed` → `owner-listening-approved`). The builder refuses a file whose
   hashes do not match the audio.
2. **Language-aware lyrics** — re-transcribe each sung section with the locally cached Whisper model,
   forced to that section's language, once with and once without the reference lyrics as a hint.
   Reconcile against `lyrics_raw.txt`: same-position substitutions take the reference spelling (logged),
   extra sung words are kept (flagged), reference words that were not heard are never forced onto notes.
   Separate syllable rules for English, Malay (sa-yang, sa-ya, di-a, bu-ah …) and Mandarin (one character
   per syllable).
3. **Notes from the whole recording** — run the existing note reader over the full vocal stem; keep
   only notes inside charted sections. Remove the three defects: equal-time syllable splits (replace with
   splits at measured loudness dips, or leave one note marked "shared" when there is no evidence),
   merging of same-pitch notes just because the transcript had no word, and automatic neighbour-based
   octave "fixes" (now only applied when the independent estimator agrees).
4. **Independent check** — the 2026-10-03 YIN estimator re-measures every new note. Disagreements are
   labelled on the note and listed per song; they are leads, not automatic pitch edits.
5. **Twinkle** — the approved English verse is copied note-for-note; only its later Mandarin verse and
   ending are added for Full song. Quick play for Twinkle is exactly the current approved excerpt.
6. **Game** — Full song / Quick play toggle on the song card with duration and languages from chart data;
   one mode-aware source for notes, phrases, level bounds, guide, progress, scoring and completion. Quick
   play may start mid-file: only its own notes are scheduled, judged and shown.
7. **Checks** — deterministic rebuild with a dry-run diff; validator for every interval, ID, order,
   pitch, bound, hash and section; Malay/Mandarin/split fixtures checked against the audio; game tests
   for both modes (start, pause/resume, retry, last hold, fade, completion, frame rates, stall, nonzero
   Quick start); existing tests including `tests/scoring-lab.cjs`.
8. **Handback** — per-song before/after table, unresolved regions, a listening page with focused links,
   HANDOFF.md and CLAUDE.md updated. No commit/push without Galvin's go-ahead (the scoring lab in the
   working tree is temporary and pushing may publish the site).

## Success criteria

- All 22 songs playable in both modes; Full charts cover every sung section the recording contains.
- `python tools/chart-builder/build_charts.py --check` reports no difference on a second run.
- Validator and all tests pass; the scoring lab and audio-clock work in the working tree still behave.
- Every song and section shows `owner-listening-pending` unless Galvin has approved it.
