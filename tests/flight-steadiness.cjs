// Real visual-control path with synthetic jitter; not live singing evidence.
const assert=require('node:assert/strict');
const {gameHarness}=require('./game-harness.cjs');
const {run,sandbox}=gameHarness();
run('drawBackground=drawHitZone=drawBird=drawCoin=()=>{};guideVoice="Low";');
for(const fps of [30,60,120,144]){
 for(const centre of [90,110,220,440,880]){
  run(`comfort=null;songPreferences.twinkle=Math.round(midiOf(${centre})-62-4);startGame('twinkle');micEnabled=true;micReady=true;keyRatio=-1;pipeSchedule=[];`);
  const anchor=run(`singingToRatio(${centre})`);
  run(`flightRatioFiltered=null;birdY=ratioToY(${anchor});birdVY=0;lastTime=1000`);
  let now=1000;sandbox.performance={now:()=>now};
  const filtered=[],raw=[];
  for(let i=0;i<fps*2;i++){
   sandbox.frequency=centre+1.5*Math.sin(i/fps*Math.PI*10);run('detectPitch=()=>frequency');
   now=1000+(i+1)*1000/fps;run(`gameLoop(${now})`);
   if(i>fps/2){filtered.push(run('birdY'));raw.push(run('ratioToY(pitchRatioSmooth)'))}
  }
  const span=a=>Math.max(...a)-Math.min(...a);
  assert.ok(span(filtered)<span(raw)*.6,`reduce 3 Hz wobble at ${centre}Hz / ${fps}fps`);
  // Small sustained changes converge instead of being locked out.
  sandbox.frequency=centre+2;const target=run('ratioToY(singingToRatio(frequency))');
  for(let i=0;i<fps*.6;i++){now+=1000/fps;run(`gameLoop(${now})`)}
  assert.ok(Math.abs(run('birdY')-target)<.15,'small held change follows within 600ms');
  sandbox.frequency=centre*2**(1/12);const before=run('birdY');now+=1000/fps;run(`gameLoop(${now})`);
  assert.ok(run('birdY')<before,'new note starts moving on first sample');
  const goal=run('ratioToY(pitchRatioSmooth)');
  for(let i=0;i<Math.ceil(fps*.25);i++){now+=1000/fps;run(`gameLoop(${now})`)}
  assert.ok(Math.abs(run('birdY')-goal)<Math.abs(before-goal)*.06,'note settles promptly');
 }
 // Slow slides stay continuous through the former lock threshold.
 run('flightRatioFiltered=null;assistedLane=null');let last=run('steadyFlightRatio(.2,1/60,true)');
 for(let i=1;i<=fps;i++){
  const ratio=.2+.14*i/fps;const next=run(`steadyFlightRatio(${ratio},${1/fps})`);
  assert.ok(next>=last&&next-last<.02,'no threshold jumps on a slow slide');last=next;
 }
}
run('flightRatioFiltered=.29');assert.equal(run('steadyFlightRatio(.31,.016,true)'),.31);
run('startGame("twinkle")');assert.equal(run('flightRatioFiltered'),null);
run('keyRatio=.57;gameLoop(9000)');assert.equal(run('flightRatioFiltered'),null);
run('trackedMidi=50.8;gameTime=10.5;assistedLane=null');const tracked=run('trackedMidi');
run('steadyFlightRatio(.05,.016)');assert.equal(run('trackedMidi'),tracked);assert.equal(run('gameTime'),10.5);
assert.equal(run('voiceMatchesTarget(150,0)'),false,'smooth height does not make a wrong note match');
// A low unrelated first sample stays low; it cannot guess a higher register.
run('comfort=null;songPreferences.twinkle=-12;startGame("twinkle");pipeSchedule=[]');
assert.ok(run('singingToRatio(110)')<0);assert.equal(run('registerOffset'),0);
// Even extreme valid frequencies produce reachable visual targets.
run('followPitch=(y)=>{targetBirdY=y};micEnabled=true;micReady=true;keyRatio=-1');
for(const frequency of [82.41,110,880,1567]){
 sandbox.frequency=frequency;run('detectPitch=()=>frequency;lastSingMs=-Infinity');
 run('gameLoop(9000)');assert.ok(run('targetBirdY>=PLAY_TOP+BIRD_R && targetBirdY<=PLAY_BOT-BIRD_R'));
}
console.log('PASS: reduced 3 Hz wobble at 90–880Hz and 30–144fps; small held changes converge; notes respond immediately and settle within 250ms; slides stay continuous; reset/key/breath handling and judgement/time independent. Live feel review pending.');
