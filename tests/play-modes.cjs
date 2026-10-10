// Full song / Quick play: the choice, what each part contains, and a Quick play that starts in the
// middle of a recording (fade-in, guide, progress, judgements, pause/resume, stall, retry, frame rates).
// Structural checks only: they do not prove a chart sounds right; listening review is separate.
const assert=require('node:assert/strict');
const {gameHarness}=require('./game-harness.cjs');
const noop=()=>{};

// ---- the choice: Full song by default, remembered, locked while a song plays
{
  const {run,element,saved}=gameHarness({mode:null});
  assert.equal(run('playMode'),'full','Full song is the default');
  run(`carouselIndex=SONGS.findIndex(s=>s.id==='baluobo');renderCarousel();`);
  assert.match(element('playModeInfo').textContent,/^Full song: 2:20 · Mandarin \+ English \(Quick play: 0:19\)$/);
  run(`setPlayMode('quick')`);
  assert.equal(saved.get('oohwoo_play_mode_v1'),'quick');
  assert.match(element('playModeInfo').textContent,/^Quick play: 0:19 · Mandarin \(Full song: 2:20\)$/);
  assert.match(element('carouselMeta').textContent,new RegExp(run(`songPlay('baluobo','quick').notes.length`)+' notes · 0:19'));
  run(`state='playing';setPlayMode('full');state='select'`);
  assert.equal(run('playMode'),'quick','no switching in the middle of a song');
  assert.equal(gameHarness({mode:'quick'}).run('playMode'),'quick','saved choice is read at start-up');
}

// ---- what each part contains
{
  const {run}=gameHarness({mode:'full'});
  const keys=Array.from(run('Object.keys(SONG_DATA).filter(key=>!SONG_DATA[key].scoreBased)'));
  for(const key of keys){
    const full=JSON.parse(run(`JSON.stringify(songPlay('${key}','full'))`));
    const quick=JSON.parse(run(`JSON.stringify(songPlay('${key}','quick'))`));
    const fullIds=new Set(full.notes.map(n=>n.id));
    if(key!=='twinkle')assert.ok(quick.notes.every(n=>fullIds.has(n.id)),key+' Quick play is part of the full song');
    assert.ok(full.notes.length>quick.notes.length,key+' full song is longer');
    assert.ok(full.level.start===0&&full.level.end>=full.notes.at(-1).end,key+' full song plays the whole recording');
    assert.ok(full.languages.length>=2,key+' full song has every language section');
    for(const play of [full,quick]){
      assert.ok(play.phrases.every(([a,b],i)=>a<=b&&(!i||a===play.phrases[i-1][1]+1)),key+' phrases cover the part in order');
      assert.equal(play.phrases.at(-1)[1],play.notes.length-1);
      assert.ok(play.level.fadeStart<play.level.end&&play.notes.at(-1).end<=play.level.end,key+' last hold ends before the part ends');
    }
  }
  // Full Twinkle starts with the approved reference verse, unchanged, then the Mandarin verse.
  const approved=JSON.parse(run('JSON.stringify(TWINKLE_NOTES)'));
  const twinkle=JSON.parse(run(`JSON.stringify(songPlay('twinkle','full').notes)`));
  approved.forEach((n,i)=>{assert.equal(twinkle[i].id,n.id);assert.equal(twinkle[i].t,n.t);assert.equal(twinkle[i].end,n.end);assert.equal(twinkle[i].midi,n.midi)});
  assert.ok(twinkle.slice(42).some(n=>/[一-鿿]/.test(n.lyric)),'Mandarin verse follows');
  // Only Twinkle's Quick play uses the semitone-shifted comfort backings (they are 40.6 s long).
  const fetched=[];
  const h=gameHarness({mode:'quick'});
  h.sandbox.fetch=async a=>{fetched.push(a);return{ok:true,arrayBuffer:async()=>new ArrayBuffer(0)}};
  h.sandbox.decodeContext={decodeAudioData:async()=>({})};
  h.run(`songPreferences.twinkle=3`);
  (async()=>{
    await h.run(`loadSongBuffer('twinkle',decodeContext)`);
    h.run(`playMode='full';audioBufferCache={}`);
    assert.equal(Math.abs(h.run(`songShift('twinkle')%12`)),0,'full Twinkle moves by octaves only');
    await h.run(`loadSongBuffer('twinkle',decodeContext)`);
    assert.deepEqual(fetched,['audio/comfort/twinkle-key-3.mp3','audio/1. Twinkle Twinkle Little Star.mp3']);
  })().catch(e=>{console.error(e);process.exitCode=1});
}

