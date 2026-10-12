import test from 'node:test';
import assert from 'node:assert/strict';
import {renderSavedReboundReferences,renderReboundScreenCard} from '../src/manager-selection/reboundPanelObservation.ts';
class Element {constructor(tag){this.tagName=tag;this.children=[];this.dataset={};this.attributes={};this.ownText='';this.listeners={};} set textContent(v){this.ownText=v;this.children=[];}get textContent(){return this.ownText+this.children.map(x=>typeof x==='string'?x:x.textContent).join('');}append(...nodes){this.children.push(...nodes);}replaceChildren(...nodes){this.ownText='';this.children=nodes;}setAttribute(k,v){this.attributes[k]=v;}addEventListener(type,fn){this.listeners[type]=fn;} }
globalThis.document={createElement:tag=>new Element(tag)};
const row={code:'01234',name:'SYNTHETIC 超跌公司',classification:'STRICT_REBOUND',reason_for_group:'SYNTHETIC 原分组理由',close:1.2,prior60_session_high:2,oversold_cutoff_80pct_prior60_high:1.6,volume_ratio_5d:1.8,oversold_flag:true,volume_flag_5d_ge_1_5:true,amount_native:12345,currency:null,amount_unit:null,price_currency:null,volume_unit:null,observed_session:'20261009',target_monday:'20261012',qualification_status:'UNVERIFIED_RESEARCH_OBSERVATION',connect_eligibility:'UNVERIFIED',history_status:'KNOWN',source_refs:[{owner:'SYNTHETIC_OWNER',sha256:'a'.repeat(64),payload_path:'/private/SYNTHETIC'}]};
const entry={index:0,bytes:1000,offset:100,sha256:'b'.repeat(64),value_state:'LOADED',value:row};
const page={projection:'rebound_references',group:'strict',matched_total:1,entries:[entry],rebound:{source_section_sha256:'c'.repeat(64),group_counts:{strict:1,near:1,pending:1,excluded:1,screen_unresolved:0},source:{status:'CANNOT_CONFIRM',eligible_screen:null,scope:'INDEPENDENT_READ_TIME_OBSERVATION_NOT_SAVED_PLAN_OR_FORMAL_SELECTION'},observation:{status:'CANNOT_CONFIRM',original_computation_status:'READY_WITH_GAPS',native_evidence:{unit_evidence:{status:'NOT_PROVEN'}},gaps:['SYNTHETIC_GAP']}}};
function render(value=page){const host=new Element('main');renderSavedReboundReferences(host,value);return host;}
test('saved rebound shows original numeric gates, reasons and unverified research scope without currency promotion',()=>{
 const text=render().textContent;
 for(const expected of ['01234','SYNTHETIC 原分组理由','1.2000','1.6000','1.8000','2026-10-09','2026-10-12','CANNOT_CONFIRM','READY_WITH_GAPS','UNVERIFIED','NOT_PROVEN','12345','SYNTHETIC_GAP'])assert.ok(text.includes(expected),expected);
 assert.doesNotMatch(text,/HKD|已核验共享|严格候选|近条件候选|\/private\/SYNTHETIC/);
});
test('near, pending and excluded retain their distinct original failure reasons',()=>{
 const near=render({...page,group:'near',entries:[{...entry,value:{...row,classification:'NEAR_CONDITION',near_failed_gate:'SYNTHETIC_GATE',near_failed_value:1.4,near_gate_value:1.5,near_gate_gap_ratio:0.0667}}]});assert.match(near.textContent,/SYNTHETIC_GATE/);assert.match(near.textContent,/1.4000/);
 const pending=render({...page,group:'pending',entries:[{...entry,value:{...row,history_unknown_reasons:['SYNTHETIC_MISSING_HISTORY']}}]});assert.match(pending.textContent,/SYNTHETIC_MISSING_HISTORY/);
 const excluded=render({...page,group:'excluded',entries:[{...entry,value:{...row,exclusion_reason_code:'SYNTHETIC_EXCLUDED',reason_for_exclusion:'SYNTHETIC 排除理由'}}]});assert.match(excluded.textContent,/SYNTHETIC_EXCLUDED/);assert.match(excluded.textContent,/SYNTHETIC 排除理由/);
});
test('empty, NOT_LOADED, null and false remain distinct; a new page replaces prior rows',()=>{
 const host=render();renderSavedReboundReferences(host,{...page,group:'screen_unresolved',matched_total:0,entries:[]});assert.doesNotMatch(host.textContent,/01234/);assert.match(host.textContent,/0 条/);
 const e={...entry,value_state:'NOT_LOADED',reason:'PAGE_BYTES_LIMIT'};delete e.value;assert.match(render({...page,entries:[e]}).textContent,/NOT_LOADED.*PAGE_BYTES_LIMIT/s);
 const text=render({...page,entries:[{...entry,value:null},{...entry,index:1,value:false}]}).textContent;assert.match(text,/null/);assert.match(text,/false/);assert.doesNotMatch(text,/01234/);
});
test('legacy V4 card behavior is retained when no observation group is supplied',()=>{
 const card=renderReboundScreenCard({...row,amount_hkd:20});assert.match(card.textContent,/严格候选/);assert.match(card.textContent,/20 HKD/);assert.match(card.textContent,/已核验共享HK 0.2/);
});

test('expanded observation evidence preserves source hashes without local paths or synthesized URLs',()=>{
 const host=render();function expand(node){if(node.tagName==='details'){node.open=true;node.listeners.toggle?.();}for(const child of node.children)if(typeof child!=='string')expand(child);}expand(host);
 assert.match(host.textContent,/SYNTHETIC_OWNER/);assert.ok(host.textContent.includes('a'.repeat(64)));assert.doesNotMatch(host.textContent,/\/private\/SYNTHETIC|payload_path|https?:\/\//);
});
