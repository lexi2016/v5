import test from 'node:test';
import assert from 'node:assert/strict';
import { M18SavedClient, chooseSection, entryPresentation } from '../src/api/m18SavedResult.ts';
const RUN = '46596b03c2ab4e29b1219fd2e5eb698f';
const identity = { run_id: RUN, target_date: '20261012', plan_sha256: 'a'.repeat(64), raw_sha256: 'b'.repeat(64), response_sha256: 'c'.repeat(64), input_identity: 'd'.repeat(64) };
const descriptor = { schema_version: 'v5.m18.v2.descriptor.v1', identity, run_id: RUN, target_date: identity.target_date, generation_id: 'e'.repeat(64), profile_sha256: 'f'.repeat(64), pages_route: '/api/v4/manager/m18/v2/pages', status: 'READY', generated_at: '2026-10-12T00:00:00+00:00' };
const binding = { identity, generation_id: descriptor.generation_id, profile_sha256: descriptor.profile_sha256, manifest_sha256: '1'.repeat(64) };
const overview = { schema: 'v5.m18.offline.v2.overview', ...binding, content_chunks: 100, sections: { status: { kind: 'string', total: 1, loaded_count: 0, not_loaded_count: 1, state: 'NOT_LOADED' }, stocks: { kind: 'array', total: 33, loaded_count: 0, not_loaded_count: 33, state: 'NOT_LOADED' } } };
const entry = { index: 0, kind: 'object', offset: 100, bytes: 5, sha256: '2'.repeat(64), value_state: 'LOADED', value: { status: 'PARTIAL', gaps: ['INPUT_MISSING'], symbol: '00001', name: 'Saved example' } };
const detail = { schema: 'v5.m18.offline.v2.detail', ...binding, section: 'stocks', selection: null, cursor: null, offset: 0, matched_total: 33, not_loaded_count: 1, remaining_entries: 1, entries: Array.from({length:32}, (_,index) => ({...entry,index})), next_cursor: 'opaque-cursor' };
const response = data => new Response(JSON.stringify(data), { headers: { 'content-type': 'application/json' } });
function clientWith(data) { const requests = []; return { requests, client: new M18SavedClient(async (url, options) => { requests.push([url, options]); return response(typeof data === 'function' ? data(url) : data); }) }; }

