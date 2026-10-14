// Package evidence and explicit editorial proposals; never edits the game/charts.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'../..'),out=path.join(root,'docs/catalogue-review-2026-10-03');
const read=p=>JSON.parse(fs.readFileSync(path.join(root,p),'utf8'));
const summary=read('docs/catalogue-review-2026-10-03/summary.json');
const charts=read('docs/catalogue-analysis/charts.json');
const evidence=read('docs/catalogue-review-2026-10-03/note-evidence.json');
const sha=p=>crypto.createHash('sha256').update(fs.readFileSync(path.join(root,p))).digest('hex');
const revisions=[];
function revise(song,index,oldText,newText,reason){
  const note=charts[song].notes[index];
  if(note.lyric!==oldText)throw Error(`Stale locator: ${song} ${index}`);
  revisions.push({song,noteIndex:index,t:note.t,end:note.end,oldText,newText,reason,
    status:'reference-supported editorial correction; exact sung wording and placement require listening',
    timingAction:'Do not change timestamps merely to fit corrected text.'});
}
for(const i of [0,3,10,17,31,34,37,44])revise('baluobo',i,'把','拔','Reference says pulling radish: 拔萝卜 / 拔不动.');
revise('baluobo',51,'巴','拔','Reference says 拔不动.');
revise('baluobo',65,'抱','拔','Reference says 拔萝卜.');
for(const [i,oldText,newText] of [[6,'春','穿'],[10,'一','衣'],[11,'念','年'],[12,'念','年']])
  revise('xiaoyanzi',i,oldText,newText,'Reference opening is 小燕子，穿花衣，年年春天来这里.');
revise('chanmalichan',42,'bas','pas','Reference word is dikupas, not ASR dikubas. Keep preceding di-/ku- pending realignment.');
revise('chanmalichan',47,'oh','oi','Reference refrain is oi oi; ASR says oh boy. Verify the actual recording.');
revise('chanmalichan',48,'boy','oi','Reference refrain is oi oi; ASR says oh boy. Verify the actual recording.');
const manifest={status:'handoff proposals, not applied chart fixes',chartSourceSha256:sha('docs/catalogue-analysis/charts.json'),
 lyricReference:{path:'lyrics_raw.txt',sha256:sha('lyrics_raw.txt'),status:'intended lyrics; actual recording may vary'},
 noteIndexConvention:'zero-based, valid only for the source hash',editorialRevisions:revisions,
 languageAlignmentRules:[
  {language:'ms',words:{sayang:['sa','yang'],saya:['sa','ya'],dia:['di','a'],buah:['bu','ah'],
    rasa:['ra','sa'],nona:['no','na'],mali:['ma','li'],ketipung:['ke','ti','pung'],payung:['pa','yung']},
   rule:'Reference syllables, not equal-duration notes. Confirm sung realization, hiatus/diphthongs, attack timing and melismas per phrase.'},
  {song:'rasasayang',rule:'Replace whole-song en assumption with ms/en/zh section tags. Reconstruct nona from ASR noh + na against the recording. Split sayang/saya correctly before alignment.'},
  {song:'chanmalichan',currentNoteIndex:63,currentLyric:'peyang',referenceWord:'payung',
   rule:'Reconstruct ke-ti-pung pa-yung over approximately 34.3–36.7 s from the recording; cannot safely fix by relabelling a single coin. Repeat correction at later occurrences.'},
  {language:'zh',rule:'Correct homophone transcription from context/reference; preserve recorded syllable timing. One character may span multiple pitches. Do not guess missing characters or split notes into equal durations.'}
 ],
 fullSongSections:summary.songs.map(s=>({song:s.song,currentPlayEnd:s.playEnd,fullRecordingSeconds:s.recordingSeconds,
   acousticSectionCandidates:s.acousticSections,status:'Not lyric/verse ground truth; confirm every language/repeat and natural ending.'})),
 excludedAutomaticActions:['Apply all independent pitch candidates','Shift all note attacks to periodic-voice onset',
   'Duplicate first verse into later languages','Lengthen level.end without a full chart','Overwrite owner-approved Twinkle excerpt']};
