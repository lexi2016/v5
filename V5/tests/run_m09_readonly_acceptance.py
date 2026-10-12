"""Fixed-commit M09 P0 acceptance: new seam tests and optional exact saved GET.

Uses existing Python/pandas/Node/frontend dependencies only. Does not rerun the
owner's 136 or 30 suites, capture a source, produce a real review, deploy, or
change service bindings. Only report.json is uploadable; logs/response are local.
"""
import argparse
from datetime import datetime,timezone
import hashlib
import http.client
import importlib.metadata
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
from v5_shadow.m09_readonly import BINDING,ROUTE,owner_root
from v5_shadow.module_api import create_module_server

CODE_SCOPE=('V5/src','V5/contracts','V5/source_owners','V5/tests','frontend/src','frontend/tests',
    'frontend/vite.config.ts','frontend/tsconfig.json','frontend/tsconfig.cloud-product.json',
    'frontend/package.json','frontend/package-lock.json','frontend/index.html',
    'frontend/daily-research-command/index.html','frontend/manager-selection/index.html','frontend/public')


def verify_checkout(repo,expected):
    def git(*args):return subprocess.run(['git',*args],cwd=repo,capture_output=True,text=True)
    head=git('rev-parse','HEAD')
    if head.returncode or head.stdout.strip()!=expected:raise ValueError('M09_FIXED_COMMIT_MISMATCH')
    if git('diff','--no-ext-diff','--quiet','HEAD','--',*CODE_SCOPE).returncode:
        raise ValueError('M09_FIXED_COMMIT_DIRTY_SOURCES')
    untracked=git('ls-files','--others','-z','--',*CODE_SCOPE)
    if untracked.returncode:raise ValueError('M09_FIXED_COMMIT_INVENTORY_FAILED')
    paths=[p for p in untracked.stdout.split('\0') if p]
    if any(not ('__pycache__' in Path(p).parts and p.endswith('.pyc')) for p in paths):
        raise ValueError('M09_FIXED_COMMIT_UNTRACKED_SOURCES')
    return head.stdout.strip()


def now():return datetime.now(timezone.utc).isoformat()
def digest(raw):return hashlib.sha256(raw).hexdigest()
def inventory(root):
    records={}
    for p in Path(root).rglob('*'):
        if p.is_symlink():raise ValueError('M09_ACCEPTANCE_SYMLINK_REJECTED')
        if p.is_file():
            sha=hashlib.sha256()
            with p.open('rb') as stream:
                for chunk in iter(lambda:stream.read(1024*1024),b''):sha.update(chunk)
            records[str(p.relative_to(root))]=(sha.hexdigest(),p.stat().st_mtime_ns)
    return records


def real_read(config,private_file):
    binding=config[BINDING];root=owner_root()
    before=inventory(Path(binding['run_root']));source_before=inventory(Path(config['data_root']))
    server=create_module_server(config);thread=threading.Thread(target=server.serve_forever);thread.start()
    try:
        c=http.client.HTTPConnection('127.0.0.1',server.server_address[1],timeout=60)
        c.request('GET',ROUTE);r=c.getresponse();body=r.read();status=r.status;c.close()
    finally:server.shutdown();thread.join();server.server_close()
    if status!=200:raise ValueError('M09_REAL_HTTP_REJECTED_'+str(status))
    value=json.loads(body)
    # Independent ORIGINAL read/projection, not a second bridge-worker response.
    code="""import json,sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from v5_shadow.a_close_daily import read_a_close_daily
from v5_shadow.a_close_daily_api import project_committed_review
b=json.load(sys.stdin);v=read_a_close_daily(b['run_root'],b['trade_date'],generation_sha256=b['generation'])
print(json.dumps(dict(review=v['review'],identity=v['identity'],publication=project_committed_review(v,b['trade_date'])['m09_publication']),ensure_ascii=False,allow_nan=False))
"""
    expected=subprocess.run([binding['python_executable'],'-I','-B','-c',code,str(root/'V5/src')],
        input=json.dumps(binding).encode(),capture_output=True,timeout=50)
    if expected.returncode:raise ValueError('M09_REAL_EXPECTED_REJECTED')
    projection=json.loads(expected.stdout)
    expected_history=projection['publication']['historical_research']
    public_history=value['publication']['historical_research']
    for field in ('original_source','original_receipt'):
        if public_history[field] is not None:
            expected_history[field]={key:expected_history[field][key] for key in public_history[field]}
    if (value['review']!=projection['review'] or value['identity']!=projection['identity']
            or value['run_id']!=binding['run_id'] or value['generation']!=binding['generation']
            or value['trade_date']!=binding['trade_date']
            or any(item!=projection['publication'][key] for key,item in value['publication'].items())):
        raise ValueError('M09_REAL_PROJECTION_MISMATCH')
    if inventory(Path(binding['run_root']))!=before or inventory(Path(config['data_root']))!=source_before:
        raise ValueError('M09_REAL_READ_CHANGED_FILES')
    if (value['status']!='PARTIAL' or value['execution_kind']!='HISTORICAL_REPLAY'
            or value['scope']!='OBSERVED_ROWS_ONLY' or value['data_kind']!='RECORDED_INPUT_REPLAY'
            or any(value[k] is not False for k in ('production_allowed','buy_gate_updated','orders_sent',
                'natural_verified','formal_eligibility_verified','strict_1500_pit_verified','source_time_verified','membership_qualification_verified'))):
        raise ValueError('M09_REAL_RESEARCH_BOUNDARY')
    private_file.write_bytes(body);historical=value['publication']['historical_research']
    return dict(status='PASS',http_status=status,trade_date=value['trade_date'],run_id=value['run_id'],generation=value['generation'],
        identity=value['identity'],response_sha256=digest(body),projection_status=value['status'],data_kind=value['data_kind'],
        execution_kind=value['execution_kind'],scope=value['scope'],snapshot_row_count=historical['snapshot_row_count'],
        missing_text=historical['missing_text'],nonfinite_unused_close_position=historical['nonfinite_unused_close_position'],
        native_row_counts={key:len(value['review'][key]) for key in ('big_picture','mainlines','core_stocks','observation_pool','next_day_trigger_tree','quality_gate')},
        exact_original_review_and_publication_equal=True,run_root_files_unchanged=True,source_api_root_files_unchanged=True)


