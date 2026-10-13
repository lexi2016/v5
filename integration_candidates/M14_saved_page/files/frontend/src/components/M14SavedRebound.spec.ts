import {afterEach, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, waitFor} from '@testing-library/vue';
import M14SavedRebound from './M14SavedRebound.vue';
import {saved, waiting, reference} from '../../tests/m14SavedReboundFixtures.mjs';
const response = (value: unknown) => new Response(JSON.stringify(value));
afterEach(() => {cleanup(); vi.unstubAllGlobals();});
async function open(view: ReturnType<typeof render>) {
 const details = view.container.querySelector<HTMLDetailsElement>('#m14-saved-rebound')!;
 details.open = true; await fireEvent(details, new Event('toggle')); return details;
}
it('loads lazily, shows all five original counts and dates, and escapes saved row text', async () => {
 const value = saved('pending', 0, 1);
 value.entries[0].value = {code: 'SYNTHETIC_ONLY', name: '<script>test</script>', observed_session: 20261009, target_monday: 20261012, history_unknown_reasons: ['SYNTHETIC_HISTORY_MISSING']};
 const fetcher = vi.fn(async () => response(value)); vi.stubGlobal('fetch', fetcher);
 const view = render(M14SavedRebound); expect(fetcher).not.toHaveBeenCalled(); const details = await open(view);
 await waitFor(() => expect(view.container.textContent).toContain('SYNTHETIC_ONLY'));
 expect(view.container.querySelector('script')).toBeNull(); expect(view.container.textContent).toContain('<script>test</script>');
 expect(view.container.textContent).toContain('保存信号日 2026-10-09 · 目标日 2026-10-12');
 expect(view.getByRole('button', {name: '待核数据/历史 · 1'}).getAttribute('aria-pressed')).toBe('true');
 expect(view.getByRole('button', {name: '严格条件研究观察 · 0'})).toBeTruthy();
 expect(view.getByRole('button', {name: '近条件研究观察 · 0'})).toBeTruthy();
 expect(view.getByRole('button', {name: '已排除观察 · 0'})).toBeTruthy();
 expect(view.getByRole('button', {name: '未决观察 · 0'})).toBeTruthy();
 for (const token of ['SYNTHETIC_HISTORY_MISSING', '60', 'natural_verified=false', 'formal_eligibility_verified=false', reference.run_id]) expect(view.container.textContent).toContain(token);
 details.open = false; await fireEvent(details, new Event('toggle')); await open(view); expect(fetcher).toHaveBeenCalledTimes(1);
});
it('pins pagination and group changes, clears old rows while loading, and distinguishes empty from WAITING', async () => {
 const requests: string[] = [];
 let resolve!: (response: Response) => void;
 vi.stubGlobal('fetch', vi.fn(async (url: string) => {
  requests.push(url); const query = new URL(url, 'http://fixture.invalid').searchParams;
  if (requests.length === 1) return response(saved());
  if (query.has('cursor')) return new Promise<Response>(done => {resolve = done;});
  return response(query.has('run_id') ? saved('strict') : waiting());
 }));
 const view = render(M14SavedRebound); await open(view);
 await waitFor(() => expect(view.container.textContent).toContain('SYNTHETIC_ONLY_0'));
 await fireEvent.click(view.getByRole('button', {name: 'M14 下一页'}));
 expect(view.container.textContent).not.toContain('SYNTHETIC_ONLY_0'); expect(view.container.textContent).not.toContain(reference.run_id);
 resolve(response(saved('pending', 32))); await waitFor(() => expect(view.container.textContent).toContain('SYNTHETIC_ONLY_32'));
 const query = new URL(requests[1], 'http://fixture.invalid').searchParams;
 for (const [key, value] of Object.entries(reference)) expect(query.get(key)).toBe(value);
 expect(view.getByRole('button', {name: 'M14 上一页'})).not.toHaveProperty('disabled', true);
 await fireEvent.click(view.getByRole('button', {name: '严格条件研究观察 · 0'}));
 await waitFor(() => expect(view.container.textContent).toContain('原数组为 0 条'));
 expect(view.container.textContent).not.toContain('SYNTHETIC_ONLY_32');
 await fireEvent.click(view.getByRole('button', {name: '重新读取 M14 配置引用'}));
 await waitFor(() => expect(view.container.textContent).toContain('M14_SAVED_REFERENCE_NOT_CONFIGURED'));
 expect(view.container.textContent).not.toContain('原数组为 0 条'); expect(view.container.textContent).not.toContain(reference.run_id);
});
it('failed group reads clear evidence and unmount aborts the pending request', async () => {
 let reject!: (reason: Error) => void; let signal: AbortSignal | null | undefined;
 vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(response(saved())).mockImplementation((_url: string, init?: RequestInit) => {
  signal = init?.signal; return new Promise<Response>((_resolve, fail) => {reject = fail;});
 }));
 const view = render(M14SavedRebound); await open(view);
 await waitFor(() => expect(view.container.textContent).toContain('SYNTHETIC_ONLY_0'));
 await fireEvent.click(view.getByRole('button', {name: '近条件研究观察 · 0'})); reject(new Error('/private/test'));
 await waitFor(() => expect(view.getByRole('alert').textContent).toContain('M14_READ_FAILED'));
 expect(view.container.textContent).not.toContain('/private/test'); expect(view.container.textContent).not.toContain('SYNTHETIC_ONLY_0');
 await fireEvent.click(view.getByRole('button', {name: '重新读取 M14 配置引用'})); view.unmount(); expect(signal?.aborted).toBe(true);
 reject(new DOMException('Aborted', 'AbortError'));
});
