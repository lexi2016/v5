<script setup lang="ts">
import {computed,onBeforeUnmount,onMounted,ref,shallowRef} from 'vue';
import {CloseRecaptureSession,DEFAULT_CLOSE_RECAPTURE_QUERY,type CloseRecaptureQuery,type CloseRecaptureState} from '../api/closeRecapture';
const props=defineProps<{initialReference?:CloseRecaptureQuery}>();
const sourceDate=ref(props.initialReference?.source_trade_date??DEFAULT_CLOSE_RECAPTURE_QUERY.source_trade_date);
const runId=ref(props.initialReference?.run_id??DEFAULT_CLOSE_RECAPTURE_QUERY.run_id);
const state=shallowRef<CloseRecaptureState>({phase:'IDLE',result:null,error:''});
const session=new CloseRecaptureSession(next=>{state.value=next;});
function reload(){session.load({source_trade_date:sourceDate.value,run_id:runId.value});}
onMounted(reload);onBeforeUnmount(()=>session.close());
const rows=computed(()=>state.value.result?.rows??[]);
const keyFields=['symbol','name','pool_rank','pool_score','last_price','prev_close_price','turnover','turnover_currency','turnover_unit','volume','observed_at','available_at','candidate_status'];
const fields=computed(()=>{const actual=new Set(rows.value.flatMap(row=>Object.keys(row)));return [...keyFields.filter(key=>actual.has(key)),...[...actual].filter(key=>!keyFields.includes(key))];});
const metadata=computed(()=>{const result=state.value.result;if(!result)return null;return {bar_window:result.bar_window,coverage:result.coverage};});
function display(value:unknown){if(value===null)return 'null · 原值缺失／无法确认';if(value===undefined)return '字段未提供';if(value==='')return '"" · 原空字符串';return typeof value==='object'?JSON.stringify(value,null,2):String(value);}
function json(value:unknown){return JSON.stringify(value,null,2);}
</script>
<template>
 <section class="m17-close" aria-label="M17 收盘补采已保存观察">
  <h3>M17 收盘补采已保存观察</h3>
  <p>独立 M17 原保存产物只读复用。按来源交易日与精确 run 读取，不触发采集，不属于经理三策略结果。READY 仅表示原产物可读，业务缺口按原样保留。</p>
  <form class="m17-controls" @submit.prevent="reload">
   <label>待查询来源交易日<input v-model="sourceDate" aria-label="M17 来源交易日" inputmode="numeric" spellcheck="false" autocomplete="off" /></label>
   <label>待查询精确保存 run<input v-model="runId" aria-label="M17 精确保存 run" spellcheck="false" autocomplete="off" /></label>
   <button type="submit">读取 M17 精确保存结果</button>
  </form>
  <p v-if="state.phase==='LOADING'" role="status" aria-live="polite">正在冷读 M17 精确保存结果，旧表格与已读身份已清空…</p>
  <p v-else-if="!state.result" role="status">CANNOT_CONFIRM · 当前没有可确认的 M17 保存结果。{{ state.error }}</p>
  <template v-if="state.result">
   <div data-testid="m17-loaded-identity">
    <p><strong>{{ state.result.status }} · 原观察 {{ state.result.candidate_count }} 行</strong></p>
    <p>来源交易日：{{ state.result.source_trade_date }} · 计划交易日：{{ state.result.plan_trade_date }}<br />精确保存 run：{{ state.result.run_id }}</p>
    <p>原采集时间：{{ state.result.captured_at }}<br />原可用时间：{{ state.result.available_at }}</p>
    <p>{{ state.result.execution_label }} · {{ state.result.operation }} · execution_kind={{ state.result.execution_kind }}</p>
   </div>
   <p class="m17-warning">历史已存结果只读复用；received_not_historical_1530=true，非历史 15:30 结果，亦不证明完整收盘。RESEARCH_ONLY=true · natural_verified=false · formal_eligibility_verified=false。无生产、交易或正式准入资格。</p>
   <p class="m17-warning">成交额 turnover 仅显示原值，币种与单位未核（UNKNOWN）；不换算金额单位。production_allowed=false · buy_gate_updated=false · orders_sent=false。</p>
   <div data-testid="m17-gaps"><h4>原始缺口</h4><ul><li v-for="gap in state.result.cannot_confirm" :key="gap">{{ gap }}</li></ul></div>
   <details open><summary>原观察窗口与覆盖</summary><pre data-testid="m17-original-metadata">{{ json(metadata) }}</pre></details>
   <h4>全部 {{ rows.length }} 行原始观察</h4>
   <div class="m17-table" tabindex="0" aria-label="M17 全部原行字段，可横向滚动"><table data-testid="m17-rows"><thead><tr><th v-for="field in fields" :key="field" scope="col">{{ field }}</th></tr></thead><tbody><tr v-for="(row,index) in rows" :key="index"><td v-for="field in fields" :key="field" :data-field="field">{{ display(row[field]) }}</td></tr></tbody></table></div>
   <details><summary>原保存身份、文件摘要与来源</summary><pre>{{ json({identity:state.result.identity,files:state.result.files,pool:state.result.pool,source:state.result.source}) }}</pre></details>
  </template>
 </section>
</template>
<style scoped>
.m17-close{margin-top:20px;padding:18px;border:1px solid #c8d3dd;border-left:4px solid #657b8e;border-radius:8px;background:#fff;color:#263c50;min-width:0}.m17-close h3{margin:0;font-size:19px}.m17-close h4{font-size:14px}.m17-close p,.m17-close li{font-size:12px;line-height:1.7;overflow-wrap:anywhere}.m17-controls{display:flex;align-items:end;gap:12px;flex-wrap:wrap;margin:14px 0}.m17-controls label{display:flex;flex-direction:column;gap:6px;font-size:12px;max-width:100%}.m17-controls label:nth-child(2){flex:1;min-width:240px}.m17-controls input,.m17-controls button{box-sizing:border-box;font:inherit;font-size:12px;padding:8px;border:1px solid #8297a9;border-radius:5px;background:#fff;max-width:100%}.m17-close button,.m17-close summary{cursor:pointer}.m17-close :is(button,input,summary):focus-visible,.m17-table:focus-visible{outline:3px solid #2563eb;outline-offset:2px}.m17-warning{padding:10px;background:#fff9e9;border:1px solid #e6ce98;color:#73531b}.m17-close details{margin:12px 0;padding:10px;background:#f8fafc;border:1px solid #d8e0e8}.m17-close pre{font:11px/1.6 ui-monospace,SFMono-Regular,Menlo,monospace;white-space:pre-wrap;overflow-wrap:anywhere;max-height:320px;overflow:auto}.m17-table{overflow:auto;max-width:100%;max-height:560px}.m17-close table{width:100%;min-width:1100px;border-collapse:collapse;font-size:11px}.m17-close th,.m17-close td{padding:8px;min-width:105px;max-width:250px;border-bottom:1px solid #dce3ea;text-align:left;vertical-align:top;white-space:pre-wrap;overflow-wrap:anywhere}.m17-close th{background:#eef3f7;position:sticky;top:0}@media(max-width:650px){.m17-close{padding:12px}.m17-controls label{width:100%}.m17-controls label:nth-child(2){min-width:0}}
</style>
