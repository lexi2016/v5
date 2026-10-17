<script setup lang="ts">
import M16SavedResearch from '../components/M16SavedResearch.vue';
import M11SavedResearch from '../components/M11SavedResearch.vue';
import M12SavedVideo from '../components/M12SavedVideo.vue';
import SourceBundleStatus from '../components/SourceBundleStatus.vue';
import { computed, nextTick, onBeforeUnmount, onMounted, ref, shallowRef, watchEffect } from 'vue';
import { M18SavedClient, SavedRunSession, type SavedEntry, type SavedRunState, chooseSection, REBOUND_GROUPS, type ReboundGroup } from '../api/m18SavedResult';
import { renderSavedUsMappingMatches } from '../manager-selection/usMappingCoverage';
import { renderSavedAnnouncementReferences } from '../manager-selection/announcementAnalysis';
import { renderSavedReboundReferences, reboundGroupLabels } from '../manager-selection/reboundPanelObservation';
const usMappingHost=ref<HTMLElement|null>(null);
const reboundHost=ref<HTMLElement|null>(null);
const announcementHost=ref<HTMLElement|null>(null);
const resultHeading=ref<HTMLElement|null>(null);
const sourceDisclosure=ref<HTMLDetailsElement|null>(null);
const sourceSummary=ref<HTMLElement|null>(null);
const sourceExpanded=ref(false);
const publicResearchHost=ref<HTMLElement|null>(null);
async function openPublicResearch(){
 const target=publicResearchHost.value?.querySelector<HTMLDetailsElement>('#m16-saved-research');
 if(!target)return;target.open=true;await nextTick();focusAndReveal(target.querySelector<HTMLElement>('summary'));
}
const videoHost=ref<HTMLElement|null>(null);
const intradayResearchHost=ref<HTMLElement|null>(null);
async function openIntradayResearch(){
 const target=intradayResearchHost.value?.querySelector<HTMLDetailsElement>('#m11-saved-research');
 if(!target)return;target.open=true;await nextTick();focusAndReveal(target.querySelector<HTMLElement>('summary'));
}
async function openVideo(){
 const target=videoHost.value?.querySelector<HTMLDetailsElement>('#m12-saved-video');
 if(!target)return;target.open=true;await nextTick();focusAndReveal(target.querySelector<HTMLElement>('summary'));
}
function focusAndReveal(target:HTMLElement|null) {
 if (!target) return;
 target.focus({preventScroll:true});
 target.scrollIntoView?.({block:'start',behavior:'auto'});
}
async function selectSection(section:string,group:ReboundGroup='strict') {
 // The session remains the only request/identity owner. Move to the result
 // immediately, including its loading/error state, rather than after the read.
 const pending=session.select(section,group);
 await nextTick();
 focusAndReveal(resultHeading.value);
 await pending;
}
async function openSources() {
 if (!sourceDisclosure.value) return;
 sourceDisclosure.value.open=true;
 sourceExpanded.value=true;
 await nextTick();
 focusAndReveal(sourceSummary.value);
}
async function openAStage() {
 await openSources();
 const target=sourceDisclosure.value?.querySelector<HTMLDetailsElement>('#m07-saved-stage');
 if (!target) return;
 target.open=true;
 await nextTick();
 focusAndReveal(target.querySelector<HTMLElement>('summary'));
}
async function openResearch() {
 await openSources();
 const target=sourceDisclosure.value?.querySelector<HTMLDetailsElement>('#m04-saved-research');
 if (!target) return;
 target.open=true;
 await nextTick();
 focusAndReveal(target.querySelector<HTMLElement>('summary'));
}
function onSourceToggle(event:Event) {
 sourceExpanded.value=(event.currentTarget as HTMLDetailsElement).open;
}
const query = new URLSearchParams(window.location.search);
function compactTargetDate(value:string):string|null {
 const compact=value.replaceAll('-','');
 if(!/^\d{8}$/.test(compact))return null;
 const year=Number(compact.slice(0,4)),month=Number(compact.slice(4,6)),day=Number(compact.slice(6,8));
 if(year<1||month<1||month>12||day<1)return null;
 const leap=year%4===0&&(year%100!==0||year%400===0);
 const days=[31,leap?29:28,31,30,31,30,31,31,30,31,30,31];
 return day<=days[month-1]?compact:null;
}
function isoTargetDate(value:string):string {return value.length===8 ? value.slice(0,4)+'-'+value.slice(4,6)+'-'+value.slice(6,8) : '';}
const requestedRun = ref(query.get('run_id') ?? '');
const initialTargetDate=query.get('target_date') ?? query.get('date') ?? '';
const targetDate=ref(compactTargetDate(initialTargetDate)===initialTargetDate ? initialTargetDate : '');
const targetDateInput=computed(()=>isoTargetDate(targetDate.value));
const dateLookup=ref('');
const dateLookupBusy=ref(false);
const state = shallowRef<SavedRunState>({phase:'IDLE',descriptor:null,overview:null,section:'',page:null,error:'',canPrevious:false});
const session = new SavedRunSession(new M18SavedClient(), next => { state.value=next; });
async function reload() {
 const run=requestedRun.value.trim();
 if (run === '' || /^[0-9a-f]{32}$/.test(run)) { const url=new URL(window.location.href);if(run)url.searchParams.set('run_id',run);else url.searchParams.delete('run_id');window.history.replaceState(null,'',url); }
 await session.load(run);
}
async function loadRunForDate() {
 const date=compactTargetDate(targetDate.value);
 if(!date){dateLookup.value='目标交易日无效，请选择有效日期。';return;}
 dateLookupBusy.value=true;
 dateLookup.value='正在读取该日期的已保存经理结果…';
 const url=new URL(window.location.href);
 url.searchParams.set('target_date',date);
 url.searchParams.set('date',date);
 window.history.replaceState(null,'',url.pathname+url.search);
 try {
  const response=await fetch(`/api/v4/manager/research/workspace?date=${encodeURIComponent(date)}&view=auto`,{cache:'no-store'});
  if(!response.ok)throw new Error(`MANAGER_DATE_LOOKUP_HTTP_${response.status}`);
  const body=await response.json() as Record<string,unknown>;
  const payload=(body.payload && typeof body.payload==='object' && !Array.isArray(body.payload) ? body.payload : body) as Record<string,unknown>;
  const product=payload.plan_product as Record<string,unknown>|undefined;
  if(!product || product.consumed!==true) throw new Error('MANAGER_DATE_LOOKUP_NOT_AVAILABLE');
  if(payload.target_trade_date!==date ||
    typeof product.run_id!=='string' || !/^[0-9a-f]{32}$/.test(product.run_id) ||
    typeof product.sha256!=='string' || !/^[0-9a-f]{64}$/.test(product.sha256)) {
   throw new Error('MANAGER_DATE_LOOKUP_IDENTITY_MISMATCH');
  }
  requestedRun.value=product.run_id;
  url.searchParams.set('run_id',product.run_id);
  window.history.replaceState(null,'',url.pathname+url.search);
  dateLookup.value=`找到目标日 ${date} 的已消费保存运行，正在核验完整结果…`;
  await reload();
  if(state.value.descriptor && state.value.descriptor.target_date===date && state.value.descriptor.run_id===product.run_id) {
   dateLookup.value=`已读取目标日 ${date} 的保存运行；业务完整性仍以各原状态与缺口为准。`;
  } else if(state.value.phase==='CANNOT_CONFIRM') {
   dateLookup.value='已找到日期匹配的引用，但完整结果读取/身份核验未通过。请查看下方技术诊断。';
  }
 } catch(error) {
  const raw=error instanceof Error ? error.message : 'UNKNOWN_ERROR';
  if(raw.includes('MANAGER_DATE_LOOKUP_HTTP_404')) dateLookup.value=`目标日 ${date} 的只读查询接口未接线（${raw}）。`;
  else if(raw.includes('MANAGER_DATE_LOOKUP_HTTP_503') || raw.includes('MANAGER_DATE_LOOKUP_NOT_AVAILABLE')) dateLookup.value=`目标日 ${date} 暂无可读取的已保存运行或来源绑定（${raw}）；未回退到 latest。`;
  else if(raw.includes('MANAGER_DATE_LOOKUP_IDENTITY_MISMATCH')) dateLookup.value=`目标日 ${date} 的返回日期、运行 ID 或 SHA 身份不一致（${raw}），已拒绝读取。`;
  else dateLookup.value=`目标日 ${date} 的已保存运行读取失败（${raw}）。`;
 } finally {dateLookupBusy.value=false;}
}

