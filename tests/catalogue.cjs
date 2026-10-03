const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {gameHarness}=require('./game-harness.cjs');
const {run,sandbox,element}=gameHarness();
const keys=Array.from(run('Object.keys(SONG_DATA)'));
assert.equal(keys.length,22);
// Every song is exercised in both Full song and Quick play.
for(const mode of ['full','quick'])for(const key of keys){
  run(`playMode='${mode}'`);
  const data=JSON.parse(run(`JSON.stringify(SONG_DATA['${key}'])`));
  const level=JSON.parse(run(`JSON.stringify(songPlay('${key}').level)`));
  assert.ok(fs.statSync(path.resolve(__dirname,'..',data.audio)).size>1000);
  run(`carouselIndex=SONGS.findIndex(s=>s.id==='${key}');currentSong='${key}';updateComfortUI();`);
  assert.equal(element('btnPlaySong').disabled,false,key+' enabled');
  const schedule=JSON.parse(run(`JSON.stringify(buildPipes(SONG_DATA['${key}'].notes,SONG_DATA['${key}'].introOffset))`));
  assert.ok(schedule.every((n,i)=>Number.isFinite(n.midi)&&n.end>n.t&&(!i||n.t>=schedule[i-1].t)));
  assert.ok(schedule.every(n=>n.t>=level.start&&n.end<=level.end),key+' '+mode+' notes inside the part');
  assert.equal(new Set(schedule.map(n=>n.id)).size,schedule.length,key+' '+mode+' note ids unique');
  const pitches=[];const noop=()=>{};
  const starts=[];
  const ctx={createGain:()=>({gain:{value:0,setValueAtTime:noop,linearRampToValueAtTime:noop},connect:noop,disconnect:noop}),destination:{},
    createOscillator:()=>({frequency:{set value(v){pitches.push(v)}},connect:noop,disconnect:noop,start:t=>starts.push(t),stop:noop})};
  sandbox.guideTestContext=ctx;run(`scheduleGuide(guideTestContext,'${key}',100)`);
  assert.equal(pitches.length,schedule.length);
  assert.ok(starts.every(t=>t>=100+level.start),key+' '+mode+' no guide tone before the backing starts');
  schedule.forEach((n,i)=>assert.ok(Math.abs(pitches[i]-run(`hzOf(${n.midi}+songShift('${key}'))`))<1e-8));
  if(key!=='twinkle'||mode==='full'){
    const before=run(`songShift('${key}')`);run('adjustSongKey(-1)');
    assert.equal(run(`songShift('${key}')`),Math.max(-36,before-12));
    assert.equal(run(`backingKey(songShift('${key}'))`),0,'original backing pitch class');
  }
  // Exercise the real game loop through every note and the deliberate ending.
  run(`startGame('${key}');micEnabled=true;micReady=true;keyRatio=-1;touchHeld=false;
    getBackingTrackTime=()=>null;gameTime=${level.start}-1.7;lastTime=1000;judgementLastTime=gameTime;
    drawBackground=drawHitZone=drawBird=drawCoin=()=>{};
    detectPitch=()=>{const n=melodyNoteAt(gameTime);return n&&gameTime>=n.t&&gameTime<n.end?hzOf(n.midi+songShift(currentSong)):-1;};
    for(let f=1;state==='playing'&&f<${Math.ceil((level.end-level.start+5)*60)};f++){
      performance.now=()=>1000+f*1000/60;gameLoop(1000+f*1000/60);
    }`);
  assert.equal(run('state'),'complete',key+' '+mode+' completes');
  assert.equal(run('Object.values(judgementCounts).reduce((a,b)=>a+b,0)'),schedule.length);
  assert.equal(run('judgementCounts.Miss'),0,key+' correct voice scores all notes');
  assert.equal(run('bestCombo'),schedule.length,key+' sustained combo');
  assert.match(element('performanceReport').innerHTML,/Notes hit/);
  assert.ok(element('performanceReport').innerHTML.startsWith(`<strong`)&&element('performanceReport').innerHTML.includes(mode==='full'?'Full song':'Quick play'));
  run('state="select";');
}
(async()=>{
  const fetched=[];sandbox.fetch=async asset=>{fetched.push(asset);return{ok:true,arrayBuffer:async()=>new ArrayBuffer(0)}};
  sandbox.decodeContext={decodeAudioData:async()=>({duration:120})};run('audioBufferCache={}');
  run(`playMode='full'`);
  for(const key of keys)await run(`loadSongBuffer('${key}',decodeContext)`);
  assert.equal(fetched.length,22);assert.ok(fetched.every(p=>!p.includes('comfort/twinkle')));
  console.log('PASS: all 22 songs in Full song and Quick play: assets, playable menus, MIDI/hold schedules inside each part, guide pitches and start times, octave adjustments, whole-part simulation, ranks and original backing loads (Full Twinkle included).');
})().catch(e=>{console.error(e);process.exitCode=1});
