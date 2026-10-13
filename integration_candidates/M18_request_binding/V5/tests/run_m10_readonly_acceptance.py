"""One fixed-commit command: targeted synthetic checks and optional real cold GET.

Uses existing Python/Node/frontend dependencies only. No service deployment,
producer, collection, scheduler, credential access or original 39-suite rerun.
Only report.json is suitable for upload; subprocess logs remain private/local.
"""
import argparse
from datetime import datetime,timezone
import hashlib
import http.client
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading

REPO=Path(__file__).resolve().parents[2]
BASE=REPO/'V5'
sys.path[:0]=[str(BASE/'src'),str(BASE/'tests')]
from v5_shadow.m10_readonly import BINDING,ROUTE,owner_root
from v5_shadow.module_api import create_module_server


CODE_SCOPE=('V5/src','V5/contracts','V5/source_owners','V5/tests','frontend/src','frontend/tests',
    'frontend/vite.config.ts','frontend/tsconfig.json','frontend/tsconfig.cloud-product.json',
    'frontend/package.json','frontend/package-lock.json','frontend/index.html',
    'frontend/daily-research-command/index.html','frontend/manager-selection/index.html','frontend/public')


def verify_checkout(repo,expected):
    def git(*args):
        return subprocess.run(['git',*args],cwd=repo,capture_output=True,text=True)
    head=git('rev-parse','HEAD')
    if head.returncode or head.stdout.strip()!=expected:raise ValueError('M10_FIXED_COMMIT_MISMATCH')
    if git('diff','--no-ext-diff','--quiet','HEAD','--',*CODE_SCOPE).returncode:
        raise ValueError('M10_FIXED_COMMIT_DIRTY_SOURCES')
    untracked=git('ls-files','--others','-z','--',*CODE_SCOPE)
    if untracked.returncode:raise ValueError('M10_FIXED_COMMIT_INVENTORY_FAILED')
    paths=[p for p in untracked.stdout.split('\0') if p]
    if any(not ('__pycache__' in Path(p).parts and p.endswith('.pyc')) for p in paths):
        raise ValueError('M10_FIXED_COMMIT_UNTRACKED_SOURCES')
    return head.stdout.strip()


def now():return datetime.now(timezone.utc).isoformat()
def digest(raw):return hashlib.sha256(raw).hexdigest()
def inventory(root):
    return {str(p.relative_to(root)):(digest(p.read_bytes()),p.stat().st_mtime_ns)
        for p in Path(root).rglob('*') if p.is_file()}


