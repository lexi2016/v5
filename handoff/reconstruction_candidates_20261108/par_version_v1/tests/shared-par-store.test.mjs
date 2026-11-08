import test from 'node:test';import assert from 'node:assert/strict';import {readFile} from 'node:fs/promises';import {webcrypto} from 'node:crypto';
import {createSharedParStore} from '../local/public/research-system/shared-par-store.mjs';
import {loadScreen} from '../local/public/research-system/par-screen-data.mjs';
const fetcher=async url=>new Response(await readFile(new URL('../local/public'+String(url),import.meta.url)));
const actual=options=>loadScreen({...options,fetcher,cryptoImpl:webcrypto});
test('one shared exact frozen projection, 21 concurrent consumers do not reload',async()=>{let calls=0;const store=createSharedParStore({loader:async x=>{calls++;return actual(x);}});const input={sourceDate:'20261106',selectionVersion:'merge407'};const values=await Promise.all(Array.from({length:21},()=>store.snapshot(input)));assert.equal(calls,1);for(const s of values){assert.equal(s.scope_count,5575);assert.equal(s.counts.union,407);assert.equal(s.counts.pending,579);assert.equal(s.source_date,'20261106');assert.equal(s.observation_date,'20261109');}});
test('versions remain separate and failures never fallback',async()=>{const store=createSharedParStore({loader:actual});assert.equal((await store.snapshot({sourceDate:'20261106',selectionVersion:'main406'})).counts.union,406);await assert.rejects(store.snapshot({sourceDate:'20261107'}),/SHARED_PAR_VERSION/);});
test('failed load can retry only same read, no stale value substituted',async()=>{let calls=0;const store=createSharedParStore({loader:async input=>{if(++calls===1)throw Error('MISSING');return actual(input);}});const input={sourceDate:'20261106',selectionVersion:'merge407'};await assert.rejects(store.read(input),/MISSING/);assert.equal((await store.snapshot(input)).counts.union,407);assert.equal(calls,2);});

test('omitted version is normalized before load and refresh revalidates',async()=>{let calls=0;const store=createSharedParStore({loader:async x=>{calls++;return actual(x);}});assert.equal((await store.snapshot({sourceDate:'20261106'})).counts.union,407);assert.equal((await store.snapshot({sourceDate:'20261106',selectionVersion:'merge407'})).counts.union,407);assert.equal(calls,2);});
test('same-date other projection cannot satisfy requested version',async()=>{
 for(const [requested,returned] of [['merge407','main406'],['main406','merge407']]){
 const store=createSharedParStore({loader:x=>actual({...x,selectionVersion:returned})});
 await assert.rejects(store.read({sourceDate:'20261106',selectionVersion:requested}),/SHARED_PAR_IDENTITY/);
 }
});
test('unexpected or absent merge identity is rejected',async()=>{
 for(const version of [undefined,'main406','UNKNOWN']){
 const store=createSharedParStore({loader:async x=>{const s=structuredClone(await actual(x));if(version===undefined)delete s.selection_version;else s.selection_version=version;return s;}});
 await assert.rejects(store.read({sourceDate:'20261106',selectionVersion:'merge407'}),/SHARED_PAR_IDENTITY/);
 }
});
test('legacy identity requires exact registered source, not just absent version',async()=>{
 for(const sourceDate of ['20261105','20261106']){
 const store=createSharedParStore({loader:async x=>{const s=structuredClone(await actual(x));s.sources.selection.sha256='a'.repeat(64);return s;}});
 await assert.rejects(store.read({sourceDate,selectionVersion:'main406'}),/SHARED_PAR_IDENTITY/);
 }
});
test('registered legacy history remains compatible with both existing request aliases',async()=>{
 for(const selectionVersion of ['merge407','main406'])assert.equal((await createSharedParStore({loader:actual}).read({sourceDate:'20261105',selectionVersion})).source_date,'20261105');
});
test('identity rejection is retryable but never returns prior good value',async()=>{
 let wrong=false;const store=createSharedParStore({loader:x=>actual({...x,selectionVersion:wrong?'main406':'merge407'})});const x={sourceDate:'20261106',selectionVersion:'merge407'};
 await store.read(x);wrong=true;await assert.rejects(store.read(x),/SHARED_PAR_IDENTITY/);wrong=false;assert.equal((await store.read(x)).selection_version,'MAIN_PLUS_SINA69_407');
});
test('forged merge version on legacy source still rejects with UNKNOWN',async()=>{
 const store=createSharedParStore({loader:async x=>{const s=structuredClone(await actual({...x,selectionVersion:'main406'}));s.selection_version='MAIN_PLUS_SINA69_407';return s;}});
 await assert.rejects(store.read({sourceDate:'20261106',selectionVersion:'merge407'}),e=>e.message==='SHARED_PAR_IDENTITY'&&e.status==='UNKNOWN');
});
test('loader cannot mutate captured requested identity',async()=>{
 const store=createSharedParStore({loader:async input=>{input.selectionVersion='main406';return actual(input);}});
 await assert.rejects(store.read({sourceDate:'20261106',selectionVersion:'merge407'}),/SHARED_PAR_IDENTITY/);
});
