<script setup lang="ts">
import {computed,onBeforeUnmount,onMounted,shallowRef} from 'vue';
import {ACloseReplaySession,A_REPLAY_SECTIONS,type ACloseReplayState,type JsonObject} from '../api/aCloseReplay';
const state=shallowRef<ACloseReplayState>({phase:'IDLE',result:null,error:''});
const session=new ACloseReplaySession(next=>{state.value=next;});
onMounted(()=>session.load());onBeforeUnmount(()=>session.close());
const historical=computed(()=>state.value.result?.publication.historical_research);
const missingText=computed(()=>historical.value?.missing_text as JsonObject|undefined);
function columns(rows:JsonObject[]){return [...new Set(rows.flatMap(row=>Object.keys(row)))];}
function display(value:unknown){
 if(value===null)return 'null · 原值缺失／无法确认';
 if(value===undefined)return '字段未提供';
 if(value==='')return '"" · 原值为空字符串';
 return typeof value==='object'?JSON.stringify(value,null,2):String(value);
}
function json(value:unknown){return JSON.stringify(value,null,2);}
</script>
<template>
 <section class="a-replay" aria-label="M09 A股历史研究回放">
  <div class="a-replay-heading"><div><span class="a-replay-eyebrow">M09 · 只读保存结果</span><h3>A 股历史研究回放</h3></div>
   <button type="button" @click="session.load()">重读固定历史研究</button></div>
  <p class="a-replay-boundary">只读取已绑定的精确 run / generation。历史研究使用原保存输入；页面不采集、不重算、不补缺失，也不证明当日自然运行资格。</p>
  <p v-if="state.phase==='LOADING'" role="status" aria-live="polite">正在冷读固定历史研究，旧结果已清空…</p>
  <p v-else-if="state.phase==='NOT_CONFIGURED'" role="status">NOT_CONFIGURED · 尚未绑定历史研究结果。{{ state.error }}</p>
  <p v-else-if="!state.result" role="status">CANNOT_CONFIRM · 当前没有可确认的历史研究结果。{{ state.error }}</p>
  <template v-if="state.result">
   <div class="a-replay-classification"><strong>历史业务日期 {{ state.result.trade_date }}</strong>
    <span>RECORDED_INPUT_REPLAY</span><span>HISTORICAL_REPLAY</span><span>PARTIAL</span><span>OBSERVED_ROWS_ONLY</span></div>
   <p>原计算时间：{{ state.result.publication.computed_at }}。上方日期来自保存结果，不能据此认定为今天的数据或自然收盘闭环。</p>
   <div class="a-replay-warning">
    <strong>仅覆盖观察到的原始行，保留真实缺口</strong>
    <p>源时间、目标时点可用性、成员资格、严格 15:00 PIT 和自然运行均未确认。行业与角色排名不完整，ST 涨跌停近似计数存在不确定性。</p>
    <p>natural_verified=false · formal_eligibility_verified=false · strict_1500_pit_verified=false<br>source_time_verified=false · membership_qualification_verified=false</p>
    <dl><div><dt>保留的原输入行数</dt><dd>{{ display(historical?.snapshot_row_count) }}</dd></div>
     <div><dt>名称缺口</dt><dd>{{ display(missingText?.name) }}</dd></div>
     <div><dt>行业代码缺口</dt><dd>{{ display(missingText?.tdx_industry_code) }}</dd></div>
     <div><dt>行业名称缺口</dt><dd>{{ display(missingText?.tdx_industry_name) }}</dd></div>
     <div><dt>原模型未使用的缺失／非有限收盘位置</dt><dd>{{ display(historical?.nonfinite_unused_close_position) }}</dd></div></dl>
    <details><summary>原历史输入身份与全部缺口</summary><pre>{{ json(historical) }}</pre></details>
   </div>
   <div class="a-replay-original-summary"><h4>{{ state.result.review.headline }}</h4>
    <p>原市场状态：{{ state.result.review.market_regime }} · 原风险基调：{{ state.result.review.risk_tone }}</p>
    <p>原模型内部状态：{{ display(state.result.review.model_review.status) }}。整体仍为 PARTIAL，视频／阶段证据缺口保持原值。</p></div>
   <section v-for="section in A_REPLAY_SECTIONS" :key="section.key" :data-testid="'m09-'+section.key" class="a-replay-section">
    <h4>{{ section.label }} <small>{{ state.result.review[section.key].length }} 条原记录</small></h4>
    <p v-if="section.key==='next_day_trigger_tree'" class="a-replay-warning">情景概率为原模型冻结常量，未经校准；不代表可用于交易的概率预测。</p>
    <div v-if="state.result.review[section.key].length" class="a-replay-table" tabindex="0" :aria-label="section.label+'原记录，可横向滚动'">
     <table><thead><tr><th v-for="field in columns(state.result.review[section.key])" :key="field">{{ field }}</th></tr></thead>
      <tbody><tr v-for="(row,index) in state.result.review[section.key]" :key="index"><td v-for="field in columns(state.result.review[section.key])" :key="field" :data-field="field">{{ display(row[field]) }}</td></tr></tbody></table>
    </div>
    <p v-else>原保存数组为空。保留原结果，不补充候选或把空数组解释为证据齐全。</p>
   </section>
   <details class="a-replay-details"><summary>原复盘链及未确认项</summary><pre>{{ json(state.result.review.close_chain) }}</pre>
    <pre>{{ json({review:state.result.publication.review_cannot_confirm,record:state.result.publication.record_cannot_confirm,model:state.result.publication.model_cannot_confirm,chain:state.result.publication.close_chain_cannot_confirm}) }}</pre></details>
   <details class="a-replay-details"><summary>完整原模型结果与全部原保存字段</summary><pre data-testid="m09-native-review">{{ json(state.result.review) }}</pre></details>
   <details class="a-replay-details" open><summary>固定结果身份与校验</summary>
    <dl class="a-replay-identity"><div><dt>run_id</dt><dd>{{ state.result.run_id }}</dd></div><div><dt>generation</dt><dd>{{ state.result.generation }}</dd></div>
     <div v-for="(value,key) in state.result.identity" :key="key"><dt>{{ key }}</dt><dd>{{ display(value) }}</dd></div>
     <div><dt>冻结 M09 来源提交</dt><dd>{{ state.result.owner_commit }}</dd></div></dl>
    <p>只读研究：production_allowed=false · buy_gate_updated=false · orders_sent=false</p>
   </details>
  </template>
 </section>
