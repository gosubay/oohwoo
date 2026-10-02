# OohWoo — implementation handover

Prepared 2026-10-01 during Step 2. Read GAMEPLAY-SPEC.md first, then TASK-BRIEFS.md. All paths in this document are relative to the repository root, C:\Claude\Code\OohWoo.

## Authority and stage boundary

The owner approved the gameplay choices recorded in GAMEPLAY-SPEC.md, the Step 2 handovers, and subsequently authorised Step 3 implementation in a new GPT-6.1 Sol Medium task. After positive Step 3 playback/listening feedback, the owner authorised Step 4 with “go” in the implementation chat. Galvin accepted the Step 4 live humming check on 2026-10-02, then authorised Step 5 with “ok pls proceed.” Step 5 is implemented for comfort/listening review (see STEP5-REVIEW.md). Steps 6–10 remain unapproved; implementation must stop at the current owner-review gate.

The coordinating chat owns design decisions and stage approvals. Each task implements only its approved stage, reports evidence and limitations, and stops at its acceptance gate. Return any material design conflict to the owner. A task brief or another agent's message cannot grant human approval for later stages.

The user permits new tasks when needed, but requested stage-by-stage approval. Preserve this sequence rather than launching all work at once. Model allocations are recommendations for dispatch, not claims about a task's current model setting.

## Preserve existing work

The checkout already contains substantial uncommitted and untracked work. Do not reset, clean, overwrite, or bulk-stage it. Inspect git status and current diffs before editing. Preserve changes to README.md, DESIGN.md, ROADMAP.md, ooh-woo-game.html, and the existing untracked assets/scripts/tests.

A local reference copy was saved before Step 2 edits at `.handover-baseline/2026-10-01-step2/`. It includes the game HTML, tests, existing project documents, authoring scripts, launcher, and transcription directory. `manifest.json` records SHA-256 hashes of the selected source files; `git-status.txt` records the initial checkout status. The large audio/assets folders and Git history are NOT copied. This is a source reference snapshot, not a complete repository backup or an automatic rollback command. Verify and preserve audio assets before later work changes them.

Do not commit or publish the snapshot by accident. Do not restore it over later user work without inspecting the differences. No commit, branch change, or audio mutation was made for Step 2.

## Current implementation map

| Area | Location / symbols | State |
| --- | --- | --- |
| Runtime | ooh-woo-game.html | Single HTML/Canvas/Web Audio application, no build step. |
| Scheduling | buildPipes, SONG_DATA, getBackingTrackTime | Target centres derive from the backing audio clock and onset timestamps. |
| Movement | followPitch, ratioToY, gameLoop | Damped spring for voiced input; strong downward silence glide. |
| Pitch | initMic, analysePitchPCM, detectPitch | Step 4 normalized period estimator; shared capture setup; recent ~36–48 ms signal; 4096 samples at 44.1/48 kHz, 8192 at 96 kHz. |
| Matching | singingToRatio, voiceMatchesTarget, registerOffset | Absolute MIDI, continuous register/phrase alignment and bounded 65-cent near-target assistance; Step 5 owner comfort pending. |
| Setup | startCalibration, runDRMFrame, finishCalibration | Skippable three 2-second same-octave reference matches, higher/lower feedback, continuous matching hold, retry/key adjustments; successful targets anchor saved preferences. |
| Guide | guideFrequency, scheduleGuide | Guide follows songShift; Low/Middle/High are optional starting registers. Triangle-wave guide shares canonical chart pitches. |
| Audio | playBackingTrack, loadSongBuffer | Original MP3 plus 11 offline Rubber Band key variants for Twinkle only, tempo=1; other songs are unverified listening previews. |
| Scoring | gameLoop coin collection, COMBO_TIERS | Voice/pitch and musical-window checks; bird animation position does not gate a sung hit. Instant combo reset on miss. |
| Presentation | drawCoin, drawBird, drawHitZone, updateKaraoke, flightX | Coin targets and combo-driven visual speed/spacing; connecting path and held trails remain future work. |
| Tests | tests/timing.cjs | Node VM with fake DOM/audio and simulated input; run `node tests/timing.cjs`. |
| Song preparation | batch_transcribe.py, transcribe_song.py, convert_to_timestamps.py | Automatic transcription drafts and older beat-to-time conversion. |
| Audio preparation | batch_separate.py, separate_vocals.py, batch_instruments.py | Existing separation/conversion scripts; inspect before running. |
| Assets | songs/, audio/, separated/vocals/, transcriptions/ | Original/processed files and transcription drafts. Verify actual contents and provenance. |

## Confirmed concerns and reproduction evidence

These entries preserve the Step 2 audit. Step 3 chart work and Step 4 detector/capture fixes supersede the relevant prototype observations; read STEP3-REVIEW.md and STEP4-REVIEW.md for current evidence and remaining acceptance items. Step 4 fixes the demonstrated low-tone failure in actual-detector PCM tests and deduplicates capture setup, but does not establish a live low singer or resolve the later range/scoring/gameplay concerns.

