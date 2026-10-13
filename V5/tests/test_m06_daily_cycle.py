"""Daily candidate orchestration with original synthetic M06 source, never a model."""
import copy
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

BASE=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(BASE/'src'),str(BASE/'tests')]
from fixtures.hk_preselection_verified_factory import create_verified_fixture
from v5_shadow import daily_tick, daily_dispatch, p0_hk_preselection as m06, run_ledger, m06_readonly
from v5_shadow.digests import canonical_bytes,sha256_json


class M06DailyCycleTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.root=Path(temp.name).resolve();source=create_verified_fixture(self.root/'input')
        for name in ('assets','output','ledger','bundles','deliveries'):(self.root/name).mkdir()
        for name,marker,data in [('output','.v5-shadow-root',b'v5.shadow-root.v1\n'),
            ('ledger','.v5-daily-run-ledger',run_ledger.MARKER),
            ('bundles','.v5-daily-bundles',b'v5.daily-bundles.v1\n'),
            ('deliveries','.v5-m06-input-deliveries',b'v5.m06-input-deliveries.v1\n')]:
            (self.root/name/marker).write_bytes(data)
        python=Path(sys.executable).resolve()
        self.registration=dict(enabled=True,python_executable=str(python),python_sha256=hashlib.sha256(python.read_bytes()).hexdigest(),
            timeout_seconds=120,store_root=str(self.root/'input'),asset_root=str(self.root/'assets'),private_root=str(self.root/'output'))
        self.policy=dict(enabled=True,delivery_root=str(self.root/'deliveries'),
            full_day_window=dict(start='08:00',end='09:30'),half_day_window=None,execution_budget_seconds=360,
            execution_mode='RECORDED_INPUT_REPLAY',production_method='EXISTING_VERIFIED_POOL')
        self.config=dict(enabled=True,bundle_root=str(self.root/'bundles'),ledger_root=str(self.root/'ledger'),
            hk_preselection=self.registration,hk_preselection_daily=self.policy)
        self.delivery=dict(schema_version='v5.m06_daily_input_delivery.v1',status='READY',
            target_date='20261008',signal_date='20261007',eligibility_source_date='20260930',
            completed_at='2026-10-08T08:01:00+08:00',files={},source_files=source['files'])
        self.path=self.root/'deliveries/20261008.json';self.write_delivery()
        self.now=datetime.fromisoformat('2026-10-08T08:02:00+08:00')
    def write_delivery(self):self.path.write_bytes(canonical_bytes(self.delivery))
    def prepare(self):
        with patch.object(m06,'_utc_now',return_value=self.now,create=True):
            return m06.prepare_daily_candidate(self.config,self.now)
    def tick(self):
        with patch('v5_shadow.daily_tick.datetime') as a,patch('v5_shadow.daily_dispatch.datetime') as b,patch.object(m06,'_utc_now',return_value=self.now,create=True):
            a.now.return_value=self.now;b.now.return_value=self.now
            return daily_tick.tick(self.config)
    def inventory(self,folder):return {p.name:p.read_bytes() for p in (self.root/folder).iterdir() if p.is_file()}

    def test_original_calendar_previous_session_half_day_and_year_boundary(self):
        self.assertEqual(m06.calendar_day('20261012'),dict(state='FULL_TRADING_DAY',signal_date='20261009'))
        self.assertEqual(m06.calendar_day('20261224'),dict(state='HALF_TRADING_DAY_AM',signal_date='20261223'))
        self.assertEqual(m06.calendar_day('20270104')['state'],'UNKNOWN')
        self.assertEqual(m06.calendar_day('20261011')['state'],'NON_TRADING_DAY')
    def test_disabled_requires_no_paths_and_no_implicit_window(self):
        self.assertEqual(m06.prepare_daily_candidate({},self.now)['status'],'DISABLED')
        for key in ('full_day_window','half_day_window','execution_budget_seconds'):
            with self.subTest(key=key):
                value=copy.deepcopy(self.config);value['hk_preselection_daily'].pop(key)
                with self.assertRaises(ValueError):m06.prepare_daily_candidate(value,self.now)
    def test_missing_delivery_waits_without_freeze_or_claim(self):
        self.path.unlink();before=self.inventory('ledger')
        self.assertEqual(self.prepare()['status'],'WAITING_M06_INPUT_DELIVERY')
        self.assertEqual(self.inventory('ledger'),before)
        self.assertEqual(list((self.root/'bundles').iterdir()),[self.root/'bundles/.v5-daily-bundles'])
    def test_future_or_incomplete_delivery_is_not_admitted(self):
        for changes,reason in [({'completed_at':'2026-10-08T08:03:00+08:00'},'M06_INPUT_DELIVERY_FUTURE'),
                               ({'status':'RUNNING'},'M06_INPUT_DELIVERY_NOT_READY')]:
            self.delivery.update(changes);self.write_delivery()
            with self.subTest(reason=reason),self.assertRaisesRegex(ValueError,reason):self.prepare()
            self.delivery['completed_at']='2026-10-08T08:01:00+08:00';self.delivery['status']='READY'
        self.assertEqual(len(list((self.root/'ledger').iterdir())),1)
    def test_wrong_signal_and_target_reject_instead_of_subtracting_calendar_day(self):
        for key,value in [('signal_date','20261006'),('target_date','20261009'),('eligibility_source_date','20261009')]:
            original=self.delivery[key];self.delivery[key]=value;self.write_delivery()
            with self.subTest(key=key),self.assertRaises(ValueError):self.prepare()
            self.delivery[key]=original
    def test_delivery_completion_cannot_precede_original_pool_receipt(self):
        self.delivery['completed_at']='2026-10-08T07:59:30+08:00';self.write_delivery()
        with self.assertRaisesRegex(ValueError,'M06_INPUT_AFTER_DELIVERY_COMPLETION'):self.prepare()
    def test_window_early_late_budget_and_unconfigured_half_day_do_not_freeze(self):
        for stamp,status in [('2026-10-08T07:59:00+08:00','WAITING_M06_WINDOW'),
            ('2026-10-08T09:30:00+08:00','MISSED_M06_WINDOW_NO_BACKFILL'),
            ('2026-10-08T09:25:00+08:00','M06_EXECUTION_BUDGET_INSUFFICIENT'),
            ('2026-12-24T08:02:00+08:00','M06_HALF_DAY_NOT_ENABLED'),
            ('2027-01-04T08:02:00+08:00','M06_CALENDAR_UNKNOWN')]:
            self.now=datetime.fromisoformat(stamp)
            with self.subTest(stamp=stamp):self.assertEqual(self.prepare()['status'],status)
        self.assertEqual(len(list((self.root/'bundles').iterdir())),1)
    def test_delivery_root_and_file_symlinks_rejected(self):
        original=self.path.read_bytes();self.path.unlink();outside=self.root/'elsewhere.json';outside.write_bytes(original);self.path.symlink_to(outside)
        with self.assertRaises((ValueError,OSError)):self.prepare()
    def test_missing_declared_input_waits_without_ledger_claim(self):
        path=next((self.root/'input/runs').rglob('artifact.csv'));path.rename(path.with_suffix('.not-delivered'))
        self.assertEqual(self.prepare()['status'],'WAITING_M06_INPUT_FILES')
        self.assertEqual(len(list((self.root/'ledger').iterdir())),1)
    def test_panel_day_is_exact_signal_not_future_or_stale(self):
        assets=self.root/'assets';(assets/'panel').mkdir()
        (assets/'panel_latest.json').write_bytes(canonical_bytes(dict(manifest_relative='panel/manifest.json')))
        for day in ('20261006','20261008'):
            (assets/'panel/manifest.json').write_bytes(canonical_bytes(dict(panel_max_date=day)))
            self.delivery['files']={str(p.relative_to(assets)):hashlib.sha256(p.read_bytes()).hexdigest() for p in assets.rglob('*') if p.is_file()}
            self.write_delivery()
            with self.subTest(day=day),self.assertRaisesRegex(ValueError,'M06_PANEL_SIGNAL_DATE_MISMATCH'):self.prepare()
    def test_explicit_half_day_window_uses_original_half_session(self):
        source=create_verified_fixture(self.root/'half-input',target='20261224',signal='20261223',eligibility='20261223')
        self.registration['store_root']=str(self.root/'half-input')
        self.delivery.update(target_date='20261224',signal_date='20261223',eligibility_source_date='20261223',
            source_files=source['files'],completed_at='2026-12-24T08:01:00+08:00')
        self.path=self.root/'deliveries/20261224.json';self.write_delivery()
        self.policy['half_day_window']=dict(start='08:00',end='09:00');self.now=datetime.fromisoformat('2026-12-24T08:02:00+08:00')
        result=self.prepare();self.assertTrue(result['job']['half_day_bound'])
        self.assertEqual(result['job']['deadline'],'2026-12-24T09:00:00+08:00')
    def test_budget_is_checked_again_after_inspection_before_freeze(self):
        with patch.object(m06,'_utc_now',return_value=datetime.fromisoformat('2026-10-08T09:25:00+08:00')):
            result=m06.prepare_daily_candidate(self.config,self.now)
        self.assertEqual(result['status'],'M06_EXECUTION_BUDGET_INSUFFICIENT')
        self.assertEqual(list((self.root/'bundles').glob('.m06-????????.json')),[])
    def test_budget_is_rechecked_after_dispatch_inspection_before_claim(self):
        prepared=self.prepare()
        with patch.object(m06,'_utc_now',return_value=datetime.fromisoformat('2026-10-08T09:25:00+08:00')):
            reason=m06.admission_reason(prepared['job'],prepared['binding'],self.now,self.config['ledger_root'])
        self.assertEqual(reason,'M06_EXECUTION_BUDGET_INSUFFICIENT')
        self.assertIsNone(run_ledger.read_run(self.config['ledger_root'],prepared['job']['identity']))
    def test_repeated_ticks_freeze_identical_request_cutoffs_and_p0_identity(self):
        first=self.prepare();self.assertEqual(first['status'],'PREPARED_M06_CANDIDATE')
        before=self.inventory('bundles');self.now+=timedelta(minutes=5);second=self.prepare()
        self.assertEqual(first['job'],second['job']);self.assertEqual(before,self.inventory('bundles'))
        request=first['job']['owner_request']
        self.assertEqual(request['admission_cutoff'],'2026-10-08T08:02:00+08:00')
        self.assertEqual(request['completion_cutoff'],'2026-10-08T09:30:00+08:00')
        self.assertEqual(first['job']['identity']['research_cutoff'],request['admission_cutoff'])
        self.assertEqual(first['binding']['owner_snapshot']['computation_identity']['research_cutoff'],request['completion_cutoff'])
    def test_same_day_delivery_config_or_dependency_change_never_rekeys_success(self):
        first=self.prepare();before=self.inventory('bundles')
        self.delivery['completed_at']='2026-10-08T08:01:01+08:00';self.write_delivery()
        with self.assertRaisesRegex(ValueError,'M06_FROZEN_INPUT_CHANGED'):self.prepare()
        self.delivery['completed_at']='2026-10-08T08:01:00+08:00';self.write_delivery()
        self.policy['execution_budget_seconds']=361
        with self.assertRaisesRegex(ValueError,'M06_FROZEN_CONFIG_CHANGED'):self.prepare()
        self.policy['execution_budget_seconds']=360
        original=m06.prepare_job
        def drift(*args):
            job,binding=original(*args);job['identity']['dependency_sha256']='0'*64;return job,binding
        with patch.object(m06,'prepare_job',side_effect=drift),self.assertRaisesRegex(ValueError,'M06_FROZEN_BINDING_CHANGED'):self.prepare()
        self.assertEqual(before,self.inventory('bundles'));self.assertIsNone(run_ledger.read_run(self.config['ledger_root'],first['job']['identity']))
    def test_concurrent_first_freeze_has_one_identical_bundle(self):
        with patch.object(m06,'_utc_now',return_value=self.now,create=True),ThreadPoolExecutor(max_workers=2) as pool:
            rows=list(pool.map(lambda _:m06.prepare_daily_candidate(self.config,self.now),range(2)))
        self.assertEqual(rows[0]['job'],rows[1]['job'])
        self.assertEqual(len(list((self.root/'bundles').glob('.m06-????????.json'))),1)
    def test_changing_p0_ledger_root_cannot_bypass_a_frozen_claim(self):
        self.prepare();other=self.root/'other-ledger';other.mkdir();(other/'.v5-daily-run-ledger').write_bytes(run_ledger.MARKER)
        self.config['ledger_root']=str(other)
        with self.assertRaisesRegex(ValueError,'M06_FROZEN_CONFIG_CHANGED'):self.prepare()
    def test_candidate_state_roots_cannot_write_inside_source_inputs(self):
        bundles=self.root/'input/bundles';bundles.mkdir();(bundles/'.v5-daily-bundles').write_bytes(b'v5.daily-bundles.v1\n')
        self.config['bundle_root']=str(bundles)
        with self.assertRaisesRegex(ValueError,'M06_DAILY_ROOT_OVERLAP'):self.prepare()
    def test_candidate_identity_pins_shared_atomic_io_code(self):
        self.assertIn('module_api.py',m06._code_manifest())
        self.assertIn('module_artifacts.py',m06._code_manifest())
    def test_cli_config_accepts_nested_daily_and_rejects_ambiguous_shape(self):
        self.assertEqual(daily_tick.daily_config({'daily':self.config,'runtime_root':'/unused'}),self.config)
        self.assertEqual(daily_tick.daily_config(self.config),self.config)
        with self.assertRaises(ValueError):daily_tick.daily_config({'daily':self.config,'enabled':True})
    def test_tick_original_owner_dual_ledger_success_promotion_and_reuse(self):
        first=self.tick();row=first['lanes'][0]
        self.assertEqual(row['status'],'SUCCEEDED',first)
        self.assertEqual(row['current_success']['status'],'CURRENT_SUCCESS_PROMOTED',row)
        binding=m06._current_binding(self.config)
        pointer=m06_readonly.read_current_success(binding)
        self.assertEqual(pointer['p0_run_id'],row['state']['latest_success']['run_id'])
        self.assertNotEqual(pointer['p0_run_id'],pointer['m06_run_id'])
        m06_readonly.validate_current_success(binding,pointer)
        api_root=self.root/'api';api_root.mkdir();(api_root/'.v5-module-root').write_bytes(b'v5.module-root.v1:source_bundle\n')
        api_config=dict(schema_version='v5.module_api.v1',module_id='source_bundle',release_id='SYNTHETIC_CYCLE',
            data_root=str(api_root),routes=[m06_readonly.ROUTE],m06_hk_preselection_binding=binding)
        record,_=m06_readonly.read_record(api_config,{})
        self.assertEqual(record['payload']['committed_reference'],pointer['committed_reference'])
        self.assertEqual(len(record['payload']['artifact']['rows']),100)
        self.assertTrue(record['payload']['fixture_only'])
        self.now+=timedelta(minutes=5);second=self.tick()['lanes'][0]
        self.assertEqual(second['status'],'REUSED_SUCCESS',second)
        self.assertEqual(second['current_success']['status'],'REUSED_CURRENT_SUCCESS')
        self.assertEqual(len(second['state']['attempts']),1)
        self.assertEqual(pointer,m06_readonly.read_current_success(binding))
        self.path.unlink();third=self.tick()['lanes'][0]
        self.assertEqual(third['status'],'WAITING_M06_INPUT_DELIVERY')
        self.assertEqual(pointer,m06_readonly.read_current_success(binding))
    def test_unknown_outcome_cannot_repeat_original_owner_or_publish_pointer(self):
        original=m06.run_owner;calls=[]
        def lost(*args,**kwargs):
            calls.append(args[1]);original(*args,**kwargs);raise TimeoutError('SYNTHETIC_LOST_REPLY')
        with patch.object(m06,'run_owner',side_effect=lost):
            first=self.tick()['lanes'][0];self.now+=timedelta(minutes=5);second=self.tick()['lanes'][0]
        self.assertEqual(first['status'],'OUTCOME_UNKNOWN_NO_AUTOMATIC_RETRY',first)
        self.assertEqual(second['status'],'IN_PROGRESS_OR_OUTCOME_UNKNOWN',second)
        self.assertEqual(len(calls),1);self.assertFalse((self.root/'output/.m06-current-success.json').exists())

    def test_cas_and_late_promotion_preserve_pointer_without_new_owner(self):
        candidate=self.prepare()
        with patch('v5_shadow.daily_dispatch.datetime') as clock,patch.object(m06,'_utc_now',return_value=self.now):
            clock.now.return_value=self.now
            row=daily_dispatch.dispatch_due([candidate['job']],{'hk_preselection':candidate['binding']},self.config['ledger_root'])['lanes'][0]
        self.assertEqual(row['status'],'SUCCEEDED',row)
        stale=copy.deepcopy(candidate['frozen']);stale['expected_current_sha256']='0'*64
        with patch.object(m06,'_utc_now',return_value=self.now):
            rejected=m06.promote_current_success(self.config,dict(candidate,frozen=stale),row)
        self.assertEqual(rejected['status'],'CURRENT_SUCCESS_CAS_MISMATCH')
        self.assertFalse((self.root/'output/.m06-current-success.json').exists())
        with patch.object(m06,'_utc_now',return_value=datetime.fromisoformat('2026-10-08T09:30:00+08:00')):
            late=m06.promote_current_success(self.config,candidate,row)
        self.assertEqual(late['status'],'CURRENT_SUCCESS_LATE_NOT_PROMOTED')
        self.assertFalse((self.root/'output/.m06-current-success.json').exists())
        with patch.object(m06,'_utc_now',return_value=self.now):
            success=m06.promote_current_success(self.config,candidate,row)
        self.assertEqual(success['status'],'CURRENT_SUCCESS_PROMOTED')
        raw=(self.root/'output/.m06-current-success.json').read_bytes()
        for status in ('FAILED','BLOCKED','IN_PROGRESS_OR_OUTCOME_UNKNOWN','OUTCOME_UNKNOWN_NO_AUTOMATIC_RETRY'):
            self.assertEqual(m06.promote_current_success(self.config,candidate,dict(status=status))['status'],'CURRENT_SUCCESS_UNCHANGED')
            self.assertEqual((self.root/'output/.m06-current-success.json').read_bytes(),raw)

    def test_candidate_does_not_rekey_other_lanes_or_run_duplicate_explicit_slot(self):
        (self.root/'bundles/20261008.json').write_bytes(canonical_bytes(dict(target_date='20261008',jobs=[])))
        identities=[]
        def capture(jobs,bindings,root):
            identities.append({name:{k:v for k,v in binding.items() if k.endswith('_sha256')} for name,binding in bindings.items() if name!='hk_preselection'})
            return dict(status='DISPATCH_ATTEMPT_ONLY',lanes=[],natural_verified=False)
        with patch('v5_shadow.daily_tick.dispatch_due',side_effect=capture):
            self.policy['enabled']=False;self.tick()
            self.policy['enabled']=True;self.path.unlink();self.tick()
        self.assertEqual(identities[0],identities[1])
        (self.root/'bundles/20261008.json').write_bytes(canonical_bytes(dict(target_date='20261008',jobs=[dict(lane='hk_preselection')])))
        with patch.object(m06,'prepare_job',side_effect=AssertionError('must not prepare duplicate')):
            self.assertEqual(self.tick()['lanes'][0]['status'],'BLOCKED_M06_DUPLICATE_SLOT')


if __name__=='__main__':unittest.main(verbosity=2)
