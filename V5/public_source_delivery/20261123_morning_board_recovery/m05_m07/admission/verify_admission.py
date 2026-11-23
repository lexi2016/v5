"""Synthetic regression for original M05 physical read versus M07 admission."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

H = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(H))
from verify_bridge import M05, M07, RELEASE_SHA, DATA_DAY, inputs, need, sha

FIXTURE_SHA = '692ece6190c4dd721ca375abb37d370cde60f8b26f9376f3289fed0fb6a32408'
CLOSURE_SHA = 'dc63874f8d9e8307ee30a50d398d3c31d3fbac0d124702786b240d7059c6c301'
ADMIT_SHA = '01c791dee6547e5e1a54ef3c412ac3102dfcafdf7e78be34c702b053f6fb5791'
FUPAN = 'a_d1_fupan_watchlist_pool'
STAGE7 = 'a_d1_stage7_fenshi_review_pool'
BAIMAO = 'a_share_baimao_research_map'
CHILD = r"""
import json, pathlib, sys
def guard(event,args):
    if event.startswith('socket.') or event in ('os.system','os.exec','os.posix_spawn'):
        raise RuntimeError(event)
sys.addaudithook(guard)
from infrastructure.stage_acquisition_universe_contracts import read_strict_a_preselection_snapshot
from stage_center.input_contracts import KNOWN_A_STAGE_POOL_IDS
from stage_center.raw_store import RawStore
from stage_center.contracts import STAGE_BY_ID
from v5_shadow.a_stage_daily import _admit
root, live, day, dates = sys.argv[1:]
snapshot = read_strict_a_preselection_snapshot(root, day)
spec = STAGE_BY_ID['STAGE_0925']
stamp = '2026-10-08T09:25:00+08:00'
flat = '2026-10-08 09:25:00'
# The same 250-code recording is used in both fixtures. The negative case must
# fail at physical-lane admission, before reaching coverage or quote checks.
rows = [dict(batch_index=i, code=f'A.{i:06}', name='SYNTHETIC',
    update_time=flat, last_price=11, open_price=10, high_price=11, low_price=10,
    prev_close_price=10, turnover=1000000, volume=100000, bid_price=11,
    ask_price=11.01, bid_vol=100, ask_vol=100, window_start='2026-10-08 09:20:00',
    window_end=flat,bar_count=5,temporal_cutoff_safe=True) for i in range(1,251)]
real = RawStore(live).publish(trade_date=day, stage_id=spec.stage_id, market='A_SHARE',
    source_id='SYNTHETIC_A_QUOTES',source_status='READY', rows=rows, cannot_confirm=[],
    source_evidence=['SYNTHETIC_ONLY'],requested_rows=250,missing_symbols=[],
    window=spec.window,cutoff_at=spec.cutoff)
sources = {k:('20260930' if k.startswith('a_d1_') else day)
           for k in KNOWN_A_STAGE_POOL_IDS}
sources.update(json.loads(dates))
request = dict(target_date=day,stage_id=spec.stage_id,cutoff='2026-10-08T'+spec.cutoff+'+08:00',
    pool_source_dates=sources,recording=dict(captured_at=stamp,acquired_at=stamp,
        **{k:real[k] for k in ('run_id','artifact_sha256','manifest_sha256','receipt_sha256')}))
out = dict(snapshot_ready=snapshot.ready,codes=len(snapshot.codes),
    contributions=dict(snapshot.pool_contribution_counts),
    rejected={p:[r for r in rs if 'SOURCE_REJECTED:' in r]
              for p,rs in snapshot.pool_diagnostics.items()
              if any('SOURCE_REJECTED:' in r for r in rs)})
try:
    _, pool, raw, quotes = _admit(request, {'pool':pathlib.Path(root),'live':pathlib.Path(live)})
    out.update(admission='PASS',admitted_quotes=len(quotes),raw_receipt_bound=raw['receipt_sha256']==real['receipt_sha256'])
except ValueError as e:
    out.update(admission=str(e),admitted_quotes=0)
print(json.dumps(out))
"""

M07_CONTROL = r"""
import json,pathlib,sys
def guard(event,args):
    if event.startswith('socket.') or event in ('os.system','os.exec','os.posix_spawn'):
        raise RuntimeError(event)
sys.addaudithook(guard)
from m07_fixture import make_case
from v5_shadow.a_stage_daily import _admit
root=pathlib.Path(sys.argv[1])
req=make_case(root,count=3,stage='STAGE_0925')
_,pool,raw,quotes=_admit(req,{k:root/k for k in ('pool','live','research','morning')})
print(json.dumps(dict(codes=len(pool.codes),admitted_quotes=len(quotes),
    raw_receipt_bound=raw['receipt_sha256']==req['recording']['receipt_sha256'])))
