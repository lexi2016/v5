import {afterEach, expect, it, vi} from 'vitest';
import {cleanup, fireEvent, render, waitFor} from '@testing-library/vue';
import M16SavedResearch from './M16SavedResearch.vue';

const flags = {read_only: true, can_execute: false, research_only: true, natural_verified: false, production_allowed: false, buy_gate_updated: false, orders_sent: false};
const fixture = () => ({
  schema_version: 'v5.m16_saved_public_research.v1', module_id: 'M16_PUBLIC_RESEARCH',
  status: 'SAVED_PUBLIC_RESEARCH_REVIEW_REQUIRED', mode: 'READ_ONLY_SAVED_RESULT',
  data_kind: 'SYNTHETIC', evidence_status: 'VERIFIED_PERSISTENCE_ONLY', business_status: 'PARTIAL_WITH_ROWS',
  reference: {trade_date: '20261012', input_identity: '1'.repeat(64), job_id: 'synthetic-public-research', generation: 'generation-1', attempt: 1, commit_sha256: '2'.repeat(64), commit_file_sha256: '6'.repeat(64), product_sha256: '3'.repeat(64), job_sha256: '4'.repeat(64), receipt_sha256: '5'.repeat(64)},
  product: {kind: 'MANAGER_RESEARCH_PRODUCT', status: 'PARTIAL_WITH_ROWS', rows: [{code: '000001', name: '合成公司', status: 'CANNOT_CONFIRM', facts: [{statement_cn: 'SYNTHETIC <script>alert(1)</script>', source: 'saved-fixture'}], thesis_cn: '合成财务正文', counterevidence_cn: ['NO_NATURAL_VERIFICATION'], confirmation_conditions: ['合成确认条件']}]},
  job: {status: 'PARTIAL_WITH_ROWS'}, receipt: {status: 'PARTIAL_WITH_ROWS'}, reason_codes: ['PUBLIC_RESEARCH_REVIEW_REQUIRED'], ...flags,
});
const waiting = (status = 'WAITING') => ({schema_version: 'v5.m16_saved_public_research.v1', module_id: 'M16_PUBLIC_RESEARCH', status, mode: 'READ_ONLY_SAVED_RESULT', reason_codes: [status === 'WAITING' ? 'M16_SAVED_REFERENCE_NOT_CONFIGURED' : 'M16_SAVED_ARTIFACT_INVALID'], ...flags});
const response = (value: unknown) => new Response(JSON.stringify(value));
afterEach(() => {cleanup(); vi.unstubAllGlobals(); window.history.replaceState({}, '', '/');});

it('loads lazily, escapes saved facts and exposes original financial research with honest labels', async () => {
  const requests: string[] = [];
  vi.stubGlobal('fetch', vi.fn(async (url: string) => {requests.push(url); return response(fixture());}));
  const view = render(M16SavedResearch);
  expect(requests).toHaveLength(0);
  const details = view.container.querySelector('details')!; details.open = true;
  await fireEvent(details, new Event('toggle'));
  await waitFor(() => expect(view.queryByTestId('m16-saved-content')).not.toBeNull());
  expect(requests).toEqual(['/api/v5/source-bundle/manager-public-research']);
  expect(view.container.querySelector('script')).toBeNull();
  expect(view.container.textContent).toContain('<script>alert(1)</script>');
  expect(view.container.textContent).toContain('合成测试资料');
  expect(view.container.textContent).toContain('VERIFIED_PERSISTENCE_ONLY');
  expect(view.container.textContent).toContain('业务原状态：PARTIAL_WITH_ROWS');
  const row = view.getByTestId('m16-research-row');
  expect(row.textContent).toContain('000001 · 合成公司');
  expect(row.textContent).toContain('CANNOT_CONFIRM');
  expect(row.textContent).toContain('合成财务正文');
  expect(row.textContent).toContain('saved-fixture');
  expect(row.textContent).toContain('NO_NATURAL_VERIFICATION');
  expect(row.textContent).toContain('合成确认条件');
  expect(view.container.textContent).toContain('commit_sha256（规范化对象摘要）');
  expect(view.container.textContent).toContain('commit_file_sha256（原文件摘要）');
  expect(view.container.textContent).toContain('synthetic-public-research');
  expect(view.container.textContent).toContain('generation-1');
  expect(view.container.textContent).toContain('1'.repeat(64));
});
it('restores the selected date from the URL and persists it when submitting', async () => {
  window.history.replaceState({}, '', '/?m16_date=20261012');
  const fetcher = vi.fn(async () => response(waiting()));
  vi.stubGlobal('fetch', fetcher);
  const first = render(M16SavedResearch);
  const input = first.getByLabelText('M16 交易日', {hidden: true}) as HTMLInputElement;
  expect(input.type).toBe('date');
  expect(input.value).toBe('2026-10-12');
  await fireEvent.update(input, '2026-10-13');
  await fireEvent.click(first.getByRole('button', {name: '读取 M16 已保存研究', hidden: true}));
  await waitFor(() => expect(fetcher).toHaveBeenCalledWith('/api/v5/source-bundle/manager-public-research?trade_date=20261013', expect.any(Object)));
  expect(new URLSearchParams(window.location.search).get('m16_date')).toBe('20261013');
  first.unmount();
  const second = render(M16SavedResearch);
  expect((second.getByLabelText('M16 交易日', {hidden: true}) as HTMLInputElement).value).toBe('2026-10-13');
});

