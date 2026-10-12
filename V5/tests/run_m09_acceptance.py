"""One offline M09 acceptance command, using only the selected existing Python."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[2]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--evidence-dir',type=Path)
    parser.add_argument('--require-supported',action='store_true')
    parser.add_argument('--require-zero-skip',action='store_true')
    args=parser.parse_args()
    evidence=(args.evidence_dir or Path(tempfile.mkdtemp(prefix='m09-acceptance-'))).resolve()
    evidence.mkdir(parents=True,exist_ok=True)
    versions={}
    for name in ('pandas','pyarrow'):
        try:versions[name]=importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:versions[name]=None
    def pair(value):
        try:return tuple(map(int,value.split('.')[:2]))
        except (AttributeError,ValueError):return (0,0)
    supported=sys.version_info >= (3,14) and (2,3)<=pair(versions['pandas'])<(3,0) and (21,0)<=pair(versions['pyarrow'])<(25,0)
    report={'schema_version':'v5.m09.acceptance.v1','started_at':datetime.now(timezone.utc).isoformat(),
            'python':sys.version.split()[0], 'dependencies':versions,'declared_environment_compatible':supported,
            'scope':'OFFLINE_SYNTHETIC_ORIGINAL_OWNER_AND_READBACK',
            'live_data':'NOT_RUN','mac':'NOT_RUN' if sys.platform!='darwin' else 'OFFLINE_TEST_ONLY',
            'api_ui_deployment':'NOT_RUN','natural_slots':'NOT_RUN','tests':None}
    if importlib.util.find_spec('pandas') is None or (args.require_supported and not supported):
        report.update(status='NOT_RUN',reason='EXISTING_INTERPRETER_DEPENDENCIES_UNAVAILABLE_OR_OUTSIDE_DECLARED_RANGE',exit_code=2)
    else:
        donor=ROOT/'handoff/v4-running-source-20261005/canonical'
        script='''import json,sys,unittest
sys.path[:0]=sys.argv[1:3]
suite=unittest.defaultTestLoader.discover(sys.argv[2])
result=unittest.TextTestRunner(verbosity=2).run(suite)
print('M09_TEST_RESULT='+json.dumps({'run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':[(str(t),reason) for t,reason in result.skipped]},sort_keys=True))
sys.exit(0 if result.wasSuccessful() else 1)
'''
        env=dict(os.environ,M09_ORIGINAL_SOURCE_ROOT=str(donor),PYTHONDONTWRITEBYTECODE='1',
                 PYTHONPATH=os.pathsep.join((str(ROOT/'V5/src'),str(ROOT/'V5/tests'))))
        result=subprocess.run([sys.executable,'-I','-B','-c',script,str(ROOT/'V5/src'),str(ROOT/'V5/tests')],
                              cwd=ROOT,env=env,text=True,capture_output=True)
        (evidence/'product.stdout.log').write_text(result.stdout)
        (evidence/'product.stderr.log').write_text(result.stderr)
        print(result.stdout+result.stderr,end='')
        marker=next((line for line in result.stdout.splitlines() if line.startswith('M09_TEST_RESULT=')),None)
        stats=json.loads(marker.split('=',1)[1]) if marker else None
        report.update(tests=stats,exit_code=result.returncode,status='FAIL')
        if result.returncode==0 and stats is not None:
            report['status']='PASS_WITH_NOT_RUN' if stats['skipped'] else 'PASS'
            if args.require_zero_skip and stats['skipped']:report.update(status='NOT_RUN',exit_code=2)
    report['finished_at']=datetime.now(timezone.utc).isoformat()
    report['source_sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
        for directory in ('V5/src/v5_shadow','V5/tests','V5/vendor/m09_a_close_daily','V5/contracts')
        for p in (ROOT/directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    (evidence/'report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    print('M09 acceptance:',report['status'])
    return report['exit_code']


if __name__=='__main__':sys.exit(main())
