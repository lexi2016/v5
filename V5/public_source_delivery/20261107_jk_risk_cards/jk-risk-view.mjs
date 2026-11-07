const SOURCE_DATE=null,RISK_CARD_COUNT=null;
function maker(document){return(tag,text='')=>{const e=document.createElement(tag);e.textContent=text;return e;};}
export function mountJKReference({document,parent,result:r,observations:o}){
 if(!SOURCE_DATE)throw Error('NO_APPROVED_PRIVATE_BINDING');
 if(r.source_date!==SOURCE_DATE||r.source_admission!==false||r.natural_verified!==false||r.business_accepted!==false)throw Error('JK_SCOPE');const el=maker(document);
 parent.append(el('strong','日韩历史晚补；不是08:00–08:10采集或自然验收。事件时刻、发布时间、读取时间分列；时区未明确处UNKNOWN。'));
 for(const c of r.comparisons){if(c.field==='post_session_reference'&&c.value!==null)throw Error('JK_CROSS_SEMANTIC');parent.append(el('p',`${c.symbol} · ${c.field}：${c.value===null?'null（未裁决，不取均值）':c.value}；${c.status}；原值 ${c.observed_values.join(' / ')}；字段 ${c.source_fields.join(' / ')}。`));}
 parent.append(el('p','KOSPI close与latest_reference跨口径，不是两个可直接合并的收盘值；各来源原值保留，统一值null。'));
 for(const x of o.records){const d=el('details');d.append(el('summary',`${x.symbol} ${x.field} · ${x.value}`),el('p',`事件原文 ${x.event_time_raw??'UNKNOWN'}；发布 ${x.source_published_at??'UNKNOWN'}；读取 ${o.recorded_at_utc}；来源 ${x.url}`),el('p',x.note));parent.append(d);}
}
export function mountRiskCards({document,parent,risk}){
 if(!SOURCE_DATE||!Number.isInteger(RISK_CARD_COUNT)||RISK_CARD_COUNT<=0)throw Error('NO_APPROVED_PRIVATE_BINDING');
 if(risk.source_date!==SOURCE_DATE||risk.new_top200_verified_members!==0||risk.cards?.length!==RISK_CARD_COUNT)throw Error('RISK_SCOPE');const el=maker(document),section=el('details');section.append(el('summary','07:00公告风险补证 · 已绑定卡片均非原Top200，不改名单'),el('p','原日期资料，事后历史晚补；精确发布时间UNKNOWN，非当时可知/PIT或自然完成。仅已绑定卡片，不是全量公告验收。'));
 for(const c of risk.cards){if(c.publication_time!=='UNKNOWN'||c.top200_member!==false||c.historical_PIT!==false||c.source_admission!==false)throw Error('RISK_QUALIFICATION');const d=el('details');d.append(el('summary',`${c.symbol} ${c.name} · 公告${c.announcement}`),el('p',c.facts),el('strong',c.caution),el('p',`落款 ${c.signed_date}；URL归档 ${c.url_archive_date}；精确发布UNKNOWN；原文 ${c.url}；页 ${c.source_pages.join(',')} ${c.source_lines}`),el('p','PDF原字节未下载，字节SHA UNKNOWN；非Top200新增成员、无买入资格，原筛选不改。'));section.append(d);}parent.append(section);
}