fs.writeFileSync(path.join(out,'correction-manifest.json'),JSON.stringify(manifest,null,2)+'\n');
const totals=summary.songs.reduce((a,s)=>{for(const k of ['notes','artificialSplits','unlabelled','pitchDisagreements','weakVoice','attackFlags'])a[k]=(a[k]||0)+s[k];return a;},{});
const clock=t=>{const seconds=Math.round(t);return `${Math.floor(seconds/60)}:${String(seconds%60).padStart(2,'0')}`;};
const lines=[
'# All-song placement review — 2026-10-03',
'',
'## Plain-language finding',
'',
'The current catalogue contains deliberate excerpts, not full songs. The files are intact. The builder uses speech-transcript guesses and equal-time syllable splits, so a chart can be on the right average pitch while its word attacks, repeated notes and endings feel wrong. This is a workflow/data issue supported by the code; it is not evidence that one named model is inherently better than another.',
'',
`Reviewed all ${totals.notes} current note events across 22 songs. The independent numerical pass flagged ${totals.pitchDisagreements} pitch disagreements, ${totals.weakVoice} notes with weak/insufficient voiced evidence and ${totals.attackFlags} pitch-attack differences greater than 100 ms. There are ${totals.artificialSplits} equal-time split notes and ${totals.unlabelled} unlabelled notes (some may be legitimate melismas). Flags overlap. None of these counts is a count of confirmed musical errors.`,
'',
'Twinkle has zero pitch disagreements and zero artificial splits. Ten of its notes differ from measured stable-pitch attacks by over 100 ms; that does not invalidate the owner-approved chart, because an audible syllable or scoop can start before stable voicing. This is why automatic onset snapping is not an acceptable repair.',
'',
'## What is ready and what is not',
'',
`Ready: all-song inventory, independently measured per-note evidence, a review queue, ${revisions.length} reference-supported text revision proposals, language-alignment rules, full-recording acoustic section candidates, and a detailed Claude implementation handoff.`,
'',
'Not done: applying new charts, listening approval, measuring every syllable boundary, and complete full-song transcription/alignment. This package does not claim those are finished. Game/chart data were intentionally preserved for the requested Claude implementation phase.',
'',
'## Complete inventory',
'',
'Play end is seconds from the start of the recording, including the intro. “Splits” counts emitted note events, not the number of source notes split. “Pitch flags” and “attack flags” are review leads from the second estimator. Recording durations are decoded vocal duration; matching source/backing container metadata is retained separately.',
'',
'| Song | Current play / full recording | Notes | Splits | Pitch flags | Attack flags | Unlabelled |',
'|---|---:|---:|---:|---:|---:|---:|',
...summary.songs.map(s=>`| ${s.recording.replace(/^\d+\. /,'')} | ${clock(s.playEnd)} / ${clock(s.recordingSeconds)} | ${s.notes} | ${s.artificialSplits} | ${s.pitchDisagreements} | ${s.attackFlags} | ${s.unlabelled} |`),
'',
'## Language-specific priorities',
'',
'- **Ba Luo Bo:** 26 of 68 notes were produced by equal-duration splitting. Multiple 把/巴/抱 should be checked against intended 拔; repeated 嘿呦 attacks must be measured rather than evenly divided. Full vocal sections continue well after the current 39.23 s ending.',
'- **Xiao Yan Zi:** zero independent pitch disagreements does not establish correct segmentation or lyrics. Intended 穿花衣 / 年年 is transcribed as 春花一 / 念念. Unlabelled pitch changes may be legitimate melisma, slides, or false subdivisions; inspect each phrase. The 438.4 s asset needs an explicit full-file review, including its long tail.',
'- **Rasa Sayang:** Malay sayang/saya are collapsed by English vowel grouping; the file is labelled en despite multiple languages. Current play ends at 37.23 s, before the Chinese acoustic section around 40.6–51.3 s. Treat the section estimates as acoustic candidates, not exact lyric boundaries.',
'- **Chan Mali Chan:** dia/saya/buah need language-aware syllable handling; supplied wording is dikupas / payung / oi oi, unlike transcript dikubas / peyang / oh boy. The first line at 9.35–10.95 s was evenly split into four notes. The actual acoustic attacks must decide how many and where. Six independent pitch flags also need source inspection.',
'',
'## Why the previous checks missed this',
'',
'The prior pitch audit uses a closely related autocorrelation method and evaluates median pitch over each authored interval. That can miss a misplaced syllable, a missed repeated attack, or a missing verse. The game test feeds pitches generated from the same chart into the game, so it verifies consistency rather than fidelity to the recording. Passing those tests was never sufficient evidence of a musically correct catalogue.',
'',
'## Evidence and handoff',
'',
'- [Claude implementation handoff](../CLAUDE-CATALOGUE-CORRECTION-HANDOFF.md)',
'- [Per-note review queue](note-review-queue.json): zero-based source indices, exact t/end, lyric, independent measurement, flags and optional candidates.',
'- [All-note evidence](note-evidence.json): every note, every asset hash/duration, full-recording voiced spans.',
'- [Correction manifest](correction-manifest.json): proposed wording fixes, language rules, full-section review candidates; no fabricated corrected timestamps.',
'- [Song summaries](summary.json).',
'',
'Method: YIN-style normalized difference estimator with 64 ms frames and 20 ms hop, compared to the builder’s 186 ms autocorrelation/Viterbi method. No chart-guided pitch selection, scale snapping or neighbour-based octave repair. Shared stems can still contain shared separation artifacts. No claim of auditory listening or exact syllable detection.',
'',
'The independently estimated pitch can be wrong too, especially on short, breathy, noisy, mixed or harmonic-rich material. An octave discrepancy needs inspection in the original source. Never auto-apply large candidate jumps.',
];
fs.writeFileSync(path.join(out,'REVIEW.md'),lines.join('\n')+'\n');
for(const [key,e] of Object.entries(evidence.songs)){
  const ds=e.assets.map(a=>a.containerDuration);
  if(Math.max(...ds)-Math.min(...ds)>.2)console.log('Asset duration discrepancy:',key,ds);
}
console.log(`Packaged ${summary.songs.length} songs, ${totals.notes} notes, ${revisions.length} editorial proposals; no chart mutations.`);
