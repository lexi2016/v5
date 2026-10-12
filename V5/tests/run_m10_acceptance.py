"""One isolated acceptance command; no network, installation or source mutation."""
from __future__ import annotations
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[2]

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--pytest-site-packages',required=True,type=Path,
                        help='Existing directory containing pytest; loaded without .pth processing')
    parser.add_argument('--evidence-dir',type=Path)
    args=parser.parse_args()
    site=args.pytest_site_packages.absolute()
    if not (site/'pytest/__init__.py').is_file(): parser.error('pytest is absent in the specified existing directory')
    evidence=args.evidence_dir or Path(tempfile.mkdtemp(prefix='m10-acceptance-'))
    evidence.mkdir(parents=True,exist_ok=True)
    sys.path.insert(0,str(ROOT/'V5/src'))
    from v5_shadow.hk_close_daily import prepare_owner_capsule
    commands=[]
    def run(name,script):
        argv=[sys.executable,'-I','-S','-B','-c',script]
        start=datetime.datetime.now(datetime.timezone.utc).isoformat()
        result=subprocess.run(argv,cwd=ROOT,text=True,capture_output=True,
            env={**os.environ,'PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1'})
        end=datetime.datetime.now(datetime.timezone.utc).isoformat()
        (evidence/(name+'.stdout.log')).write_text(result.stdout)
        (evidence/(name+'.stderr.log')).write_text(result.stderr)
        commands.append({'suite':name,'argv':argv,'start':start,'end':end,'exit_code':result.returncode,
                         'process_environment':{'PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1'}})
        print(name+':\n'+result.stdout+result.stderr,flush=True)
        return result.returncode
    prefix=f'import sys;sys.path[:0]={[str(ROOT/"V5/src"),str(site)]!r};import pytest;'
    product=run('product',prefix+f'sys.exit(pytest.main(["-q","-p","no:cacheprovider",{str(ROOT/"V5/tests")!r}]))')
    original=ROOT/'handoffs/M10/handoff/v4-running-source-20261005/canonical/tests'
    with prepare_owner_capsule() as capsule:
        paths=[str(original/name) for name in ('test_close_review_producer.py','test_close_review_verified_inputs.py','test_close_snapshot_idempotent_reuse.py')]
        argv=['-q','-p','no:cacheprovider',*paths,'-k','not vipdoc_normalizer and not executor_requires']
        canonical=run('frozen-original',f'import sys;sys.path[:0]={[str(capsule),str(site)]!r};import pytest;sys.exit(pytest.main({argv!r}))')
    hashes={str(p.relative_to(ROOT)):{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
            for directory in ('V5/src/v5_shadow','V5/tests','integration_candidates/M10/CAPSULE_INTEGRATION_CANDIDATE')
            for p in (ROOT/directory).rglob('*') if p.is_file() and '__pycache__' not in str(p)}
    report={'python':sys.version,'commands':commands,'source_files':hashes,
            'not_run':{'test_vipdoc_normalizer_freezes_target_date_and_removes_external_paths':'Frozen import_hkconnect_close_source.py not part of supplied M10 closure.',
                       'test_close_review_executor_requires_and_passes_stage_selection_root':'Full runtime_tasks/scheduler closure not supplied; no live scheduler execution.',
                       'natural_run':'M02 membership/PIT and active half-day contracts unverified; no real collection.',
                       'api_ui_deployment':'This command is offline engine/read-projection acceptance only.'},
            'result':'PASS' if product==canonical==0 else 'FAIL'}
    (evidence/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Evidence:',evidence)
    return 0 if report['result']=='PASS' else 1

if __name__=='__main__': sys.exit(main())
