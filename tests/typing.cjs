const assert = require('node:assert/strict');
const {gameHarness} = require('./game-harness.cjs');
async function harness() {
  const h=gameHarness({mode:'full'}), inputHandlers={}, controls={};
  h.element('typingInput').addEventListener=(name,fn)=>inputHandlers[name]=fn;
  for(const id of ['btnSingMode','btnTypeMode','typingPause','typingRestart','typingMenu'])
    h.element(id).addEventListener=(name,fn)=>controls[id]=fn;
  let now=1000, captures=0, oscillators=0, closed=0, suspended=0;
  const contexts=[];
  h.sandbox.performance={now:()=>now};
  h.sandbox.navigator.mediaDevices={getUserMedia(){captures++;throw Error('Unexpected mic');}};
  const param=()=>({value:0,events:[],setValueAtTime(v,t){this.events.push([v,t]);},linearRampToValueAtTime(){},cancelScheduledValues(t){this.events=this.events.filter(e=>e[1]<t);}});
  h.sandbox.window.AudioContext=class {
    constructor(){this.currentTime=10;this.state='running';contexts.push(this);}
    createOscillator(){oscillators++;return {frequency:param(),connect(){},disconnect(){},start(){},stop(){}};}
    createGain(){return {gain:param(),connect(){},disconnect(){}};}
    resume(){this.state='running';return Promise.resolve();}
    suspend(){suspended++;this.state='suspended';return Promise.resolve();}
    close(){closed++;this.state='closed';return Promise.resolve();}
  };
  h.run(`installTypingControls(); setControlMode('type'); currentSong='twinkle'; startTypingGame();
    drawBackground=()=>{};drawPipe=()=>{};drawBird=()=>{};drawCoin=()=>{};`);
  await Promise.resolve(); await Promise.resolve();
  return {...h,inputHandlers,controls,contexts,time:v=>now=v,
    counts:()=>({captures,oscillators,closed,suspended}),
    input(text, type='insertText') {h.element('typingInput').value=text; inputHandlers.input({data:text,inputType:type});}};
}