def environment():
    try:pandas=importlib.metadata.version('pandas')
    except importlib.metadata.PackageNotFoundError:pandas=None
    supported=sys.version_info[:2]>=(3,14) and pandas is not None and tuple(int(p) for p in pandas.split('.')[:2])>=(2,3)
    return dict(python='.'.join(map(str,sys.version_info[:3])),pandas=pandas,supported=bool(supported),pyarrow_required_for_cold_read=False)


def worker_environment(executable):
    code="""import importlib.metadata,json,sys
try:pandas=importlib.metadata.version('pandas')
except importlib.metadata.PackageNotFoundError:pandas=None
supported=sys.version_info[:2]>=(3,14) and pandas is not None and tuple(int(p) for p in pandas.split('.')[:2])>=(2,3)
print(json.dumps(dict(python='.'.join(map(str,sys.version_info[:3])),pandas=pandas,supported=bool(supported))))
"""
    probe=subprocess.run([executable,'-I','-B','-c',code],capture_output=True,text=True,timeout=15)
    if probe.returncode or len(probe.stdout)>4096:raise ValueError('M09_WORKER_ENVIRONMENT_PROBE_FAILED')
    value=json.loads(probe.stdout)
    if not isinstance(value,dict) or type(value.get('supported')) is not bool:
        raise ValueError('M09_WORKER_ENVIRONMENT_PROBE_INVALID')
    return value


