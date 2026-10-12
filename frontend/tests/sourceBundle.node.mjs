import test from 'node:test';
import assert from 'node:assert/strict';
import {SOURCE_ROUTE,SourceBundleSession,readSourceBundle} from '../src/api/sourceBundle.ts';
const flags={natural_verified:false,formal_eligibility_verified:false,production_allowed:false,buy_gate_updated:false,orders_sent:false};
const sample=()=>({schema_version:'v5.source_bundle.result.v1',status:'SOURCE_BUNDLE_ATTEMPTED',observed_at:'2026-10-12T15:00:00Z',request_sha256:'a'.repeat(64),data_kind:'RECORDED_INPUT_REPLAY',...flags,modules:['M01_A_MARKET','M02_HK_MARKET','M03_US_MARKET','M05_A_PRESELECTION'].map((module_id,i)=>({module_id,owner_entry:['m01_a_source','m02_hk_source','m03_us_source','m05_a_preselection'][i],status:i===2?'VALIDATED_SOURCE_BINDING':'BLOCKED_REQUEST_MISSING',...flags}))});
const response=value=>new Response(JSON.stringify(value),{headers:{'content-type':'application/json'}});
test('source panel reads only saved route and preserves owner states and historical replay',async()=>{
 const expected=sample();let seen;
 const value=await readSourceBundle(async(url,init)=>{seen={url,init};return response(expected);});
 assert.deepEqual(value,expected);assert.equal(seen.url,SOURCE_ROUTE);assert.equal(seen.init.method,'GET');assert.equal(seen.init.cache,'no-store');assert.equal(seen.init.credentials,'omit');
});
test('missing or duplicate modules, wrong owner, promoted flags and malformed identity fail closed',async()=>{
 for(const mutate of [x=>x.modules.pop(),x=>x.modules[1]=x.modules[0],x=>x.modules[2].owner_entry='us_mapping',x=>x.natural_verified=true,x=>x.modules[0].production_allowed=true,x=>x.request_sha256='bad',x=>x.data_kind='NATURAL']){
  const bad=sample();mutate(bad);await assert.rejects(()=>readSourceBundle(async()=>response(bad)),/SOURCE_/);
 }
});
test('HTTP errors, invalid JSON, absent and oversized streams stay unconfirmed',async()=>{
 for(const value of [new Response('{}',{status:404}),new Response('not JSON'),new Response(null),new Response('{}',{headers:{'content-length':String(16*1024*1024+1)}})])await assert.rejects(()=>readSourceBundle(async()=>value),/SOURCE_/);
});
test('failed re-read clears previously valid source result',async()=>{
 let fail=false;const states=[];const session=new SourceBundleSession(s=>states.push(s),async()=>{if(fail)throw new Error('offline');return response(sample());});
 await session.load();assert.equal(states.at(-1).phase,'LOADED');fail=true;await session.load();assert.equal(states.at(-1).phase,'CANNOT_CONFIRM');assert.equal(states.at(-1).result,null);
});
test('repeated reads do not let older completion replace new result',async()=>{
 let resolve;let n=0;const states=[];const session=new SourceBundleSession(s=>states.push(s),async()=>++n===1?await new Promise(r=>resolve=r):response(sample()));
 const old=session.load();await session.load();const count=states.length;resolve(response({...sample(),request_sha256:'b'.repeat(64)}));await old;assert.equal(states.length,count);assert.equal(states.at(-1).result.request_sha256,'a'.repeat(64));
});
test('closing a pending read ignores later completion',async()=>{
 let resolve;const states=[];const session=new SourceBundleSession(s=>states.push(s),async()=>await new Promise(r=>resolve=r));const task=session.load();session.close();const count=states.length;resolve(response(sample()));await task;assert.equal(states.length,count);
});
