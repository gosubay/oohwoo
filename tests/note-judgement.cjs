const assert=require('node:assert/strict');
const {gameHarness}=require('./game-harness.cjs');
const {run,element}=gameHarness();
function grade(samples,end=1) {
  return run(`gradeNote({note:{t:0},end:${end},samples:${JSON.stringify(samples)}})`);
}
const sample=(a,b,error)=>({a,b,error});
for(const [cents,expected] of [[0,'Perfect'],[35,'Perfect'],[36,'Great'],[65,'Great'],[66,'Good'],[90,'Good'],[91,'Miss'],[100,'Miss']])
  assert.equal(grade([sample(0,1,cents)]).name,expected);
for(const [late,expected] of [[.1,'Perfect'],[.101,'Great'],[.18,'Great'],[.181,'Good'],[.25,'Good'],[.251,'Miss']])
  assert.equal(grade([sample(0,late,null),sample(late,1,0)]).name,expected);
for(const [coverage,expected] of [[.8,'Perfect'],[.79,'Great'],[.6,'Great'],[.59,'Good'],[.35,'Good'],[.34,'Miss']])
  assert.equal(grade([sample(0,coverage,0),sample(coverage,1,null)]).name,expected);
assert.equal(grade([sample(0,1,null)]).name,'Miss');
assert.equal(grade([sample(0,.79,0),sample(.79,.84,null),sample(.84,.85,0),sample(.85,1,null)]).name,'Perfect','bounded gap credited');
assert.equal(grade([sample(0,.7,0),sample(.7,.85,null),sample(.85,.9,0),sample(.9,1,null)]).name,'Great','long gap not bridged');
assert.equal(grade([sample(0,.02,0),sample(.02,.1,null)],.1).name,'Miss','transient below stability requirement');
assert.equal(grade([sample(-.2,.1,0)],.1).name,'Perfect','already held pitch on time');
assert.equal(grade([sample(0,.35,0),sample(.35,1,300)]).name,'Miss','weighted median');
const gaps=[];let gapTime=0;
for(let i=0;i<5;i++) { gaps.push(sample(gapTime,gapTime+.1,0));gapTime+=.1;gaps.push(sample(gapTime,gapTime+.08,null));gapTime+=.08; }
gaps.push(sample(gapTime,1,0));
assert.equal(grade(gaps).name,'Great','gap credit capped at 15%');
for(const fps of [30,60,120,144]) {
  run(`startGame('twinkle');noteJudgements=[makeNoteJudgement({t:0,end:1,midi:60},null)];judgementLastTime=0;`);
  for(let f=1;f<=fps;f++) run(`gameTime=${f/fps};updateNoteJudgements(gameTime,60+songShift(currentSong));`);
  assert.equal(run('noteJudgements[0].result.name'),'Perfect');
  assert.equal(run('combo'),1);assert.equal(run('score'),1);
  run('updateNoteJudgements(2,60);');assert.equal(run('score'),1,'resolve once');
}
run(`startGame('twinkle');noteJudgements=[];`);
for(const [error,label,combo] of [[0,'Perfect',1],[50,'Great',2],[80,'Good',0],[200,'Miss',0]]) {
  run(`{const e=makeNoteJudgement({t:0,end:1},null);e.samples=[{a:0,b:1,error:${error}}];noteJudgements.push(e);resolveNoteJudgement(e);}`);
  assert.equal(run('noteJudgements.at(-1).result.name'),label);assert.equal(run('combo'),combo);
}
assert.equal(run('bestCombo'),2);assert.ok(Math.abs(run('performanceSummary().performance')-57.5)<1e-8);
assert.equal(run('performanceSummary().rank'),'D');
run('songComplete()');assert.match(element('performanceReport').innerHTML,/Good 1 · Miss 1/);
assert.equal(run('judgementFeedback.length'),4);
run('startGame("twinkle")');assert.equal(run('bestCombo'),0);assert.equal(run('judgementFeedback.length'),0);
run(`noteJudgements=[makeNoteJudgement({t:0,end:1,midi:60},null)];judgementLastTime=0;gameTime=1;updateNoteJudgements(1,60+songShift(currentSong));`);
assert.equal(run('noteJudgements[0].result.name'),'Miss','stall cannot create a hold');
run(`startGame('twinkle');noteJudgements=[60,61].map(midi=>makeNoteJudgement({t:0,end:1,midi},null));judgementLastTime=0;`);
for(let f=1;f<=60;f++)run(`gameTime=${f/60};updateNoteJudgements(gameTime,60.5+songShift(currentSong));`);
assert.equal(run('noteJudgements[0].result.name'),'Great');
assert.equal(run('noteJudgements[1].result.name'),'Miss','one voice cannot score distinct overlapping pitches');
run(`startGame('twinkle');micEnabled=true;micReady=true;keyRatio=-1;touchHeld=false;
  pipeSchedule=buildPipes([{t:1,end:1.5,midi:60,ratio:0}]);
  noteJudgements=pipeSchedule.map(n=>makeNoteJudgement(n,null));judgementLastTime=.9;
  nextPipeIdx=0;gameTime=.9;lastTime=900;getBackingTrackTime=()=>null;
  singingToRatio=()=>0;registerOffset=0;detectPitch=()=>hzOf(60+songShift(currentSong));
  drawBackground=drawHitZone=drawBird=drawCoin=()=>{};`);
for(let f=1;f<=40;f++) run(`gameLoop(${900+f*1000/60});`);
assert.equal(run('judgementCounts.Perfect'),1);assert.equal(run('combo'),1);
console.log('PASS: pitch/timing/coverage boundaries, sustain, gaps, median, FPS, combo, rank, reset, stalls and game-loop scoring.');
