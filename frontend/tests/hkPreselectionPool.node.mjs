import test from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';

const apiUrl = new URL('../src/api/hkPreselectionPool.ts', import.meta.url);
const flags = { research_only:true, natural_verified:false, formal_eligibility_verified:false, production_allowed:false, buy_gate_updated:false, orders_sent:false };
const tradingFlags = { production_allowed:false, buy_gate_updated:false, orders_sent:false };
const digest = character => character.repeat(64);
const response = (value, status=200) => new Response(JSON.stringify(value), { status, headers:{'content-type':'application/json'} });
const sample = () => {
 const target='20261013', signal='20261012', computation=digest('a');
 const source={role:'HK_CONNECT_D1_TOP100_0_2',run_id:'SYNTHETIC_HK02_RUN',artifact_sha256:digest('b'),manifest_sha256:digest('c'),receipt_sha256:digest('d'),artifact_relative:`runs/${target}/HK_CONNECT_D1_TOP100_0_2/SYNTHETIC_HK02_RUN/artifact.csv`};
 const prefix=`hk_preselection/${target}/objects/${computation}`;
 const rows=Array.from({length:100},(_,index)=>{
  const rank=index+1,code=String(101-rank).padStart(5,'0'),score=(1-rank/1000).toFixed(3);
  return {rank:String(rank),code_norm:`HK.${code}`,name:`SYNTHETIC_${code}`,score_prob_active:score,trade_date:target,signal_date:signal,target_date:target,selected_strategy:'prob_active',d1_freshness_status:'PASS',symbol:`HK.${code}`,market:'HK',pool_id:'hkconnect_d1_top100',pool_rank:rank,stock_name:`SYNTHETIC_${code}`,pool_score:Number(score),recommendation_status:'WATCH_ONLY',empty_original:'',original_zero:'0',...tradingFlags};
 });
 return {
  artifact:{schema_version:'v3_5.preselection_pool.v1',trade_date:target,pool_id:'hkconnect_d1_top100',display_name:'港股通 0.2 D-1 Top100',market:'HK',status:'STRICT_0_2_READY',producer_id:'v3_shared_hk_0_2_consumer_v1',source_role:'SHARED_VERIFIED_HK_0_2',source_path:source.artifact_relative,source_sha256:source.artifact_sha256,source_run_id:source.run_id,source_manifest_sha256:source.manifest_sha256,source_receipt_sha256:source.receipt_sha256,source_row_count:100,signal_date:signal,target_date:target,stage_selection_eligible:true,rows,cannot_confirm:['RESEARCH_ONLY_NOT_BUY_GATE'],...tradingFlags},
  committed_reference:{schema_version:'v5.hk_preselection_committed_reference.v1',owner:'M06',market:'HK',status:'COMMITTED',business_status:'STRICT_0_2_READY',data_kind:'VERIFIED_SOURCE_SNAPSHOT',target_date:target,signal_date:signal,eligibility_source_date:signal,research_cutoff:'2026-10-13T09:20:00+08:00',execution_mode:'MANUAL_RECOVERY',fixture_only:true,computation_sha256:computation,request_sha256:digest('e'),artifact_relative:`${prefix}/artifact.json`,artifact_sha256:digest('f'),manifest_relative:`${prefix}/manifest.json`,manifest_sha256:digest('1'),receipt_relative:`${prefix}/receipt.json`,receipt_sha256:digest('2'),computation_identity:{lane:'hk_preselection',target_date:target,input_sha256:digest('3'),research_cutoff:'2026-10-13T09:20:00+08:00',code_sha256:digest('4'),config_sha256:digest('5'),dependency_sha256:digest('6')},producer_computation_identity:null,producer_reference:{relative:`${prefix}/producer_receipt.json`,sha256:digest('7'),production_method:'EXISTING_VERIFIED_POOL'},reader_reference:{relative:`${prefix}/strict_reader_receipt.json`,sha256:digest('8')},verified_source_reference:source,model_weights_reverified:false,...flags},
  model_weights_reverified:false,fixture_only:true,...flags,
 };
};
const missing = () => ({status:'NOT_CONFIGURED',module_id:'M06_HK_PRESELECTION',reason_codes:['M06_REFERENCE_NOT_CONFIGURED'],model_weights_reverified:false,...flags});

