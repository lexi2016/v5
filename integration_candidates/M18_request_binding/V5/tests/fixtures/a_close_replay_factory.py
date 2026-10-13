"""SYNTHETIC ONLY: original M09 owner writes new isolated test records.

Never imported by an HTTP worker. Existing pandas suffices; no input capture.
"""
import json
from pathlib import Path
import subprocess
import sys

BASE=Path(__file__).resolve().parents[2]


def create_fixture(root,*,revision=1,origin_extra=None):
    owner=BASE/'source_owners/m09'
    code=r'''
import json,sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from v5_shadow import a_close_historical as h
from v5_shadow.a_close_daily import read_a_close_daily
from v5_shadow.a_close_daily_api import project_committed_review
base=Path(sys.argv[2]);base.mkdir(parents=True,exist_ok=True);revision=int(sys.argv[3]);source=base/('snapshot-'+str(revision));root=base/'runs'
rows=[dict(trade_date='20261009',ts_code=f'{i:06}.SZ',name=f'SYNTHETIC_{i}',pct_chg=pct,
 amount=100000000.0,bar_close_pos=.8,tdx_industry_code='I1' if i<4 else 'I2',
 tdx_industry_name='SYNTHETIC_INDUSTRY_A' if i<4 else 'SYNTHETIC_INDUSTRY_B')
 for i,pct in enumerate([10.,2.,-10.,-1.,0.,3.],1)]
rows[0]['name']='';rows[1]['tdx_industry_code']=None;rows[1]['tdx_industry_name']='';rows[2]['bar_close_pos']=float('nan')
origin=dict(sha256=str(revision)*64,bytes=1,format='SYNTHETIC_FIXTURE_ONLY',hash_verified=True);origin.update(json.loads(sys.argv[4]))
h._write_snapshot(source,'20261009',rows,origin,None)
h.initialize_a_close_historical_root(root)
result=h.run_a_close_historical(root,source,'20261009',attempt_id='synthetic-'+str(revision))
if result['status']!='SUCCEEDED':raise RuntimeError(json.dumps(result))
committed=read_a_close_daily(root,'20261009',generation_sha256=result['generation_sha256'])
preview=project_committed_review(committed,'20261009')
print(json.dumps(dict(binding=dict(run_root=str(root),trade_date='20261009',run_id=result['run_id'],generation=result['generation_sha256'],python_executable=sys.executable),review=committed['review'],publication=preview['m09_publication'],identity=committed['identity']),ensure_ascii=False,allow_nan=False))
'''
    proc=subprocess.run([sys.executable,'-I','-B','-c',code,str(owner/'V5/src'),str(root),str(revision),json.dumps(origin_extra or {})],capture_output=True,text=True,timeout=60)
    if proc.returncode:raise AssertionError('M09_SYNTHETIC_FIXTURE_FAILED: '+proc.stderr[-3000:])
    value=json.loads(proc.stdout);return value['binding'],value
