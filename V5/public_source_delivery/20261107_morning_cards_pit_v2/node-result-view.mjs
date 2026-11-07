const RECORD_DATE=null; // Private exact-record binding deliberately excluded.
const NODES=new Set(['morning-materials','terminal-1700','evening-prepare','evening-check','evening-delivery']);
export function mountNodeResult({document,parent,nodeId,loader=loadNodeResult}){
 if(!NODES.has(nodeId))return;
 const el=(tag,text='')=>{const e=document.createElement(tag);e.textContent=text;return e;};
 const section=el('section'),button=el('button',nodeId==='morning-materials'?'事后复盘，非盘前已知 · 打开已绑定历史原文关联':'打开已绑定手动结果原件');button.type='button';const body=el('div');section.append(button,body);parent.append(section);
 button.onclick=async()=>{button.disabled=true;body.replaceChildren(el('p','核验原文件SHA…'));try{const result=await loader(nodeId);if(result.schema!=='EXISTING_MANUAL_NODE_RESULT_V1'||result.node_id!==nodeId||RECORD_DATE===null||result.record_date!==RECORD_DATE||result.natural_verified!==false||result.delivery_status!=='NOT_SENT')throw Error('NODE_BINDING');
 body.replaceChildren(el('h4','已保存手动结果，不是自动业务完成'),el('p',`记录日 ${result.record_date}；资料日 ${result.source_date}；仅手动测试；自然触发未验证；未发送；业务验收未授予。不是当前所选业务日的完成证明。`));
 if(result.records.source_cards){
  const c=result.records.source_cards;const provenance=c.ranking_provenance;if(provenance?.source!=='G4'||provenance.historical_PIT!==false||provenance.source_admission!==false)throw Error('PIT_PROVENANCE');
  const warning=el('strong','事后复盘，非盘前已知。'+provenance.notice);warning.setAttribute?.('role','alert');body.append(warning);
  body.append(el('p',`历史原文关联：完整Top200 ${c.denominator}；名称文本命中 ${c.matched_symbols} 股、${c.mention_lines} 处。身份 UNKNOWN；事实 UNKNOWN；图片未审。截止之后发布的原文不能倒填为截止前可得，网页时区UNKNOWN。未匹配不等于无题材；不改变排序、选股或买入资格。`));
  for(const card of c.cards){const d=el('details');d.append(el('summary',`${card.rank} · ${card.symbol} ${card.name} · ${card.mentions.length}处名称命中`),el('p',`排名日 ${card.rank_date}；个股面板日 ${card.panel_date}；身份 ${card.identity_review}；事实 ${card.factual_verification}`));for(const m of card.mentions)d.append(el('p',`原发布时间 ${m.published_time_raw}（${m.timezone}）；${m.file}:${m.line}`),el('blockquote',m.quote),el('p',`来源 ${m.url}；SHA256 ${m.sha256}`));if(!card.mentions.length)d.append(el('p','本三篇未匹配，不推断无题材。'));body.append(d);}
 }
 for(const [role,title]of [['receipt','实际运行回执'],['summary','选股导出摘要'],['report','节点检查报告'],['delivery_text','19点本地交付正文（未发送）'],['selected_csv','候选原CSV'],['pending_csv','待核原CSV']]){const value=result.records[role];if(value===undefined)continue;const details=el('details');details.append(el('summary',title),el('pre',typeof value==='string'?value:JSON.stringify(value,null,2)));body.append(details);}
 }catch{body.replaceChildren(el('p','UNKNOWN · 原件缺失或校验失败，没有替换为其他记录。'));}finally{button.disabled=false;}};
}
async function loadNodeResult(){throw Error('PUBLIC_EXPORT_NO_APPROVED_PRIVATE_BINDING');}
