import test from 'node:test';
import assert from 'node:assert/strict';
import {existsSync,readFileSync} from 'node:fs';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
const apiUrl=new URL('../src/api/hkCloseReview.ts',import.meta.url);
const flags={research_only:true,production_allowed:false,buy_gate_updated:false,orders_sent:false,natural_verified:false,formal_eligibility_verified:false};
const response=(v,status=200)=>new Response(JSON.stringify(v),{status});
const missing=()=>({status:'NOT_CONFIGURED',module_id:'M10_HK_CLOSE_REVIEW',reason_codes:['M10_REFERENCE_NOT_CONFIGURED'],...flags});
// Actual byte-identical original Store + cold projection over explicit synthetic inputs.
const root=fileURLToPath(new URL('../../',import.meta.url));
const generated=spawnSync(process.env.PYTHON||'python',['-I','-S','-B','V5/tests/export_m10_readonly_fixture.py'],{cwd:root,encoding:'utf8'});
const fixture=generated.status===0?JSON.parse(generated.stdout):null;
const sample=()=>structuredClone(fixture);
test('M10 frozen original synthetic projection is available',()=>assert.equal(generated.status,0,generated.stderr));
test('M10 saved review frontend client exists',()=>assert.ok(existsSync(apiUrl),'M10 saved review client is required'));
const api=existsSync(apiUrl)?await import(apiUrl.href):null;
if(api&&fixture){
 const {readHkCloseReview,HkCloseReviewSession}=api;
 test('GET preserves real original projection shape and all20/100/70 rows without scalar conversion',async()=>{
  let seen;const expected=sample();const result=await readHkCloseReview(async(url,init)=>{seen={url,init};return response(expected);});
  assert.deepEqual(result,expected);assert.deepEqual(['close_top20','model_rows','stage_rows'].map(k=>result.review[k].length),[20,100,70]);
  assert.equal(seen.url,'/api/v5/source-bundle/hk-close-review');assert.equal(seen.init.method,'GET');assert.equal(seen.init.cache,'no-store');assert.equal(seen.init.credentials,'omit');
  assert.equal(result.status,'PARTIAL');assert.equal(result.review.source_status,'MODEL_REVIEW_READY');
  assert.ok(Object.values(result.review.stages).every(x=>x.source_status==='PARTIAL_WITH_ROWS'&&x.hit_count===null));
  assert.ok(result.review.top20_attribution.every(x=>x.stage_union_hit===null&&x.classification==='CANNOT_CONFIRM'));
 });
 test('wrong identity, date, unsafe outer flags and promoted partial metrics fail closed',async()=>{
  for(const mutate of [x=>x.run_id='latest',x=>x.generation='bad',x=>x.native_review_sha256='bad',x=>x.review.trade_date='20261013',x=>x.identity.trade_date='20261013',x=>x.status='READY',x=>x.data_kind='NATURAL',x=>x.natural_admission='VERIFIED',x=>x.natural_verified=true,x=>x.orders_sent=true,x=>x.review.production_allowed=true,x=>x.review.stages.STAGE_0925.hit_count=0,x=>x.review.stage_union.precision=0,x=>x.review.top20_attribution[0].stage_union_hit=false,x=>x.review.top20_attribution[0].classification='missed',x=>delete x.review.stages.STAGE_0925,x=>x.review.row_counts.model_0_2=99,x=>x.review.model_rows[0].trade_date='20261013']){
   const value=sample();mutate(value);await assert.rejects(()=>readHkCloseReview(async()=>response(value)),/M10_/);
  }
 });
 test('NOT_CONFIGURED differs from empty rows and never carries stale review',async()=>{
  assert.deepEqual(await readHkCloseReview(async()=>response(missing())),missing());
  const states=[];await new HkCloseReviewSession(x=>states.push(x),async()=>response(missing())).load();
  assert.equal(states.at(-1).phase,'NOT_CONFIGURED');assert.equal(states.at(-1).result,null);
  const bad=missing();bad.review=sample().review;await assert.rejects(()=>readHkCloseReview(async()=>response(bad)),/M10_/);
 });
 test('HTTP error, invalid JSON, absent or oversized data is unconfirmed',async()=>{
  for(const value of [response({},409),response({},503),new Response('bad json'),new Response(null),new Response('{}',{headers:{'content-length':String(16*1024*1024+1)}}),new Response(' '.repeat(16*1024*1024+1))])await assert.rejects(()=>readHkCloseReview(async()=>value),/M10_/);
 });
 test('refresh clears previous rows immediately and failed read leaves no stale result',async()=>{
  let resolve,n=0;const states=[];const session=new HkCloseReviewSession(x=>states.push(x),async()=>++n===1?response(sample()):await new Promise(r=>resolve=r));
  await session.load();const task=session.load();assert.equal(states.at(-1).phase,'LOADING');assert.equal(states.at(-1).result,null);
  resolve(response({},503));await task;assert.equal(states.at(-1).phase,'CANNOT_CONFIRM');assert.equal(states.at(-1).result,null);
 });
 test('late success cannot replace newer missing configuration and Close aborts',async()=>{
  let resolve,n=0;const states=[],signals=[];const session=new HkCloseReviewSession(x=>states.push(x),async(_url,init)=>{signals.push(init.signal);return ++n===1?await new Promise(r=>resolve=r):response(missing());});
  const older=session.load();await session.load();assert.equal(signals[0].aborted,true);const count=states.length;resolve(response(sample()));await older;
  assert.equal(states.length,count);assert.equal(states.at(-1).phase,'NOT_CONFIGURED');session.close();await session.load();assert.equal(n,2);
 });
 test('close ignores completion and prevents new reads',async()=>{
  let resolve,signal,calls=0;const states=[];const session=new HkCloseReviewSession(x=>states.push(x),async(_url,init)=>{calls++;signal=init.signal;return await new Promise(r=>resolve=r);});
  const task=session.load();session.close();const count=states.length;resolve(response(sample()));await task;await session.load();assert.equal(states.length,count);assert.equal(calls,1);assert.equal(signal.aborted,true);
 });
}
test('M10 panel stays in existing source page, distinguishes partial and renders original arrays',()=>{
 const url=new URL('../src/components/HkCloseReview.vue',import.meta.url);assert.ok(existsSync(url),'M10 panel is required');
 const panel=readFileSync(url,'utf8'),host=readFileSync(new URL('../src/components/SourceBundleStatus.vue',import.meta.url),'utf8'),proxy=readFileSync(new URL('../vite.config.ts',import.meta.url),'utf8');
 for(const key of ['close_top20','model_rows','stage_rows','top20_attribution','generation','native_review_sha256','PARTIAL','NOT_CONFIGURED','PIT','natural_verified=false','formal_eligibility_verified=false'])assert.ok(panel.includes(key),key);
 assert.match(panel,/v-for="\(row, index\) in state\.result\.review\[section\.key\]"/);
 assert.match(host,/<HkCloseReview\s*\/>/);assert.match(proxy,/\/api\/v5\/source-bundle\/hk-close-review/);
 assert.doesNotMatch(panel,/v-html|\.sort\(|\.toSorted\(|method:\s*['"]POST/);
});
