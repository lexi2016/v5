"""Independent, diagnostic-only Futu single-page history canary.

`args` is entirely offline. Only explicit `capture` loads the existing SDK.
No owner build, subscription, order, retry, pagination, credential read or install.
"""
from __future__ import annotations
import argparse
import ast
from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib
import inspect
import json
import math
import multiprocessing
import os
from pathlib import Path
import re
import stat
import struct
import sys
import time
import types
from typing import Any
import uuid

PINNED = Path(__file__).absolute().parent / 'pinned'
PINS = {
    'safe_io.py': 'e1a5fc5dba23dd10c727f002848b38e6d688b98316c99480bbef95fd97c66312',
    'repair.py': '9f547b8d2307b847b3d284eff2e5914d715283a06eb427044074b34bdc3114da',
    'contracts.py': 'eee026873e0d765fcedf52077daea823edf6ee7013f37c106c82b66a4582d85a',
    'trading_calendar.py': '584f28d18273a8824c5f68a701aa4404123b5c71900caada3e2772828991ee8f',
    'market_calendar_2026.json': '9e2638b69e25495478cecb6ed551713178fcb989a63ebb4ecfd59689615f0acb',
    'workspace_plan.py': 'be0d5e69ff72efd07d2caca4e68948245db4900a8c41f467e9c30f6899c044b1',
    'futu_quote_provider.py': 'b8ce38b6e255a0048a0028024c6c5bb376762e906a2dc4602c32dcb1ac91faae',
}
ALLOWED_CODES = ('HK.00001', 'HK.00376', 'HK.01191')
HOST, PORT = '127.0.0.1', 11111
START, END, SIGNAL, TARGET = '2026-07-20', '2026-10-13', '20261013', '20261014'
MAX_SECONDS, MIN_INTERVAL = 60.0, 1.0
SAFETY = dict(research_only=True, formal=False, natural=False, production=False,
              production_allowed=False, orders=False, orders_sent=False, buy=False,
              buy_gate_updated=False, formal_eligibility_verified=False, natural_verified=False)
CONTRACT = dict(source_contract='FUTU_HISTORY_K_DAY_AUTYPE_NONE_SDK_NATIVE',
    price_adjustment='AuType.NONE_UNADJUSTED', price_scale_applied=1,
    volume_scale_applied=1, turnover_scale_applied=1,
    volume_unit='NOT_EXPLICITLY_DOCUMENTED_ON_HISTORY_FIELD_PAGE',
    price_currency='NOT_PROVEN', turnover_currency='NOT_PROVEN',
    cross_source_unit_equivalence=False, historical_pit=False,
    provider_finality='NOT_ATTESTED', run_class='MANUAL_RECOVERY', **SAFETY)


def _bootstrap_read(path, limit=2*1024**2):
    """Bootstrap pinned safe-I/O loading without following any path symlink."""
    path = Path(path)
    if '..' in path.parts: raise ValueError('PARENT_TRAVERSAL')
    path = Path(os.path.abspath(path))
    fd = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in path.parts[1:-1]:
            nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd); fd = nxt
        file_fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
    finally: os.close(fd)
    try:
        before = os.fstat(file_fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size > limit: raise ValueError('NOT_BOUNDED_REGULAR_FILE')
        with os.fdopen(os.dup(file_fd), 'rb') as stream: raw = stream.read(limit+1)
        after = os.fstat(file_fd)
        fields = lambda s: (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
        if len(raw)>limit or fields(before)!=fields(after): raise ValueError('SOURCE_CHANGED')
        return raw
    finally: os.close(file_fd)


def _extract(raw, names, scope, filename):
    selected = [n for n in ast.parse(raw).body if isinstance(n, ast.FunctionDef) and n.name in names]
    if sorted(n.name for n in selected) != sorted(names): raise ValueError('PINNED_FUNCTION_MISSING')
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(filename), 'exec'), scope)
    return scope


def _sources(source_root=PINNED):
    root = Path(source_root)
    raws = {name: _bootstrap_read(root/name) for name in PINS}
    for name, raw in raws.items():
        if hashlib.sha256(raw).hexdigest()!=PINS[name]: raise ValueError('PINNED_SOURCE_SHA:'+name)
    names = ['_canonical','_sha','_absolute','_open_directory','_read','_json','_new_output','_write_once']
    scope = dict(json=json, hashlib=hashlib, Path=Path, os=os, re=re, stat=stat, MAX_INPUT_BYTES=2*1024**2)
    _extract(raws['safe_io.py'], names, scope, root/'safe_io.py')
    return raws, types.SimpleNamespace(**{name:scope[name] for name in names})


