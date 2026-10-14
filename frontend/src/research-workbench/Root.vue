<script setup lang="ts">
import {onBeforeUnmount, ref} from 'vue';
import ResearchView from './views/ResearchView.vue';
function initialDate() {
 const raw=new URLSearchParams(location.search).get('date');
 return raw || new Intl.DateTimeFormat('sv-SE',{timeZone:'Asia/Shanghai'}).format(new Date()).replaceAll('-','');
}
const date=ref(initialDate());
const error=ref('');
function changeDate(event:Event) {
 const value=(event.target as HTMLInputElement).value.replaceAll('-','');
 if(!/^\d{8}$/.test(value)){error.value='请输入有效研究日期';return;}
 date.value=value;error.value='';const url=new URL(location.href);url.searchParams.set('view','research');url.searchParams.set('date',value);history.pushState(null,'',url);
}
function pop(){date.value=initialDate();}
window.addEventListener('popstate',pop);onBeforeUnmount(()=>window.removeEventListener('popstate',pop));
</script>
<template>
 <main class="v5-research-root">
  <nav aria-label="V5页面导航"><a href="?">经理已保存结果</a> · <strong>研报决策台</strong></nav>
  <label>研究自然日 <input aria-label="研究自然日" type="date" :value="`${date.slice(0,4)}-${date.slice(4,6)}-${date.slice(6,8)}`" @change="changeDate" /></label>
  <p v-if="error" role="alert">{{error}}</p>
  <ResearchView :archive-date="date" />
 </main>
</template>
<style scoped>.v5-research-root{--line:#cbd5e1;--ink:#172f49;--muted:#526579;--blue:#2563eb;--green:#15803d;--red:#b91c1c;--amber:#a16207;--steel:#64748b;padding:20px;max-width:1600px;margin:auto}nav{margin-bottom:18px}input{margin:10px;padding:8px}a{color:inherit}</style>
