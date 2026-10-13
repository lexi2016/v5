import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const root=new URL('../frontend/src/', import.meta.url);
test('research entry is isolated from legacy and saved manager',()=>{
 const main=readFileSync(new URL('main.ts',root),'utf8');
 assert.match(main,/view === 'research'/);
 assert.match(main,/research-workbench\/Root.vue/);
 assert.match(main,/view === 'legacy'/);
 assert.match(main,/SavedManagerResultView/);
});
test('isolated research APIs never call V4 endpoints',()=>{
 for(const name of ['research_lane','wechat_research']){
 const code=readFileSync(new URL(`research-workbench/api/${name}.ts`,root),'utf8');
 assert.doesNotMatch(code,/\/api\/v3\//);
 assert.match(code,/\/api\/v5\/research\//);
 }
});
test('archive original content is rendered without assigning a false source',()=>{
 const code=readFileSync(new URL('research-workbench/composables/useResearchLane.ts',root),'utf8');
 assert.match(code,/archive_materials/);
 assert.match(code,/source: "archive"/);
 const card=readFileSync(new URL('research-workbench/components/research/ResearchFeedCard.vue',root),'utf8');
 assert.match(card,/归档原文/);
 assert.match(card,/<pre/);
 assert.doesNotMatch(card,/v-html/);
});
