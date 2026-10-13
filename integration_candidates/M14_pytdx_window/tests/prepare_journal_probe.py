"""Synthetic batch journal -> real preparation logic, fake Parquet I/O only."""
import copy
from datetime import datetime,timedelta,timezone
import importlib.util
import json
import os
from pathlib import Path
import sys
import types
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
BASE=Path(os.environ['M14_WINDOW_RUNTIME'])
BATCH=Path(os.environ['M14_BATCH_MODULE'])
HELPER=Path(os.environ['M14_CAPTURE_HELPER'])
sys.path.insert(0,str(BASE/'src'));import v5_shadow
sys.path.insert(0,str(ROOT/'tests'))
from test_private_window_binding import PrivateWindowBindingTests
from test_rebound_pytdx_window import canonical,sha
PrivateWindowBindingTests.setUpClass();fixture=PrivateWindowBindingTests();fixture.setUp()
# Preserve fixtures until process exit; TemporaryDirectory's cleanup is outside
# the preparation guard's scope and the disposable test process owns the files.
r=fixture.root
spec=importlib.util.spec_from_file_location('batch_probe',BATCH);batch=importlib.util.module_from_spec(spec);spec.loader.exec_module(batch)
h=batch._helper(HELPER)
now=datetime.now(timezone.utc)
signal='20261013';target='20261014';members=['HK.00001','HK.00002','HK.02825','HK.03469']
paths={k:fixture.paths[k] for k in ('master_manifest','master_artifact','master_receipt')}
paths.update(panel=fixture.paths['window_parent_panel'],panel_manifest=fixture.paths['window_parent_manifest'])
files={p:fixture.files[p] for p in paths.values()}
original_request=dict(schema_version='v5.rebound_owner_request.v1',target_date=target,signal_date=signal,research_cutoff='2026-10-13T10:00:00+00:00',data_kind='SYNTHETIC',input_root=str(r/'deliberately-missing-original-root'),paths=paths,files=files)
def write(name,value):
    p=r/name;p.write_bytes(canonical(value));return str(p),sha(p.read_bytes())
art=dict(schema_version='v5.rebound_owner.v1',run_id='0'*32,request=original_request,request_sha256=sha(canonical(original_request)),research_observation=dict(strict=[],near=[],pending=[dict(code=c) for c in members],excluded=[],screen_unresolved=[]))
ap,ash=write('original-artifact.json',art)
man=dict(schema_version='v5.rebound_owner_manifest.v1',run_id='0'*32,target_date=target,artifact_sha256=ash,request_sha256=art['request_sha256'])
mp,msh=write('original-manifest.json',man)
rp,rsh=write('original-receipt.json',dict(schema_version='v5.rebound_owner_receipt.v1',run_id='0'*32,status='COMMITTED',artifact_sha256=ash,manifest_sha256=msh))
pp,psh=write('parent-pointer.json',dict(manifest_relative=paths['panel_manifest'].removeprefix('assets/hk_0_2/')))
reference=dict(run_id='0'*32,artifact_sha256=ash,manifest_sha256=msh,receipt_sha256=rsh)
parent=dict(parent_pointer_sha256=psh,parent_manifest_relative=paths['panel_manifest'].removeprefix('assets/hk_0_2/'),parent_manifest_sha256=files[paths['panel_manifest']],parent_panel_relative=paths['panel'].removeprefix('assets/hk_0_2/'),parent_panel_sha256=files[paths['panel']])
keys=[dict(code=c,date='20261012') for c in members]
base_task=dict(target_date=target,signal_date=signal,keys=keys,original_reference=reference,parent_binding=parent,expected_panel_sha256=files[paths['panel']])
rows=[]
for i in range(119,-1,-1):
    day=datetime(2026,10,13)-timedelta(days=i)
    rows.append(dict(datetime=day.strftime('%Y-%m-%d 15:00'),open=8,high=10,low=7,close=8,trade=150 if i==0 else 100,amount=700))
class API:
    def __init__(self,fail=False):self.fail=fail
    def get_instrument_bars(self,*args):
        if self.fail:raise ConnectionError('synthetic query failure')
        return copy.deepcopy(rows)
    def disconnect(self):pass
