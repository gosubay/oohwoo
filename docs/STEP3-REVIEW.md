# Step 3 — Twinkle reference verse, owner playback review recorded

2026-10-01. Implementation and numerical checks complete. Following the listening-inspector procedure, Galvin reported “sounds good, it works.” Positive human playback/listening acceptance is recorded. The feedback does not specify an exhaustive note-by-note audit or real-microphone playtest; detailed timing uncertainty and live-voice checks remain documented below. Steps 4–10 have not been started or approved here. No commit, publishing, branch change, or audio replacement was made. Existing checkout work was preserved.

## What changed

Twinkle now has one 42-note chart containing D4–B4 pitches/MIDI, absolute backing timestamps, explicit ends, syllables, six phrases, rests, separate draft beat markers, and level bounds. Targets, guide durations, and lyric highlights use those same note events. Repeated pitches remain separate syllables. Lyrics clear in authored gaps. The last D4 lasts through 39.90 seconds, followed by a deliberate backing fade from 40.00 to 40.60 seconds; finishing no longer depends on the last coin disappearing. This excerpt includes the recording's introduction and one English verse.

The existing Low/Medium/High guide choices preserve the chart's intervals in D3/D4/D5 registers. The recording's vocal reference is D4–B4. This stage does not add key transposition, new microphone behaviour, sustain scoring, flight paths, or the later combo changes. Prototype gameplay limitations still apply, including the demonstrated low-note detector issue and scoring that depends on bird position.

Other songs keep their existing note arrays and audio. Their chart status is `legacy-unverified`; song cards say listening review is pending. Their musical accuracy and catalogue counts were not verified in this stage.

## Assets and evidence

`audio/` contains 23 MP3s, including both Rain Rain variants. `docs/audio-inventory.json` records the current path, size, and SHA-256 of every file. All three exact Twinkle hashes are embedded in the chart's provenance, together with their source paths; `tests/chart.cjs` verifies all these assets remain unchanged.

| Evidence | Result | What it establishes |
| --- | --- | --- |
| Browser Web Audio decode | Source, backing, vocal each 88.96 s | Actual decoded length, rather than rounded transcription metadata |
| Numerical comparison, 8–40 s | Backing and vocal delays both 0.000 s at 0.363 ms lag resolution, +/-100 ms search | Relative alignment of these files; does not establish absolute note onsets |
| Least-squares source reconstruction | Backing gain 1.00018; vocal gain 0.99953; relative RMS residual 3.51% | Strong evidence these are complementary stems of this source, allowing lossy encoding/separation error |
| Independent vocal autocorrelation | 42/42 note medians within 0.35 semitone of chart pitches, over 15 reliable frames each | Numerical support for D4–B4 melody including octave; not proof of lyric attacks/rests |
| Numerical phrase-release inspection | Releases 14.76, 19.70, 24.50, 29.35, 34.22, 39.90 s | Provisional release/gap corrections; tolerances require listening |
| `node tests/timing.cjs` | PASS | Existing runtime regression suite with chart-aware timestamp/end assertions |
| `node tests/chart.cjs` | PASS | Hashes, pitches/octaves, coverage, phrases, guide durations, backing fade/end, fixed deadlines at 30/60/120/144 fps, simulated pause/resume, lyric clearing |
| Chrome inspector | Three assets loaded/decoded; full excerpt playback clock advanced and stopped | Browser playback can start/finish; visual waveform and chart available |
| Chrome game | Reference card shows 42 notes / 41s; playback launched and completed with no microphone fallback | Real browser launch/completion check; score is not evidence of valid singing |
| Owner playback/listening review | **Positive feedback recorded, 2026-10-01** | Galvin reported “sounds good, it works” after the inspector listening prompt; detailed phrase-by-phrase coverage was not reported. The agent did not hear the recording. |
| Real microphone / live singer comfort and fun | **Pending** | Requires Galvin and later a second comfortable range; synthetic tests do not qualify |

`docs/twinkle-analysis.json` contains the numerical method, chart SHA-256 (embedded JSON text with LF normalised), asset provenance, relative-alignment/reconstruction metrics, per-note medians, and 10 ms frame data. Autocorrelation uses 186 ms windows and amplitude/confidence filtering on the separated vocal. It can confuse harmonics and cannot resolve a consonant or a repeated-note syllable merely from pitch. No separation model was rerun. `batch_instruments.py` describes a Demucs non-vocal sum but skips existing outputs, so execution history is unknown. Numerical reconstruction supports an instrumental stem; audible vocal bleed and backing sound quality remain unverified. Other audio files were inventoried/hashed, not content-verified.

