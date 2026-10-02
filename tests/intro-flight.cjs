const assert=require('node:assert/strict');
const {gameHarness}=require('./game-harness.cjs');
const {run,sandbox,element}=gameHarness();
let now=1000;sandbox.performance={now:()=>now};
run(`startGame('twinkle');micEnabled=true;micReady=true;keyRatio=-1;touchHeld=false;
  getBackingTrackTime=()=>null;gameTime=0;lastTime=1000;
  pipeSchedule=buildPipes([{t:10,end:11,midi:62,ratio:0},{t:12,end:13,midi:71,ratio:.71}]);
  noteJudgements=pipeSchedule.map(n=>makeNoteJudgement(n,null));judgementLastTime=0;
  detectPitch=()=>hzOf(62);drawBackground=drawHitZone=drawBird=drawCoin=()=>{};`);
for(let f=1;f<=30;f++){now=1000+f*1000/60;run(`gameLoop(${now})`);}
assert.equal(run('registerOffset'),12,'higher comfortable octave established during intro');
assert.equal(run('score'),0);assert.equal(run('combo'),0);
assert.match(element('noteHint').textContent,/Warm up/);
const lowerY=run('birdY');
run('detectPitch=()=>hzOf(67)');
for(let f=31;f<=60;f++){now=1000+f*1000/60;run(`gameLoop(${now})`);}
assert.ok(run('birdY')<lowerY-100,'higher singing lifts bird during intro');
const higherY=run('birdY');run('detectPitch=()=>hzOf(64)');
for(let f=61;f<=90;f++){now=1000+f*1000/60;run(`gameLoop(${now})`);}
assert.ok(run('birdY')>higherY+50,'lower singing lowers bird');
assert.equal(run('registerOffset'),12,'no octave wrapping during warmup');
assert.equal(run('judgementCounts.Perfect+judgementCounts.Great+judgementCounts.Good+judgementCounts.Miss'),0);
run('startGame("twinkle");gameTime=0;singingToRatio(hzOf(62));');
assert.equal(run('registerOffset'),0);
now+=30;run('singingToRatio(-1)');now+=100;run('singingToRatio(hzOf(62))');
assert.equal(run('registerOffset'),0,'silence resets stability evidence');
console.log('PASS: stable intro octave alignment, live high/low movement, no scores/combos, locked octave and retry/silence reset.');
