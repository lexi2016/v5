import{readVerifiedJSON}from'./verified-json.mjs?v=integrated3';
// Fixed-byte display adapter. This module never computes stock signals.
export const SCREEN_DATES=['20261106','20261105'];
export const SCREEN_GROUPS=['original','nav_smallk','nav_pullback','nav_breakout'];
export const SCREEN_LABELS={union:'四组去重候选',original:'原公式',nav_smallk:'导航小K',nav_pullback:'导航回踩',nav_breakout:'导航突破',pending:'含待核结果',all:'全部股票'};
const need=(ok,code='PAR_SCREEN_CONTRACT')=>{if(!ok)throw Error(code);};
const sha=v=>typeof v==='string'&&/^[a-f0-9]{64}$/.test(v),date=v=>{if(typeof v!=='string'||!/^20\d{6}$/.test(v))return false;const y=Number(v.slice(0,4)),m=Number(v.slice(4,6)),d=Number(v.slice(6,8)),t=new Date(Date.UTC(y,m-1,d));return t.getUTCFullYear()===y&&t.getUTCMonth()===m-1&&t.getUTCDate()===d},tri=v=>['TRUE','FALSE','UNKNOWN'].includes(v);
export function validateScreen(s){
 need(s?.schema==='PAR_SCREEN_DISPLAY_V1'&&date(s.source_date)&&Number.isSafeInteger(s.scope_count)&&s.scope_count>0&&s.scope_count<=10000&&Array.isArray(s.rows)&&s.rows.length===s.scope_count);
 need(s.qualifications?.research_only===true&&s.qualifications.production_allowed===false&&s.qualifications.selection_admission===false&&s.qualifications.manual_chart_confirmation==='UNKNOWN'&&s.qualifications.buy_qualification===false&&s.qualifications.orders_sent===false);
 for(const key of ['selection','catalog'])need(sha(s.sources?.[key]?.sha256)&&Number.isSafeInteger(s.sources[key].bytes)&&s.sources[key].bytes>0);
 const seen=new Set();for(const r of s.rows){
  need(typeof r.symbol==='string'&&/^\d{6}\.(SH|SZ|BJ)$/.test(r.symbol)&&!seen.has(r.symbol));seen.add(r.symbol);
  need(r.name===null||typeof r.name==='string'&&r.name.length<=80);need(date(r.actual_date)&&r.actual_date<=s.source_date);
  need(typeof r.status==='string'&&typeof r.source_family==='string'&&(r.history_bars===null||Number.isSafeInteger(r.history_bars)&&r.history_bars>=0)&&Array.isArray(r.reasons)&&r.reasons.every(x=>typeof x==='string'));
  for(const g of SCREEN_GROUPS)for(const layer of ['baseline','after_redgreen','after_risk']){need(tri(r.layers?.[g]?.[layer]));if(r.actual_date!==s.source_date)need(r.layers[g][layer]==='UNKNOWN');}
 }
 if(s.partitions!==undefined){
  need(s.calculation_date===s.source_date&&date(s.observation_date)&&s.observation_date>s.source_date);
  const measured={COMPUTED_CURRENT:0,RETAINED_NO_BAR:0,SOURCE_BLOCKED:0};
  for(const r of s.rows){need(Object.hasOwn(measured,r.owner_outcome));measured[r.owner_outcome]++;if(r.owner_outcome==='COMPUTED_CURRENT')need(r.actual_date===s.source_date&&r.status==='NUMERIC_PROXIES_COMPUTED');else need(r.actual_date<s.source_date&&r.status===(r.owner_outcome==='RETAINED_NO_BAR'?'NO_TARGET_DAY_BAR':'UNKNOWN_ERROR'));}
  need(Object.keys(s.partitions).length===3&&Object.keys(measured).every(k=>s.partitions[k]===measured[k]));
  need(s.qualifications.source_admission===false&&s.qualifications.research_consumption_allowed===false&&sha(s.sources.independent_output_review?.sha256));
 }else need(s.calculation_date===undefined&&s.observation_date===undefined&&s.rows.every(r=>r.owner_outcome===undefined));
 return s;
}
export function countScreen(s){const groups=Object.fromEntries(SCREEN_GROUPS.map(g=>[g,{TRUE:0,FALSE:0,UNKNOWN:0}]));let union=0,pending=0,current=0;for(const r of s.rows){for(const g of SCREEN_GROUPS)groups[g][r.layers[g].after_risk]++;if(SCREEN_GROUPS.some(g=>r.layers[g].after_risk==='TRUE'))union++;if(SCREEN_GROUPS.some(g=>r.layers[g].after_risk==='UNKNOWN'))pending++;if(r.actual_date===s.source_date)current++;}return{groups,union,pending,current,retained:s.partitions?.RETAINED_NO_BAR??s.rows.length-current,blocked:s.partitions?.SOURCE_BLOCKED??0};}
export function filterScreen(s,{group='union',query='',sort='symbol_asc'}={}){need(['union','pending','all',...SCREEN_GROUPS].includes(group));const q=query.trim().toLocaleLowerCase();const rows=s.rows.filter(r=>(!q||`${r.symbol} ${r.name??''}`.toLocaleLowerCase().includes(q))&&(group==='all'||group==='union'&&SCREEN_GROUPS.some(g=>r.layers[g].after_risk==='TRUE')||group==='pending'&&SCREEN_GROUPS.some(g=>r.layers[g].after_risk==='UNKNOWN')||SCREEN_GROUPS.includes(group)&&r.layers[group].after_risk==='TRUE'));return rows.sort((a,b)=>{if(sort.startsWith('name_')){if(!a.name!==!b.name)return a.name?-1:1;const c=(a.name??'').localeCompare(b.name??'','zh-CN');if(c)return sort==='name_desc'?-c:c;}return (sort==='symbol_desc'?-1:1)*a.symbol.localeCompare(b.symbol);});}
async function readBounded(response,max){need(response.ok&&!response.redirected,'PAR_SCREEN_HTTP');const reader=response.body?.getReader();need(reader,'PAR_SCREEN_STREAM');const parts=[];let size=0;try{while(true){const {done,value}=await reader.read();if(done)break;size+=value.length;if(size>max){await reader.cancel();throw Error('PAR_SCREEN_SIZE');}parts.push(value);}}finally{reader.releaseLock();}const bytes=new Uint8Array(size);let at=0;for(const part of parts){bytes.set(part,at);at+=part.length;}return bytes;}
export async function loadScreen({fetcher=fetch,cryptoImpl=crypto,signal,sourceDate=null,selectionVersion='main406'}={}){
 need(sourceDate===null||SCREEN_DATES.includes(sourceDate),'PAR_SCREEN_REQUESTED_DATE');
 need(['main406','merge407'].includes(selectionVersion),'SELECTION_VERSION');
 if(selectionVersion==='merge407'&&sourceDate!=='20261105')return loadMerged407({fetcher,cryptoImpl,signal});
 const pointerPath=sourceDate?`/research-system/par-screen-data/${sourceDate}.json`:'/research-system/par-screen-data/current.json';
 const options={credentials:'same-origin',cache:'no-store',redirect:'error',signal};
 const p=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(await readBounded(await fetcher(pointerPath,options),16384)));
 need(p?.schema==='PAR_SCREEN_POINTER_V1'&&date(p.source_date)&&Number.isSafeInteger(p.scope_count)&&sha(p.ref?.sha256)&&Number.isSafeInteger(p.ref.bytes)&&p.ref.bytes>0&&p.ref.bytes<=16*1024*1024&&p.ref.path===`/research-system/par-screen-data/${p.ref.sha256}.json`);
 const raw=await readBounded(await fetcher(p.ref.path,options),p.ref.bytes);need(raw.length===p.ref.bytes,'PAR_SCREEN_SIZE');const hash=Array.from(new Uint8Array(await cryptoImpl.subtle.digest('SHA-256',raw)),x=>x.toString(16).padStart(2,'0')).join('');need(hash===p.ref.sha256,'PAR_SCREEN_HASH');
 const value=validateScreen(JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(raw)));need(value.source_date===p.source_date&&(sourceDate===null||value.source_date===sourceDate)&&value.scope_count===p.scope_count,'PAR_SCREEN_DATE');return value;
}

