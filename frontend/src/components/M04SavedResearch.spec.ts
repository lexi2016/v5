import {afterEach,expect,it,vi} from 'vitest';
import {cleanup,fireEvent,render,waitFor} from '@testing-library/vue';
import M04SavedResearch from './M04SavedResearch.vue';
const flags={research_only:true,natural_verified:false,historical_pit_claimed:false,formal_eligibility_verified:false,production_allowed:false,buy_gate_updated:false,orders_sent:false};
function fixture(){return {schema_version:'v5.m04_saved_research.v1',module_id:'M04_RESEARCH_INTELLIGENCE',status:'SAVED_HISTORICAL_SAMPLE',data_kind:'RECORDED_INPUT_REPLAY',coverage_scope:'FIXED_18_ARTICLE_SAMPLE',article_count:18,pit:'UNKNOWN',missing_retrieved_at:18,missing_available_at:18,out_of_sample_record_errors:53,reference:{archive_date:'20261012',source_slot:'2100',source_run_id:'hip-49cb26f7f3a0661bde1d1440',publication_time_is_not_article_availability:true},archive:{archive_date:'20261012',article_count:18,articles:Array.from({length:18},(_,i)=>({article_id:String(i),source_title:`SYNTHETIC ${i} <script>alert(1)</script>`,evidence_sentence:'Synthetic original evidence',retrieved_at:null,available_at:null})),production_allowed:false,buy_gate_updated:false,orders_sent:false},...flags};}
afterEach(()=>{cleanup();vi.unstubAllGlobals();});
it('lazy disclosure reads 18 original rows, renders text safely and preserves the historical boundary',async()=>{
 const fetcher=vi.fn(async()=>new Response(JSON.stringify(fixture())));vi.stubGlobal('fetch',fetcher);
 const view=render(M04SavedResearch);expect(fetcher).not.toHaveBeenCalled();
 const details=view.container.querySelector<HTMLDetailsElement>('#m04-saved-research')!;details.open=true;await fireEvent(details,new Event('toggle'));
 await waitFor(()=>expect(view.container.querySelectorAll('.m04-articles>li')).toHaveLength(18));
 expect(view.container.querySelector('script')).toBeNull();expect(view.container.textContent).toContain('<script>alert(1)</script>');
 expect(view.container.textContent).toContain('PIT UNKNOWN');expect(view.container.textContent).toContain('18/18 缺 retrieved_at');expect(view.container.textContent).toContain('样本外读取错误：53');
 details.open=false;await fireEvent(details,new Event('toggle'));details.open=true;await fireEvent(details,new Event('toggle'));expect(fetcher).toHaveBeenCalledTimes(1);
});
it('failed refresh removes all previous rows and exposes a recoverable error',async()=>{
 const fetcher=vi.fn().mockResolvedValueOnce(new Response(JSON.stringify(fixture()))).mockResolvedValueOnce(new Response('{}',{status:503}));vi.stubGlobal('fetch',fetcher);
 const view=render(M04SavedResearch);await fireEvent.click(view.getByRole('button',{name:'重新读取 M04 已保存样本',hidden:true}));await waitFor(()=>expect(view.container.querySelectorAll('.m04-articles>li')).toHaveLength(18));
 await fireEvent.click(view.getByRole('button',{name:'重新读取 M04 已保存样本',hidden:true}));await waitFor(()=>expect(view.container.textContent).toContain('M04_HTTP_503'));expect(view.container.querySelectorAll('.m04-articles>li')).toHaveLength(0);
});
