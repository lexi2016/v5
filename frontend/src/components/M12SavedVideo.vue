<script setup lang="ts">
import {onBeforeUnmount,ref,shallowRef} from 'vue';
import {SavedVideoSession,type VideoState} from '../api/m12SavedVideo';
const date=ref('');
const state=shallowRef<VideoState>({phase:'IDLE',result:null,error:''});
const session=new SavedVideoSession(next=>{state.value=next;});
function load(){void session.load(date.value.trim());}
function onToggle(event:Event){if((event.currentTarget as HTMLDetailsElement).open&&state.value.phase==='IDLE')load();}
onBeforeUnmount(()=>session.close());
</script>
<template>
 <details id="m12-saved-video" class="m12-video" @toggle="onToggle">
  <summary>M12 视频复盘 · 读取已保存原文</summary>
  <section aria-label="M12 已保存视频复盘">
   <p>核验原视频产物和回执后读取。ASR_REVIEW_REQUIRED 表示原文仍待复核；视频只补充证据，未完成独立事实核验。此入口不启动视频下载或 ASR。</p>
   <form @submit.prevent="load"><label>交易日（可留空读取已绑定运行）<input v-model="date" placeholder="YYYYMMDD" inputmode="numeric" maxlength="8" aria-label="M12 交易日" /></label><button type="submit">读取 M12 已保存视频</button></form>
   <p v-if="state.phase==='IDLE'">尚未读取保存结果。</p>
   <p v-else-if="state.phase==='LOADING'" role="status">正在核验原视频运行…</p>
   <p v-else-if="state.phase==='WAITING'" role="status">WAITING · 暂无可确认的合格保存结果。{{ state.result?.reason_codes.join(' · ') }}</p>
   <p v-else-if="state.phase==='CANNOT_CONFIRM'" role="alert">CANNOT_CONFIRM · 当前读取失败，已清除旧结果。{{ state.error }}</p>
   <article v-if="state.phase==='LOADED' && state.result" data-testid="m12-saved-content">
    <p v-if="state.result.data_kind==='SYNTHETIC'" role="note">SYNTHETIC · 合成测试资料，不是真实视频复盘。</p>
    <p v-else>资料类型：{{ state.result.data_kind }} · 尚未声明自然日端到端验收通过</p>
    <h3>{{ state.result.video?.title || '原视频未提供标题' }}</h3>
    <p>{{ state.result.reference?.trade_date }} · BV {{ state.result.video?.bv_id }} · 原运行 {{ state.result.reference?.run_id }}</p>
    <p>原 ASR：{{ state.result.video?.asr_status }} · 缺口审计：{{ state.result.video?.gap_status }} · 股票别名：{{ state.result.video?.stockdict_status ?? '未提供' }}</p>
    <h4>已保存 ASR 原文 · 待复核</h4><pre>{{ state.result.transcript?.text }}</pre>
    <p v-if="state.result.transcript?.truncated">仅展示前 262144 个字符，共 {{ state.result.transcript.total_characters }} 个字符；原文件未改动。</p>
    <details><summary>原始 ASR 分段</summary><pre>{{ state.result.segments?.text }}</pre><p v-if="state.result.segments?.truncated">分段展示已截断，共 {{ state.result.segments.total_characters }} 个字符。</p></details>
    <details><summary>核验身份与摘要</summary><pre>{{ JSON.stringify(state.result.reference,null,2) }}</pre></details>
   </article>
  </section>
 </details>
</template>
<style scoped>
.m12-video{margin:18px;border:1px solid #c8d3dd;border-radius:8px;padding:16px;scroll-margin-top:16px}.m12-video>summary{font-weight:600;color:#254d71;cursor:pointer}.m12-video summary:focus{outline:2px solid #254d71;outline-offset:4px}.m12-video p{line-height:1.65;font-size:13px;overflow-wrap:anywhere}.m12-video form{display:flex;gap:12px;flex-wrap:wrap;align-items:end}.m12-video label{display:grid;gap:6px}.m12-video input,.m12-video button{padding:8px}.m12-video pre{white-space:pre-wrap;overflow-wrap:anywhere;max-height:420px;overflow:auto;font-size:13px}.m12-video h3{font-size:17px}
</style>