## Remaining chart uncertainty

Onsets retain the automatic draft's beat positions (10.33–38.66 s), not verified syllable attacks. Allow up to **0.35 s uncertainty**, particularly the first note of a phrase, slides, and consonants. Most within-phrase note ends are provisional next-onset-minus-80-ms articulation boundaries. Phrase ends were corrected by inspecting reliable vocal frames and decay, with roughly 0.12 s window/decay uncertainty. Short gaps are explicitly labelled syllable gaps, rather than claims of silent accompaniment. Beat markers remain an automatic draft and do not drive notes.

The six standard lyric lines were retained from the authored verse and need checking against this exact singer. The authored ending falls in the numerical inter-verse vocal gap; its musical naturalness needs ear approval. Do not describe the chart as recording-verified or expand it to a full song before this review.

## Galvin's exact listening procedure

1. Open the game with `start-game.bat`, using localhost. In the same browser open `http://localhost:8080/tools/twinkle-review.html`. The normal server supports listening and editing previews; numerical analysis needs the optional server below.
2. Press **Load three recordings**. Use headphones. Select **Original recording**, tick **Chart guide**, choose **Whole verse including ending**, and press **Play section**. Listen through the intro, all six lyric lines, the last held “Are,” and the fade. This is about 41 seconds.
3. Review each of the six phrases in order using **Section** and **Loop section**. First compare original plus guide; then untick guide and listen to **Separated vocal**. Check every syllable's attack/release, repeated notes, pitch/octave, lyric spelling, and breaths. The gold cursor and green chart bars show where the chart thinks they belong. Pay particular attention to phrase 1 (10.33 s), the middle phrases (20.36–29.35 s), phrase 5 (30.00 s), and phrase 6/final hold (34.85–39.90 s).
4. Select **Instrumental backing** with guide on and repeat the whole excerpt. Confirm the guide fits the backing key and timing; listen for distracting vocal bleed. Judge whether the fade after the final tonic feels finished, and whether the introduction is acceptable for this reference level.
5. If something is early/late, report the note ID (for example `n07 Star`), expected change, and recording time. You can edit MIDI/onset/end in the table and replay immediately; **Export edited draft JSON** saves a review draft for a contributor to validate/incorporate. It does not change the game or grant approval. No device-latency adjustment should be used to conceal a chart mistake.
6. Open the game, choose Twinkle, and play with **Hear my guide melody** on. Medium matches the recorded vocal octave; Low is one octave lower. Sing the verse, try Escape pause/resume midway, and retry. Check start/middle/end alignment and that the final note is allowed to finish before results. Treat microphone detection, comfort, scoring/holds, silence movement, and combo issues as later-stage findings. The current detector may reject low voices.
7. Report approval or any corrections above. Galvin's positive playback/listening feedback is now recorded; detailed corrections can still be incorporated if discovered. This report does not approve Step 4.

## Optional numerical recheck / authoring tool

From the repository root run `python tools/reference-server.py` in a Python environment with numpy (the desktop's bundled Python used here has numpy). It binds only to 127.0.0.1:8081. Open `http://localhost:8081/tools/twinkle-review.html`, load the recordings, and press **Run numerical analysis**. The browser decodes/downmixes/resamples audio and sends PCM only to this local server; PCM stays in memory and only the evidence JSON is written. Stop that workspace server with Ctrl+C when finished. A regular HTTP server is sufficient for all listening controls and edited-draft export.

Validate changes with `node tests/timing.cjs` and `node tests/chart.cjs`. Update the embedded JSON in `ooh-woo-game.html`, recompute rests/level bounds when timings change, regenerate numerical evidence against that same chart, and repeat human listening. Never silently set `listeningVerified` or `ownerApproved` from an automated result.

## Files touched in this stage

- `ooh-woo-game.html`: embedded reference chart, chart consumers, ending, honest review labels.
- `tests/timing.cjs`: chart-loading fixture and updated shared-onset/end assertions.
- `tests/chart.cjs`: reference chart, asset, numerical evidence, guide/backing and clock checks.
- `tools/twinkle-review.html`, `tools/reference-server.py`: local playback/loop/editor and optional numerical inspection.
- `docs/audio-inventory.json`, `docs/twinkle-analysis.json`, `docs/STEP3-REVIEW.md`: provenance, evidence and review instructions.
- `docs/step3-browser-complete.png`, `docs/step3-inspector.png`: browser completion and inspector screenshots.
- `docs/TASK-BRIEFS.md`: Step 3 progress and review gate; later approvals unchanged.

No baseline backup was restored. Existing project documents and assets outside the listed stage changes were preserved.
