import { afterEach, expect, it, vi } from 'vitest';
import { cleanup, render, screen, fireEvent, waitFor } from '@testing-library/vue';
import SavedManagerResultView from './SavedManagerResultView.vue';
afterEach(() => { cleanup(); vi.unstubAllGlobals(); window.history.replaceState({}, '', '/'); });
it('looks up the exact selected target date before opening the saved M18 run', async () => {
 const run='a'.repeat(32);
 const product={run_id:run,sha256:'b'.repeat(64),consumed:true};
 const requests:string[]=[];
 vi.stubGlobal('fetch',vi.fn(async (url:string) => {
  requests.push(url);
  if(url==='/api/v4/manager/research/workspace?date=20261016&view=auto') {
   return new Response(JSON.stringify({target_trade_date:'20261016',plan_product:product}));
  }
  return new Response(JSON.stringify({status:'CANNOT_CONFIRM',reason_codes:['MODULE_RESULT_NOT_AVAILABLE']}),{status:503});
 }));
 render(SavedManagerResultView);
 await screen.findByRole('alert');
 await fireEvent.update(screen.getByLabelText('目标交易日'),'2026-10-16');
 await fireEvent.click(screen.getByRole('button',{name:'按日期查找已保存运行'}));
 expect(await screen.findByText(/已找到日期匹配的引用/)).toBeTruthy();
 expect(requests).toContain('/api/v4/manager/research/workspace?date=20261016&view=auto');
 expect(new URLSearchParams(window.location.search).get('target_date')).toBe('20261016');
 expect(new URLSearchParams(window.location.search).get('run_id')).toBe(run);
 expect(requests.some(url=>url.startsWith('/api/v4/manager/m18/v2')&&url.includes(run))).toBe(true);
});

it('does not bind a date to a run when the saved workspace date identity differs', async () => {
 vi.stubGlobal('fetch',vi.fn(async (url:string) => {
  if(url==='/api/v4/manager/research/workspace?date=20261016&view=auto') {
   return new Response(JSON.stringify({target_trade_date:'20261015',plan_product:{run_id:'a'.repeat(32),sha256:'b'.repeat(64),consumed:true}}));
  }
  return new Response(JSON.stringify({status:'CANNOT_CONFIRM',reason_codes:['MODULE_RESULT_NOT_AVAILABLE']}),{status:503});
 }));
 render(SavedManagerResultView);
 await screen.findByRole('alert');
 await fireEvent.update(screen.getByLabelText('目标交易日'),'2026-10-16');
 await fireEvent.click(screen.getByRole('button',{name:'按日期查找已保存运行'}));
 expect(await screen.findByText(/MANAGER_DATE_LOOKUP_IDENTITY_MISMATCH/)).toBeTruthy();
 expect(new URLSearchParams(window.location.search).get('run_id')).toBeNull();
});

it('ignores an older date lookup after the date input changes again', async () => {
 let complete!:(value:Response)=>void;
 const run='a'.repeat(32);
 vi.stubGlobal('fetch',vi.fn(async (url:string) => {
  if(url==='/api/v4/manager/research/workspace?date=20261016&view=auto') return await new Promise<Response>(resolve=>{complete=resolve;});
  return new Response(JSON.stringify({status:'CANNOT_CONFIRM',reason_codes:['MODULE_RESULT_NOT_AVAILABLE']}),{status:503});
 }));
 render(SavedManagerResultView);
 await screen.findByRole('alert');
 const input=screen.getByLabelText('目标交易日');
 await fireEvent.update(input,'2026-10-16');
 await fireEvent.click(screen.getByRole('button',{name:'按日期查找已保存运行'}));
 await fireEvent.update(input,'2026-10-17');
 complete(new Response(JSON.stringify({target_trade_date:'20261016',plan_product:{run_id:run,sha256:'b'.repeat(64),consumed:true}})));
 await waitFor(()=>expect(screen.getByText(/目标交易日已变更为 20261017/)).toBeTruthy());
 expect(new URLSearchParams(window.location.search).get('target_date')).toBe('20261017');
 expect(new URLSearchParams(window.location.search).get('run_id')).toBeNull();
 expect(screen.queryByText(/已找到日期匹配的引用/)).toBeNull();
 await fireEvent.update(screen.getByLabelText('目标交易日'),'2026-10-17');
 await fireEvent.click(screen.getByRole('button',{name:'按日期查找已保存运行'}));
 expect(await screen.findByText(/目标日 20261017 暂无可读取的已保存运行/)).toBeTruthy();
 await waitFor(()=>expect((screen.getByRole('button',{name:'按日期查找已保存运行'}) as HTMLButtonElement).disabled).toBe(false));
});