def real_read(config,private_file):
    binding=config[BINDING]
    before=inventory(Path(binding['run_root']));source_before=inventory(Path(config['data_root']))
    server=create_module_server(config);thread=threading.Thread(target=server.serve_forever);thread.start()
    try:
        client=http.client.HTTPConnection('127.0.0.1',server.server_address[1],timeout=40)
        client.request('GET',ROUTE);response=client.getresponse();body=response.read();status=response.status;client.close()
    finally:server.shutdown();thread.join();server.server_close()
    if status!=200:raise ValueError('M10_REAL_HTTP_REJECTED_'+str(status))
    value=json.loads(body)
    # Independent cold read of the same frozen function, never default builder.
    worker=BASE/'src/v5_shadow/m10_readonly_worker.py'
    expected=subprocess.run([binding['python_executable'],'-I','-S','-B',str(worker),str(owner_root())],
        input=json.dumps(binding).encode(),capture_output=True,timeout=35)
    if expected.returncode:raise ValueError('M10_REAL_EXPECTED_REJECTED')
    projection=json.loads(expected.stdout)
    if value['review']!=projection['review'] or value['run_id']!=binding['run_id'] or value['generation']!=binding['generation']:
        raise ValueError('M10_REAL_PROJECTION_MISMATCH')
    if inventory(Path(binding['run_root']))!=before or inventory(Path(config['data_root']))!=source_before:
        raise ValueError('M10_REAL_READ_CHANGED_FILES')
    if any(value[k] is not False for k in ('production_allowed','buy_gate_updated','orders_sent','natural_verified','formal_eligibility_verified')):
        raise ValueError('M10_REAL_RESEARCH_BOUNDARY')
    private_file.write_bytes(body)
    review=value['review']
    return dict(status='PASS',http_status=status,run_id=value['run_id'],generation=value['generation'],
        native_review_sha256=value['native_review_sha256'],response_sha256=digest(body),
        projection_status=value['status'],data_kind=value['data_kind'],natural_admission=value['natural_admission'],
        counts={k:len(review[k]) for k in ('close_top20','model_rows','stage_rows','top20_attribution')},
        stage_statuses={k:v.get('source_status') for k,v in review['stages'].items()},
        exact_original_projection_equal=True,run_root_files_unchanged=True,source_api_root_files_unchanged=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expected-commit');parser.add_argument('--source-config',type=Path)
    parser.add_argument('--evidence-dir',type=Path,required=True)
    parser.add_argument('--skip-frontend',action='store_true',help='Synthetic cloud checks only; reports frontend NOT_RUN, never full acceptance.')
    args=parser.parse_args()
    if args.source_config and (not args.expected_commit or args.skip_frontend):parser.error('Real acceptance requires --expected-commit and all frontend checks')
    report=dict(schema_version='v5.m10_readonly_acceptance.v1',started_utc=now(),mode='REAL_SAVED_COLD_READ' if args.source_config else 'SYNTHETIC_ONLY',
        steps=[],real_read={'status':'NOT_RUN'},frontend={'status':'NOT_RUN'},network_collection=False,producer_invoked=False,services_changed=False,deployed=False)
    evidence=args.evidence_dir.resolve();evidence.mkdir(parents=True,exist_ok=True)
    existing=subprocess.run(['git','rev-parse','HEAD'],cwd=REPO,capture_output=True,text=True)
    head=existing.stdout.strip() if existing.returncode==0 else None;report['commit']=head
    if args.expected_commit:
        try:report['commit']=verify_checkout(REPO,args.expected_commit)
        except ValueError as error:
            report.update(status='FAILED',reason=str(error),ended_utc=now());(evidence/'report.json').write_text(json.dumps(report,indent=2)+'\n');return 1
    owner_root()
    code_paths=['V5/src/v5_shadow/module_api.py','V5/src/v5_shadow/source_bundle.py','V5/src/v5_shadow/m10_readonly.py','V5/src/v5_shadow/m10_readonly_worker.py','V5/contracts/m10_readonly_runtime.json','V5/source_owners/m10/V5/src/v5_shadow/hk_close_daily.py','frontend/src/api/hkCloseReview.ts','frontend/src/components/HkCloseReview.vue','frontend/src/components/SourceBundleStatus.vue','frontend/vite.config.ts']
    code_paths += ['V5/tests/run_m10_readonly_acceptance.py','V5/tests/test_m10_acceptance_runner.py',
        'V5/tests/test_m10_readonly_api.py','V5/tests/export_m10_readonly_fixture.py','V5/tests/fixtures/hk_close_readonly_factory.py',
        'frontend/tests/hkCloseReview.node.mjs','frontend/src/components/HkCloseReview.spec.ts']
    if args.expected_commit:
        tracked=subprocess.run(['git','ls-files','-z','--',*CODE_SCOPE],cwd=REPO,capture_output=True,text=True,check=True)
        code_paths=[p for p in tracked.stdout.split('\0') if p]
    report['source_files']=[dict(path=p,sha256=digest((REPO/p).read_bytes()),bytes=(REPO/p).stat().st_size) for p in code_paths]
    env=dict(os.environ,PYTHON=sys.executable,PYTHONDONTWRITEBYTECODE='1');failed=False
    def run(name,argv,cwd):
        nonlocal failed
        started=now()
        try:
            proc=subprocess.run(argv,cwd=cwd,env=env,capture_output=True,timeout=300)
            out,err,code=proc.stdout,proc.stderr,proc.returncode
        except (OSError,subprocess.TimeoutExpired) as error:
            out=b'';err=type(error).__name__.encode();code=127
        (evidence/(name+'.stdout.local.log')).write_bytes(out);(evidence/(name+'.stderr.local.log')).write_bytes(err)
        report['steps'].append(dict(name=name,started_utc=started,ended_utc=now(),exit_code=code,
            stdout_sha256=digest(out),stderr_sha256=digest(err),status='PASS' if code==0 else 'FAILED'))
        failed=failed or code!=0
    with tempfile.TemporaryDirectory(prefix='m10-private-readonly-') as temp:
        if args.source_config:
            try:report['real_read']=real_read(json.loads(args.source_config.read_bytes()),Path(temp)/'response.json');env['V5_M10_RESPONSE_FILE']=str(Path(temp)/'response.json')
            except Exception as error:
                report['real_read']=dict(status='FAILED',reason=str(error) if str(error).startswith('M10_') else type(error).__name__);failed=True
        script="import sys;sys.path[:0]=['V5/src','V5/tests'];import unittest;unittest.main(module=None,argv=['unittest','test_m10_readonly_api','test_m10_acceptance_runner','test_module_api','test_source_bundle.SourceBundleTests.test_source_publication_is_readonly_and_separate_from_manager','-v'])"
        run('targeted-python',[sys.executable,'-I','-S','-B','-c',script],REPO)
        run('targeted-node',['node','--test','tests/hkCloseReview.node.mjs','tests/hkPreselectionPool.node.mjs','tests/sourceBundle.node.mjs'],REPO/'frontend')
        if not args.skip_frontend and not (args.source_config and report['real_read']['status']!='PASS'):
            run('component-dom',['npm','run','test','--','src/components/HkCloseReview.spec.ts'],REPO/'frontend')
            run('typecheck',['npm','run','typecheck','--','--project','tsconfig.cloud-product.json'],REPO/'frontend')
            run('build',['npm','run','build'],REPO/'frontend')
            report['frontend']['status']='PASS' if all(s['status']=='PASS' for s in report['steps'] if s['name'] in ('component-dom','typecheck','build')) else 'FAILED'
    report['ended_utc']=now()
    report['status']='FAILED' if failed else ('PARTIAL_VERIFICATION' if args.skip_frontend else 'PASS')
    (evidence/'report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({k:report[k] for k in ('status','mode','real_read','frontend')},ensure_ascii=False))
    return 1 if failed else 0


if __name__=='__main__':raise SystemExit(main())