const isUsMapping=computed(()=>state.value.section==='us_mapping_research');
const isRebound=computed(()=>state.value.section==='rebound_research_observation');
function selectRebound(group:ReboundGroup='strict') { void selectSection('rebound_research_observation',group); }
const isAnnouncement=computed(()=>state.value.section==='announcement_reviewed_analysis');
function showManager() { const sections={...state.value.overview?.sections};delete sections.announcement_reviewed_analysis;delete sections.rebound_research_observation;delete sections.us_mapping_research;const section=chooseSection(sections);if(section)void selectSection(section); }
watchEffect(()=>{const page=state.value.page,host=announcementHost.value;if(host&&page?.projection==='announcement_references')renderSavedAnnouncementReferences(host,page);const reboundPage=state.value.page,reboundTarget=reboundHost.value;if(reboundTarget&&reboundPage?.projection==='rebound_references')renderSavedReboundReferences(reboundTarget,reboundPage);const usPage=state.value.page,usTarget=usMappingHost.value;if(usTarget&&usPage?.projection==='us_mapping_matches')renderSavedUsMappingMatches(usTarget,usPage);},{flush:'post'});
function sectionChange(event: Event) { void selectSection((event.target as HTMLSelectElement).value); }
const sectionLabels: Record<string,string> = { summary:'本次研究概览', stocks:'经理候选股票', gaps:'数据与证据缺口', materials:'研究材料', lanes:'研究任务', themes:'研究主题', market_screen:'市场筛选', announcement_reviewed_analysis:'公告研究股票', announcement_observation:'公告观察', us_mapping_research:'美股与港股映射', us_market_attention:'美股关注', rebound_research_observation:'反弹研究观察', plan_product:'已消费研究计划', runtime_gaps:'运行缺口', existing_material_bindings:'材料关联', rejected_relations:'未采用关联' };
function sectionLabel(key:string) { return sectionLabels[key] ?? key; }
function explainError(raw:string) {
 if(/M18_HTTP_503|MODULE_RESULT_NOT_AVAILABLE|MODULE_BINDING_NOT_CONFIGURED/.test(raw)) return '当前没有可核验的已保存产物或来源绑定。请先确认真实输入、保存回执和运行 ID；这不代表结果为 0 条。';
 if(/MODULE_RESULT_INVALID|CONTRACT_SHA_INVALID|SOURCE_IDENTITY_REQUIRED/.test(raw)) return '返回结果的身份或完整性校验未通过。请检查绑定、来源 SHA 和保存回执；旧结果不会作为本次成功展示。';
 if(/ROUTE_NOT_CONFIGURED|404/.test(raw)) return '当前读取接口未接线或目标资源不存在。请检查部署版本和只读路由配置。';
 if(/NETWORK|ECONNREFUSED|fetch/i.test(raw)) return '无法连接读取服务。请确认服务已启动且地址可达后重试。';
 return '读取失败，系统未将其当作成功或空结果。请查看技术诊断并核对请求身份。';
}
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
  <form class="control-panel" @submit.prevent="loadRunForDate">
   <label>目标交易日<input :value="targetDateInput" type="date" aria-label="目标交易日" @input="targetDate=($event.target as HTMLInputElement).value.replaceAll('-','')" /></label>
   <button type="submit" :disabled="dateLookupBusy || !targetDate">{{ dateLookupBusy ? '正在查找…' : '按日期查找已保存运行' }}</button>
   <span class="runtime-state" role="status">{{ dateLookup || '仅查找该日期已保存结果；不触发采集，不回退 latest。' }}</span>
  </form>
  <form class="control-panel" @submit.prevent="reload">
   <label>运行 ID<input v-model="requestedRun" aria-label="运行 ID" spellcheck="false" autocomplete="off" /></label>
   <button type="submit">{{ state.phase==='LOADING' ? '重新读取' : '读取已保存结果' }}</button>
   <span class="runtime-state">{{ state.descriptor ? `目标日 ${state.descriptor.target_date}` : '目标日尚未确认' }}</span>
  </form>
  <nav class="entry-nav" aria-label="功能入口">
   <button type="button" :class="{active:!isAnnouncement&&!isRebound&&!isUsMapping}" :aria-current="!isAnnouncement&&!isRebound&&!isUsMapping ? 'page' : undefined" :disabled="!state.overview" @click="showManager">经理已保存结果</button>
   <button type="button" :class="{active:isAnnouncement}" :aria-current="isAnnouncement ? 'page' : undefined" :disabled="!state.overview?.sections.announcement_reviewed_analysis" @click="selectSection('announcement_reviewed_analysis')">公告研究股票</button>
   <button type="button" :class="{active:isRebound}" :aria-current="isRebound ? 'page' : undefined" :disabled="!state.overview?.sections.rebound_research_observation" @click="selectRebound()">超跌研究</button>
   <button type="button" :class="{active:isUsMapping}" :aria-current="isUsMapping ? 'page' : undefined" :disabled="!state.overview?.sections.us_mapping_research" @click="selectSection('us_mapping_research')">美股驱动</button>
   <button type="button" aria-controls="m16-saved-research" @click="openPublicResearch">公开资料研究 · M16</button>
   <button type="button" aria-controls="m11-saved-research" @click="openIntradayResearch">盘中研究 · M11</button>
   <button type="button" aria-controls="m12-saved-video" @click="openVideo">视频复盘 · M12</button>
   <button type="button" aria-controls="m04-saved-research" @click="openResearch">研究情报 · M04</button>
   <button type="button" aria-controls="source-module-content" :aria-expanded="sourceExpanded" @click="openSources">源模块实际状态</button>
   <button type="button" aria-controls="m07-saved-stage" @click="openAStage">A 股阶段选股 · M07 已保存结果</button>
   <a class="entry-nav-link" href="?view=research">研报决策台</a>
  </nav>
  <p class="navigation-status">当前页面只读取已保存结果，不启动采集。接口 READY 仅表示保存产物可读取，不代表业务完整、全部模块可用或交易许可。</p>
  <div class="navigation-status" role="status">
   <p v-if="state.overview && !state.overview.sections.announcement_reviewed_analysis">公告研究股票：尚未确认当前运行存在合格的已保存结果；按钮禁用不代表 0 条。</p>
   <p v-if="state.overview && !state.overview.sections.rebound_research_observation">超跌研究：尚未确认当前运行存在合格的已保存结果；按钮禁用不代表 0 条。</p>
   <p v-if="state.overview && !state.overview.sections.us_mapping_research">美股驱动：尚未确认当前运行存在合格的已保存结果；按钮禁用不代表 0 条。</p>
  </div>
  <section id="saved-result-content" aria-labelledby="saved-result-title">
   <header class="saved-result-heading">
    <h2 id="saved-result-title" ref="resultHeading" tabindex="-1">{{ state.section ? sectionLabel(state.section) : '经理已保存结果' }}</h2>
    <p v-if="state.descriptor"><span>目标日 {{ state.descriptor.target_date }}</span><span>已读取运行 {{ state.descriptor.run_id }}</span></p>
   </header>
  <p v-if="state.phase==='LOADING'" class="task-message" role="status" aria-live="polite">正在读取同一运行的有界数据页…</p>
  <div v-if="state.phase==='CANNOT_CONFIRM'" class="task-message task-error" role="alert">
   <strong>CANNOT_CONFIRM · 当前请求未能确认，未显示旧结果。</strong>
   <p>{{ explainError(state.error) }}</p>
   <details v-if="state.error"><summary>技术诊断（原始错误）</summary><pre>{{ state.error }}</pre></details>
  </div>
  <div v-if="state.overview && !isAnnouncement && !isRebound && !isUsMapping" class="task-counts"><article v-for="key in ['stocks','materials','gaps']" :key="key"><span>{{ sectionLabel(key) }}</span><strong>{{ state.overview.sections[key]?.total ?? '未提供' }}</strong></article></div>
  <section v-if="state.overview" class="task-status-view saved-sections" aria-label="已保存内容">
   <div class="control-panel"><label>内容分区<select :value="state.section" aria-label="内容分区" @change="sectionChange"><option v-for="(meta,key) in state.overview.sections" :key="key" :value="key">{{ sectionLabel(String(key)) }}{{ ['announcement_reviewed_analysis','rebound_research_observation','us_mapping_research'].includes(String(key)) ? ' · 同次运行研究引用' : ` · ${meta.total} 条 · ${meta.kind}` }}</option></select></label><span>按原始分区分页读取，每页最多 32 条</span><button v-if="state.overview.sections.gaps" type="button" @click="selectSection('gaps')">查看缺口 · {{ state.overview.sections.gaps.total }}</button><button v-if="state.overview.sections.materials" type="button" @click="selectSection('materials')">研究材料 · {{ state.overview.sections.materials.total }}</button></div>
   <p v-if="!Object.keys(state.overview.sections).length" class="task-message">保存产物没有可展示的分区。未推断业务成功。</p>
   <div v-if="isRebound" class="control-panel" role="group" aria-label="超跌观察分组"><button v-for="group in REBOUND_GROUPS" :key="group" type="button" :aria-pressed="(state.group ?? 'strict')===group" @click="selectRebound(group)">{{ reboundGroupLabels[group] }} · {{ state.page?.rebound?.group_counts[group] ?? '未读取' }}</button></div>
   <template v-if="state.page">
    <div class="saved-pagination"><button type="button" :disabled="!state.canPrevious || state.phase==='LOADING'" @click="session.previous()">上一页</button><span>当前 {{ state.page.entries.length ? state.page.offset+1 : 0 }}–{{ state.page.offset+state.page.entries.length }} / {{ state.page.matched_total }} 条</span><button type="button" :disabled="!state.page.next_cursor || state.phase==='LOADING'" @click="session.next()">下一页</button></div>
    <div v-if="isAnnouncement" ref="announcementHost" class="saved-announcements"></div>
    <div v-else-if="isRebound" ref="reboundHost" class="saved-announcements"></div>
    <div v-else-if="isUsMapping" ref="usMappingHost" class="saved-announcements"></div>
    <p v-else-if="state.page.matched_total===0" class="task-message">此分区原始值为空数组（0 条）。这不代表其他内容已就绪。</p>
    <div v-else class="saved-table-scroll"><table><thead><tr><th>条目</th><th>原始状态</th><th>内容与缺口</th></tr></thead><tbody>
     <tr v-for="entry in state.page.entries" :key="`${state.section}:${entry.index}`"><th scope="row">{{ title(entry) }}</th><td>{{ businessState(entry) }}</td><td>
      <template v-if="entry.value_state==='LOADED'"><pre>{{ excerpt(entry) }}</pre><details><summary>完整条目与来源摘要</summary><pre>{{ json(entry.value) }}</pre><p>条目 SHA256：{{ entry.sha256 }}</p><p>原始字节：{{ entry.bytes }}；位置：{{ entry.offset }}</p></details></template>
      <template v-else><p>条目尚未加载：{{ entry.reason ?? 'NOT_LOADED' }}。保留缺口，不替换为空值。</p><p>原始字节：{{ entry.bytes }}；SHA256：{{ entry.sha256 }}</p></template>
     </td></tr>
    </tbody></table></div>
    <p class="task-message">本页只展示已读取的条目；其余未加载数：{{ state.page.not_loaded_count }}。单条或页面限制按原返回状态显示，未加载不会当作空值。</p>
   </template>
  </section>
  <details v-if="state.descriptor" class="task-status-view saved-identity" aria-label="结果身份">
   <summary>本次结果身份 · 目标日 {{ state.descriptor.target_date }} · 展开核对运行与摘要</summary>
   <dl><div><dt>运行 ID</dt><dd>{{ state.descriptor.run_id }}</dd></div><div><dt>目标日</dt><dd>{{ state.descriptor.target_date }}</dd></div><div><dt>保存描述生成时间</dt><dd>{{ state.descriptor.generated_at }}</dd></div></dl>
   <details><summary>核对同一运行与摘要</summary><dl>
    <div v-for="(value,key) in state.descriptor.identity" :key="key"><dt>{{ key }}</dt><dd>{{ value }}</dd></div>
    <div><dt>离线 generation（不是发布 generation）</dt><dd>{{ state.descriptor.generation_id }}</dd></div>
    <div><dt>profile SHA256</dt><dd>{{ state.descriptor.profile_sha256 }}</dd></div>
    <div><dt>manifest SHA256</dt><dd>{{ state.overview?.manifest_sha256 ?? '尚未读取' }}</dd></div>
   </dl></details>
  </details>
  </section>
  <details id="source-module-content" ref="sourceDisclosure" class="task-status-view source-disclosure" @toggle="onSourceToggle">
   <summary ref="sourceSummary">源模块实际状态 · 点击展开基础数据、预选池与复盘</summary>
   <SourceBundleStatus />
  </details>
  <section ref="publicResearchHost" aria-label="M16 公开资料研究入口"><M16SavedResearch /></section>
  <section ref="intradayResearchHost" aria-label="M11 盘中研究入口"><M11SavedResearch /></section>
  <section ref="videoHost" aria-label="M12 视频复盘入口"><M12SavedVideo /></section>
 </main>