test('descriptor is requested only for the exact run using GET and no-store', async () => {
 const {client, requests} = clientWith(descriptor); assert.deepEqual(await client.descriptor(RUN), descriptor);
 assert.equal(requests.length, 1); assert.equal(requests[0][0], '/api/v4/manager/m18/v2?run_id=' + RUN);
 assert.equal(requests[0][1].method, 'GET'); assert.equal(requests[0][1].cache, 'no-store');
});
test('invalid run is rejected before a network request', async () => { const {client, requests} = clientWith(descriptor); await assert.rejects(client.descriptor('../wrong')); assert.equal(requests.length, 0); });
test('descriptor identity, target and route cannot be substituted', async () => {
 for (const patch of [{run_id: '0'.repeat(32)}, {target_date: '20261011'}, {pages_route: 'https://elsewhere.invalid/pages'}, {identity: {...identity, run_id: '0'.repeat(32)}}]) {
  await assert.rejects(clientWith({...descriptor, ...patch}).client.descriptor(RUN), /M18_/);
 }
});
test('overview binds generation and all six identities without fetching content pages', async () => {
 const {client, requests} = clientWith(overview); assert.deepEqual(await client.overview(descriptor), overview);
 assert.match(requests[0][0], /\/overview\?run_id=.*&generation_id=/); assert.equal(requests.length,1);
 for (const key of Object.keys(identity)) await assert.rejects(clientWith({...overview, identity:{...identity,[key]:'0'.repeat(identity[key].length)}}).client.overview(descriptor), /M18_BINDING/);
 await assert.rejects(clientWith({...overview,generation_id:'0'.repeat(64)}).client.overview(descriptor), /M18_BINDING/);
});
test('section pages retain actual PARTIAL and gaps and never turn NOT_LOADED into empty success', async () => {
 const {client, requests} = clientWith(detail); const page=await client.section(descriptor, overview, 'stocks');
 assert.equal(page.entries[0].value.status,'PARTIAL'); assert.deepEqual(page.entries[0].value.gaps,['INPUT_MISSING']);
 assert.match(requests[0][0], /section=stocks/); assert.equal(requests.length,1);
 const unavailable={...entry, value_state:'NOT_LOADED', reason:'ITEM_BYTES_LIMIT'}; delete unavailable.value;
 const result=await clientWith({...detail,not_loaded_count:33,entries:Array.from({length:32},(_,index)=>({...unavailable,index}))}).client.section(descriptor,overview,'stocks');
 assert.equal(entryPresentation(result.entries[0]).state,'NOT_LOADED'); assert.equal(entryPresentation(result.entries[0]).value,undefined);
});
test('section rejects wrong manifest, section, cursor and offset', async () => {
 for (const patch of [{manifest_sha256:'0'.repeat(64)}, {section:'other'}, {cursor:'stale'}, {offset:32}]) await assert.rejects(clientWith({...detail,...patch}).client.section(descriptor,overview,'stocks'), /M18_/);
 const next={...detail,cursor:'opaque-cursor',offset:32,not_loaded_count:32,entries:[{...entry,index:32}],next_cursor:null,remaining_entries:0};
 assert.equal((await clientWith(next).client.section(descriptor,overview,'stocks','opaque-cursor',32)).offset,32);
});
test('HTTP missing/invalid remains CANNOT_CONFIRM with fixed reason; no fallback endpoint', async () => {
 const calls=[]; const client=new M18SavedClient(async url=>{calls.push(url); return new Response(JSON.stringify({status:'CANNOT_CONFIRM',reason_codes:['MODULE_RESULT_NOT_AVAILABLE']}),{status:503});});
 await assert.rejects(client.descriptor(RUN), /HTTP_503.*MODULE_RESULT_NOT_AVAILABLE/); assert.equal(calls.length,1);
});
test('response bytes are bounded even without Content-Length and abort is forwarded', async () => {
 const {client}=clientWith({huge:'x'.repeat(300000)}); await assert.rejects(client.descriptor(RUN),/M18_RESPONSE_LIMIT/);
 const controller=new AbortController(); const {client:ok,requests}=clientWith(descriptor); await ok.descriptor(RUN,controller.signal); assert.equal(requests[0][1].signal,controller.signal);
});
test('section chooser prefers real stock rows, otherwise actual existing sections', () => {
 assert.equal(chooseSection(overview.sections),'stocks'); assert.equal(chooseSection({status:overview.sections.status}),'status'); assert.equal(chooseSection({}),'');
});
test('null, empty arrays and false remain distinct values', () => {
 for (const value of [null,[],false,'CANNOT_CONFIRM']) assert.deepEqual(entryPresentation({...entry,value}).value,value);
});

test('newer runs cancel and suppress older results even if transport ignores abort', async () => {
 const {SavedRunSession}=await import('../src/api/m18SavedResult.ts');
 let finishOld; const old=new Promise(resolve=>{finishOld=resolve;}); let count=0;
 const client={descriptor:async ()=>++count===1 ? old : descriptor, overview:async()=>overview, section:async()=>detail};
 const session=new SavedRunSession(client); const first=session.load(RUN); const second=session.load(RUN);
 await second; finishOld({...descriptor,target_date:'19990101'}); await first;
 assert.equal(session.state.descriptor.target_date,'20261012'); assert.equal(session.state.phase,'LOADED');
});
test('section navigation replaces rows and preserves opaque cursor history; failures show no stale data', async () => {
 const {SavedRunSession}=await import('../src/api/m18SavedResult.ts');
 const calls=[]; let fail=false;
 const client={descriptor:async()=>descriptor,overview:async()=>overview,section:async(_d,_o,_s,cursor,offset)=>{calls.push({cursor,offset}); if(fail)throw Error('M18_HTTP_409'); return offset ? {...detail,offset,cursor,entries:[{...entry,index:32}],next_cursor:null,remaining_entries:0} : detail;}};
 const session=new SavedRunSession(client); await session.load(RUN); await session.next(); assert.equal(session.state.page.offset,32);
 await session.previous(); assert.equal(session.state.page.offset,0); assert.deepEqual(calls.map(x=>x.offset),[0,32,0]);
 fail=true; await session.select('status'); assert.equal(session.state.phase,'CANNOT_CONFIRM'); assert.equal(session.state.page,null); assert.match(session.state.error,/409/);
});