async function loadMerged407(options){
 const root='/research-system/par-screen-data/',sha='9d1b65dc64e4b3ca3c08a114457a262f0743c7fc50affaffa82968ff990e710e',size=3183878,admissionHash='e207d45d21d2f4cfae49b38a26a5640dfcbf36d11fe7a269fc1ca18af1106d1c';
 const a=await readVerifiedJSON(root+'merge407-admission.json',{...options,expectedHash:admissionHash,expectedBytes:3376,maxBytes:3376});
 need(a.status==='PASS_RESEARCH_MERGE_DISPLAY_ONLY'&&a.research_display_allowed===true&&a.ui_adoption_permitted===true&&a.no_buy===true&&a.production_allowed===false&&a.old_main_selected_406_unchanged===true,'MERGE_ADMISSION');
 const p=await readVerifiedJSON(root+'merge407.json',{...options,expectedHash:'9498fc43e9782df7d65afb454b2dca4a4d0f48b6d6c8bf5add15cb6be8ab507d',expectedBytes:334,maxBytes:334});
 need(p.selection_version==='MAIN_PLUS_SINA69_407'&&p.source_date==='20261106'&&p.scope_count===5575&&p.ref?.path===root+sha+'.json'&&p.ref.sha256===sha&&p.ref.bytes===size,'MERGE_POINTER');
 const value=validateScreen(await readVerifiedJSON(p.ref.path,{...options,expectedHash:sha,expectedBytes:size,maxBytes:size})),c=countScreen(value);
 need(value.selection_version===p.selection_version&&value.source_date===p.source_date&&value.scope_count===p.scope_count&&value.sources.research_merge_admission.sha256===admissionHash&&value.sources.selection.sha256===a.output_ref.sha256&&value.sources.selection_manifest.sha256===a.candidate_manifest_ref.sha256&&value.sources.selection_counts.sha256===a.counts_ref.sha256,'MERGE_BINDING');
 need(c.union===a.dedup_selected&&c.union===407&&c.pending===a.dedup_pending&&c.pending===579&&c.current===5534&&c.retained===6&&c.blocked===35&&SCREEN_GROUPS.every((g,i)=>c.groups[g].TRUE===a.group_true[i]),'MERGE_COUNTS');return value;
}
