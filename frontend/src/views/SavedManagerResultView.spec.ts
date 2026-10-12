import { afterEach, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/vue';
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
 const overview={...binding,schema:'v5.m18.offline.v2.overview',content_chunks:5,sections:{announcement_reviewed_analysis:{kind:'object',total:1,loaded_count:0,not_loaded_count:1,state:'NOT_LOADED'},stocks:{kind:'array',total:0,loaded_count:0,not_loaded_count:0,state:'NOT_LOADED'}}};
 const page={...binding,schema:'v5.m18.offline.v2.detail',section:'announcement_reviewed_analysis',projection:'announcement_references',selection:null,cursor:null,offset:0,matched_total:1,not_loaded_count:0,remaining_entries:0,next_cursor:null,
  announcement:{status:'READY',plan_cutoff:'2026-10-12T07:42:13+08:00',source_section_sha256:'2'.repeat(64),reference_count:1,gaps:[],products:[]},
  entries:[{index:0,kind:'object',offset:0,bytes:900,sha256:'3'.repeat(64),value_state:'LOADED',value:{stock_code:'01234',stock_name:'合成公告公司',research_status:'SELECTED',publication_date:'2026-10-09',target_trade_date:'20261012',point_in_time_status:'CANNOT_CONFIRM',connect_eligibility_status:'NOT_ASSESSED',selection_reasons:[{disposition:'SELECTED_EVENT',reason:'合成逐篇理由'}],risk_notes:['合成风险'],article_refs:[{art_code:'SYNTHETIC',title:'合成公告',source_sha256:'4'.repeat(64)}]}}]};
 const requests:string[]=[];
 vi.stubGlobal('fetch',vi.fn(async (url:string)=>{requests.push(url);return new Response(JSON.stringify(url.includes('/overview?')?overview:url.includes('/sections?')?page:descriptor));}));
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
});
