import test from 'node:test';
import assert from 'node:assert/strict';
import { renderSavedAnnouncementReferences } from '../src/manager-selection/announcementAnalysis.ts';
class Element {
 constructor(tag) { this.tagName=tag;this.children=[];this.dataset={};this.attributes={};this.ownText=''; }
 set textContent(value) { this.ownText=value;this.children=[]; }
 get textContent() { return this.ownText+this.children.map(x=>typeof x==='string'?x:x.textContent).join(''); }
 append(...nodes) { this.children.push(...nodes); }
 replaceChildren(...nodes) { this.ownText='';this.children=[...nodes]; }
 setAttribute(name,value) { this.attributes[name]=value; }
}
const ref={stock_code:'01234',stock_name:'合成示例公司',research_status:'SELECTED',target_trade_date:'20261012',publication_date:'2026-10-09',reviewed_at:'2026-10-11T17:18:37Z',owner_available_at:'2026-10-12T01:21:24+08:00',point_in_time_status:'CANNOT_CONFIRM',connect_eligibility_status:'NOT_ASSESSED',product_sha256:'a'.repeat(64),selection_reasons:[{disposition:'SELECTED_EVENT',reason:'原始逐篇理由'}],risk_notes:['原始风险'],article_refs:[{art_code:'SYNTHETIC-001',title:'合成公告标题',disposition:'SELECTED_EVENT',reason:'原始公告理由',factual_summary:'原始事实摘要',source_sha256:'b'.repeat(64)}]};
const entry={index:0,kind:'object',offset:0,bytes:1000,sha256:'c'.repeat(64),value_state:'LOADED',value:ref};
const page={projection:'announcement_references',entries:[entry],matched_total:147,announcement:{status:'READY',plan_cutoff:'2026-10-12T07:42:13+08:00',reference_count:147,source_section_sha256:'d'.repeat(64),gaps:[],products:[]}};
function render(value) { globalThis.document={createElement:tag=>new Element(tag)};const host=new Element('div');renderSavedAnnouncementReferences(host,value);return host; }
test('saved references reuse V4 stock reasons and article facts while retaining dates, provenance and uncertainty',()=>{
 const host=render(page),text=host.textContent;
 for(const expected of ['01234 合成示例公司','入选研究名单','原始逐篇理由','原始风险','原始公告理由','原始事实摘要','2026-10-09','20261012','CANNOT_CONFIRM','NOT_ASSESSED','SYNTHETIC-001','b'.repeat(64),'147']) assert.ok(text.includes(expected),expected);
 assert.ok(text.includes('原文链接未提供'));
 const all=[];function visit(node){all.push(node);node.children?.filter(x=>typeof x!=='string').forEach(visit);}visit(host);
 assert.equal(all.filter(x=>x.tagName==='a').length,0);
 assert.ok(all.some(x=>x.dataset.announcementSelectionStock==='01234'));
});
test('oversized/missing entries remain NOT_LOADED, never fabricated stocks',()=>{
 const unavailable={...entry,value_state:'NOT_LOADED',reason:'ITEM_BYTES_LIMIT'};delete unavailable.value;
 const host=render({...page,entries:[unavailable]});assert.match(host.textContent,/NOT_LOADED/);assert.match(host.textContent,/ITEM_BYTES_LIMIT/);assert.doesNotMatch(host.textContent,/合成示例公司/);
});
test('render replaces previous results and treats data as literal text',()=>{
 const host=render(page);renderSavedAnnouncementReferences(host,{...page,entries:[{...entry,value:{...ref,stock_name:'<script>never execute</script>',research_status:'CONDITIONAL_WATCH'}}]});
 assert.doesNotMatch(host.textContent,/合成示例公司/);assert.match(host.textContent,/条件观察/);assert.match(host.textContent,/<script>never execute<\/script>/);
});

test('null and false references are shown as original values without invented stock rows',()=>{
 const host=render({...page,entries:[{...entry,value:null},{...entry,index:1,value:false}]});
 assert.match(host.textContent,/null/);assert.match(host.textContent,/false/);assert.doesNotMatch(host.textContent,/未评估|入选研究名单/);
});
