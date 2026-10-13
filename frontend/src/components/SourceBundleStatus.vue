<script setup lang="ts">
import { onBeforeUnmount, onMounted, shallowRef } from 'vue';
import { SourceBundleSession, type SourceState } from '../api/sourceBundle';
import M07SavedStage from './M07SavedStage.vue';
import HkPreselectionPool from './HkPreselectionPool.vue';
import HkCloseReview from './HkCloseReview.vue';
import ACloseReplay from './ACloseReplay.vue';
import HkStageObserved from './HkStageObserved.vue';
import CloseRecapture from './CloseRecapture.vue';
import M04SavedResearch from './M04SavedResearch.vue';
const state=shallowRef<SourceState>({phase:'IDLE',result:null,error:''});
const session=new SourceBundleSession(next=>{state.value=next;});
const names:Record<string,string>={M01_A_MARKET:'M01 A 股基础数据',M02_HK_MARKET:'M02 港股基础数据',M03_US_MARKET:'M03 美股基础数据',M05_A_PRESELECTION:'M05 A 股预选池'};
onMounted(()=>session.load());onBeforeUnmount(()=>session.close());
function json(value:unknown){return JSON.stringify(value,null,2);}
</script>
<template>
 <section class="source-status task-status-view" aria-label="基础数据与 A 股预选池实际状态">
  <div class="source-header"><h2>基础数据与 A 股预选池</h2><button type="button" @click="session.load()">读取模块实际结果</button></div>
  <p>独立的单次源输入任务。下方保留各模块原始状态；此按钮只读保存结果。录制回放与历史日期不代表今日采集、同日闭环或正式准入。</p>
  <p v-if="state.phase==='LOADING'" role="status" aria-live="polite">正在读取实际保存结果…</p>
  <p v-else-if="!state.result" role="status">CANNOT_CONFIRM · 尚无可确认的模块结果。{{ state.error }}</p>
  <template v-if="state.result">
   <p>输入类型：{{ state.result.data_kind }} · 运行观察时间：{{ state.result.observed_at }}</p>
   <p class="source-digest">请求 SHA256：{{ state.result.request_sha256 }} · natural_verified=false</p>
   <div class="source-grid"><article v-for="row in state.result.modules" :key="row.module_id">
    <h3>{{ names[row.module_id] }}</h3><p><strong>{{ row.status }}</strong></p>
    <p v-if="row.error">{{ row.error_type }}：{{ row.error }}</p>
    <details v-if="row.owner_result"><summary>模块原始结果、日期与缺口</summary><pre>{{ json(row.owner_result) }}</pre></details>
   </article></div>
  </template>
  <M04SavedResearch />
  <M07SavedStage />
  <HkPreselectionPool />
  <HkStageObserved />
  <HkCloseReview />
  <ACloseReplay />
  <CloseRecapture />
 </section>
</template>
<style scoped>
.source-status{padding:18px}.source-header{display:flex;gap:16px;align-items:center;justify-content:space-between;flex-wrap:wrap}.source-header h2{font-size:18px;margin:0}.source-header button{padding:8px 12px}.source-status p{font-size:13px;line-height:1.65;overflow-wrap:anywhere}.source-digest{color:#526579}.source-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.source-grid article{border:1px solid #c8d3dd;border-radius:8px;padding:14px;min-width:0}.source-grid h3{font-size:15px;margin:0}.source-grid summary{cursor:pointer;color:#254d71}.source-grid pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px;max-height:320px;overflow:auto}@media(max-width:650px){.source-grid{grid-template-columns:1fr}}
</style>

