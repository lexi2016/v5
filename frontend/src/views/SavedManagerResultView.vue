<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, shallowRef } from 'vue';
import { M18SavedClient, SavedRunSession, type SavedEntry, type SavedRunState } from '../api/m18SavedResult';
const query = new URLSearchParams(window.location.search);
const requestedRun = ref(query.get('run_id') ?? '46596b03c2ab4e29b1219fd2e5eb698f');
const state = shallowRef<SavedRunState>({phase:'IDLE',descriptor:null,overview:null,section:'',page:null,error:'',canPrevious:false});
const session = new SavedRunSession(new M18SavedClient(), next => { state.value=next; });
async function reload() {
 const run=requestedRun.value.trim();
 if (/^[0-9a-f]{32}$/.test(run)) { const url=new URL(window.location.href);url.searchParams.set('run_id',run);window.history.replaceState(null,'',url); }
 await session.load(run);
}
function sectionChange(event: Event) { void session.select((event.target as HTMLSelectElement).value); }
const sectionLabels: Record<string,string> = { summary:'本次研究概览', stocks:'经理候选股票', gaps:'数据与证据缺口', materials:'研究材料', lanes:'研究任务', themes:'研究主题', market_screen:'市场筛选', announcement_reviewed_analysis:'公告复核结果', announcement_observation:'公告观察', us_mapping_research:'美股与港股映射', us_market_attention:'美股关注', rebound_research_observation:'反弹研究观察', plan_product:'已消费研究计划', runtime_gaps:'运行缺口', existing_material_bindings:'材料关联', rejected_relations:'未采用关联' };
function sectionLabel(key:string) { return sectionLabels[key] ?? key; }
function json(value:unknown):string { return JSON.stringify(value,null,2) ?? '未提供'; }
function record(entry:SavedEntry):Record<string,unknown>|null { return entry.value!==null && typeof entry.value==='object' && !Array.isArray(entry.value) ? entry.value as Record<string,unknown> : null; }
function title(entry:SavedEntry) { const row=record(entry);return row ? [row.symbol ?? row.stock_key ?? row.code, row.name ?? row.stock_name ?? row.title].filter(value=>typeof value==='string'||typeof value==='number').join(' · ') || `记录 ${entry.index+1}` : `记录 ${entry.index+1}`; }
function businessState(entry:SavedEntry) { const row=record(entry);return entry.value_state==='NOT_LOADED' ? 'NOT_LOADED' : row && typeof (row.status ?? row.state)==='string' ? String(row.status ?? row.state) : '已读取 · 业务状态未声明'; }
function excerpt(entry:SavedEntry) { const row=record(entry);const value=row ? row.gaps ?? row.missing ?? row.why_watch ?? row.reasons ?? row.reason ?? row.summary ?? entry.value : entry.value; const text=json(value);return text.length>700 ? text.slice(0,700)+'…（展开完整条目）' : text; }
onMounted(reload);
onBeforeUnmount(()=>session.close());
</script>

