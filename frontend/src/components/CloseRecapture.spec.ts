import {afterEach,expect,it,vi} from 'vitest';
import {cleanup,fireEvent,render,waitFor} from '@testing-library/vue';
import {spawnSync} from 'node:child_process';
import {resolve} from 'node:path';
import CloseRecapture from './CloseRecapture.vue';
import {DEFAULT_CLOSE_RECAPTURE_QUERY} from '../api/closeRecapture';
const generated=spawnSync(process.env.PYTHON||'python',['-I','-B','tests/export_m17_fixture.py'],{cwd:resolve(process.cwd()),encoding:'utf8'});
if(generated.status!==0)throw new Error('M17_SYNTHETIC_FIXTURE_FAILED: '+generated.stderr);
const fixture=JSON.parse(generated.stdout);
const query=(value:typeof fixture.ready)=>({source_trade_date:value.source_trade_date,run_id:value.run_id});
const response=(value:unknown,status=200)=>new Response(JSON.stringify(value),{status});
afterEach(()=>{cleanup();vi.unstubAllGlobals();});
it('renders original dates, all 100 rows and fields, exact identity, gaps and unverified money units',async()=>{
 const value=structuredClone(fixture.ready);value.rows[0].last_price=null;
 vi.stubGlobal('fetch',vi.fn(async()=>response(value)));
 const view=render(CloseRecapture,{props:{initialReference:query(value)}});
 await waitFor(()=>expect(view.getByTestId('m17-rows')).toBeDefined());
 const rows=view.getByTestId('m17-rows').querySelectorAll('tbody tr');expect(rows.length).toBe(100);
 for(const key of ['source_trade_date','plan_trade_date','run_id','captured_at','available_at','execution_kind','execution_label','operation'])expect(view.container.textContent).toContain(value[key]);
 value.rows.forEach((row:Record<string,unknown>,i:number)=>Object.entries(row).forEach(([field,item])=>{
  const cell=Array.from(rows[i].querySelectorAll('td')).find(td=>td.getAttribute('data-field')===field);
  expect(cell).toBeDefined();expect(cell?.textContent).toContain(typeof item==='object'?JSON.stringify(item,null,2):String(item));
 }));
 for(const gap of value.cannot_confirm)expect(view.getByTestId('m17-gaps').textContent).toContain(gap);
 expect(view.container.textContent).toContain('币种与单位未核');expect(view.container.textContent).not.toContain('亿元');
 expect(view.container.textContent).toContain('received_not_historical_1530=true');
 expect(view.container.textContent).toContain('natural_verified=false');expect(view.container.textContent).toContain('formal_eligibility_verified=false');
 expect(JSON.parse(view.getByTestId('m17-original-metadata').textContent||'{}').coverage).toEqual(value.coverage);
});
it('keeps original PARTIAL and its two rows without inventing an empty success',async()=>{
 vi.stubGlobal('fetch',vi.fn(async()=>response(fixture.partial)));
 const view=render(CloseRecapture,{props:{initialReference:query(fixture.partial)}});
 await waitFor(()=>expect(view.getByTestId('m17-rows').querySelectorAll('tbody tr').length).toBe(2));
 expect(view.container.textContent).toContain('PARTIAL');expect(view.getByTestId('m17-gaps').textContent).toContain('PYTDX_EXHQ_COVERAGE_INCOMPLETE');
});
it('auto-reads only the reserved exact reference and keeps missing service visibly unconfirmed',async()=>{
 const requests:string[]=[];vi.stubGlobal('fetch',vi.fn(async(url:string)=>{requests.push(url);return response({},503);}));
 const view=render(CloseRecapture);
 await waitFor(()=>expect(view.container.textContent).toContain('M17_HTTP_503'));
 expect(Object.fromEntries(new URL(requests[0],'http://local').searchParams)).toEqual(DEFAULT_CLOSE_RECAPTURE_QUERY);
 expect(view.queryByRole('table')).toBeNull();expect(view.container.textContent).toContain('CANNOT_CONFIRM');
});
it('changing the exact query clears old rows during reload and rejects a mismatched saved run',async()=>{
 let resolveRead!:(response:Response)=>void;let calls=0;
 vi.stubGlobal('fetch',vi.fn(async()=>++calls===1?response(fixture.ready):await new Promise<Response>(r=>{resolveRead=r;})));
 const view=render(CloseRecapture,{props:{initialReference:query(fixture.ready)}});
 await waitFor(()=>expect(view.queryByRole('table')).not.toBeNull());
 await fireEvent.update(view.getByLabelText('M17 精确保存 run'),fixture.partial.run_id);
 await fireEvent.click(view.getByRole('button',{name:'读取 M17 精确保存结果'}));
 expect(view.queryByRole('table')).toBeNull();expect(view.queryByTestId('m17-loaded-identity')).toBeNull();
 resolveRead(response(fixture.ready));await waitFor(()=>expect(view.container.textContent).toContain('M17_EXACT_REFERENCE'));
 expect(view.queryByRole('table')).toBeNull();expect(view.queryByTestId('m17-loaded-identity')).toBeNull();
});
it('unmount aborts its own read',async()=>{
 let signal:AbortSignal|undefined;let finish!:(response:Response)=>void;
 vi.stubGlobal('fetch',vi.fn(async(_url:string,init:RequestInit)=>{signal=init.signal as AbortSignal;return await new Promise<Response>(r=>{finish=r;});}));
 const view=render(CloseRecapture);await waitFor(()=>expect(signal).toBeDefined());
 view.unmount();expect(signal?.aborted).toBe(true);finish(response({},503));
});
