import {afterEach,describe,expect,it,vi} from 'vitest';
import {cleanup,fireEvent,render,waitFor} from '@testing-library/vue';
import {readFileSync} from 'node:fs';
import {spawnSync} from 'node:child_process';
import {resolve} from 'node:path';
import HkCloseReview from './HkCloseReview.vue';

// A one-real-GET response may be supplied privately by the acceptance runner.
// It is never included in report.json, stdout or GitHub.
function savedProjection(){
 const privateFile=process.env.V5_M10_RESPONSE_FILE;
 if(privateFile)return JSON.parse(readFileSync(privateFile,'utf8'));
 const proc=spawnSync(process.env.PYTHON||'python',['-I','-S','-B','V5/tests/export_m10_readonly_fixture.py'],{cwd:resolve(process.cwd(),'..'),encoding:'utf8'});
 if(proc.status!==0)throw new Error('M10_SYNTHETIC_FIXTURE_FAILED');
 return JSON.parse(proc.stdout);
}
const missing={status:'NOT_CONFIGURED',module_id:'M10_HK_CLOSE_REVIEW',reason_codes:['M10_REFERENCE_NOT_CONFIGURED'],research_only:true,production_allowed:false,buy_gate_updated:false,orders_sent:false,natural_verified:false,formal_eligibility_verified:false};
const response=(value:unknown,status=200)=>new Response(JSON.stringify(value),{status});
afterEach(()=>{cleanup();vi.unstubAllGlobals();});
describe('M10 exact saved read-only review panel',()=>{
 it('renders every original saved row, same run/generation and partial null metrics',async()=>{
  const value=savedProjection();vi.stubGlobal('fetch',vi.fn(async()=>response(value)));
  const view=render(HkCloseReview);
  await waitFor(()=>expect(view.container.textContent).toContain(value.generation));
  expect(view.container.textContent).toContain(value.run_id);
  expect(view.container.textContent).toContain(value.native_review_sha256);
  expect(view.container.textContent).toContain('PARTIAL');
  expect(view.container.textContent).toContain('null · 无法确认');
  const tables=view.container.querySelectorAll('table');expect(tables.length).toBe(5);
  const keys=['close_top20','model_rows','stage_rows','top20_attribution'];
  keys.forEach((key,index)=>{
   const rows=tables[index+1].querySelectorAll('tbody tr');expect(rows.length).toBe(value.review[key].length);
   value.review[key].forEach((row:Record<string,unknown>,rowIndex:number)=>expect(rows[rowIndex].textContent).toContain(String(row.code)));
  });
  expect(tables[0].querySelectorAll('tbody tr').length).toBe(7);
  expect(view.container.textContent).toContain('formal_eligibility_verified=false');
 });
 it('clears every previous table while refreshing and on rejection',async()=>{
  const value=savedProjection();let resolveRead!:(value:Response)=>void;let calls=0;
  vi.stubGlobal('fetch',vi.fn(async()=>++calls===1?response(value):await new Promise<Response>(r=>{resolveRead=r;})));
  const view=render(HkCloseReview);await waitFor(()=>expect(view.container.querySelectorAll('table').length).toBe(5));
  await fireEvent.click(view.getByRole('button',{name:'重读固定复盘结果'}));
  expect(view.container.querySelectorAll('table').length).toBe(0);resolveRead(response({},409));
  await waitFor(()=>expect(view.container.textContent).toContain('CANNOT_CONFIRM'));
  expect(view.container.querySelectorAll('table').length).toBe(0);
 });
 it('shows explicit missing binding without a successful empty review',async()=>{
  vi.stubGlobal('fetch',vi.fn(async()=>response(missing)));const view=render(HkCloseReview);
  await waitFor(()=>expect(view.container.textContent).toContain('NOT_CONFIGURED'));
  expect(view.container.querySelectorAll('table').length).toBe(0);
 });
});