</template>
<style scoped>
.saved-result-heading{padding:14px 24px 0}.saved-result-heading h2{margin:0;font-size:20px;scroll-margin-top:16px}.saved-result-heading p{display:flex;flex-wrap:wrap;gap:8px 18px;margin:8px 0 0;font-size:13px;color:#526579;overflow-wrap:anywhere}.saved-result-heading h2:focus,.source-disclosure>summary:focus{outline:2px solid #254d71;outline-offset:4px}.source-disclosure>summary{padding:18px;cursor:pointer;color:#254d71;font-weight:600;scroll-margin-top:16px}.source-disclosure :deep(.source-status){margin:0;border:0;box-shadow:none}@media(max-width:650px){.saved-result-heading{padding:14px 18px 0}.saved-result-heading p{display:grid;gap:6px}}
.saved-run-view .control-panel{flex-wrap:wrap}.saved-run-view .control-panel input{width:min(36ch,75vw)}.saved-run-view .entry-nav{flex-wrap:wrap}.saved-run-view button:disabled{cursor:not-allowed}.saved-identity{padding:18px}.saved-identity h2{margin:0 0 12px;font-size:18px}.saved-identity dl{display:grid;gap:10px}.saved-identity dt{font-size:12px;color:#526579}.saved-identity dd{margin:4px 0;overflow-wrap:anywhere;font-size:13px}.saved-sections .control-panel{padding:16px}.saved-pagination{display:flex;gap:16px;align-items:center;padding:14px 18px}.saved-pagination button{padding:7px 12px}.saved-table-scroll{overflow:auto;margin:0 18px}.saved-table-scroll table{width:100%;border-collapse:collapse;font-size:13px}.saved-table-scroll th,.saved-table-scroll td{text-align:left;padding:12px;border:1px solid #c8d3dd;vertical-align:top}.saved-table-scroll thead{background:#e3ebf2}.saved-table-scroll th:first-child{min-width:130px}.saved-table-scroll pre{margin:0;white-space:pre-wrap;overflow-wrap:anywhere;max-width:850px;font-family:inherit;line-height:1.6}.saved-table-scroll details{margin-top:12px}.saved-table-scroll details p{overflow-wrap:anywhere}.saved-table-scroll summary,.saved-identity summary{cursor:pointer;color:#254d71}@media(max-width:650px){.saved-run-view .page-header{padding:18px;flex-direction:column;gap:12px}.saved-run-view .control-panel,.saved-run-view .entry-nav{padding:12px 18px}.saved-run-view .task-status-view{margin:14px 12px}.saved-run-view .navigation-status{margin:12px}.saved-pagination{gap:8px;font-size:12px}}
.saved-announcements{padding:0 18px}.saved-announcements :deep(article){border:1px solid #d6dde5;border-radius:8px;padding:14px;margin:12px 0}.saved-announcements :deep(h4){font-size:1.05rem;margin:0 0 10px}.saved-announcements :deep(p){line-height:1.65;overflow-wrap:anywhere}.saved-announcements :deep(details){margin:10px 0}.saved-announcements :deep(summary){cursor:pointer;line-height:1.6}.saved-announcements :deep(pre){white-space:pre-wrap;overflow-wrap:anywhere;font-size:.8rem}
</style>


