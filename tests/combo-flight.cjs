const assert = require('node:assert/strict');
const {gameHarness} = require('./game-harness.cjs');
const {run, sandbox, element, html} = gameHarness();
run('drawBackground=drawHitZone=drawBird=drawCoin=()=>{};');
assert.match(html, /id="comboDisplay"[\s\S]*?Score[\s\S]*?Combo[\s\S]*?Multiplier/);
assert.doesNotMatch(html, /pipes cleared/);
assert.equal(run('formatScore(48)'), '48');
assert.equal(run('formatScore(48.5)'), '48.5');
for (const [combo, points, speed] of [[0,1,1],[9,1,1],[10,2,1.3],[19,2,1.3],[20,2.5,1.6],[39,2.5,1.6],[40,3,2],[100,3,2]]) {
  assert.equal(run(`comboFlightTier(${combo})[1]`),speed);
  assert.equal(run(`comboToReward(${combo})[1]`),points);
}
for (const fps of [30,60,120,144]) {
  run('flightSpeed=1;flightDistance=0;combo=40;');
  let prev=1;
  for(let frame=0;frame<fps*3;frame++) {
    run(`updateFlightSpeed(${1/fps})`);
    const next=run('flightSpeed');
    assert.ok(next>=prev && next<2,'smooth boost without overshoot'); prev=next;
    assert.equal(run('flightX(HIT_ZONE_X)'),run('HIT_ZONE_X'),'singing line stays fixed');
  }
  assert.ok(Math.abs(run('flightSpeed')-2)<.005);
  assert.ok(run('flightX(HIT_ZONE_X+120)-flightX(HIT_ZONE_X)')>239,'notes spread farther apart');
  run(`combo=0;updateFlightSpeed(${1/fps})`);
  assert.ok(run('flightSpeed')>1 && run('flightSpeed')<prev,'miss eases down');
}
for (const speed of [1,1.3,1.6,2,1.47,1.83]) {
  run(`flightSpeed=${speed};`);
  assert.ok(run(`buildPipes(TWINKLE_NOTES).every(n => Math.abs(flightX(
    PIPE_SPAWN_X+PIPE_W/2-PIPE_SPEED*(n.t-n.spawnTime))-HIT_ZONE_X)<1e-8)`));
}
const results=[];
for (const count of [0,9,19,39,40]) {
  run(`startGame('twinkle');combo=${count};flightSpeed=comboFlightTier(combo)[1];
    micEnabled=false;micReady=false;keyRatio=.29;birdY=ratioToY(.29);birdVY=0;
    gameTime=0;lastTime=1000;getBackingTrackTime=()=>null;detectPitch=()=>-1;
    pipeSchedule=buildPipes([{t:.1,end:.7,ratio:.29,midi:songTonicMidi(currentSong)+melodySemitones(.29),lyric:'star'}]);
    noteJudgements=pipeSchedule.map(n=>makeNoteJudgement(n,null));judgementLastTime=0;
    nextPipeIdx=0;activeCoins=[];`);
  for(let f=1;f<=45;f++) { sandbox.performance={now:()=>1000+f*1000/60};run(`gameLoop(${1000+f*1000/60})`); }
  results.push({time:run('gameTime'),y:run('birdY'),count:run('combo')-count,coins:run('activeCoins.length')});
  assert.equal(run('combo'),count+1);
  assert.equal(run('score'),run('comboToReward(combo)[1]'),'point tiers preserved');
  assert.equal(element('comboNum').textContent, count+1);
  assert.equal(element('multiplierNum').textContent, `${run('comboToReward(combo)[1]')}×`);
  assert.equal(element('scoreDisplay').textContent, String(run('score')));
}
assert.ok(results.every(r=>r.time===results[0].time && r.y===results[0].y && r.count===1 && r.coins===0));
// No scheduled note means a rest; a miss before an overlapping success starts a new streak.
run('startGame("twinkle");combo=19;micEnabled=false;micReady=false;keyRatio=.29;birdY=ratioToY(.29);birdVY=0;gameTime=1;lastTime=1000;getBackingTrackTime=()=>null;detectPitch=()=>-1;pipeSchedule=[];noteJudgements=[];nextPipeIdx=0;activeCoins=[];');
sandbox.performance={now:()=>1100}; run('gameLoop(1100)');
assert.equal(run('combo'),19);
run(`gameTime=1;lastTime=1000;noteJudgements=[makeNoteJudgement({t:.8,end:1,midi:66},null),makeNoteJudgement({t:1.01,end:1.05,midi:66},null)];
noteJudgements[1].samples=[{a:1.01,b:1.05,error:0}];`);
run('gameLoop(1100)');
assert.equal(run('combo'),1); assert.equal(run('score'),1);
assert.equal(element('multiplierNum').textContent,'1×');
run('gameLoop(1200)'); assert.equal(run('score'),1,'resolved notes score only once');
run('gameTime=1;lastTime=1000;combo=19;noteJudgements=[makeNoteJudgement({t:.8,end:1,midi:66},null)];');
run('gameLoop(1100)');
assert.equal(run('combo'),0); assert.equal(element('comboNum').textContent,0);
assert.equal(element('multiplierNum').textContent,'1×');
run('paused=true'); const snapshot=run('[flightSpeed,flightDistance,bgOffset1,gameTime,score].join()');
run('gameLoop(2000)'); assert.equal(run('[flightSpeed,flightDistance,bgOffset1,gameTime,score].join()'),snapshot);
run('startGame("twinkle")'); assert.equal(run('flightSpeed'),1); assert.equal(run('flightDistance'),0);
assert.equal(run('score'),0); assert.equal(run('combo'),0);
assert.equal(element('multiplierNum').textContent,'1×');
console.log('PASS: 10/20/40 tiers, smooth boost/miss easing at 30–144fps, wider spacing, exact authored arrivals, threshold scoring, pause and retry reset.');
