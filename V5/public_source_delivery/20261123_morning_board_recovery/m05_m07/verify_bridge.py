"""Exact M05 writer → restored M07 strict pool reader, synthetic only."""
import hashlib,json,os,subprocess,sys
from pathlib import Path
H=Path(__file__).resolve().parent
R=H.parent
M05=R/'m05_original_source_lookup_20261123'
M07=R/'m07_exact_0925_0930_20261120/V5/source_owners/m07'
RELEASE=M05/'V5/releases/m05/20261013.1-50adce44/release.json'
RELEASE_SHA='f77c0ead2053a15cbd089c02cce2cf0c7bea59ac2fb0e86ad2cc032c9d87adbb'
DATA_DAY='20261008'
def sha(x):return hashlib.sha256(x).hexdigest()
def need(value,label):
    if not value:raise ValueError(label)
def inputs():
    raw=RELEASE.read_bytes();need(sha(raw)==RELEASE_SHA,'M05_RELEASE')
    m=json.loads(raw); rows=m['runtime_files']+m['verification_files']
    for ref in rows:
        p=M05/ref['path']; b=p.read_bytes()
        need(len(b)==ref['bytes'] and sha(b)==ref['sha256'],'M05_MEMBER:'+ref['path'])
    return len(m['runtime_files']),len(m['verification_files'])
CHILD=r"""
import json,sys
def protect(event,args):
 if event.startswith('socket.') or event in ('os.system','os.exec','os.posix_spawn'):
  raise RuntimeError(event)
sys.addaudithook(protect)
from infrastructure.stage_acquisition_universe_contracts import read_strict_a_preselection_snapshot
r,day=sys.argv[1:]
s=read_strict_a_preselection_snapshot(r,day)
old=read_strict_a_preselection_snapshot(r,'20261009')
print(json.dumps({'ready':s.ready,'unique_codes':len(s.codes),'pools':{
 p.pool_id:[p.artifact_raw_sha256,p.manifest_raw_sha256,p.receipt_raw_sha256,len(p.artifact['rows'])] for p in s.pools},
 'different_target_ready':old.ready,'different_target_codes':len(old.codes)}))
"""
def run():
    runtime,tests=inputs()
    sys.path[:0]=[str(M05/'V5/tests'),str(M05/'V5/src')]
    def protect(event,args):
        if event.startswith('socket.') or event in ('os.system','os.exec','os.posix_spawn'):
            raise RuntimeError(event)
    sys.addaudithook(protect)
    from test_m05_daily_boundary import M05DailyTests,make_lane,make_wechat_lane,make_baimao_lane
    t=M05DailyTests()
    try:
        t.setUp()
        request=t.request([make_lane(t.source/'fupan',count=250),make_lane(t.source/'stage7','stage7'),
          make_wechat_lane(t.source/'wechat',DATA_DAY,'20260930'),make_baimao_lane(t.source/'baimao',DATA_DAY)])
        before=t.tree(t.source),t.tree(t.control),t.tree(t.v4)
        written=t.daily(request)
        need(written['status']=='READY' and written['integration_status']=='WAIT_INTEGRATION'
          and written['row_count']==253 and not written['orders_sent'],'M05_WRITE')
        expected={p['pool_id']:[p[k+'_raw_sha256'] for k in ('artifact','manifest','receipt')]+[len(p['rows'])] for p in written['receipts']}
        files={k:sha(v) for k,v in t.tree(t.out).items()}
        env={'PATH':os.environ['PATH'],'PYTHONNOUSERSITE':'1','PYTHONDONTWRITEBYTECODE':'1',
             'LC_ALL':'C.UTF-8','PYTHONPATH':str(M07/'owner')}
        got=subprocess.run([sys.executable,'-B','-c',CHILD,str(t.out),DATA_DAY],cwd=t.root,env=env,capture_output=True,timeout=25,check=True)
        x=json.loads(got.stdout)
        need(x['ready'] and x['pools']==expected and not x['different_target_ready'] and x['different_target_codes']==0,'M07_PHYSICAL_READ')
        need(files=={k:sha(v) for k,v in t.tree(t.out).items()} and before==(t.tree(t.source),t.tree(t.control),t.tree(t.v4)),'UNEXPECTED_CHANGE')
        return dict(schema='M05_M07_EXACT_OFFLINE_HANDOFF_V1',release_sha256=RELEASE_SHA,runtime_files_verified=runtime,
          original_tests_files_verified=tests,manifest_trios_match=len(expected),written_rows=253,reader_unique_codes=x['unique_codes'],
          changed_after_read=0,other_day_denied=True,synthetic_day=DATA_DAY,full_six_lane_test='BLOCKED_EXISTING_PYARROW_MISSING',
          production=False,live_requests=0,actual_today_pool=False)
    finally:t.doCleanups()
if __name__=='__main__':print(json.dumps(run(),ensure_ascii=False,indent=2))
