# Step 4 — microphone pitch detection, complete for review

2026-10-01. Galvin authorised Step 4 with “go” after the Step 3 review. Implementation, synthetic signal checks, recorded-vocal checks and basic Chrome capture checks are complete. Owner humming/voice response acceptance is pending. Steps 5–10 were not implemented or approved. Existing checkout work and all audio/chart assets were preserved; no commit or publishing was requested or performed.

## Plain-language changes

The detector now recognises the low notes that previously failed, rejects quiet/unsteady input, and clears the last reading when sound stops. Note names include the correct octave, so a low A shows A2 rather than the old display's nearest C4. Setup calls share one pending microphone request and reuse working capture; failed setup releases newly acquired resources and can be retried. Losing a device invalidates its readings, and old-device events cannot invalidate a replacement. Microphone permission is now requested through Play, voice setup or Enable mic, rather than at page load. The menu pitch tester runs only one polling loop.

The debug view/log reports voiced status, rejection reason, confidence, processing cost, estimate-window age, polling interval, capture-context time and reported device latency. None of these adjusts the Twinkle chart. Comfortable-range setup, octave/register tracking, bounded assistance, movement, scoring and combo remain later work.

## Reproduction and method

Before editing, the real 4096-sample detector was exercised with amplitude-0.2 sine PCM at 44.1 and 48 kHz. 82.41 and 110 Hz both returned -1: the selected false candidate was approximately 1876.60 or 1882.35 Hz, outside the existing supported range. `docs/step4-baseline.json` stores the results and the pre-change detector's SHA-256. The old search compared unnormalised overlap correlation to full-buffer energy and could select the short-lag shoulder of the zero-lag peak. Widening frequency limits would have accepted that wrong pitch.

