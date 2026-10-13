<script setup lang="ts">
import {onBeforeUnmount,ref,shallowRef,watch} from 'vue';
import {readM15,readM15Page,type Overview,type Page,type M15Lane} from '../api/m15Mapping';
const props=defineProps<{targetDate?:string}>();
const date=ref(props.targetDate||'');const overview=shallowRef<Overview|null>(null);const page=shallowRef<Page|null>(null);
const lane=ref<M15Lane>('seed');const loading=ref(false);const error=ref('');let revision=0;let controller:AbortController|null=null;
function clear(){revision++;controller?.abort();overview.value=null;page.value=null;error.value='';loading.value=false;}
watch(()=>props.targetDate,value=>{date.value=value||'';clear();});watch(date,clear);
async function load(){clear();const version=revision;loading.value=true;controller=new AbortController();try{const result=await readM15(date.value,fetch,controller.signal);if(version===revision)overview.value=result;}catch(e){if(version===revision)error.value=e instanceof Error?e.message:'M15_READ_FAILED';}finally{if(version===revision)loading.value=false;}}
async function rows(selected:M15Lane,offset=0){const saved=overview.value;if(!saved)return;revision++;const version=revision;controller?.abort();controller=new AbortController();page.value=null;error.value='';loading.value=true;lane.value=selected;
 try{const result=await readM15Page(saved,selected,offset,fetch,controller.signal);if(version===revision)page.value=result;}catch(e){if(version===revision)error.value=e instanceof Error?e.message:'M15_PAGE_FAILED';}finally{if(version===revision)loading.value=false;}}
function json(v:unknown){return JSON.stringify(v,null,2);}onBeforeUnmount(clear);
</script>
<template>
 <details id="m15-saved-mapping" class="m15-mapping">
  <summary>M15 美股到港股映射 · 种子与原材料两路径</summary>
  <section aria-label="M15 已保存映射">
   <p>只读固定保存结果。四键种子不代表全市场；行业材料与显式个股关系分别展示。目标资格、历史可用性和自然运行均未提升。</p>
   <label>目标日 <input v-model="date" inputmode="numeric" maxlength="8" placeholder="YYYYMMDD" /></label>
   <button type="button" :disabled="loading||!/^\d{8}$/.test(date)" @click="load">读取该日保存结果</button>
   <p v-if="loading" role="status">正在读取…</p><p v-if="error" role="alert">CANNOT_CONFIRM · {{ error }}；当前页旧行已清除。</p>
   <template v-if="overview">
    <h3>{{ overview.target_date }} · {{ overview.reference.run_id }}</h3>
    <p>摘要 {{ overview.reference.sha256 }} · 美股 session {{ overview.us_session_date ?? 'UNKNOWN' }}</p>
    <p>种子：{{ overview.seed_status }} / 来源 {{ overview.seed_source_status }} · 材料：{{ overview.material_status ?? 'NOT_RUN' }}</p>
    <p>目标资格：{{ overview.target_date_eligibility }} · RESEARCH_ONLY · formal_eligible=false · natural_verified=false</p>
    <section aria-label="种子原覆盖诊断与恢复边界">
     <p>本次路径：{{ overview.mode }}{{ overview.mode==='seed' ? ' · 仅四键种子，材料路径 NOT_RUN' : '' }}</p>
     <p>种子覆盖诊断：{{ overview.seed_coverage_diagnostics?.status ?? 'UNKNOWN · 原保存未提供覆盖诊断' }}</p>
     <p>诊断原因（独立于种子 gaps）：{{ overview.seed_coverage_diagnostics?.reason_codes == null ? 'UNKNOWN · 原保存未提供原因' : json(overview.seed_coverage_diagnostics.reason_codes) }}</p>
     <p>覆盖范围：{{ json(overview.seed_coverage_scope ?? null) }} · {{ overview.seed_coverage_diagnostics?.scope ?? 'UNKNOWN' }}</p>
     <p>执行类型：{{ overview.seed_execution_kind ?? 'UNKNOWN' }}</p>
     <details><summary>完整原覆盖诊断（含 registry / scope）</summary><pre>{{ json(overview.seed_coverage_diagnostics ?? null) }}</pre></details>
     <details><summary>原恢复评估与历史资格边界</summary><pre>{{ json(overview.seed_recovery_evaluation ?? null) }}</pre></details>
    </section>
    <p>材料缺口：{{ json(overview.material_reasons) }} · 种子缺口：{{ json(overview.seed_gaps) }}</p>
    <nav aria-label="M15 路径"><button v-for="key in (['seed','industry','individual'] as const)" :key="key" type="button" :disabled="loading||overview.lanes[key]===null" @click="rows(key)">{{ key }} · {{ overview.lanes[key] ?? 'NOT_EVALUATED' }}</button></nav>
    <section v-if="page" :aria-label="lane+'映射行'"><p>{{ lane }} · {{ page.offset+1 }}–{{ page.offset+page.rows.length }} / {{ page.total }}</p>
     <p v-if="page.total===0">该路径原保存行数为 0；是否合法空仍以上述原状态与缺口为准。</p>
     <ol :start="page.offset+1"><li v-for="(row,index) in page.rows" :key="index"><pre>{{ json(row) }}</pre></li></ol>
     <button type="button" :disabled="loading||page.offset===0" @click="rows(lane,Math.max(0,page.offset-50))">上一页</button>
     <button type="button" :disabled="loading||page.next_offset===null" @click="page.next_offset!==null&&rows(lane,page.next_offset)">下一页</button>
    </section>
    <details><summary>原范围、完整性与保存身份</summary><pre>{{ json(overview) }}</pre></details>
   </template>
  </section>
 </details>
</template>
<style scoped>
.m15-mapping{margin-top:18px;border:1px solid #c8d3dd;border-radius:8px;padding:14px}.m15-mapping summary{cursor:pointer;font-weight:600}.m15-mapping p{overflow-wrap:anywhere;line-height:1.6}.m15-mapping pre{white-space:pre-wrap;overflow-wrap:anywhere;max-height:28rem;overflow:auto}.m15-mapping button{padding:8px;margin:5px}.m15-mapping input{padding:8px;width:9rem}
</style>