def _window(raws, source_root):
    scope = dict(re=re, datetime=datetime)
    _extract(raws['contracts.py'], ['trade_date'], scope, Path(source_root)/'contracts.py')
    # Only the original window function executes. The owner is not imported or built.
    # Its read-only source provider is bound to these independently pinned bytes.
    source_map = {'contracts/trading_calendar.py':raws['trading_calendar.py'],
        'contracts/market_calendar_2026.json':raws['market_calendar_2026.json'],
        'v4/manager_research/workspace_plan.py':raws['workspace_plan.py']}
    scope.update(owner_io=types.SimpleNamespace(_sources=lambda:dict(source_map), CAPSULE=Path(source_root)),
                 types=types, sys=sys, ast=ast, uuid=uuid, hashlib=hashlib)
    _extract(raws['repair.py'], ['_history_window'], scope, Path(source_root)/'repair.py')
    return scope['_history_window'](SIGNAL)


def symbolic_request(code):
    return dict(code=code, start=START, end=END, ktype='K_DAY', autype='NONE',
                fields=['ALL'], max_count=100, page_req_key=None, extended_time=False, session='NONE')


def prepare_plan(codes, *, source_root=PINNED):
    if (not isinstance(codes,list) or not 1<=len(codes)<=3 or len(set(codes))!=len(codes)
            or any(c not in ALLOWED_CODES for c in codes)):
        raise ValueError('EXPLICIT_1_TO_3_UNIQUE_ALREADY_USED_CODES_REQUIRED')
    raws, _ = _sources(source_root)
    window = _window(raws, source_root)
    required = sorted(set(window['prior60']+[SIGNAL]))
    if len(window['prior60'])!=60 or len(required)!=61 or required[0]!='20260720':
        raise ValueError('PINNED_WINDOW_MISMATCH')
    return dict(schema_version='v5.m14_futu_history_canary_plan.v1', codes=list(codes),
        start=START, end=END, signal_date=SIGNAL, target_date=TARGET,
        calendar=window, calendar_invocation='repair._history_window(signal_date)',
        required_sessions=required, endpoint=f'{HOST}:{PORT}',
        requests=[symbolic_request(c) for c in codes], pinned_sources=dict(PINS),
        max_connections=1, max_history_calls=len(codes), quota_calls_max=2,
        min_interval_seconds=MIN_INTERVAL, hard_limit_seconds=MAX_SECONDS,
        auto_retry=False, auto_pagination=False, subscribe=False, full_pool_authorized=False,
        original_connection=dict(repository='lexi2016/v4',commit='74478a0e62be215c8527ccc9a14b89b51042d014',
            path='handoff/v4-running-source-20261005/canonical/infrastructure/futu_quote_provider.py',
            function='_default_context', sha256=PINS['futu_quote_provider.py']),
        original_five_script=dict(path='/Users/lexi/Documents/Codex/2026-10-09/task/rebound-owner-ebe5944e/evidence/capture_five_once.py',
            sha256='e5006ec6f1f7e4b327d67e51005123a9ad58caff596854e7d501d413292cc05a',
            body_available=False, reuse='DOCUMENTED_PARAMETER_CONTRACT_NEW_BOUNDED_WRAPPER'),
        **CONTRACT)


