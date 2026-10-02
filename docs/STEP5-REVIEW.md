# Step 5 — comfortable register and bounded pitch assistance

Implemented 2026-10-02 for owner comfort/listening review. Galvin explicitly authorised Step 5 with “ok pls proceed.” Step 6 remains unapproved.

## Plain-language changes

The game offers a skippable 6-second (three 2-second steps) guided check: listen, then match three specific reference notes in the same octave. Nearby tuning within 65 cents is accepted, with higher/lower/matched feedback. Each step plays a 300 ms tone and excludes the first 500 ms from capture judgement. Every note needs at least 300 ms of continuous matching input; arbitrary steady pitches or another octave cannot complete setup. Too little humming offers retry/skip. Existing preferences survive a skipped check; new successful measurements replace them.

Twinkle chooses a musical key near the centre of the measured range. Too high / Too low adjusts the next attempt by a semitone, and Reset comfort restores the starting-register choice. These controls are available in song selection and on results. Mid-song key changes are blocked. Low/Middle/High select pending setup reference notes without age/gender labels. Setup adjustment preserves saved settings until successful completion. The separate menu Voice control explicitly resets measured comfort and saved song keys.

The raw pitch keeps its octave. Rising through an octave boundary stays rising, rather than folding down to Do. A coherent octave alternative can be established between phrases with 80 ms of continuous near-target input. Once established, it is locked within the phrase. Nearby singing gets at most 65 cents of target-aware help; a clearly different note retains its own height. A held unrelated pitch cannot follow different melody notes, and unvoiced input clears the match.

## Key and backing implementation

Twinkle's authored D4–B4 chart is unchanged. `songShift` selects a total semitone shift for guide and matching. `backingKey` chooses the equivalent pitch class from −5 through +6; guide register can differ by whole octaves, which preserves the backing's harmony. This avoids extreme octave shifts of an entire instrumental mix. Visual lanes remain relative to the chart's semitone intervals, independent of the measured width.

Eleven additional instrumental excerpts are rendered offline with FFmpeg's librubberband, `tempo=1`, `pitchq=quality`, `channels=together`, `window=long`, `transients=mixed`. The original key uses the existing backing. Runtime playback rate remains 1; audio-clock deadlines, guide starts/ends, original chart and source assets remain unchanged. Only the bounded 40.60-second Twinkle excerpt is rendered. No external audio service or runtime FFmpeg dependency is needed.

