const {gameHarness}=require('../../tests/game-harness.cjs');
const {run}=gameHarness();
const out={};
for(const key of Array.from(run('Object.keys(SONG_DATA)'))){
  out[key]=JSON.parse(run(`JSON.stringify({audio:SONG_DATA['${key}'].audio,intro:SONG_DATA['${key}'].introOffset,status:SONG_DATA['${key}'].chartStatus,notes:buildPipes(SONG_DATA['${key}'].notes,SONG_DATA['${key}'].introOffset).map(n=>({t:n.t,end:n.end,midi:n.midi,lyric:n.lyric}))})`));
}
require('fs').writeFileSync(process.argv[2],JSON.stringify(out));
console.log(Object.entries(out).map(([k,v])=>k+' '+v.status+' '+v.notes.length+' first '+v.notes[0].t.toFixed(2)+' midi '+v.notes[0].midi).join('\n'));
