const ANNOTATION_SYMBOL=null;const ANNOTATION_DATES=[];const DEFAULT_DATE=null;
export function mountAnnouncementAnnotation({document,parent,event,annotations}){
 if(ANNOTATION_SYMBOL===null||DEFAULT_DATE===null)throw Error('PUBLIC_EXPORT_NO_APPROVED_PRIVATE_BINDING');
 const el=(tag,text='')=>{const e=document.createElement(tag);e.textContent=text;return e;};
 const root=el('details');root.append(el('summary','07:00公告附注 · 仅单股已绑定公告历史补证，非全量公告完成'));
 root.append(el('p',`原Par名：${event.panel_name_retained}；面板实际日 ${event.panel_actual_date}。公告新名：${event.announced_new_name}，${event.event_date}开市起。原名、ST筛选及风险规则均不改。`));
 root.append(el('p',`公告落款 ${event.announcement_signed_date}；URL归档日 ${event.source_url_archive_date}；精确发布时刻 UNKNOWN；本轮读取 ${event.research_observed_at_utc}；历史PIT=false。来源 ${event.source_url}`),el('p',event.risk));
 const date=el('select'),stage=el('select'),status=el('p');date.setAttribute?.('aria-label','附注查询日期');stage.setAttribute?.('aria-label','附注开市阶段');
 for(const value of ANNOTATION_DATES){const o=el('option',value);o.value=value;date.append(o);}date.value=DEFAULT_DATE;
 for(const [value,label] of [['UNKNOWN','开市阶段未知'],['PRE_OPEN','开市前'],['AFTER_OPEN','开市后']]){const o=el('option',label);o.value=value;stage.append(o);}stage.value='UNKNOWN';
 const render=()=>{const a=annotations?.[date.value+'|'+stage.value];if(!a||a.symbol!==ANNOTATION_SYMBOL||a.source_name_rewritten!==false||a.risk_filter_changed!==false){status.textContent='UNKNOWN · 附注条件不匹配，不应用名称';return;}status.textContent=`代码 ${a.symbol}；查询 ${date.value} / ${stage.value}；${a.annotation_state}；原面板名仍 ${a.source_name}；附注 ${a.display_name_annotation??'暂不应用，等待日期/开市阶段确认'}。不是风险解除或选股资格。`;};
 date.onchange=render;stage.onchange=render;root.append(date,stage,status,el('p','仅一个已读公告附注，无全量公告覆盖证明；展开或切换条件只读，不启动采集，不更新证券主表。'));render();parent.append(root);
}
