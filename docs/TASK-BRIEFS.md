# OohWoo — staged tasks and approval gates

Prepared 2026-10-01. This file is a dispatch plan, not authorisation to execute every stage.

## Stage ledger

| Step | Stage | Status | Proposed owner |
| --- | --- | --- | --- |
| 1 | Gameplay decisions | Approved | Coordinating chat; Astra Medium as proposed by owner |
| 2 | Specification and handovers | Approved by owner | Coordinating chat |
| 3 | Verified Twinkle chart | Implementation complete; owner playback/listening review positive (2026-10-01); detailed timing uncertainty and live-voice checks retained | Music and charts task; GPT-6.1 Sol Medium |
| 4 | Reliable pitch detection | Accepted by owner: steady live hum, higher/lower response and silence clearing confirmed (2026-10-02) | Voice system work; GPT-6.1 Sol Medium as proposed |
| 5 | Comfortable ranges and octave tracking | Owner confirms audible tuning and Low/Middle/High work for Twinkle (2026-10-02); prior timing/audio limitations retained | Continue Voice system task; GPT-6.1 Sol Medium |
| 6 | Movement, scoring, and musical path | Pitch feedback implemented. Owner approved graded pitch/timing/hold judgement and results on 2026-10-02; implemented with Perfect/Great combo, Good/Miss reset, floating grades and ranked report. Path/trail and remaining movement work pending; live grading review pending | Gameplay work |
| 7 | Combo flight | Owner authorised visual speed at 10/25/50 combo; implemented wider visual spacing, faster scenery, wind and smooth transitions with unchanged musical timing. Live feel review pending | Continue Gameplay task; GPT-6.1 Sol Medium |
| 8 | Integrated validation | Awaiting approval; not started | Fresh Review task; Astra Medium |
| 9 | Full songs and catalogue expansion | Owner asked on 2026-10-02 for all other songs to be fixed like Twinkle: 21 recording-based excerpt charts drafted and in the game; **owner listening pending for every song**; full-length songs and full Twinkle not started. See STEP9-CATALOGUE-REVIEW.md | Continue Music and charts task, or fresh catalogue task if needed; Sol Medium |
| 10 | Final documentation | Awaiting approval; not started | Implementation task drafts; coordinating chat reviews |

Use the project saved for C:\Claude\Code\OohWoo after resolving it with list_projects. Model IDs proposed for dispatch: gpt-6.1-sol and gpt-6-astra, reasoning medium. Verify availability at creation. Do not silently substitute a model or imply this file changes the coordinating chat's model.

Create tasks only as needed for approved stages. Run source mutations sequentially initially: most systems share ooh-woo-game.html. Keep approvals and design discussion in the coordinating chat. A fresh independent review should assess the implementation rather than just repeat its completion report.

## Common brief for every task

Read AGENTS.md, docs/GAMEPLAY-SPEC.md, docs/IMPLEMENTATION-HANDOVER.md, and the relevant stage below. Inspect the current worktree and preserve existing work. Follow the approved gameplay decisions. The brief states target behaviour; it does not claim that behaviour already exists. Implement only the stage explicitly authorised in the task's user prompt. Provide the completion report specified in IMPLEMENTATION-HANDOVER.md and stop at the approval gate. If earlier prerequisites are not satisfied, identify the dependency and complete only independent work that is within scope.

## Step 3 — verified Twinkle reference chart

Purpose: make the chart, guide, targets, and actual recording agree for one intentional verse.

Work:
- Identify/hash the source and instrumental assets; confirm their relative alignment and whether audio/ actually contains the intended instrumental mix.
- Define a small chart representation with pitch including octave, onset/end, lyrics, rests/phrases, level bounds, and provenance. Keep beat markers separate.
- Use transcription as a draft; verify/edit against the recording. Build the smallest useful local inspection/editor tool if it materially helps corrections and looping sections.
- Preserve the same musical facts for guide, targets, and lyric display. Make level completion intentional, including the last held note and audio ending.
- Do not expand all songs or redesign the microphone/control system in this stage. Clearly mark legacy charts as unverified rather than silently converting assumptions into facts.

Acceptance: chart validation passes; a listening/visual check covers the entire excerpt; pitches, rests, repeated notes, starts, ends, and lyrics are reviewed; frame-rate/pause tests do not shift musical deadlines. Provide a short playback procedure for Galvin. Record timestamp uncertainty honestly; owner listening approval is required.

2026-10-01 progress: a 42-note D4–B4 reference chart now owns targets, guide durations, lyric phrases, explicit rests and a final hold/fade ending at 40.60 s. Exact Twinkle source/backing/vocal hashes and a 23-file audio inventory are recorded. Numerical analysis supports all 42 pitches and zero relative stem delay; runtime/asset/chart checks pass. Onsets and most syllable gaps remain draft estimates (up to 0.35 s uncertainty), and listening/live-voice acceptance is pending. See [STEP3-REVIEW.md](STEP3-REVIEW.md) for evidence, limitations, files changed, and the precise owner procedure. This status is completion **for review**, not full chart verification or permission to start Step 4.

