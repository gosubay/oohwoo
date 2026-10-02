// Actual embedded chart and runtime; numerical/structural tests do not prove ear accuracy.
const fs = require('node:fs'), path = require('node:path'), vm = require('node:vm');
const assert = require('node:assert/strict'), crypto = require('node:crypto');
const root = path.resolve(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'ooh-woo-game.html'),'utf8');
const chartText = html.match(/<script id="twinkle-chart" type="application\/json">([\s\S]*?)<\/script>/)[1];
const chart = JSON.parse(chartText);
const notes = chart.notes;
assert.equal(notes.length,42);
assert.equal(new Set(notes.map(n=>n.id)).size,42);
assert.equal(chart.provenance.listeningVerified,false);
assert.equal(chart.provenance.ownerApproved,false);
for (const asset of chart.provenance.assets) {
  const data = fs.readFileSync(path.join(root,asset.path));
  assert.equal(data.length,asset.bytes);
  assert.equal(crypto.createHash('sha256').update(data).digest('hex'),asset.sha256);
}
const inventory = JSON.parse(fs.readFileSync(path.join(root,'docs/audio-inventory.json'),'utf8').replace(/^\uFEFF/,''));
assert.equal(inventory.length,23);
for(const a of inventory) assert.equal(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,a.path))).digest('hex'),a.sha256);
const pitchName = midi=>['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'][midi%12]+(Math.floor(midi/12)-1);
for(let i=0;i<notes.length;i++) {
 const n=notes[i];assert.equal(n.pitch,pitchName(n.midi));
 assert.ok(n.onset>=chart.level.start && n.end>n.onset && n.end<=chart.level.end);
 assert.ok(!i || n.onset>=notes[i-1].end,'no overlapping melody events');
 assert.ok(n.lyric && n.phrase===Math.floor(i/7)+1);
}
assert.equal(chart.level.melodyStart,notes[0].onset);
assert.equal(chart.level.melodyEnd,notes.at(-1).end);
assert.ok(chart.level.fadeStart>=notes.at(-1).end && chart.level.end>chart.level.fadeStart);
const timeline=[...notes.map(n=>({start:n.onset,end:n.end})),...chart.rests].sort((a,b)=>a.start-b.start);
let cursor=chart.level.start;
for(const e of timeline){assert.equal(e.start,cursor,'every gap is an explicit rest');assert.ok(e.end>e.start);cursor=e.end}
assert.equal(cursor,chart.level.end);
assert.equal(chart.phrases.length,6);
for(const p of chart.phrases)assert.ok(notes.slice(p.firstNote,p.lastNote+1).every(n=>n.phrase===p.id));
assert.ok(chart.beatMarkers.times.length>notes.length,'beats are not note events');

const noop=()=>{}, elements=new Map(), handlers=[];
function el(id){if(!elements.has(id))elements.set(id,{style:{},dataset:{},classList:{add:noop,remove:noop,toggle:noop},addEventListener:noop,querySelectorAll:()=>[],getContext:()=>new Proxy({},{get:()=>noop}),getBoundingClientRect:()=>({width:390,height:844}),textContent:'',innerHTML:''});return elements.get(id)}
el('twinkle-chart').textContent=chartText;
const sandbox=vm.createContext({console,Math,Date,Float32Array,Uint8Array,performance:{now:()=>1000},
 setTimeout:noop,clearTimeout:noop,setInterval:noop,clearInterval:noop,requestAnimationFrame:()=>1,cancelAnimationFrame:noop,
 localStorage:{getItem:()=>null,setItem:noop},navigator:{userAgent:'iPhone test'},window:{innerWidth:390,innerHeight:844,addEventListener:noop},
 document:{getElementById:el,querySelectorAll:()=>[],addEventListener:(event,fn)=>{if(event==='keydown')handlers.push(fn)}}});
