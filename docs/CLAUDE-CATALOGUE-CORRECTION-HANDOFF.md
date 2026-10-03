# OohWoo: recording-faithful catalogue correction

Prepared 2026-10-03, Singapore time. Intended implementer: Claude Code, using the owner's requested Opus 5.5 / High configuration if available in their installation. This document has not been sent to a Claude session. It does not claim that model was launched.

## Owner's request and outcome

Galvin says Twinkle feels close, while the other 21 songs feel worse, especially Chinese and Malay. Review and correct placement for all songs, then implement the correction. Explain and address the unexpectedly short songs. Retain the recent temporary scoring selector and audio-clock work in the existing working tree.

Recommended product assumption, pending a different owner preference: Full song is the normal experience; Quick play remains a separately labelled excerpt. Include the actual recording's sung language sections and repeated verses. Never extend playback into an uncharted section and call it complete. The owner has requested catalogue correction; proceed with reversible preparation and implementation without asking for the same permission again. Listening verification is an acceptance requirement, not a reason to stop all useful work.

## What has actually been reviewed

- All 22 current charts, all 1,413 note events, the chart/transcription pipeline, and the supplied lyric reference.
- Independent numerical pitch measurement of every full separated vocal recording, using a different estimator from the chart builder. Source/backing/vocal asset hashes and container durations are recorded in `catalogue-review-2026-10-03/note-evidence.json`.
- Results and exact per-note locations: `catalogue-review-2026-10-03/REVIEW.md`, `summary.json`, `note-review-queue.json`, and `note-evidence.json`.
- Specific lyric corrections and alignment rules: `catalogue-review-2026-10-03/correction-manifest.json`.
- These are numerical and source reviews, NOT a claim of listening to all recordings, NOT corrected or approved timing data. No chart was overwritten. The audit's pitch candidates must not be blindly applied.

## Why the songs are short — confirmed implementation behavior

`tools/chart-builder/build_charts.py` uses `MIN_EXCERPT=15`, `TARGET_MIN=24`, `MAX_EXCERPT=45`, `INTERLUDE=2.5`. It chooses the first break after 15 seconds when the next stretch is separated by 2.5 seconds, has a median register difference of 7 semitones, or lacks transcript words. Otherwise it uses a breath around 24–45 seconds. These are heuristics, not true verse boundaries. The minimum rule can continue across the first verse; the soft maximum is not a strict cap.

`level.end` then schedules a backing fade/stop and ends gameplay. Audio files are intact. Full-length song work was explicitly left unfinished in `docs/TASK-BRIEFS.md` Step 9. Rasa Sayang currently includes the Malay and English stretches but stops before the later Chinese stretch; it is not simply 'one language for every song.' Twinkle is a reference verse too.

Do not just raise `level.end`, loop the existing notes, or copy an English verse's timings to its translation. Repeats and different languages may change timing, syllable counts, melody, octave, and phrase lengths.

## Confirmed pipeline defects and risks

