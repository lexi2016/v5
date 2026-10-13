import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/vue';
import SavedManagerResultView from './SavedManagerResultView.vue';

const route='/api/v4/manager/m18/v2';
const explicitRun='46596b03c2ab4e29b1219fd2e5eb698f', selectedRun='0'.repeat(32);
function transport(options: { substituteExplicit?: boolean; failDefault?: boolean } = {}) {
 const requests: URL[]=[];
 vi.stubGlobal('fetch',vi.fn(async (input:string)=>{
  const url=new URL(input,window.location.origin);
  if(!url.pathname.startsWith(route))return new Response('{}',{status:503});
  requests.push(url);
  const requested=url.searchParams.get('run_id');
  if(!requested&&options.failDefault)return new Response(JSON.stringify({reason_codes:['NO_VERIFIED_SAVED_RUN']}),{status:503});
  const run=options.substituteExplicit?selectedRun:requested??selectedRun;
  const identity={run_id:run,target_date:'20261013',plan_sha256:'a'.repeat(64),raw_sha256:'b'.repeat(64),response_sha256:'c'.repeat(64),input_identity:'d'.repeat(64)};
  const binding={identity,generation_id:'e'.repeat(64),profile_sha256:'f'.repeat(64),manifest_sha256:'1'.repeat(64)};
  const sections=Object.fromEntries(['stocks','gaps'].map(key=>[key,{kind:'array',total:0,loaded_count:0,not_loaded_count:0,state:'NOT_LOADED'}]));
  const value=url.pathname.endsWith('/overview')?{...binding,schema:'v5.m18.offline.v2.overview',content_chunks:1,sections}:url.pathname.endsWith('/sections')?{...binding,schema:'v5.m18.offline.v2.detail',section:url.searchParams.get('section'),selection:null,cursor:null,offset:0,matched_total:0,not_loaded_count:0,remaining_entries:0,next_cursor:null,entries:[]}:{...binding,schema_version:'v5.m18.v2.descriptor.v1',run_id:run,target_date:identity.target_date,pages_route:route+'/pages',status:'READY',generated_at:'2026-10-13T00:00:00Z'};
  return new Response(JSON.stringify(value));
 }));
 return requests;
}
beforeEach(()=>window.history.replaceState(null,'','/manager-selection/?tab=saved#result'));
afterEach(()=>{cleanup();vi.unstubAllGlobals();window.history.replaceState(null,'','/');});
async function ready(run:string) {
 await screen.findByText('已读取运行 '+run);
 await waitFor(()=>expect(screen.queryByText('正在读取同一运行的有界数据页…')).toBeNull());
}

it('starts with a blank run, displays the actual saved identity and pins navigation to it',async()=>{
 const requests=transport();const {container}=render(SavedManagerResultView);
 expect(screen.getByRole('textbox',{name:'运行 ID'})).toHaveProperty('value','');
 await ready(selectedRun);
 expect(requests[0].pathname).toBe(route);expect(requests[0].search).toBe('');
 expect(container.querySelector('.saved-result-heading')?.textContent).toContain('目标日 20261013');
 await fireEvent.click(screen.getByRole('button',{name:'查看缺口 · 0'}));
 await ready(selectedRun);
 for(const url of requests.slice(1)){expect(url.searchParams.get('run_id')).toBe(selectedRun);expect(url.searchParams.get('generation_id')).toBe('e'.repeat(64));}
 expect(new URL(window.location.href).searchParams.has('run_id')).toBe(false);
});
it('clearing an explicit run removes only run_id and reloads the default saved selection',async()=>{
 window.history.replaceState(null,'','/manager-selection/?tab=saved&run_id='+explicitRun+'#result');
 const requests=transport();render(SavedManagerResultView);await ready(explicitRun);
 expect(requests[0].searchParams.get('run_id')).toBe(explicitRun);
 await fireEvent.update(screen.getByRole('textbox',{name:'运行 ID'}),'');
 await fireEvent.click(screen.getByRole('button',{name:'读取已保存结果'}));await ready(selectedRun);
 expect(window.location.pathname+window.location.search+window.location.hash).toBe('/manager-selection/?tab=saved#result');
 expect(requests.filter(url=>url.pathname===route).map(url=>url.search)).toEqual(['?run_id='+explicitRun,'']);
 expect(screen.queryByText('已读取运行 '+explicitRun)).toBeNull();
});
it('an explicit run mismatch fails closed without redirecting to the default selection',async()=>{
 window.history.replaceState(null,'','/?run_id='+explicitRun);
 const requests=transport({substituteExplicit:true});render(SavedManagerResultView);
 expect(await screen.findByRole('alert')).toHaveProperty('textContent',expect.stringContaining('M18_DESCRIPTOR'));
 expect(requests).toHaveLength(1);expect(requests[0].searchParams.get('run_id')).toBe(explicitRun);
 expect(screen.queryByText('已读取运行 '+selectedRun)).toBeNull();
 expect(new URL(window.location.href).searchParams.get('run_id')).toBe(explicitRun);
});
it('a failed default reload clears old rows and identity without retrying the old run',async()=>{
 window.history.replaceState(null,'','/?run_id='+explicitRun);
 const requests=transport({failDefault:true});render(SavedManagerResultView);await ready(explicitRun);
 await fireEvent.update(screen.getByRole('textbox',{name:'运行 ID'}),'');
 await fireEvent.click(screen.getByRole('button',{name:'读取已保存结果'}));
 expect(await screen.findByRole('alert')).toHaveProperty('textContent',expect.stringContaining('NO_VERIFIED_SAVED_RUN'));
 expect(screen.queryByText('已读取运行 '+explicitRun)).toBeNull();expect(screen.queryByRole('table')).toBeNull();
 expect(requests.filter(url=>url.pathname===route).map(url=>url.search)).toEqual(['?run_id='+explicitRun,'']);
 expect(new URL(window.location.href).searchParams.has('run_id')).toBe(false);
});