test('same-run announcement projection is the default and pages references, not the one container object', async () => {
 const sections={...overview.sections,announcement_reviewed_analysis:{kind:'object',total:1,loaded_count:0,not_loaded_count:1,state:'NOT_LOADED'}};
 const announcement={status:'READY',plan_cutoff:'2026-10-12T07:42:13+08:00',gaps:[],source_section_sha256:'3'.repeat(64),reference_count:33,products:[{product_sha256:'4'.repeat(64),consumed:true}]};
 const page={...detail,section:'announcement_reviewed_analysis',projection:'announcement_references',announcement};
 const {client,requests}=clientWith(page);
 assert.equal(chooseSection(sections),'announcement_reviewed_analysis');
 const result=await client.section(descriptor,{...overview,sections},'announcement_reviewed_analysis');
 assert.equal(result.matched_total,33);assert.equal(result.announcement.reference_count,33);
 assert.match(requests[0][0],/projection=announcement_references/);
 for(const patch of [{projection:'wrong'},{announcement:{...announcement,reference_count:1}},{announcement:{...announcement,source_section_sha256:'wrong'}},{announcement:undefined}]) {
  await assert.rejects(clientWith({...page,...patch}).client.section(descriptor,{...overview,sections},'announcement_reviewed_analysis'),/M18_/);
 }
 await assert.rejects(clientWith({...detail,projection:'announcement_references',announcement}).client.section(descriptor,overview,'stocks'),/M18_/);
});

test('rebound closed group projection preserves announcement default and rejects wrong groups or counts',async()=>{
 const sections={...overview.sections,rebound_research_observation:{kind:'object',total:1,loaded_count:0,not_loaded_count:1,state:'NOT_LOADED'}};
 const rebound={source_section_sha256:'3'.repeat(64),group_counts:{strict:33,near:2,pending:1,excluded:1,screen_unresolved:0},source:{status:'CANNOT_CONFIRM',eligible_screen:null},observation:{status:'CANNOT_CONFIRM',original_computation_status:'READY_WITH_GAPS'}};
 const page={...detail,section:'rebound_research_observation',projection:'rebound_references',group:'strict',rebound};
 const {client,requests}=clientWith(page);
 const result=await client.section(descriptor,{...overview,sections},'rebound_research_observation',null,0,undefined,'strict');
 assert.equal(result.matched_total,33);assert.equal(result.rebound.source.eligible_screen,null);assert.match(requests[0][0],/projection=rebound_references&group=strict/);
 for(const patch of [{group:'near'},{rebound:{...rebound,group_counts:{...rebound.group_counts,strict:1}}},{projection:'announcement_references'}]) await assert.rejects(clientWith({...page,...patch}).client.section(descriptor,{...overview,sections},'rebound_research_observation',null,0,undefined,'strict'),/M18_/);
 await assert.rejects(client.section(descriptor,{...overview,sections},'rebound_research_observation',null,0,undefined,'cards'),/M18_/);
 assert.equal(chooseSection({...sections,announcement_reviewed_analysis:sections.rebound_research_observation}),'announcement_reviewed_analysis');
});

test('rebound group navigation resets cursors, keeps group across pages and suppresses a stale group result',async()=>{
 const {SavedRunSession}=await import('../src/api/m18SavedResult.ts');const calls=[];let finishOld;let delay=false;
 const client={descriptor:async()=>descriptor,overview:async()=>overview,section:async(_d,_o,section,cursor,offset,_signal,group)=>{calls.push({section,cursor,offset,group});if(delay&&group==='near')return new Promise(resolve=>finishOld=resolve);return {...detail,section,group,offset,cursor,entries:offset?[{...entry,index:offset}]:detail.entries,next_cursor:offset?null:'next'};}};
 const session=new SavedRunSession(client);await session.load(RUN);await session.select('rebound_research_observation','strict');await session.next();assert.equal(calls.at(-1).group,'strict');assert.equal(calls.at(-1).offset,32);
 await session.select('rebound_research_observation','pending');assert.equal(calls.at(-1).cursor,null);assert.equal(calls.at(-1).offset,0);assert.equal(session.state.group,'pending');assert.equal(session.state.canPrevious,false);
 delay=true;const old=session.select('rebound_research_observation','near');await session.select('rebound_research_observation','excluded');finishOld({...detail,group:'near'});await old;assert.equal(session.state.group,'excluded');assert.equal(session.state.page.group,'excluded');
});

