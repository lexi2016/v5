"""Targeted offline acceptance; optional explicit saved-input replay, never collection."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[2]
SUITES=['test_a_close_historical','test_a_close_receipt_integrity',
    'test_a_close_daily.DailyBehaviorTests.test_price_chain_writer_reader_preserves_native_fields',
    'test_a_close_daily.DailyBehaviorTests.test_cas_conflict_keeps_served_generation',
    'test_a_close_daily.DailyBehaviorTests.test_later_failure_keeps_previous_success',
    'test_a_close_daily.DailyBehaviorTests.test_source_receipt_time_disagreement_rejected',
    'test_a_close_daily_sources.SourceTests.test_full_original_product_writer_and_independent_reader_keep_all_boundaries',
    'test_a_close_daily_sources.SourceTests.test_original_reader_rejects_modified_payload']


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--evidence-dir',type=Path)
    parser.add_argument('--require-supported',action='store_true')
    parser.add_argument('--require-zero-skip',action='store_true')
    for key in ('source-root','pointer','pointer-sha256','panel-sha256','trade-date','snapshot-root','run-root','receipt','receipt-sha256'):
        parser.add_argument('--'+key)
    args=parser.parse_args();evidence=args.evidence_dir or Path(tempfile.mkdtemp(prefix='m09-history-evidence-'))
    evidence.mkdir(parents=True,exist_ok=True)
    versions={}
    for name in ('pandas','pyarrow'):
        try:versions[name]=importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:versions[name]=None
    def pair(v):
        try:return tuple(map(int,v.split('.')[:2]))
        except (AttributeError,ValueError):return (0,0)
    supported=sys.version_info >= (3,14) and (2,3)<=pair(versions['pandas'])<(3,0) and (21,0)<=pair(versions['pyarrow'])<(25,0)
    report=dict(schema_version='v5.m09.historical_acceptance.v1',started_at=datetime.now(timezone.utc).isoformat(),
                python=sys.version.split()[0],dependencies=versions,declared_environment_compatible=supported,
                tests=None,real_saved_input='NOT_RUN',natural_run='NOT_RUN',deployment='NOT_RUN',original_136_rerun='NOT_RUN')
    if versions['pandas'] is None or (args.require_supported and not supported):
        report.update(status='NOT_RUN',reason='EXISTING_ENVIRONMENT_UNSUPPORTED',exit_code=2)
    else:
        script='''import json,sys,unittest
sys.path[:0]=sys.argv[1:3]
suite=unittest.defaultTestLoader.loadTestsFromNames(json.loads(sys.argv[3]))
r=unittest.TextTestRunner(verbosity=2).run(suite)
print('M09_RESULT='+json.dumps(dict(run=r.testsRun,failures=len(r.failures),errors=len(r.errors),skipped=[(str(t),why) for t,why in r.skipped]),sort_keys=True))
sys.exit(0 if r.wasSuccessful() else 1)
'''
        env=dict(os.environ,PYTHONPATH=os.pathsep.join((str(ROOT/'V5/src'),str(ROOT/'V5/tests'))),PYTHONDONTWRITEBYTECODE='1')
        result=subprocess.run([sys.executable,'-I','-B','-c',script,str(ROOT/'V5/src'),str(ROOT/'V5/tests'),json.dumps(SUITES)],cwd=ROOT,env=env,text=True,capture_output=True)
        (evidence/'targeted.stdout.log').write_text(result.stdout);(evidence/'targeted.stderr.log').write_text(result.stderr)
        print(result.stdout+result.stderr,end='')
        marker=next((line for line in result.stdout.splitlines() if line.startswith('M09_RESULT=')),None)
        stats=json.loads(marker.split('=',1)[1]) if marker else None
        report.update(tests=stats,status='FAIL',exit_code=result.returncode or (0 if stats else 1))
        if result.returncode==0 and stats:
            report['status']='PASS_WITH_NOT_RUN' if stats['skipped'] else 'PASS'
            if args.require_zero_skip and stats['skipped']:report.update(status='NOT_RUN',exit_code=2)
        fields=[args.source_root,args.pointer,args.pointer_sha256,args.panel_sha256,args.trade_date,args.snapshot_root,args.run_root]
        if any(fields) and not all(fields):report.update(status='NOT_RUN',exit_code=2,real_saved_input='MISSING_EXPLICIT_INPUT_ARGUMENTS')
        elif all(fields) and report['exit_code']==0:
            sys.path.insert(0,str(ROOT/'V5/src'))
            from v5_shadow import a_close_historical as h
            from v5_shadow.a_close_daily import read_a_close_daily
            try:
                h.prepare_a_close_historical_snapshot(args.source_root,args.pointer,args.pointer_sha256,args.panel_sha256,
                    args.trade_date,args.snapshot_root,receipt_path=args.receipt,expected_receipt_sha256=args.receipt_sha256)
                h.initialize_a_close_historical_root(args.run_root)
                receipt=h.run_a_close_historical(args.run_root,args.snapshot_root,args.trade_date,attempt_id='mac-existing-history')
                if receipt['status']!='SUCCEEDED':raise ValueError(receipt.get('reason','HISTORICAL_REPLAY_FAILED'))
                read=read_a_close_daily(args.run_root,args.trade_date)
                cold_code="import json,sys;from pathlib import Path;sys.path.insert(0,sys.argv[1]);from v5_shadow.a_close_daily import read_a_close_daily;from v5_shadow.a_close_daily_api import read_a_close_preview;r=read_a_close_daily(Path(sys.argv[2]),sys.argv[3]);p=read_a_close_preview(Path(sys.argv[2]),sys.argv[3]);assert p['m09_publication']['generation_sha256']==r['identity']['generation_sha256'];assert p['model_review']['run_id']==r['identity']['model_run_id'];print(json.dumps(r['identity'],sort_keys=True))"
                cold=subprocess.run([sys.executable,'-I','-B','-c',cold_code,str(ROOT/'V5/src'),args.run_root,args.trade_date],capture_output=True,text=True)
                if cold.returncode or json.loads(cold.stdout)!=read['identity']:
                    raise ValueError('M09_HISTORICAL_COLD_READ_FAILED:'+cold.stderr)
                report['real_saved_input']=dict(status='HISTORICAL_RESEARCH_SAVED_AND_COLD_READ',identity=read['identity'],cold_read_verified=True,
                    execution_kind=read['record']['execution_kind'],business_status=read['record']['business_status'],
                    scope=read['record']['scope'],historical_research=read['record']['historical_research'],
                    original_close_chain_status=read['review']['close_chain'].get('status'),
                    natural_verified=False,strict_1500_pit_verified=False)
            except Exception as exc:
                message=type(exc).__name__+':'+str(exc)
                for value in (args.source_root,args.snapshot_root,args.run_root):message=message.replace(value,'<PRIVATE_INPUT_OR_RUN_ROOT>')
                report.update(status='FAIL',exit_code=1,real_saved_input=dict(status='FAILED',reason=message))
    report['finished_at']=datetime.now(timezone.utc).isoformat()
    report['source_sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
        for p in [ROOT/'V5/src/v5_shadow'/name for name in ('a_close_historical.py','a_close_daily.py','a_close_daily_sources.py','a_close_daily_worker.py','a_close_daily_api.py')]
        +[Path(__file__).resolve(),ROOT/'V5/tests/test_a_close_historical.py']}
    (evidence/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('M09 historical acceptance:',report['status'])
    return report['exit_code']


if __name__=='__main__':sys.exit(main())