"""

def run():
    inputs()
    closure = (M07/'OWNER_CLOSURE.json').read_bytes()
    need(sha(closure)==CLOSURE_SHA, 'M07_CLOSURE')
    for ref in json.loads(closure)['entries']:
        p = M07/'owner'/ref['path']
        raw = p.read_bytes()
        need(len(raw)==ref['bytes'] and sha(raw)==ref['sha256'], 'M07_MEMBER:'+ref['path'])
    need(sha((M07/'V5/src/v5_shadow/a_stage_daily.py').read_bytes())==ADMIT_SHA, 'M07_ADMIT_SHA')
    sys.path[:0] = [str(M05/'V5/tests'),str(M05/'V5/src')]
    def deny(event,args):
        if event.startswith('socket.') or event in ('os.system','os.exec','os.posix_spawn'):
            raise RuntimeError(event)
    sys.addaudithook(deny)
    from test_m05_daily_boundary import M05DailyTests,make_lane,make_wechat_lane,make_baimao_lane
    def case(contract_statuses, *, baimao=True, clear_fixture_gap=False):
        t = M05DailyTests()
        try:
            t.setUp()
            a = make_lane(t.source/'fupan', count=250)
            b = make_lane(t.source/'stage7', 'stage7')
            if contract_statuses:
                for source in (a,b):
                    p = Path(source['input_root'])/'manifest.json'
                    m = json.loads(p.read_bytes())
                    m['status'] += '_DATA_PARTIAL'
                    if clear_fixture_gap:
                        m['cannot_confirm'] = []
                    p.write_text(json.dumps(m))
                    source['files'][p.name] = hashlib.sha256(p.read_bytes()).hexdigest()
            lanes = [a,b,make_wechat_lane(t.source/'wechat',DATA_DAY,'20260930')]
            if baimao:
                lanes.append(make_baimao_lane(t.source/'baimao',DATA_DAY))
            req = t.request(lanes)
            source_before = t.tree(t.source),t.tree(t.control),t.tree(t.v4)
            written = t.daily(req)
            need(written['status']=='READY' and written['integration_status']=='WAIT_INTEGRATION'
                 and written['row_count']==252+int(baimao) and not written['orders_sent'], 'M05_WRITE')
            dates = {FUPAN:'20260930',STAGE7:'20260930','wechat_public_account_v3_preselect':'20260930',BAIMAO:DATA_DAY}
            original_out = t.tree(t.out)
            live = t.root/'synthetic_quotes'
            live.mkdir()
            env = dict(PATH=os.environ['PATH'],PYTHONNOUSERSITE='1',
                PYTHONDONTWRITEBYTECODE='1',LC_ALL='C.UTF-8',
                PYTHONPATH=os.pathsep.join([str(M07/'V5/src'),str(M07/'owner')]))
            child = subprocess.run([sys.executable,'-B','-c',CHILD,str(t.out),str(live),
                                    DATA_DAY,json.dumps(dates)], cwd=t.root,env=env,
                                   capture_output=True,text=True,timeout=25)
            need(child.returncode==0,child.stderr)
            need(source_before==(t.tree(t.source),t.tree(t.control),t.tree(t.v4))
                 and original_out==t.tree(t.out), 'SOURCE_MUTATED')
            result = json.loads(child.stdout)
            result['m05_artifact_contract'] = {p['pool_id']:{k:p['artifact'].get(k) for k in ('status','producer_id','source_role','target_date','signal_date')} for p in written['receipts']}
            need(result['snapshot_ready'], 'SNAPSHOT_NOT_READY')
            return result
        finally:
            t.doCleanups()
    negative = case(False)
    need(negative['codes']==1 and set(negative['rejected'])=={FUPAN,STAGE7,BAIMAO}
         and all(negative['contributions'].get(p,0)==0 for p in (FUPAN,STAGE7))
         and negative['admission']=='M07_M05_REJECTED_PHYSICAL_LANE','BARE_STATUS_MUST_BLOCK:'+repr(negative))
    status_only = case(True)
    need(status_only['contributions'][FUPAN]==250 and status_only['contributions'][STAGE7]==1
         and status_only['codes']==250 and status_only['admission']=='M07_M05_REJECTED_PHYSICAL_LANE'
         and 'producer identity mismatch' in str(status_only['rejected'][BAIMAO]), 'STATUS_ONLY_NOT_ENOUGH:'+repr(status_only))
    no_rejects = case(True,baimao=False,clear_fixture_gap=True)
    need(not no_rejects['rejected'] and no_rejects['codes']==250
         and no_rejects['admission']=='M07_M05_SOURCE_DATE_MISMATCH'
         and all(v['target_date'] is None and v['signal_date'] is None
                 for v in no_rejects['m05_artifact_contract'].values()), 'M05_M07_HEADER_CONTRACT:'+repr(no_rejects))
    fixture = M07/'V5/tests/m07_fixture.py'
    need(sha(fixture.read_bytes())==FIXTURE_SHA,'M07_ORIGINAL_FIXTURE')
    import tempfile
    with tempfile.TemporaryDirectory(prefix='m07-original-admission-') as tmp:
        child = subprocess.run([sys.executable,'-B','-c',M07_CONTROL,tmp], cwd=tmp,
            env=dict(PATH=os.environ['PATH'],PYTHONNOUSERSITE='1',PYTHONDONTWRITEBYTECODE='1',
            LC_ALL='C.UTF-8',PYTHONPATH=os.pathsep.join([str(M07/'V5/src'),str(M07/'owner'),str(fixture.parent)])),
            capture_output=True,text=True,timeout=25)
        need(child.returncode==0,child.stderr)
        positive = json.loads(child.stdout)
        need(positive=={'codes':3,'admitted_quotes':3,'raw_receipt_bound':True},'M07_CONTROL:'+repr(positive))
    return dict(schema='V5_M05_M07_ADMISSION_REGRESSION_V1', m05_release_sha256=RELEASE_SHA,
        m07_admission_sha256=ADMIT_SHA,m07_owner_closure_sha256=CLOSURE_SHA,synthetic_m05_date=DATA_DAY,
        original_m05=negative,status_only=status_only,clean_three_lane_m05=no_rejects,
        original_m07_fixture_control=positive,live_requests=0,natural_run=False,production=False)

if __name__=='__main__':
    print(json.dumps(run(),ensure_ascii=False,indent=2,sort_keys=True))
