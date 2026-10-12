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
