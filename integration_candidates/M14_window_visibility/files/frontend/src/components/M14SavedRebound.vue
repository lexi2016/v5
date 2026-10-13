<script setup lang="ts">
import {computed, onBeforeUnmount, ref, shallowRef, watchEffect} from 'vue';
import {M14_REBOUND_GROUPS, SavedReboundSession, type M14SavedState} from '../api/m14SavedRebound';
import {renderSavedReboundReferences, reboundGroupLabels} from '../manager-selection/reboundPanelObservation';
const state = shallowRef<M14SavedState>({phase: 'IDLE', result: null, error: '', group: 'pending', canPrevious: false});
const host = ref<HTMLElement | null>(null);
const session = new SavedReboundSession(next => {state.value = next;});
const saved = computed(() => state.value.result?.status === 'SAVED_RESEARCH' ? state.value.result : null);
function object(value: unknown): Record<string, unknown> {
 return value !== null && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {};
}
const native = computed(() => object(saved.value?.rebound.observation.native_evidence));
const coverage = computed(() => object(saved.value?.rebound.observation.coverage));
const contract = computed(() => object(native.value.source_contract));
function shown(value: unknown) {return typeof value === 'string' && ['NOT_PROVEN', 'NOT_ATTESTED'].includes(value) ? '尚未证实' : typeof value === 'string' && value.trim() ? value : typeof value === 'number' && Number.isFinite(value) ? String(value) : '未知（原保存结果未提供）';}
const pendingSummary = computed(() => {
 const reasons = object(native.value.pending_reasons);
 const counts = new Map<string, number>();
 for (const items of Object.values(reasons)) if (Array.isArray(items)) {
  for (const reason of new Set(items.filter((item): item is string => typeof item === 'string'))) counts.set(reason, (counts.get(reason) ?? 0) + 1);
 }
 return [...counts].map(([reason, count]) => ({reason, count}));
});
const reasonLabels: Record<string, string> = {
 PRIOR60_KEYS_MISSING: '此前 60 个交易日记录有缺失',
 PREVIOUS5_KEYS_MISSING: '此前 5 个交易日记录有缺失',
 SOURCE_ROW_INVALID: '来源行情行不符合校验要求',
};
function reload() {void session.load(state.value.group);}
function onToggle(event: Event) {if ((event.currentTarget as HTMLDetailsElement).open && state.value.phase === 'IDLE') reload();}
function day(value: string) {return `${value.slice(0, 4)}-${value.slice(4, 6)}-${value.slice(6)}`;}
watchEffect(() => {if (host.value && saved.value) renderSavedReboundReferences(host.value, saved.value);}, {flush: 'post'});
onBeforeUnmount(() => session.close());
</script>
<template>
 <details id="m14-saved-rebound" class="m14-saved" @toggle="onToggle">
  <summary>M14 独立超跌研究 · 已保存结果 · 展开只读</summary>
  <section aria-label="M14 独立已保存研究结果">
   <p>读取配置中精确绑定的 M14 原保存结果，独立于经理运行。切换分组和翻页固定同一运行与三份 SHA256；重新读取配置引用才会重新选择绑定。</p>
   <p class="m14-boundary">只读研究，不触发行情采集、重算、生成候选或交易。SYNTHETIC 为合成输入，RECORDED_INPUT_REPLAY 为录制输入回放，均不证明自然运行或正式准入。</p>
   <p class="m14-warning">待核数据/历史组保留历史缺口：此前 60 个交易日与前 5 日均量仍须核实。pending 不等于严格条件或近条件通过，也不表示正式候选。</p>
   <div class="m14-controls" role="group" aria-label="M14 原研究分组">
    <button v-for="group in M14_REBOUND_GROUPS" :key="group" type="button" :aria-pressed="state.group===group" @click="session.select(group)">{{ reboundGroupLabels[group] }} · {{ saved?.rebound.group_counts[group] ?? '未读取' }}</button>
   </div>
   <button type="button" @click="reload">重新读取 M14 配置引用</button>
   <p v-if="state.phase==='IDLE'">尚未读取；展开后读取 M14 独立保存引用。</p>
   <p v-else-if="state.phase==='LOADING'" role="status" aria-live="polite">正在读取 M14 已保存分组；旧行与显示身份已清空…</p>
   <p v-else-if="state.phase==='CANNOT_CONFIRM'" role="alert">CANNOT_CONFIRM · 当前 M14 保存结果无法确认，未显示旧行。{{ state.error }}</p>
   <template v-if="state.result?.status==='WAITING'">
    <p role="status">WAITING · 尚未配置 M14 精确保存引用；不是分组为空，也不自动改读经理结果。</p>
    <ul><li v-for="reason in state.result.reason_codes" :key="reason">{{ reason }}</li></ul>
   </template>
   <template v-if="saved">
    <h3>保存信号日 {{ day(saved.signal_date) }} · 目标日 {{ day(saved.target_date) }}</h3>
    <p>来源 {{ saved.source_kind }} · 保存状态 {{ saved.status }} · 输入类型 {{ saved.data_kind }} · 原执行类型 {{ saved.execution_kind }}</p>
    <p>原运行 ID：{{ saved.reference.run_id }}</p>
    <section aria-label="M14 已保存同源窗口证据" class="m14-window-evidence">
     <h4>这次研究使用的数据</h4>
     <p>研究截止时点：{{ shown(native.research_cutoff) }}</p>
     <p>已保存行情行数：{{ shown(coverage.panel_row_count) }} · 股票数：{{ shown(coverage.panel_code_count) }}</p>
     <p>来源：{{ contract.provider === 'PYTDX_EXHQ_SDK' ? '通达信扩展行情 SDK' : shown(contract.provider) }} · 接口：{{ shown(contract.interface) }}</p>
     <p>历史窗口：{{ contract.high_window === 'SAME_INTERFACE_EXACT_NATIVE_CALENDAR_PRIOR60' ? '同一接口、按原交易日历核对的此前 60 个交易日' : shown(contract.high_window) }}；成交量窗口：{{ contract.volume_window === 'SAME_INTERFACE_EXACT_PREVIOUS5_FULL_SESSIONS_PLUS_SIGNAL' ? '同一接口、此前 5 个完整交易日及信号日' : shown(contract.volume_window) }}。</p>
     <p>成交量单位：{{ shown(contract.volume_unit) }} · 价格口径：{{ shown(contract.price_basis) }} · 数据最终性：{{ shown(contract.provider_finality) }}</p>
     <h4>尚未通过的原因</h4>
     <ul v-if="pendingSummary.length"><li v-for="item in pendingSummary" :key="item.reason">{{ reasonLabels[item.reason] ?? '原保存原因' }}：{{ item.count }} 只（{{ item.reason }}）</li></ul>
     <p v-else>原保存结果未提供原因明细；不据此判断没有缺口。</p>
     <p>计数按原保存的逐股原因归类，同一股票可能有多个原因。缺少交易日记录或行情异常仍属待核，不表示正式条件通过；未保存的具体缺日和异常行详情不作推断。</p>
     <details><summary>展开原保存的窗口机器字段</summary><pre>{{ JSON.stringify({coverage, native_evidence: native}, null, 2) }}</pre></details>
    </section>
    <p class="m14-boundary">research_only=true；production_allowed=false；buy_gate_updated=false；orders_sent=false；natural_verified=false；formal_eligibility_verified=false。</p>
    <div class="m14-pagination">
     <button type="button" :disabled="!state.canPrevious" @click="session.previous()">M14 上一页</button>
     <span>当前 {{ saved.entries.length ? saved.offset+1 : 0 }}–{{ saved.offset+saved.entries.length }} / {{ saved.matched_total }} 条 · 每页最多 32 条</span>
     <button type="button" :disabled="!saved.next_cursor" @click="session.next()">M14 下一页</button>
    </div>
    <div ref="host" class="m14-rows"></div>
    <p>本页已载入值 {{ saved.loaded_count }} 条；本分组未在本页载入值 {{ saved.not_loaded_count }} 条；本页之后尚余 {{ saved.remaining_entries }} 条。NOT_LOADED 保留原条目摘要，不当作空值。</p>
    <details class="m14-identity"><summary>核对 M14 原保存引用与本页条目摘要</summary>
     <dl><div v-for="(value,key) in saved.reference" :key="key"><dt>{{ key }}</dt><dd>{{ value }}</dd></div><div><dt>source_section_sha256</dt><dd>{{ saved.rebound.source_section_sha256 }}</dd></div></dl>
     <p>原条目 SHA256 与安全展示值 SHA256 分别标识原值和展示投影；未提供原始字节位置。</p>
     <ul><li v-for="entry in saved.entries" :key="entry.index">记录 {{ entry.index+1 }} · {{ entry.value_state }} · 原始 {{ entry.bytes }} bytes<br />原条目 SHA256：{{ entry.sha256 }}<br />展示投影 SHA256：{{ entry.projection_sha256 ?? '未载入展示值' }}</li></ul>
    </details>
   </template>
  </section>
 </details>
