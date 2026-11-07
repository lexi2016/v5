const SOURCE_DATE=null;
export function mountConsolidatedReview({document,parent,review:r,csv}){
 if(SOURCE_DATE===null||r?.scope!=='POST_CLOSE_RETROSPECTIVE_ONLY_NOT_1500_CAPTURE'||r.data_date!==SOURCE_DATE||r.natural_verified!==false||r.business_accepted!==false||r.rows?.length!==200||r.rows.some(x=>x.historical_PIT!==false||x.source_admission!==false||x.buy_eligibility!=='NOT_EVALUATED'))throw Error('CONSOLIDATED_SCOPE');
 const el=(tag,text='')=>{const e=document.createElement(tag);e.textContent=text;return e;};
 parent.append(el('strong','收盘后事后复盘，非15:00已知。排名源G4，不能倒写为盘前或15点采集完成。'),el('p',`200行；既有四组TRUE ${r.counts.existing_any_true}；含UNKNOWN ${r.counts.has_unknown}；新闻名称命中 ${r.counts.news_matched}。身份/事实总体UNKNOWN，单张公告不认证全表；NO_BUY，图审UNKNOWN。`));
 const table=el('table'),head=el('tr');for(const x of ['原排名','完整代码/原名','排名日/来源','选股行日/来源','原公式/小K/回踩/突破','新闻名称命中','公告/名称附注','资格'])head.append(el('th',x));table.append(head);
 for(const row of r.rows){const tr=el('tr');for(const value of [row.rank,`${row.symbol} ${row.name_retained}`,`${row.rank_date} / ${row.ranking_source}`,`${row.selection_row_date} / ${row.selection_row_source}`,`${row.original} / ${row.nav_smallk} / ${row.nav_pullback} / ${row.nav_breakout}`,`${row.news_mention_lines}处；身份/事实UNKNOWN`,[row.official_note,row.name_event_note].filter(Boolean).join('；')||'UNKNOWN','NO_BUY；图审UNKNOWN；PIT=false；source_admission=false'])tr.append(el('td',String(value)));table.append(tr);}parent.append(table);
 const raw=el('details');raw.append(el('summary','打开原REVIEW200.csv全文（只读）'),el('pre',csv));parent.append(raw);
}
