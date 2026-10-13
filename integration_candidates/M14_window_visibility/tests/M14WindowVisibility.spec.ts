import {afterEach, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, waitFor} from '@testing-library/vue';
import M14SavedRebound from './M14SavedRebound.vue';
import {saved} from '../../tests/m14SavedReboundFixtures.mjs';
afterEach(()=>{cleanup();vi.unstubAllGlobals();});
async function show(value: ReturnType<typeof saved>) {
 vi.stubGlobal('fetch',vi.fn(async()=>new Response(JSON.stringify(value))));const view=render(M14SavedRebound);
 const details=view.container.querySelector<HTMLDetailsElement>('#m14-saved-rebound')!;details.open=true;await fireEvent(details,new Event('toggle'));
 await waitFor(()=>expect(view.queryByRole('region',{name:'M14 已保存同源窗口证据'})).not.toBeNull());return view;
}
it('shows exact saved cutoff, panel coverage and all saved pending reason counts without formal eligibility',async()=>{
 const value=saved();value.rebound.observation.coverage={panel_row_count:40930,panel_code_count:690};
 const pending: Record<string,string[]>={};for(let i=1;i<=688;i++)pending[`HK.${String(i).padStart(5,'0')}`]=['PRIOR60_KEYS_MISSING'];pending['HK.00689']=['SOURCE_ROW_INVALID'];pending['HK.00690']=['SOURCE_ROW_INVALID'];
 value.rebound.observation.native_evidence={research_cutoff:'2026-10-13T18:40:58.776354Z',source_contract:{name:'SYNTHETIC_SAME_SOURCE',provider:'PYTDX_EXHQ_SDK',interface:'get_instrument_bars',volume_unit:null,price_basis:'NOT_PROVEN',provider_finality:'NOT_ATTESTED'},pending_reasons:pending};
 const view=await show(value);const section=view.getByRole('region',{name:'M14 已保存同源窗口证据'});expect(section.textContent).toContain('2026-10-13T18:40:58.776354Z');expect(section.textContent).toContain('40930');expect(section.textContent).toContain('688 只');expect(section.textContent).toContain('2 只');expect(section.textContent).toContain('不表示正式条件通过');expect(section.querySelector('details')?.open).toBe(false);expect(section.textContent).not.toContain('20260925');
});
it('leaves unavailable evidence unknown rather than inventing zero or complete history',async()=>{
 const value=saved();value.rebound.observation.native_evidence={};value.rebound.observation.coverage={};const view=await show(value);const section=view.getByRole('region',{name:'M14 已保存同源窗口证据'});expect(section.textContent).toContain('未知（原保存结果未提供）');expect(section.textContent).toContain('不据此判断没有缺口');expect(section.textContent).not.toContain('0 只');
});
