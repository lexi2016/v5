<script setup lang="ts">
import {computed, onBeforeUnmount, ref, shallowRef} from 'vue';
import {SavedPublicResearchSession, type PublicResearchState} from '../api/m16SavedResearch';
const date = ref('');
const state = shallowRef<PublicResearchState>({phase: 'IDLE', result: null, error: ''});
const saved = computed(() => state.value.phase === 'LOADED' && state.value.result?.status === 'SAVED_PUBLIC_RESEARCH_REVIEW_REQUIRED' ? state.value.result : null);
const session = new SavedPublicResearchSession(next => {state.value = next;});
function load() {void session.load(date.value.trim());}
function onToggle(event: Event) {
  if ((event.currentTarget as HTMLDetailsElement).open && state.value.phase === 'IDLE') load();
}
function json(value: unknown) {return JSON.stringify(value, null, 2) ?? '未提供';}
function display(value: unknown) {return typeof value === 'string' ? value : json(value);}
function rowTitle(row: Record<string, unknown>, index: number) {
  return [row.code ?? row.symbol ?? row.stock_key, row.name ?? row.stock_name].filter(value => typeof value === 'string' || typeof value === 'number').join(' · ') || `研究条目 ${index + 1}`;
}
function rowDetails(row: Record<string, unknown>) {
  return Object.entries(row).filter(([key]) => !['code', 'symbol', 'stock_key', 'name', 'stock_name', 'status', 'facts'].includes(key));
}
function factRows(value: unknown): Record<string, unknown>[] | null {
  return Array.isArray(value) && value.every(row => row !== null && typeof row === 'object' && !Array.isArray(row)) ? value : null;
}
function factDetails(fact: Record<string, unknown>) {
  return Object.entries(fact).filter(([key]) => !['statement_cn', 'statement'].includes(key));
}
const fieldLabels: Record<string, string> = {
  thesis_cn: '研究论点', financial_research: '财务研究', financials: '财务资料', research: '研究正文', summary: '研究摘要',
  inferences_cn: '原研究推断', counterevidence_cn: '反证与疑点', confirmation_conditions: '确认条件', invalidation_conditions: '失效条件',
  research_next_action: '原研究下一步建议（仅展示）', research_recommendation: '原研究建议（仅展示）',
  sources: '来源', source: '来源', source_url: '来源网址（仅文本）', source_reason: '来源说明', source_excerpt: '原文摘录', source_sha256: '来源 SHA256',
  fact_kind: '事实类型', locator: '定位', page: '页码', fields: '原始字段', observation: '观察', stage_observation: '阶段观察',
  gaps: '资料缺口', reason_codes: '原因', reasons: '原因',
};
onBeforeUnmount(() => session.close());
</script>
<template>
 <details id="m16-saved-research" class="m16-research" @toggle="onToggle">
  <summary>M16 经理公开资料研究 · 读取已保存产物</summary>
  <section aria-label="M16 已保存公开资料研究">
   <p>只读取已绑定的原经理公开资料研究 product、job 与 receipt。不启动 provider 或 ensure，不生成新研究，不触发交易；缺少合格保存材料时保留 WAITING。</p>
   <p>VERIFIED_PERSISTENCE_ONLY 仅确认保存证据，不代表真实业务完成、自然日验收通过或可执行。原业务状态与资料缺口按原样保留，研究结论仍待复核。</p>
   <form @submit.prevent="load">
    <label>交易日（可留空读取已绑定结果）<input v-model="date" placeholder="YYYYMMDD" inputmode="numeric" maxlength="8" aria-label="M16 交易日" /></label>
    <button type="submit">读取 M16 已保存研究</button>
   </form>
   <p v-if="state.phase === 'IDLE'">尚未读取保存结果。</p>
   <p v-else-if="state.phase === 'LOADING'" role="status">正在核验已保存公开资料研究…</p>
   <p v-else-if="state.phase === 'WAITING'" role="status">WAITING · 暂无可确认的合格保存结果。{{ state.result?.reason_codes.join(' · ') }}</p>
   <p v-else-if="state.phase === 'CANNOT_CONFIRM'" role="alert">CANNOT_CONFIRM · 当前读取未能确认，已清除旧结果。{{ state.result?.reason_codes.join(' · ') || state.error }}</p>
   <article v-if="saved" data-testid="m16-saved-content">
    <p v-if="saved.data_kind === 'SYNTHETIC'" class="synthetic-note" role="note">SYNTHETIC · 合成测试资料，不是真实公开资料研究。</p>
    <p v-else>资料类型：{{ saved.data_kind }} · 尚未声明真实业务完成或自然日验收通过</p>
    <h3>已保存公开资料研究 · 待复核</h3>
    <p>{{ saved.status }} · 业务原状态：{{ saved.business_status }}</p>
    <p>目标日 {{ saved.reference.trade_date }} · 原任务 {{ saved.reference.job_id }} · generation {{ saved.reference.generation }} · attempt {{ saved.reference.attempt }}</p>
    <p>证据：{{ saved.evidence_status }} · {{ saved.reason_codes.join(' · ') }}</p>
    <section aria-label="M16 原公开资料研究条目">
     <p v-if="!saved.product.rows">原产物未提供 rows；未推断研究结果为空或业务成功，请核对下方原产物。</p>
     <p v-else-if="saved.product.rows.length === 0">原产物 rows 为空（0 条），不代表研究完整或业务成功。</p>
     <article v-for="(row, index) in saved.product.rows" :key="index" class="research-row" data-testid="m16-research-row">
      <h4>{{ rowTitle(row, index) }}</h4>
      <p>条目原状态：{{ row.status ?? '未声明' }}</p>
      <section v-if="row.facts !== undefined" aria-label="公开资料原始事实">
       <h5>事实与来源 · 原始内容</h5>
       <ol v-if="factRows(row.facts)" class="fact-list">
        <li v-for="(fact, factIndex) in factRows(row.facts)" :key="factIndex">
         <p>{{ display(fact.statement_cn ?? fact.statement ?? '原事实未提供正文') }}</p>
         <dl><div v-for="[key, content] in factDetails(fact)" :key="key"><dt>{{ fieldLabels[key] ?? key }}</dt><dd><pre>{{ display(content) }}</pre></dd></div></dl>
        </li>
       </ol>
       <pre v-else>{{ json(row.facts) }}</pre>
      </section>
      <section v-for="[key, content] in rowDetails(row)" :key="key"><h5>{{ fieldLabels[key] ?? key }}</h5><pre>{{ display(content) }}</pre></section>
     </article>
    </section>
    <details><summary>核验身份与保存摘要</summary><p>commit_sha256（规范化对象摘要）：{{ saved.reference.commit_sha256 }}</p><p>commit_file_sha256（原文件摘要）：{{ saved.reference.commit_file_sha256 }}</p><pre>{{ json(saved.reference) }}</pre></details>
    <details><summary>原研究 product · 完整业务内容与缺口</summary><pre>{{ json(saved.product) }}</pre></details>
    <details><summary>原任务 job · 保存记录</summary><pre>{{ json(saved.job) }}</pre></details>
    <details><summary>原回执 receipt · 保存记录</summary><pre>{{ json(saved.receipt) }}</pre></details>
   </article>
  </section>
 </details>
