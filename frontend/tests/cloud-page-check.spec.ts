// Opt-in jsdom + REAL loopback HTTP integration. This is NOT a browser test.
// Start the isolated synthetic preview, then set V5_PAGE_CHECK_FIXTURE,
// V5_PAGE_CHECK_ORIGIN and V5_PAGE_CHECK_EVIDENCE before running this file alone.
import {readFileSync, writeFileSync} from 'node:fs';
import {join} from 'node:path';
import {afterAll, afterEach, beforeEach, describe, expect, it, vi} from 'vitest';
import {cleanup, configure, fireEvent, render, screen, waitFor} from '@testing-library/vue';
import SavedManager from '../src/views/SavedManagerResultView.vue';
import ResearchRoot from '../src/research-workbench/Root.vue';
import CloseRecapture from '../src/components/CloseRecapture.vue';

const fixturePath=process.env.V5_PAGE_CHECK_FIXTURE;
const origin=process.env.V5_PAGE_CHECK_ORIGIN;
const evidence=process.env.V5_PAGE_CHECK_EVIDENCE;
const enabled=Boolean(fixturePath&&origin&&evidence);
const fixture=enabled?JSON.parse(readFileSync(fixturePath!,'utf8')):null;
const nativeFetch=globalThis.fetch;
const requests:Record<string,unknown>[]=[];
const consoleErrors:string[]=[];
configure({asyncUtilTimeout:15000});

function save(name:string,container:HTMLElement) {
 writeFileSync(join(evidence!,name+'.dom.html'),
  '<!-- JSDOM COMPONENT DOM ONLY; NOT A BROWSER SCREENSHOT. ALL INPUTS SYNTHETIC. -->\n'+container.outerHTML);
}

