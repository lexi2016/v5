"""SIMULATED process/ledger integration; not natural-market acceptance.
Pool/quote fixture provenance: fixed F test_manager_close_executor_rework.py L35-84,
Git blob 38fa6bbf4200fbbb53599fdb01132b3472970ad5. Never import its scheduler.
Run from repository root: python -B integration_candidates/M17/after/V5/tests/test_daily_close_recapture_owner.py
"""
import csv
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE=Path(__file__).resolve().parents[1]
REPO=next(p for p in (HERE,*HERE.parents) if (p/'V5/vendor/close_discovery_baseline').is_dir())
sys.path.insert(0,str(HERE/'src'))

def encoded(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def digest(v):return hashlib.sha256(v).hexdigest()

def fixture(root):
    state=root/'state';state.mkdir();(state/'.v5-m17-close-root').write_text('v5.m17.simulated-close.v1\n')
    ledger=root/'ledger';ledger.mkdir();(ledger/'.v5-daily-run-ledger').write_text('v5.daily-run-ledger.v1\n')
    universe=root/'universe'; source='20260928';run='20260928-hk-connect-d1-top100-0-2-fixture'
    relative=f'runs/{source}/HK_CONNECT_D1_TOP100_0_2/{run}'
    folder=universe/'.runtime/data'/relative;folder.mkdir(parents=True)
    rows=[dict(trade_date=source,bar_time='17:30',rank=i,code=f'HK.{i:05d}',name=f'stock-{i}',signal_date='20260924',target_date=source,recommendation_status='WATCH_ONLY_BACKTEST_GATED',production_allowed='False',score_prob_active='0.5') for i in range(1,101)]
    buffer=io.StringIO(newline='');writer=csv.DictWriter(buffer,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    artifact=buffer.getvalue().encode();(folder/'artifact.csv').write_bytes(artifact)
    manifest=dict(schema_version='v3_shared_data.manifest.v1',market='HK_CONNECT',stage_id='D1_PREMARKET',trade_date=source,row_count=100,source_id='hkconnect_0_2_frozen_prob_active',signal_date='20260924',captured_at='2026-09-24T17:30:43+08:00',artifact_relative=relative+'/artifact.csv',artifact_sha256=digest(artifact),provenance=dict(source_contract='tdx_vipdoc_71_day_prob_active'))
    raw=encoded(manifest);(folder/'manifest.json').write_bytes(raw)
    receipt=dict(schema_version='v3_shared_data.receipt.v1',status='READY',owner='v3_shared_data',role='HK_CONNECT_D1_TOP100_0_2',trade_date=source,run_id=run,artifact_sha256=digest(artifact),manifest_sha256=digest(raw),production_allowed=False,buy_gate_updated=False,orders_sent=False)
    (folder/'receipt.json').write_bytes(encoded(receipt))
    quotes=[dict(code=r['code'],update_time='2026-09-28 15:46:00',open_price=10.0,high_price=10.5,low_price=9.9,last_price=10.2,prev_close_price=10.0,turnover=1000.0,volume=100,window_start='2026-09-28 15:46:00',window_end='2026-09-28 15:46:00',bar_count=1,temporal_cutoff_safe=True) for r in rows]
    simulation=dict(clocks=['2026-09-29T00:00:05+08:00','2026-09-29T00:00:10+08:00','2026-09-29T00:00:10.500000+08:00','2026-09-29T00:00:11+08:00'],result=dict(status='READ_OK',rows=quotes,requested_code_count=100,completed_code_count=100,no_data_codes=[],cannot_confirm=[]))
    config=dict(capture_mode='PYTDX_LATE_OBSERVATION',owner_root=str(REPO/'V5/vendor/close_discovery_baseline'),python=str(Path(sys.executable).absolute()),state_root=str(state),universe_root=str(universe),source_manifest=str(HERE/'contracts/close_recapture_source_manifest.json'),timeout_seconds=30)
    request=dict(config=config,source_trade_date=source,research_cutoff=simulation['clocks'][0],execution_kind='SIMULATED',simulation=simulation)
    return request,ledger

class LateRegistrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name).resolve()
        spec=importlib.util.find_spec('v5_shadow.daily_close_recapture_owner')
        self.assertIsNotNone(spec,'M17 standalone adapter is missing')
        from v5_shadow import daily_close_recapture_owner as owner
        self.owner=owner;self.request,self.ledger=fixture(self.root)
    def tearDown(self):self.tmp.cleanup()
    def run_daily(self):
        return self.owner.run_close_recapture_daily(self.request,str(self.ledger),self.owner.bind_close_recapture_owner(self.request['config']))
    def test_real_process_chain_and_reuse_cold_reader(self):
        result=self.run_daily();self.assertEqual(result['status'],'SUCCEEDED',result)
        ref=result['state']['latest_success']['product_reference'];self.assertEqual(ref['source_trade_date'],'20260928');self.assertEqual(ref['plan_trade_date'],'20260929')
        self.assertNotEqual(ref['ledger_run_id'],ref['pool_run_id']);self.assertNotEqual(ref['producer_pid'],ref['reader_pid']);self.assertNotEqual(os.getpid(),ref['reader_pid'])
        self.assertEqual(ref['execution_kind'],'SIMULATED');self.assertFalse(ref['natural_verified']);self.assertEqual(len(ref['files']),4)
        before={p: p.read_bytes() for p in Path(self.request['config']['state_root']).rglob('*') if p.is_file()}
        reused=self.run_daily();self.assertEqual(reused['status'],'REUSED_SUCCESS');self.assertEqual(len(reused['state']['attempts']),1)
        self.assertEqual(before,{p:p.read_bytes() for p in before});self.assertFalse(list(Path(self.request['config']['state_root']).rglob('*1530*')))
        self.assertFalse(any(k.startswith(('ops.','domains.','apps.api.')) for k in sys.modules))
    def test_reused_success_corruption_is_not_ready_or_retried(self):
        self.assertEqual(self.run_daily()['status'],'SUCCEEDED')
        p=Path(self.request['config']['state_root'])/'workbench_research/20260928/close_recapture.candidates.json';p.write_bytes(b'{}')
        result=self.run_daily();self.assertEqual(result['status'],'BLOCKED_SAVED_PRODUCT_INVALID');self.assertEqual(len(result['state']['attempts']),1);self.assertEqual(p.read_bytes(),b'{}')
    def test_running_is_unknown_and_never_retried(self):
        from v5_shadow.run_ledger import claim_run
        binding=self.owner.bind_close_recapture_owner(self.request['config']);identity=self.owner.request_identity(self.request,binding)
        claim=claim_run(str(self.ledger),identity,max_attempts=1)
        result=self.run_daily();self.assertEqual(result['status'],'IN_PROGRESS_OR_OUTCOME_UNKNOWN');self.assertEqual(result['state']['attempts'][0]['run_id'],claim['run_id'])
        self.assertFalse((Path(self.request['config']['state_root'])/'workbench_research').exists())
    def test_unbound_real_execution_is_blocked_without_workers(self):
        self.request['execution_kind']='OWNER_VERIFIED';self.request.pop('simulation')
        result=self.run_daily();self.assertEqual(result['status'],'BLOCKED');self.assertIn('REAL_COLLECTOR_NOT_BOUND',result['state']['attempts'][0]['reason_codes']);self.assertFalse((Path(self.request['config']['state_root'])/'workbench_research').exists())
    def test_unknown_mode_rejected(self):
        self.request['config']['capture_mode']='UNKNOWN'
        with self.assertRaisesRegex(ValueError,'CAPTURE_MODE'):self.run_daily()
    def test_missing_pool_fails_closed(self):
        self.request['config']['universe_root']=str(self.root/'missing')
        result=self.run_daily();self.assertIn(result['status'],('BLOCKED','FAILED'));self.assertIsNone(result['state']['latest_success'])
    def test_window_before_155505_is_rejected(self):
        self.request['simulation']['clocks'][0]='2026-09-28T15:55:04+08:00';self.request['research_cutoff']=self.request['simulation']['clocks'][0]
        result=self.run_daily();self.assertEqual(result['status'],'FAILED');self.assertIsNone(result['state']['latest_success'])
    def test_input_envelope_substitution_rejected(self):
        binding=self.owner.bind_close_recapture_owner(self.request['config'])
        with self.assertRaisesRegex(ValueError,'ENVELOPE'):
            self.owner.verify_envelope({'ledger_run_id':'wrong'},self.request,'right')
    def test_source_manifest_drift_rejected_before_claim(self):
        manifest=json.loads(Path(self.request['config']['source_manifest']).read_text());manifest['files'][0]['sha256']='0'*64
        p=self.root/'source.json';p.write_text(json.dumps(manifest));self.request['config']['source_manifest']=str(p)
        with self.assertRaisesRegex(ValueError,'SOURCE'):self.run_daily()
        self.assertFalse((self.ledger/'manager_close_recapture').exists())
    def test_other_six_lanes_remain_registered(self):
        from v5_shadow.run_ledger import LANES
        self.assertEqual(LANES,{'announcement','us_mapping','rebound','manager_plan','hk_preselection','a_stage','manager_close_recapture'})
    def test_new_identity_keeps_previous_run_separate(self):
        first=self.run_daily();self.assertEqual(first['status'],'SUCCEEDED')
        self.request['simulation']['clocks'][0]='2026-09-29T00:00:06+08:00';self.request['research_cutoff']=self.request['simulation']['clocks'][0]
        second=self.run_daily();self.assertEqual(second['status'],'SUCCEEDED')
        self.assertNotEqual(first['state']['latest_success']['run_id'],second['state']['latest_success']['run_id'])
        self.assertEqual(second['state']['latest_success']['product_reference']['producer_status'],'ALREADY_EXISTS')
    def test_partial_coverage_is_not_upgraded(self):
        sim=self.request['simulation']['result'];sim['rows']=sim['rows'][:2];sim['completed_code_count']=2
        result=self.run_daily();self.assertEqual(result['status'],'SUCCEEDED')
        ref=result['state']['latest_success']['product_reference'];self.assertEqual(ref['owner_status'],'PARTIAL');self.assertEqual(ref['candidate_count'],2);self.assertIn('PYTDX_EXHQ_COVERAGE_INCOMPLETE',ref['cannot_confirm'])
    def test_current_or_previous_session_limit_preserved(self):
        self.request['simulation']['clocks'][0]='2026-09-30T16:00:00+08:00';self.request['research_cutoff']=self.request['simulation']['clocks'][0]
        result=self.run_daily();self.assertEqual(result['status'],'FAILED');self.assertIn('LATE_RECAPTURE_SOURCE_NOT_CURRENT_OR_PREVIOUS_SESSION',result['state']['attempts'][0]['reason_codes'])
    def test_external_pool_drift_blocks_saved_reuse(self):
        self.assertEqual(self.run_daily()['status'],'SUCCEEDED')
        p=next(Path(self.request['config']['universe_root']).rglob('artifact.csv'));p.write_bytes(b'changed')
        result=self.run_daily();self.assertEqual(result['status'],'BLOCKED_SAVED_PRODUCT_INVALID');self.assertEqual(len(result['state']['attempts']),1)
    def test_receipt_corruption_blocks_saved_reuse(self):
        self.assertEqual(self.run_daily()['status'],'SUCCEEDED')
        p=Path(self.request['config']['state_root'])/'workbench_research/20260928/close_recapture.receipt.json';p.write_bytes(b'{}')
        result=self.run_daily();self.assertEqual(result['status'],'BLOCKED_SAVED_PRODUCT_INVALID');self.assertEqual(p.read_bytes(),b'{}')
    def test_python_guards_deny_network_subprocess_and_reader_write(self):
        code="""import sys, pathlib, socket, subprocess
sys.path.insert(0,sys.argv[1])
from v5_shadow.daily_close_recapture_owner import _audit_guard
_audit_guard('reader',pathlib.Path(sys.argv[2]))
for action in (lambda:socket.socket(),lambda:subprocess.run([sys.executable,'-c','pass']),lambda:open(pathlib.Path(sys.argv[2])/'forbidden','w')):
    try:action()
    except PermissionError:pass
    else:raise AssertionError('guard failed')
"""
        done=subprocess.run([sys.executable,'-I','-B','-c',code,str(HERE/'src'),str(self.root)],capture_output=True,text=True)
        self.assertEqual(done.returncode,0,done.stderr);self.assertFalse((self.root/'forbidden').exists())
    def test_standalone_cli_full_chain(self):
        p=self.root/'request.json';p.write_text(json.dumps(self.request));script=HERE/'src/v5_shadow/daily_close_recapture_owner.py'
        done=subprocess.run([sys.executable,'-I','-B',str(script),'--request',str(p),'--ledger-root',str(self.ledger)],capture_output=True,text=True)
        self.assertEqual(done.returncode,0,done.stderr+done.stdout);self.assertEqual(json.loads(done.stdout)['status'],'SUCCEEDED')

if __name__=='__main__':unittest.main(verbosity=2)
