<script setup lang="ts">
import {onBeforeUnmount,shallowRef} from 'vue';
import {SavedResearchSession,type SavedResearchState} from '../api/m04SavedResearch';
const state=shallowRef<SavedResearchState>({phase:'IDLE',result:null,error:''});
const session=new SavedResearchSession(next=>{state.value=next;});
function onToggle(event:Event){if((event.currentTarget as HTMLDetailsElement).open&&state.value.phase==='IDLE')void session.load();}
function text(value:unknown){return typeof value==='string'&&value.trim()?value:'未提供';}
function json(value:unknown){return JSON.stringify(value,null,2);}
onBeforeUnmount(()=>session.close());
</script>
<template>
 <details id="m04-saved-research" class="m04-research" @toggle="onToggle">
  <summary>M04 研究情报 · 已保存历史样本 · 展开只读结果</summary>
  <section aria-label="M04 已保存研究情报">
   <p>固定历史样本；只读原存档，未启动新采集或模型。PIT UNKNOWN，不能据此确认当时可获得性或正式准入。</p>
   <button type="button" @click="session.load()">重新读取 M04 已保存样本</button>
   <p v-if="state.phase==='IDLE'">尚未读取保存样本。</p>
   <p v-else-if="state.phase==='LOADING'" role="status" aria-live="polite">正在冷读原 M04 存档…</p>
   <p v-else-if="state.phase==='NOT_CONFIGURED'" role="status">NOT_CONFIGURED · 尚未绑定这份已保存样本。</p>
   <p v-else-if="state.phase==='CANNOT_CONFIRM'" role="alert">CANNOT_CONFIRM · 当前读取失败，未显示旧结果。{{ state.error }}</p>
   <template v-if="state.result">
    <h3>研究情报 · {{ state.result.reference.archive_date }} · {{ state.result.article_count }} 条</h3>
    <p>来源时段：21:00（Asia/Shanghai） · 来源运行：{{ state.result.reference.source_run_id }}</p>
    <p>保存状态：SAVED_HISTORICAL_SAMPLE · {{ state.result.missing_retrieved_at }}/18 缺 retrieved_at，{{ state.result.missing_available_at }}/18 缺 available_at · PIT UNKNOWN</p>
    <p>完整 manifest 的样本外读取错误：{{ state.result.out_of_sample_record_errors }}。其他日期或产物未随这三份文件复制，未声明全量验证。</p>
    <p>批次时间 {{ state.result.reference.batch_fetched_at ?? '未提供' }}；发布记录时间 {{ state.result.reference.source_publication_available_at ?? '未提供' }}。批次、发布时间不能替代逐条资料可获得时间。</p>
    <ol class="m04-articles"><li v-for="article in state.result.archive.articles" :key="String(article.article_id)">
     <h4>{{ text(article.source_title) }}</h4>
     <p>{{ text(article.stock_code) }} · {{ text(article.stock_name) }} · {{ text(article.theme) }}</p>
     <p>原催化：{{ text(article.catalyst) }}</p><p>原证据：{{ text(article.evidence_sentence) }}</p>
     <p>来源：{{ text(article.source_name) }} · 原发布时间：{{ text(article.published_at) }}</p>
     <p>retrieved_at：UNKNOWN · available_at：UNKNOWN</p>
     <details><summary>完整原始研究条目</summary><pre>{{ json(article) }}</pre></details>
    </li></ol>
    <details><summary>原存档状态、身份与缺口</summary><pre>{{ json(state.result) }}</pre></details>
   </template>
  </section>
 </details>
</template>
<style scoped>
.m04-research{margin-top:18px;border:1px solid #c8d3dd;border-radius:8px;padding:14px;scroll-margin-top:16px}.m04-research>summary{font-weight:600;cursor:pointer;color:#254d71}.m04-research>summary:focus{outline:2px solid #254d71;outline-offset:4px}.m04-research p{font-size:13px;line-height:1.65;overflow-wrap:anywhere}.m04-research button{padding:8px 12px}.m04-articles{padding-left:24px}.m04-articles>li{padding:12px 0;border-bottom:1px solid #d6dde5}.m04-articles h4{margin:0;font-size:15px}.m04-research pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px;max-height:360px;overflow:auto}.m04-research details summary{cursor:pointer}.m04-research h3{font-size:17px}
</style>