def require_supported_environments(runner,worker):
    if runner.get('supported') is not True or worker.get('supported') is not True:
        raise ValueError('M09_SUPPORTED_EXISTING_ENV_REQUIRED')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expected-commit');parser.add_argument('--source-config',type=Path)
    parser.add_argument('--evidence-dir',type=Path,required=True)
    parser.add_argument('--skip-frontend',action='store_true',help='Cloud compatibility only; DOM/typecheck/build explicitly NOT_RUN.')
    args=parser.parse_args()
    if args.source_config and (not args.expected_commit or args.skip_frontend):parser.error('Real acceptance requires fixed commit and all frontend checks')
    report=dict(schema_version='v5.m09_readonly_acceptance.v1',started_utc=now(),
        mode='REAL_SAVED_COLD_READ' if args.source_config else 'SYNTHETIC_ONLY',environment=environment(),
        steps=[],real_read={'status':'NOT_RUN'},frontend={'status':'NOT_RUN'},network_collection=False,
        real_producer_invoked=False,synthetic_test_fixture_producer_only=True,services_changed=False,deployed=False,
        original_136_rerun=False,original_30_rerun=False)
    evidence=args.evidence_dir.resolve();evidence.mkdir(parents=True,exist_ok=True)
    existing=subprocess.run(['git','rev-parse','HEAD'],cwd=REPO,capture_output=True,text=True)
    report['commit']=existing.stdout.strip() if existing.returncode==0 else None
    env=dict(os.environ,PYTHON=sys.executable,PYTHONDONTWRITEBYTECODE='1');failed=False
    def run(name,argv,cwd):
        nonlocal failed
        started=now()
        try:
            proc=subprocess.run(argv,cwd=cwd,env=env,capture_output=True,timeout=300);out,err,code=proc.stdout,proc.stderr,proc.returncode
        except (OSError,subprocess.TimeoutExpired) as error:out=b'';err=type(error).__name__.encode();code=127
        (evidence/(name+'.stdout.local.log')).write_bytes(out);(evidence/(name+'.stderr.local.log')).write_bytes(err)
        report['steps'].append(dict(name=name,started_utc=started,ended_utc=now(),exit_code=code,
            stdout_sha256=digest(out),stderr_sha256=digest(err),status='PASS' if code==0 else 'FAILED'))
        failed=failed or code!=0
    try:
        if args.expected_commit:report['commit']=verify_checkout(REPO,args.expected_commit)
        config=None
        if args.source_config:
            config=json.loads(args.source_config.read_bytes())
            report['worker_environment']=worker_environment(config[BINDING]['python_executable'])
            require_supported_environments(report['environment'],report['worker_environment'])
        owner_root()
        code_paths=['V5/src/v5_shadow/module_api.py','V5/src/v5_shadow/source_bundle.py','V5/src/v5_shadow/m09_readonly.py',
            'V5/src/v5_shadow/m09_readonly_worker.py','V5/contracts/m09_readonly_runtime.json','V5/tests/run_m09_readonly_acceptance.py',
            'V5/tests/test_m09_readonly_api.py','V5/tests/test_m09_acceptance_runner.py','V5/tests/fixtures/a_close_replay_factory.py',
            'V5/tests/export_m09_readonly_fixture.py','frontend/src/api/aCloseReplay.ts','frontend/src/components/ACloseReplay.vue',
            'frontend/src/components/ACloseReplay.spec.ts','frontend/src/components/SourceBundleStatus.vue',
            'frontend/src/components/SourceBundleStatus.m09.spec.ts','frontend/tests/aCloseReplay.node.mjs','frontend/vite.config.ts']
        if args.expected_commit:
            tracked=subprocess.run(['git','ls-files','-z','--',*CODE_SCOPE],cwd=REPO,capture_output=True,text=True,check=True)
            code_paths=[p for p in tracked.stdout.split('\0') if p]
        report['source_files']=[dict(path=p,sha256=digest((REPO/p).read_bytes()),bytes=(REPO/p).stat().st_size) for p in code_paths]
        with tempfile.TemporaryDirectory(prefix='m09-private-readonly-') as temp:
            if args.source_config:
                try:
                    report['real_read']=real_read(config,Path(temp)/'response.json')
                    env['V5_M09_RESPONSE_FILE']=str(Path(temp)/'response.json')
                except Exception as error:
                    report['real_read']=dict(status='FAILED',reason=str(error) if str(error).startswith('M09_') else type(error).__name__);failed=True
            script="import sys;sys.path[:0]=['V5/src','V5/tests'];import unittest;unittest.main(module=None,argv=['unittest','test_m09_readonly_api','test_m09_acceptance_runner','test_module_api','-v'])"
            run('targeted-python',[sys.executable,'-I','-B','-c',script],REPO)
            run('targeted-node',['node','--test','tests/aCloseReplay.node.mjs','tests/hkCloseReview.node.mjs','tests/hkPreselectionPool.node.mjs','tests/sourceBundle.node.mjs'],REPO/'frontend')
            if not args.skip_frontend and not (args.source_config and report['real_read']['status']!='PASS'):
                run('component-dom',['npm','run','test','--','src/components/ACloseReplay.spec.ts','src/components/SourceBundleStatus.m09.spec.ts'],REPO/'frontend')
                run('typecheck',['npm','run','typecheck','--','--project','tsconfig.cloud-product.json'],REPO/'frontend')
                run('build',['npm','run','build'],REPO/'frontend')
                report['frontend']['status']='PASS' if all(s['status']=='PASS' for s in report['steps'] if s['name'] in ('component-dom','typecheck','build')) else 'FAILED'
    except Exception as error:
        report['reason']=str(error) if str(error).startswith('M09_') else type(error).__name__;failed=True
    report['ended_utc']=now();report['status']='FAILED' if failed else ('PARTIAL_VERIFICATION' if args.skip_frontend else 'PASS')
    (evidence/'report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({k:report[k] for k in ('status','mode','real_read','frontend')},ensure_ascii=False))
    return 1 if failed else 0


if __name__=='__main__':raise SystemExit(main())
