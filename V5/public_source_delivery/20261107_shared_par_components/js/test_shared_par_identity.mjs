import test, {before, after} from 'node:test';
import assert from 'node:assert/strict';
import {createSharedParStore} from './shared-par-store.mjs';
import {SCREEN_DATES, loadScreen} from './par-screen-data.mjs';

// Synthetic schema fixture only. No source registration or admission is created.
const HASH='2ddb37d1126eb2a68bd4179a65532b6f063212decb2dad2c4af3666bc4edb64f';
function screen(){return {
 schema:'PAR_SCREEN_DISPLAY_V1',source_date:'20261106',scope_count:1,
 selection_version:'MAIN_PLUS_SINA69_407',
 qualifications:{research_only:true,production_allowed:false,selection_admission:false,manual_chart_confirmation:'UNKNOWN',buy_qualification:false,orders_sent:false},
 sources:{selection:{sha256:HASH,bytes:24541169},catalog:{sha256:'a'.repeat(64),bytes:1}},
 rows:[{symbol:'000001.SZ',name:null,actual_date:'20261106',status:'fixture',source_family:'fixture',history_bars:1,reasons:[],layers:Object.fromEntries(['original','nav_smallk','nav_pullback','nav_breakout'].map(g=>[g,{baseline:'UNKNOWN',after_redgreen:'UNKNOWN',after_risk:'UNKNOWN'}]))}]
};}
const request={sourceDate:'20261106',selectionVersion:'merge407'};
before(()=>{assert.deepEqual(SCREEN_DATES,[]);SCREEN_DATES.push('20261106');});
after(()=>{SCREEN_DATES.splice(0);});
test('same-date wrong version rejected',async()=>{
 const s=screen();s.selection_version='WRONG_VERSION';
 await assert.rejects(createSharedParStore({loader:async()=>s}).read(request),/SHARED_PAR_IDENTITY/);
});
test('registered version cannot hide wrong source identity',async()=>{
 const s=screen();s.sources.selection.sha256='b'.repeat(64);
 await assert.rejects(createSharedParStore({loader:async()=>s}).read(request),e=>e.message==='SHARED_PAR_IDENTITY'&&e.status==='UNKNOWN');
});
test('exact synthetic identity accepted, concurrent consumers share load',async()=>{
 let calls=0;const store=createSharedParStore({loader:async()=>{calls++;return screen();}});
 const rows=await Promise.all(Array.from({length:21},()=>store.read(request)));
 assert.equal(calls,1);assert.equal(rows.length,21);
});
test('loader cannot rewrite original request identity',async()=>{
 const store=createSharedParStore({loader:async input=>{input.selectionVersion='main406';const s=screen();delete s.selection_version;s.sources.selection={sha256:'77a9c0e5518376b42e51742e84f2969b91a6fc86c240d025406e7e228c7aeaf4',bytes:24011343};return s;}});
 await assert.rejects(store.read(request),/SHARED_PAR_IDENTITY/);
});
test('legacy requires registered exact digest and size',async()=>{
 const s=screen();delete s.selection_version;s.sources.selection={sha256:'77a9c0e5518376b42e51742e84f2969b91a6fc86c240d025406e7e228c7aeaf4',bytes:24011343};
 const store=createSharedParStore({loader:async()=>s});await store.read({...request,selectionVersion:'main406'});
 s.sources.selection.bytes++;await assert.rejects(store.read({...request,selectionVersion:'main406'}),/SHARED_PAR_IDENTITY/);
});
test('failed read never returns old success',async()=>{
 let wrong=false;const store=createSharedParStore({loader:async()=>{const s=screen();if(wrong)s.selection_version='other';return s;}});
 await store.read(request);wrong=true;await assert.rejects(store.read(request),/SHARED_PAR_IDENTITY/);
});
test('unregistered date stays blocked',async()=>{
 await assert.rejects(createSharedParStore({loader:async()=>screen()}).read({...request,sourceDate:'20261109'}),/SHARED_PAR_VERSION/);
});
test('public default loader remains unbound',async()=>{
 await assert.rejects(loadScreen(),/PUBLIC_EXPORT_NO_APPROVED_PRIVATE_BINDING/);
});