test('M06 read-only frontend client exists', () => assert.ok(existsSync(apiUrl), 'M06 saved-pool frontend reader is required'));
const api = existsSync(apiUrl) ? await import(apiUrl.href) : null;
if (api) {
 const {HK_PRESELECTION_ROUTE,readHkPreselectionPool,HkPreselectionSession}=api;
 test('GET preserves all100 original rows, fields, dates, identities and source order',async()=>{
  const expected=sample(),controller=new AbortController();let seen;
  const result=await readHkPreselectionPool(async(url,init)=>{seen={url,init};return response(expected);},controller.signal);
  assert.deepEqual(result,expected);assert.equal(result.artifact.rows.length,100);
  assert.equal(result.artifact.rows[0].symbol,'HK.00100');assert.equal(result.artifact.rows[99].symbol,'HK.00001');
  assert.equal(result.artifact.rows[0].score_prob_active,'0.999');assert.equal(result.artifact.rows[0].empty_original,'');
  assert.equal(result.committed_reference.target_date,'20261013');assert.equal(result.committed_reference.signal_date,'20261012');assert.equal(result.committed_reference.eligibility_source_date,'20261012');
  assert.deepEqual(seen,{url:'/api/v5/source-bundle/hk-preselection',init:{method:'GET',cache:'no-store',credentials:'omit',signal:controller.signal}});
  assert.equal(HK_PRESELECTION_ROUTE,seen.url);
 });
 test('99 rows, duplicate symbols, wrong row identity and altered dates fail closed',async()=>{
  for(const mutate of [x=>x.artifact.rows.pop(),x=>x.artifact.rows[1].symbol=x.artifact.rows[0].symbol,x=>x.artifact.rows[0].market='A',x=>x.artifact.rows[0].pool_id='other',x=>x.artifact.rows[0].pool_rank=2,x=>x.artifact.rows[0].signal_date='20261009',x=>x.artifact.rows[0].target_date='20261014',x=>x.artifact.rows[0].code_norm='HK.00999',x=>x.artifact.rows[0].score_prob_active='NaN',x=>x.artifact.rows[0].pool_score=2,x=>x.artifact.rows[0].recommendation_status='BUY']){
   const value=sample();mutate(value);await assert.rejects(()=>readHkPreselectionPool(async()=>response(value)),/M06_/);
  }
 });
 test('unsafe claims are rejected at payload, reference, artifact and row boundaries',async()=>{
  for(const mutate of [x=>x.research_only=false,x=>x.model_weights_reverified=true,x=>x.natural_verified=true,x=>x.formal_eligibility_verified=true,x=>x.orders_sent=true,x=>x.committed_reference.production_allowed=true,x=>x.committed_reference.model_weights_reverified=true,x=>x.artifact.buy_gate_updated=true,x=>x.artifact.rows[0].production_allowed=true,x=>x.artifact.rows[0].formal_eligibility_verified=true,x=>x.artifact.natural_verified=true,x=>delete x.orders_sent]){
   const value=sample();mutate(value);await assert.rejects(()=>readHkPreselectionPool(async()=>response(value)),/M06_.*BOUNDARY/);
  }
 });
 test('wrong committed, source and computation identities cannot be displayed',async()=>{
  for(const mutate of [x=>x.committed_reference.owner='M05',x=>x.committed_reference.status='PREPARED',x=>x.committed_reference.artifact_sha256='bad',x=>x.committed_reference.fixture_only=false,x=>x.committed_reference.computation_identity.target_date='20261014',x=>x.committed_reference.artifact_relative='/private/artifact.json',x=>x.committed_reference.verified_source_reference.run_id='WRONG_RUN',x=>x.artifact.source_sha256=digest('0'),x=>x.artifact.source_manifest_sha256=digest('0'),x=>x.artifact.source_receipt_sha256=digest('0'),x=>x.artifact.source_path='other.csv',x=>x.artifact.target_date='20261014',x=>x.artifact.signal_date='20261009',x=>x.committed_reference.target_date='20260230',x=>x.committed_reference.eligibility_source_date='20261014']){
   const value=sample();mutate(value);await assert.rejects(()=>readHkPreselectionPool(async()=>response(value)),/M06_/);
  }
 });
 test('NOT_CONFIGURED is explicit and never represented as an empty successful pool',async()=>{
  assert.deepEqual(await readHkPreselectionPool(async()=>response(missing())),missing());
  const states=[];await new HkPreselectionSession(state=>states.push(state),async()=>response(missing())).load();
  assert.equal(states.at(-1).phase,'NOT_CONFIGURED');assert.equal(states.at(-1).result,null);assert.match(states.at(-1).error,/M06_REFERENCE_NOT_CONFIGURED/);
  for(const mutate of [x=>x.module_id='M05_A_PRESELECTION',x=>x.reason_codes=[],x=>x.model_weights_reverified=true,x=>x.artifact=sample().artifact]){
   const value=missing();mutate(value);await assert.rejects(()=>readHkPreselectionPool(async()=>response(value)),/M06_/);
  }
 });
 test('HTTP missing and corrupt results, invalid JSON, empty and oversized responses fail closed',async()=>{
  for(const value of [response({status:'CANNOT_CONFIRM',reason_codes:['MODULE_RESULT_INVALID']},409),response({},503),response({},404),new Response('not JSON'),new Response(null),new Response('{}',{headers:{'content-length':String(16*1024*1024+1)}}),new Response(' '.repeat(16*1024*1024+1))])await assert.rejects(()=>readHkPreselectionPool(async()=>value),/M06_/);
 });
 test('new reads immediately clear old rows and a failed read leaves no stale result',async()=>{
  let resolve,n=0;const states=[];const session=new HkPreselectionSession(state=>states.push(state),async()=>++n===1?response(sample()):await new Promise(r=>resolve=r));
  await session.load();assert.equal(states.at(-1).phase,'LOADED');const task=session.load();
  assert.equal(states.at(-1).phase,'LOADING');assert.equal(states.at(-1).result,null);
  resolve(response({},503));await task;assert.equal(states.at(-1).phase,'CANNOT_CONFIRM');assert.equal(states.at(-1).result,null);
 });
 test('late success cannot overwrite newer missing configuration and old request is aborted',async()=>{
  let resolve,n=0;const states=[],signals=[];const session=new HkPreselectionSession(state=>states.push(state),async(_url,init)=>{signals.push(init.signal);return ++n===1?await new Promise(r=>resolve=r):response(missing());});
  const old=session.load();await session.load();assert.equal(signals[0].aborted,true);const count=states.length;
  resolve(response(sample()));await old;assert.equal(states.length,count);assert.equal(states.at(-1).phase,'NOT_CONFIGURED');assert.equal(states.at(-1).result,null);
 });
 test('late failure cannot clear a newer valid result',async()=>{
  let reject,n=0;const states=[];const session=new HkPreselectionSession(state=>states.push(state),async()=>++n===1?await new Promise((_resolve,r)=>reject=r):response(sample()));
  const old=session.load();await session.load();const count=states.length;reject(new Error('old offline'));await old;
  assert.equal(states.length,count);assert.equal(states.at(-1).phase,'LOADED');
 });
 test('closing aborts pending read, ignores completion and prevents additional reads',async()=>{
  let resolve,calls=0,signal;const states=[];const session=new HkPreselectionSession(state=>states.push(state),async(_url,init)=>{calls++;signal=init.signal;return await new Promise(r=>resolve=r);});
  const task=session.load();session.close();assert.equal(signal.aborted,true);const count=states.length;resolve(response(sample()));await task;await session.load();
  assert.equal(states.length,count);assert.equal(calls,1);
 });
}

test('standalone panel renders original row fields and embeds only within source status',()=>{
 const panelUrl=new URL('../src/components/HkPreselectionPool.vue',import.meta.url);
 assert.ok(existsSync(panelUrl),'M06 read-only pool panel is required');
 const panel=readFileSync(panelUrl,'utf8'),host=readFileSync(new URL('../src/components/SourceBundleStatus.vue',import.meta.url),'utf8');
 assert.match(panel,/v-for="row in state\.result\.artifact\.rows"/);assert.match(panel,/row\[field\]/);
 assert.match(panel,/eligibility_source_date/);assert.match(panel,/model_weights_reverified=false/);assert.match(panel,/natural_verified=false/);assert.match(panel,/formal_eligibility_verified=false/);assert.match(panel,/PIT/);assert.match(panel,/NOT_CONFIGURED/);
 assert.match(host,/import HkPreselectionPool from/);assert.match(host,/<HkPreselectionPool\s*\/>/);
 assert.doesNotMatch(panel,/\.sort\(|\.toSorted\(|method:\s*['"]POST|v-html/);
});
