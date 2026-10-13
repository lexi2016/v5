import assert from 'node:assert/strict';
import test from 'node:test';
import fs from 'node:fs';
const moduleURL=new URL('../src/api/m15Mapping.ts',import.meta.url);
test('M15 API client exists',()=>assert.ok(fs.existsSync(moduleURL)));
const {readM15,readM15Page}=await import(moduleURL.href);
const flags={RESEARCH_ONLY:true,formal_eligible:false,natural_verified:false,full_market_coverage:false,production_allowed:false,buy_gate_updated:false,orders_sent:false};
const reference={run_id:'a'.repeat(32),sha256:'b'.repeat(64),target_date:'20261012'};
function fixture(){return {schema_version:'v5.m15.public.v1',target_date:'20261012',reference,lanes:{seed:0,industry:51,individual:null},page_size:50,...flags};}
function fetcher(value,status=200){return async(url,init)=>{assert.equal(init.method,'GET');assert.equal(init.credentials,'omit');return new Response(JSON.stringify(value),{status});};}
test('overview retains unknown lane distinct from zero',async()=>{const value=await readM15('20261012',fetcher(fixture()));assert.equal(value.lanes.individual,null);assert.equal(value.lanes.seed,0);});
test('different target rejected',async()=>{await assert.rejects(readM15('20261013',fetcher(fixture())),/DATE_MISMATCH/);});
test('formal or natural upgrade rejected',async()=>{for(const key of ['formal_eligible','natural_verified','full_market_coverage','production_allowed','buy_gate_updated','orders_sent'])await assert.rejects(readM15('20261012',fetcher({...fixture(),[key]:true})),/BOUNDARY/);});
test('failed API cannot return stale result',async()=>{await assert.rejects(readM15('20261012',fetcher({},503)),/HTTP_503/);});
test('page identities and complete continuation',async()=>{const overview=fixture();const page={schema_version:'v5.m15.page.v1',target_date:'20261012',reference,lane:'industry',offset:50,total:51,rows:[{label:'CPO'}],next_offset:null,...flags};assert.equal((await readM15Page(overview,'industry',50,fetcher(page))).rows.length,1);await assert.rejects(readM15Page(overview,'industry',50,fetcher({...page,reference:{...reference,run_id:'c'.repeat(32)}})),/IDENTITY/);await assert.rejects(readM15Page(overview,'industry',50,fetcher({...page,next_offset:100})),/SEQUENCE/);});
test('unknown lane cannot be silently relabelled a valid empty',async()=>{const page={schema_version:'v5.m15.page.v1',target_date:'20261012',reference,lane:'individual',offset:0,total:0,rows:[],next_offset:null,...flags};await assert.rejects(readM15Page(fixture(),'individual',0,fetcher(page)),/CONTRACT/);});

test('original partial coverage and recovery survive client without upgrading seed-only',async()=>{const original={...fixture(),mode:'seed',seed_gaps:[],seed_coverage_diagnostics:{status:'PARTIAL',reason_codes:['BROADER_US_HK_RELATIONS_NOT_ASSESSED','TARGET_DATE_ELIGIBILITY_CANNOT_CONFIRM'],registry_readback:{cards:[]}},seed_recovery_evaluation:{historical_availability:'NOT_ESTABLISHED',formal_eligible:false},lanes:{seed:2,industry:null,individual:null}};const value=await readM15('20261012',fetcher(original));assert.deepEqual(value,original);assert.equal(value.lanes.industry,null);});
test('legacy overview without coverage remains missing',async()=>{const value=await readM15('20261012',fetcher(fixture()));assert.equal(value.seed_coverage_diagnostics,undefined);assert.equal(value.seed_recovery_evaluation,undefined);});
test('component renders original coverage reasons and explicit seed-only boundary',()=>{const source=fs.readFileSync(new URL('../src/components/M15SavedMapping.vue',import.meta.url),'utf8');for(const text of ['overview.seed_coverage_diagnostics?.status','overview.seed_coverage_diagnostics.reason_codes','overview.seed_recovery_evaluation','仅四键种子，材料路径 NOT_RUN','原保存未提供覆盖诊断'])assert.ok(source.includes(text));});
