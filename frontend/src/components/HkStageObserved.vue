<script setup lang="ts">
import {computed,onBeforeUnmount,onMounted,shallowRef} from 'vue';
import {HkStageObservedSession,HK_STAGES,HK_STAGE_LABELS,type HkObservedState} from '../api/hkStageObserved';
const state=shallowRef<HkObservedState>({phase:'IDLE',references:[],selected:null,result:null,error:''});
const session=new HkStageObservedSession(next=>{state.value=next;});
onMounted(()=>session.load());onBeforeUnmount(()=>session.close());
const stages=computed(()=>HK_STAGES.filter(stage=>state.value.references.some(r=>r.stage_id===stage)));
const runs=computed(()=>state.value.references.filter(r=>r.stage_id===state.value.selected?.stage_id));
const rows=computed(()=>state.value.result?.artifact.rows??[]);
const columns=computed(()=>[...new Set(rows.value.flatMap(row=>Object.keys(row)))]);
const modes=computed(()=>[...new Set(rows.value.map(row=>row.source_mode).filter(x=>typeof x==='string'))]);
const originalMeta=computed(()=>{const a=state.value.result?.artifact;if(!a)return null;return Object.fromEntries(Object.entries(a).filter(([k])=>k!=='rows'));});
function stageChanged(event:Event){const stage=(event.target as HTMLSelectElement).value;const ref=state.value.references.find(r=>r.stage_id===stage);if(ref)session.select(ref);}
function runChanged(event:Event){const hash=(event.target as HTMLSelectElement).value;const ref=state.value.references.find(r=>r.import_sha256===hash);if(ref)session.select(ref);}
function display(value:unknown){if(value===null)return 'null · 原值缺失／无法确认';if(value===undefined)return '字段未提供';if(value==='')return '"" · 原空字符串';return typeof value==='object'?JSON.stringify(value,null,2):String(value);}
function json(value:unknown){return JSON.stringify(value,null,2);}
</script>
<template>
 <section class="hk-observed" aria-label="M08 港股八阶段历史保存结果">
  <div class="hk-observed-heading"><div><span>M08 · 只读历史观察</span><h3>港股八阶段历史保存结果</h3></div><button type="button" @click="session.load()">重读八阶段历史清单</button></div>
  <p>保留已配置的全部 10 套精确 run，覆盖八阶段。同阶段可有多套保存结果，按清单顺序展示，不合并、不取 latest。只读取独立 V5 保存副本，不采集行情、不重新选股。</p>
  <div v-if="state.references.length" class="hk-observed-controls">
   <label>阶段 <select aria-label="M08 阶段" :value="state.selected?.stage_id" @change="stageChanged"><option v-for="stage in stages" :key="stage" :value="stage">{{ HK_STAGE_LABELS[stage] }}</option></select></label>
   <label>该阶段保存 run <select aria-label="M08 保存 run" :value="state.selected?.import_sha256" @change="runChanged"><option v-for="ref in runs" :key="ref.import_sha256" :value="ref.import_sha256">{{ ref.target_date }} · {{ ref.run_id }} · {{ ref.import_sha256.slice(0,12) }}</option></select></label>
   <button v-if="state.selected" type="button" @click="session.select(state.selected)">重读所选保存结果</button>
  </div>
  <p v-if="state.phase==='LOADING'" role="status" aria-live="polite">正在冷读精确历史保存结果，旧表格与结果身份已清空…</p>
  <p v-else-if="state.phase==='NOT_CONFIGURED'" role="status">NOT_CONFIGURED · 尚未配置八阶段的 10 套精确 reference。{{ state.error }}</p>
  <p v-else-if="!state.result" role="status">CANNOT_CONFIRM · 当前没有可确认的保存结果。{{ state.error }}</p>
  <template v-if="state.result">
   <div class="hk-observed-tags"><strong>历史业务日期 {{ state.result.reference.target_date }}</strong><span>HISTORICAL</span><span>OBSERVED_ONLY</span><span>{{ state.result.status }}</span><span>{{ state.result.stage_group }}</span></div>
   <p>原阶段：{{ state.result.reference.stage_id }} · 原 source_status：{{ display(state.result.artifact.source_status) }} · 原 selection_status：{{ state.result.status }}</p>
   <p class="hk-observed-warning">这是已保存原结果的历史观察，不证明当日自然选股、行情真实性或 PIT。captured_at=null；natural_verified=false · pit_verified=false · formal_admission=false。原 PARTIAL／CANNOT_CONFIRM 状态及缺口保留。</p>
   <p>普通阶段／竞价／D1 参考均保留原行来源标签：<strong v-for="mode in modes" :key="String(mode)" class="hk-observed-mode">{{ mode }}</strong></p>
   <p>竞价 SECOND_FILTER 与 D1_REFERENCE 按原字段分别展示，不能互相替代。Stage8 为独立 HK_STAGE8_SEPARATE，不属于 M10 的前七阶段分组。</p>
   <div class="hk-observed-gaps"><h4>原覆盖、缺口与证据</h4><pre data-testid="m08-original-metadata">{{ json(originalMeta) }}</pre></div>
   <h4>所选 run 的全部 {{ rows.length }} 行原字段</h4>
   <div v-if="rows.length" class="hk-observed-table" tabindex="0" aria-label="M08 全部原行与字段，可横向滚动"><table data-testid="m08-rows"><thead><tr><th v-for="field in columns" :key="field">{{ field }}</th></tr></thead><tbody><tr v-for="(row,index) in rows" :key="index"><td v-for="field in columns" :key="field" :data-field="field">{{ display(row[field]) }}</td></tr></tbody></table></div>
   <p v-else>原保存数组为空，保留原状态；不补造行、不视为证据齐全。</p>
   <details class="hk-observed-details"><summary>完整原保存结果（仅本机路径脱敏）</summary><pre data-testid="m08-original-artifact">{{ json(state.result.artifact) }}</pre></details>
   <details class="hk-observed-details" open><summary>精确保存身份与历史观察边界</summary><dl><div v-for="(value,key) in state.result.reference" :key="key"><dt>{{ key }}</dt><dd>{{ display(value) }}</dd></div></dl><p>实际导入保存时间：{{ state.result.provenance.imported_at }}；这不是历史行情采集时间。</p><pre>{{ json(state.result.provenance) }}</pre><p>research_only=true · production_allowed=false · buy_gate_updated=false · orders_sent=false</p></details>
  </template>
 </section>
