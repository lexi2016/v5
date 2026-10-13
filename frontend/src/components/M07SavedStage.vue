<script setup lang="ts">
import {computed,onBeforeUnmount,ref,shallowRef} from 'vue';
import {A_STAGES,A_STAGE_LABELS,SavedAStageSession,type SavedAStageState} from '../api/m07SavedStage';
const state=shallowRef<SavedAStageState>({phase:'IDLE',result:null,error:''});
const date=ref(''),stage=ref('');
const session=new SavedAStageSession(next=>{state.value=next;});
function reload(){void session.load({date:date.value.trim(),stage:stage.value});}
function onToggle(event:Event){if((event.currentTarget as HTMLDetailsElement).open&&state.value.phase==='IDLE')reload();}
const selection=computed(()=>state.value.result?.selection??null);
const originalMeta=computed(()=>selection.value?Object.fromEntries(Object.entries(selection.value).filter(([key])=>key!=='rows')):null);
function display(value:unknown):string{if(value===undefined)return '未提供';if(value===null)return 'null · 原值缺失';if(value==='')return '"" · 原空字符串';return typeof value==='object'?JSON.stringify(value,null,2):String(value);}
function reasons(row:Record<string,unknown>){return Object.fromEntries(Object.entries(row).filter(([key])=>/reason|cannot_confirm|missing|evidence|gap|summary/i.test(key)));}
onBeforeUnmount(()=>session.close());
</script>
<template>
 <details id="m07-saved-stage" class="m07-stage" @toggle="onToggle">
  <summary>M07 A 股阶段选股 · 已保存结果 · 展开只读</summary>
  <section aria-label="M07 A 股阶段已保存结果">
   <p>只读取绑定的原始保存结果；日期和阶段仅筛选保存引用，留空读取已配置引用。不会采集行情、重新计算、生成候选或执行交易。</p>
   <form class="m07-controls" @submit.prevent="reload">
    <label>原目标日（可选，YYYYMMDD）<input v-model="date" aria-label="M07 目标日" placeholder="YYYYMMDD" inputmode="numeric" maxlength="8" autocomplete="off" /></label>
    <label>原阶段（可选）<select v-model="stage" aria-label="M07 阶段"><option value="">已配置保存阶段</option><option v-for="id in A_STAGES" :key="id" :value="id">{{ A_STAGE_LABELS[id] }} · {{ id }}</option></select></label>
    <button type="submit">{{ state.phase==='LOADING'?'重新读取 M07 保存结果':'读取 M07 保存结果' }}</button>
   </form>
   <p v-if="state.phase==='IDLE'">尚未读取；展开后核对保存引用。</p>
   <p v-else-if="state.phase==='LOADING'" role="status" aria-live="polite">正在读取 M07 原保存结果；旧行与身份已清空…</p>
   <p v-else-if="state.phase==='CANNOT_CONFIRM'" role="alert">CANNOT_CONFIRM · 当前保存结果无法确认，未显示旧行。{{ state.error }}</p>
   <template v-if="state.result">
    <p v-if="state.result.status==='WAITING'" role="status">WAITING · 尚无可确认的 M07 原保存结果，等待以下输入或精确引用。</p>
    <div v-if="state.result.reason_codes.length"><h3>当前原因码</h3><ul><li v-for="(reason,index) in state.result.reason_codes" :key="index">{{ reason }}</li></ul></div>
    <div v-if="state.result.missing_inputs.length"><h3>具体缺失输入</h3><ul><li v-for="(missing,index) in state.result.missing_inputs" :key="index">{{ missing }}</li></ul></div>
    <template v-if="selection && state.result.reference">
     <h3>A 股原保存结果 · {{ state.result.reference.target_date }} · {{ state.result.reference.stage_id }}</h3>
     <p>读取状态 {{ state.result.status }} · 输入类型 {{ state.result.data_kind }}</p>
     <p class="m07-boundary">VERIFIED_SAVED 仅表示保存引用读取核验。录制输入回放不证明当日自然运行、行情真实性或正式准入；原 PARTIAL_WITH_ROWS / CANNOT_CONFIRM 与缺口按原样保留。</p>
     <p data-testid="m07-original-status">原 source_status：{{ selection.source_status }} · 原 selection_status：{{ selection.selection_status }}</p>
     <h3>原排名、股票与分数 · {{ selection.rows.length }} 行</h3>
     <div v-if="selection.rows.length" class="m07-table" tabindex="0" aria-label="M07 原行，可横向滚动"><table><thead><tr><th>原 rank</th><th>原 code</th><th>原 name</th><th>原 score</th><th>原原因与缺口</th></tr></thead><tbody>
      <tr v-for="(row,index) in selection.rows" :key="index"><td>{{ display(row.rank) }}</td><td>{{ display(row.code) }}</td><td>{{ display(row.name) }}</td><td>{{ display(row.score) }}</td><td><pre>{{ display(reasons(row)) }}</pre><details><summary>完整原行</summary><pre>{{ display(row) }}</pre></details></td></tr>
     </tbody></table></div>
     <p v-else>原 rows 为空，保持原状态；没有补造股票或分数。</p>
     <details open><summary>原状态、证据与 cannot_confirm</summary><pre data-testid="m07-original-metadata">{{ display(originalMeta) }}</pre></details>
     <details open><summary>精确保存身份 · 日期 / 阶段 / run / SHA</summary><dl><div v-for="(value,key) in state.result.reference" :key="key"><dt>{{ key }}</dt><dd>{{ value }}</dd></div></dl><p>owner_commit：{{ state.result.owner_commit }}</p></details>
    </template>
   </template>
   <p class="m07-boundary">natural_verified=false · formal_eligibility_verified=false · production_allowed=false · buy_gate_updated=false · orders_sent=false</p>
  </section>
 </details>
</template>
<style scoped>
.m07-stage{margin-top:18px;padding:14px;border:1px solid #c8d3dd;border-radius:8px;scroll-margin-top:16px;min-width:0}.m07-stage>summary{font-weight:600;color:#254d71;cursor:pointer}.m07-stage summary:focus,.m07-stage input:focus-visible,.m07-stage select:focus-visible,.m07-stage button:focus-visible,.m07-table:focus-visible{outline:2px solid #254d71;outline-offset:4px}.m07-stage p,.m07-stage li{font-size:13px;line-height:1.65;overflow-wrap:anywhere}.m07-stage h3{font-size:15px;margin:16px 0 8px}.m07-controls{display:flex;gap:12px;align-items:end;flex-wrap:wrap;margin:14px 0}.m07-controls label{display:flex;flex-direction:column;gap:6px;font-size:12px;min-width:0;max-width:100%}.m07-controls input,.m07-controls select,.m07-controls button{font:inherit;padding:8px;max-width:100%;box-sizing:border-box}.m07-stage button,.m07-stage summary{cursor:pointer}.m07-boundary{padding:10px;background:#fff9e9;border:1px solid #e6ce98;color:#73531b}.m07-table{overflow-x:auto}.m07-table table{width:100%;border-collapse:collapse;font-size:12px;min-width:650px}.m07-table th,.m07-table td{text-align:left;vertical-align:top;padding:9px;border:1px solid #dce3ea;overflow-wrap:anywhere}.m07-table th{background:#eef3f7}.m07-stage pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px;max-height:360px;overflow:auto}.m07-stage dl{display:grid;gap:8px;font-size:12px}.m07-stage dt{color:#526579}.m07-stage dd{margin:4px 0;overflow-wrap:anywhere}.m07-stage section>details{margin-top:14px}@media(max-width:650px){.m07-stage{padding:12px}.m07-controls label{width:100%}}
</style>
