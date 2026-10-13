import type { JsonObject } from '../api/managerWorkspace';
const object=(value:unknown):JsonObject=>value!==null&&typeof value==='object'&&!Array.isArray(value)?value as JsonObject:{};
const label=(value:unknown):string=>value===null||value===undefined?'未知':String(value);
const day=(value:unknown):string=>{const text=typeof value==='number'?String(value):value;return typeof text==='string'&&/^\d{8}$/.test(text)?`${text.slice(0,4)}-${text.slice(4,6)}-${text.slice(6)}`:label(value);};
const strings=(value:unknown):string[]=>Array.isArray(value)?value.filter((v):v is string=>typeof v==='string'):[];

/** Full-row aggregate, never a formal screen or candidate count. */
export function renderReboundPanelObservation(host:HTMLElement, input:unknown):void {
  host.replaceChildren();host.hidden=input===undefined||input===null;
  if(host.hidden)return;
  const el=<K extends keyof HTMLElementTagNameMap>(tag:K,text='')=>{const node=document.createElement(tag);node.textContent=text;return node;};
  const value=object(input);
  host.append(el('h3','原面板数值观察（未正式评估）'),
    el('p',`输入行情日期 ${day(value.signal_date)}；计划目标日 ${day(value.target_date)}；实际观察时点 ${label(value.observed_at)}。`),
    el('p',`服务端本次读取时点 ${label(value.observation_read_as_of)}；原计划研究截止 ${label(value.plan_research_cutoff)}。当前观察独立展示，不代表原计划当时已知，未写入保存计划。`),
    el('p','正式资格 CANNOT_CONFIRM；eligible_screen=null。仅当前读取的原生数值，不是正式候选，不代表全市场覆盖。单位、历史尺度、行情终态及目标日资格均未验证。'));
  const reasons=strings(value.reason_codes);
  if(reasons.length)host.append(el('p',`原产物缺口：${reasons.join('；')}`));
  const summary=object(value.row_summary);
  if(value.eligible_screen!==null||value.formal_status!=='CANNOT_CONFIRM'||typeof summary.observed_rows!=='number'||!Number.isInteger(summary.observed_rows)||summary.observed_rows<0){
    host.append(el('p','观察产物未接通或不适用于当前日期、历史视图或服务端读取时点；观察记录数未知，正式筛选保持原状态。'));return;
  }
  host.append(el('p',`观察记录 ${label(summary.observed_rows)} 条；输入不完整 ${label(summary.numeric_input_incomplete)} 条。以上是记录数，不是候选数。`));
  const missing=strings(summary.missing_history_dates);
  host.append(el('p',missing.length?`历史缺失日期：${missing.map(day).join('、')}。`:'未返回历史缺失日期；不据此认定历史尺度或正式资格已验证。'));
  const comparisons=object(summary.native_comparison_counts);
  for(const [key,title] of [['close_le_prior60_high_times_0_8','收盘≤此前60日高点×0.8'],['current_to_previous5_ge_1_5','当日量/此前5日均量≥1.5']]){
    const counts=object(comparisons[key]);
    host.append(el('p',`${title}：未知 ${label(counts.unknown)} 条；数值比较为真 ${label(counts.true)} 条；数值比较为假 ${label(counts.false)} 条。未据此评估正式资格。`));
  }
  host.append(el('p','此处展示全量记录汇总；完整逐行数值保留在绑定的独立观察产物，未截断计算输入，也未加入正式筛选。'));
  const evidence=el('details');evidence.append(el('summary','全量汇总缺口与原产物 SHA 引用'));
  let shown=false;evidence.addEventListener('toggle',()=>{if(evidence.open&&!shown){shown=true;evidence.append(el('pre',JSON.stringify({
    source_run_id:value.source_run_id,binding_reference:value.binding_reference,scope:value.scope,row_summary:summary},null,2)));}});
  host.append(evidence);
}