Method reference: [FFmpeg rubberband filter documentation](https://ffmpeg.org/ffmpeg-filters.html#rubberband). An initial default-window tone test showed unacceptable spectral spreading; the longer mixed-transient configuration was selected after better numerical results. Timbre and transient texture can still change. Human listening approval remains required before this approach is treated as accepted sound quality.

## Range limits and catalogue

Transposition never reduces a melody's span. If the 9-semitone Twinkle melody does not fit the measured comfort with the 65-cent assistance margin, Play explains that a narrower arrangement is needed and offers retry/reset. There is no newly verified narrow arrangement to substitute. The other 21 songs remain listening previews with unverified arrangements and disabled gameplay launch, rather than receiving unverified key variants. Their original data and assets are preserved for Step 9.

## Evidence

| Check | Outcome | Evidence type |
| --- | --- | --- |
| Step 4 owner live humming | Steady note, higher/lower response, and “No steady note” in silence all confirmed by Galvin | Human live-microphone report |
| Absolute ascending pitches over multiple octave boundaries | Pass, no wrapping | Actual mapping tests |
| Coherent low/middle/high octave alternatives | Pass | Actual mapping tests |
| Low/high signal through the actual estimator into mapping | Pass | Synthetic PCM, not a second live singer |
| Wrong held Do against changing Sol/La/Mi, silence, out-of-bound assistance | Rejected | Actual mapping tests |
| Register change and phrase lock | 80 ms evidence required; mid-phrase change stays absolute | Actual mapping tests |
| Key fit, saved semitone changes, geometry intervals, insufficient-range gate | Pass | Actual runtime tests |
| 6-second (three 2-second steps) setup at 30/60/120/144 fps, missing input retry, skip | Pass | Simulated input and UI state |
| 11 shifted instrumental assets | All decode to exactly 40.60 s; finite samples; no clipping | Actual audio decoding |
| Pitch-shift probe | Largest spectral-peak error about 3.82 cents | Rendered known tone |
| Audio envelope alignment | Best offsets −10/0/+10 ms; correlations 0.870–0.935 | Whole-excerpt numerical comparison, not per-note timing proof |
| Chrome setup/skip/key changes/start | Visible controls, guide range changes, adjusted track starts; no game errors | Browser smoke check |
| New sound quality and comfort | Pending Galvin's listening/singing review | Human gate |

Commands run: `node tests/comfort.cjs`, `node tests/timing.cjs`, `node tests/chart.cjs`, `node tests/pitch.cjs`, `node tests/pitch-recording.cjs`, `node tests/microphone.cjs`, `git diff --check`; audio generation and numerical validation via `tools/render-comfort-audio.py` and `tools/check-comfort-audio.py`. Test results establish technical behaviour, not singing ability or comfort.

## Files touched

- `ooh-woo-game.html`: comfort UI/preferences, absolute register model, bounded matching, guide/key agreement, shifted backing cache/load, preview cancellation and setup cleanup.
- `audio/comfort/twinkle-key-*.mp3`: 11 generated instrumental excerpts, preserving original assets.
- `tools/render-comfort-audio.py`, `tools/check-comfort-audio.py`: reproducible generation/validation, requiring FFmpeg with librubberband and NumPy.
- `tests/comfort.cjs`: actual range/tracking tests plus labelled detector PCM and setup simulations.
- `tests/timing.cjs`: obsolete stateless octave tests replaced by the sequential register suite; existing motion/timing checks retained.
- `docs/step5-audio.json`: render settings, exact hashes, durations, pitch probes, alignment and loudness measurements.
- `docs/step5-comfort-setup.png`, this report, stage ledger and handover.

No commit or publication. Existing dirty work is preserved.

## Owner check

Owner feedback, 2026-10-02: gameplay feels acceptable for now; tuning remains unintuitive and the low reference is difficult to hear. Calibration references now include quieter second/third harmonics while retaining the original fundamental, and sustain for 400 ms with a short release rather than fading immediately over 300 ms. Capture still starts after 500 ms; the three two-second steps and pitch targets are unchanged. The starting-register prompt now asks for notes that feel easy to sing. The comfort suite passes; improved audibility still needs a live listening check on the owner's device. Gameplay movement is unchanged in this adjustment.

Open `http://localhost:8081/ooh-woo-game.html` in Chrome with headphones. Choose Set up my voice, then Start 6-second check. Listen and match the named notes in the same octave. Choose Notes too high / Notes too low before retrying if the reference feels uncomfortable. Try Twinkle with the guide on; if the range feels awkward, adjust Too high / Too low between attempts and retry. Report whether the guide is comfortable and whether the adjusted backing sounds natural. Setup can be skipped; Reset comfort can remove a measured range that blocks Play.

Step 6 still owns sustained-note judgement, scoring independent of bird movement, near-hover silence, coin paths and hold trails. Existing spring movement and once-per-coin prototype scoring remain; their limitations must not be mistaken for a range/detector failure. Speaker leakage, another live singer, and mobile devices remain untested. The numeric Hz/clarity display is not proof of accurate musical judgement against the source recording.

Owner adjustment, 2026-10-02: Galvin requested 3 seconds × 3 steps (9 seconds total) instead of 12 seconds. Per-step countdown and ring now reset for each short step; the prompts allow breathing between them. Existing range and audio acceptance remains pending.

Owner flight feedback, 2026-10-02: Galvin reported improved bird response and successful low singing, then requested steadier visuals during a 2–3 Hz held-note fluctuation. A visual-only target anchor now ignores changes inside 3.5 Hz or 25 cents. Changes beyond both limits immediately update the existing spring target; an accepted authored note, fresh vocal attack, restart or keyboard control updates/resets it promptly. Actual MIDI/register judgement, assistance limits, scoring windows and audio timing are unchanged. `node tests/flight-steadiness.cjs` checks 3 Hz peak-to-peak jitter through the actual game loop at 90–880 Hz and 30/60/120/144 fps, immediate semitone movement, resets and judgement independence. Timing/comfort suites also pass. This is the requested narrow visual tuning; broader Step 6 remains unapproved and human smoothness feedback is pending.

Owner correction, 2026-10-02: setup now uses 2 seconds × 3 steps (6 seconds total). The short echo uses two 220 ms notes, with input sampling after 700 ms to avoid measuring the guide. The prior hard visual anchor felt harder to control and jumpy in Galvin’s live check. It has been replaced by continuous semitone-domain exponential smoothing: 25–100 ms response depending smoothly on the size of the change, followed by the existing spring. There is no locked height or threshold-release snap. Detection, accepted register, scoring windows and chart timing remain unchanged. Updated actual-loop tests cover small sustained changes, smooth slides, reduced 3 Hz jitter, note response and convergence at 30–144fps; the 6-second setup and timing suites pass. Live feel acceptance is pending.

Owner guided-calibration correction, 2026-10-02: Galvin reported erratic/high flight and requested matching the played pitch instead of guessing low/middle/high. Setup now uses named, same-octave targets, ±65-cent tolerance and 300 ms continuous matching per step. Low begins at A2 (110 Hz), middle at A3, high at A4; the other two targets are +4/+9 semitones. On success, the target range determines the key, while observed pitch errors remain diagnostics rather than retuning the guide. Failed checks and pending preset/key choices preserve previous settings. Initial gameplay register is the selected octave (offset 0); a single unrelated first sample no longer guesses an octave shift. Between-phrase alternate-octave matching still requires continuous near-target evidence. Off-range voice preserves absolute pitch for judgement but targets the nearest reachable screen edge. Actual guided-setup, wrong-note/wrong-octave, slightly-sharp/key-invariance, first-sample register and reachable-geometry tests pass; live feel remains pending.