def encode_native(value):
    """Whole SDK-decoded return, not TCP/protobuf wire bytes; no float rounding."""
    if all(hasattr(value,n) for n in ('columns','dtypes','itertuples','index')):
        return {'__type__':'DataFrame', 'columns':[encode_native(x) for x in value.columns],
            'dtypes':[str(x) for x in value.dtypes], 'index':[encode_native(x) for x in value.index],
            'rows':[[encode_native(x) for x in row] for row in value.itertuples(index=False,name=None)]}
    if value is None or type(value) in (bool,int,str): return value
    if isinstance(value,float):
        if math.isfinite(value): return float(value)
        return {'__type__':'float','value':'NaN' if math.isnan(value) else ('Infinity' if value>0 else '-Infinity'),
                'ieee754_hex':struct.pack('!d',value).hex()}
    if isinstance(value,bytes): return {'__type__':'bytes','hex':value.hex()}
    if isinstance(value,tuple): return {'__type__':'tuple','items':[encode_native(x) for x in value]}
    if isinstance(value,list): return [encode_native(x) for x in value]
    if isinstance(value,dict):
        if any(not isinstance(k,str) for k in value):
            return {'__type__':'mapping','items':[[encode_native(k),encode_native(v)] for k,v in value.items()]}
        return {k:encode_native(v) for k,v in value.items()}
    if isinstance(value,(datetime,date,Decimal)):
        return {'__type__':type(value).__name__,'value':str(value)}
    if type(value).__name__ in ('NAType','NaTType'):
        return {'__type__':type(value).__name__,'value':str(value)}
    if type(value).__module__.startswith('numpy') and hasattr(value,'item'):
        return encode_native(value.item())
    raise ValueError('UNSUPPORTED_NATIVE_CELL_TYPE:'+type(value).__module__+'.'+type(value).__name__)


def quota_evidence(response, codes):
    result = dict(valid=False, used=None, remaining=None, detail_count=None, occupied_codes=[], missing_codes=list(codes), anomalies=[])
    if not isinstance(response,tuple) or len(response)!=2 or response[0]!=0:
        result['reason']='QUOTA_RET_OR_RESPONSE_SHAPE'; return result
    data=response[1]
    if not isinstance(data,tuple) or len(data)!=3:
        result['reason']='QUOTA_DATA_MUST_BE_TUPLE'; return result
    used,remaining,details=data
    if type(used) is not int or type(remaining) is not int or min(used,remaining)<0 or not isinstance(details,list):
        result['reason']='QUOTA_COUNTS_OR_DETAIL_SHAPE'; return result
    present = [x.get('code') for x in details if isinstance(x,dict) and isinstance(x.get('code'),str)]
    result.update(used=used,remaining=remaining,detail_count=len(details),occupied_codes=sorted(set(present)),
                  missing_codes=[c for c in codes if c not in present])
    if len(details)!=used: result['anomalies'].append('DETAIL_COUNT_DIFFERS_FROM_USED')
    if len(present)!=len(set(present)): result['anomalies'].append('DUPLICATE_DETAIL_CODES')
    if len(present)!=len(details): result['anomalies'].append('MALFORMED_DETAIL_ENTRIES')
    result['valid']=not result['missing_codes']
    result['reason']='ALL_REQUESTED_CODES_ALREADY_OCCUPIED' if result['valid'] else 'REQUESTED_CODES_NOT_IN_CURRENT_DETAIL'
    return result


def diagnostics(code, frame, plan):
    if not isinstance(frame,dict) or frame.get('__type__')!='DataFrame': raise ValueError('HISTORY_NOT_DATAFRAME')
    columns,rows=frame['columns'],frame['rows']
    if len(rows)>100 or len(columns)!=len(set(columns)): raise ValueError('HISTORY_SHAPE_BOUND')
    required=('code','time_key','open','high','low','close','volume')
    if not all(k in columns for k in required): raise ValueError('HISTORY_REQUIRED_COLUMNS')
    indexes={k:columns.index(k) for k in required}
    seen,duplicates,invalid_dates,invalid_ohlc,invalid_volume,zero,future,wrong_code=[],[],[],[],[],[],[],[]
    comparison_day={'HK.00376':'20260831','HK.01191':'20260724'}.get(code)
    comparison=[]
    number=lambda x: type(x) in (int,float) and math.isfinite(x)
    for i,row in enumerate(rows):
        if len(row)!=len(columns): raise ValueError('HISTORY_ROW_WIDTH')
        if row[indexes['code']]!=code: wrong_code.append(i)
        try:
            label=row[indexes['time_key']]
            day=datetime.strptime(label, '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d')
            if day in seen: duplicates.append(day)
            seen.append(day)
            if day>SIGNAL: future.append(i)
        except (ValueError,TypeError): invalid_dates.append(i); day=None
        o,h,l,c=[row[indexes[k]] for k in ('open','high','low','close')]
        if (not all(number(v) and v>0 for v in (o,h,l,c))
                or h<max(o,l,c) or l>min(o,h,c)): invalid_ohlc.append(i)
        v=row[indexes['volume']]
        if not number(v) or v<0: invalid_volume.append(i)
        elif v==0: zero.append(i)
        if day==comparison_day:
            comparison.append(dict(row_index=i,date=day,open=o,high=h,low=l,close=c))
    return dict(returned_rows=len(rows), missing_sessions=sorted(set(plan['required_sessions'])-set(seen)),
        duplicate_dates=sorted(set(duplicates)), invalid_date_rows=invalid_dates,
        invalid_ohlc_rows=invalid_ohlc, invalid_volume_rows=invalid_volume,zero_volume_rows=zero,
        wrong_code_rows=wrong_code,future_rows=future,
        outside_required_sessions=sorted(set(seen)-set(plan['required_sessions'])),
        presence_20260925='20260925' in seen, raw_values_modified=False,
        ohlc_comparison=dict(date=comparison_day,futu_rows=comparison,
            original_comparison='ORIGINAL_VALUES_NOT_PROVIDED; ORIGINAL_DECODER_OHLC_INVALID_OPEN_GT_HIGH' if comparison_day else 'NOT_REQUESTED'),
        validator='FINITE_STRICT_POSITIVE_OHLC_FULL_ENVELOPE; FINITE_VOLUME_GE_ZERO',
        owner_admission=False)


