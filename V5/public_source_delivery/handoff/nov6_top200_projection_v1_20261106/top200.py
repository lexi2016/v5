"""Nov6 fixed-reference Top200 projection. No market requests or indicator work.

The Decimal ranking is the recovered D30 research rule, applied to independently
verified current G4 bytes. This is not a new universe, BUY rule, or owner run.
"""
import csv
import hashlib
import io
import json
import math
import os
import re
import stat
from contextlib import contextmanager
from decimal import Context, Decimal, ROUND_HALF_EVEN, localcontext
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOME = 'handoff/nov6_top200_projection_v1_20261106'
TARGET = 20261106
MEMORY = 2952790016
DISK = 1879048192
CAP = 16777216
INPUT_MANIFEST = {'path':HOME+'/INPUT_REFS.json','bytes':1143,
                  'sha256':'77c37165891af89dc74b0449fb048633862d4610f940717a6be9f825e11363a9'}
FLAGS = dict(no_buy=True,production_allowed=False,source_admission=False,
             selection_admission=False,business_admission=False,full_universe_certified=False,
             historical_PIT=False,main_four_group_results_changed=False)

def need(ok, message):
    if not ok: raise ValueError(message)

def encode(value):
    return (json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()

def digest(value): return hashlib.sha256(encode(value)).hexdigest()

def numeric(v):
    return type(v) in (int,float) and math.isfinite(v)

def same(a,b):
    return type(a) is type(b) and (a==b or type(a)is float and math.isnan(a) and math.isnan(b))

def rank_row(row):
    symbol=row.get('symbol')
    need(type(symbol)is str and re.fullmatch(r'\d{6}\.(SH|SZ|BJ)',symbol),'SYMBOL')
    need(type(row.get('source_date'))is int and row['source_date']==TARGET,'SOURCE_DATE')
    state=row.get('status')
    need(state in ('RAW_OHLCV_VALID_NOT_ADMITTED','EXPLICIT_ZERO_BAR_NO_VALID_OHLCV'), 'UNKNOWN_SOURCE_STATUS')
    base=dict(symbol=symbol,source_date=TARGET,actual_date=TARGET,rank=None,
              rank_eligibility='UNKNOWN',change_pct_decimal=None,change_pct_display=None,
              reason=None,**FLAGS)
    block=row['original_block']
    if state=='EXPLICIT_ZERO_BAR_NO_VALID_OHLCV':
        base.update(actual_date=None,reason=state)
        return base
    bar=row['bar']
    need(all(same(bar[k],block[k]) for k in ('open','high','low','close','amount')),'RAW_BAR_JOIN')
    need(same(row['reference_previous'],block['previous']),'RAW_PREVIOUS_JOIN')
    need(same(row['native_volume'],block['native_volume']),'RAW_VOLUME_JOIN')
    need((bar.get('year'),bar.get('month'),bar.get('day'))==(2026,11,6),'BAR_DATE')
    fields=('open','high','low','close','previous','native_volume')
    if not all(numeric(block[k])and block[k]>0 for k in fields):
        base['reason']='NONPOSITIVE_OR_NONFINITE_REQUIRED_RAW_VALUE'; return base
    if not (block['high']>=max(block[k]for k in ('open','low','close')) and
            block['low']<=min(block[k]for k in ('open','high','close'))):
        base['reason']='INVALID_RAW_OHLC_ENVELOPE';return base
    with localcontext(Context(prec=28,rounding=ROUND_HALF_EVEN)):
        change=(Decimal(str(block['close']))/Decimal(str(block['previous']))-1)*100
        display=str(change.quantize(Decimal('.01')))
    off=block['md1_byte_offset']
    need(type(off)is int and off>=0,'OFFSET')
    base.update(rank_eligibility='RANKABLE_FIXED_REFERENCE_RESEARCH_ONLY',reason=None,
                raw_close=str(block['close']),reference_previous=str(block['previous']),
                open=str(block['open']),high=str(block['high']),low=str(block['low']),
                native_volume=str(block['native_volume']),amount_raw=str(block['amount']),
                change_pct_decimal=str(change),change_pct_display=display,
                volume_vendor_unit_certification='UNCONFIRMED',amount_display_currency_certified=False,
                lineage=dict(md1_member=block['md1_member'],cod_member=block['cod_member'],
                             md1_byte_offset=off,reference_byte_offset=off+4,close_byte_offset=off+36,
                             cod_record_index=block['cod_record_index'],seq=block['seq']))
    return base

def project_rows(rows,symbols):
    need(type(rows)is list and type(symbols)is list,'ARRAY_SCOPE')
    need(len(symbols)==len(set(symbols)),'DUPLICATE_SCOPE')
    by={r['symbol']:r for r in rows}
    need(len(rows)==len(by)==len(symbols)and set(by)==set(symbols),'EXACT_FULL_SCOPE')
    scope=[rank_row(by[s]) for s in symbols]
    ranked=[r for r in scope if r['rank_eligibility']!='UNKNOWN']
    ranked.sort(key=lambda r:(Decimal(r['change_pct_decimal']).copy_negate(),r['symbol']))
    for i,r in enumerate(ranked,1):r['rank']=i
    return dict(schema='NOV6_FIXED_REFERENCE_TOP200_V1',status='READY_PENDING_INDEPENDENT_REVIEW',
                source_date=TARGET,scope_count=len(scope),valid_rank_count=len(ranked),
                unknown_count=len(scope)-len(ranked),top_count=min(200,len(ranked)),
                rows=ranked[:200],unknown=[r for r in scope if r['rank_eligibility']=='UNKNOWN'],
                scope_rows=scope,rank_rule='Decimal precision28 ROUND_HALF_EVEN; (G4 close/G4 previous-1)*100 descending, symbol ascending tie-break',
                scope_label='Existing fixed5575 mixed-source research identity reference; not certified exchange-wide ordinary-A universe',
                numerical_four_group_filter_applied=False,score_or_action_filter_applied=False,
                formula_calls=0,native_calls=0,parquet_reads=0,market_requests=0,**FLAGS)

@contextmanager
def held(relative, root=ROOT):
    parts=Path(relative).parts
    need(parts and not Path(relative).is_absolute()and all(x not in ('.','..')for x in parts),'RELATIVE_PATH')
    fds=[os.open(root,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)]
    links=[]
    try:
        for part in parts[:-1]:
            fd=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fds[-1])
            links.append((fds[-1],part,fd));fds.append(fd)
        def verify():
            s=os.stat(root,follow_symlinks=False);a=os.fstat(fds[0])
            need((s.st_dev,s.st_ino)==(a.st_dev,a.st_ino),'ROOT_CHANGED')
            for parent,name,child in links:
                s=os.stat(name,dir_fd=parent,follow_symlinks=False);a=os.fstat(child)
                need(stat.S_ISDIR(s.st_mode)and(s.st_dev,s.st_ino)==(a.st_dev,a.st_ino),'DIRECTORY_CHANGED')
        verify();yield fds[-1],parts[-1],verify;verify()
    finally:
        for fd in reversed(fds):os.close(fd)