const manualRun='b'.repeat(32);
const deferredResponse=()=>{let resolve!:(value:Response)=>void;const promise=new Promise<Response>(r=>{resolve=r;});return {promise,resolve};};

it.each(['late-success','late-503','late-no-product','late-identity-mismatch','late-json'] as const)('manual run submission wins over %s date lookup',async mode=>{
 const lookup=deferredResponse();
 let finishJson!:(value:unknown)=>void;
 let jsonStarted!:()=>void;
 const jsonReady=new Promise<void>(r=>{jsonStarted=r;});
 const requests:string[]=[];
 const identity={run_id:manualRun,target_date:'20261015',plan_sha256:'a'.repeat(64),raw_sha256:'b'.repeat(64),response_sha256:'c'.repeat(64),input_identity:'d'.repeat(64)};
 const binding={identity,generation_id:'e'.repeat(64),profile_sha256:'f'.repeat(64),manifest_sha256:'1'.repeat(64)};
 const descriptor={...binding,schema_version:'v5.m18.v2.descriptor.v1',run_id:manualRun,target_date:'20261015',pages_route:'/api/v4/manager/m18/v2/pages',status:'READY',generated_at:'2026-10-15T00:00:00Z'};
 const overview={...binding,schema:'v5.m18.offline.v2.overview',content_chunks:1,sections:{stocks:{kind:'array',total:1,loaded_count:0,not_loaded_count:1,state:'NOT_LOADED'}}};
 const page={...binding,schema:'v5.m18.offline.v2.detail',section:'stocks',selection:null,cursor:null,offset:0,matched_total:1,not_loaded_count:0,remaining_entries:0,next_cursor:null,entries:[{index:0,kind:'object',offset:0,bytes:64,sha256:'2'.repeat(64),value_state:'LOADED',value:{symbol:'HK.B0001',name:'B股测试行',status:'READY'}}]};
 vi.stubGlobal('fetch',vi.fn(async(url:string)=>{
  requests.push(url);
  if(url==='/api/v4/manager/research/workspace?date=20261016&view=auto') return lookup.promise;
  if(url==='/api/v4/manager/m18/v2?run_id='+manualRun) return new Response(JSON.stringify(descriptor));
  if(url.startsWith('/api/v4/manager/m18/v2/overview?')) return new Response(JSON.stringify(overview));
  if(url.startsWith('/api/v4/manager/m18/v2/sections?')) return new Response(JSON.stringify(page));
  return new Response(JSON.stringify({status:'CANNOT_CONFIRM',reason_codes:['MODULE_RESULT_NOT_AVAILABLE']}),{status:503});
 }));
 render(SavedManagerResultView);
 await screen.findByRole('alert');
 const dateInput=screen.getByLabelText('目标交易日');
 await fireEvent.update(dateInput,'2026-10-16');
 await fireEvent.click(screen.getByRole('button',{name:'按日期查找已保存运行'}));
 if(mode==='late-json'){
  lookup.resolve({ok:true,status:200,json:()=>{jsonStarted();return new Promise(resolve=>{finishJson=resolve;});}} as Response);
  await jsonReady;
 }
 const runInput=screen.getByLabelText('运行 ID');
 await fireEvent.update(runInput,manualRun);
 await fireEvent.click(screen.getByRole('button',{name:'读取已保存结果'}));
 await waitFor(()=>expect(new URLSearchParams(window.location.search).get('run_id')).toBe(manualRun));
 expect(await screen.findByRole('row',{name:/HK\.B0001 · B股测试行/})).toBeTruthy();
 expect(screen.getAllByText('目标日 20261015').length).toBeGreaterThan(0);
 expect(screen.getByText('已切换到手动运行 ID 查询；先前日期查询已取消。')).toBeTruthy();
 if(mode!=='late-json'){
  if(mode==='late-503') lookup.resolve({ok:false,status:503,json:async()=>({})} as Response);
  if(mode==='late-no-product') lookup.resolve({ok:true,status:200,json:async()=>({target_trade_date:'20261016'})} as Response);
  if(mode==='late-identity-mismatch') lookup.resolve({ok:true,status:200,json:async()=>({target_trade_date:'20261015',plan_product:{run_id:'a'.repeat(32),sha256:'c'.repeat(64),consumed:true}})} as Response);
  if(mode==='late-success') lookup.resolve({ok:true,status:200,json:async()=>({target_trade_date:'20261016',plan_product:{run_id:'a'.repeat(32),sha256:'c'.repeat(64),consumed:true}})} as Response);
 } else finishJson({target_trade_date:'20261016',plan_product:{run_id:'a'.repeat(32),sha256:'c'.repeat(64),consumed:true}});
 await waitFor(()=>expect((screen.getByLabelText('运行 ID') as HTMLInputElement).value).toBe(manualRun));
 expect(new URLSearchParams(window.location.search).get('run_id')).toBe(manualRun);
 expect(screen.getByRole('alert').textContent).toContain('M18_HTTP_503');
 expect(screen.queryByText(/已找到日期匹配的引用/)).toBeNull();
});

