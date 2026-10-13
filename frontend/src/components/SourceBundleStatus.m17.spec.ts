import {afterEach,expect,it,vi} from 'vitest';
import {cleanup,fireEvent,render,waitFor} from '@testing-library/vue';
import SourceBundleStatus from './SourceBundleStatus.vue';
const flags={natural_verified:false,formal_eligibility_verified:false,production_allowed:false,buy_gate_updated:false,orders_sent:false};
const source={schema_version:'v5.source_bundle.result.v1',status:'SOURCE_BUNDLE_ATTEMPTED',observed_at:'2026-10-12T15:00:00Z',request_sha256:'a'.repeat(64),data_kind:'RECORDED_INPUT_REPLAY',...flags,
 modules:['M01_A_MARKET','M02_HK_MARKET','M03_US_MARKET','M05_A_PRESELECTION'].map((module_id,i)=>({module_id,owner_entry:['m01_a_source','m02_hk_source','m03_us_source','m05_a_preselection'][i],status:i===2?'VALIDATED_SOURCE_BINDING':'BLOCKED_REQUEST_MISSING',...flags}))};
afterEach(()=>{cleanup();vi.unstubAllGlobals();});
it('mounts independent M17 exact GET; its failure and reload do not replace source/module results',async()=>{
 const requests:string[]=[];let resolveM17!:(response:Response)=>void;
 vi.stubGlobal('fetch',vi.fn(async(url:string)=>{
  requests.push(url);
  if(url.endsWith('/status'))return new Response(JSON.stringify(source));
  if(url.startsWith('/api/v5/manager/close-recapture?'))return await new Promise<Response>(r=>{resolveM17=r;});
  return new Response('{}',{status:503});
 }));
 const view=render(SourceBundleStatus);
 await waitFor(()=>expect(requests.length).toBe(6));
 await waitFor(()=>expect(view.container.textContent).toContain('VALIDATED_SOURCE_BINDING'));
 expect(view.getByRole('region',{name:'M17 收盘补采已保存观察'})).toBeDefined();
 expect(requests.filter(url=>url.startsWith('/api/v5/manager/close-recapture?'))).toEqual(['/api/v5/manager/close-recapture?source_trade_date=20261012&run_id=ca2c344b61334ad28f4b6146117643cd']);
 resolveM17(new Response('{}',{status:503}));await waitFor(()=>expect(view.container.textContent).toContain('M17_HTTP_503'));
 expect(view.container.querySelectorAll('.source-grid article').length).toBe(4);
 expect(view.container.textContent).toContain('VALIDATED_SOURCE_BINDING');
 await fireEvent.click(view.getByRole('button',{name:'读取 M17 精确保存结果'}));
 await waitFor(()=>expect(requests.length).toBe(7));expect(requests.at(-1)).toContain('/api/v5/manager/close-recapture?');
 expect(view.container.querySelectorAll('.source-grid article').length).toBe(4);
 resolveM17(new Response('{}',{status:409}));await waitFor(()=>expect(view.container.textContent).toContain('M17_HTTP_409'));
});
