<script setup lang="ts">
import {computed, onBeforeUnmount, ref, shallowRef} from 'vue';
import {SavedIntradayResearchSession, type IntradayResearchState} from '../api/m11SavedResearch';
const date = ref('');
const state = shallowRef<IntradayResearchState>({phase: 'IDLE', result: null, error: ''});
const saved = computed(() => state.value.phase === 'LOADED' && state.value.result?.status === 'SAVED_RESEARCH_REVIEW_REQUIRED' ? state.value.result : null);
const session = new SavedIntradayResearchSession(next => { state.value = next; });
function load() { void session.load(date.value.trim()); }
function onToggle(event: Event) {
  if ((event.currentTarget as HTMLDetailsElement).open && state.value.phase === 'IDLE') load();
}
onBeforeUnmount(() => session.close());
</script>
<template>
 <details id="m11-saved-research" class="m11-research" @toggle="onToggle">
  <summary>M11 盘中研究 · 读取已保存产物</summary>
  <section aria-label="M11 已保存盘中研究">
   <p>只读取已绑定、经摘要核验的原研究产物。此入口不启动 capture 或 generate，read_record 不生成研究报告；缺少合格保存材料时保留 WAITING。</p>
   <p>VERIFIED_PERSISTENCE_ONLY 仅确认保存证据，业务结论仍待复核。六槽状态只说明该槽是否绑定保存产物，未声明自然日完整验收通过，不触发交易。</p>
   <form @submit.prevent="load">
    <label>交易日（可留空读取已绑定运行）<input v-model="date" placeholder="YYYYMMDD" inputmode="numeric" maxlength="8" aria-label="M11 交易日" /></label>
    <button type="submit">读取 M11 已保存研究</button>
   </form>
   <p v-if="state.phase==='IDLE'">尚未读取保存结果。</p>
   <p v-else-if="state.phase==='LOADING'" role="status">正在核验已保存研究…</p>
   <p v-else-if="state.phase==='WAITING'" role="status">WAITING · 暂无可确认的合格保存结果。{{ state.result?.reason_codes.join(' · ') }}</p>
   <p v-else-if="state.phase==='CANNOT_CONFIRM'" role="alert">CANNOT_CONFIRM · 当前读取失败，已清除旧结果。{{ state.error }}</p>
   <div v-if="state.result?.slots" class="m11-slots" role="list" aria-label="M11 六槽保存状态">
    <p v-for="row in state.result.slots" :key="row.slot" :data-slot="row.slot" role="listitem"><strong>{{ row.slot }}</strong> · {{ row.status }}</p>
   </div>
   <article v-if="saved" data-testid="m11-saved-content">
    <p v-if="saved.data_kind==='SYNTHETIC'" role="note">SYNTHETIC · 合成测试资料，不是真实盘中研究。</p>
    <p v-else>资料类型：{{ saved.data_kind }} · 尚未声明自然日端到端验收通过</p>
    <h3>已保存研究 · 待复核</h3>
    <p>{{ saved.status }} · 业务原状态：{{ saved.business_status }}</p>
    <p>目标日 {{ saved.reference.trade_date }} · 操作 {{ saved.reference.operation }} · 绑定槽 {{ saved.reference.slot }} · 原运行 {{ saved.reference.run_id }}</p>
    <p>证据：{{ saved.evidence_status }} · {{ saved.reason_codes.join(' · ') }}</p>
    <p v-if="saved.reference.operation==='generate'">日研究产物不代表六个盘中槽已完成采集；未绑定的槽继续显示 WAITING。</p>
    <section v-if="saved.research.intraday_research" aria-label="M11 盘中研究原业务内容"><h4>盘中研究 · 原业务内容与缺口</h4><pre>{{ JSON.stringify(saved.research.intraday_research,null,2) }}</pre></section>
    <section v-if="saved.research.research_review" aria-label="M11 研究复核原业务内容"><h4>研究复核 · 原业务内容与缺口</h4><pre>{{ JSON.stringify(saved.research.research_review,null,2) }}</pre></section>
    <details><summary>核验身份与摘要</summary><pre>{{ JSON.stringify(saved.reference,null,2) }}</pre></details>
   </article>
  </section>
 </details>
</template>
<style scoped>
.m11-research{margin:18px;border:1px solid #c8d3dd;border-radius:8px;padding:16px;scroll-margin-top:16px}.m11-research>summary{font-weight:600;color:#254d71;cursor:pointer}.m11-research summary:focus{outline:2px solid #254d71;outline-offset:4px}.m11-research p{line-height:1.65;font-size:13px;overflow-wrap:anywhere}.m11-research form{display:flex;gap:12px;flex-wrap:wrap;align-items:end}.m11-research label{display:grid;gap:6px}.m11-research input,.m11-research button{padding:8px}.m11-research pre{white-space:pre-wrap;overflow-wrap:anywhere;max-height:420px;overflow:auto;font-size:13px}.m11-research h3{font-size:17px}.m11-slots{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:8px;margin-top:14px}.m11-slots p{margin:0;padding:8px;background:#eef3f7;border-radius:4px}
</style>
