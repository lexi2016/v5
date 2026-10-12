import {afterEach,describe,expect,it,vi} from 'vitest';
import {cleanup,fireEvent,render,waitFor} from '@testing-library/vue';
import {readFileSync} from 'node:fs';import {spawnSync} from 'node:child_process';import {resolve} from 'node:path';
import HkStageObserved from './HkStageObserved.vue';
let cached:any;
function saved(){if(!cached){const file=process.env.V5_M08_RESPONSES_FILE;if(file)cached=JSON.parse(readFileSync(file,'utf8'));else{const proc=spawnSync(process.env.PYTHON||'python',['-I','-B','V5/tests/export_m08_readonly_fixture.py'],{cwd:resolve(process.cwd(),'..'),encoding:'utf8'});if(proc.status!==0)throw new Error('M08_SYNTHETIC_FIXTURE_FAILED');cached=JSON.parse(proc.stdout);}}return structuredClone(cached);}
const response=(v:unknown,status=200)=>new Response(JSON.stringify(v),{status});
const missing={status:'NOT_CONFIGURED',module_id:'M08_HK_STAGE_OBSERVED',reason_codes:['M08_REFERENCES_NOT_CONFIGURED'],research_only:true,production_allowed:false,buy_gate_updated:false,orders_sent:false,natural_verified:false,pit_verified:false,formal_admission:false,raw_input_verified:false,computation_replayed:false,market_data_authenticity_verified:false};
afterEach(()=>{cleanup();vi.unstubAllGlobals();});
describe('M08 exact historical stage/run selector',()=>{
 it('renders all ten saved runs, every original row/field, stage labels and observation boundaries',async()=>{
  const data=saved();vi.stubGlobal('fetch',vi.fn(async(url:string)=>{const hash=new URL(url,'http://local').searchParams.get('import_sha256');return response(hash?data.results.find((r:any)=>r.reference.import_sha256===hash):data.catalog);}));const view=render(HkStageObserved);
  await waitFor(()=>expect(view.queryByTestId('m08-rows')).not.toBeNull());expect((view.getByLabelText('M08 阶段') as HTMLSelectElement).options.length).toBe(8);
  for(const result of data.results){
   await fireEvent.update(view.getByLabelText('M08 阶段'),result.reference.stage_id);
   await fireEvent.update(view.getByLabelText('M08 保存 run'),result.reference.import_sha256);
   await waitFor(()=>expect(view.getByTestId('m08-original-artifact').textContent).toBe(JSON.stringify(result.artifact,null,2)));
   const rows=view.getByTestId('m08-rows').querySelectorAll('tbody tr');expect(rows.length).toBe(result.artifact.rows.length);
   result.artifact.rows.forEach((row:Record<string,unknown>,i:number)=>Object.entries(row).forEach(([key,value])=>{const cell=Array.from(rows[i].querySelectorAll('td')).find(td=>td.getAttribute('data-field')===key);expect(cell).toBeDefined();expect(cell?.textContent).toContain(value===null?'null':typeof value==='object'?JSON.stringify(value,null,2):String(value));}));
   for(const value of [result.reference.target_date,result.reference.run_id,result.reference.import_sha256,result.status,result.stage_group,'captured_at=null','natural_verified=false','formal_admission=false'])expect(view.container.textContent).toContain(value);
  }
  expect(view.container.textContent).toContain('SECOND_FILTER');expect(view.container.textContent).toContain('D1_REFERENCE');expect(view.container.textContent).toContain('独立 Stage8');
 },90000);
 it('refresh/loading and disconnection remove old identity and all rows',async()=>{
  const data=saved();let finish!:(r:Response)=>void;let count=0;vi.stubGlobal('fetch',vi.fn(async()=>++count===1?response(data.catalog):count===2?response(data.results[0]):await new Promise<Response>(r=>{finish=r;})));const view=render(HkStageObserved);await waitFor(()=>expect(view.queryByTestId('m08-rows')).not.toBeNull());await fireEvent.click(view.getByRole('button',{name:'重读八阶段历史清单'}));expect(view.queryByTestId('m08-rows')).toBeNull();expect(view.container.textContent).not.toContain(data.results[0].reference.run_id);finish(response({},503));await waitFor(()=>expect(view.container.textContent).toContain('M08_HTTP_503'));expect(view.queryByTestId('m08-rows')).toBeNull();
 });
 it('stale selection cannot overwrite a newer selected run',async()=>{
  const data=saved();let stale!:(r:Response)=>void;let count=0;vi.stubGlobal('fetch',vi.fn(async(url:string)=>{const hash=new URL(url,'http://local').searchParams.get('import_sha256');if(!hash)return response(data.catalog);if(++count===2)return await new Promise<Response>(r=>{stale=r;});return response(data.results.find((r:any)=>r.reference.import_sha256===hash));}));const view=render(HkStageObserved);await waitFor(()=>expect(view.queryByTestId('m08-rows')).not.toBeNull());await fireEvent.update(view.getByLabelText('M08 阶段'),data.results[1].reference.stage_id);expect(view.queryByTestId('m08-rows')).toBeNull();await fireEvent.update(view.getByLabelText('M08 阶段'),data.results[2].reference.stage_id);await waitFor(()=>expect(view.getByTestId('m08-original-artifact').textContent).toBe(JSON.stringify(data.results[2].artifact,null,2)));stale(response(data.results[1]));await new Promise(r=>setTimeout(r,0));expect(view.getByTestId('m08-original-artifact').textContent).toBe(JSON.stringify(data.results[2].artifact,null,2));
 });
 it('missing binding and rejected safety never show fabricated rows',async()=>{
  vi.stubGlobal('fetch',vi.fn(async()=>response(missing)));let view=render(HkStageObserved);await waitFor(()=>expect(view.container.textContent).toContain('NOT_CONFIGURED'));expect(view.queryByTestId('m08-rows')).toBeNull();cleanup();const data=saved();data.results[0].natural_verified=true;let n=0;vi.stubGlobal('fetch',vi.fn(async()=>response(++n===1?data.catalog:data.results[0])));view=render(HkStageObserved);await waitFor(()=>expect(view.container.textContent).toContain('CANNOT_CONFIRM'));expect(view.queryByTestId('m08-rows')).toBeNull();
 });
});