it('shows an ordinary V5 page and keeps missing API results visibly unconfirmed', async () => {
 vi.stubGlobal('fetch',vi.fn(async () => new Response(JSON.stringify({status:'CANNOT_CONFIRM',reason_codes:['MODULE_RESULT_NOT_AVAILABLE']}),{status:503})));
 render(SavedManagerResultView);
 expect(screen.getByRole('heading',{name:'V5 经理选股'})).toBeTruthy();
 expect(await screen.findByRole('alert')).toHaveProperty('textContent',expect.stringContaining('CANNOT_CONFIRM'));
 expect(screen.getByRole('button',{name:'A 股阶段选股 · M07 已保存结果'})).toHaveProperty('disabled',false);
 expect(screen.getByRole('link',{name:'研报决策台'}).getAttribute('href')).toBe('?view=research');
 expect(screen.queryByRole('table')).toBeNull();
 expect(vi.mocked(fetch).mock.calls.filter(([url])=>String(url).startsWith('/api/v4/manager/m18/v2'))).toHaveLength(1);
 await fireEvent.click(screen.getByRole('button',{name:'源模块实际状态'}));
 expect(screen.getByRole('region',{name:'M17 收盘补采已保存观察'})).toBeTruthy();
});
it('opens consumed announcement references by default and reuses the stock reasons view', async () => {
 const run='46596b03c2ab4e29b1219fd2e5eb698f';
 const identity={run_id:run,target_date:'20261012',plan_sha256:'a'.repeat(64),raw_sha256:'b'.repeat(64),response_sha256:'c'.repeat(64),input_identity:'d'.repeat(64)};
 const binding={identity,generation_id:'e'.repeat(64),profile_sha256:'f'.repeat(64),manifest_sha256:'1'.repeat(64)};
 const descriptor={...binding,schema_version:'v5.m18.v2.descriptor.v1',run_id:run,target_date:'20261012',pages_route:'/api/v4/manager/m18/v2/pages',status:'READY',generated_at:'2026-10-12T00:00:00Z'};
 const overview={...binding,schema:'v5.m18.offline.v2.overview',content_chunks:5,sections:{announcement_reviewed_analysis:{kind:'object',total:1,loaded_count:0,not_loaded_count:1,state:'NOT_LOADED'},stocks:{kind:'array',total:0,loaded_count:0,not_loaded_count:0,state:'NOT_LOADED'},rebound_research_observation:{kind:'object',total:1,loaded_count:0,not_loaded_count:1,state:'NOT_LOADED'},us_mapping_research:{kind:'object',total:1,loaded_count:0,not_loaded_count:1,state:'NOT_LOADED'}}};
 const page={...binding,schema:'v5.m18.offline.v2.detail',section:'announcement_reviewed_analysis',projection:'announcement_references',selection:null,cursor:null,offset:0,matched_total:1,not_loaded_count:0,remaining_entries:0,next_cursor:null,
  announcement:{status:'READY',plan_cutoff:'2026-10-12T07:42:13+08:00',source_section_sha256:'2'.repeat(64),reference_count:1,gaps:[],products:[]},
  entries:[{index:0,kind:'object',offset:0,bytes:900,sha256:'3'.repeat(64),value_state:'LOADED',value:{stock_code:'01234',stock_name:'合成公告公司',research_status:'SELECTED',publication_date:'2026-10-09',target_trade_date:'20261012',point_in_time_status:'CANNOT_CONFIRM',connect_eligibility_status:'NOT_ASSESSED',selection_reasons:[{disposition:'SELECTED_EVENT',reason:'合成逐篇理由'}],risk_notes:['合成风险'],article_refs:[{art_code:'SYNTHETIC',title:'合成公告',source_sha256:'4'.repeat(64)}]}}]};
 const rebound={...page,section:'rebound_research_observation',projection:'rebound_references',group:'strict',announcement:undefined,
  rebound:{source_section_sha256:'5'.repeat(64),group_counts:{strict:1,near:0,pending:0,excluded:0,screen_unresolved:0},source:{status:'CANNOT_CONFIRM',eligible_screen:null,scope:'INDEPENDENT_READ_TIME_OBSERVATION_NOT_SAVED_PLAN_OR_FORMAL_SELECTION'},observation:{status:'CANNOT_CONFIRM',original_computation_status:'READY_WITH_GAPS',gaps:['SYNTHETIC_UNIT_UNVERIFIED']}},
  entries:[{...page.entries[0],value:{code:'04321',name:'合成超跌公司',classification:'STRICT_REBOUND',reason_for_group:'合成原分组理由',amount_native:12,volume_unit:'NOT_PROVEN',connect_eligibility:'UNVERIFIED',observed_session:'20261009',target_monday:'20261012'}}]};
 const usMapping={...page,section:'us_mapping_research',projection:'us_mapping_matches',announcement:undefined,
  us_mapping:{source_section_sha256:'6'.repeat(64),match_count:1,source:{orders_sent:false,registry_readback:{scope:'ORIGINAL_REVIEWED_RETROSPECTIVE_RESEARCH_NOT_CURRENT_SELECTION',seed_target_date:'20260930'}},daily_run:{status:'COMPLETED',target_trade_date:'20261012',us_session_date:'20261009',target_date_eligibility:'CANNOT_CONFIRM'},coverage_diagnostics:{schema_version:'v5.us_mapping_scope.v1',status:'PARTIAL',scope:'PINNED_REVIEWED_RELATIONS_WITHIN_CONFIGURED_US_SAMPLE',full_market_coverage:false,formal_eligible:false,natural_verified:false,reviewed_us_symbols:['SYNTHETIC_US'],reviewed_us_symbol_count:1,configured_sample_count:3,rising_individual_count:2,assessed_rising_symbol_count:1,unassessed_rising_symbol_count:1},plan_reference:{value_state:'NOT_LOADED',reason:'OWNER_CHAIN_MISSING'}},
  entries:[{...page.entries[0],value:{hk_symbol:'HK.09876',hk_name:'合成美股驱动公司',us_symbol:'SYNTHETIC_US',change_pct:1.25,relationship_type:'PRODUCT_PEER',reason:'合成原美股驱动理由',maturity:'合成产品阶段',limitations:['合成关系限制'],official_sources:[{title:'合成官方来源',url:'https://example.com/report'}]}}]};
 const requests:string[]=[];
 vi.stubGlobal('fetch',vi.fn(async (url:string)=>{requests.push(url);if(!url.startsWith('/api/v4/manager/m18/v2'))return new Response('{}',{status:503});let value:unknown=url.includes('/overview?')?overview:url.includes('/sections?')?page:descriptor;if(url.includes('projection=rebound_references'))value=url.includes('group=near')?{...rebound,group:'near',matched_total:0,entries:[]}:rebound;if(url.includes('projection=us_mapping_matches'))value=usMapping;return new Response(JSON.stringify(value));}));
 render(SavedManagerResultView);
 expect(await screen.findByRole('heading',{name:'01234 合成公告公司｜入选研究名单'})).toBeTruthy();
 expect(screen.getByText('入选事件研究：合成逐篇理由。')).toBeTruthy();
 expect(screen.getByText('风险/限制：合成风险')).toBeTruthy();
 expect(screen.getByText('历史 PIT：CANNOT_CONFIRM；互联互通资格：NOT_ASSESSED。')).toBeTruthy();
 expect(screen.getByRole('button',{name:'公告研究股票'}).getAttribute('aria-current')).toBe('page');
 const managerRequests=requests.filter(url=>url.startsWith('/api/v4/manager/m18/v2'));
 expect(managerRequests).toHaveLength(3);
 expect(managerRequests[2]).toContain('section=announcement_reviewed_analysis&projection=announcement_references');
 expect(screen.queryByRole('table')).toBeNull();
 expect(screen.getByRole('link',{name:'研报决策台'}).getAttribute('href')).toBe('?view=research');
 await fireEvent.click(screen.getByRole('button',{name:'超跌研究'}));
 expect(await screen.findByRole('heading',{name:'合成超跌公司 · 04321 · 严格条件研究观察'})).toBeTruthy();
 expect(screen.queryByRole('heading',{name:'01234 合成公告公司｜入选研究名单'})).toBeNull();
 expect(screen.getByText('原分类 STRICT_REBOUND；分组理由：合成原分组理由。')).toBeTruthy();
 expect(screen.getByText(/原生成交额 amount_native 12；币种 未知；成交额单位 未知；成交量单位 NOT_PROVEN/)).toBeTruthy();
 await fireEvent.click(screen.getByRole('button',{name:'近条件研究观察 · 0'}));
 expect(await screen.findByText('近条件研究观察原数组为 0 条，不代表正式资格已确认。')).toBeTruthy();
 expect(screen.queryByRole('heading',{name:'合成超跌公司 · 04321 · 严格条件研究观察'})).toBeNull();
 await fireEvent.click(screen.getByRole('button',{name:'美股驱动'}));
 expect(await screen.findByRole('heading',{name:'合成美股驱动公司 · HK.09876'})).toBeTruthy();
 expect(screen.getByText('合成原美股驱动理由')).toBeTruthy();
 expect(screen.getByText('产品同业（非供货关系）')).toBeTruthy();
 expect(screen.getByRole('link',{name:'合成官方来源'}).getAttribute('href')).toBe('https://example.com/report');
 expect(screen.getByText(/本页已读取 1 条关系 · 1 个港股主体/)).toBeTruthy();
 expect(screen.getByText(/本冻结响应的计划消费状态：NOT_LOADED/)).toBeTruthy();
 expect(screen.getByRole('button',{name:'美股驱动'}).getAttribute('aria-current')).toBe('page');
 expect(requests.at(-1)).toContain('section=us_mapping_research&projection=us_mapping_matches');
 await fireEvent.click(screen.getByRole('button',{name:'公告研究股票'}));
 expect(await screen.findByRole('heading',{name:'01234 合成公告公司｜入选研究名单'})).toBeTruthy();
 expect(screen.queryByRole('heading',{name:'合成美股驱动公司 · HK.09876'})).toBeNull();
 await fireEvent.update(screen.getByLabelText('目标交易日'),'2026-10-16');
 await fireEvent.click(screen.getByRole('button',{name:'按日期查找已保存运行'}));
 expect(await screen.findByText(/目标日 20261016 暂无可读取的已保存运行/)).toBeTruthy();
 expect(screen.queryByRole('heading',{name:'01234 合成公告公司｜入选研究名单'})).toBeNull();
 expect(screen.queryByRole('heading',{name:'合成超跌公司 · 04321 · 严格条件研究观察'})).toBeNull();
 expect(new URLSearchParams(window.location.search).get('run_id')).toBeNull();
});

