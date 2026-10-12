<script setup lang="ts">
import {onBeforeUnmount,onMounted,shallowRef} from 'vue';
import {HK_REVIEW_STAGES,HkCloseReviewSession,type HkCloseReviewState,type ReviewRows} from '../api/hkCloseReview';
const state=shallowRef<HkCloseReviewState>({phase:'IDLE',result:null,error:''});
const session=new HkCloseReviewSession(next=>{state.value=next;});
const sections:{key:ReviewRows;title:string}[]=[{key:'close_top20',title:'收盘涨幅 Top20'},{key:'model_rows',title:'0.2 模型保存行'},{key:'stage_rows',title:'七阶段保存行'},{key:'top20_attribution',title:'Top20 归因与证据缺口'}];
const metricFields=['source_status','evidence_status','selected_count','hit_count','coverage_pct','precision_pct','cannot_confirm'];
onMounted(()=>session.load());onBeforeUnmount(()=>session.close());
function fields(key:ReviewRows){return [...new Set((state.value.result?.review[key]||[]).flatMap(row=>Object.keys(row)))];}
function text(value:unknown):string {return value===null?'null · 无法确认':value===undefined?'—':value===''?'""':typeof value==='object'?JSON.stringify(value):String(value);}
function cell(row:Record<string,unknown>,field:string,key:ReviewRows):string {
 if(key==='stage_rows'&&field==='hit_top20'){
  const status=state.value.result?.review.stages[String(row.stage_id)]?.source_status;
  if(status!=='READY'&&status!=='READY_EMPTY')return `CANNOT_CONFIRM（原保存字段：${text(row[field])}）`;
 }
 return text(row[field]);
}
</script>
<template>
 <section class="hk-review" aria-label="M10 港股收盘复盘只读结果">
  <div class="review-header"><h3>M10 港股收盘复盘</h3><button type="button" @click="session.load()">重读固定复盘结果</button></div>
  <p>录制输入回放，仅查看已保存复盘。港股资格、PIT 与自然运行尚未通过；natural_verified=false · formal_eligibility_verified=false。此处不代表正式推荐。</p>
  <p>research_only=true · production_allowed=false · buy_gate_updated=false · orders_sent=false。</p>
  <p v-if="state.phase==='LOADING'" role="status" aria-live="polite">正在校验并读取固定 run / generation…</p>
  <p v-else-if="state.phase==='NOT_CONFIGURED'" role="status">NOT_CONFIGURED · 尚未绑定已保存的复盘结果。</p>
  <p v-else-if="!state.result" role="status">CANNOT_CONFIRM · {{ state.error || '尚无可确认的保存结果。' }}</p>
  <template v-if="state.result">
   <p class="review-boundary"><strong>{{ state.result.status }}</strong> · 交易日 {{ state.result.review.trade_date }} · {{ state.result.data_kind }} · natural_admission={{ state.result.natural_admission }}</p>
   <p>原计算标签：{{ state.result.review.source_status }}。页面保留 PARTIAL 与缺口；无法确认的指标和归因命中显示 null，不按 0 计算。</p>
   <dl class="review-identity"><dt>固定 run</dt><dd>{{ state.result.run_id }}</dd><dt>固定 generation</dt><dd>{{ state.result.generation }}</dd><dt>原复盘 SHA256</dt><dd>{{ state.result.native_review_sha256 }}</dd></dl>
   <details><summary>输入身份与未确认原因</summary><pre>{{ JSON.stringify({identity:state.result.identity,cannot_confirm:state.result.review.cannot_confirm},null,2) }}</pre></details>
   <h4>七阶段证据状态与指标</h4>
   <div class="review-scroll"><table><thead><tr><th>阶段</th><th v-for="field in metricFields" :key="field">{{ field }}</th></tr></thead>
    <tbody><tr v-for="stage in HK_REVIEW_STAGES" :key="stage"><th>{{ stage }}</th><td v-for="field in metricFields" :key="field">{{ text(state.result.review.stages[stage]?.[field]) }}</td></tr></tbody>
   </table></div>
   <details><summary>模型指标、阶段并集与 KPI</summary><pre>{{ JSON.stringify({models:state.result.review.models,stage_union:state.result.review.stage_union,kpi:state.result.review.kpi},null,2) }}</pre></details>
   <details v-for="section in sections" :key="section.key" :open="section.key==='close_top20'">
    <summary>{{ section.title }} · {{ state.result.review[section.key].length }} 行</summary>
    <p v-if="section.key==='stage_rows'">原保存行与顺序保留。PARTIAL_WITH_ROWS 阶段的命中字段仅作原值审计，结论为 CANNOT_CONFIRM。</p>
    <div class="review-scroll"><table :aria-label="section.title"><thead><tr><th v-for="field in fields(section.key)" :key="field">{{ field }}</th></tr></thead>
     <tbody><tr v-for="(row, index) in state.result.review[section.key]" :key="index"><td v-for="field in fields(section.key)" :key="field">{{ cell(row,field,section.key) }}</td></tr></tbody>
    </table></div>
   </details>
  </template>
 </section>
</template>
<style scoped>
.hk-review{margin-top:24px;border-top:1px solid #c8d3dd;padding-top:18px}.review-header{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}.review-header h3{margin:0;font-size:17px}.review-header button{padding:8px 12px}.hk-review p{font-size:13px;line-height:1.7;overflow-wrap:anywhere}.review-boundary{background:#fff4d6;padding:10px 12px;border-radius:6px}.review-identity{display:grid;grid-template-columns:120px minmax(0,1fr);gap:6px;font-size:12px}.review-identity dd{margin:0;overflow-wrap:anywhere}.hk-review details{margin:12px 0}.hk-review summary{cursor:pointer;color:#254d71;font-weight:600}.hk-review pre{white-space:pre-wrap;overflow-wrap:anywhere;max-height:280px;overflow:auto;font-size:12px}.review-scroll{overflow:auto;max-height:430px;margin-top:10px}.review-scroll table{border-collapse:collapse;font-size:12px;min-width:100%;text-align:left}.review-scroll th,.review-scroll td{border:1px solid #d8e0e7;padding:7px;vertical-align:top;white-space:nowrap;max-width:420px}.review-scroll th{background:#edf2f6;position:sticky;top:0}.review-scroll td{white-space:normal;overflow-wrap:anywhere;min-width:70px}
</style>
