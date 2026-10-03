// Loads the actual single-file game with a minimal DOM; no microphone is mocked
// unless a test explicitly supplies PCM or capture devices.
// mode: the saved Full song / Quick play choice. Reference tests default to 'quick' (Twinkle's
// approved 42-note verse); tests/catalogue.cjs exercises both modes explicitly.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
function gameHarness({mode='quick'}={}){
 const html=fs.readFileSync(path.resolve(__dirname,'../index.html'),'utf8');
 const noop=()=>{},elements=new Map(),handlers={},saved=new Map();
 const element=id=>{if(!elements.has(id))elements.set(id,{style:{},dataset:{},classList:{add:noop,remove:noop,toggle:noop},addEventListener:noop,querySelectorAll:()=>[],getContext:()=>new Proxy({},{get:()=>noop}),getBoundingClientRect:()=>({width:390,height:844}),textContent:'',innerHTML:''});return elements.get(id)};
 element('twinkle-chart').textContent=html.match(/<script id="twinkle-chart" type="application\/json">([\s\S]*?)<\/script>/)[1];
 const sandbox=vm.createContext({console,Math,Date,Float32Array,Float64Array,Uint8Array,Promise,performance:require('node:perf_hooks').performance,
 setTimeout:noop,clearTimeout:noop,setInterval:noop,clearInterval:noop,requestAnimationFrame:()=>1,cancelAnimationFrame:noop,
 localStorage:{getItem:k=>saved.has(k)?saved.get(k):k==='oohwoo_play_mode_v1'?mode:null,setItem:(k,v)=>saved.set(k,String(v))},navigator:{userAgent:'iPhone test'},window:{innerWidth:390,innerHeight:844,addEventListener:noop},
 document:{getElementById:element,querySelectorAll:()=>[],addEventListener:(event,fn)=>(handlers[event]||=[]).push(fn)}});
 vm.runInContext(html.match(/<script>([\s\S]*?)<\/script>/)[1],sandbox);
 return {sandbox,run:code=>vm.runInContext(code,sandbox),element,html,handlers,saved};
}
module.exports={gameHarness};