function variableReboundFixture() {
 const section='rebound_research_observation';
 const sections={...overview.sections,[section]:{kind:'object',total:1,loaded_count:0,not_loaded_count:1,state:'NOT_LOADED'}};
 const rebound={source_section_sha256:'3'.repeat(64),group_counts:{strict:70,near:0,pending:0,excluded:0,screen_unresolved:0},source:{status:'CANNOT_CONFIRM',eligible_screen:null},observation:{status:'CANNOT_CONFIRM'}};
 const page=(offset,count,cursor,next_cursor)=>({...detail,section,projection:'rebound_references',group:'strict',rebound,offset,cursor,matched_total:70,entries:Array.from({length:count},(_,position)=>({...entry,index:offset+position})),remaining_entries:70-offset-count,not_loaded_count:70-count,next_cursor});
 return {section,overview:{...overview,sections},page,pages:[page(0,29,null,'at29'),page(29,30,'at29','at59'),page(59,11,'at59',null)]};
}
test('rebound accepts byte-bounded variable pages and non-multiple-of-32 continuation offsets',async()=>{
 const fixture=variableReboundFixture();
 for(const expected of fixture.pages) {
  const {client}=clientWith(expected);
  assert.deepEqual(await client.section(descriptor,fixture.overview,fixture.section,expected.cursor,expected.offset),expected);
 }
 const empty={...fixture.page(0,0,null,null),matched_total:0,not_loaded_count:0,remaining_entries:0,rebound:{...fixture.pages[0].rebound,group_counts:{strict:0,near:0,pending:0,excluded:0,screen_unresolved:0}}};
 assert.equal((await clientWith(empty).client.section(descriptor,fixture.overview,fixture.section)).entries.length,0);
 // Existing ordinary and announcement sections keep their fixed-entry cursor contract.
 await assert.rejects(clientWith(detail).client.section(descriptor,overview,'stocks','at29',29),/M18_SECTION_REQUEST/);
});
test('rebound variable-page session preserves exact rows and opaque history through next and previous',async()=>{
 const {SavedRunSession}=await import('../src/api/m18SavedResult.ts');const fixture=variableReboundFixture();const requests=[];
 const client=new M18SavedClient(async url=>{
  const parsed=new URL(url,'http://fixture.invalid');const cursor=parsed.searchParams.get('cursor');requests.push({path:parsed.pathname,cursor});
  if(parsed.pathname.endsWith('/overview'))return response(fixture.overview);
  if(parsed.pathname.endsWith('/sections'))return response(parsed.searchParams.get('section')==='stocks'?detail:fixture.pages.find(page=>page.cursor===cursor));
  return response(descriptor);
 });
 const session=new SavedRunSession(client);await session.load(RUN);await session.select(fixture.section,'strict');
 const seen=[...session.state.page.entries.map(row=>row.index)];
 await session.next();assert.equal(session.state.phase,'LOADED');assert.equal(session.state.page.offset,29);seen.push(...session.state.page.entries.map(row=>row.index));
 await session.next();assert.equal(session.state.page.offset,59);seen.push(...session.state.page.entries.map(row=>row.index));
 assert.deepEqual(seen,Array.from({length:70},(_,index)=>index));assert.equal(session.state.page.next_cursor,null);
 await session.previous();assert.equal(session.state.page.offset,29);await session.previous();assert.equal(session.state.page.offset,0);await session.next();assert.equal(session.state.page.offset,29);
 assert.deepEqual(requests.filter(row=>row.path.endsWith('/sections')).slice(1).map(row=>row.cursor),[null,'at29','at59','at29',null,'at29']);
});
test('rebound variable pages reject no progress, excess rows, gaps and wrong continuation selectors',async()=>{
 const fixture=variableReboundFixture();
 const bad=[fixture.page(0,0,null,'at0'),fixture.page(0,33,null,'at33'),{...fixture.pages[0],entries:fixture.pages[0].entries.map((row,index)=>({...row,index:index+1}))},{...fixture.pages[0],next_cursor:null},{...fixture.pages[0],remaining_entries:42},{...fixture.pages[0],group:'near'}];
 for(const page of bad)await assert.rejects(clientWith(page).client.section(descriptor,fixture.overview,fixture.section),/M18_/);
 await assert.rejects(clientWith(fixture.page(59,12,'at59',null)).client.section(descriptor,fixture.overview,fixture.section,'at59',59),/M18_/);
 await assert.rejects(clientWith(fixture.pages[1]).client.section(descriptor,fixture.overview,fixture.section,'wrong',29),/M18_/);
});