</template>
<style scoped>
.m14-window-evidence pre{white-space:pre-wrap;overflow-wrap:anywhere}.m14-saved{margin:18px;border:1px solid #c8d3dd;border-radius:10px;background:#fff;color:#21384d}.m14-saved>summary{padding:18px;cursor:pointer;color:#254d71;font-weight:600;scroll-margin-top:16px}.m14-saved>summary:focus{outline:2px solid #254d71;outline-offset:4px}.m14-saved>section{padding:0 18px 18px}.m14-saved p{line-height:1.7;overflow-wrap:anywhere}.m14-boundary{padding:12px;background:#eef3f8;border-radius:6px}.m14-warning{padding:12px;background:#fff8e8;border-left:3px solid #ad791d}.m14-controls,.m14-pagination{display:flex;flex-wrap:wrap;align-items:center;gap:10px;margin:14px 0}.m14-saved button{padding:8px 12px;cursor:pointer}.m14-controls button[aria-pressed=true]{background:#254d71;color:white}.m14-saved button:disabled{cursor:not-allowed;opacity:.55}.m14-identity{margin-top:16px}.m14-identity summary{cursor:pointer}.m14-identity dl{display:grid;gap:10px}.m14-identity dt{font-size:12px;color:#526579}.m14-identity dd{margin:4px 0;overflow-wrap:anywhere}.m14-identity li{margin:12px 0;overflow-wrap:anywhere}.m14-rows :deep(article){border:1px solid #d6dde5;border-radius:8px;padding:14px;margin:12px 0}.m14-rows :deep(p){line-height:1.65;overflow-wrap:anywhere}.m14-rows :deep(h4){font-size:1.05rem;margin:0 0 10px}.m14-rows :deep(summary){cursor:pointer}.m14-rows :deep(pre){white-space:pre-wrap;overflow-wrap:anywhere;font-size:.8rem}@media(max-width:650px){.m14-saved{margin:14px 12px}.m14-pagination{font-size:12px}}
</style>