1. **English syllabification is applied to Malay.** Vowel grouping treats `y` as a vowel, collapsing `sayang` and `saya` into single syllables. Consecutive-vowel words such as `dia` and `buah` are also collapsed. This shifts the distribution of syllables among notes. Use language-tagged sections and recording-confirmed syllables, with explicit Malay entries where needed; do not use one English heuristic for all languages.
2. **Transcript text is treated as usable lyrics without correction.** Examples include 把/巴/抱萝卜, 春花一, 念念, `dikubas`, `peyang`, and `oh boy`. The repository's `lyrics_raw.txt` supplies intended wording. Treat it as a reference, not proof of what an AI-generated singer actually performed. Correct ordinary written homophone errors, and listen for substitutions, omissions, and extra repetitions. Never force missing reference words onto unrelated notes.
3. **Equal-time division manufactures onsets.** `build_charts.py` divides a note carrying multiple syllables into equal durations and inserts 40 ms gaps. 233 current notes have the resulting `split` marker. These boundaries are not acoustic measurements. Preserve real syllable attacks and releases; if uncertain, mark them uncertain rather than manufacture precision. Do not create scoring silence where the singer sustains.
4. **Missing transcript labels can erase real repeats.** The builder merges same-pitch notes when the later note has no lyric and the gap is under 60 ms. Missing ASR text is not evidence of a melisma. Separate same-pitch syllable attacks from continuing vowels using the recording.
5. **Pitch cannot establish words or rhythm on its own.** The old 91–100% result compares a note's median pitch to an autocorrelation measurement closely related to the builder. It does not verify syllable boundaries, releases, missing verses, or independent accuracy. `tests/catalogue.cjs` synthesizes a perfect singer FROM the chart; it proves runtime consistency, not musical correctness.
6. **Onsets and tuning need evidence.** Builder frames span about 186 ms; short scoops, register changes, short notes, and octave choices need inspection. Whole-recording tuning is subtracted before rounding, while the backing remains in its original tuning. Do not automatically retune every song, impose a major scale, or use neighbour proximity as proof a leap is wrong. Check original source and separated vocal where either estimator disagrees.
7. **Language/register switches are not endings.** Rasa Sayang's whole-file transcript language is `en` despite Malay/English/Chinese sections. Single song-level language cannot govern bilingual alignment. Lack of ASR text does not prove silence. Wordless hooks can be playable; decide their treatment from sound and explicit section metadata.
8. **Long asset anomaly.** Xiao Yan Zi is approximately 438.4 seconds, much longer than the anticipated 1–2 minutes. Inspect its complete source, repeated material, and tail. Preserve it; do not silently truncate, deduplicate, or substitute an asset.

## Implement in this order

### A. Make corrections durable and reviewable

Add a versioned, source-hash-bound correction layer to the builder for phrase bounds, syllable text/attacks, musical pitch events, and include/exclude decisions. A corrected JSON chart must not lose edits on the next rebuild. Maintain the distinction between automatically proposed, contributor-reviewed, and owner-listening-approved.

For every change record song, original note/phrase locator, old/new values, evidence/reason, and confidence. Current indices in the manifest are ZERO-BASED and only valid with its chart source hash. Reject a stale hash; do not silently match another note by index. Generate stable note IDs for new full charts. Keep all legacy files and uncommitted user work.

Keep `index.html` as the runnable game. The catalogue block is generated: edit chart sources/corrections and use `tools/chart-builder/apply_to_game.py`, never hand-edit the generated block. Existing documentation mentioning `ooh-woo-game.html` is stale.

### B. Establish language-aware alignment

Inventory every recording's sections using audio plus the supplied lyric text: language, repeat identity, singer/register, sung/wordless/instrumental, onset and end. ASR times are rough anchors, not scoring deadlines. Use language-constrained transcription/alignment only when those tools are available; do not install or download a model unnecessarily.

Correct Mandarin words/characters and Malay syllables before aligning. Mandarin characters are useful lyric units but can span multiple musical notes; English/Malay words can span syllables and pitches. Support one syllable across several pitch events and repeated syllables on one pitch. Keep lyric timing and musical note timing separate where needed. Do not generate extra scoring targets merely because a word has more characters.

Measure consonant/voicing attacks, stable pitch centres, release/breaths, and sustained vowels from original/source and vocal stems. Pitch-centre onset and heard syllable onset may differ; inspect them rather than shifting every onset by a constant amount. Existing reference Twinkle can legitimately begin before stable periodic voicing.

### C. Correct all songs, with an early quality checkpoint

First prove the method on the approved Twinkle excerpt and the problematic Ba Luo Bo, Xiao Yan Zi, Rasa Sayang, and Chan Mali Chan sections. Preserve the close-feeling Twinkle excerpt unless recording evidence warrants a specific correction. Use the per-note queue to loop small regions with source/vocal/guide independently selectable. Listen to the whole corrected section, not just the flags, because automatic checks can miss errors.