<template>
 <main class="dashboard-shell saved-run-view">
  <header class="page-header">
   <div><h1>V5 经理选股</h1><p>读取已保存的同一次运行结果。结果中的 PARTIAL、CANNOT_CONFIRM 与资料缺口按原样保留；只读研究，不触发采集或交易。</p></div>
   <span class="runtime-badge">已保存结果 · READ_ONLY</span>
  </header>
  <form class="control-panel" @submit.prevent="reload">
   <label>运行 ID<input v-model="requestedRun" aria-label="运行 ID" spellcheck="false" autocomplete="off" /></label>
   <button type="submit">{{ state.phase==='LOADING' ? '重新读取' : '读取已保存结果' }}</button>
   <span class="runtime-state">{{ state.descriptor ? `目标日 ${state.descriptor.target_date}` : '目标日尚未确认' }}</span>
  </form>
  <nav class="entry-nav" aria-label="功能入口">
   <button type="button" class="active" aria-current="page">经理已保存结果</button>
   <button type="button" disabled>阶段选股 · 未接入</button>
   <button type="button" disabled>研报决策台 · 未接入</button>
   <button type="button" disabled>公告分析 · 未接入</button>
  </nav>
  <p class="navigation-status">当前页面只确认本次已保存结果的读取。接口 READY 表示保存产物可读取，不代表业务完整、全部模块可用或交易许可。</p>
  <p v-if="state.phase==='LOADING'" class="task-message" role="status" aria-live="polite">正在读取同一运行的有界数据页…</p>
  <p v-if="state.phase==='CANNOT_CONFIRM'" class="task-message task-error" role="alert">CANNOT_CONFIRM · 当前请求未能确认，未显示旧结果。{{ state.error }}</p>
  <section v-if="state.descriptor" class="task-status-view saved-identity" aria-label="结果身份">
   <h2>本次结果</h2>
   <dl><div><dt>运行 ID</dt><dd>{{ state.descriptor.run_id }}</dd></div><div><dt>目标日</dt><dd>{{ state.descriptor.target_date }}</dd></div><div><dt>保存描述生成时间</dt><dd>{{ state.descriptor.generated_at }}</dd></div></dl>
   <details><summary>核对同一运行与摘要</summary><dl>
    <div v-for="(value,key) in state.descriptor.identity" :key="key"><dt>{{ key }}</dt><dd>{{ value }}</dd></div>
    <div><dt>离线 generation（不是发布 generation）</dt><dd>{{ state.descriptor.generation_id }}</dd></div>
    <div><dt>profile SHA256</dt><dd>{{ state.descriptor.profile_sha256 }}</dd></div>
    <div><dt>manifest SHA256</dt><dd>{{ state.overview?.manifest_sha256 ?? '尚未读取' }}</dd></div>
   </dl></details>
  </section>
  <div v-if="state.overview" class="task-counts"><article v-for="key in ['stocks','materials','gaps']" :key="key"><span>{{ sectionLabel(key) }}</span><strong>{{ state.overview.sections[key]?.total ?? '未提供' }}</strong></article></div>
  <section v-if="state.overview" class="task-status-view saved-sections" aria-label="已保存内容">
   <div class="control-panel"><label>内容分区<select :value="state.section" aria-label="内容分区" @change="sectionChange"><option v-for="(meta,key) in state.overview.sections" :key="key" :value="key">{{ sectionLabel(String(key)) }} · {{ meta.total }} 条 · {{ meta.kind }}</option></select></label><span>按原始分区分页读取，每页最多 32 条</span><button v-if="state.overview.sections.gaps" type="button" @click="session.select('gaps')">查看缺口 · {{ state.overview.sections.gaps.total }}</button><button v-if="state.overview.sections.materials" type="button" @click="session.select('materials')">研究材料 · {{ state.overview.sections.materials.total }}</button></div>
   <p v-if="!Object.keys(state.overview.sections).length" class="task-message">保存产物没有可展示的分区。未推断业务成功。</p>
   <template v-if="state.page">
    <div class="saved-pagination"><button type="button" :disabled="!state.canPrevious || state.phase==='LOADING'" @click="session.previous()">上一页</button><span>当前 {{ state.page.entries.length ? state.page.offset+1 : 0 }}–{{ state.page.offset+state.page.entries.length }} / {{ state.page.matched_total }} 条</span><button type="button" :disabled="!state.page.next_cursor || state.phase==='LOADING'" @click="session.next()">下一页</button></div>
    <p v-if="state.page.matched_total===0" class="task-message">此分区原始值为空数组（0 条）。这不代表其他内容已就绪。</p>
    <div v-else class="saved-table-scroll"><table><thead><tr><th>条目</th><th>原始状态</th><th>内容与缺口</th></tr></thead><tbody>
     <tr v-for="entry in state.page.entries" :key="`${state.section}:${entry.index}`"><th scope="row">{{ title(entry) }}</th><td>{{ businessState(entry) }}</td><td>
      <template v-if="entry.value_state==='LOADED'"><pre>{{ excerpt(entry) }}</pre><details><summary>完整条目与来源摘要</summary><pre>{{ json(entry.value) }}</pre><p>条目 SHA256：{{ entry.sha256 }}</p><p>原始字节：{{ entry.bytes }}；位置：{{ entry.offset }}</p></details></template>
      <template v-else><p>条目尚未加载：{{ entry.reason ?? 'NOT_LOADED' }}。保留缺口，不替换为空值。</p><p>原始字节：{{ entry.bytes }}；SHA256：{{ entry.sha256 }}</p></template>
     </td></tr>
    </tbody></table></div>
    <p class="task-message">本页只展示已读取的条目；其余未加载数：{{ state.page.not_loaded_count }}。大条目超出单条或页面上限时保持 NOT_LOADED。</p>
   </template>
  </section>
 </main>
</template>
<style scoped>
.saved-run-view .control-panel{flex-wrap:wrap}.saved-run-view .control-panel input{width:min(36ch,75vw)}.saved-run-view .entry-nav{flex-wrap:wrap}.saved-run-view button:disabled{cursor:not-allowed}.saved-identity{padding:18px}.saved-identity h2{margin:0 0 12px;font-size:18px}.saved-identity dl{display:grid;gap:10px}.saved-identity dt{font-size:12px;color:#526579}.saved-identity dd{margin:4px 0;overflow-wrap:anywhere;font-size:13px}.saved-sections .control-panel{padding:16px}.saved-pagination{display:flex;gap:16px;align-items:center;padding:14px 18px}.saved-pagination button{padding:7px 12px}.saved-table-scroll{overflow:auto;margin:0 18px}.saved-table-scroll table{width:100%;border-collapse:collapse;font-size:13px}.saved-table-scroll th,.saved-table-scroll td{text-align:left;padding:12px;border:1px solid #c8d3dd;vertical-align:top}.saved-table-scroll thead{background:#e3ebf2}.saved-table-scroll th:first-child{min-width:130px}.saved-table-scroll pre{margin:0;white-space:pre-wrap;overflow-wrap:anywhere;max-width:850px;font-family:inherit;line-height:1.6}.saved-table-scroll details{margin-top:12px}.saved-table-scroll details p{overflow-wrap:anywhere}.saved-table-scroll summary,.saved-identity summary{cursor:pointer;color:#254d71}@media(max-width:650px){.saved-run-view .page-header{padding:18px;flex-direction:column;gap:12px}.saved-run-view .control-panel,.saved-run-view .entry-nav{padding:12px 18px}.saved-run-view .task-status-view{margin:14px 12px}.saved-run-view .navigation-status{margin:12px}.saved-pagination{gap:8px;font-size:12px}}
</style>
