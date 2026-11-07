// Fixed-byte display adapter. This module never computes stock signals.
export const SCREEN_DATES=[];
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
export async function loadScreen(){throw Error('PUBLIC_EXPORT_NO_APPROVED_PRIVATE_BINDING');}