// Shared V4 row renderer. Legacy qualified-screen behavior remains the default;
// saved independent observations explicitly select the downgraded presentation.
const cardText=(value:unknown,absent='未提供')=>typeof value==='string'&&value?value:absent;
const cardNumber=(value:unknown,digits=4)=>typeof value==='number'&&Number.isFinite(value)?value.toFixed(digits):'未知';
const cardScalar=(value:unknown,absent='未提供')=>typeof value==='number'&&Number.isFinite(value)?String(value):cardText(value,absent);
const cardEl=<K extends keyof HTMLElementTagNameMap>(tag:K,content='',className='')=>{const node=document.createElement(tag);node.textContent=content;node.className=className;return node;};
const cardDetails=(title:string,value:unknown)=>{const node=cardEl('details');node.append(cardEl('summary',title));let loaded=false;node.addEventListener('toggle',()=>{if(node.open&&!loaded){loaded=true;node.append(cardEl('pre',JSON.stringify(value,null,2)));}});return node;};
export const reboundGroupLabels:Record<import('../api/m18SavedResult').ReboundGroup,string>={strict:'严格条件研究观察',near:'近条件研究观察',pending:'待核数据/历史',excluded:'已排除观察',screen_unresolved:'未决观察'};
function withoutLocalPaths(value:unknown):unknown{
  if(Array.isArray(value))return value.map(withoutLocalPaths);
  if(value!==null&&typeof value==='object')return Object.fromEntries(Object.entries(value).filter(([key])=>!/(^path$|_path$|^root$|_root$)/i.test(key)).map(([key,item])=>[key,withoutLocalPaths(item)]));
  return value;
}
export function renderReboundScreenCard(row:JsonObject,pending=false,group?:import('../api/m18SavedResult').ReboundGroup):HTMLElement{
  const node=cardEl('article','','manager-catalyst-card');
  const classification=group?reboundGroupLabels[group]:pending?'待核数据/历史':String(row.classification)==='STRICT_REBOUND'?'严格候选':'近条件候选';
  node.dataset.screenCode=cardText(row.code,'UNKNOWN');
  node.dataset.screenStatus=group?'UNVERIFIED_RESEARCH_OBSERVATION':pending?'PARTIAL_UNKNOWN':String(row.history_status||'KNOWN');
  node.append(cardEl('h4',`${cardText(row.name)} · ${cardText(row.code)} · ${classification}`));
  if(group){
    node.append(cardEl('p',`原分类 ${label(row.classification)}；分组理由：${label(row.reason_for_group)}。`),
      cardEl('p',`观察行情日 ${day(row.observed_session)}；目标日 ${day(row.target_monday??row.target_trade_date)}；研究资格 ${label(row.qualification_status)}；互联互通 ${label(row.connect_eligibility)}。`),
      cardEl('p',`原生成交额 amount_native ${cardNumber(row.amount_native,0)}；币种 ${label(row.currency)}；成交额单位 ${label(row.amount_unit)}；成交量单位 ${label(row.volume_unit)}。`),
      cardEl('p',`收盘 ${cardNumber(row.close)}；此前60日高点 ${cardNumber(row.prior60_session_high)}；原超跌门槛 ${cardNumber(row.oversold_cutoff_80pct_prior60_high)}；原数值超跌标记 ${label(row.oversold_flag)}；价格币种 ${label(row.price_currency)}。`),
      cardEl('p',`5日量比 ${cardNumber(row.volume_ratio_5d)} / 1.5；原量比标记 ${label(row.volume_flag_5d_ge_1_5)}；60日历史 ${label(row.history_status)}（${cardScalar(row.prior60_session_count,'?')}个交易日）。数值比较不确认正式资格。`));
  }else{
    node.append(cardEl('p',`成交额 ${cardNumber(row.amount_hkd,0)} HKD（观察值）；60日历史 ${cardText(row.history_status)}（${cardScalar(row.prior60_session_count,'?')}个交易日）`),
      cardEl('p',`超跌 ${row.oversold_flag===true?'通过':row.oversold_flag===false?'未通过':'待核'}；5日量比 ${cardNumber(row.volume_ratio_5d)} / 1.5；收盘较当日低点反弹 ${cardNumber(row.rebound_close_vs_low_pct,2)}%（观察值）`));
  }
  if(row.near_failed_gate)node.append(cardEl('p',`剩余条件差项：${cardText(row.near_failed_gate)} = ${cardNumber(row.near_failed_value)}，门槛 ${cardNumber(row.near_gate_value)}，相对差距 ${cardNumber(row.near_gate_gap_ratio)}`));
  if(group&&row.near_failed_gate)node.append(cardEl('p',`原条件差值 ${cardNumber(row.near_gate_gap_value)}。`));
  if(pending||group==='pending')node.append(cardEl('p',`待核原因：${group?label(row.history_unknown_reasons):cardText(row.history_unknown_reasons,'60日历史不足，不能完成严格或近条件判定。')}`));
  if(group==='excluded')node.append(cardEl('p',`排除代码 ${label(row.exclusion_reason_code)}；排除理由：${label(row.reason_for_exclusion)}。`));
  node.append(cardEl('p',group?'独立研究观察，未写入保存计划；单位、历史尺度与正式资格缺口保持原状。':'仅由已核验共享HK 0.2面板重算；研究筛选结果，不是买卖、下单或Stage门禁。'),cardDetails('该股筛选数值、差项与来源',group?withoutLocalPaths(row):row));
  return node;
}
/** Only the fields rendered here; independent owners need no invented M18 identity. */
export interface SavedReboundPresentation {
  source_kind?: string;
  projection?: string;
  group?: import('../api/m18SavedResult').ReboundGroup;
  rebound?: import('../api/m18SavedResult').ReboundMetadata;
  matched_total: number;
  entries: Pick<import('../api/m18SavedResult').SavedEntry, 'index' | 'bytes' | 'sha256' | 'value_state' | 'reason' | 'value'>[];
}
export function renderSavedReboundReferences(host:HTMLElement,page:SavedReboundPresentation):void{
  const independent=page.source_kind==='M14_OWNER';
  host.replaceChildren(cardEl('h3',independent?'M14 独立已保存超跌研究':'超跌研究观察（同次运行保存响应）'));host.setAttribute('aria-label',independent?'M14 独立已保存超跌研究':'同次运行超跌研究观察');
  const meta=page.rebound,group=page.group;
  if(page.projection!=='rebound_references'||!meta||!group){host.append(cardEl('p','CANNOT_CONFIRM：研究观察尚未读取。'));return;}
  const source=meta.source,observation=meta.observation;
  host.append(cardEl('p',`外层状态 ${label(source.status)}；观察状态 ${label(observation.status)}；原计算状态 ${label(observation.original_computation_status)}。`),
    cardEl('p',independent?'这是 M14 原运行的独立已保存研究；读取不重新计算。正式资格 CANNOT_CONFIRM，未改变 market_screen；单位和互联互通未核实，不能据研究分组推定可交易。':'这是独立读取时研究观察，不是保存计划消费或正式筛选。正式资格 CANNOT_CONFIRM，未改变 market_screen；单位和互联互通未核实，不能据研究分组推定可交易。'),
    cardEl('p',`原范围：${label(source.scope)}；eligible_screen=${source.eligible_screen===null?'null':label(source.eligible_screen)}。`),
    cardEl('p',Object.entries(reboundGroupLabels).map(([key,title])=>`${title} ${meta.group_counts[key as import('../api/m18SavedResult').ReboundGroup]}`).join('；')+'。各原分组分开分页，不重复计入 cards 合并数组。'));
  host.append(cardEl('p',`观察行情日 ${day(observation.observed_session)}；观察目标日 ${day(observation.target_trade_date)}。`));
  const native=object(observation.native_evidence);if(Object.keys(native).length)host.append(cardEl('p',`原单位证据：${label(object(native.unit_evidence).status)}；原行情日期证据：${label(object(native.date_evidence).observation_status)}。不把准备时间或读取时间替代计划研究截止。`));
  for(const [title,raw] of [['外层缺口',source.reason_codes],['观察缺口',observation.gaps]])if(Array.isArray(raw)&&raw.length)host.append(cardEl('p',`${title}：${raw.map(label).join('；')}`));
  if(page.matched_total===0)host.append(cardEl('p',`${reboundGroupLabels[group]}原数组为 0 条，不代表正式资格已确认。`));
  for(const entry of page.entries){
    if(entry.value_state!=='LOADED'){host.append(cardEl('p',`记录 ${entry.index+1} · NOT_LOADED · ${entry.reason??'NOT_LOADED'}；${entry.bytes} bytes；SHA256 ${entry.sha256}`));continue;}
    const row=object(entry.value);
    if(typeof row.code!=='string'||!row.code){host.append(cardEl('p',`记录 ${entry.index+1} · 股票字段未确认：${JSON.stringify(entry.value)}`));continue;}
    const card=renderReboundScreenCard(row,false,group);card.append(cardEl('p',`保存条目 SHA256 ${entry.sha256}`));host.append(card);
  }
  host.append(cardDetails('观察范围、覆盖、原缺口与来源绑定',withoutLocalPaths(meta)));
}
