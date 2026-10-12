import {afterEach,expect,it,vi} from 'vitest';
import {cleanup,fireEvent,render,waitFor} from '@testing-library/vue';
import SourceBundleStatus from './SourceBundleStatus.vue';
const flags={natural_verified:false,formal_eligibility_verified:false,production_allowed:false,buy_gate_updated:false,orders_sent:false};
const source={schema_version:'v5.source_bundle.result.v1',status:'SOURCE_BUNDLE_ATTEMPTED',observed_at:'2026-10-12T15:00:00Z',request_sha256:'a'.repeat(64),data_kind:'RECORDED_INPUT_REPLAY',...flags,
 modules:['M01_A_MARKET','M02_HK_MARKET','M03_US_MARKET','M05_A_PRESELECTION'].map((module_id,i)=>({module_id,owner_entry:['m01_a_source','m02_hk_source','m03_us_source','m05_a_preselection'][i],status:i===2?'VALIDATED_SOURCE_BINDING':'BLOCKED_REQUEST_MISSING',...flags}))};
afterEach(()=>{cleanup();vi.unstubAllGlobals();});
it('all five reads mount independently and a rejected M09 leaves old source and HK panels intact',async()=>{
 const requests:string[]=[];let resolveM09!:(response:Response)=>void;
 vi.stubGlobal('fetch',vi.fn(async(url:string)=>{
  requests.push(url);
  if(url.endsWith('/status'))return new Response(JSON.stringify(source));
  if(url.endsWith('/hk-stage-observed'))return new Response(JSON.stringify({status:'NOT_CONFIGURED',module_id:'M08_HK_STAGE_OBSERVED',reason_codes:['M08_REFERENCES_NOT_CONFIGURED'],research_only:true,pit_verified:false,formal_admission:false,raw_input_verified:false,computation_replayed:false,market_data_authenticity_verified:false,...flags}));
  if(url.endsWith('/a-close-replay'))return await new Promise<Response>(r=>{resolveM09=r;});
  const m10=url.endsWith('/hk-close-review');return new Response(JSON.stringify({status:'NOT_CONFIGURED',module_id:m10?'M10_HK_CLOSE_REVIEW':'M06_HK_PRESELECTION',reason_codes:[m10?'M10_REFERENCE_NOT_CONFIGURED':'M06_REFERENCE_NOT_CONFIGURED'],research_only:true,model_weights_reverified:false,...flags}));
 }));
 const view=render(SourceBundleStatus);
 await waitFor(()=>expect(requests.length).toBe(5));
 await waitFor(()=>expect(view.container.textContent).toContain('VALIDATED_SOURCE_BINDING'));
 expect(view.container.querySelectorAll('.source-grid article').length).toBe(4);
 expect(new Set(requests).size).toBe(5);
 expect(view.getByRole('region',{name:'M09 A股历史研究回放'})).toBeDefined();
 resolveM09(new Response('{}',{status:503}));await waitFor(()=>expect(view.container.textContent).toContain('M09_HTTP_503'));
 expect(view.container.querySelectorAll('.source-grid article').length).toBe(4);
 expect(view.container.textContent).toContain('VALIDATED_SOURCE_BINDING');
 await fireEvent.click(view.getByRole('button',{name:'读取模块实际结果'}));
 await waitFor(()=>expect(requests.length).toBe(6));
 expect(requests.at(-1)).toBe('/api/v5/source-bundle/status');
});
