import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';
import test from 'node:test';
const apiUrl=new URL('../src/api/m04SavedResearch.ts',import.meta.url);
let api;
const FLAGS={research_only:true,natural_verified:false,historical_pit_claimed:false,formal_eligibility_verified:false,production_allowed:false,buy_gate_updated:false,orders_sent:false};
function fixture(){return {schema_version:'v5.m04_saved_research.v1',module_id:'M04_RESEARCH_INTELLIGENCE',status:'SAVED_HISTORICAL_SAMPLE',data_kind:'RECORDED_INPUT_REPLAY',coverage_scope:'FIXED_18_ARTICLE_SAMPLE',article_count:18,pit:'UNKNOWN',missing_retrieved_at:18,missing_available_at:18,out_of_sample_record_errors:53,reference:{archive_date:'20261012',source_slot:'2100',source_run_id:'hip-49cb26f7f3a0661bde1d1440',publication_time_is_not_article_availability:true},archive:{archive_date:'20261012',article_count:18,articles:Array.from({length:18},(_,i)=>({article_id:String(i),source_title:'SYNTHETIC <script>alert(1)</script>',retrieved_at:null,available_at:null})),production_allowed:false,buy_gate_updated:false,orders_sent:false},...FLAGS};}
async function load(){assert.ok(existsSync(apiUrl),'M04 client must exist');return api??=await import(apiUrl.href);}
test('fixed GET reads all 18 synthetic articles and preserves unknown clocks',async()=>{
 const m=await load();let called;const result=await m.readSavedResearch(async(url,init)=>{called={url,init};return new Response(JSON.stringify(fixture()));});
 assert.equal(called.url,'/api/v5/source-bundle/research-intelligence');assert.equal(called.init.method,'GET');assert.equal(called.init.cache,'no-store');assert.equal(called.init.credentials,'omit');
 assert.deepEqual(result,fixture());
});
test('not configured remains missing and incomplete, false PIT or unsafe rows are rejected',async()=>{
 const m=await load();const missing={status:'NOT_CONFIGURED',module_id:'M04_RESEARCH_INTELLIGENCE',reason_codes:['M04_SAVED_REFERENCE_NOT_CONFIGURED'],...FLAGS};
 assert.equal(await m.readSavedResearch(async()=>new Response(JSON.stringify(missing))),null);
 for(const mutate of [v=>v.pit='PASS',v=>v.article_count=17,v=>v.archive.articles.pop(),v=>v.reference.source_run_id='latest',v=>v.production_allowed=true,v=>v.archive.orders_sent=true,v=>v.missing_available_at=0,v=>v.out_of_sample_record_errors=0,v=>v.archive.articles[0].available_at='2026-10-12T21:00:00+08:00']){
  const value=fixture();mutate(value);await assert.rejects(m.readSavedResearch(async()=>new Response(JSON.stringify(value))));
 }
 await assert.rejects(m.readSavedResearch(async()=>new Response('{}',{status:503})),/M04_HTTP_503/);
 await assert.rejects(m.readSavedResearch(async()=>new Response('{}',{headers:{'content-length':String(17*1024*1024)}})),/M04_RESPONSE_LIMIT/);
});
test('retry clears old results and stale or closed requests cannot replace current state',async()=>{
 const m=await load();const calls=[],states=[];const session=new m.SavedResearchSession(s=>states.push(s),()=>new Promise(resolve=>calls.push(resolve)));
 const old=session.load(),current=session.load();calls[1](new Response(JSON.stringify(fixture())));await current;calls[0](new Response('{}',{status:503}));await old;
 assert.equal(states.at(-1).phase,'LOADED');const failing=session.load();assert.equal(states.at(-1).result,null);calls[2](new Response('{}',{status:503}));await failing;assert.equal(states.at(-1).phase,'CANNOT_CONFIRM');assert.equal(states.at(-1).result,null);
 const closing=session.load();session.close();const length=states.length;calls[3](new Response(JSON.stringify(fixture())));await closing;assert.equal(states.length,length);
});
test('source module and main navigation expose a lazy fixed-sample research disclosure',async()=>{
 const source=readFileSync(new URL('../src/components/SourceBundleStatus.vue',import.meta.url),'utf8');assert.match(source,/<M04SavedResearch\s*\/>/);
 const component=readFileSync(new URL('../src/components/M04SavedResearch.vue',import.meta.url),'utf8');assert.match(component,/id="m04-saved-research"/);assert.match(component,/@toggle="onToggle"/);assert.doesNotMatch(component,/v-html|onMounted/);assert.match(component,/PIT UNKNOWN/);assert.match(component,/样本外/);
 const view=readFileSync(new URL('../src/views/SavedManagerResultView.vue',import.meta.url),'utf8');assert.match(view,/@click="openResearch"/);assert.match(view,/研究情报 · M04/);assert.match(view,/target.open=true/);
});

test('M04 route uses the existing read-only source proxy',()=>{const vite=readFileSync(new URL('../vite.config.ts',import.meta.url),'utf8');assert.match(vite,/proxy\['\/api\/v5\/source-bundle\/research-intelligence'\] = readonlyProxy\(sourceTarget\)/);});