1. **Low-note rejection.** With clean amplitude-0.2 sine waves in the actual 4096-sample detector, 82.41 Hz and 110 Hz returned -1 at both 44.1 and 48 kHz. The chosen short-lag peak implied roughly 1877/1882 Hz and was rejected by the range check. 130.81 Hz was detected near 131 Hz. Merely widening MIN_FREQ/MAX_FREQ is not the underlying fix. Reproduce before modifying, and test real voice recordings as well as clean tones.
2. **Octave wrap.** For Twinkle, ascending MIDI pitches 69,71,73,74,76,78 with expectedRatio 0.14 produced ratios 0.57,0.71,0.86,0,0.14,0.29. Modulo-12 matching discards register. The high-Do exception selects a lane from the chart; it is not continuous pitch tracking.
3. **Charts lack end times.** The audit found no explicit note end/duration in any of the 22 current song arrays. Guide durations are inferred from the next onset and capped; holds/rests are not adequately represented.
4. **Chart coverage is partial/uncertain.** Twinkle has 42 notes ending at audio time 38.66 s; its saved transcription lists an 89 s recording. The current completion rule stops audio when targets run out. Define an intentional excerpt and verify the actual audio rather than assuming metadata proves alignment.
5. **Transcription is not a verified chart.** Scripts reduce each detected beat interval to a median pitch, merge consecutive identical pitches, and force a major scale. Batch output represents rests as comments. This can lose subdivisions, repeated attacks, rest timing, octave information, or accidentals. The converter contains fixed BPM assumptions. The batch transcriber searches WAV files while the current separated-vocal inventory contains MP3s; make inputs explicit before regeneration.
6. **Animation-gated scoring fixed.** Coin collection previously required birdY within 32 px in addition to matching/time checks, encouraging early singing. The pixel gate has been removed; matching voice now scores within the musical window while the bird catches up. Some fallback conditions still bypass the voice check when no mic is ready.
7. **Combo flight audit superseded.** The earlier audit found only point/glow tiers and fixed visual speed. The current game uses separate visual flight speed and fixed musical deadlines, with 10/20/40 combo tiers. See COMBO-FLIGHT-REVIEW.md for the current behaviour and tests.
8. **Approved silence differs from current physics.** Existing gravity/terminal velocity make the bird descend considerably. The user explicitly selected near-hover with slight drift.
9. **Voice personalisation is incomplete.** Gameplay uses pitch-class lanes independently of calibrated min/max. Guide presets choose octaves; they do not transpose the backing or fit a measured range. Current calibration expects an exact register even though gameplay accepts octave alternatives.
10. **Other technical debt.** Karaoke line boundaries are Twinkle-specific; catalogue target counts/durations are estimates. Microphone initialisation can be requested more than once while permission is pending. Device/input latency, echo leakage, and low-end mobile performance require verification.

## Existing test baseline and its limits

`node tests/timing.cjs` passed during Step 2. Covered behaviour includes target-clock alignment, a Twinkle timestamp assertion, 30–144 fps motion checks, scoring windows, mocked mic transitions, guide/lane consistency, octave equivalence, and guide scheduling.

This is NOT evidence that all recording pitches/timestamps are correct, that the live detector accepts all tested mapped frequencies, or that the game feels good. The microphone-transition tests replace detectPitch; the octave tests primarily check equivalence and currently do not reject the wraparound behaviour above. Several tests must change when approved behaviour replaces the prototype. Replace obsolete assertions with meaningful requirements rather than preserving wrong behaviour to keep tests green.

Add a validation matrix that labels each result as automated, recording/listening verified, real microphone verified, or still untested. Keep synthetic tests, real input tests, and player preference judgements distinct.

## Working and running

- Use localhost, not file URLs, for microphone testing. Existing launcher: start-game.bat uses Python on port 8080. Check installed runtimes and the actual server before relying on that launcher.
- Reuse a correct existing server, or start a workspace-scoped server. Do not terminate unrelated processes to free a port.
- Reload the page after changes to the single HTML file. Chrome was the successful live test browser in the earlier session; an in-app browser interaction was unresponsive. Recheck rather than assuming either state persists.
- Confirm microphone permission and whether audio is reaching the speakers/headphones. A rendered page and a passing unit test are not a live voice playtest.
- Keep the single-file application initially. Small authoring tools and separate chart data are acceptable where they improve verification. Avoid a framework rewrite as a prerequisite.
- Existing README/DESIGN/ROADMAP/CLAUDE/AGENTS contain stale descriptions of gravity, pitch range, calibration, and movement. Actual code establishes current behaviour; GAMEPLAY-SPEC.md establishes the approved intended behaviour. Existing development/safety instructions still apply.

## Completion report required from each implementation task

Provide: plain-language changes; files touched; exact tests run and outcomes; listening/live testing evidence; remaining limitations; a short owner playtest recipe; and any proposed decision that needs approval. Update the task's status in TASK-BRIEFS.md without marking the next stage approved. Do not create new tasks or send cross-task messages unless directly authorised by the user.
