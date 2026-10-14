"""P0 registration-only integration. All market inputs are synthetic temp fixtures."""
import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / 'src'))
sys.path.insert(0, str(HERE / 'tests'))
from test_daily_close_recapture_owner import fixture, digest
from v5_shadow import main_registry, main_runtime, daily_dispatch, run_ledger

class RegistrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.request, self.ledger = fixture(self.root)
        folder = next(Path(self.request['config']['universe_root']).rglob('manifest.json')).parent
        manifest = json.loads((folder/'manifest.json').read_bytes())
        self.pool = dict(owner='v3_shared_data',role='HK_CONNECT_D1_TOP100_0_2',trade_date='20260928',
            signal_date=manifest['signal_date'],source_id=manifest['source_id'],run_id=folder.name,
            artifact_ref=manifest['artifact_relative'],artifact_sha256=manifest['artifact_sha256'],
            manifest_ref=str(folder.relative_to(Path(self.request['config']['universe_root'])/'.runtime/data'))+'/manifest.json',
            manifest_sha256=digest((folder/'manifest.json').read_bytes()),
            receipt_ref=str(folder.relative_to(Path(self.request['config']['universe_root'])/'.runtime/data'))+'/receipt.json',
            receipt_sha256=digest((folder/'receipt.json').read_bytes()),captured_at=manifest['captured_at'],row_count=100)
        self.registration = dict(enabled=True,execution_kind='SIMULATED',config=self.request['config'],pool_reference=self.pool)
        self.job = dict(lane='manager_close_recapture',owner_request=self.request,
            scheduled_at='2026-09-29T00:00:00+08:00',deadline='2026-09-29T00:10:00+08:00',max_attempts=1)
        self.now = datetime.fromisoformat('2026-09-29T00:00:06+08:00')

    def api(self):
        import importlib.util
        self.assertIsNotNone(importlib.util.find_spec("v5_shadow.p0_close_recapture"), "P0 M17 execution registration missing")
        from v5_shadow import p0_close_recapture
        return p0_close_recapture

    def prepared(self):
        return self.api().prepare_job(self.job,self.registration,'20260929')

    def dispatch(self, job, binding):
        with patch('v5_shadow.daily_dispatch.datetime') as clock:
            clock.now.return_value = self.now
            return daily_dispatch.dispatch_due([job],{'manager_close_recapture':binding},str(self.ledger))['lanes'][0]

    def test_registry_contract_is_callable_but_not_naturally_verified(self):
        row=main_registry.registry_by_id()['M17_CLOSE_RECAPTURE']
        self.assertEqual(row.status,'READY')
        self.assertEqual(row.runtime,'daily_tick')
        self.assertEqual(len(main_registry.MODULE_REGISTRY),18)

    def test_config_default_is_disabled_and_enabled_invalid_is_blocked(self):
        c=dict(runtime_root=str(self.root/'runtime'),composition='unused',module_api={},daily={})
        data=self.root/'api-data';data.mkdir()
        (data/'.v5-module-root').write_text('v5.module-root.v1:p0_test\n')
        c['module_api']=dict(schema_version='v5.module_api.v1',module_id='p0_test',release_id='SYNTHETIC',data_root=str(data),routes=[])
        self.assertIn('close_recapture',main_runtime.validate_config(c),'P0 config registration missing')
        self.assertEqual(main_runtime.validate_config(c)['close_recapture']['status'],'DISABLED')
        c['daily']['close_recapture']={'enabled':True}
        self.assertEqual(main_runtime.validate_config(c)['close_recapture']['status'],'BLOCKED_M17_REGISTRATION')
        self.assertFalse((self.root/'runtime').exists())

    def test_exact_mode_roots_manifest_pool_and_identity_are_bound(self):
        job,binding=self.prepared()
        from v5_shadow.daily_close_recapture_owner import run_close_recapture_owner
        self.assertIs(binding['invoke'],run_close_recapture_owner)
        self.assertEqual(job['identity']['target_date'],'20260928')
        self.assertEqual(set(job['identity']),{'lane','target_date','input_sha256','research_cutoff','code_sha256','config_sha256','dependency_sha256'})
        self.assertEqual(binding['pool_reference'],self.pool)
        for field in ('execution_kind','pool_reference'):
            bad=copy.deepcopy(self.registration);bad.pop(field)
            self.assertEqual(self.api().validate_registration(bad)['status'],'BLOCKED_M17_REGISTRATION')
        self.assertEqual(self.api().validate_registration({'enabled':False})['status'],'DISABLED')

    def test_slot_is_explicit_no_morning_defaults_or_multiple_attempts(self):
        for field in ('scheduled_at','deadline','max_attempts'):
            bad=dict(self.job);bad.pop(field)
            with self.assertRaises(ValueError):self.api().prepare_job(bad,self.registration,'20260929')
        bad=dict(self.job,max_attempts=2)
        with self.assertRaises(ValueError):self.api().prepare_job(bad,self.registration,'20260929')

    def test_real_missing_binding_blocks_before_claim_or_worker(self):
        self.request['execution_kind']='OWNER_VERIFIED';self.request.pop('simulation')
        self.registration['execution_kind']='OWNER_VERIFIED'
        result=self.api().validate_registration(self.registration)
        self.assertEqual(result['status'],'BLOCKED_M17_REGISTRATION')
        self.assertIn('REAL_COLLECTOR_NOT_BOUND',result['reason_codes'])
        self.assertEqual(list(self.ledger.iterdir()),[self.ledger/'.v5-daily-run-ledger'])

    def test_request_config_and_execution_kind_cannot_cross_bind(self):
        for mutate in (lambda r:r.update(execution_kind='OWNER_VERIFIED'),lambda r:r['config'].update(timeout_seconds=31)):
            req=copy.deepcopy(self.request);mutate(req)
            with self.assertRaises(ValueError):self.api().prepare_job(dict(self.job,owner_request=req),self.registration,'20260929')

    def test_previous_source_dispatch_real_process_cold_reuse_and_pool_corruption(self):
        job,binding=self.prepared();result=self.dispatch(job,binding)
        self.assertEqual(result['status'],'SUCCEEDED',result)
        saved=result['state']['latest_success'];ref=saved['product_reference']
        self.assertEqual(ref['pool'],self.pool);self.assertEqual(ref['execution_kind'],'SIMULATED')
        self.assertFalse(saved['natural_verified']);self.assertNotEqual(ref['producer_pid'],ref['reader_pid'])
        self.assertEqual(self.dispatch(job,binding)['status'],'REUSED_SUCCESS')
        path=Path(self.request['config']['state_root'])/'workbench_research/20260928/close_recapture.candidates.json'
        path.write_bytes(b'{}')
        failed=self.dispatch(job,binding)
        self.assertEqual(failed['status'],'BLOCKED_SAVED_PRODUCT_INVALID')
        self.assertEqual(failed['state']['latest_success'],saved)
        self.assertEqual(len(failed['state']['attempts']),1)

    def test_lost_call_stays_running_and_does_not_retry(self):
        job,binding=self.prepared()
        with patch('v5_shadow.daily_close_recapture_owner._process',side_effect=TimeoutError):
            first=self.dispatch(job,binding);second=self.dispatch(job,binding)
        self.assertEqual(first['status'],'OUTCOME_UNKNOWN_NO_AUTOMATIC_RETRY')
        self.assertEqual(second['status'],'IN_PROGRESS_OR_OUTCOME_UNKNOWN')
        self.assertEqual(len(second['state']['attempts']),1)
        self.assertEqual(second['state']['attempts'][0]['status'],'RUNNING')

    def test_pool_change_rejected_before_claim(self):
        job,binding=self.prepared()
        path=Path(self.request['config']['universe_root'])/'.runtime/data'/self.pool['receipt_ref']
        path.write_bytes(b'{}')
        self.assertEqual(self.dispatch(job,binding)['status'],'BLOCKED_M17_REGISTRATION')
        self.assertIsNone(run_ledger.read_run(str(self.ledger),job['identity']))

    def test_old_source_and_same_day_before_close_rejected(self):
        job,binding=self.prepared();self.now=datetime.fromisoformat('2026-09-30T00:00:06+08:00')
        self.assertEqual(self.dispatch(job,binding)['status'],'M17_SOURCE_NOT_CURRENT_OR_PREVIOUS_SESSION')
        self.now=datetime.fromisoformat('2026-09-28T15:55:04+08:00')
        self.assertEqual(self.dispatch(job,binding)['status'],'M17_SOURCE_WINDOW_NOT_COMPLETE')

    def test_tick_entrypoint_uses_explicit_late_job_and_source_date(self):
        from v5_shadow import daily_tick
        bundle=self.root/'bundles';bundle.mkdir();(bundle/'.v5-daily-bundles').write_bytes(b'v5.daily-bundles.v1\n')
        (bundle/'20260929.json').write_text(json.dumps(dict(target_date='20260929',jobs=[self.job])))
        config=dict(enabled=True,bundle_root=str(bundle),ledger_root=str(self.ledger),close_recapture=self.registration)
        with patch('v5_shadow.daily_tick.datetime') as tick_clock,patch('v5_shadow.daily_dispatch.datetime') as dispatch_clock:
            tick_clock.now.return_value=self.now;dispatch_clock.now.return_value=self.now
            result=daily_tick.tick(config)
        self.assertEqual(result['lanes'][0]['status'],'SUCCEEDED',result)
        self.assertEqual(result['lanes'][0]['state']['identity']['target_date'],'20260928')
        self.assertEqual(result['manager']['status'],'BLOCKED_POST_OWNER_REQUEST_MISSING')
        self.assertFalse(result['natural_verified'])

    def test_real_config_can_bind_with_existing_runtime_boundary_verified(self):
        from v5_shadow import daily_close_recapture_owner as owner
        self.registration['execution_kind']='OWNER_VERIFIED'
        config=self.registration['config'];config['timeout_seconds']=420
        (Path(config['state_root'])/'.v5-m17-close-root').write_bytes(owner.REAL_MARKER)
        config['real_binding']=dict(active_capture_mode=owner.MODE,pytdx_python=config['python'],
            pytdx_python_sha256=digest(Path(config['python']).resolve().read_bytes()),
            pytdx_exhq_sha256=digest(b'SYNTHETIC_RUNTIME_BOUNDARY'),
            provider_root=str(Path(config['owner_root'])/'upstreams/v3_shared_data'),
            state_root=config['state_root'],universe_root=config['universe_root'])
        # Read-only runtime availability is the only substituted boundary. No capture.
        with patch.object(owner,'_real_runtime_ready',return_value=True):
            result=self.api().validate_registration(self.registration)
        self.assertEqual(result['status'],'BOUND_NOT_NATURALLY_VERIFIED')
        self.assertFalse(result['natural_verified'])
        with patch.object(owner,'_real_runtime_ready',return_value=False):
            self.assertIn('M17_PYTDX_RUNTIME_NOT_BOUND',self.api().validate_registration(self.registration)['reason_codes'])
        config['real_binding']['active_capture_mode']='UNBOUND'
        self.assertIn('M17_REAL_ACTIVE_MODE_NOT_BOUND',self.api().validate_registration(self.registration)['reason_codes'])
        self.assertFalse((Path(config['state_root'])/'workbench_research').exists())

    def test_success_with_changed_bound_pool_keeps_unknown_claim(self):
        from v5_shadow import daily_close_recapture_owner as owner
        job,binding=self.prepared();original=owner._process
        def changed_reader(role,*args):
            value=original(role,*args)
            if role=='reader':value['pool']=dict(value['pool'],run_id='SYNTHETIC_CHANGED_POOL')
            return value
        with patch.object(owner,'_process',side_effect=changed_reader):result=self.dispatch(job,binding)
        self.assertEqual(result['status'],'OUTCOME_UNKNOWN_NO_AUTOMATIC_RETRY')
        state=run_ledger.read_run(str(self.ledger),job['identity'])
        self.assertIsNone(state['latest_success']);self.assertEqual(state['attempts'][0]['status'],'RUNNING')

    def test_terminal_owner_failure_finishes_once_without_retry(self):
        from v5_shadow import daily_close_recapture_owner as owner
        job,binding=self.prepared()
        with patch.object(owner,'_process',return_value=dict(owner_status='INPUT_MISSING',reason='SYNTHETIC_OWNER_INPUT_MISSING')):
            first=self.dispatch(job,binding);second=self.dispatch(job,binding)
        self.assertEqual(first['status'],'BLOCKED');self.assertEqual(second['status'],'RETRY_BLOCKED')
        self.assertEqual(len(second['state']['attempts']),1)

    def test_source_drift_rejected_before_calendar_admission(self):
        import shutil
        isolated=self.root/'frozen-owner';shutil.copytree(self.request['config']['owner_root'],isolated)
        self.request['config']['owner_root']=str(isolated)
        job,binding=self.prepared()
        calendar=isolated/'contracts/trading_calendar.py'
        calendar.write_bytes(calendar.read_bytes()+b'\n# SYNTHETIC_SOURCE_DRIFT\n')
        with self.assertRaisesRegex(ValueError,'M17_SOURCE_BYTES_MISMATCH'):
            self.api().admission_reason(job,binding,self.now)

    def test_pool_reference_metadata_mismatch_blocks_before_capture(self):
        self.registration['pool_reference']['signal_date']='20260923'
        self.assertEqual(self.api().validate_registration(self.registration)['status'],'BLOCKED_M17_REGISTRATION')
        self.assertFalse((Path(self.request['config']['state_root'])/'workbench_research').exists())

    def test_m17_configuration_does_not_rekey_other_owner_success(self):
        from v5_shadow import daily_tick
        bundle=self.root/'bundles';bundle.mkdir();(bundle/'.v5-daily-bundles').write_bytes(b'v5.daily-bundles.v1\n')
        cutoff=self.request['research_cutoff']
        job=dict(self.job,lane='announcement',owner_request=dict(binding=dict(target_date='20260929'),cutoff=cutoff),research_cutoff=cutoff)
        (bundle/'20260929.json').write_text(json.dumps(dict(target_date='20260929',jobs=[job])))
        config=dict(enabled=True,bundle_root=str(bundle),ledger_root=str(self.ledger))
        receipt=dict(status='SUCCEEDED',product_reference=dict(evidence='SYNTHETIC_EXISTING_OWNER'),readback_verified=True,retry_safe_without_external_effect=False,reason_codes=[])
        with patch('v5_shadow.daily_tick.datetime') as a,patch('v5_shadow.daily_dispatch.datetime') as b,patch('v5_shadow.daily_tick.read_announcement_owner',return_value=receipt):
            a.now.return_value=self.now;b.now.return_value=self.now
            first=daily_tick.tick(config)['lanes'][0]
            config['close_recapture']=self.registration
            second=daily_tick.tick(config)['lanes'][0]
        self.assertEqual(first['status'],'SUCCEEDED')
        self.assertEqual(second['status'],'REUSED_SUCCESS')
        self.assertEqual(second['state']['latest_success']['run_id'],first['state']['latest_success']['run_id'])

    def test_all_six_existing_ledger_lanes_preserved(self):
        job,_=self.prepared()
        self.assertEqual(run_ledger.LANES,{'announcement','us_mapping','rebound','manager_plan','hk_preselection','a_stage','manager_close_recapture'})
        for lane in run_ledger.LANES-{'manager_close_recapture'}:
            identity=dict(job['identity'],lane=lane)
            claim=run_ledger.claim_run(str(self.ledger),identity,max_attempts=1)
            receipt=dict(status='BLOCKED',product_reference={},readback_verified=False,retry_safe_without_external_effect=False,reason_codes=['SYNTHETIC_TEST'])
            state=run_ledger.finish_run(str(self.ledger),claim,receipt)
            self.assertEqual(run_ledger.read_run(str(self.ledger),identity),state)

if __name__=='__main__':unittest.main(verbosity=2)
