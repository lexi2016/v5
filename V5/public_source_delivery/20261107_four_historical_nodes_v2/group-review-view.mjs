const SOURCE_DATE=null;
export function mountGroupReview({document,parent,review,provenance}){
 if(SOURCE_DATE===null||provenance?.source!=='G4'||provenance.historical_PIT!==false||provenance.source_admission!==false||review.source_date!==SOURCE_DATE||review.buy_qualification!==false||review.rows?.length!==200||review.rows.some(r=>r.no_buy!==true))throw Error('GROUP_REVIEW_SCOPE');
 const el=(tag,text='')=>{const e=document.createElement(tag);e.textContent=text;return e;};
 parent.append(el('strong','事后复盘，非当日盘前已知。'+provenance.notice),el('p',`08:50历史研究表：原范围 ${review.denominator}；Top200 ${review.top_rows}；既有四组TRUE重合 ${review.selected_overlap}；含UNKNOWN ${review.unknown_overlap}。NO_BUY；不是新选股、冻结观察名单或买入/持有指令。`));
 const table=el('table'),head=el('tr');for(const name of ['原排名','代码/旧展示名','排名日','选股行日','选股来源/状态','原公式','导航小K','导航回踩','导航突破','资格'])head.append(el('th',name));table.append(head);
 for(const r of review.rows){const tr=el('tr');for(const value of [r.rank,`${r.symbol} ${r.name}`,r.rank_actual_date,r.selection_actual_date,`${r.source_family} / ${r.owner_outcome}`,r.groups.original,r.groups.nav_smallk,r.groups.nav_pullback,r.groups.nav_breakout,'NO_BUY；图审UNKNOWN'])tr.append(el('td',String(value)));table.append(tr);}parent.append(table,el('p','选股来源列不代表排名来源。排名来源G4、事后排名，非盘前已知；historical_PIT=false，source_admission=false。逐行旧日期和UNKNOWN原样保留，不修改原筛选。'));
}
