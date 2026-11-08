"""Synthetic 17:00 report-to-outbox preparation. No sender or production binding.
Original terminal nodes.py owns state/approval review; this module never calls it.
A pinned report is input evidence, NOT independently verified business success.
"""
import datetime as dt
import hashlib
import json
from pathlib import Path
import types
from zoneinfo import ZoneInfo
REGISTRY = {}
PIN = '50a7fee95e2b24911ee3c205b5e402316a764e7d7d1ece2a634bb78552ac5891'
KEYS = ('task_id','node','environment_id','binding_version','authorization_ref','channel','destination','input_sha256','code_version','data_date','run_id','output_root')
def sha(raw): return hashlib.sha256(raw).hexdigest()
def canonical(doc): return json.dumps(doc,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def _outbox():
    path=Path(__file__).with_name('outbox.py');raw=path.read_bytes()
    if sha(raw)!=PIN: raise ValueError('DEPENDENCY_CHANGED')
    module=types.ModuleType('terminal_outbox');module.__file__=str(path)
    exec(compile(raw,str(path),'exec'),module.__dict__)
    return module

def assemble(raw, expected_sha, date, identity):
    if sha(raw)!=expected_sha: raise ValueError('REPORT_CHANGED')
    r=json.loads(raw)
    if r.get('schema')!='RETRY_TERMINAL_NODE_V1' or r.get('node')!='terminal-1700': raise ValueError('REPORT_TYPE')
    if r.get('target_date')!=date or not identity or r.get('identity')!=identity: raise ValueError('REPORT_IDENTITY')
    when=dt.datetime.fromisoformat(r['checked_at'])
    if when.utcoffset() is None: raise ValueError('AWARE_CLOCK_REQUIRED')
    local=when.astimezone(ZoneInfo('Asia/Shanghai'))
    if local.strftime('%Y%m%d')!=date or local.time()<dt.time(17): raise ValueError('TERMINAL_DATE_TIME_GATE')
    known={'COMPLETED_REVIEW_VERIFIED','UNKNOWN_RECONCILIATION_REQUIRED','NOT_RUN','BLOCKED'}
    status=r.get('status') if r.get('status') in known else 'UNKNOWN'
    return {'schema':'SYNTHETIC_TERMINAL_ALERT_V1','node':'1700','data_date':date,
        'report_sha256':expected_sha,'identity':identity,'reported_generation_status':status,
        'generation_independently_verified':False,'alert_required':status!='COMPLETED_REVIEW_VERIFIED',
        'reason':r.get('reason'),'browser_acceptance':'UNKNOWN','delivery_status':'UNKNOWN',
        'business_accepted':False,'natural_verified':False}

def prepare(key, raw):
    if key not in REGISTRY: raise ValueError('NO_SYNTHETIC_BINDING')
    b=REGISTRY[key]
    if b.get('domain')!='synthetic': raise ValueError('PRODUCTION_BLOCKED')
    c=b['outbox_config']
    if {k:c[k] for k in KEYS}!=b['identity'] or c['node']!='1700' or c['destination']!='SYNTHETIC_NO_RECIPIENT': raise ValueError('OUTBOX_BINDING_CHANGED')
    if c['input_sha256']!=b['report_sha256']: raise ValueError('INPUT_BINDING_CHANGED')
    alert=assemble(raw,b['report_sha256'],c['data_date'],b['report_identity'])
    outbox=_outbox();outbox.REGISTRY={'synthetic':c}
    # Deliberately only preparation. No attempt, reconcile, sender or owner execution.
    item=outbox.prepare('synthetic',canonical(alert).decode())
    return {'status':'SYNTHETIC_PREPARATION_ONLY','alert':alert,'outbox':item,
            'delivery_state':item['state'],'sent_in_this_call':False,
            'delivery_verified':False,'natural_verified':False,'business_accepted':False}
