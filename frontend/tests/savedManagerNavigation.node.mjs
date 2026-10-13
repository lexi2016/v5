import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { runInNewContext } from 'node:vm';

const source = readFileSync(new URL('../src/views/SavedManagerResultView.vue', import.meta.url), 'utf8');
const template = source.slice(source.indexOf('<template>'), source.indexOf('</template>\n<style'));

// Execute the view's run-input and URL controls without requiring a Vue build.
// Rendered identity and real-session integration are covered by the view spec.
function runControls(href) {
 const window={location:new URL(href),history:{replaceState(_state,_title,url){window.location=new URL(url);}}};
 const requests=[];
 const setup=source.slice(source.indexOf('const query ='),source.indexOf('const state ='));
 const reload=source.match(/async function reload\(\) \{[\s\S]*?\n\}/)?.[0];
 assert.ok(reload,'the run reload handler must exist');
 const controls=runInNewContext(setup+'\n'+reload+'\n({requestedRun,reload})',{URL,URLSearchParams,window,ref:value=>({value}),session:{load:async run=>requests.push(run)}});
 return {...controls,window,requests};
}
test('no run selector starts blank and requests the default without adding a historical run',async()=>{
 const controls=runControls('https://fixture.invalid/manager-selection/?tab=saved#result');
 assert.equal(controls.requestedRun.value,'');await controls.reload();
 assert.equal(controls.window.location.href,'https://fixture.invalid/manager-selection/?tab=saved#result');
 assert.deepEqual(controls.requests,['']);
});
test('clearing the run input removes only its URL selector before loading the default',async()=>{
 const run='46596b03c2ab4e29b1219fd2e5eb698f';
 const controls=runControls('https://fixture.invalid/manager-selection/?tab=saved&run_id='+run+'#result');
 assert.equal(controls.requestedRun.value,run);await controls.reload();
 assert.equal(controls.window.location.searchParams.get('run_id'),run);
 controls.requestedRun.value=' ';await controls.reload();
 assert.equal(controls.window.location.href,'https://fixture.invalid/manager-selection/?tab=saved#result');
 assert.deepEqual(controls.requests,[run,'']);
});

test('saved result content precedes a closed source disclosure and preserves the source component', () => {
  const result = template.indexOf('id="saved-result-content"');
  const disclosure = template.indexOf('id="source-module-content"');
  assert.ok(result >= 0, 'the results must have a stable navigation target');
  assert.ok(disclosure > result, 'the source disclosure must follow the results');
  assert.match(template, /<details[^>]*id="source-module-content"[^>]*>/);
  assert.doesNotMatch(template.match(/<details[^>]*id="source-module-content"[^>]*>/)[0], /\sopen(?:\s|=|>)/);
  assert.equal(template.split('<SourceBundleStatus').length - 1, 1);
  assert.ok(template.indexOf('<SourceBundleStatus') > disclosure);
});

test('result navigation has a visible heading, focus and scroll instead of only starting a request', () => {
  assert.match(template, /ref="resultHeading"[^>]*tabindex="-1"/);
  assert.match(source, /\.focus\(\{\s*preventScroll:\s*true\s*\}\)/);
  assert.match(source, /\.scrollIntoView\?\.\(\{\s*block:\s*'start'/);
  assert.match(template, /@click="selectSection\('announcement_reviewed_analysis'\)"/);
  assert.match(template, /@click="selectSection\('us_mapping_research'\)"/);
  assert.match(template, /aria-controls="source-module-content"/);
});

test('the selected result exposes its verified date and run without enabling missing routes', () => {
  assert.match(template, /已读取运行\s*\{\{\s*state\.descriptor\.run_id\s*\}\}/);
  assert.match(template, /目标日\s*\{\{\s*state\.descriptor\.target_date\s*\}\}/);
  assert.match(template, /<button type="button" aria-controls="m07-saved-stage" @click="openAStage">A 股阶段选股 · M07 已保存结果<\/button>/);
  assert.match(template, /<button type="button" disabled>研报决策台 · 未接入<\/button>/);
  assert.match(template, /CANNOT_CONFIRM · 当前请求未能确认，未显示旧结果。\{\{ state.error \}\}/);
});