def _stamp(clock):
    now=clock()
    if now.tzinfo is None or now.utcoffset() is None: raise ValueError('NAIVE_CLOCK')
    return now.astimezone(timezone.utc).isoformat(timespec='microseconds')


def _live_connector(raws, io):
    # Only the explicit capture worker reaches this import. No SDK configuration is read here.
    import futu
    source=inspect.getsourcefile(futu.OpenQuoteContext)
    if not source: raise ValueError('OPEN_QUOTE_CONTEXT_SOURCE_UNAVAILABLE')
    source_raw=io._read(source,8*1024**2)
    identity=dict(sdk_version=str(getattr(futu,'__version__','UNKNOWN')),
        open_quote_context_source_file=str(source),open_quote_context_source_sha256=io._sha(source_raw),synthetic=False)
    def request(code):
        return dict(code=code,start=START,end=END,ktype=futu.KLType.K_DAY,autype=futu.AuType.NONE,
            fields=[futu.KL_FIELD.ALL],max_count=100,page_req_key=None,extended_time=False,session=futu.Session.NONE)
    # Validate all required SDK constants before creating the sole quote context.
    request(ALLOWED_CODES[0])
    scope=dict(Any=Any)
    _extract(raws['futu_quote_provider.py'],['_default_context'],scope,'<pinned-original-futu-context>')
    return scope['_default_context'](),identity,request


