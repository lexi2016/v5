import {cleanup,fireEvent,render,screen,waitFor} from '@testing-library/vue';
import {afterEach,expect,it,vi} from 'vitest';
import Root from './Root.vue';
afterEach(()=>{cleanup();vi.unstubAllGlobals();history.replaceState(null,'','/');});
function fakeReader() {
 const calls:string[]=[];
 vi.stubGlobal('fetch',vi.fn(async(url:string)=>{calls.push(url);const d=new URL(url,'http://localhost').searchParams.get('research_date')||'20261012';return {ok:true,json:async()=>({schema_version:'v3_5.research_lane.v1',research_date:d,endpoint_mode:'EXACT',status:'NOT_MATERIALIZED',reason:'TEST_NO_SAVED_DATE',cannot_confirm:['TEST_NO_SAVED_DATE'],write_policy:'read_only',recommendation_status:'RESEARCH_ONLY',production_allowed:false,buy_gate_updated:false,orders_sent:false})};}));
 return calls;
}
it('opens the selected natural date using only the dedicated V5 research route',async()=>{
 history.replaceState(null,'','/?view=research&date=20261012');const calls=fakeReader();render(Root);
 await screen.findByText('TEST_NO_SAVED_DATE');
 expect(calls).toEqual(['/api/v5/research/lane?research_date=20261012']);
 expect((screen.getByLabelText('研究自然日') as HTMLInputElement).value).toBe('2026-10-12');
 expect(screen.getByRole('link',{name:'经理已保存结果'}).getAttribute('href')).toBe('?');
});
it('date changes and browser history read exact dates without starting other modules',async()=>{
 history.replaceState(null,'','/?view=research&date=20261012');const calls=fakeReader();render(Root);
 await screen.findByText('TEST_NO_SAVED_DATE');
 await fireEvent.change(screen.getByLabelText('研究自然日'),{target:{value:'2026-10-13'}});
 await waitFor(()=>expect(calls.at(-1)).toBe('/api/v5/research/lane?research_date=20261013'));
 history.replaceState(null,'','/?view=research&date=20261011');window.dispatchEvent(new PopStateEvent('popstate'));
 await waitFor(()=>expect(calls.at(-1)).toBe('/api/v5/research/lane?research_date=20261011'));
 expect(calls.every(x=>x.startsWith('/api/v5/research/'))).toBe(true);
});