it('keeps missing bindings WAITING and invalid artifacts CANNOT_CONFIRM without saved content', async () => {
  for (const status of ['WAITING', 'CANNOT_CONFIRM']) {
    vi.stubGlobal('fetch', vi.fn(async () => response(waiting(status))));
    const view = render(M16SavedResearch);
    await fireEvent.click(view.getByRole('button', {name: '读取 M16 已保存研究', hidden: true}));
    await waitFor(() => expect(view.container.textContent).toContain(status === 'WAITING' ? 'M16_SAVED_REFERENCE_NOT_CONFIGURED' : 'M16_SAVED_ARTIFACT_INVALID'));
    expect(view.queryByTestId('m16-saved-content')).toBeNull();
    expect(view.queryByTestId('m16-research-row')).toBeNull();
    view.unmount();
  }
});
it('clears old rows during a new date read, rejects failures and leaves a working retry', async () => {
  let complete!: (value: Response) => void;
  const fetcher = vi.fn().mockResolvedValueOnce(response(fixture())).mockImplementationOnce(() => new Promise(resolve => {complete = resolve;})).mockResolvedValueOnce(response({...waiting(), requested_trade_date: '20261013'}));
  vi.stubGlobal('fetch', fetcher);
  const view = render(M16SavedResearch);
  const button = view.getByRole('button', {name: '读取 M16 已保存研究', hidden: true});
  await fireEvent.click(button);
  await waitFor(() => expect(view.queryByTestId('m16-saved-content')).not.toBeNull());
  await fireEvent.update(view.getByLabelText('M16 交易日'), '2026-10-13');
  await fireEvent.click(button);
  expect(view.queryByTestId('m16-saved-content')).toBeNull();
  expect(view.queryByTestId('m16-research-row')).toBeNull();
  complete(new Response('{}', {status: 503}));
  await waitFor(() => expect(view.container.textContent).toContain('M16_HTTP_503'));
  await fireEvent.click(button);
  await waitFor(() => expect(view.container.textContent).toContain('M16_SAVED_REFERENCE_NOT_CONFIGURED'));
  expect(fetcher.mock.calls[2][0]).toBe('/api/v5/source-bundle/manager-public-research?trade_date=20261013');
});
it('ignores an older date response after the new date and aborts pending work on unmount', async () => {
  const calls: {resolve: (value: Response) => void; signal: AbortSignal}[] = [];
  vi.stubGlobal('fetch', vi.fn((url: string, init: RequestInit) => new Promise<Response>(resolve => calls.push({resolve, signal: init.signal as AbortSignal}))));
  const view = render(M16SavedResearch);
  const button = view.getByRole('button', {name: '读取 M16 已保存研究', hidden: true});
  await fireEvent.update(view.getByLabelText('M16 交易日'), '2026-10-12'); await fireEvent.click(button);
  await fireEvent.update(view.getByLabelText('M16 交易日'), '2026-10-13'); await fireEvent.click(button);
  expect(calls[0].signal.aborted).toBe(true);
  calls[1].resolve(response({...waiting(), requested_trade_date: '20261013'}));
  await waitFor(() => expect(view.container.textContent).toContain('M16_SAVED_REFERENCE_NOT_CONFIGURED'));
  calls[0].resolve(response(fixture())); await new Promise(resolve => setTimeout(resolve, 0));
  expect(view.queryByTestId('m16-saved-content')).toBeNull();
  await fireEvent.click(button); view.unmount(); expect(calls[2].signal.aborted).toBe(true);
  calls[2].resolve(response({...waiting(), requested_trade_date: '20261013'}));
});
it('keeps saved business CANNOT_CONFIRM visible without claiming completed natural research', async () => {
  const value = fixture(); value.data_kind = 'OWNER_RESULT'; value.business_status = value.product.status = 'CANNOT_CONFIRM';
  vi.stubGlobal('fetch', vi.fn(async () => response(value)));
  const view = render(M16SavedResearch);
  await fireEvent.click(view.getByRole('button', {name: '读取 M16 已保存研究', hidden: true}));
  await waitFor(() => expect(view.queryByTestId('m16-saved-content')).not.toBeNull());
  expect(view.container.textContent).toContain('业务原状态：CANNOT_CONFIRM');
  expect(view.container.textContent).toContain('不代表真实业务完成');
  expect(view.container.textContent).toContain('OWNER_RESULT');
  expect(view.container.querySelectorAll('button')).toHaveLength(1);
});
