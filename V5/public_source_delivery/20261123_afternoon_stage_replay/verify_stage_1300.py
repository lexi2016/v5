"""Offline test of the existing A-side admission at the afternoon time boundary."""
import copy, hashlib, json, pathlib, sys, tempfile

def pin(path, sha):
    b=path.read_bytes()
    if hashlib.sha256(b).hexdigest()!=sha: raise ValueError('INPUT_PIN:'+path.name)
    return b

def forbid(event, args):
    if event.startswith('socket.') or event in ('os.system','os.exec','os.posix_spawn'):
        raise RuntimeError('OFFLINE:'+event)

root=pathlib.Path(__file__).resolve().parents[1]
m=root/'m07_exact_0925_0930_20261120/V5/source_owners/m07'
closure_sha='dc63874f8d9e8307ee30a50d398d3c31d3fbac0d124702786b240d7059c6c301'
closure=json.loads(pin(m/'OWNER_CLOSURE.json',closure_sha))
for record in closure['entries']:
    p=m/'owner'/record['path']
    if len(pin(p,record['sha256']))!=record['bytes']: raise ValueError('INPUT_BYTES')
admit_sha='01c791dee6547e5e1a54ef3c412ac3102dfcafdf7e78be34c702b053f6fb5791'
fixture_sha='692ece6190c4dd721ca375abb37d370cde60f8b26f9376f3289fed0fb6a32408'
pin(m/'V5/src/v5_shadow/a_stage_daily.py',admit_sha)
pin(m/'V5/tests/m07_fixture.py',fixture_sha)
sys.path[:0]=[str(m/p) for p in ('V5/src','owner','V5/tests')]
sys.addaudithook(forbid)
from stage_center.contracts import STAGE_BY_ID
from v5_shadow.a_stage_daily import _admit
from m07_fixture import make_case

stage='STAGE_1300_1315'; spec=STAGE_BY_ID[stage]
if (spec.window,spec.cutoff,spec.markets)!=('13:00-13:15','13:15:00',('A_SHARE','HK_CONNECT')):
    raise ValueError('STAGE_CONTRACT')
with tempfile.TemporaryDirectory(prefix='m07-stage-1300-only-') as td:
    t=pathlib.Path(td); req=make_case(t,count=3,stage=stage)
    roots={k:t/k for k in ('pool','live','research','morning')}
    before={p.relative_to(t):p.read_bytes() for p in t.rglob('*') if p.is_file()}
    _,pool,raw,quotes=_admit(req,roots)
    if len(pool.codes)!=3 or len(quotes)!=3 or raw['receipt_sha256']!=req['recording']['receipt_sha256']:
        raise ValueError('POSITIVE_QC')
    cases=[
        ('missed_cutoff',{'acquired_at':'2026-10-12T13:15:01+08:00'}, {},'M07_RECORDING_OUTSIDE_WINDOW_OR_FUTURE'),
        ('lunch_not_stage',{'captured_at':'2026-10-12T12:59:59+08:00'}, {},'M07_RECORDING_OUTSIDE_WINDOW_OR_FUTURE'),
        ('no_auction_slack',{}, {'cutoff':'2026-10-12T13:15:05+08:00'}, 'M07_ORIGINAL_CUTOFF_MISMATCH'),
        ('wrong_raw_receipt',{'receipt_sha256':'0'*64},{},'M07_RAW_RECEIPT_BINDING'),
    ]
    rejected=[]
    for name,record,header,expected in cases:
        edit=copy.deepcopy(req);edit['recording'].update(record);edit.update(header)
        try: _admit(edit,roots)
        except ValueError as e:
            if str(e)!=expected: raise ValueError(name+':'+str(e))
            rejected.append(dict(case=name,reason=expected))
        else: raise ValueError(name+':NOT_REJECTED')
    after={p.relative_to(t):p.read_bytes() for p in t.rglob('*') if p.is_file()}
    lock=pathlib.Path('pool/.import.lock.mutex')
    if lock not in before:
        if after.pop(lock,None)!=b'': raise ValueError('UNEXPECTED_TEST_LOCK_CHANGE')
    if before!=after: raise ValueError('FIXTURE_ARTIFACT_MODIFIED')
print(json.dumps(dict(schema='V5_M07_1300_SYNTHETIC_V1',stage=stage,window_bjt=spec.window,cutoff_bjt=spec.cutoff,
    fixture_business_date='20261012', a_side_quotes=3,excluded_lane='HK_EXECUTION_NOT_TESTED',
    rejected=rejected,owner_closure_sha256=closure_sha,admit_sha256=admit_sha,
    fixture_sha256=fixture_sha,market_requests=0,business_start=False,formal=False),ensure_ascii=False,indent=2))
