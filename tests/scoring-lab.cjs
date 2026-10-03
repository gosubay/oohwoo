const assert = require('node:assert/strict');
const {gameHarness} = require('./game-harness.cjs');
const {run, element} = gameHarness();
function start(mode) {
  element('scoringMode').value = mode;
  run(`startGame('twinkle');
    noteJudgements=[makeNoteJudgement({t:1,end:2,midi:60,ratio:0},null)];
    birdY=ratioToY(0);gameTime=1;`);
}
start('strict');
run('updateCoinJudgements');
assert.equal(run('score'), 0);
const late = '{note:{t:0},end:1,samples:[{a:0,b:.4,error:null},{a:.4,b:1,error:60}]}';
assert.equal(run(`gradeNote(${late}).name`), 'Miss');
assert.equal(run(`gradeNote(${late},true).name`), 'Perfect');
assert.equal(run('gradeNote({note:{t:0},end:1,samples:[]},true).name'), 'Miss');
for (const [mode, midi, points] of [['coins','null',1],['hybrid','null',.8],['hybrid','60+songShift(currentSong)',1],['hybrid','64+songShift(currentSong)',.8]]) {
  start(mode);
  run(`updateCoinJudgements(1,.99,birdY,${midi});`);
  assert.equal(run('score'), points);
  assert.equal(run('combo'), 1);
  run(`updateCoinJudgements(1.01,1,birdY,${midi});resolveNoteJudgement(noteJudgements[0]);`);
  assert.equal(run('score'), points, 'each coin awards once');
}
start('coins');
run('birdY=ratioToY(1);updateCoinJudgements(1,.99,birdY,null);');
assert.equal(run('score'), 0, 'wrong height cannot catch');
run('updateCoinJudgements(2,1,birdY,null);');
assert.equal(run('judgementCounts.Miss'), 1);
start('coins');
run('updateCoinJudgements(2,0,birdY,null);');
assert.equal(run('score'), 0, 'a stalled frame cannot sweep through a coin');
start('coins');
run('songComplete()');
assert.equal(run('score'), 0, 'completion cannot award uncollected coins');
assert.match(element('performanceReport').innerHTML, /Catch coins.*Coins caught/);
start('relaxed');
assert.equal(run('scoringMode'), 'relaxed');
element('scoringMode').value = 'coins';
assert.equal(run('scoringMode'), 'relaxed', 'mode is fixed during a run');

run(`backingStartTime=5;backingCtx={currentTime:10,baseLatency:.02,outputLatency:.08};`);
assert.ok(Math.abs(run('getBackingTrackTime()')-4.9)<1e-9);
run(`performance={now:()=>1000};backingCtx={state:'running',currentTime:10,getOutputTimestamp:()=>({contextTime:9.8,performanceTime:950})};`);
assert.ok(Math.abs(run('getBackingTrackTime()')-4.85)<.01, 'clock follows output timestamp');
run(`backingCtx={state:'running',currentTime:10,getOutputTimestamp:()=>({contextTime:9.8,performanceTime:1})};`);
assert.ok(run('getBackingTrackTime()')<=5, 'clock cannot exceed rendered audio');
run('backingCtx=null;');
assert.equal(run('getBackingTrackTime()'), null);
console.log('PASS: scoring modes, instant catches, pitch bonuses, misses, stalls, mode locking and audible clock.');