2026-10-01 owner review update: after opening the listening inspector and being asked to listen once and report anything early, late or awkward, Galvin reported “sounds good, it works.” This records positive human playback/listening acceptance of the reference excerpt. It does not establish an exhaustive note-by-note audit or a real-microphone playtest; the documented timing estimates and later live-voice acceptance items remain. Step 4 still awaits separate owner authorisation.

## Step 4 — reliable microphone pitch detection

Purpose: fix the demonstrated low-note failure without trading it for excessive delay or unstable tracking.

Work:
- Reproduce 82.41/110 Hz rejection in the real detector at 44.1/48 kHz and inspect the selected autocorrelation peak.
- Implement justified period selection/confidence/voicing improvements; profile on relevant hardware where available. Do not simply relax all thresholds or widen frequency limits.
- Test low/middle/high tones, realistic harmonics, amplitude changes, silence/noise, pitch transitions, and octave ambiguities. Include real voice evidence where available.
- Add input timing diagnostics and robust single microphone initialisation. Report device/input latency separately from chart timing and animation response.

Acceptance: low-note regression is fixed; silence is unvoiced; transitions and harmonics meet documented error/latency goals; no duplicate capture setup; existing timing behaviour stays intact. Synthetic tests alone do not complete live-mic acceptance.

2026-10-01 progress: reproduced 82.41/110 Hz rejection before editing; replaced the faulty correlation-peak search with a normalized period estimator. 318 actual-detector synthetic cases and 12 transitions pass, microphone lifecycle/cleanup tests pass, and all 42 recorded Twinkle note medians are within 50 cents. Chrome processing measured about 0.1 ms median / 0.1–0.2 ms p95 on this desktop. Live capture connected at 48 kHz and current quiet input was unvoiced; owner humming/real low-voice responsiveness remains pending. The chart and later gameplay/range systems were preserved. See [STEP4-REVIEW.md](STEP4-REVIEW.md) for exact evidence, timing limits and the short owner check. Step 5 remains unapproved.

## Step 5 — comfortable register, transposition, and bounded assistance

Purpose: let different singers follow the same melody comfortably without octave wrap or automatic chart-following.

Work:
- Implement skippable 10–15-second comfort setup and between-attempt Too high/Too low adjustments.
- Preserve absolute pitch/register tracking and support coherent octave alternatives, rather than discard octave every frame.
- Make moderate assistance target-aware and bounded; keep clearly incorrect notes and silence incorrect. The score must not determine a matching input merely because a target is present.
- Fit the musical key to the comfortable range. Ensure backing, guide, and target frequencies agree. Choose a concrete transposition approach and evaluate sound quality before committing to it. Changing playback rate alone must not change song tempo unintentionally.
- Handle insufficient range with an explicit narrower arrangement/alternative rather than distorted intervals. Keep screen geometry distinct from musical pitch.

Acceptance: low and high registers work; an ascending octave crossing never wraps down; alternate-octave phrases work; a held unrelated pitch does not collect a changing melody; the same target means the same sound across guide/backing/scoring; setup can be skipped/retried and saved preferences can be changed. Galvin approves comfort.

## Step 6 — smooth musical flight and fair scoring

Purpose: implement the approved feel with accepted notes as target heights and voice-based judgement independent of animation lag.

Work:
- Separate note judgement, accepted-pitch target, visual spring movement, and collection feedback.
- Implement note onsets/holds/repeated-note behaviour, once-only resolution, limited syllable-gap grace, and explicit rest handling.
- Replace strong silence descent with near-hover and slight drift. Keep smooth, promptly reversible movement and gently changing tilt.
- Add coins with faint connecting paths and sustain trails. Do not draw misleading connections across long rests.
- Maintain keyboard/touch fallback and distinguish fallback play from evidence of microphone correctness.
- Show score and best literal streak on results; preserve enough event information for combo boost behaviour in Step 7.

Acceptance: correct input scores during visual transit; long notes require meaningful sustain; one input cannot collect distinct-pitch overlapping notes; scheduled rests protect streak/boost; no instant death; comparable response at 30/60/120/144 fps. Galvin approves the feel using voice, not just keyboard.

## Step 7 — combo flight state machine

Purpose: make success feel faster without changing musical timing or increasing vertical-control lag.

Work:
- Implement normal/boosted/weakened states and the exact approved recovery rules from GAMEPLAY-SPEC.md.
- Separate literal streak/best streak from flight boost and score multiplier. Document multiplier choices for owner review.
- Add smooth scenery acceleration/deceleration, longer trails, and a gentle camera effect while maintaining target readability.
- Keep target deadlines, music tempo, guide scheduling, and vertical response invariant under combo changes.

