// Keep screen awake: held only on the gameplay screen, dropped on leaving, re-asked after the page was hidden.
const assert=require('node:assert');
const {gameHarness}=require('./game-harness.cjs');
(async()=>{
 // No wake lock support (older phones): nothing breaks.
 { const g=gameHarness(); g.run(`showScreen('game');showScreen('main')`); }
 const g=gameHarness(); const log=[]; let onRelease=null;
 g.sandbox.navigator.wakeLock={request:kind=>{log.push('request '+kind);
  return Promise.resolve({addEventListener:(e,fn)=>{onRelease=fn;},release:()=>{log.push('release');return Promise.resolve();}});}};
 const tick=()=>new Promise(r=>setImmediate(r));
 g.run(`showScreen('select')`); await tick();
 assert.deepStrictEqual(log,[],'not held on menus');
 g.run(`showScreen('game')`); g.run(`showScreen('game')`); await tick();
 assert.deepStrictEqual(log,['request screen'],'one request when a song starts');
 // Phone locked / app switched: the browser releases it; coming back asks again.
 g.sandbox.document.visibilityState='hidden'; onRelease(); g.handlers.visibilitychange.forEach(fn=>fn());
 g.sandbox.document.visibilityState='visible'; g.handlers.visibilitychange.forEach(fn=>fn()); await tick();
 assert.deepStrictEqual(log,['request screen','request screen']);
 g.run(`showScreen('complete')`); await tick();
 assert.deepStrictEqual(log,['request screen','request screen','release'],'released after the song');
 // Leaving while the request is still pending must not leave the screen locked on.
 g.run(`showScreen('game');showScreen('select')`); await tick();
 assert.strictEqual(log.at(-1),'release');
 // A refusal (e.g. battery saver) is logged, not thrown.
 g.sandbox.navigator.wakeLock.request=()=>Promise.reject(new Error('battery saver'));
 g.run(`showScreen('game')`); await tick();
 console.log('screen-awake: OK');
})().catch(e=>{console.error(e);process.exit(1);});
