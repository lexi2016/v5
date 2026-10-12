"""Single existing-interpreter command for bounded M08 engineering acceptance.

No install, provider access, user data, natural scheduling or deployment.
"""
import argparse
from datetime import datetime,timezone
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
import sys
import os

ROOT=Path(__file__).resolve().parents[1]
PATTERNS=('test_hk_stage_daily.py','test_hk_stage_m06_adapter.py','test_hk_stage_observed.py','test_hk_stage_api.py','test_stage_selection.py','test_module_artifacts.py','test_source_capsule.py')


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=ROOT/'tests/logs/M08_FINAL');args=p.parse_args()
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,PYTHONPATH=str(ROOT/'src'),PYTHONDONTWRITEBYTECODE='1')
    results=[]
    for pattern in PATTERNS:
        cmd=[sys.executable,'-B','-m','unittest','discover','-s','tests','-p',pattern,'-v']
        started=datetime.now(timezone.utc).isoformat()
        proc=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,text=True)
        finished=datetime.now(timezone.utc).isoformat()
        name=pattern.removesuffix('.py')
        (out/(name+'.stdout.txt')).write_text(proc.stdout)
        (out/(name+'.stderr.txt')).write_text(proc.stderr)
        results.append(dict(command='python -B -m unittest discover -s tests -p '+pattern+' -v',started_at=started,finished_at=finished,exit_code=proc.returncode,stdout=name+'.stdout.txt',stderr=name+'.stderr.txt'))
        print(pattern, 'PASS' if proc.returncode==0 else 'FAIL',flush=True)
    def version(name):
        try:return importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:return 'NOT_INSTALLED'
    runtime=dict(python=platform.python_version(),pandas=version('pandas'),pyarrow=version('pyarrow'),pytest=version('pytest'))
    def parts(value):
        try:return tuple(int(v) for v in value.split('.')[:2])
        except ValueError:return (0,0)
    supported=sys.version_info>=(3,14) and (2,3)<=parts(runtime['pandas'])<(3,0) and (21,0)<=parts(runtime['pyarrow'])<(25,0)
    record=dict(schema_version='v5.m08.engineering_test_receipt.v1',scope='SYNTHETIC_RETAINED_OWNER_CHAIN_AND_READONLY_API',results=results,runtime=runtime,
        production_runtime_accepted=supported,
        natural_verified=False,formal_admission=False,mac_verified=False,ui_deployed=False,
        not_run=['Full pytest donor runtime suite: excluded from bounded acceptance; inspect recorded pytest availability and supply full donor runtime to run separately','Live/provider SDK collection: outside retained-input scope','Mac supported-runtime acceptance and existing UI mounting: separate executor required','Natural scheduler/deadline activation and two-day evidence: not activated'],
        result='PASS_ENGINEERING_CANDIDATE' if all(r['exit_code']==0 for r in results) else 'FAILED')
    (out/'receipt.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(record,ensure_ascii=False,indent=2));return 0 if record['result']=='PASS_ENGINEERING_CANDIDATE' else 1

if __name__=='__main__':raise SystemExit(main())
