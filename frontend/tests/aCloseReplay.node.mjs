import test from 'node:test';
import assert from 'node:assert/strict';
import {existsSync,readFileSync} from 'node:fs';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
const apiUrl=new URL('../src/api/aCloseReplay.ts',import.meta.url);
const flags={research_only:true,production_allowed:false,buy_gate_updated:false,orders_sent:false,natural_verified:false,formal_eligibility_verified:false,strict_1500_pit_verified:false,source_time_verified:false,membership_qualification_verified:false};
const response=(v,status=200)=>new Response(JSON.stringify(v),{status});
const missing=()=>({status:'NOT_CONFIGURED',module_id:'M09_A_CLOSE_REPLAY',reason_codes:['M09_REFERENCE_NOT_CONFIGURED'],...flags});
const root=fileURLToPath(new URL('../../',import.meta.url));
// This fixture deliberately carries None text values. Preserve the frozen
// owner's legacy string inference in its producer and independent cold reader.
// Scope the compatibility setting to this synthetic Python process tree only.
const generated=spawnSync(process.env.PYTHON||'python',['-I','-B','V5/tests/export_m09_readonly_fixture.py'],{cwd:root,encoding:'utf8',env:{...process.env,PANDAS_FUTURE_INFER_STRING:'0'}});
const fixture=generated.status===0?JSON.parse(generated.stdout):null;
const sample=()=>structuredClone(fixture);
test('M09 fixture comes from original synthetic producer/store/cold reader',()=>assert.equal(generated.status,0,generated.stderr));
test('M09 independent replay client exists',()=>assert.ok(existsSync(apiUrl),'M09 exact replay client is required'));
const api=existsSync(apiUrl)?await import(apiUrl.href):null;
if(api&&fixture){
 const {readACloseReplay,ACloseReplaySession}=api;
 test('fixed GET preserves original review, actual historical date, gaps and identity',async()=>{
  let seen;const expected=sample();const result=await readACloseReplay(async(url,init)=>{seen={url,init};return response(expected);});
  assert.deepEqual(result,expected);assert.equal(seen.url,'/api/v5/source-bundle/a-close-replay');
  assert.equal(seen.init.method,'GET');assert.equal(seen.init.cache,'no-store');assert.equal(seen.init.credentials,'omit');
  assert.equal(result.trade_date,'20261009');assert.equal(result.status,'PARTIAL');
  assert.equal(result.publication.historical_research.snapshot_row_count,6);
 });
 test('identity, date, research flags, classification and promotion tamper fail closed',async()=>{
  for(const mutate of [x=>x.run_id='latest',x=>x.generation='bad',x=>x.trade_date='20261012',x=>x.review.trade_date='20261012',
   x=>x.review.model_review.run_id='other',x=>x.publication.generation_sha256='0'.repeat(64),x=>x.identity.record_sha256='bad',
   x=>x.status='READY',x=>x.execution_kind='DAILY_RESEARCH',x=>x.data_kind='REAL',x=>x.scope='FULL_MARKET',x=>x.natural_verified='false',
   x=>x.orders_sent=true,x=>x.review.production_allowed=true,x=>x.publication.read_status='CANNOT_CONFIRM',
   x=>x.publication.historical_research.source_time_verified=true,x=>x.publication.historical_research.membership_qualification_verified=true,
   x=>x.publication.historical_research.snapshot_row_count=-1,x=>x.review.big_picture[0].trade_date='20261013',
   x=>x.publication.business_status='READY',x=>x.publication.scenario_probabilities_status='CALIBRATED',
   x=>x.review.model_review.model_promotion='PROMOTED',x=>x.publication.natural_verified=true]){
   const value=sample();mutate(value);await assert.rejects(()=>readACloseReplay(async()=>response(value)),/M09_/);
  }
 });
 test('NOT_CONFIGURED never masquerades as empty saved result',async()=>{
  assert.deepEqual(await readACloseReplay(async()=>response(missing())),missing());
  const bad=missing();bad.review=sample().review;await assert.rejects(()=>readACloseReplay(async()=>response(bad)),/M09_/);
 });
 test('invalid, disconnected, oversized and empty responses fail closed',async()=>{
  for(const v of [response({},409),response({},503),new Response('bad json'),new Response(null),
   new Response('{}',{headers:{'content-length':String(16*1024*1024+1)}}),new Response(' '.repeat(16*1024*1024+1))])
   await assert.rejects(()=>readACloseReplay(async()=>v),/M09_/);
 });
 test('refresh clears all previous data immediately and rejection keeps it cleared',async()=>{
  let resolve,n=0;const states=[];const session=new ACloseReplaySession(x=>states.push(x),async()=>++n===1?response(sample()):await new Promise(r=>resolve=r));
  await session.load();const task=session.load();assert.equal(states.at(-1).phase,'LOADING');assert.equal(states.at(-1).result,null);
  resolve(response({},503));await task;assert.equal(states.at(-1).phase,'CANNOT_CONFIRM');assert.equal(states.at(-1).result,null);
 });
 test('late response cannot override newer missing reference and Close cancels',async()=>{
  let resolve,n=0;const states=[],signals=[];const session=new ACloseReplaySession(x=>states.push(x),async(_url,init)=>{signals.push(init.signal);return ++n===1?await new Promise(r=>resolve=r):response(missing());});
  const older=session.load();await session.load();assert.equal(signals[0].aborted,true);const count=states.length;resolve(response(sample()));await older;
  assert.equal(states.length,count);assert.equal(states.at(-1).phase,'NOT_CONFIGURED');session.close();await session.load();assert.equal(n,2);
 });
 test('separate M09 sessions and modules never share abort state',async()=>{
  let finish,firstSignal;const a=[],b=[];const one=new ACloseReplaySession(x=>a.push(x),async(_url,init)=>{firstSignal=init.signal;return await new Promise(r=>finish=r);});
  const two=new ACloseReplaySession(x=>b.push(x),async()=>response(missing()));const pending=one.load();await two.load();two.close();
  assert.equal(firstSignal.aborted,false);finish(response(sample()));await pending;assert.equal(a.at(-1).phase,'LOADED');one.close();
 });
}
test('separate panel mounted alongside existing M06/M10, without replacing source cards',()=>{
 const url=new URL('../src/components/ACloseReplay.vue',import.meta.url);assert.ok(existsSync(url),'M09 component is required');
 const panel=readFileSync(url,'utf8'),host=readFileSync(new URL('../src/components/SourceBundleStatus.vue',import.meta.url),'utf8');
 for(const key of ['HISTORICAL_REPLAY','PARTIAL','OBSERVED_ROWS_ONLY','NOT_CONFIGURED','strict_1500_pit_verified=false','generation','trade_date','historical_research'])assert.ok(panel.includes(key),key);
 for(const name of ['HkPreselectionPool','HkCloseReview','ACloseReplay'])assert.match(host,new RegExp('<'+name+'\\s*/>'));
 assert.match(host,/v-for="row in state.result.modules"/);
 assert.doesNotMatch(panel,/v-html|\.sort\(|\.toSorted\(|20261009|20261012|20261013/);
 assert.match(readFileSync(new URL('../vite.config.ts',import.meta.url),'utf8'),/\/api\/v5\/source-bundle\/a-close-replay/);
});