Acceptance sequences: boost -> miss -> three successes -> restored; boost -> miss -> one/two successes -> miss -> broken; rests during recovery do not break it; sustained notes resolve once; restart clears boost state. Run identical audio/input timelines with and without visual boosts and compare note deadlines/judgements. Galvin approves intensity and recovery feel.

2026-10-02 scoped combo update: owner approved 10/20/40 consecutive-note tiers with 1×/2×/2.5×/3× points and 1×/1.3×/1.6×/2× visual speed/spacing. Implemented in the existing combo flight path with a labeled top HUD, half-point scores, miss reset and unchanged authored timing; automated checks and mobile HUD inspection pass. See [COMBO-FLIGHT-REVIEW.md](COMBO-FLIGHT-REVIEW.md). This scoped update does not complete the broader Step 7 recovery-state design above.

## Step 8 — independent integrated review

Purpose: assess the actual game against the approved specification, not merely accept earlier task reports.

Work: review the final diff/data/provenance; exercise full excerpt startup, setup, audio, voice, scoring, combo, pause/resume, retry, ending, preferences, and fallbacks. Test speakers/headphones and device/browser combinations where access allows. Check background audio does not silently play the game. Examine frame stalls, permission failures, voice-range changes, octave boundaries, and scoring edges.

Acceptance: categorised findings with reproduction evidence; fixes verified in their owning task; live playtests cover Galvin and another comfortable vocal range. Explicitly list unavailable devices/untested cases. Completion requires owner approval; a clean automated run is insufficient.

## Step 9 — full songs and catalogue expansion

Purpose: move from the approved one-verse reference to full-song play and then verified song batches.

Work: complete full Twinkle first, including repeated sections/lyrics/rests and its musical ending; apply the proven chart and range workflow to small agreed batches. Validate each exact recording. Generate catalogue duration/target count from chart data. Mark unverified songs clearly. Do not assume a shared tempo or major scale for all recordings.

Acceptance: every released song has provenance, a complete approved chart/ending, guide/backing agreement, supported comfort options, listening verification, and a playtest report. Owner approves each batch.

## Step 10 — final handover

Purpose: make the finished game understandable and maintainable.

Work: reconcile README.md, DESIGN.md, ROADMAP.md, CLAUDE.md, and AGENTS.md with delivered behaviour while preserving applicable contributor rules; document architecture, chart authoring, transposition, timing, voice detection, tunable settings, tests, run instructions, and known limitations. Update this ledger to reflect actual approvals and completed work. Separate historical snapshots from the deliverable.

Acceptance: instructions can run the game and tests on a documented environment; a contributor can add/verify a song; no document claims unverified functionality is complete. Coordinating chat reviews and owner approves.

2026-10-02 owner live microphone acceptance: Galvin confirmed steady-note display and higher/lower response, with “No steady note” after stopping. This passes the three requested live checks; it does not certify every device or singer. Galvin then authorised Step 5 with “ok pls proceed.”

2026-10-02 Step 5 progress: skippable 6-second (three 2-second steps) comfort measurement, saved key adjustment, absolute octave tracking, 65-cent bounded help and 11 tempo-preserving Twinkle backing variants implemented. Technical range/audio/timing tests pass; Chrome setup and adjusted playback checked. Insufficient range explicitly requests a narrower arrangement/retry; unverified catalogue songs remain listening previews. See [STEP5-REVIEW.md](STEP5-REVIEW.md). Human comfort and shifted-audio listening approval remain pending. Step 6 is unapproved.

2026-10-02 owner feedback: improved response and successful low singing confirmed. Requested visual steadiness for small held-note fluctuations implemented as a separate target anchor, without changing microphone judgement or audio/scoring timing. Actual game-loop jitter/response tests pass; owner smoothness review pending. This does not authorise the remaining Step 6 work.

2026-10-02 follow-up: owner requested 2 seconds per tone (6 seconds total) and reported worse movement after the hard visual anchor. Setup shortened; anchor replaced with continuous adaptive smoothing. Jitter, slow slides, small held changes, note transitions, 6-second setup and timing checks pass; live feedback pending. Broader Step 6 remains unapproved.

2026-10-02 guided setup correction: owner requested matching actual reference pitches after reporting erratic/high flight. Three 2-second same-octave checks now validate ±65-cent matching holds and anchor the selected key. First-sample octave guessing removed; off-range visual targets constrained to screen edges. Saved settings survive failed/pending checks. Automated guided-match/register/geometry tests pass; live feel review pending. Step 6 remains unapproved.

2026-10-02 scoring feedback: after the scoped combo update, Galvin reported roughly 70% feel and an incentive to sing ahead so the bird reached notes. The 32 px bird-to-coin requirement was removed from sung-note scoring; pitch and musical time still decide hits. Timing tests cover a correct note while the bird is far away, plus wrong pitch, silence and late input. Live feel needs another owner check before expanding the chart.