reuse=[]
for code in sorted(batch.REUSE_CODES):
    task=dict(base_task,schema_version=h.TASK_SCHEMA,canary_codes=[code],keys=[k for k in keys if k['code']==code])
    plan=h.prepare_plan(task,baseline_root=BASE);out=r/('canary-'+code)
    result=h.capture_plan(plan,baseline_root=BASE,output_dir=out,connector=lambda:(API(),h.ENDPOINT),clock=lambda:now)
    rr=result['sources'][0]
    reuse.append(dict(code=code,receipt_path=str(out/rr['relative']),receipt_sha256=rr['sha256'],plan_path=str(out/'plan.json'),plan_sha256=sha((out/'plan.json').read_bytes())))
task=dict(base_task,schema_version=batch.TASK_SCHEMA,prepared_at=(now-timedelta(seconds=10)).isoformat(),valid_until=(now+timedelta(hours=1)).isoformat(),exact_member_codes=members,exact_member_codes_sha256=sha(canonical(members)),keys_sha256=sha(canonical(keys)),initial_reuse=reuse)
ctx=dict(schema_version=batch.CONTEXT_SCHEMA,target_date=target,signal_date=signal,original_reference=reference,parent_binding=parent,exact_member_codes=members,keys=keys,files=dict(original_artifact=ap,original_manifest=mp,original_receipt=rp,parent_pointer=pp,parent_manifest=str(r/paths['panel_manifest']),parent_panel=str(r/paths['panel'])))
cp,_=write('context.json',ctx)
plan=batch.prepare_plan(task,baseline_root=BASE,capture_helper=HELPER,context_file=cp,clock=lambda:now)
planp,plansha=write('batch-plan.json',plan)
journal=r/'journal'
result=batch.capture_plan(plan,baseline_root=BASE,capture_helper=HELPER,context_file=cp,output_dir=journal,connector=lambda:(API(True),h.ENDPOINT),clock=lambda:now,max_calls=1,max_seconds=10)
assert result['status']=='FINISHED_WITH_ERRORS',result
import pandas as pd
parent_frame=pd.DataFrame([dict(trade_date_compact=signal,code_norm=c) for c in members])
new_frame=None
# Use actual pandas frames but no fabricated claim that Parquet worked.
def read_parquet(path,columns):
    return (parent_frame if Path(path).name=='hkconnect_vipdoc_daily_panel.parquet' else new_frame)[list(columns)].copy()
def to_parquet(self,handle,index=False):
    global new_frame
    new_frame=self.copy();handle.write(b'SYNTHETIC_PARQUET_IO_SEAM_NOT_REAL_PARQUET')
pyarrow=types.ModuleType('pyarrow');pyarrow.__path__=[];parquet=types.ModuleType('pyarrow.parquet')
spec=importlib.util.spec_from_file_location('prepare_probe',ROOT/'preparation/prepare_pytdx_window.py');prep=importlib.util.module_from_spec(spec);spec.loader.exec_module(prep)
output=ROOT/('prep-probe-'+str(os.getpid()))
args=types.SimpleNamespace(baseline_root=str(BASE),batch_helper=str(BATCH),capture_helper=str(HELPER),plan=planp,plan_sha256=plansha,context_file=cp,capture_dir=str(journal),output_dir=str(output),original_input_root=str(r))
with patch.dict(sys.modules,{'pyarrow':pyarrow,'pyarrow.parquet':parquet}),patch.object(pd,'read_parquet',side_effect=read_parquet),patch.object(pd.DataFrame,'to_parquet',to_parquet):
    prepared=prep.prepare(args)
request=json.loads((output/'owner-request.json').read_bytes())
manifest=json.loads((Path(request['input_root'])/request['paths']['panel_manifest']).read_bytes())
assert prepared['owner_execution']=='NOT_RUN'
assert prepared['member_count']==4 and prepared['pending_member_count']==1,prepared
assert prepared['private_files_with_routing']==10,prepared
assert manifest['capture_audit']['failed_codes']==['HK.00002']
assert len(manifest['capture_audit']['receipts'])==4
assert request['input_root']==str(output/'input')
assert manifest['manifest_prepared_at']>=manifest['capture_audit']['audited_at']
from v5_shadow import rebound_owner as owner
assert owner._request(request)==request
assert owner._metadata(Path(request['input_root']),request)[0]==manifest
print(json.dumps(dict(status='PREPARE_SYNTHETIC_JOURNAL_PASS',members=4,pending=1,files=10,parquet='SYNTHETIC_IO_SEAM',owner='NOT_RUN')))