</template>
<style scoped>
.hk-observed{margin-top:20px;padding:18px;border:1px solid #c8d3dd;border-left:4px solid #687849;border-radius:8px;background:#fff;color:#263c50;min-width:0}.hk-observed-heading,.hk-observed-controls{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}.hk-observed-heading span{font-size:11px;font-weight:700;color:#607348}.hk-observed h3{margin:5px 0;font-size:19px}.hk-observed h4{font-size:14px}.hk-observed p{font-size:12px;line-height:1.7;overflow-wrap:anywhere}.hk-observed button,.hk-observed select{font:inherit;font-size:12px;padding:8px;border:1px solid #8297a9;border-radius:5px;background:#fff;max-width:100%}.hk-observed-controls{justify-content:flex-start;margin:14px 0}.hk-observed-controls label{display:flex;flex-direction:column;gap:6px;min-width:0;max-width:100%;font-size:12px}.hk-observed button,.hk-observed summary{cursor:pointer}.hk-observed button:focus-visible,.hk-observed select:focus-visible,.hk-observed summary:focus-visible,.hk-observed-table:focus-visible{outline:3px solid #2563eb;outline-offset:2px}.hk-observed-tags{display:flex;flex-wrap:wrap;gap:8px}.hk-observed-tags strong{width:100%;font-size:16px}.hk-observed-tags span,.hk-observed-mode{padding:4px 6px;border:1px solid #d5ddc8;background:#f6f8f0;border-radius:4px;font-size:11px}.hk-observed-mode{display:inline-block;margin:4px}.hk-observed-warning{padding:12px;background:#fff9e9;border:1px solid #e6ce98;color:#73531b}.hk-observed-table{overflow-x:auto;max-width:100%}.hk-observed table{width:100%;min-width:900px;border-collapse:collapse;font-size:11px}.hk-observed th,.hk-observed td{min-width:100px;max-width:300px;padding:8px;border-bottom:1px solid #dce3ea;text-align:left;vertical-align:top;white-space:pre-wrap;overflow-wrap:anywhere}.hk-observed th{background:#eef3f7}.hk-observed-details,.hk-observed-gaps{margin-top:14px;padding:10px;background:#f8fafc;border:1px solid #d8e0e8}.hk-observed pre{font:11px/1.6 ui-monospace,SFMono-Regular,Menlo,monospace;white-space:pre-wrap;overflow-wrap:anywhere;max-height:360px;overflow:auto}.hk-observed dl{display:grid;gap:8px;grid-template-columns:1fr;font-size:11px}.hk-observed dt{color:#647889}.hk-observed dd{margin:4px 0;overflow-wrap:anywhere;font-family:ui-monospace,SFMono-Regular,Menlo,monospace}@media(max-width:650px){.hk-observed{padding:12px}.hk-observed-controls label{width:100%}}
</style>
