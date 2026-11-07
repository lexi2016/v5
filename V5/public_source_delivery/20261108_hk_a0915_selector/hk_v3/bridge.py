"""Pinned original M10 cold-read bridge, NOT HK collector or production activation."""
import datetime as dt
import hashlib
import json
from pathlib import Path
import runpy
import tempfile

HERE=Path(__file__).resolve().parent
SOURCE=HERE.parent/'hk_close_source_recovery_20261107/hk_close_daily.py.reference'
SOURCE_SHA='60e6c0b2561c732ea0eb7c7fc694fe9981833d5bc879760bacbfe84d22295027'
NODES={'hk-continuous-close','hk-auction-final'}
TRUSTED_RUNS={} # no guessed paths, runtime source authority or calendar bindings

def original():
    if SOURCE.is_symlink() or any(p.is_symlink() for p in SOURCE.parents):
        raise ValueError('CODE_SYMLINK')
    if hashlib.sha256(SOURCE.read_bytes()).hexdigest()!=SOURCE_SHA:
        raise ValueError('ORIGINAL_CODE_CHANGED')
    return runpy.run_path(str(SOURCE),run_name='original_m10_cold_reader')

def blocked(node,reason):
    return dict(node_id=node,status='BLOCKED',reason=reason,production_allowed=False,
                natural_verified=False,business_verified=False,orders_sent=False)

def inspect_recorded(node, *, root, run_id, target_date, pins, gate):
    """Local recorded input only. Pins bind five committed M10 files, never admit sources.
    Snapshot reads are bounded and isolated before invoking unmodified original reader.
    Caller supplies existing task lock/resource guard; omitted guard cannot proceed.
    """
    if node not in NODES: raise ValueError('NODE_NOT_SUPPORTED')
    dt.datetime.strptime(target_date,'%Y%m%d')
    if not callable(gate): raise ValueError('ORIGINAL_RESOURCE_AND_LOCK_GATE_REQUIRED')
    gate()
    m=original();m['_run_path'](root,run_id) # original path/run validation
    names=['latest_success.json']+[run_id+'/'+n+'.json' for n in ['payload','publication','manifest','receipt']]
    if set(pins)!=set(names):raise ValueError('EXACT_COMMITTED_FILE_PINS_REQUIRED')
    total=0
    with tempfile.TemporaryDirectory(prefix='hk-m10-read-') as temp:
        for name in names:
            gate()
            path=m['_path'](root,name)
            with path.open('rb') as f:raw=f.read(8*1024*1024+1)
            total+=len(raw)
            if len(raw)>8*1024*1024 or total>16*1024*1024:raise ValueError('READ_BUDGET_EXCEEDED')
            if hashlib.sha256(raw).hexdigest()!=pins[name]:raise ValueError('INPUT_PIN_CHANGED')
            dst=Path(temp,name);dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(raw)
        payload=m['read_hk_close_projection'](temp,run_id)
        if payload.get('schema')!=m['DAILY_SCHEMA']:raise ValueError('DAILY_ENVELOPE_REQUIRED')
        if payload['identity']['trade_date']!=target_date:raise ValueError('TRADE_DATE_MISMATCH')
        gate()
    result=blocked(node,'ORIGINAL_OWNER_CALENDAR_SOURCE_AND_STAGE_AUTHORITY_NOT_BOUND')
    result.update(read_status='ORIGINAL_M10_COMMITTED_PROJECTION_READ',target_date=target_date,
                  run_id=run_id,input_pins=dict(pins),original_code_sha256=SOURCE_SHA,
                  projection=payload,actual_cas_end=None,
                  stage_admission='UNKNOWN',collector_running=False)
    return result

def dispatch(node,run_key):
    """No caller-provided trusted contract or boolean can activate a producer."""
    if node not in NODES|{'hk-open'}:return blocked(node,'NODE_NOT_SUPPORTED')
    if run_key not in TRUSTED_RUNS:return blocked(node,'TRUSTED_RUN_NOT_REGISTERED')
    binding=TRUSTED_RUNS[run_key]
    if binding.node!=node:return blocked(node,'REGISTERED_NODE_MISMATCH')
    from capture import execute
    try:return execute(binding)
    except (ValueError,OSError,KeyError,TypeError) as error:
        return blocked(node,str(error))

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('node',choices=sorted(NODES|{'hk-open'}));p.add_argument('run_key');a=p.parse_args()
    print(json.dumps(dispatch(a.node,a.run_key),sort_keys=True));raise SystemExit(2)
