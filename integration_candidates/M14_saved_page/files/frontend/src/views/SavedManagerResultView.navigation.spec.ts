import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/vue';
import { flushPromises } from '@vue/test-utils';
import SavedManagerResultView from './SavedManagerResultView.vue';

// Synthetic transport fixtures exercise the real SavedRunSession and view.
// No production source module, session method or renderer is replaced.
const run = '46596b03c2ab4e29b1219fd2e5eb698f';
const identity = { run_id: run, target_date: '20261012', plan_sha256: 'a'.repeat(64), raw_sha256: 'b'.repeat(64), response_sha256: 'c'.repeat(64), input_identity: 'd'.repeat(64) };
const binding = { identity, generation_id: 'e'.repeat(64), profile_sha256: 'f'.repeat(64), manifest_sha256: '1'.repeat(64) };
const descriptor = { ...binding, schema_version: 'v5.m18.v2.descriptor.v1', run_id: run, target_date: identity.target_date, pages_route: '/api/v4/manager/m18/v2/pages', status: 'READY', generated_at: '2026-10-12T00:00:00Z' };
const sectionNames = ['announcement_reviewed_analysis', 'stocks', 'gaps', 'materials', 'rebound_research_observation', 'us_mapping_research'];
const overview = { ...binding, schema: 'v5.m18.offline.v2.overview', content_chunks: 5, sections: Object.fromEntries(sectionNames.map(key => [key, { kind: 'array', total: key === 'stocks' ? 1 : 0, loaded_count: 0, not_loaded_count: key === 'stocks' ? 1 : 0, state: 'NOT_LOADED' }])) };
function sectionPage(section: string, group = 'strict') {
  const page: Record<string, unknown> = { ...binding, schema: 'v5.m18.offline.v2.detail', section, selection: null, cursor: null, offset: 0, matched_total: 0, not_loaded_count: 0, remaining_entries: 0, next_cursor: null, entries: [] };
  if (section === 'stocks') Object.assign(page, { matched_total: 1, entries: [{ index: 0, kind: 'object', offset: 0, bytes: 100, sha256: '2'.repeat(64), value_state: 'LOADED', value: { code: 'SYNTHETIC_ONLY', name: '合成经理股票', status: 'PARTIAL', gaps: ['合成缺口保留'] } }] });
  if (section === 'announcement_reviewed_analysis') Object.assign(page, { projection: 'announcement_references', announcement: { status: 'PARTIAL', plan_cutoff: '2026-10-12T00:00:00Z', source_section_sha256: '3'.repeat(64), reference_count: 0, gaps: ['SYNTHETIC_GAP'], products: [] } });
  if (section === 'rebound_research_observation') Object.assign(page, { projection: 'rebound_references', group, rebound: { source_section_sha256: '4'.repeat(64), group_counts: { strict: 0, near: 0, pending: 0, excluded: 0, screen_unresolved: 0 }, source: {}, observation: { status: 'CANNOT_CONFIRM' } } });
  if (section === 'us_mapping_research') Object.assign(page, { projection: 'us_mapping_matches', us_mapping: { source_section_sha256: '5'.repeat(64), match_count: 0, source: {}, daily_run: {}, coverage_diagnostics: null, plan_reference: { value_state: 'NOT_LOADED', reason: 'SYNTHETIC_MISSING' } } });
  return page;
}
function transport(sectionOverride?: (url: URL) => Promise<Response> | undefined) {
  const requests: string[] = [];
  vi.stubGlobal('fetch', vi.fn(async (input: string) => {
    requests.push(input);
    if (!input.startsWith('/api/v4/manager/m18/v2')) return new Response('{}', { status: 503 });
    const url = new URL(input, window.location.origin);
    if (url.pathname.endsWith('/sections')) {
      const override = sectionOverride?.(url);
      if (override) return override;
      return new Response(JSON.stringify(sectionPage(url.searchParams.get('section')!, url.searchParams.get('group') ?? 'strict')));
    }
    return new Response(JSON.stringify(url.pathname.endsWith('/overview') ? overview : descriptor));
  }));
  return requests;
}
const scroll = vi.fn();
const originalScroll = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'scrollIntoView');
beforeEach(() => {
  window.history.replaceState(null, '', '/?run_id=' + run);
  scroll.mockClear();
  Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', { configurable: true, value: scroll });
});
afterEach(() => {
  cleanup(); vi.unstubAllGlobals();
  if (originalScroll) Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', originalScroll);
  else delete (HTMLElement.prototype as Partial<HTMLElement>).scrollIntoView;
  window.history.replaceState(null, '', '/');
});
async function ready() {
  await screen.findByRole('combobox', { name: '内容分区' });
  await waitFor(() => expect(screen.queryByText('正在读取同一运行的有界数据页…')).toBeNull());
}

