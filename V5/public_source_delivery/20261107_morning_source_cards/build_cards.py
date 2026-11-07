"""Readonly Top200/text exact-name association. No rankings, labels or formula changes."""
import argparse,csv,hashlib,html,json,sqlite3
from pathlib import Path

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def build(db, texts, out, expected_db_sha):
    if sha(db)!=expected_db_sha: raise ValueError('database input hash changed')
    receipt=json.loads((texts/'RECEIPT.json').read_text())
    records=receipt['records']
    if len(records)!=3: raise ValueError('three source records required')
    articles=[]
    for r in records:
        f=Path(r['file'])
        if f.name!=str(f): raise ValueError('nonlocal source path')
        p=texts/f
        if p.stat().st_size!=r['bytes'] or sha(p)!=r['sha256']:raise ValueError('source hash/size changed')
        articles.append((r,p.read_text().splitlines()))
    con=sqlite3.connect(db.resolve().as_uri()+'?mode=ro',uri=True)
    rows=con.execute('SELECT p.symbol,p.name,t.rank,p.actual_date,t.actual_date FROM top200 t JOIN panel p USING(symbol) ORDER BY t.rank').fetchall();con.close()
    if len(rows)!=200 or len({r[0] for r in rows})!=200:raise ValueError('Top200 denominator mismatch')
    cards=[]
    for symbol,name,rank,panel_date,rank_date in rows:
        mentions=[]
        if name:
            for source,lines in articles:
                for line_no,line in enumerate(lines,1):
                    if name in line:
                        mentions.append(dict(file=source['file'],line=line_no,quote=line,url=source['url'],sha256=source['sha256'],published_time_raw=source['published_time_raw'],timezone=source['timezone']))
        cards.append(dict(symbol=symbol,name=name,rank=rank,panel_date=panel_date,rank_date=rank_date,association='EXACT_NAME_TEXT_MATCH_REQUIRES_IDENTITY_REVIEW' if mentions else 'NOT_MATCHED_IN_THESE_THREE_TEXTS',identity_review='UNKNOWN',factual_verification='UNKNOWN',buy_eligibility='NOT_EVALUATED',mentions=mentions))
    out.mkdir(parents=True,exist_ok=False)
    payload=dict(source_date=receipt['data_date'],mode='HISTORICAL_TEXT_ASSOCIATION_ONLY',source_receipt_sha256=sha(texts/'RECEIPT.json'),database_sha256=expected_db_sha,denominator=200,matched_symbols=sum(bool(c['mentions']) for c in cards),mention_lines=sum(len(c['mentions']) for c in cards),natural_verified=False,business_accepted=False,images_reviewed=False,cards=cards)
    (out/'cards.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
    with (out/'coverage.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['symbol','name','rank','panel_date','rank_date','association','mention_lines','identity_review','factual_verification'])
        for c in cards:w.writerow([c[k] for k in ['symbol','name','rank','panel_date','rank_date','association']]+[len(c['mentions']),'UNKNOWN','UNKNOWN'])
    esc=html.escape
    body=['<!doctype html><meta charset="utf-8"><title>Top200 盘前三栏来源关联</title><style>body{font:16px system-ui;max-width:1100px;margin:30px auto;padding:16px}details{border-bottom:1px solid #ddd;padding:12px}blockquote{white-space:pre-wrap;background:#f5f5f5;padding:12px}small{color:#555}</style>',f'<h1>Top200 盘前三栏来源关联</h1><p>历史资料日期 {esc(payload["source_date"])}。200 只中 {payload["matched_symbols"]} 只出现同名文本。非新增选股、非买点或公告事实确认。人工身份核对 UNKNOWN；图片未审；自然触发未验收。</p><p>只作原文检索，不因未匹配而判定无题材。不回填盘前已知时间，截止时点之后发布的材料不能视为截止之前已可得。</p>']
    for c in cards:
        body.append(f'<details><summary>{c["rank"]}. {esc(c["symbol"])} {esc(c["name"] or "UNKNOWN")} · {len(c["mentions"])} 处同名文本</summary><small>面板日期 {esc(str(c["panel_date"]))}；排名日期 {esc(str(c["rank_date"]))}；身份/事实 UNKNOWN</small>')
        for m in c['mentions']:body.append(f'<p><a href="{esc(m["url"],quote=True)}">{esc(m["file"])} 第 {m["line"]} 行</a> · {esc(m["published_time_raw"])}（源时区未明）</p><blockquote>{esc(m["quote"])}</blockquote>')
        body.append('</details>')
    (out/'index.html').write_text('\n'.join(body))
    return payload
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--db',type=Path,required=True);p.add_argument('--texts',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--db-sha256',required=True);a=p.parse_args()
    try:
        r=build(a.db,a.texts,a.out,a.db_sha256);print(json.dumps({k:r[k] for k in ['source_date','denominator','matched_symbols','mention_lines','natural_verified','business_accepted']}))
    except (ValueError,OSError,KeyError,sqlite3.Error) as e: p.exit(2,f'BLOCKED: {e}\n')
