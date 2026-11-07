const SOURCE_DATE=null;const FINAL_KEY=null;
export function mountHKCloseHistory({document,parent,observations:h,nodeId}){
 if(SOURCE_DATE===null||FINAL_KEY===null||h?.data_date!==SOURCE_DATE||h.source_admission!==false||h.natural_verified!==false||h.production_allowed!==false||h.business_accepted!==false||h.official_schedule[FINAL_KEY]!==null)throw Error('HK_SCOPE');
 const el=(tag,text='')=>{const e=document.createElement(tag);e.textContent=text;return e;};
 parent.append(el('h4',nodeId==='hk-continuous-close'?'16:00连续盘结束 · 一般规则':'CAS竞价终结 · 实际时刻UNKNOWN'),el('strong','原历史日历史媒体参考，不是本日实时行情或自然采集验收。'));
 parent.append(el('p',`港交所一般规则：正常全日连续盘16:00结束；适用证券CAS在16:08–16:10随机结束。原历史日实际连续盘结束事件UNKNOWN；实际CAS终结时刻UNKNOWN。不能填写固定16:10，不能借新闻时刻代替。`),el('p',`官方规则来源：${h.official_schedule.url}；核对位置 ${h.official_schedule.read_locator}。当日日历 ${h.day_calendar_binding}；原港股范围 ${h.native_hk_scope}。`));
 const table=el('table'),head=el('tr');for(const title of ['指标','媒体报道收盘值','日涨跌%','媒体发布时间原文（时区UNKNOWN）','来源'])head.append(el('th',title));table.append(head);
 for(const r of h.media_observations){const tr=el('tr');for(const value of [r.symbol,r.value,r.daily_change_pct,r.publication_raw,r.source_url])tr.append(el('td',String(value)));table.append(tr);}parent.append(table,el('p','媒体指数不是原港股观察池、Top20或native close_review。source_admission=false；production_allowed=false；自然触发未验。离线原M10代码恢复不代表联网采集器恢复。'));
}
