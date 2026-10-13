import {afterEach,expect,it,vi} from 'vitest';
import {cleanup,fireEvent,render,waitFor} from '@testing-library/vue';
import SavedManagerResultView from './SavedManagerResultView.vue';
afterEach(()=>{cleanup();vi.unstubAllGlobals();});
it('M11 homepage navigation opens real lazy saved research and focuses it without replacing M04/M12',async()=>{
 const slots=['09:25','09:35','10:00','11:30','14:00','15:00'];
 const fixture={schema_version:'v5.m11_saved_research.v1',module_id:'M11_INTRADAY_RESEARCH',status:'SAVED_RESEARCH_REVIEW_REQUIRED',data_kind:'SYNTHETIC',research_only:true,natural_verified:false,review_completed:false,production_allowed:false,buy_gate_updated:false,orders_sent:false,reason_codes:['RESEARCH_REVIEW_REQUIRED'],reference:{trade_date:'20261012',run_id:'synthetic-capture',commit_sha256:'a'.repeat(64),operation:'capture',slot:'09:25'},evidence_status:'VERIFIED_PERSISTENCE_ONLY',business_status:'PARTIAL',research:{intraday_research:{status:'PARTIAL',cannot_confirm:['Synthetic original intraday research']}},slots:slots.map(slot=>({slot,status:slot==='09:25'?'SAVED':'WAITING'}))};
 const calls:string[]=[];vi.stubGlobal('fetch',vi.fn(async(url:string)=>{calls.push(url);return url.startsWith('/api/v5/source-bundle/intraday-research')?new Response(JSON.stringify(fixture)):new Response('{}',{status:503});}));
 const view=render(SavedManagerResultView);const source=view.container.querySelector<HTMLDetailsElement>('#source-module-content')!;const video=view.container.querySelector<HTMLDetailsElement>('#m12-saved-video')!;
 expect(source.open).toBe(false);expect(video.open).toBe(false);expect(calls.filter(x=>x.includes('/intraday-research'))).toHaveLength(0);
 await fireEvent.click(view.getByRole('button',{name:'盘中研究 · M11'}));
 const target=view.container.querySelector<HTMLDetailsElement>('#m11-saved-research')!;
 await waitFor(()=>expect(target.open).toBe(true));await waitFor(()=>expect(view.queryByTestId('m11-saved-content')).not.toBeNull());
 expect(document.activeElement).toBe(target.querySelector('summary'));expect(source.open).toBe(false);expect(video.open).toBe(false);expect(view.container.textContent).toContain('Synthetic original intraday research');
 expect(view.getByRole('button',{name:'研究情报 · M04'})).toBeTruthy();expect(view.getByRole('button',{name:'视频复盘 · M12'})).toBeTruthy();expect(view.container.querySelector('#saved-result-content')).toBeTruthy();
 expect(calls.filter(x=>x.includes('/intraday-research'))).toEqual(['/api/v5/source-bundle/intraday-research']);
});
it('M11 navigation remains useful for unconfigured evidence while manager fetch fails',async()=>{vi.stubGlobal('fetch',vi.fn(async(url:string)=>url.includes('/intraday-research')?new Response(JSON.stringify({schema_version:'v5.m11_saved_research.v1',module_id:'M11_INTRADAY_RESEARCH',status:'WAITING',reason_codes:['M11_SAVED_REFERENCE_NOT_CONFIGURED'],research_only:true,natural_verified:false,review_completed:false,production_allowed:false,buy_gate_updated:false,orders_sent:false})):new Response('{}',{status:503})));const view=render(SavedManagerResultView);await fireEvent.click(view.getByRole('button',{name:'盘中研究 · M11'}));await waitFor(()=>expect(view.container.textContent).toContain('M11_SAVED_REFERENCE_NOT_CONFIGURED'));expect(view.queryByTestId('m11-saved-content')).toBeNull();});