def checked(pin,root=ROOT):
    need(type(pin)is dict and type(pin['bytes'])is int and 0<=pin['bytes']<=16*1024**2,'INPUT_SIZE')
    need(type(pin['sha256'])is str and re.fullmatch('[a-f0-9]{64}',pin['sha256']),'INPUT_SHA')
    with held(pin['path'],root)as(parent,leaf,verify):
        fd=os.open(leaf,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent)
        try:
            before=os.fstat(fd);need(stat.S_ISREG(before.st_mode)and before.st_size==pin['bytes'],'INPUT_REGULAR_SIZE')
            chunks=[];left=pin['bytes']+1
            while left:
                b=os.read(fd,min(left,1024*1024))
                if not b:break
                chunks.append(b);left-=len(b)
            result=b''.join(chunks);after=os.fstat(fd);named=os.stat(leaf,dir_fd=parent,follow_symlinks=False)
            key=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
            need(key(before)==key(after)==key(named),'INPUT_CHANGED');verify()
            need(len(result)==pin['bytes']and hashlib.sha256(result).hexdigest()==pin['sha256'],'INPUT_HASH')
            return result
        finally:os.close(fd)

def resources():
    info=Path('/proc/meminfo').read_text()
    memory=int(re.search(r'^MemAvailable:\s+(\d+) kB$',info,re.M)[1])*1024
    cg=Path('/sys/fs/cgroup/memory.max');cur=Path('/sys/fs/cgroup/memory.current')
    if cg.exists()and cur.exists():
        limit=cg.read_text().strip();used=cur.read_text().strip()
        if limit!='max': memory=min(memory,int(limit)-int(used))
    disk=os.statvfs(ROOT);free=disk.f_bavail*disk.f_frsize
    need(memory>=MEMORY and free>=DISK+CAP,'ORIGINAL_RESOURCE_FLOOR_PLUS_PROJECTION_CAP')
    return dict(available_memory_bytes=memory,disk_free_bytes=free,memory_floor=MEMORY,disk_floor=DISK,output_cap=CAP)

