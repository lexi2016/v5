import test from 'node:test';import assert from 'node:assert/strict';
import {existsSync} from 'node:fs';import {spawnSync} from 'node:child_process';import {fileURLToPath} from 'node:url';
const apiUrl=new URL('../src/api/hkStageObserved.ts',import.meta.url),root=fileURLToPath(new URL('../../',import.meta.url));
const generated=spawnSync(process.env.PYTHON||'python',['-I','-B','V5/tests/export_m08_readonly_fixture.py'],{cwd:root,encoding:'utf8'});
const fixture=generated.status===0?JSON.parse(generated.stdout):null,response=(v,status=200)=>new Response(JSON.stringify(v),{status});
const missing=()=>({status:'NOT_CONFIGURED',module_id:'M08_HK_STAGE_OBSERVED',reason_codes:['M08_REFERENCES_NOT_CONFIGURED'],research_only:true,production_allowed:false,buy_gate_updated:false,orders_sent:false,natural_verified:false,pit_verified:false,formal_admission:false,raw_input_verified:false,computation_replayed:false,market_data_authenticity_verified:false});
test('M08 fixture uses frozen original owner/store and observed cold reader',()=>assert.equal(generated.status,0,generated.stderr));
test('M08 independent observed client exists',()=>assert.ok(existsSync(apiUrl)));
const api=existsSync(apiUrl)?await import(apiUrl.href):null;
if(api&&fixture){
 const {readHkStageObserved,HkStageObservedSession}=api;
 test('catalog retains ten refs/eight stages and exact GET retains all rows/fields',async()=>{
  assert.deepEqual(await readHkStageObserved(null,async()=>response(fixture.catalog)),fixture.catalog);
  for(const expected of fixture.results){let seen;const got=await readHkStageObserved(expected.reference,async(url,init)=>{seen={url,init};return response(expected);});assert.deepEqual(got,expected);assert.equal(got.artifact.rows.length,10);assert.equal(seen.init.method,'GET');assert.equal(seen.init.cache,'no-store');assert.equal(seen.init.credentials,'omit');assert.equal(new URL(seen.url,'http://local').searchParams.get('run_id'),expected.reference.run_id);}
 });
 test('status, reference, safety, capture and Stage8 tamper are rejected',async()=>{
  for(const mutate of [x=>x.reference.run_id='other',x=>x.artifact.run_id='other',x=>x.artifact.trade_date='20261012',x=>x.status='READY_EMPTY',x=>x.natural_verified=true,x=>x.provenance.pit_verified='false',x=>x.provenance.captured_at='2026-10-08T00:00:00Z',x=>x.data_kind='REAL',x=>x.stage_group='HK_STAGE8_SEPARATE',x=>x.m10_stage_member=false,x=>x.artifact.orders_sent=true,x=>x.artifact.rows.pop(),x=>x.provenance.original_reference.artifact_sha256='bad']){const value=structuredClone(fixture.results[0]);mutate(value);await assert.rejects(()=>readHkStageObserved(fixture.results[0].reference,async()=>response(value)),/M08_/);}
 });
 test('catalog rejects dropped or duplicated references',async()=>{for(const mutate of [x=>x.references.pop(),x=>x.references[1]=x.references[0],x=>x.references_verified=true]){const value=structuredClone(fixture.catalog);mutate(value);await assert.rejects(()=>readHkStageObserved(null,async()=>response(value)),/M08_/);}});
 test('unconfigured is distinct; disconnected/invalid/oversized clear data',async()=>{
  assert.deepEqual(await readHkStageObserved(null,async()=>response(missing())),missing());
  for(const r of [response({},409),response({},503),new Response('bad'),new Response(null),new Response('{}',{headers:{'content-length':String(16*1024*1024+1)}})])await assert.rejects(()=>readHkStageObserved(null,async()=>r),/M08_/);
 });
 test('stage/run switch clears old data and stale completion cannot win',async()=>{
  let pending;const states=[];let n=0;const session=new HkStageObservedSession(x=>states.push(x),async()=>++n===1?response(fixture.catalog):n===2?response(fixture.results[0]):n===3?await new Promise(r=>pending=r):response(fixture.results[1]));
  await session.load();assert.equal(states.at(-1).phase,'LOADED');const stale=session.select(fixture.catalog.references[2]);assert.equal(states.at(-1).result,null);await session.select(fixture.catalog.references[1]);const count=states.length;pending(response(fixture.results[2]));await stale;assert.equal(states.length,count);assert.deepEqual(states.at(-1).result,fixture.results[1]);session.close();await session.load();assert.equal(n,4);
 });
 test('reload disconnect clears old catalog and result; sessions have independent aborts',async()=>{
  let n=0;const states=[];const s=new HkStageObservedSession(x=>states.push(x),async()=>++n===1?response(fixture.catalog):n===2?response(fixture.results[0]):Promise.reject(new Error('offline')));await s.load();await s.load();assert.equal(states.at(-1).phase,'CANNOT_CONFIRM');assert.equal(states.at(-1).result,null);assert.deepEqual(states.at(-1).references,[]);
  let done,signal;const a=new HkStageObservedSession(()=>{},async(_u,i)=>{signal=i.signal;return await new Promise(r=>done=r)}),b=new HkStageObservedSession(()=>{},async()=>response(missing()));const p=a.load();await b.load();b.close();assert.equal(signal.aborted,false);done(response(missing()));await p;a.close();s.close();
 });
}