The new estimator uses squared differences at each lag, cumulative mean normalisation, the first sufficiently periodic local trough, and interpolation of the raw difference trough. It adapts steps 2–5 of [de Cheveigné & Kawahara's YIN paper](https://www.ee.columbia.edu/~dpwe/papers/deChevK02-yin.pdf); it does not implement the paper's full step-6 local search or claim its published error rate. If no trough meets the threshold, this game rejects the frame instead of choosing a noisy fallback. Confidence is a periodicity score, not a calibrated probability of singing.

Two-pass low-pass filtering/reduction keeps the search near 11–12 kHz for common 44.1/48 kHz input. The newest 35 ms integration window is compared with preceding periods; accepted notes use roughly 36–48 ms of recent signal. The existing 80–1600 Hz limits remain. A five-cent numerical fringe is clamped at the boundaries to accommodate interpolation error; it does not accept a new range. No expected chart pitch, calibration or score enters the estimator. A 4096-sample capture buffer remains adequate at 44.1/48 kHz; 96 kHz uses 8192 samples for sufficient history. Scratch arrays are reused.

## Evidence and limits

| Check | Evidence/result | Category |
| --- | --- | --- |
| Original low-tone failure | 82.41/110 Hz rejected at 44.1/48 kHz; false candidates around 1880 Hz | Pre-change actual-detector PCM reproduction |
| 318 signal cases | PASS; 80–1600 Hz, 22.05/44.1/48/96 kHz, several amplitudes/phases, harmonics, missing fundamental with multiple upper harmonics, DC, noise, clipping, amplitude ramp, silence and out-of-range tones | Synthetic PCM through the actual detector; no pitch-mapping mocks |
| Synthetic pitch accuracy | Maximum error about 2.59 cents over the checked cases | Synthetic, not a real-singer guarantee |
| 12 transitions | PASS; attacks/pitch changes settle in 35–45 ms of signal history; silence becomes unvoiced within 10 ms in these step fixtures; all remain stable by 60 ms | Synthetic, with 5 ms observation steps; excludes device and frame-poll delay |
| Microphone lifecycle | PASS: shared pending request, ready reuse, resume, synchronous denial, cleanup after partial failure, retry, device loss/replacement, one tester loop, latency metadata, 96 kHz buffer | Mock capture devices; not permission or hardware compatibility evidence |
| Recorded Twinkle vocal | 42/42 medians within 50 cents; maximum deviation 31.93 cents; 709/735 analysed core frames voiced | Real recorded voice, numerical analysis; D4–B4, not a live low singer |
| Chrome estimator cost | Warm median about 0.100 ms; p95 0.100–0.200 ms across two checks, over 300 estimates after 100 warm-up calls; latest exact values in browser JSON | Windows desktop Chrome 154; timer resolution applies, not mobile performance |
| Node estimator cost | Warm median approximately 0.12 ms; exact latest figures in synthetic JSON | This host's Node VM, not browser/mobile latency |
| Chrome live capture | Connected at 48 kHz; current quiet input displayed unvoiced; device reported 10 ms input latency | Basic connection/current-input check; no audible singing evidence or human comfort judgement |
| Existing timing/chart tests | PASS; guide/targets/chart assets and deliberate ending remain valid | Runtime regression and asset checks |
| Low live singer, pitch changes, responsiveness and comfort | Pending owner check | Real microphone/human acceptance |
| Phones, other browsers/devices, speakers vs headphones | Untested here | Later hardware/integration validation |

The real recording report in `docs/step4-browser.json` includes the exact vocal-asset hash, estimator-source hash, per-note observations, browser identity and timing measurements. `tests/pitch-recording.cjs` checks that this evidence matches the current estimator and asset. `docs/step4-synthetic.json` records signal cases, transitions, estimator hash and Node measurements. The recorded voice contains no 82/110 Hz low singer; synthetic regression coverage is not presented as that missing evidence. The agent verified numerical results, UI state and capture availability, not the sound of anyone singing.

## Timing and ambiguity cautions

`computeMs` is CPU time for one read/estimate. `windowCenterAgeMs` estimates where the analysed signal lies within recent buffered audio; it is approximate and omits unknown capture/browser buffering. `pollIntervalMs` measures how often the game calls the detector, which depends on frame rate/stalls. `audioTime` belongs to the capture AudioContext and is not the backing-track clock. `captureLatencyMs` is the browser track's reported latency where available, not an acoustic loopback measurement. AudioContext `baseLatency` and `outputLatency` concern rendering/output and must not be added as if they were microphone capture latency. End-to-end input delay still needs measurement on real devices. No automatic chart shift or scoring-latency correction was added in this stage.

Periodicity alone cannot identify a human singer. A nearly absent fundamental and overwhelmingly dominant second harmonic can correctly appear as an octave higher according to the observed waveform; no chart-driven guess forces it lower. Periodic backing/guide leakage may also look voiced. Echo cancellation is requested on a best-effort basis; noise suppression and automatic gain control are requested off to preserve singing. Actual settings are recorded when exposed, and a browser/device may choose different settings. Headphones and later speaker-leakage testing remain necessary. Existing downstream octave folding, assistance, silence physics and bird-position scoring are unchanged and retain their documented shortcomings.

## Galvin's short voice check

1. Open `http://localhost:8081/tools/pitch-review.html` with the workspace review server running, or `http://localhost:8080/tools/pitch-review.html` with the regular game server. This page uses the estimator from the current game. Click **Enable microphone** and allow localhost if prompted. Use headphones.
2. Hum a comfortable low note for two seconds, then a middle note and a higher note, leaving silence between them. The number should settle promptly, change with your pitch, and clear when you stop. If possible report the lowest Hz you see; no particular low note is required and this is not an extreme-range test.
3. Report whether notes disappear, fluctuate by whole octaves, or feel delayed. If humming still gives no reading, check the browser/OS input selection and microphone mute state. Click **Stop microphone** when done.
4. Open the game, tap **Enable mic**, and confirm the main pitch tester behaves similarly. **Record 10s Debug Log** exports numerical readings and timing metadata locally, not microphone audio. You can retry permission/device setup with Enable mic. Then try the Twinkle reference verse with headphones; score/animation/comfort issues can still belong to later stages.
5. Owner voice acceptance is pending until that check is reported. A positive browser-capture result or synthetic test does not substitute for it. Step 5 requires separate approval.

The temporary browser microphone check during implementation used live capture only for UI/availability observations; the recording-analysis button processes the existing vocal MP3. No live microphone audio file was saved or posted.

## Reproduce checks and files touched

Run from the repository root:

```
node tests/pitch.cjs
node tests/microphone.cjs
node tests/pitch-recording.cjs
node tests/timing.cjs
node tests/chart.cjs
git diff --check
```

All passed for this review. `pitch.cjs` refreshes only the synthetic report; the historical baseline is preserved. To refresh browser recording evidence, run `python tools/reference-server.py` with numpy available, open the pitch review page on port 8081, and click **Check recorded voice and processing speed**. The server binds only to localhost and saves the recording report into the fixed local evidence file. Basic live checking works with the regular server as well. Browser recording evidence must be rerun when the estimator changes.

Files touched in Step 4:

- `ooh-woo-game.html`: estimator, capture lifecycle, permission timing, truthful note labels and diagnostics.
- `tests/game-harness.cjs`, `tests/pitch.cjs`, `tests/microphone.cjs`, `tests/pitch-recording.cjs`: actual game harness and signal/lifecycle/evidence checks.
- `tools/pitch-review.html`, `tools/reference-server.py`: local voice/recording check and fixed report endpoint.
- `docs/step4-baseline.json`, `docs/step4-synthetic.json`, `docs/step4-browser.json`: reproduction, numerical and browser evidence.
- `docs/STEP4-REVIEW.md`, `docs/TASK-BRIEFS.md`, `docs/IMPLEMENTATION-HANDOVER.md`: review and stage status.
- `docs/step4-microphone-check.png`: browser diagnostic screenshot.

Other existing uncommitted/untracked work was preserved. No Twinkle chart facts, original/processed audio, or other-song note arrays were changed by Step 4.
# Owner live check — 2026-10-02

Galvin supplied eight live pitch screenshots (110.5–232.9 Hz, clarity 0.97–1.00), then explicitly confirmed a steady held note, higher/lower response, and “No steady note” when he stopped. Those three requested acceptance checks pass. This does not imply perfect scale tuning, a second live singer, mobile coverage, or measured end-to-end latency. Step 5 was subsequently authorised with “ok pls proceed.”