def _capture(plan, directory, *, io, connector, clock, monotonic, sleep):
    started=_stamp(clock); began=monotonic(); last=None; api=None; records=[]; refs=[]
    pre=post=None; failure=None; connected=False; sdk={}; connection_started=None
    plan_hash=io._sha(io._canonical(plan))
    io._write_once(directory,'plan.json',plan)
    io._write_once(directory,'capture-attempt.json',dict(started_at=started,plan_sha256=plan_hash,**SAFETY))
    def pace():
        nonlocal last
        if last is not None: sleep(max(0,MIN_INTERVAL-(monotonic()-last)))
        if monotonic()-began>=MAX_SECONDS: raise TimeoutError('CANARY_DEADLINE')
        last=monotonic()
    def query(name, request, call):
        pace()
        rec=dict(request=request,request_sha256=io._sha(io._canonical(request)),
            started_at=_stamp(clock),acquired_at=None,finished_at=None,response=None,response_sha256=None,
            status='FAILED',sdk=sdk,plan_sha256=plan_hash,**CONTRACT)
        refs.append(io._write_once(directory,'attempt-'+name+'.json',dict(request=request,
            request_sha256=rec['request_sha256'],started_at=rec['started_at'],plan_sha256=plan_hash,**SAFETY)))
        response=None; error=None
        try:
            response=call(); rec['acquired_at']=_stamp(clock)
            rec['response']=encode_native(response)
            encoded=io._canonical(rec['response'])
            if len(encoded)>8*1024**2: raise ValueError('RESPONSE_BYTES_BOUND')
            rec['response_sha256']=io._sha(encoded); rec['status']='RESPONSE_CAPTURED'
        except Exception as exc:
            error=exc; rec.update(error_type=type(exc).__name__,error_message=str(exc)[:500])
        rec['finished_at']=_stamp(clock)
        return rec,response,error
    def get_quota(label):
        rec,response,error=query('quota-'+label,dict(method='get_history_kl_quota',get_detail=True),
                                 lambda:api.get_history_kl_quota(get_detail=True))
        evidence=quota_evidence(response,plan['codes']) if error is None else dict(valid=False,reason='QUOTA_EXCEPTION')
        rec['quota']=evidence
        refs.append(io._write_once(directory,'quota-'+label+'.json',rec))
        return evidence,error
    try:
        connection_started=_stamp(clock)
        api,sdk,request_builder=connector(); connected=True
        io._write_once(directory,'connection.json',dict(started_at=connection_started,acquired_at=_stamp(clock),
            endpoint=plan['endpoint'],sdk=sdk,original_connection=plan['original_connection'],**SAFETY))
        pre,error=get_quota('before')
        if error: raise error
        if not pre['valid']: failure='PREFLIGHT_REJECTED'
        else:
            for code in plan['codes']:
                actual=request_builder(code)
                # All live request parameters are explicit; record both symbolic contract and actual SDK values.
                request=dict(method='request_history_kline',parameters=symbolic_request(code),sdk_parameters=encode_native(actual))
                rec,response,error=query(code,request,lambda actual=actual:api.request_history_kline(**actual))
                if error is None:
                    try:
                        if not isinstance(response,tuple) or len(response)!=3 or response[0]!=0: raise ValueError('HISTORY_RET_OR_SHAPE')
                        rec['diagnostics']=diagnostics(code,rec['response']['items'][1],plan)
                        key=response[2]
                        rec['status']='PARTIAL' if key not in (None,b'','') else 'CAPTURED'
                    except Exception as exc:
                        error=exc; rec.update(status='RESPONSE_INVALID',error_type=type(exc).__name__,error_message=str(exc)[:500])
                rec.update(code=code,finished_at=_stamp(clock))
                refs.append(io._write_once(directory,'response-'+code+'.json',rec)); records.append(rec)
                if error is not None: failure='FAILED'; break
    except Exception as exc:
        failure='FAILED'; refs.append(io._write_once(directory,'failure.json',dict(error_type=type(exc).__name__,
            error_message=str(exc)[:500],finished_at=_stamp(clock),**SAFETY)))
    finally:
        if api is not None:
            # This bounded read is the sole permitted cleanup query, even after a history error.
            try: post,_=get_quota('after')
            except Exception as exc: post=dict(valid=False,reason=type(exc).__name__)
            try: api.close()
            except Exception as exc:
                failure='FAILED'; refs.append(io._write_once(directory,'close-error.json',dict(error_type=type(exc).__name__,**SAFETY)))
    change=dict(before_used=(pre or {}).get('used'),after_used=(post or {}).get('used'),
        before_remaining=(pre or {}).get('remaining'),after_remaining=(post or {}).get('remaining'),
        used_delta=None,remaining_delta=None,cause_attributed=False)
    if all(type(change[k]) is int for k in ('before_used','after_used','before_remaining','after_remaining')):
        change.update(used_delta=change['after_used']-change['before_used'],remaining_delta=change['after_remaining']-change['before_remaining'])
    complete=len(records)==len(plan['codes']) and all(r['status']=='CAPTURED' for r in records)
    status=failure or ('CAPTURED' if complete else 'PARTIAL')
    if not post or not post.get('valid'): status=failure or 'PARTIAL'
    result=dict(schema_version='v5.m14_futu_history_canary_summary.v1',status=status,
        started_at=started,finished_at=_stamp(clock),plan_sha256=plan_hash,connected=connected,
        history_calls=len(records),requested_codes=plan['codes'],sdk=sdk,quota_before=pre,quota_after=post,
        quota_change=change,receipts=refs,code_results=[dict(code=r['code'],status=r['status'],diagnostics=r.get('diagnostics')) for r in records],
        full_pool_authorized=False,repair_ready=False,**CONTRACT)
    io._write_once(directory,'summary.json',result)
    return result