def main():
    resources_before=resources()
    # The entry manifest is local explicit task-owner input, not a source-discovered filename.
    refs=json.loads(checked(INPUT_MANIFEST))
    loaded={k:checked(v)for k,v in refs.items()}
    review=json.loads(loaded['source_review']);ledger=json.loads(loaded['ledger']);catalog=json.loads(loaded['catalog'])
    need(review['status']=='PASS_SCOPED_ACTUAL_RAW_LEDGER_AND_GBBQ_INTEGRITY_REVIEW'and review['source_date']==TARGET,'RAW_REVIEW')
    need(review['ledger_ref']==refs['ledger']and review['catalog_ref']==refs['catalog'],'REVIEW_BINDING')
    need(ledger['fixed_scope_count']==5575 and ledger['source_date']==TARGET,'FIXED_5575_TARGET')
    symbols=[r['symbol']for r in catalog['latest_selections']]
    need(len(symbols)==5575 and symbols==ledger['scope_order'],'CATALOG_ORDER')
    projection=project_rows(ledger['rows'],symbols)
    projection.update(input_refs=refs,raw_ledger_sha256=refs['ledger']['sha256'],package_ref=ledger['package_ref'],
                      original_parser_ref=ledger['parser_ref'],original_g4_fields_are_inferred_offsets=True,
                      source_timestamps=review['source_timestamps']['g4'])
    scope=projection.pop('scope_rows')
    scope_doc=dict(schema='NOV6_TOP200_FULL_SCOPE_LEDGER_V1',source_date=TARGET,rows=scope,input_refs=refs,**FLAGS)
    consumer=projection
    buf=io.StringIO(newline='');columns=['rank','symbol','source_date','raw_close','reference_previous','change_pct_decimal','change_pct_display','native_volume','amount_raw']
    writer=csv.DictWriter(buf,fieldnames=columns,extrasaction='ignore');writer.writeheader();writer.writerows(consumer['rows'])
    files={'SCOPE5575.json':encode(scope_doc),'TOP200.json':encode(consumer),'TOP200.csv':buf.getvalue().encode()}
    need(sum(map(len,files.values()))+65536<CAP,'OUTPUT_CAP')
    for pin in refs.values():checked(pin)
    resources_after=resources()
    with held(HOME+'/run_20261106_once')as(parent,name,verify):
        os.mkdir(name,dir_fd=parent);os.fsync(parent)
        fd=os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=parent)
        try:
            need(not os.listdir(fd),'NEW_DIRECTORY_NOT_EMPTY');identity=os.fstat(fd)
            def outverify():
                verify();s=os.stat(name,dir_fd=parent,follow_symlinks=False)
                need(stat.S_ISDIR(s.st_mode)and(s.st_dev,s.st_ino)==(identity.st_dev,identity.st_ino),'OUTPUT_REPLACED')
            written=0;output_refs=[]
            def save(leaf,b):
                nonlocal written
                written+=len(b);need(written<CAP,'OUTPUT_CAP');outverify()
                out=os.open(leaf,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=fd)
                try:
                    view=memoryview(b)
                    while view:view=view[os.write(out,view):]
                    os.fsync(out)
                finally:os.close(out)
                os.fsync(fd);outverify()
                return dict(path=HOME+'/run_20261106_once/'+leaf,bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
            for leaf,b in files.items():output_refs.append(save(leaf,b))
            manifest=dict(schema='NOV6_TOP200_PROJECTION_MANIFEST_V1',status='COMPLETE_PENDING_INDEPENDENT_REVIEW',
                          source_date=TARGET,scope_count=5575,valid_rank_count=consumer['valid_rank_count'],unknown_count=consumer['unknown_count'],
                          top_count=consumer['top_count'],output_refs=output_refs,input_refs=refs,resource_before=resources_before,resource_after=resources_after,
                          source_file_unchanged_verified=True,no_formula_native_par_or_network=True,**FLAGS)
            result=save('MANIFEST.json',encode(manifest));print(json.dumps(result))
        finally:os.close(fd)

if __name__=='__main__':main()