vm.runInContext(html.match(/<script>([\s\S]*?)<\/script>/)[1],sandbox);
const run=s=>vm.runInContext(s,sandbox);
run('drawBackground = drawHitZone = drawBird = drawCoin = () => {};');
// The other 21 songs are recording-based drafts: never legacy, never claimed as owner-approved.
assert.equal(run('Object.values(SONG_DATA).filter(s=>s.chartStatus === "legacy-unverified").length'),0);
assert.equal(run('Object.values(SONG_DATA).filter(s=>s.chartStatus === "recording-drafted; owner-listening-pending").length'),21);
for (const voice of ['Low','Medium','High']) {
 const tones=[];
 sandbox.fakeCtx={destination:{},createGain:()=>({gain:{setValueAtTime:noop,linearRampToValueAtTime:noop},connect:noop}),createOscillator:()=>{const t={frequency:{},connect:noop,start(t){this.startTime=t},stop(t){this.endTime=t}};tones.push(t);return t}};
 run(`guideVoice='${voice}'; scheduleGuide(fakeCtx,'twinkle',50)`);
 assert.equal(tones.length,42);
 tones.forEach((t,i)=>{assert.ok(Math.abs(t.startTime-50-notes[i].onset)<1e-9);assert.ok(Math.abs(t.endTime-50-notes[i].end)<1e-9);const octaves=Math.log2(t.frequency.value/(440*2**((notes[i].midi-69)/12)));assert.ok(Math.abs(octaves-Math.round(octaves))<1e-8)});
}
// Real game loop driven by backing clock at the beginning, middle and end at all frame rates.
for(const fps of [30,60,120,144]){
 run(`backingCtx={currentTime:50,suspend(){this.suspended=true},resume(){this.suspended=false},close:()=>Promise.resolve()};backingStartTime=50;startGame('twinkle');keyRatio=-1;micEnabled=false;`);
 const original=run('JSON.stringify(pipeSchedule.map(n=>[n.t,n.end,n.spawnTime]))');
 for(const audioTime of [10.33,24.03,38.66,39.89,40.59]){
   run(`backingCtx.currentTime=50+${audioTime};gameLoop(1000+${audioTime}*1000+1000/${fps})`);
   assert.ok(Math.abs(run('gameTime')-audioTime)<1e-9);assert.equal(run('state'),'playing');
   assert.equal(run('JSON.stringify(pipeSchedule.map(n=>[n.t,n.end,n.spawnTime]))'),original);
 }
 handlers.forEach(fn=>fn({code:'Escape',preventDefault:noop}));
 assert.equal(run('paused && backingCtx.suspended'),true);
 run('gameLoop(999999)');assert.ok(Math.abs(run('gameTime')-40.59)<1e-9);
 handlers.forEach(fn=>fn({code:'Escape',preventDefault:noop}));
 assert.equal(run('!paused && !backingCtx.suspended'),true);
 run('backingCtx.currentTime=90.601;gameLoop(1000000)');assert.equal(run('state'),'complete');
}
run('backingCtx=null;startGame("twinkle");gameTime=14.9;gameLoop(1000)');
assert.equal(run('karaokeActiveIdx'),-1,'phrase breath clears lyric highlight');
run('gameTime=38.7;gameLoop(1000)');assert.equal(run('karaokeActiveIdx'),41);
run('gameTime=40.1;gameLoop(1000)');assert.equal(run('karaokeActiveIdx'),-1);
// Exercise actual playback setup: backing fade/duration must use the same bounds.
let started, ramp, held;
sandbox.window.AudioContext = class {
 constructor(){this.state='running';this.currentTime=50;this.destination={}}
 createBufferSource(){return {connect:noop,start(...args){started=args},stop:noop}}
 createGain(){return {gain:{value:0,setValueAtTime(value,time){held=[value,time]},linearRampToValueAtTime(value,time){ramp=[value,time]}},connect:noop}}
 close(){return Promise.resolve()}
};
run('guideEnabled=false;audioBufferCache.twinkle={duration:88.96};currentSong="twinkle"');
(async()=>{
 await run('playBackingTrack()');
 assert.deepEqual(started,[51.7,chart.level.start,chart.level.end-chart.level.start]);
 assert.deepEqual(held,[.85,51.7+chart.level.fadeStart]);
 assert.deepEqual(ramp,[0,51.7+chart.level.end]);
 const evidence=JSON.parse(fs.readFileSync(path.join(root,'docs/twinkle-analysis.json'),'utf8'));
 assert.equal(evidence.chartSha256,crypto.createHash('sha256').update(chartText.replace(/\r\n/g,'\n')).digest('hex'),'analysis is tied to current embedded chart text (LF normalised)');
 assert.equal(evidence.notes.length,42);
 for(const n of evidence.notes){assert.ok(n.frames>15);assert.ok(Math.abs(n.medianMidi-n.expectedMidi)<.35)}
 assert.equal(evidence.alignment.backing.stemDelaySeconds,0);
 assert.equal(evidence.alignment.vocal.stemDelaySeconds,0);
 console.log('PASS: asset hashes, 42 numerical vocal pitches/octaves, explicit notes/rest coverage, phrases, guide ends, clock deadlines at 30/60/120/144 fps, pause/resume, backing fade and deliberate completion. Listening and real microphone acceptance remain pending.');
})().catch(e=>{console.error(e);process.exitCode=1});