describe.skipIf(!enabled)('cloud synthetic page components against real saved-result HTTP',()=>{
 beforeEach(()=>{
  if(!/^http:\/\/127\.0\.0\.1:[1-9][0-9]*$/.test(origin!))throw new Error('LOOPBACK_PREVIEW_REQUIRED');
  vi.spyOn(console,'error').mockImplementation((...args)=>{consoleErrors.push(args.map(String).join(' '));});
  vi.stubGlobal('fetch',async(input:string|URL|Request,init?:RequestInit)=>{
   const url=new URL(String(input),origin!);
   if(url.origin!==origin)throw new Error('NON_PREVIEW_REQUEST_DENIED');
   const row:Record<string,unknown>={url:url.href,method:init?.method??'GET',layer:'REAL_HTTP_FROM_JSDOM'};
   requests.push(row);
   try {
    const response=await nativeFetch(url,init);row.status=response.status;
    const body=await response.clone().json().catch(()=>null);
    if(body)row.response_identity={run_id:body.run_id,identity:body.identity,
      generation_id:body.generation_id,manifest_sha256:body.manifest_sha256,research_date:body.research_date};
    return response;
   } catch(error) {row.error=String(error);throw error;}
  });
 });
 afterEach(()=>{cleanup();vi.restoreAllMocks();vi.unstubAllGlobals();history.replaceState(null,'','/');});
 afterAll(()=>{writeFileSync(join(evidence!,'dom-requests.json'),JSON.stringify({
  layer:'JSDOM_NOT_BROWSER',input_kind:'SYNTHETIC',browser_screenshots:'NOT_RUN',
  requests,component_console_errors:consoleErrors},null,2));});

 it('navigates saved manager sections and pages without mixing runs; failed run clears rows',async()=>{
  history.replaceState(null,'','/?run_id='+fixture.manager_descriptor.run_id);
  const view=render(SavedManager);
  await screen.findByText('SYNTHETIC_ONLY · 合成经理股票');
  expect(view.container.textContent).toContain(fixture.manager_descriptor.run_id);
  expect(screen.getByRole('link',{name:'研报决策台'}).getAttribute('href')).toBe('?view=research');
  await fireEvent.click(screen.getByRole('button',{name:'源模块实际状态'}));
  expect(view.container.querySelector<HTMLDetailsElement>('#source-module-content')!.open).toBe(true);
  await fireEvent.click(screen.getByRole('button',{name:'研究材料 · 70'}));
  await waitFor(()=>expect(view.container.querySelectorAll('.saved-table-scroll tbody tr')).toHaveLength(32));
  await fireEvent.click(screen.getByRole('button',{name:'下一页'}));
  await screen.findByText('当前 33–64 / 70 条');
  const pageCalls=requests.filter(row=>String(row.url).includes('/sections?'));
  for(const call of pageCalls){
   expect(new URL(String(call.url)).searchParams.get('run_id')).toBe(fixture.manager_descriptor.run_id);
   expect((call.response_identity as any)?.identity).toEqual(fixture.manager_descriptor.identity);
  }
  save('manager-same-run-page2',view.container);
  await fireEvent.update(screen.getByLabelText('运行 ID'),'f'.repeat(32));
  await fireEvent.submit(screen.getByLabelText('运行 ID').closest('form')!);
  await waitFor(()=>expect(view.container.querySelector('.task-error')).not.toBeNull());
  expect(view.container.querySelectorAll('.saved-table-scroll tbody tr')).toHaveLength(0);
  save('manager-wrong-run-error',view.container);
 },30000);

 it('reads original M04 list/detail and switches exact new, old and missing dates with explicit latest',async()=>{
  history.replaceState(null,'','/?view=research&date='+fixture.m04_dates[0]);
  const view=render(ResearchRoot);
  await waitFor(()=>expect(view.container.querySelectorAll('.hourly-feed-card.archive').length).toBeGreaterThan(0));
  const detail=view.container.querySelector<HTMLDetailsElement>('.archive-original')!;
  await fireEvent.click(detail.querySelector('summary')!);
  expect(detail.open).toBe(true);
  expect(detail.querySelector('pre')!.textContent).toContain('独立测试合成正文，没有真实业务含义');
  save('m04-new-original-detail',view.container);
  await fireEvent.change(screen.getByLabelText('研究自然日'),{target:{value:'2020-01-02'}});
  await waitFor(()=>expect(screen.getByTestId('research-date-identity').textContent).toContain('实际来源日期：20200102'));
  expect(view.container.querySelector('.archive-original')!.textContent).toContain('UNKNOWN');
  expect(view.container.textContent).toContain('M04_SOURCE_RUN_UNKNOWN');
  save('m04-old-unknown-evidence',view.container);
  await fireEvent.change(screen.getByLabelText('研究自然日'),{target:{value:'1999-01-01'}});
  await screen.findByText('NOT_MATERIALIZED');
  expect(view.container.querySelectorAll('.hourly-feed-card.archive')).toHaveLength(0);
  save('m04-missing-date',view.container);
  await fireEvent.click(screen.getByRole('button',{name:'查看 latest'}));
  await waitFor(()=>expect(screen.getByTestId('research-date-identity').textContent).toContain('实际来源日期：'+fixture.m04_dates[0]));
  expect(screen.getByTestId('research-date-identity').textContent).toContain('不是所选日期数据');
  save('m04-explicit-latest',view.container);
 },30000);

 it('renders all original M17 rows and exact run; a wrong run clears both table and loaded identity',async()=>{
  const view=render(CloseRecapture);
  await waitFor(()=>expect(view.container.textContent).toContain('M17_HTTP_409'));
  await fireEvent.update(view.getByLabelText('M17 来源交易日'),fixture.m17_query.source_trade_date);
  await fireEvent.update(view.getByLabelText('M17 精确保存 run'),fixture.m17_query.run_id);
  await fireEvent.submit(view.getByLabelText('M17 精确保存 run').closest('form')!);
  await waitFor(()=>expect(view.queryByTestId('m17-rows')).not.toBeNull());
  expect(view.getByTestId('m17-rows').querySelectorAll('tbody tr')).toHaveLength(100);
  expect(view.getByTestId('m17-loaded-identity').textContent).toContain(fixture.m17_query.run_id);
  expect(view.getByTestId('m17-loaded-identity').textContent).toContain('execution_kind=SIMULATED');
  expect(view.container.textContent).toContain('natural_verified=false');
  save('m17-exact-simulated',view.container);
  await fireEvent.update(view.getByLabelText('M17 精确保存 run'),'f'.repeat(32));
  await fireEvent.submit(view.getByLabelText('M17 精确保存 run').closest('form')!);
  expect(view.queryByTestId('m17-loaded-identity')).toBeNull();
  expect(view.queryByTestId('m17-rows')).toBeNull();
  await waitFor(()=>expect(view.container.textContent).toContain('M17_HTTP_409'));
  expect(view.queryByTestId('m17-rows')).toBeNull();
  save('m17-wrong-run-error',view.container);
 },30000);
});