Then apply the method to all remaining songs, prioritizing Mary Had a Little Lamb, Five Little Monkeys, If You're Happy, Little Bunny, and The More We Get Together from the independent numerical triage. Flags can overlap and can arise from tuning, slides, harmonic ambiguity, or stem artifacts; they are not an automatic pitch edit list.

For each song deliver a corrected current excerpt AND complete full-song chart. Extend Twinkle through its actual later Mandarin section and ending. For every other song chart all actual verses/languages/repeats, preserve intentional rests/interludes, and record explicit full and quick-play bounds. Do not infer complete full charts by repeating the first verse.

### D. Integrate full-song/quick-play selection

Expose Full song / Quick play in song selection, with accurate duration and languages from chart metadata. Make the distinction clear before playing. A full run must use the full chart, full audio boundaries, correct final hold, and natural ending. Quick play must be a reviewed subset with an intentional fade.

Use absolute recording timestamps consistently for audio offsets, notes, lyric display, progress, guide, scoring, and completion. Recent `backingStartTime` changes account for nonzero level starts and output latency; preserve them. If Quick play begins mid-file, only schedule guide notes in its selected interval and initialize note judgements/cursors to that interval. Do not create oscillators for notes before the source offset. Do not let later full-song notes score as misses in Quick play.

Preserve the scoring lab's strict/relaxed/coins/hybrid modes, pitch detection, and flight feel. Keep source pitch versus playable octave adaptation explicit. Expanding full-song ranges must not silently squash pitch semantics or make keyboard practice unreachable. Do not overwrite the single-file game from an older duplicate.

### E. Acceptance and handback

- Deterministic rebuild: sources plus overrides regenerate the same game chart, with a dry-run diff of what changes.
- Validate every note and lyric interval, stable IDs, ordering, finite pitches, chart bounds, source hashes, explicit sections/rests, and no unintended overlap. Melismas and repeated syllables must be represented deliberately.
- Fixtures for Malay `sa-yang`, `sa-ya`, `di-a`, `bu-ah` and recorded exceptions; Mandarin homophones; unequal same-pitch syllable durations; notes without ASR words; language/register switches; and true melismas. Fixtures must check audio-backed boundaries rather than just reproduce the algorithm.
- Independent estimator disagreements are resolved or explicitly labelled; do not convert candidate pitches such as implausible subharmonics directly into notes. Show per-song before/after issues and unresolved regions.
- Play original vocal against guide for every corrected section and full-song end. Check exact source/backing/vocal alignment; similar durations alone do not prove zero offset or drift.
- Exercise each Full/Quick combination through start, pause/resume, retry, last hold, fade, and completion. Check timing at multiple frame rates and under a stall. Check guide and progress at a nonzero Quick start. Run the existing relevant tests, including `tests/scoring-lab.cjs`, without bulk-staging unrelated files or refreshing unrelated evidence fixtures.
- Track review status per section and whole song. Numerical test success never equals listening approval. Owner listening/live singing remains required to call the new charts verified; plainly report any audio/device limitation.
- Deliver the edited game, durable correction sources, the all-song before/after table, focused review links, and exact remaining uncertainties. No automatic commit, push, or deployment was requested.

## Audit reproduction

The audit script needs only numpy and ffmpeg/ffprobe. In this Codex environment it ran with:

```powershell
& 'C:/Users/Admin/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' tools/catalogue-audit/review-placement.py --ffmpeg 'C:/AI/GPT-SoVITS-v2pro-20250604/runtime/ffmpeg.exe' --ffprobe 'C:/AI/GPT-SoVITS-v2pro-20250604/runtime/ffprobe.exe'
```

Use existing equivalent tools in Claude Code if available. The audit is local and sends no audio to an external service. It writes only its dated review directory. The source recording remains the authority; the audit is a triage aid.
