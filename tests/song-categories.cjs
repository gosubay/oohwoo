const assert=require('node:assert/strict');
const {gameHarness}=require('./game-harness.cjs');
const {run,sandbox,element}=gameHarness({mode:'full'});
// Browser audio is covered below; keep menu tests quiet in this headless harness.
run('playPreview=()=>{}');
assert.equal(run('SONGS.length'),36);
assert.equal(run('new Set(SONGS.map(s=>s.id)).size'),36);
for(const [category,count] of [['all',36],['nursery',22],['christmas',6],['cny',8]]){
  run(`setSongCategory('${category}')`);
  assert.equal(run('filteredSongs().length'),count);
  const first=run('carouselIndex');
  for(let i=0;i<count;i++){
    assert.equal(run(`songCategory==='all'||SONGS[carouselIndex].category===songCategory`),true);
    run('carouselNext()');
  }
  assert.equal(run('carouselIndex'),first,'next wraps within '+category);
  run('carouselPrev();carouselNext()');
  assert.equal(run('carouselIndex'),first,'previous wraps within '+category);
  run('renderCarousel()');
  assert.match(element('songCategoryCount').textContent,new RegExp(`of ${count} songs`));
  if(category==='cny'){
    assert.equal(element('btnPlaySong').disabled,true);
    assert.match(element('carouselCard').innerHTML,/Coming soon/);
    assert.equal(run('filteredSongs().filter(s=>s.id===\'hexinnian\').length'),1);
    assert.equal(run('filteredSongs().every(s=>!SONG_DATA[s.id])'),true,'no fallback melody for pending titles');
  }
}
run("setSongCategory('christmas');carouselIndex=SONGS.findIndex(s=>s.id==='silentnight');setSongCategory('all')");
assert.equal(run('SONGS[carouselIndex].id'),'silentnight','retain selected song if still visible');
run('renderCarousel()');
assert.equal(element('btnPlaySong').disabled,false);
assert.equal(element('btnModeFull').disabled,false);
assert.equal(element('btnModeFull').textContent,'Melody practice');
assert.match(element('carouselMeta').textContent||element('carouselCard').innerHTML,/Melody practice/);

const openings={jinglebells:[55,64,62,60],deckthehalls:[67,65,64,62,60],silentnight:[67,69,67,64],
  wewish:[55,60,60,62,60,59],joytotheworld:[72,71,69,67,65,64,62,60],firstnoel:[64,62,60,62,64,65,67]};
const keys=Object.keys(openings);
for(const key of keys){
  assert.deepEqual(Array.from(run(`CAROL_PRACTICE.${key}.notes.slice(0,${openings[key].length}).map(n=>n.midi)`)),openings[key]);
  for(const mode of ['full','quick']){
    run(`playMode='${mode}';carouselIndex=SONGS.findIndex(s=>s.id==='${key}');currentSong='${key}';updateComfortUI()`);
    assert.equal(element('btnPlaySong').disabled,false);
    const play=JSON.parse(run(`JSON.stringify(songPlay('${key}'))`));
    assert.equal(play.scoreBased,true);
    assert.ok(play.notes.length>0);
    assert.ok(play.notes.every((n,i,a)=>n.end>n.t&&n.t>=play.level.start&&n.end<=play.level.end&&(!i||n.t>=a[i-1].end-1e-5)));
    assert.equal(play.phrases[0][0],0);
    assert.equal(play.phrases.at(-1)[1],play.notes.length-1);
    const fullIds=new Set(Array.from(run(`songPlay('${key}','full').notes.map(n=>n.id)`)));
    assert.ok(play.notes.every(n=>fullIds.has(n.id)));
    run(`startGame('${key}');micEnabled=true;micReady=true;keyRatio=-1;touchHeld=false;
      getBackingTrackTime=()=>null;lastTime=1000;judgementLastTime=gameTime;
      drawBackground=drawHitZone=drawBird=drawCoin=()=>{};
      detectPitch=()=>{const n=melodyNoteAt(gameTime);return n&&gameTime>=n.t&&gameTime<n.end?hzOf(n.midi+songShift(currentSong)):-1;};
      for(let f=1;state==='playing'&&f<${Math.ceil((play.seconds+5)*60)};f++){
        performance.now=()=>1000+f*1000/60;gameLoop(1000+f*1000/60);
      }`);
    assert.equal(run('state'),'complete',key+' '+mode+' completes');
    assert.equal(run('judgementCounts.Miss'),0,key+' '+mode+' correct singing');
    assert.equal(run('bestCombo'),play.notes.length);
    assert.ok(element('performanceReport').innerHTML.includes(play.label));
    run("state='select'");
  }
}

(async()=>{
  let fetches=0;
  sandbox.fetch=()=>{fetches++;throw Error('Score practice must work without a download')};
  sandbox.pianoContext={sampleRate:8000,createBuffer:(channels,length,rate)=>{
    const data=new Float32Array(length);
    return{length,sampleRate:rate,duration:length/rate,getChannelData:()=>data};
  }};
  for(const key of keys){
    run(`playMode='full';guideEnabled=false`);
    const buffer=await run(`loadSongBuffer('${key}',pianoContext)`);
    const data=buffer.getChannelData(0);
    const first=JSON.parse(run(`JSON.stringify(CAROL_PRACTICE.${key}.notes[0])`));
    assert.ok(data.every(Number.isFinite));
    assert.ok(data.some(v=>Math.abs(v)>.01),'audible piano with guide checkbox off');
    assert.ok(data.slice(0,first.t*8000).every(v=>v===0),'same lead-in as chart');
    const expected=run(`hzOf(${first.midi}+songShift('${key}'))`);
    const start=Math.round((first.t+.03)*8000), length=Math.min(1000,Math.floor((first.end-first.t-.05)*8000));
    let crossings=0;
    for(let i=start+1;i<start+length;i++)if(data[i-1]<=0&&data[i]>0)crossings++;
    assert.ok(Math.abs(crossings*8000/length-expected)<12,'generated pitch matches '+key);
    const again=await run(`loadSongBuffer('${key}',pianoContext)`);
    assert.equal(again,buffer,'reuse same-key audio');
    run(`songPreferences['${key}']=songShift('${key}')+1`);
    assert.notEqual(await run(`loadSongBuffer('${key}',pianoContext)`),buffer,'key change regenerates audio');
  }
  assert.equal(fetches,0);
  console.log('PASS: four categories, filtered wrapping, pending CNY entries, six score melodies, both practice lengths complete with accurate singing, synthesized pitches, lead-ins and key-aware audio caching.');
})().catch(error=>{console.error(error);process.exitCode=1});
