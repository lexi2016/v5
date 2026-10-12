import {afterEach,describe,expect,it,vi} from 'vitest';
import {cleanup,fireEvent,render,waitFor} from '@testing-library/vue';
import {readFileSync} from 'node:fs';
import {spawnSync} from 'node:child_process';
import {resolve} from 'node:path';
import ACloseReplay from './ACloseReplay.vue';
import {A_REPLAY_SECTIONS} from '../api/aCloseReplay';

function savedProjection(){
 const privateFile=process.env.V5_M09_RESPONSE_FILE;
 if(privateFile)return JSON.parse(readFileSync(privateFile,'utf8'));
 const proc=spawnSync(process.env.PYTHON||'python',['-I','-B','V5/tests/export_m09_readonly_fixture.py'],{cwd:resolve(process.cwd(),'..'),encoding:'utf8'});
 if(proc.status!==0)throw new Error('M09_SYNTHETIC_FIXTURE_FAILED');
 return JSON.parse(proc.stdout);
}
const missing={status:'NOT_CONFIGURED',module_id:'M09_A_CLOSE_REPLAY',reason_codes:['M09_REFERENCE_NOT_CONFIGURED'],research_only:true,production_allowed:false,buy_gate_updated:false,orders_sent:false,natural_verified:false,formal_eligibility_verified:false,strict_1500_pit_verified:false,source_time_verified:false,membership_qualification_verified:false};
const response=(value:unknown,status=200)=>new Response(JSON.stringify(value),{status});
afterEach(()=>{cleanup();vi.unstubAllGlobals();});
describe('M09 exact saved historical replay panel',()=>{
 it('renders actual date, exact identity, original rows and honest gaps',async()=>{
  const value=savedProjection();vi.stubGlobal('fetch',vi.fn(async()=>response(value)));const view=render(ACloseReplay);
  await waitFor(()=>expect(view.container.textContent).toContain(value.generation));
  for(const item of [value.run_id,value.trade_date,'PARTIAL','HISTORICAL_REPLAY','OBSERVED_ROWS_ONLY',value.identity.canonical_review_sha256])expect(view.container.textContent).toContain(item);
  for(const {key} of A_REPLAY_SECTIONS){
   const section=view.getByTestId('m09-'+key);const rows=section.querySelectorAll('tbody tr');expect(rows.length).toBe(value.review[key].length);
   value.review[key].forEach((row:Record<string,unknown>,i:number)=>Object.entries(row).forEach(([field,item])=>{
    const cell=Array.from(rows[i].querySelectorAll('td')).find(td=>td.getAttribute('data-field')===field);
    expect(cell).toBeDefined();expect(cell?.textContent).toContain(typeof item==='object'?JSON.stringify(item,null,2):String(item));
   }));
  }
  expect(view.getByTestId('m09-native-review').textContent).toContain(JSON.stringify(value.review,null,2));
  expect(view.container.textContent).toContain(String(value.publication.historical_research.snapshot_row_count));
  expect(view.container.textContent).toContain('strict_1500_pit_verified=false');
  expect(view.container.textContent).toContain('冻结常量，未经校准');
 });
 it('clears all old identity and rows on loading and disconnection',async()=>{
  const value=savedProjection();let resolveRead!:(value:Response)=>void;let calls=0;
  vi.stubGlobal('fetch',vi.fn(async()=>++calls===1?response(value):await new Promise<Response>(r=>{resolveRead=r;})));
  const view=render(ACloseReplay);await waitFor(()=>expect(view.container.textContent).toContain(value.run_id));
  await fireEvent.click(view.getByRole('button',{name:'重读固定历史研究'}));
  expect(view.container.textContent).not.toContain(value.run_id);expect(view.container.querySelectorAll('table').length).toBe(0);
  resolveRead(response({},503));await waitFor(()=>expect(view.container.textContent).toContain('CANNOT_CONFIRM'));
  expect(view.container.textContent).not.toContain(value.generation);expect(view.container.querySelectorAll('table').length).toBe(0);
 });
 it('renders missing configuration separately and never shows synthetic fallback',async()=>{
  vi.stubGlobal('fetch',vi.fn(async()=>response(missing)));const view=render(ACloseReplay);
  await waitFor(()=>expect(view.container.textContent).toContain('NOT_CONFIGURED'));
  expect(view.container.querySelectorAll('table').length).toBe(0);
 });
 it('rejects promoted source-time evidence without retaining old report',async()=>{
  const value=savedProjection();value.publication.historical_research.source_time_verified=true;
  vi.stubGlobal('fetch',vi.fn(async()=>response(value)));const view=render(ACloseReplay);
  await waitFor(()=>expect(view.container.textContent).toContain('CANNOT_CONFIRM'));
  expect(view.container.textContent).not.toContain(value.run_id);
 });
});
