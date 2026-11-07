"""Render the source-linked historical brief only; does not fetch or select stocks."""
import argparse,hashlib,html,json
from pathlib import Path

def render(d):
 if d['natural_verified'] or d['business_accepted'] or d['new_selection'] or d['buy_decision']:raise ValueError('HISTORICAL_SCOPE_ONLY')
 if d['matched_symbols']+d['unmatched_symbols']!=d['top200_denominator']:raise ValueError('DENOMINATOR_MISMATCH')
 sources={r['file']:r for r in d['sources']}
 lines=['# '+d['title'],'',d['status']+'。整理日 '+d['prepared_date']+'。','',d['timing_note'],'','## 先看这四条']
 for t in d['themes']:lines+=['- **'+t['title']+'**：'+t['summary']+' [来源，第 '+t['lines']+' 行]('+sources[t['source_file']]['url']+')']
 lines+=['','## 原 Top200 的资料关联',f"完整分母 {d['top200_denominator']}；{d['matched_symbols']} 只同名命中，{d['mention_lines']} 处引文；{d['unmatched_symbols']} 只未匹配。",d['preview_rule'],'、'.join(f"{x['name']}（{x['symbol']}，原第{x['original_top200_rank']}）" for x in d['matched_preview']),'','## 三篇来源与原标时']
 for r in d['sources']:lines+=['- ['+r['file']+']('+r['url']+')：'+r['published_time_raw']+'（源时区未明）']
 lines+=['','## 未验收','；'.join(d['gaps'])+'。']
 md='\n'.join(lines)+'\n';e=html.escape
 body=['<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>'+e(d['title'])+'</title><style>body{font:16px/1.6 system-ui;max-width:1000px;margin:20px auto;padding:18px;color:#243246}h1{font-size:25px}h2{font-size:19px;margin-bottom:4px}li{margin:8px 0}.notice{background:#fff4dc;padding:12px;border-left:4px solid #c0861c}small{color:#666}</style><h1>'+e(d['title'])+'</h1><div class="notice">'+e(d['status']+'。整理日 '+d['prepared_date']+'。 '+d['timing_note'])+'</div><h2>先看这四条</h2><ul>']
 for t in d['themes']:body+=['<li><b>'+e(t['title'])+'</b>：'+e(t['summary'])+' <a href="'+e(sources[t['source_file']]['url'],quote=True)+'">来源 '+e(t['lines'])+' 行</a></li>']
 body+=['</ul><h2>原 Top200 的资料关联</h2><p>'+e(lines[lines.index('## 原 Top200 的资料关联')+1])+'</p><p>'+e(d['preview_rule'])+'</p><p>'+e('、'.join(x['name']+' '+x['symbol'] for x in d['matched_preview']))+'</p><h2>来源与原标时</h2>']
 for r in d['sources']:body+=['<p><a href="'+e(r['url'],quote=True)+'">'+e(r['file'])+'</a> '+e(r['published_time_raw'])+' <small>源时区未明</small></p>']
 body+=['<h2>未验收</h2><p>'+e('；'.join(d['gaps']))+'。</p></html>']
 return md,'\n'.join(body)
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--input',type=Path,required=True);a.add_argument('--sha256',required=True);a.add_argument('--out',type=Path,required=True);x=a.parse_args();raw=x.input.read_bytes()
 if hashlib.sha256(raw).hexdigest()!=x.sha256:a.exit(2,'INPUT_HASH_MISMATCH\n')
 md,ht=render(json.loads(raw));x.out.mkdir(exist_ok=False);(x.out/'BRIEF.md').write_text(md);(x.out/'index.html').write_text(ht)