(async()=>{
for(const speed of [.75,1,1.25]) {
  const h=await harness(),{run}=h;
  run(`typingSpeed=${speed};startTypingGame()`);await Promise.resolve();await Promise.resolve();
  assert.equal(run('typingRun.words.length'),32);
  assert.equal(run('typingRun.notes.length'),42);
  assert.equal(run('typingRun.words[0].notes.length'),2);
  assert.ok(run('typingRun.lead')>=4);
  assert.ok(run('typingNoteX(typingRun.notes[0],typingRun)')<390,'first note visible at count-in start');
  assert.ok(run('typingNoteX(typingRun.notes[1],typingRun)')<390,'second note visible at count-in start');
  assert.equal(run('JSON.stringify(typingRun.notes.map(n=>n.note.midi))'),run('JSON.stringify(TWINKLE_NOTES.map(n=>n.midi))'));
  assert.equal(run('typingAudio.oscillator.frequency.events.length'),42,'entire melody scheduled before typing');
  assert.ok(Math.abs(run('(typingRun.notes[10].at-typingRun.lead)*typingRun.speed-(TWINKLE_NOTES[10].t-TWINKLE_NOTES[0].t)'))<1e-8);
  h.input('TW');h.input('x');assert.equal(run('typingRun.letter'),2);assert.equal(run('typingRun.errors'),1);
  h.input(' !., inkle');assert.equal(run('typingRun.words[0].status'),'prepared');assert.equal(run('typingRun.score'),0);
  run('advanceTyping(typingRun.notes[0].at)');assert.equal(run('typingRun.score'),100);
  run('advanceTyping(typingRun.notes[0].at)');assert.equal(run('typingRun.score'),100,'score once');
  run('advanceTyping(typingRun.notes[1].at)');assert.equal(run('typingRun.collected'),2,'whole multi-note word');
  assert.equal(h.counts().captures,0);
  for(const delta of [.301,.3,0,-.001]) {
    run('stopTypingGame();typingRun=createTypingRun();typingRun.launching=false');
    run(`acceptTypingText('twinkle',typingRun.lead-(${delta}))`);
    assert.equal(run('typingRun.words[0].status'),delta>=0?'prepared':'missed');
    assert.equal(run('typingRun.score'),delta>=0 && delta<=.3?25+(delta===0?100:0):0);
  }
}
{
  const h=await harness(),{run,element}=h;
  h.input('TwinkleTwinkleLittleStarHowIWonder');
  assert.equal(run('typingRun.word'),5);assert.equal(run('typingRun.accepted'),27);
  assert.equal(run('typingRun.errors'),0);assert.match(element('typingMessage').textContent,/Ready/);
  assert.equal(run('typingRun.words[5].status'),'waiting','cannot spill into hidden words');
  assert.equal(run('typingRun.windowStart'),0,'prepared words stay visible');
  run('advanceTyping(typingRun.words[0].deadline+.001)');h.contexts[0].currentTime=run('typingRun.anchor+typingRun.clock');
  h.input('I');assert.equal(run('typingRun.words[5].status'),'prepared');
  h.input('w','insertFromPaste');assert.equal(run('typingRun.letter'),0);
  h.input('w','insertReplacementText');assert.equal(run('typingRun.letter'),0);
  run('advanceTyping(typingRun.words[3].deadline+.001)');h.contexts[0].currentTime=run('typingRun.anchor+typingRun.clock');
  h.inputHandlers.compositionstart();h.inputHandlers.compositionend({data:'w'});h.input('w','insertFromComposition');
  assert.equal(run('typingRun.letter'),1,'IME counted once');
  h.input('o');assert.equal(run('typingRun.letter'),2);
  const errors=run('typingRun.errors');
  run("acceptTypingText('nder',typingRun.words[9].deadline+.001)");
  assert.equal(run('typingRun.windowStart'),10,'all missed deadlines advanced in one event');
  assert.equal(run('typingRun.errors'),errors,'stale partial commit ignored');assert.equal(run('typingRun.letter'),0);
  assert.equal(run('typingRun.words[6].status'),'missed');
}
{
  const h=await harness(),{run}=h;
  // Prepare each window as music unlocks it, including the final word ahead of time.
  run(`for(let i=0;i<typingRun.words.length;i++) {
    const t=i<5?0:typingRun.words[i-5].deadline+.001;
    acceptTypingText(typingRun.words[i].match,t);
  }`);
  assert.equal(run('typingRun.words.at(-1).status'),'prepared');assert.equal(run('typingRun.done'),false);
  run('advanceTyping(typingRun.end)');assert.equal(run('typingRun.collected'),42);assert.equal(run('typingRun.score'),4200);
  assert.ok(run('typingStats(typingRun).wpm')>0);run('finishTypingGame()');assert.equal(run('state'),'complete');
  assert.equal(h.saved.get(run('typingBestKey(1)')),'4200');
  assert.notEqual(run('typingBestKey(.75)'),run('typingBestKey(1)'));
  assert.notEqual(run('typingBestKey(1.25)'),run('typingBestKey(1)'));
  assert.equal(run('typingRun'),null);assert.equal(run('typingAudio'),null);
  run('startTypingGame()');await Promise.resolve();assert.equal(run('typingRun.score'),0);
  assert.equal(h.counts().captures,0);
}
{
  const h=await harness(),{run}=h;
  h.contexts[0].currentTime+=3;run('typingFrame(1000);toggleTypingPause(true)');await Promise.resolve();
  const clock=run('typingRun.clock');h.time(90000);h.input('twinkle');run('typingFrame(90000)');
  assert.equal(run('typingRun.clock'),clock);assert.equal(run('typingRun.accepted'),0);
  run('toggleTypingPause(false)');await Promise.resolve();assert.equal(run('paused'),false);
  assert.equal(run('typingNow()'),clock,'audio clock freezes with pause');
  run('toggleTypingPause(true)');await Promise.resolve();
  run('toggleTypingPause(false);toggleTypingPause(true)');await Promise.resolve();
  assert.equal(run('paused'),true,'background pause cancels pending resume');
  h.sandbox.document.visibilityState='hidden';for(const fn of h.handlers.visibilitychange)fn();assert.equal(run('paused'),true);
  h.controls.typingMenu();assert.equal(run('typingRun'),null);assert.equal(run('typingAudio'),null);
  run("playPreview=()=>{};setControlMode('sing')");assert.equal(run('playMode'),'full');assert.equal(h.element('btnModeFull').disabled,false);
  h.sandbox.window.visualViewport={width:390,height:420,offsetTop:20,offsetLeft:0};
  run('startTypingGame();resizeTypingGame()');assert.equal(h.element('typingPanel').style.top,'295px');
  run('stopTypingGame()');await Promise.resolve();assert.equal(run('typingRun'),null,'stale async launch cannot revive run');
}
{
  const h=await harness(),{run}=h;
  run(`drawPipe=()=>{throw Error('Typing drew a pipe')};acceptTypingText('twinkletwinkle');lastTime=0;`);
  let prev=run('birdY');
  for(let i=1;i<=100;i++) {
    h.contexts[0].currentTime=10+i*.05;run(`typingFrame(${i*50})`);
    const y=run('birdY');assert.ok(Math.abs(y-prev)<=13.00001,'bounded motion every frame');prev=y;
  }
  const scheduled=run('typingAudio.oscillator.frequency.events.length');
  h.contexts[0].currentTime=run('typingRun.anchor+typingRun.end');run('typingFrame(60000)');
  assert.equal(run('state'),'complete','melody ends even on misses');assert.equal(scheduled,42);
  let prevented=0;for(const fn of h.handlers.keydown)fn({key:' ',code:'Space',preventDefault(){prevented++;}});
  assert.equal(prevented,0);
}
{
  const h=await harness(),{run}=h;
  run("stopTypingGame();window.AudioContext=undefined;startTypingGame()");
  assert.equal(run('typingRun.silent'),true);assert.equal(run('typingStats(typingRun).wpm'),0);
  h.time(3000);run('typingFrame(3000)');assert.equal(run('typingRun.clock'),2);
  run('toggleTypingPause(true)');h.time(90000);run('typingFrame(90000)');assert.equal(run('typingRun.clock'),2);
  run('toggleTypingPause(false)');h.time(92000);run('typingFrame(92000)');assert.equal(run('typingRun.clock'),4);
  h.time(95000);run('typingFrame(95000)');assert.equal(run('typingStats(typingRun).duration'),2000,'WPM excludes count-in and pause');
}
for(const fps of [30,60,144]) {
  const h=await harness(),{run}=h;
  run(`typingRun.words.forEach(w=>w.status='prepared');lastTime=0;`);
  let previous=run('birdY');
  for(let i=1;i<=fps*15;i++) {
    h.contexts[0].currentTime=10+i/fps;run(`typingFrame(${i*1000/fps})`);
    const y=run('birdY');assert.ok(Math.abs(y-previous)<=260/fps+.00001,'large/repeated pitch transitions stay bounded');previous=y;
  }
  assert.ok(run('typingRun.collected')>10);
}
console.log('PASS: fixed tempo/pitch, 42-note melody, deadline equality and late recovery, real-second bonus at all speeds, musical five-word window, once-only note scoring, early final word, IME/paste, pause/audio clock, silent fallback/WPM, lifecycle, speed best scores, visible initial notes, no pipes and bounded flight at 30/60/144fps.');
})().catch(e=>{console.error(e);process.exitCode=1;});