it('puts saved results before collapsed, still-mounted source modules with verified run and date', async () => {
  transport();
  const { container } = render(SavedManagerResultView);
  await ready();
  const results = container.querySelector('#saved-result-content')!;
  const sources = container.querySelector<HTMLDetailsElement>('#source-module-content')!;
  expect(results).toBeTruthy(); expect(sources).toBeTruthy();
  expect(results.compareDocumentPosition(sources) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  expect(sources.open).toBe(false);
  expect(sources.querySelector('.source-status')).toBeTruthy();
  expect(screen.getByRole('heading', { name: '公告研究股票', level: 2 })).toBeTruthy();
  expect(screen.getByText('已读取运行 ' + run)).toBeTruthy();
  expect(results.textContent).toContain('目标日 20261012');
  const m07Button = screen.getByRole('button', { name: 'A 股阶段选股 · M07 已保存结果' });
  expect(m07Button).toBeTruthy();
  expect(m07Button).not.toHaveProperty('disabled', true);
  expect(scroll).not.toHaveBeenCalled();
  await fireEvent.click(m07Button);

  const m07Stage = container.querySelector<HTMLDetailsElement>('#m07-saved-stage');
  await waitFor(() => expect(m07Stage?.open).toBe(true));
  expect(m07Stage).toBeTruthy();
  expect(screen.getByText('研报决策台 · 未接入')).toHaveProperty('disabled', true);
});

it('opens and focuses the complete source disclosure without remounting its requests', async () => {
  const requests = transport();
  const { container } = render(SavedManagerResultView);
  await ready();
  const initialSourceReads = requests.filter(url => !url.startsWith('/api/v4/manager/m18/v2')).length;
  const button = screen.getByRole('button', { name: '源模块实际状态' });
  await fireEvent.click(button);
  const sources = container.querySelector<HTMLDetailsElement>('#source-module-content')!;
  await waitFor(() => expect(sources.open).toBe(true));
  expect(document.activeElement).toBe(sources.querySelector('summary'));
  expect(button.getAttribute('aria-expanded')).toBe('true');
  expect(screen.getByRole('region', { name: 'M17 收盘补采已保存观察' })).toBeTruthy();
  sources.open = false; await fireEvent(sources, new Event('toggle'));
  await fireEvent.click(button);
  expect(requests.filter(url => !url.startsWith('/api/v4/manager/m18/v2'))).toHaveLength(initialSourceReads);
  expect(scroll).toHaveBeenCalled();
});

it('moves all four result entries to their actual heading and retains the requested run', async () => {
  const requests = transport(); render(SavedManagerResultView); await ready();
  for (const [button, heading] of [['经理已保存结果', '经理候选股票'], ['经理同次运行超跌引用', '反弹研究观察'], ['美股驱动', '美股与港股映射'], ['公告研究股票', '公告研究股票']]) {
    await fireEvent.click(screen.getByRole('button', { name: button }));
    await waitFor(() => expect(document.activeElement).toBe(screen.getByRole('heading', { name: heading, level: 2 })));
    await ready();
    expect(screen.getByRole('button', { name: button }).getAttribute('aria-current')).toBe('page');
    expect(requests.at(-1)).toContain('run_id=' + run);
  }
  expect(scroll).toHaveBeenCalledTimes(4);
});

it('makes content selection, gaps and materials shortcuts focus the same result heading', async () => {
  transport(); render(SavedManagerResultView); await ready();
  await fireEvent.change(screen.getByRole('combobox', { name: '内容分区' }), { target: { value: 'stocks' } });
  await waitFor(() => expect(document.activeElement).toBe(screen.getByRole('heading', { name: '经理候选股票', level: 2 })));
  expect(await screen.findByText('SYNTHETIC_ONLY · 合成经理股票')).toBeTruthy();
  await fireEvent.click(screen.getByRole('button', { name: '查看缺口 · 0' }));
  await waitFor(() => expect(document.activeElement).toBe(screen.getByRole('heading', { name: '数据与证据缺口', level: 2 })));
  await fireEvent.click(screen.getByRole('button', { name: '研究材料 · 0' }));
  await waitFor(() => expect(document.activeElement).toBe(screen.getByRole('heading', { name: '研究材料', level: 2 })));
});

it('focuses the chosen result while it loads and preserves a later failure without stale rows', async () => {
  let finish: (response: Response) => void = () => {};
  transport(url => url.searchParams.get('section') === 'us_mapping_research' ? new Promise(resolve => { finish = resolve; }) : undefined);
  const { container } = render(SavedManagerResultView); await ready();
  await fireEvent.click(screen.getByRole('button', { name: '经理已保存结果' }));
  await screen.findByText('SYNTHETIC_ONLY · 合成经理股票');
  await fireEvent.click(screen.getByRole('button', { name: '美股驱动' }));
  await waitFor(() => expect(document.activeElement).toBe(screen.getByRole('heading', { name: '美股与港股映射', level: 2 })));
  expect(screen.queryByText('SYNTHETIC_ONLY · 合成经理股票')).toBeNull();
  expect(container.querySelector('#saved-result-content')?.textContent).toContain('正在读取同一运行');
  finish(new Response(JSON.stringify({ reason_codes: ['SYNTHETIC_UNAVAILABLE'] }), { status: 503 }));
  expect(await screen.findByRole('alert')).toHaveProperty('textContent', expect.stringContaining('M18_HTTP_503: SYNTHETIC_UNAVAILABLE'));
  expect(container.querySelector('#saved-result-content')?.contains(screen.getByRole('alert'))).toBe(true);
  expect(screen.queryByRole('table')).toBeNull();
});

it('keeps latest-navigation wins when an earlier source response arrives last', async () => {
  let finish: (response: Response) => void = () => {};
  transport(url => url.searchParams.get('section') === 'stocks' ? new Promise(resolve => { finish = resolve; }) : undefined);
  render(SavedManagerResultView); await ready();
  await fireEvent.click(screen.getByRole('button', { name: '经理已保存结果' }));
  await fireEvent.click(screen.getByRole('button', { name: '美股驱动' }));
  await ready();
  finish(new Response(JSON.stringify(sectionPage('stocks'))));
  await flushPromises();
  await waitFor(() => expect(document.activeElement).toBe(screen.getByRole('heading', { name: '美股与港股映射', level: 2 })));
  expect(screen.queryByText('SYNTHETIC_ONLY · 合成经理股票')).toBeNull();
  expect(screen.queryByRole('alert')).toBeNull();
});

it('clears the displayed identity when another run cannot be read', async () => {
  transport(); render(SavedManagerResultView); await ready();
  expect(screen.getByText('已读取运行 ' + run)).toBeTruthy();
  await fireEvent.update(screen.getByRole('textbox', { name: '运行 ID' }), 'not-a-run');
  await fireEvent.click(screen.getByRole('button', { name: '读取已保存结果' }));
  expect(await screen.findByRole('alert')).toHaveProperty('textContent', expect.stringContaining('M18_RUN_ID'));
  expect(screen.queryByText('已读取运行 ' + run)).toBeNull();
  expect(screen.getByRole('heading', { name: '经理已保存结果', level: 2 })).toBeTruthy();
  expect(screen.getByRole('button', { name: '源模块实际状态' })).toBeTruthy();
});


it('M04 direct entry opens both disclosures, focuses the result and leaves the manager run unchanged', async () => {
  const requests=transport();
  const {container}=render(SavedManagerResultView);await ready();
  const beforeRun=(screen.getByRole('textbox',{name:'运行 ID'}) as HTMLInputElement).value;
  await fireEvent.click(screen.getByRole('button',{name:'研究情报 · M04'}));
  const sources=container.querySelector<HTMLDetailsElement>('#source-module-content')!;
  const research=container.querySelector<HTMLDetailsElement>('#m04-saved-research')!;
  await waitFor(()=>{expect(sources.open).toBe(true);expect(research.open).toBe(true);});
  await fireEvent(research,new Event('toggle'));
  await waitFor(()=>expect(requests.filter(url=>url==='/api/v5/source-bundle/research-intelligence')).toHaveLength(1));
  expect(document.activeElement).toBe(research.querySelector('summary'));
  expect((screen.getByRole('textbox',{name:'运行 ID'}) as HTMLInputElement).value).toBe(beforeRun);
  await fireEvent.click(screen.getByRole('button',{name:'研究情报 · M04'}));
  expect(requests.filter(url=>url==='/api/v5/source-bundle/research-intelligence')).toHaveLength(1);
});