</template>
<style scoped>
.a-replay{margin-top:20px;padding:18px;border:1px solid #c8d3dd;border-left:4px solid #a66c15;border-radius:8px;background:#fff;color:#263c50;min-width:0}.a-replay-heading{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}.a-replay-eyebrow{color:#796338;font-size:11px;font-weight:700}.a-replay h3{margin:5px 0;font-size:19px}.a-replay h4{font-size:14px;margin:8px 0}.a-replay p{font-size:12px;line-height:1.7;overflow-wrap:anywhere}.a-replay button{font:inherit;font-size:12px;padding:9px 12px;background:#fff;border:1px solid #8297a9;border-radius:5px;cursor:pointer}.a-replay button:focus-visible,.a-replay summary:focus-visible,.a-replay-table:focus-visible{outline:3px solid #2563eb;outline-offset:2px}.a-replay-classification{display:flex;flex-wrap:wrap;align-items:center;gap:7px;margin-top:14px}.a-replay-classification strong{font-size:16px;width:100%}.a-replay-classification span{padding:4px 7px;border:1px solid #e0c78f;background:#fffbef;font-size:11px;border-radius:4px}.a-replay-warning{padding:12px;background:#fff9e9;border:1px solid #e6ce98;color:#73531b}.a-replay-warning strong{font-size:14px}.a-replay dl{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px}.a-replay dt{font-size:11px;color:#647889}.a-replay dd{font-size:13px;margin:4px 0;overflow-wrap:anywhere}.a-replay-section{border:1px solid #d8e0e8;border-radius:5px;margin-top:15px;padding:10px;min-width:0}.a-replay-section h4{display:flex;justify-content:space-between;gap:10px}.a-replay-section small{font-size:11px;color:#687d8e;font-weight:400}.a-replay-table{overflow-x:auto;max-width:100%}.a-replay table{border-collapse:collapse;font-size:11px;min-width:700px;width:100%}.a-replay th,.a-replay td{border-bottom:1px solid #dce3ea;padding:8px;text-align:left;vertical-align:top;min-width:95px;max-width:320px;white-space:pre-wrap;overflow-wrap:anywhere}.a-replay th{background:#eef3f7;font-weight:600}.a-replay-details{margin-top:14px;border:1px solid #d8e0e8;padding:10px;background:#f8fafc}.a-replay summary{cursor:pointer;font-size:12px;font-weight:600}.a-replay pre{font:11px/1.6 ui-monospace,SFMono-Regular,Menlo,monospace;white-space:pre-wrap;overflow-wrap:anywhere;max-height:460px;overflow:auto}.a-replay .a-replay-identity{grid-template-columns:1fr}.a-replay-identity dd{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:11px}.a-replay-boundary{color:#617487}@media(max-width:650px){.a-replay{padding:12px}.a-replay dl{grid-template-columns:1fr 1fr}}
</style>