def capture_plan(plan, *, output_dir, connector, source_root=PINNED, clock=None, monotonic=time.monotonic, sleep=time.sleep):
    """Explicit injected connector, primarily for offline synthetic receipts."""
    _,io=_sources(source_root)
    if io._canonical(plan)!=io._canonical(prepare_plan(plan['codes'],source_root=source_root)): raise ValueError('PLAN_MISMATCH')
    directory=io._new_output(output_dir)
    try:
        return _capture(plan,directory,io=io,connector=connector,clock=clock or (lambda:datetime.now(timezone.utc)),monotonic=monotonic,sleep=sleep)
    finally: os.close(directory)


def _worker(plan, output_dir, identity, source_root):
    raws,io=_sources(source_root)
    directory=io._open_directory(output_dir)
    try:
        st=os.fstat(directory)
        if (st.st_dev,st.st_ino)!=identity: raise ValueError('OUTPUT_DIRECTORY_IDENTITY')
        _capture(plan,directory,io=io,connector=lambda:_live_connector(raws,io),
            clock=lambda:datetime.now(timezone.utc),monotonic=time.monotonic,sleep=time.sleep)
    finally: os.close(directory)


def _supervise(process, seconds, monotonic=time.monotonic):
    began=monotonic(); process.start()
    process.join(timeout=max(0,seconds-(monotonic()-began)))
    killed=process.is_alive()
    if killed:
        process.kill()  # No grace interval that extends the acquisition allowance.
        process.join()
    return dict(hard_timeout=killed,worker_exitcode=process.exitcode,elapsed_seconds=monotonic()-began)


def capture_cli(plan, output_dir, source_root=PINNED):
    _,io=_sources(source_root)
    directory=io._new_output(output_dir)
    try:
        st=os.fstat(directory)
        started=datetime.now(timezone.utc).isoformat(timespec='microseconds')
        io._write_once(directory,'supervisor-attempt.json',dict(started_at=started,hard_limit_seconds=MAX_SECONDS,**SAFETY))
        process=multiprocessing.get_context('spawn').Process(target=_worker,args=(plan,str(output_dir),(st.st_dev,st.st_ino),str(source_root)))
        result=_supervise(process,MAX_SECONDS)
        result.update(started_at=started,finished_at=datetime.now(timezone.utc).isoformat(timespec='microseconds'),**SAFETY)
        io._write_once(directory,'supervisor.json',result)
        try: summary=io._json(io._read(Path(output_dir)/'summary.json',8*1024**2))
        except FileNotFoundError:
            summary=dict(status='HARD_TIMEOUT' if result['hard_timeout'] else 'WORKER_FAILED',
                started_at=started,finished_at=result['finished_at'],quota_after=None,
                quota_change='UNAVAILABLE_DO_NOT_INFER',partial_receipts_retained=True,
                full_pool_authorized=False,repair_ready=False,**CONTRACT)
            io._write_once(directory,'summary.json',summary)
        # Supervisor status is authoritative if SDK shutdown exceeded the cap.
        return dict(summary=summary,supervisor=result)
    finally: os.close(directory)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('args','capture'))
    parser.add_argument('--codes',nargs='+',required=True,choices=ALLOWED_CODES)
    parser.add_argument('--source-root',default=str(PINNED))
    parser.add_argument('--output-dir')
    args=parser.parse_args(argv)
    plan=prepare_plan(args.codes,source_root=args.source_root)
    if args.action=='args':
        if args.output_dir: parser.error('args is read-only; omit --output-dir')
        print(json.dumps(plan,ensure_ascii=False,sort_keys=True,allow_nan=False)); return 0
    if not args.output_dir: parser.error('capture requires a previously absent --output-dir leaf')
    outcome=capture_cli(plan,args.output_dir,args.source_root)
    print(json.dumps(outcome,ensure_ascii=False,sort_keys=True,allow_nan=False))
    return 0 if outcome['summary']['status']=='CAPTURED' and not outcome['supervisor']['hard_timeout'] else 2

if __name__=='__main__':
    try: raise SystemExit(main())
    except (ValueError,OSError) as error:
        print(type(error).__name__+': '+str(error),file=sys.stderr); raise SystemExit(2)
