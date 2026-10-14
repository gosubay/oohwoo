# All-song placement review — 2026-10-03

## Plain-language finding

The current catalogue contains deliberate excerpts, not full songs. The files are intact. The builder uses speech-transcript guesses and equal-time syllable splits, so a chart can be on the right average pitch while its word attacks, repeated notes and endings feel wrong. This is a workflow/data issue supported by the code; it is not evidence that one named model is inherently better than another.

Reviewed all 1413 current note events across 22 songs. The independent numerical pass flagged 105 pitch disagreements, 69 notes with weak/insufficient voiced evidence and 118 pitch-attack differences greater than 100 ms. There are 233 equal-time split notes and 93 unlabelled notes (some may be legitimate melismas). Flags overlap. None of these counts is a count of confirmed musical errors.

Twinkle has zero pitch disagreements and zero artificial splits. Ten of its notes differ from measured stable-pitch attacks by over 100 ms; that does not invalidate the owner-approved chart, because an audible syllable or scoop can start before stable voicing. This is why automatic onset snapping is not an acceptable repair.

## What is ready and what is not

Ready: all-song inventory, independently measured per-note evidence, a review queue, 17 reference-supported text revision proposals, language-alignment rules, full-recording acoustic section candidates, and a detailed Claude implementation handoff.

Not done: applying new charts, listening approval, measuring every syllable boundary, and complete full-song transcription/alignment. This package does not claim those are finished. Game/chart data were intentionally preserved for the requested Claude implementation phase.

## Complete inventory

Play end is seconds from the start of the recording, including the intro. “Splits” counts emitted note events, not the number of source notes split. “Pitch flags” and “attack flags” are review leads from the second estimator. Recording durations are decoded vocal duration; matching source/backing container metadata is retained separately.

| Song | Current play / full recording | Notes | Splits | Pitch flags | Attack flags | Unlabelled |
|---|---:|---:|---:|---:|---:|---:|
| Twinkle Twinkle Little Star | 0:41 / 1:29 | 42 | 0 | 0 | 10 | 0 |
| Brother John - Two Tigers | 0:35 / 1:47 | 32 | 0 | 0 | 0 | 0 |
| Humpty Dumpty | 0:39 / 1:24 | 68 | 5 | 2 | 3 | 3 |
| Head Shoulders Knees Toes | 0:32 / 1:27 | 40 | 0 | 2 | 1 | 5 |
| London Bridge | 0:45 / 1:35 | 75 | 0 | 1 | 0 | 2 |
| Itsy Bitsy Spider | 0:23 / 1:35 | 46 | 7 | 2 | 2 | 0 |
| Baa Baa Black Sheep | 0:29 / 1:38 | 40 | 4 | 2 | 1 | 1 |
| Mary Had A Little Lamb | 0:41 / 1:38 | 84 | 24 | 13 | 13 | 0 |
| Row Row Row Your Boat | 0:21 / 0:53 | 47 | 8 | 7 | 8 | 2 |
| The More We Get Together | 0:38 / 1:19 | 57 | 0 | 9 | 8 | 8 |
| Little Bunny | 0:42 / 1:28 | 75 | 6 | 11 | 8 | 11 |
| Rain Rain Go Away | 0:39 / 3:00 | 47 | 10 | 1 | 1 | 3 |
| Finger Family | 0:26 / 1:45 | 38 | 4 | 1 | 1 | 13 |
| Wheels On The Bus | 0:45 / 2:15 | 79 | 8 | 5 | 5 | 11 |
| Old McDonald Had a Farm | 0:28 / 3:55 | 60 | 31 | 6 | 7 | 0 |
| If you're happy and you know it | 0:53 / 1:47 | 141 | 44 | 15 | 9 | 0 |
| 5 Little Monkeys | 1:02 / 2:46 | 100 | 28 | 15 | 12 | 0 |
| Baby Shark | 0:55 / 2:18 | 114 | 14 | 2 | 4 | 11 |
| Ba Luo Bo | 0:39 / 2:20 | 68 | 26 | 3 | 6 | 0 |
| Xiao Yan Zi - Little Bird | 0:37 / 7:18 | 43 | 0 | 0 | 1 | 11 |
| Rasa Sayang | 0:37 / 0:59 | 53 | 2 | 2 | 8 | 7 |
| Chan Mali Chan | 0:37 / 2:16 | 64 | 12 | 6 | 10 | 5 |

## Language-specific priorities

- **Ba Luo Bo:** 26 of 68 notes were produced by equal-duration splitting. Multiple 把/巴/抱 should be checked against intended 拔; repeated 嘿呦 attacks must be measured rather than evenly divided. Full vocal sections continue well after the current 39.23 s ending.
- **Xiao Yan Zi:** zero independent pitch disagreements does not establish correct segmentation or lyrics. Intended 穿花衣 / 年年 is transcribed as 春花一 / 念念. Unlabelled pitch changes may be legitimate melisma, slides, or false subdivisions; inspect each phrase. The 438.4 s asset needs an explicit full-file review, including its long tail.
- **Rasa Sayang:** Malay sayang/saya are collapsed by English vowel grouping; the file is labelled en despite multiple languages. Current play ends at 37.23 s, before the Chinese acoustic section around 40.6–51.3 s. Treat the section estimates as acoustic candidates, not exact lyric boundaries.
- **Chan Mali Chan:** dia/saya/buah need language-aware syllable handling; supplied wording is dikupas / payung / oi oi, unlike transcript dikubas / peyang / oh boy. The first line at 9.35–10.95 s was evenly split into four notes. The actual acoustic attacks must decide how many and where. Six independent pitch flags also need source inspection.

## Why the previous checks missed this

The prior pitch audit uses a closely related autocorrelation method and evaluates median pitch over each authored interval. That can miss a misplaced syllable, a missed repeated attack, or a missing verse. The game test feeds pitches generated from the same chart into the game, so it verifies consistency rather than fidelity to the recording. Passing those tests was never sufficient evidence of a musically correct catalogue.

## Evidence and handoff

- [Claude implementation handoff](../CLAUDE-CATALOGUE-CORRECTION-HANDOFF.md)
- [Per-note review queue](note-review-queue.json): zero-based source indices, exact t/end, lyric, independent measurement, flags and optional candidates.
- [All-note evidence](note-evidence.json): every note, every asset hash/duration, full-recording voiced spans.
- [Correction manifest](correction-manifest.json): proposed wording fixes, language rules, full-section review candidates; no fabricated corrected timestamps.
- [Song summaries](summary.json).

Method: YIN-style normalized difference estimator with 64 ms frames and 20 ms hop, compared to the builder’s 186 ms autocorrelation/Viterbi method. No chart-guided pitch selection, scale snapping or neighbour-based octave repair. Shared stems can still contain shared separation artifacts. No claim of auditory listening or exact syllable detection.

The independently estimated pitch can be wrong too, especially on short, breathy, noisy, mixed or harmonic-rich material. An octave discrepancy needs inspection in the original source. Never auto-apply large candidate jumps.
