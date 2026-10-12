import test from 'node:test';
import assert from 'node:assert/strict';
import {renderSavedUsMappingMatches,renderUsMappingCoverage} from '../src/manager-selection/usMappingCoverage.ts';
class Element {constructor(tag){this.tagName=tag;this.children=[];this.dataset={};this.ownText='';}set textContent(value){this.ownText=value;this.children=[];}get textContent(){return this.ownText+this.children.map(node=>typeof node==='string'?node:node.textContent).join('');}append(...nodes){this.children.push(...nodes);}replaceChildren(...nodes){this.ownText='';this.children=nodes;}}
globalThis.document={createElement:tag=>new Element(tag),createTextNode:text=>String(text)};
const diagnostics={schema_version:'v5.us_mapping_scope.v1',status:'PARTIAL',scope:'PINNED_REVIEWED_RELATIONS_WITHIN_CONFIGURED_US_SAMPLE',us_session_date:'20261009',reviewed_us_symbols:['SYN_A','SYN_B','SYN_C','SYN_D'],reviewed_us_symbol_count:4,configured_sample_count:33,rising_individual_count:23,assessed_rising_symbol_count:4,unassessed_rising_symbol_count:19,full_market_coverage:false,formal_eligible:false,natural_verified:false,reason_codes:['BROADER_US_HK_RELATIONS_NOT_ASSESSED']};
const row=(hk,us)=>({hk_symbol:hk,hk_name:'SYNTHETIC '+hk,us_symbol:us,change_pct:1.25,session_date:'20261009',relationship_type:'PRODUCT_PEER',reason:'SYNTHETIC 产品同业理由，并非供货证明',maturity:'SYNTHETIC 原产品阶段',limitations:['SYNTHETIC 原限制'],research_priority:'WATCH',official_sources:[{title:'SYNTHETIC 官方材料',url:'https://example.com/report',published_at:'2026-10-01'},{title:'unsafe',url:'javascript:alert(1)'}],target_date_eligibility:'CANNOT_CONFIRM',reviewed_relation_artifact_sha256:'a'.repeat(64)});
const rows=[row('HK.00001','SYN_A'),row('HK.00001','SYN_B'),row('HK.00002','SYN_C'),row('HK.00003','SYN_D')];
const entries=rows.map((value,index)=>({index,kind:'object',offset:100+1000*index,bytes:1000,sha256:String(index+1).repeat(64),value_state:'LOADED',value}));
const page={projection:'us_mapping_matches',matched_total:4,entries,us_mapping:{source_section_sha256:'b'.repeat(64),match_count:4,source:{target_trade_date:'20261012',RESEARCH_ONLY:true,orders_sent:false,registry_readback:{scope:'ORIGINAL_REVIEWED_RETROSPECTIVE_RESEARCH_NOT_CURRENT_SELECTION',seed_target_date:'20260930',formal_eligible:false}},daily_run:{status:'COMPLETED',target_trade_date:'20261012',us_session_date:'20261009',research_cutoff:'2026-10-12T04:39:26+08:00',generated_at:'2026-10-11T20:39:26Z',target_date_eligibility:'CANNOT_CONFIRM',run_id:'f'.repeat(32)},coverage_diagnostics:diagnostics,plan_reference:{value_state:'LOADED',source_section_sha256:'c'.repeat(64),value:{status:'SOURCE_FAILED',target_trade_date:'20261012',production_allowed:false,orders_sent:false}}}};
const all=(node)=>typeof node==='string'?[]:[node,...node.children.flatMap(all)];
const render=(value=page)=>{const host=new Element('main');renderSavedUsMappingMatches(host,value);return host;};
test('saved US relationships reuse V4 three-stock grouping, original reasons, stages and safe official sources',()=>{
 const host=render();const cards=all(host).filter(node=>node.dataset.usHkResult);
 assert.equal(cards.length,3);assert.match(host.textContent,/本页已读取 4 条关系.*3 个港股主体/);
 for(const expected of ['SYN_A +1.25% / SYN_B +1.25%','产品同业（非供货关系）','SYNTHETIC 产品同业理由','SYNTHETIC 原产品阶段','SYNTHETIC 原限制','配置样本 33','未评估 19','CANNOT_CONFIRM','20261012','20261009'])assert.ok(host.textContent.includes(expected),expected);
 const links=all(host).filter(node=>node.tagName==='a');assert.equal(links.length,3);assert.ok(links.every(link=>link.href==='https://example.com/report'&&link.rel==='noopener noreferrer'));
 const original=new Element('main');renderUsMappingCoverage(original,{coverage_diagnostics:diagnostics,daily_run:{...page.us_mapping.daily_run,matches:rows}});
 assert.deepEqual(cards.map(card=>card.textContent),all(original).filter(node=>node.dataset.usHkResult).map(card=>card.textContent));
});
test('daily dates, cutoff, limited scope and frozen response plan state stay separate from historical seeds',()=>{
 const text=render().textContent;
 for(const expected of ['2026-10-12T04:39:26+08:00','2026-10-11T20:39:26Z','本冻结响应的计划消费状态','SOURCE_FAILED','20260930','ORIGINAL_REVIEWED_RETROSPECTIVE_RESEARCH_NOT_CURRENT_SELECTION','false','PARTIAL','PINNED_REVIEWED_RELATIONS_WITHIN_CONFIGURED_US_SAMPLE'])assert.ok(text.includes(expected),expected);
 assert.doesNotMatch(text,/已消费今日计划|4 只股票|4 个港股主体|全市场已评估|大涨筛选/);
});
test('missing and oversized values remain explicit without old stock cards or fabricated plan consumption',()=>{
 const host=render();const missing={...entries[0],value_state:'NOT_LOADED',reason:'ITEM_BYTES_LIMIT'};delete missing.value;
 renderSavedUsMappingMatches(host,{...page,entries:[missing,{...entries[1],value:null},{...entries[2],value:false}],us_mapping:{...page.us_mapping,plan_reference:{value_state:'NOT_LOADED',reason:'SOURCE_NOT_AVAILABLE'}}});
 assert.equal(all(host).filter(node=>node.dataset.usHkResult).length,0);
 for(const expected of ['NOT_LOADED','ITEM_BYTES_LIMIT','null','false','SOURCE_NOT_AVAILABLE'])assert.ok(host.textContent.includes(expected),expected);
 assert.doesNotMatch(host.textContent,/SYNTHETIC 产品同业理由/);
});
test('empty scoped matches and literal text keep the original V4 uncertainty behavior',()=>{
 const host=render({...page,matched_total:0,entries:[],us_mapping:{...page.us_mapping,match_count:0,daily_run:{...page.us_mapping.daily_run,status:'VALID_EMPTY'},coverage_diagnostics:{...diagnostics,reason_codes:['<img src=x onerror=alert(1)>']}}});
 assert.match(host.textContent,/本次已审关系范围内无匹配港股/);assert.equal(all(host).filter(node=>node.tagName==='img').length,0);assert.match(host.textContent,/<img/);
});
test('original consumed reference is displayed without overriding qualification or scope gaps',()=>{
 const consumed={...page.us_mapping.plan_reference,value:{status:'CONSUMED',available_at:'2026-10-11T20:39:26Z',plan_cutoff:'2026-10-12T07:42:13+08:00',reason:null,RESEARCH_ONLY:true,production_allowed:false,orders_sent:false}};
 const text=render({...page,us_mapping:{...page.us_mapping,plan_reference:consumed}}).textContent;
 for(const expected of ['本冻结响应的计划消费状态：CONSUMED','2026-10-12T07:42:13+08:00','CANNOT_CONFIRM','PARTIAL','"reason": null','"production_allowed": false'])assert.ok(text.includes(expected),expected);
 assert.doesNotMatch(render({...page,us_mapping:{...page.us_mapping,plan_reference:{value_state:'NOT_LOADED',reason:'REFERENCE_MISSING'}}}).textContent,/消费状态：CONSUMED/);
});
