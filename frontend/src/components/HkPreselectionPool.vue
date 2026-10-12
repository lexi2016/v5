<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, shallowRef } from 'vue';
import { HkPreselectionSession, type HkPreselectionState } from '../api/hkPreselectionPool';

const state = shallowRef<HkPreselectionState>({ phase: 'IDLE', result: null, error: '' });
const session = new HkPreselectionSession(next => { state.value = next; });
// Put identity fields first, then retain every other original field. Never sort rows or scores.
const fields = computed(() => {
 const original = new Set((state.value.result?.artifact.rows ?? []).flatMap(row => Object.keys(row)));
 const leading = ['pool_rank', 'symbol', 'stock_name', 'score_prob_active', 'target_date', 'signal_date'];
 return Array.from(new Set([...leading.filter(field => original.has(field)), ...original]));
});
function cell(value: unknown): string {
 if (value === undefined) return '（无此字段）';
 if (value === '') return '""';
 return typeof value === 'string' ? value : JSON.stringify(value);
}
function json(value: unknown) { return JSON.stringify(value, null, 2); }
onMounted(() => session.load());
onBeforeUnmount(() => session.close());
</script>

<template>
 <section class="hk-preselection" aria-label="M06 港股通已提交 Top100 只读预选池" :aria-busy="state.phase === 'LOADING'">
  <div class="hk-header">
   <h2>M06 港股通 Top100 · 已提交预选池</h2>
   <button type="button" @click="session.load()">读取 M06 已提交结果</button>
  </div>
  <p>只读已配置的 committed reference，按原始字段与原顺序展示全部 100 行。读取不会生成、重排或提交预选池。</p>
  <p class="hk-boundary">仅供研究观察 · model_weights_reverified=false · formal_eligibility_verified=false · natural_verified=false。未重新验证模型权重，不代表正式准入、PIT 或自然运行验证。</p>
  <p class="hk-boundary">research_only=true · production_allowed=false · buy_gate_updated=false · orders_sent=false。原始 stage_selection_eligible 字段不提升以上边界。</p>
  <p v-if="state.phase === 'LOADING'" role="status" aria-live="polite">正在读取 M06 已提交结果…</p>
  <p v-else-if="state.phase === 'NOT_CONFIGURED'" role="status">NOT_CONFIGURED · M06 尚未配置已提交引用。{{ state.error }}</p>
  <p v-else-if="!state.result" role="status">CANNOT_CONFIRM · 无法确认 M06 已提交结果。{{ state.error }}</p>
  <template v-if="state.result">
   <dl class="hk-identity">
    <div><dt>目标日期 target_date</dt><dd>{{ state.result.committed_reference.target_date }}</dd></div>
    <div><dt>信号日期 signal_date</dt><dd>{{ state.result.committed_reference.signal_date }}</dd></div>
    <div><dt>资格来源日期 eligibility_source_date</dt><dd>{{ state.result.committed_reference.eligibility_source_date }}</dd></div>
    <div><dt>研究截止 research_cutoff</dt><dd>{{ state.result.committed_reference.research_cutoff }}</dd></div>
    <div><dt>原始状态 / 运行方式</dt><dd>{{ state.result.artifact.status }} / {{ state.result.committed_reference.execution_mode }}</dd></div>
    <div><dt>fixture_only</dt><dd>{{ state.result.fixture_only }}{{ state.result.fixture_only ? ' · 合成测试数据，非实际源结果' : '' }}</dd></div>
    <div><dt>源运行 source_run_id</dt><dd>{{ state.result.artifact.source_run_id }}</dd></div>
    <div><dt>源产物 SHA256</dt><dd>{{ state.result.artifact.source_sha256 }}</dd></div>
    <div><dt>源 manifest / receipt SHA256</dt><dd>{{ state.result.artifact.source_manifest_sha256 }}<br>{{ state.result.artifact.source_receipt_sha256 }}</dd></div>
    <div><dt>已提交产物 artifact_relative</dt><dd>{{ state.result.committed_reference.artifact_relative }}</dd></div>
    <div><dt>已提交产物 SHA256</dt><dd>{{ state.result.committed_reference.artifact_sha256 }}</dd></div>
    <div><dt>计算身份 computation_sha256</dt><dd>{{ state.result.committed_reference.computation_sha256 }}</dd></div>
   </dl>
   <p>实际载入 {{ state.result.artifact.rows.length }} / 100 行 · 表格可横向滚动查看全部原始字段。空字符串显示为 ""；原始分数字符串保留其精度。</p>
   <div class="hk-table-scroll" tabindex="0" role="region" aria-label="M06 全部 100 行原始字段，可横向滚动">
    <table>
     <caption>港股通 Top100 原始字段 · 原顺序 · WATCH_ONLY</caption>
     <thead><tr><th v-for="field in fields" :key="field" scope="col">{{ field }}</th></tr></thead>
     <tbody><tr v-for="row in state.result.artifact.rows" :key="row.symbol" data-m06-row><td v-for="field in fields" :key="field">{{ cell(row[field]) }}</td></tr></tbody>
    </table>
   </div>
   <details><summary>原始 artifact 与 committed reference（完整字段）</summary><pre>{{ json(state.result) }}</pre></details>
  </template>
 </section>
</template>

<style scoped>
.hk-preselection{border-top:1px solid #c8d3dd;margin-top:22px;padding-top:20px;min-width:0}.hk-header{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px}.hk-header h2{font-size:18px;margin:0}.hk-header button{padding:8px 12px}.hk-preselection p{font-size:13px;line-height:1.65;overflow-wrap:anywhere}.hk-boundary{color:#6b4b19}.hk-identity{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px 18px;font-size:12px}.hk-identity div{min-width:0}.hk-identity dt{color:#526579}.hk-identity dd{margin:3px 0 0;overflow-wrap:anywhere;line-height:1.5}.hk-table-scroll{overflow:auto;max-height:620px;border:1px solid #c8d3dd;border-radius:6px}.hk-table-scroll:focus-visible{outline:2px solid #254d71;outline-offset:3px}table{border-collapse:collapse;font-size:12px;white-space:nowrap;width:100%}caption{text-align:left;padding:10px;font-weight:600}th,td{text-align:left;padding:8px 10px;border-bottom:1px solid #e0e6ec}th{position:sticky;top:0;background:#edf2f7;z-index:1}tbody tr:nth-child(even){background:#f7f9fc}details{margin-top:14px}summary{cursor:pointer;font-size:13px;color:#254d71}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px;max-height:320px;overflow:auto}@media(max-width:650px){.hk-identity{grid-template-columns:1fr}}
</style>
