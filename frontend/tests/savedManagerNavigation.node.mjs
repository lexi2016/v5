import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const source = readFileSync(new URL('../src/views/SavedManagerResultView.vue', import.meta.url), 'utf8');
const template = source.slice(source.indexOf('<template>'), source.indexOf('</template>\n<style'));

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
