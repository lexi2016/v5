import { afterEach, expect, it, vi } from 'vitest';
import { cleanup, render, screen, fireEvent } from '@testing-library/vue';
import SavedManagerResultView from './SavedManagerResultView.vue';
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });
it('shows an ordinary V5 page and keeps missing API results visibly unconfirmed', async () => {
 vi.stubGlobal('fetch',vi.fn(async () => new Response(JSON.stringify({status:'CANNOT_CONFIRM',reason_codes:['MODULE_RESULT_NOT_AVAILABLE']}),{status:503})));
 render(SavedManagerResultView);
 expect(screen.getByRole('heading',{name:'V5 经理选股'})).toBeTruthy();
 expect(await screen.findByRole('alert')).toHaveProperty('textContent',expect.stringContaining('CANNOT_CONFIRM'));
 expect(screen.getByText('阶段选股 · 未接入')).toHaveProperty('disabled',true);
 expect(screen.queryByRole('table')).toBeNull();
 expect(fetch).toHaveBeenCalledTimes(1);
});
it('opens consumed announcement references by default and reuses the stock reasons view', async () => {
 const run='46596b03c2ab4e29b1219fd2e5eb698f';
 const identity={run_id:run,target_date:'20261012',plan_sha256:'a'.repeat(64),raw_sha256:'b'.repeat(64),response_sha256:'c'.repeat(64),input_identity:'d'.repeat(64)};
 const binding={identity,generation_id:'e'.repeat(64),profile_sha256:'f'.repeat(64),manifest_sha256:'1'.repeat(64)};
 const descriptor={...binding,schema_version:'v5.m18.v2.descriptor.v1',run_id:run,target_date:'20261012',pages_route:'/api/v4/manager/m18/v2/pages',status:'READY',generated_at:'2026-10-12T00:00:00Z'};
 const overview={...binding,schema:'v5.m18.offline.v2.overview',content_chunks:5,sections:{announcement_reviewed_analysis:{kind:'object',total:1,loaded_count:0,not_loaded_count:1,state:'NOT_LOADED'},stocks:{kind:'array',total:0,loaded_count:0,not_loaded_count:0,state:'NOT_LOADED'},rebound_research_observation:{kind:'object',total:1,loaded_count:0,not_loaded_count:1,state:'NOT_LOADED'}}};
 const page={...binding,schema:'v5.m18.offline.v2.detail',section:'announcement_reviewed_analysis',projection:'announcement_references',selection:null,cursor:null,offset:0,matched_total:1,not_loaded_count:0,remaining_entries:0,next_cursor:null,
  announcement:{status:'READY',plan_cutoff:'2026-10-12T07:42:13+08:00',source_section_sha256:'2'.repeat(64),reference_count:1,gaps:[],products:[]},
  entries:[{index:0,kind:'object',offset:0,bytes:900,sha256:'3'.repeat(64),value_state:'LOADED',value:{stock_code:'01234',stock_name:'合成公告公司',research_status:'SELECTED',publication_date:'2026-10-09',target_trade_date:'20261012',point_in_time_status:'CANNOT_CONFIRM',connect_eligibility_status:'NOT_ASSESSED',selection_reasons:[{disposition:'SELECTED_EVENT',reason:'合成逐篇理由'}],risk_notes:['合成风险'],article_refs:[{art_code:'SYNTHETIC',title:'合成公告',source_sha256:'4'.repeat(64)}]}}]};
 const rebound={...page,section:'rebound_research_observation',projection:'rebound_references',group:'strict',announcement:undefined,
  rebound:{source_section_sha256:'5'.repeat(64),group_counts:{strict:1,near:0,pending:0,excluded:0,screen_unresolved:0},source:{status:'CANNOT_CONFIRM',eligible_screen:null,scope:'INDEPENDENT_READ_TIME_OBSERVATION_NOT_SAVED_PLAN_OR_FORMAL_SELECTION'},observation:{status:'CANNOT_CONFIRM',original_computation_status:'READY_WITH_GAPS',gaps:['SYNTHETIC_UNIT_UNVERIFIED']}},
  entries:[{...page.entries[0],value:{code:'04321',name:'合成超跌公司',classification:'STRICT_REBOUND',reason_for_group:'合成原分组理由',amount_native:12,volume_unit:'NOT_PROVEN',connect_eligibility:'UNVERIFIED',observed_session:'20261009',target_monday:'20261012'}}]};
 const requests:string[]=[];
 vi.stubGlobal('fetch',vi.fn(async (url:string)=>{requests.push(url);let value:unknown=url.includes('/overview?')?overview:url.includes('/sections?')?page:descriptor;if(url.includes('projection=rebound_references'))value=url.includes('group=near')?{...rebound,group:'near',matched_total:0,entries:[]}:rebound;return new Response(JSON.stringify(value));}));
 render(SavedManagerResultView);
 expect(await screen.findByRole('heading',{name:'01234 合成公告公司｜入选研究名单'})).toBeTruthy();
 expect(screen.getByText('入选事件研究：合成逐篇理由。')).toBeTruthy();
 expect(screen.getByText('风险/限制：合成风险')).toBeTruthy();
 expect(screen.getByText('历史 PIT：CANNOT_CONFIRM；互联互通资格：NOT_ASSESSED。')).toBeTruthy();
 expect(screen.getByRole('button',{name:'公告研究股票'}).getAttribute('aria-current')).toBe('page');
 expect(requests).toHaveLength(3);
 expect(requests[2]).toContain('section=announcement_reviewed_analysis&projection=announcement_references');
 expect(screen.queryByRole('table')).toBeNull();
 expect(screen.queryByRole('link')).toBeNull();
 await fireEvent.click(screen.getByRole('button',{name:'超跌研究'}));
 expect(await screen.findByRole('heading',{name:'合成超跌公司 · 04321 · 严格条件研究观察'})).toBeTruthy();
 expect(screen.queryByRole('heading',{name:'01234 合成公告公司｜入选研究名单'})).toBeNull();
 expect(screen.getByText('原分类 STRICT_REBOUND；分组理由：合成原分组理由。')).toBeTruthy();
 expect(screen.getByText(/原生成交额 amount_native 12；币种 未知；成交额单位 未知；成交量单位 NOT_PROVEN/)).toBeTruthy();
 await fireEvent.click(screen.getByRole('button',{name:'近条件研究观察 · 0'}));
 expect(await screen.findByText('近条件研究观察原数组为 0 条，不代表正式资格已确认。')).toBeTruthy();
 expect(screen.queryByRole('heading',{name:'合成超跌公司 · 04321 · 严格条件研究观察'})).toBeNull();
 await fireEvent.click(screen.getByRole('button',{name:'公告研究股票'}));
 expect(await screen.findByRole('heading',{name:'01234 合成公告公司｜入选研究名单'})).toBeTruthy();
});
