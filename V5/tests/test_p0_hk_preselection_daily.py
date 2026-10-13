"""New P0 -> fixed M06 daily -> cold reader integration; synthetic input only."""
import copy
from datetime import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

BASE=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(BASE/'src'),str(BASE/'tests')]
from fixtures.hk_preselection_verified_factory import create_verified_fixture
from v5_shadow import daily_tick,daily_dispatch,run_ledger,main_runtime,main_registry
from v5_shadow.digests import sha256_json

class M06DailyIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve()
        source=create_verified_fixture(self.root/'input')
        for name in ('assets','output','ledger','bundles'):(self.root/name).mkdir()
        (self.root/'output/.v5-shadow-root').write_bytes(b'v5.shadow-root.v1\n')
        (self.root/'ledger/.v5-daily-run-ledger').write_bytes(run_ledger.MARKER)
        (self.root/'bundles/.v5-daily-bundles').write_bytes(b'v5.daily-bundles.v1\n')
        self.registration=dict(enabled=True,python_executable=str(Path(sys.executable).resolve()),
            python_sha256=hashlib.sha256(Path(sys.executable).resolve().read_bytes()).hexdigest(),timeout_seconds=120,
            store_root=str(self.root/'input'),asset_root=str(self.root/'assets'),private_root=str(self.root/'output'))
        self.request=dict(signal_date='20261007',target_date='20261008',eligibility_source_date='20260930',
            admission_cutoff='2026-10-08T08:01:00+08:00',completion_cutoff='2026-10-08T09:20:00+08:00',
            files={},source_files=source['files'],execution_mode='RECORDED_INPUT_REPLAY',production_method='EXISTING_VERIFIED_POOL')
        self.job=dict(lane='hk_preselection',owner_request=self.request,scheduled_at='2026-10-08T08:00:00+08:00',
            deadline='2026-10-08T09:30:00+08:00',half_day_bound=True,max_attempts=1)
        self.now=datetime.fromisoformat('2026-10-08T08:02:00+08:00')
        self.config=dict(enabled=True,bundle_root=str(self.root/'bundles'),ledger_root=str(self.root/'ledger'),hk_preselection=self.registration)
    def api(self):
        self.assertIsNotNone(importlib.util.find_spec('v5_shadow.p0_hk_preselection'),'M06 daily execution binding missing')
        from v5_shadow import p0_hk_preselection
        return p0_hk_preselection
    def prepared(self):return self.api().prepare_job(self.job,self.registration,'20261008')
    def dispatch(self,job,binding):
        with patch('v5_shadow.daily_dispatch.datetime') as clock:
            clock.now.return_value=self.now
            return daily_dispatch.dispatch_due([job],{'hk_preselection':binding},str(self.root/'ledger'))['lanes'][0]
    def tick(self):
        (self.root/'bundles/20261008.json').write_text(json.dumps(dict(target_date='20261008',jobs=[self.job])))
        with patch('v5_shadow.daily_tick.datetime') as a,patch('v5_shadow.daily_dispatch.datetime') as b:
            a.now.return_value=self.now;b.now.return_value=self.now
            return daily_tick.tick(self.config)
    def test_registry_and_disabled_config(self):
        row=main_registry.registry_by_id()['M06_HK_PRESELECTION']
        self.assertEqual(row.runtime,'daily_tick')
        c=dict(runtime_root='/unused',composition='/unused',module_api={},daily={})
        self.assertEqual(main_runtime.validate_config(c)['hk_preselection']['status'],'DISABLED')
    def test_original_owner_and_fresh_reader_finish_both_exact_ledgers(self):
        job,binding=self.prepared();first=self.dispatch(job,binding)
        self.assertEqual(first['status'],'SUCCEEDED',first)
        state=first['state'];ref=state['latest_success']['product_reference']
        self.assertEqual(ref['p0_ledger_run_id'],state['latest_success']['run_id'])
        self.assertNotEqual(ref['m06_ledger_run_id'],ref['p0_ledger_run_id'])
        self.assertNotEqual(ref['committed_reference']['computation_sha256'],ref['m06_ledger_run_id'])
        self.assertEqual(ref['m06_computation_identity'],binding['owner_snapshot']['computation_identity'])
        self.assertEqual(ref['committed_reference']['producer_computation_identity'],ref['m06_computation_identity'])
        self.assertNotEqual(ref['producer_pid'],ref['reader_pid'])
        self.assertEqual(ref['row_count'],100);self.assertTrue(ref['fixture_only'])
        self.assertFalse(ref['producer_model_weights_reverified']);self.assertFalse(ref['reader_model_weights_reverified'])
        self.assertEqual(ref['production_method'],'EXISTING_VERIFIED_POOL')
        self.assertEqual(run_ledger.read_run(str(self.root/'ledger'),job['identity']),state)
        second=self.dispatch(job,binding)
        self.assertEqual(second['status'],'REUSED_SUCCESS',second)
        self.assertEqual(second['state']['latest_success'],state['latest_success'])
        self.assertEqual(len(second['state']['attempts']),1)
    def test_tick_uses_explicit_slot_and_distinct_cutoffs(self):
        result=self.tick();row=result['lanes'][0]
        self.assertEqual(row['status'],'SUCCEEDED',result)
        self.assertEqual(row['state']['identity']['research_cutoff'],self.request['admission_cutoff'])
        ref=row['state']['latest_success']['product_reference']
        self.assertEqual(ref['committed_reference']['research_cutoff'],self.request['completion_cutoff'])
        self.assertFalse(result['natural_verified'])
    def test_no_implicit_slot_or_missing_request_field_or_extra_argument(self):
        for key in ('scheduled_at','deadline','half_day_bound','max_attempts'):
            job=dict(self.job);job.pop(key)
            with self.subTest(key=key),self.assertRaises(ValueError):self.api().prepare_job(job,self.registration,'20261008')
        for key in self.request:
            req=dict(self.request);req.pop(key)
            with self.subTest(key=key),self.assertRaises(ValueError):self.api().prepare_job(dict(self.job,owner_request=req),self.registration,'20261008')
        with self.assertRaises(ValueError):self.api().prepare_job(dict(self.job,max_attempts=2),self.registration,'20261008')
    def test_future_admission_rejected_without_relaxing_other_lanes(self):
        self.request['admission_cutoff']='2026-10-08T08:03:00+08:00'
        job,binding=self.prepared()
        self.assertEqual(self.dispatch(job,binding)['status'],'FUTURE_RESEARCH_CUTOFF')
        self.assertIsNone(run_ledger.read_run(str(self.root/'ledger'),job['identity']))
    def test_source_changed_after_prepare_blocks_before_claim(self):
        job,binding=self.prepared()
        path=next((self.root/'input/runs').rglob('artifact.csv'));path.write_bytes(path.read_bytes()+b'bad')
        self.assertEqual(self.dispatch(job,binding)['status'],'BLOCKED_M06_REGISTRATION')
        self.assertIsNone(run_ledger.read_run(str(self.root/'ledger'),job['identity']))
    def test_existing_source_newer_than_admission_is_rejected(self):
        self.request['admission_cutoff']='2026-10-08T07:58:00+08:00'
        with self.assertRaisesRegex(ValueError,'M06_SOURCE_AFTER_ADMISSION'):self.prepared()
    def test_generation_is_explicit_absence_only_and_not_replay(self):
        self.request.update(production_method='GENERATE_IF_ABSENT',execution_mode='MANUAL_RECOVERY')
        with self.assertRaisesRegex(ValueError,'M06_GENERATION_REQUIRES_ABSENT_POOL'):self.prepared()
        self.request['execution_mode']='RECORDED_INPUT_REPLAY'
        with self.assertRaises(ValueError):self.prepared()
    def test_generation_cutoff_is_bounded_and_original_runtime_gate_remains(self):
        (self.root/'input/latest.json').write_text('{"entries":{}}')
        self.request.update(production_method='GENERATE_IF_ABSENT',execution_mode='MANUAL_RECOVERY')
        self.request['source_files']={str(p.relative_to(self.root/'input')):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (self.root/'input').rglob('*') if p.is_file() and (p.name=='latest.json' or '/assets/' in str(p))}
        self.request['completion_cutoff']=self.request['admission_cutoff']
        with self.assertRaisesRegex(ValueError,'M06_GENERATION_WINDOW'):self.prepared()
        self.request['completion_cutoff']='2026-10-08T09:20:00+08:00'
        with self.assertRaisesRegex(ValueError,'M06_PRODUCER_RUNTIME_MISMATCH|M06_REQUIRED_ASSET_FILE_MISSING'):self.prepared()
        self.assertEqual(list((self.root/'output').iterdir()),[self.root/'output/.v5-shadow-root'])
    def test_missing_config_model_pin_marker_or_source_never_claims(self):
        for change in ({'python_sha256':'0'*64},{'private_root':str(self.root/'input')},{'enabled':False}):
            reg=dict(self.registration,**change)
            with self.subTest(change=change),self.assertRaises(ValueError):self.api().prepare_job(self.job,reg,'20261008')
        self.request['execution_mode']='MANUAL_RECOVERY'
        with self.assertRaisesRegex(ValueError,'M06_REQUIRED_ASSET_FILE_MISSING'):self.prepared()
        self.assertEqual(list((self.root/'ledger').iterdir()),[self.root/'ledger/.v5-daily-run-ledger'])
    def test_unknown_owner_outcome_never_reinvokes(self):
        job,binding=self.prepared()
        original=binding['invoke']
        def lost(*args):original(*args);raise TimeoutError('SYNTHETIC_LOST_RESPONSE')
        binding['invoke']=lost
        first=self.dispatch(job,binding);second=self.dispatch(job,binding)
        self.assertEqual(first['status'],'OUTCOME_UNKNOWN_NO_AUTOMATIC_RETRY',first)
        self.assertEqual(second['status'],'IN_PROGRESS_OR_OUTCOME_UNKNOWN',second)
        self.assertEqual(len(second['state']['attempts']),1)
    def test_corruption_blocks_saved_reuse(self):
        job,binding=self.prepared();first=self.dispatch(job,binding)
        ref=first['state']['latest_success']['product_reference'];path=self.root/'output'/ref['committed_reference']['artifact_relative']
        replacement=path.with_name('synthetic-corruption.tmp');replacement.write_bytes(path.read_bytes()+b' ');os.replace(replacement,path)
        row=self.dispatch(job,binding)
        self.assertEqual(row['status'],'BLOCKED_SAVED_PRODUCT_INVALID',row)
        self.assertEqual(row['state']['latest_success'],first['state']['latest_success'])
    def test_request_configuration_and_dependency_changes_cannot_reuse(self):
        job,binding=self.prepared();first=self.dispatch(job,binding)
        changed=dict(self.registration,timeout_seconds=121)
        job2,binding2=self.api().prepare_job(self.job,changed,'20261008')
        self.assertNotEqual(job2['identity']['config_sha256'],job['identity']['config_sha256'])
        self.assertIsNone(run_ledger.read_run(str(self.root/'ledger'),job2['identity']))
        binding['dependency_sha256']='0'*64
        self.assertEqual(self.dispatch(job,binding)['status'],'OWNER_BINDING_IDENTITY_MISMATCH')
    def test_ledger_only_receipt_tampering_cannot_match_publication(self):
        job,binding=self.prepared();first=self.dispatch(job,binding)
        ref=first['state']['latest_success']['product_reference']
        state=run_ledger.read_run(str(self.root/'output/.m06-ledger'),ref['m06_computation_identity'])
        state['latest_success']['product_reference']['producer_receipt']['extra_forged_evidence']='SYNTHETIC_TAMPER'
        path=self.root/'output/.m06-ledger/hk_preselection/20261008'/(run_ledger.identity_key(ref['m06_computation_identity'])+'.json')
        path.write_text(json.dumps(state))
        with self.assertRaisesRegex(ValueError,'M06_LEDGER_PUBLICATION_RECEIPT_MISMATCH'):
            self.api()._process('read',self.request,self.registration,binding['owner_snapshot'],
                reference=ref['committed_reference'],m06_ledger_run_id=ref['m06_ledger_run_id'])
    def test_window_closed_tick_never_attaches_unverified_saved_success(self):
        self.assertEqual(self.tick()['lanes'][0]['status'],'SUCCEEDED')
        self.now=datetime.fromisoformat('2026-10-08T10:00:00+08:00')
        row=self.tick()['lanes'][0]
        self.assertEqual(row['status'],'MISSED_WINDOW_NO_BACKFILL')
        self.assertNotIn('state',row)
    def test_wrong_cold_reader_run_retains_unknown_p0_claim(self):
        job,binding=self.prepared();original=self.api()._process
        def wrong_read(action,*args,**kwargs):
            result=original(action,*args,**kwargs)
            if action=='read':result['payload']['m06_ledger_run_id']='SYNTHETIC_WRONG_RUN'
            return result
        with patch.object(self.api(),'_process',side_effect=wrong_read):row=self.dispatch(job,binding)
        self.assertEqual(row['status'],'OUTCOME_UNKNOWN_NO_AUTOMATIC_RETRY',row)
        state=run_ledger.read_run(str(self.root/'ledger'),job['identity'])
        self.assertIsNone(state['latest_success']);self.assertEqual(state['attempts'][-1]['status'],'RUNNING')
    def test_concurrent_dispatch_does_not_duplicate_owner(self):
        from concurrent.futures import ThreadPoolExecutor
        job,binding=self.prepared()
        with patch('v5_shadow.daily_dispatch.datetime') as clock:
            clock.now.return_value=self.now
            def dispatch():return daily_dispatch.dispatch_due([job],{'hk_preselection':binding},str(self.root/'ledger'))['lanes'][0]
            with ThreadPoolExecutor(max_workers=2) as pool:rows=list(pool.map(lambda _:dispatch(),range(2)))
        self.assertEqual(sum(r['status']=='SUCCEEDED' for r in rows),1,rows)
        self.assertTrue({r['status'] for r in rows}<={'SUCCEEDED','REUSED_SUCCESS','IN_PROGRESS_OR_OUTCOME_UNKNOWN'})
        state=run_ledger.read_run(str(self.root/'ledger'),job['identity'])
        self.assertEqual(len(state['attempts']),1)
    def test_expired_generation_window_blocks_without_original_owner(self):
        job,binding=self.prepared()
        request=dict(self.request,production_method='GENERATE_IF_ABSENT',execution_mode='MANUAL_RECOVERY',completion_cutoff=self.now.isoformat())
        job=dict(job,owner_request=request)
        self.assertEqual(self.api().admission_reason(job,binding,self.now,str(self.root/'ledger')),'M06_GENERATION_COMPLETION_WINDOW_EXPIRED')

    def test_worker_drift_after_admission_cannot_finish_old_identity(self):
        job,binding=self.prepared();original=binding['invoke']
        worker=BASE/'src/v5_shadow/m06_daily_worker.py';raw=worker.read_bytes()
        def drift(*args):
            worker.write_bytes(raw+b'\n# SYNTHETIC_POST_ADMISSION_DRIFT\n')
            try:return original(*args)
            finally:worker.write_bytes(raw)
        binding['invoke']=drift
        row=self.dispatch(job,binding)
        self.assertEqual(row['status'],'OUTCOME_UNKNOWN_NO_AUTOMATIC_RETRY',row)
        self.assertIsNone(run_ledger.read_run(str(self.root/'ledger'),job['identity'])['latest_success'])

    def test_existing_optional_name_receipt_must_be_declared(self):
        assets=self.root/'assets'
        for kind,field in (('panel','panel_relative'),('model','bundle_relative'),('name','dictionary_relative')):
            folder=assets/kind;folder.mkdir()
            (folder/'data.bin').write_bytes(b'SYNTHETIC_NOT_A_MODEL')
            (folder/'manifest.json').write_text(json.dumps({field:kind+'/data.bin'}))
            (assets/(kind+'_latest.json')).write_text(json.dumps(dict(manifest_relative=kind+'/manifest.json')))
        receipt=assets/'name/receipt.json';receipt.write_text('{}')
        self.request['files']={str(p.relative_to(assets)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in assets.rglob('*') if p.is_file() and p!=receipt}
        with self.assertRaisesRegex(ValueError,'M06_REQUIRED_ASSET_RECEIPT'):self.prepared()

    def test_m06_config_does_not_rekey_other_lanes(self):
        observed=[]
        (self.root/'bundles/20261008.json').write_text(json.dumps(dict(target_date='20261008',jobs=[])))
        def capture(jobs,bindings,root):
            observed.append({lane:{k:v for k,v in b.items() if k.endswith('_sha256')} for lane,b in bindings.items()})
            return dict(status='DISPATCH_ATTEMPT_ONLY',lanes=[],natural_verified=False)
        with patch('v5_shadow.daily_tick.datetime') as clock,patch('v5_shadow.daily_tick.dispatch_due',side_effect=capture):
            clock.now.return_value=self.now
            daily_tick.tick(self.config);self.config['hk_preselection']={'enabled':False};daily_tick.tick(self.config)
        self.assertEqual(observed[0],observed[1])

if __name__=='__main__':unittest.main(verbosity=2)