// ---- a Quick play that starts in the middle of the recording
(async()=>{
  const {run,sandbox,element,handlers}=gameHarness({mode:'quick'});
  const key='fivemonkeys';
  const level=JSON.parse(run(`JSON.stringify(songPlay('${key}').level)`));
  const notes=JSON.parse(run(`JSON.stringify(songPlay('${key}').notes)`));
  assert.ok(level.start>10&&level.fadeIn>0,'this Quick play starts mid-recording with a fade-in');
  let started,gains=[],tones=[];
  sandbox.window.AudioContext=class{
    constructor(){this.state='running';this.currentTime=50;this.destination={}}
    createBufferSource(){return{connect:noop,start(...a){started=a},stop:noop}}
    createGain(){const id=this.gainCount=(this.gainCount||0)+1;return{gain:{value:0,setValueAtTime:(v,t)=>gains.push([id,'set',v,t]),linearRampToValueAtTime:(v,t)=>gains.push([id,'ramp',v,t])},connect:noop}}
    createOscillator(){const o={frequency:{},connect:noop,disconnect:noop,start(t){o.at=t},stop:noop};tones.push(o);return o}
    suspend(){this.suspended=true}resume(){this.suspended=false}close(){return Promise.resolve()}
  };
  run(`guideEnabled=true;audioBufferCache['${key}:0']={duration:166};currentSong='${key}'`);
  await run('playBackingTrack()');
  const sourceStart=51.7;
  assert.deepEqual(started,[sourceStart,level.start,+(level.end-level.start).toFixed(10)].map((v,i)=>i===2?started[2]:v));
  assert.ok(Math.abs(started[2]-(level.end-level.start))<1e-9);
  assert.ok(Math.abs(run('backingStartTime')-(sourceStart-level.start))<1e-9);
  const backing=gains.filter(g=>g[0]===1).map(g=>g.slice(1));   // the first gain node is the backing track's
  assert.deepEqual(backing.slice(0,2),[['set',0,sourceStart],['ramp',0.45,sourceStart+level.fadeIn]],'fades in from silence');
  assert.deepEqual(backing.slice(-2),[['set',0.45,sourceStart-level.start+level.fadeStart],['ramp',0,sourceStart-level.start+level.end]],'deliberate fade at the part end');
  assert.equal(tones.length,notes.length,'guide plays only this part');
  assert.ok(tones.every(o=>o.at>=sourceStart),'no guide tone before the backing starts');
  assert.ok(Math.abs(Math.min(...tones.map(o=>o.at))-(sourceStart-level.start+notes[0].t))<1e-9);

  // Game clock follows the backing clock from the part's own start, at several frame rates.
  run('drawBackground=drawHitZone=drawBird=drawCoin=()=>{};getBackingTrackTime=()=>backingCtx.currentTime-backingStartTime');
  for(const fps of [30,60,120,144]){
    run(`backingCtx=new window.AudioContext();backingCtx.currentTime=${sourceStart};backingStartTime=${sourceStart-level.start};startGame('${key}');micEnabled=true;micReady=true;keyRatio=-1;touchHeld=false;
      detectPitch=()=>{const n=melodyNoteAt(gameTime);return n&&gameTime>=n.t&&gameTime<n.end?hzOf(n.midi+songShift(currentSong)):-1;};lastTime=1000;`);
    assert.ok(Math.abs(run('gameTime')-level.start)<1e-9,'song clock starts at the part start');
    assert.equal(element('songProgress').value,0,'progress starts at zero');
    assert.equal(element('songTimer').textContent,`0:00/0:${String(Math.ceil(level.end-level.start)).padStart(2,'0')}`);
    let frame=0;const step=()=>{frame++;run(`backingCtx.currentTime+=${1/fps};performance.now=()=>1000+${frame*1000/fps};gameLoop(1000+${frame*1000/fps})`)};
    const half=level.start+(level.end-level.start)/2;
    while(run('gameTime')<half)step();
    const progress=element('songProgress').value;
    assert.ok(Math.abs(progress-(run('gameTime')-level.start))<1e-9,'progress counts from the part start');
    // pause: music and song clock stop together; a long stall afterwards does not skip notes
    handlers.keydown.forEach(fn=>fn({code:'Escape',key:'Escape',preventDefault:noop}));
    assert.equal(run('paused&&backingCtx.suspended'),true);
    const frozen=run('gameTime');run('gameLoop(999999)');assert.equal(run('gameTime'),frozen);
    handlers.keydown.forEach(fn=>fn({code:'Escape',key:'Escape',preventDefault:noop}));
    assert.equal(run('!paused&&!backingCtx.suspended'),true);
    run(`lastTime=1000+${frame*1000/fps}`);
    while(run('state')==='playing'&&frame<fps*60)step();
    assert.equal(run('state'),'complete',fps+' fps completes at the part end');
    assert.ok(run('gameTime')>=level.end);
    assert.equal(run('Object.values(judgementCounts).reduce((a,b)=>a+b,0)'),notes.length,'only this part is judged');
    assert.equal(run('judgementCounts.Miss'),0,fps+' fps: later notes of the recording are not misses');
    assert.match(element('performanceReport').innerHTML,/Quick play · /);
  }
  // retry: everything resets to the part start, even before the audio clock is ready
  run(`getBackingTrackTime=()=>null;startGame('${key}')`);
  assert.equal(run('gameTime'),level.start);
  assert.equal(run('Object.values(judgementCounts).reduce((a,b)=>a+b,0)'),0);
  assert.equal(run('nextPipeIdx+nextCoinIdx'),0);
  console.log('PASS: Full song default and remembered choice, mode lock while playing, Full contains Quick, full Twinkle keeps the approved verse, comfort backings only for Twinkle Quick, mid-recording Quick start (offset, fade-in, guide, progress, pause/resume, stall, completion, no extra misses at 30-144 fps, retry).');
})().catch(e=>{console.error(e);process.exitCode=1});