</template>
<style scoped>
.m16-research{margin:18px;border:1px solid #c8d3dd;border-radius:8px;padding:16px;scroll-margin-top:16px}.m16-research>summary{font-weight:600;color:#254d71;cursor:pointer}.m16-research summary:focus{outline:2px solid #254d71;outline-offset:4px}.m16-research p{line-height:1.65;font-size:13px;overflow-wrap:anywhere}.m16-research form{display:flex;gap:12px;flex-wrap:wrap;align-items:end}.m16-research label{display:grid;gap:6px}.m16-research input,.m16-research button{padding:8px}.m16-research pre{white-space:pre-wrap;overflow-wrap:anywhere;max-height:420px;overflow:auto;font-size:13px}.m16-research h3{font-size:17px}.m16-research h4{font-size:15px;margin:0}.m16-research h5{font-size:13px;margin:12px 0 6px}.m16-research details{margin-top:12px}.m16-research details summary{cursor:pointer;color:#254d71}.research-row{border:1px solid #d6dde5;border-radius:6px;padding:14px;margin:12px 0}.synthetic-note{padding:10px;border:1px solid #af782e;background:#fff5df;font-weight:600}
.fact-list{padding-left:24px}.fact-list li{margin:12px 0}.fact-list dl{display:grid;gap:6px;font-size:13px}.fact-list dt{color:#526579}.fact-list dd{margin:2px 0 0}.fact-list pre{margin:0}
</style>
