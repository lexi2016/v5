import test from 'node:test';
import assert from 'node:assert/strict';
import {existsSync,readFileSync} from 'node:fs';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
const apiUrl=new URL('../src/api/closeRecapture.ts',import.meta.url);
const generated=spawnSync(process.env.PYTHON||'python',['-I','-B',fileURLToPath(new URL('./export_m17_fixture.py',import.meta.url))],{encoding:'utf8'});
const fixture=generated.status===0?JSON.parse(generated.stdout):null;
const response=(value,status=200)=>new Response(JSON.stringify(value),{status});
const query=value=>({source_trade_date:value.source_trade_date,run_id:value.run_id});
test('M17 fixtures come from original synthetic owner and exact cold reader',()=>{
 assert.equal(generated.status,0,generated.stderr);
 assert.equal(fixture.ready.rows.length,100);assert.equal(fixture.partial.rows.length,2);
 assert.equal(fixture.ready.execution_kind,'SIMULATED');assert.equal(fixture.partial.status,'PARTIAL');
});
test('M17 has an independent exact-run client',()=>assert.ok(existsSync(apiUrl),'missing M17 close-recapture client'));
test('M17 panel is mounted separately and source proxy preserves the legacy 1530 client',()=>{
 const panelUrl=new URL('../src/components/CloseRecapture.vue',import.meta.url);
 assert.ok(existsSync(panelUrl),'missing M17 panel');
 const source=readFileSync(new URL('../src/components/SourceBundleStatus.vue',import.meta.url),'utf8');
 assert.match(source,/import CloseRecapture from '\.\/CloseRecapture.vue'/);assert.match(source,/<CloseRecapture\s*\/>/);
 const vite=readFileSync(new URL('../vite.config.ts',import.meta.url),'utf8');
 assert.match(vite,/proxy\['\/api\/v5\/manager\/close-recapture'\] = readonlyProxy\(sourceTarget\)/);
 const old=readFileSync(new URL('../src/api/managerWorkbenchResearch.ts',import.meta.url),'utf8');
 assert.match(old,/\/api\/v4\/manager\/workbench-research/);assert.doesNotMatch(old,/close-recapture/);
});
const api=existsSync(apiUrl)?await import(apiUrl.href):null;
if(api&&fixture){
 const {readCloseRecapture,CloseRecaptureSession,DEFAULT_CLOSE_RECAPTURE_QUERY}=api;
 test('exact GET keeps original READY/PARTIAL rows and money units unchanged',async()=>{
  for(const original of Object.values(fixture)){
   let seen;const value=await readCloseRecapture(query(original),async(url,init)=>{seen={url,init};return response(original);});
   assert.deepEqual(value,original);const url=new URL(seen.url,'http://local');
   assert.equal(url.pathname,'/api/v5/manager/close-recapture');assert.deepEqual(Object.fromEntries(url.searchParams),query(original));
   assert.equal(seen.init.method,'GET');assert.equal(seen.init.credentials,'omit');assert.equal(seen.init.cache,'no-store');
   assert.equal(value.rows[0].turnover,1000);assert.equal(value.rows[0].turnover_unit,'UNKNOWN');
   assert.ok(value.cannot_confirm.includes('PYTDX_TURNOVER_CURRENCY_UNIT_UNVERIFIED'));
  }
  assert.deepEqual(DEFAULT_CLOSE_RECAPTURE_QUERY,{source_trade_date:'20261012',run_id:'ca2c344b61334ad28f4b6146117643cd'});
 });
 test('invalid or extra query values never request a guessed date/run',async()=>{
  for(const invalid of [{},{...query(fixture.ready),source_trade_date:'20260230'},{...query(fixture.ready),run_id:'latest'},{...query(fixture.ready),run_id:123},{...query(fixture.ready),limit:'100'},{...query(fixture.ready),source_trade_date:['20260928']}]){
   let calls=0;await assert.rejects(()=>readCloseRecapture(invalid,async()=>{calls++;return response(fixture.ready);}),/M17_QUERY/);assert.equal(calls,0);
  }
 });
 test('wrong schema, exact identity, boundary, counts and malformed original rows are rejected',async()=>{
  const mutations=[x=>x.schema_version='v5.m18.v1',x=>x.source_trade_date='20261012',x=>x.run_id='f'.repeat(32),x=>x.plan_trade_date=x.source_trade_date,x=>x.identity.target_date='20261012',x=>x.identity.input_sha256='bad',x=>x.identity.lane='manager_plan',x=>x.execution_label='NATURAL',x=>x.operation='NEW_CAPTURE',x=>x.execution_kind='UNVERIFIED',x=>x.RESEARCH_ONLY='true',x=>x.natural_verified=true,x=>x.formal_eligibility_verified=true,x=>x.production_allowed=true,x=>x.buy_gate_updated=true,x=>x.orders_sent=true,x=>x.received_not_historical_1530=false,x=>x.candidate_count=0,x=>x.rows=[],x=>x.rows[1]=x.rows[0],x=>x.rows[0].source_trade_date='20261012',x=>x.rows[0].symbol='bad',x=>x.rows[0].candidate_status='BUY',x=>x.rows[0].turnover_unit='HKD',x=>x.rows[0].observed_at='bad',x=>x.rows[0].available_at='2000-01-01T00:00:00Z',x=>delete x.rows[0].last_price,x=>x.rows[0].turnover={},x=>x.coverage.observed_count=1,x=>x.coverage.ratio=0,x=>x.pool.trade_date='20261012',x=>x.pool.artifact_sha256='bad',x=>x.bar_window.stage_id='STAGE_1530',x=>x.source.provider='guessed',x=>x.cannot_confirm=[],x=>x.files.receipt.sha256='bad',x=>x.files.snapshot.artifact_ref='/private/file',x=>x.status='READY_EMPTY'];
  for(const mutate of mutations){const value=structuredClone(fixture.ready);mutate(value);await assert.rejects(()=>readCloseRecapture(query(fixture.ready),async()=>response(value)),/M17_/);}
 });
 test('impossible calendar timestamps and hour 24 are rejected instead of normalized',async()=>{
  for(const mutate of [x=>x.identity.research_cutoff='2026-02-30T00:00:00+08:00',x=>x.rows[0].available_at='2026-09-28T24:00:00+08:00']){const value=structuredClone(fixture.ready);mutate(value);await assert.rejects(()=>readCloseRecapture(query(fixture.ready),async()=>response(value)),/M17_/);}
 });
 test('HTTP, missing body, malformed UTF-8/JSON and both byte-limit paths fail closed',async()=>{
  const max=256*1024;
  for(const r of [response({},409),response({},503),new Response(null),new Response('bad'),new Response(new Uint8Array([255])),new Response('{}',{headers:{'content-length':String(max+1)}}),new Response('{}',{headers:{'content-length':'bad'}}),new Response(' '.repeat(max+1))])
   await assert.rejects(()=>readCloseRecapture(query(fixture.ready),async()=>r),/M17_/);
  const raw=JSON.stringify(fixture.ready);const padded=raw+' '.repeat(max-new TextEncoder().encode(raw).length);
  assert.deepEqual(await readCloseRecapture(query(fixture.ready),async()=>new Response(padded)),fixture.ready);
  let cancelled=false;const stream=new ReadableStream({start(c){c.enqueue(new Uint8Array(max));c.enqueue(new Uint8Array(1));},cancel(){cancelled=true;}});
  await assert.rejects(()=>readCloseRecapture(query(fixture.ready),async()=>new Response(stream)),/M17_RESPONSE_LIMIT/);assert.equal(cancelled,true);
 });
 test('repeat clicks clear old success and earlier responses cannot overwrite a later run',async()=>{
  const states=[];let resolveOld,oldSignal,calls=0;
  const session=new CloseRecaptureSession(x=>states.push(x),async(_url,init)=>{calls++;if(calls===1)return response(fixture.ready);if(calls===2){oldSignal=init.signal;return new Promise(r=>resolveOld=r);}return response(fixture.partial);});
  await session.load(query(fixture.ready));assert.equal(states.at(-1).phase,'LOADED');
  const stale=session.load(query(fixture.ready));assert.equal(states.at(-1).result,null);
  await session.load(query(fixture.partial));assert.equal(oldSignal.aborted,true);assert.deepEqual(states.at(-1).result,fixture.partial);
  const count=states.length;resolveOld(response(fixture.ready));await stale;assert.equal(states.length,count);session.close();
 });
 test('reload failure and malformed response never retain success or become empty success',async()=>{
  for(const next of [async()=>{throw new Error('offline');},async()=>response({}),async()=>response({},503)]){
   const states=[];let calls=0;const session=new CloseRecaptureSession(x=>states.push(x),async()=>++calls===1?response(fixture.ready):next());
   await session.load(query(fixture.ready));await session.load(query(fixture.ready));assert.equal(states.at(-2).result,null);assert.equal(states.at(-1).phase,'CANNOT_CONFIRM');assert.equal(states.at(-1).result,null);session.close();
  }
 });
 test('query snapshot is immutable across a pending load and close cancels without emission',async()=>{
  const states=[];let resolveRead,signal,calls=0;const input=query(fixture.ready);
  const session=new CloseRecaptureSession(x=>states.push(x),async(_u,init)=>{calls++;signal=init.signal;return new Promise(r=>resolveRead=r);});
  const pending=session.load(input);input.run_id='f'.repeat(32);resolveRead(response(fixture.ready));await pending;assert.equal(states.at(-1).phase,'LOADED');
  const closed=session.load(query(fixture.ready));const count=states.length;session.close();assert.equal(signal.aborted,true);resolveRead(response(fixture.ready));await closed;assert.equal(states.length,count);await session.load(query(fixture.ready));assert.equal(calls,2);
 });
}
