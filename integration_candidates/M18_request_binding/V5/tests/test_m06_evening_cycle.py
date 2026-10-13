"""D-close -> next-session M06 contract; all inputs are synthetic fixtures."""
from datetime import datetime, timedelta
import hashlib
import json
import unittest
from unittest.mock import patch
import test_m06_daily_cycle as support
from fixtures.hk_preselection_verified_factory import create_verified_fixture
from v5_shadow import p0_hk_preselection as m06, daily_dispatch
from v5_shadow.digests import canonical_bytes, sha256_json


class M06EveningCycleTests(unittest.TestCase):
    setUp = support.M06DailyCycleTests.setUp
    write_delivery = support.M06DailyCycleTests.write_delivery
    def prepare(self):
        with patch('v5_shadow.m06_deadline_process._utc_now',return_value=self.now):
            return support.M06DailyCycleTests.prepare(self)
    tick = support.M06DailyCycleTests.tick
    inventory = support.M06DailyCycleTests.inventory

    def evening(self, scheduled='20261009', target='20261012', *, live_clock=False):
        store=self.root/'evening-input'
        create_verified_fixture(store,target=target,signal=scheduled,eligibility=scheduled,
                                master_capture_time='00:01:00' if live_clock else '17:30:15')
        date=f'{scheduled[:4]}-{scheduled[4:6]}-{scheduled[6:]}'
        entry=json.loads((store/'latest.json').read_bytes())['entries'][target+'/HK_CONNECT_D1_TOP100_0_2']
        manifest=json.loads((store/entry['manifest_relative']).read_bytes())
        manifest['captured_at']=date+('T00:02:00+08:00' if live_clock else 'T17:31:00+08:00')
        (store/entry['manifest_relative']).write_bytes(canonical_bytes(manifest))
        receipt=json.loads((store/entry['receipt_relative']).read_bytes())
        receipt.update(finished_at=date+('T00:03:00+08:00' if live_clock else 'T17:32:00+08:00'),manifest_sha256=sha256_json(manifest))
        (store/entry['receipt_relative']).write_bytes(canonical_bytes(receipt))
        self.registration['store_root']=str(store)
        self.policy.update(date_contract='CLOSE_TO_NEXT_HK_SESSION_V1',owner_contract_cutoff_time='09:20',full_day_window=dict(start='17:30',end='18:30'),
                           half_day_window=dict(start='17:30',end='18:30'))
        self.delivery.update(target_date=target,signal_date=scheduled,eligibility_source_date=scheduled,
                             completed_at=date+('T00:04:00+08:00' if live_clock else 'T17:33:00+08:00'),
                             source_files={str(p.relative_to(store)):hashlib.sha256(p.read_bytes()).hexdigest()
                                           for p in store.rglob('*') if p.is_file()})
        self.path=self.root/'deliveries'/f'{target}.json';self.write_delivery()
        self.now=datetime.fromisoformat(date+'T17:35:00+08:00')
        if live_clock:
            self.now=datetime.now(m06.TZ)
            self.policy.update(full_day_window=dict(start='00:00',end='23:59'),half_day_window=dict(start='00:00',end='23:59'))

    def test_actual_original_owner_evening_mapping_two_ledgers_reader_and_reuse(self):
        # Synthetic fixture only; use actual current process/ledger clock rather
        # than pretending the unchanged original child ran on a historical day.
        scheduled=datetime.now(m06.TZ).strftime('%Y%m%d')
        cycle=m06.calendar_day(scheduled,evening=True)
        if cycle['state'] not in ('FULL_TRADING_DAY','HALF_TRADING_DAY_AM'):
            self.skipTest('Actual clock is outside the fixed 2026 HK session calendar')
        self.evening(scheduled,cycle['target_date'],live_clock=True)
        from v5_shadow import m06_readonly
        with patch.object(m06,'run_owner',wraps=m06.run_owner) as owner:
            first=self.tick()['lanes'][0]
            self.assertEqual(first['status'],'SUCCEEDED',first)
            self.assertEqual(first['current_success']['status'],'CURRENT_SUCCESS_PROMOTED',first)
            pointer=m06_readonly.read_current_success(m06._current_binding(self.config))
            product=first['state']['latest_success']['product_reference']
            self.assertEqual(pointer['p0_identity']['target_date'],cycle['target_date'])
            self.assertEqual(pointer['p0_identity']['research_cutoff'],product['admission_cutoff'])
            self.assertEqual(pointer['m06_identity']['research_cutoff'],product['owner_contract_cutoff'])
            self.assertNotEqual(product['execution_deadline'],product['owner_contract_cutoff'])
            self.assertNotIn('completion_cutoff',product)
            m06_readonly.validate_current_success(m06._current_binding(self.config),pointer)
            self.now+=timedelta(minutes=5)
            second=self.tick()['lanes'][0]
            self.assertEqual(second['status'],'REUSED_SUCCESS',second)
            self.assertEqual(owner.call_count,1)
            self.assertEqual(m06_readonly.read_current_success(m06._current_binding(self.config)),pointer)

    def test_evening_unknown_after_original_owner_does_not_restart_or_promote(self):
        scheduled=datetime.now(m06.TZ).strftime('%Y%m%d');cycle=m06.calendar_day(scheduled,evening=True)
        if cycle['state'] not in ('FULL_TRADING_DAY','HALF_TRADING_DAY_AM'):
            self.skipTest('Actual clock is outside fixed 2026 calendar')
        self.evening(scheduled,cycle['target_date'],live_clock=True)
        original=m06.run_owner;calls=[]
        def lost(*args,**kwargs):
            calls.append(args[1]);original(*args,**kwargs);raise TimeoutError('SYNTHETIC_LOST_OWNER_REPLY')
        with patch.object(m06,'run_owner',side_effect=lost):
            first=self.tick()['lanes'][0];self.now+=timedelta(minutes=5);second=self.tick()['lanes'][0]
        self.assertEqual(first['status'],'OUTCOME_UNKNOWN_NO_AUTOMATIC_RETRY',first)
        self.assertEqual(second['status'],'IN_PROGRESS_OR_OUTCOME_UNKNOWN',second)
        self.assertEqual(len(calls),1)
        self.assertFalse((self.root/'output/.m06-current-success.json').exists())

    def test_tick_seals_real_adapter_bytes_then_original_inspector_rejects_fake_model(self):
        # Hash-complete synthetic assets must never masquerade as a real model.
        import test_m06_input_delivery as delivery_support
        from v5_shadow import m06_input_delivery as adapter
        fixture=delivery_support.M06InputDeliveryTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        fixture.upstream();self.evening('20261012','20261013');self.path.unlink()
        self.registration['asset_root']=str(fixture.root/'assets')
        settings={k:v for k,v in fixture.config.items() if k!='delivery_root'}
        settings['original_store_root']=self.registration['store_root']
        self.policy['input_delivery']=settings
        with patch.object(adapter,'_utc_now',return_value=self.now),patch.object(m06,'_process',wraps=m06._process) as inspect:
            with self.assertRaises(ValueError):self.prepare()
        self.assertGreaterEqual(inspect.call_count,1)
        registration=inspect.call_args.args[2]
        self.assertNotEqual(registration['store_root'],settings['original_store_root'])
        self.assertNotEqual(registration['asset_root'],settings['original_asset_root'])
        self.assertTrue(registration['store_root'].startswith(settings['snapshot_root']+'/'))
        self.assertTrue(self.path.is_file())
        self.assertEqual(json.loads(self.path.read_bytes())['completed_at'],self.now.isoformat())
        self.assertEqual(len(list((self.root/'ledger').iterdir())),1)
        self.assertFalse((self.root/'output/.m06-current-success.json').exists())

    def test_original_calendar_next_session_and_unknown_year(self):
        for scheduled,target,state in [('20261009','20261012','FULL_TRADING_DAY'),
            ('20261012','20261013','FULL_TRADING_DAY'),('20261002','20261005','FULL_TRADING_DAY'),('20261224','20261228','HALF_TRADING_DAY_AM')]:
            with self.subTest(scheduled=scheduled):
                self.assertEqual(m06.calendar_day(scheduled,evening=True),dict(state=state,scheduled_date=scheduled,signal_date=scheduled,target_date=target))
        self.assertEqual(m06.calendar_day('20261011',evening=True)['state'],'NON_TRADING_DAY')
        self.assertEqual(m06.calendar_day('20261231',evening=True)['state'],'UNKNOWN')
        self.assertEqual(m06.calendar_day('20270104',evening=True)['state'],'UNKNOWN')

    def test_evening_friday_admits_signal_today_target_next_monday(self):
        self.evening()
        result=self.prepare()
        self.assertEqual(result['status'],'PREPARED_M06_CANDIDATE',result)
        self.assertEqual(result['job']['owner_request']['signal_date'],'20261009')
        self.assertEqual(result['job']['identity']['target_date'],'20261012')
        self.assertEqual(result['job']['scheduled_at'],'2026-10-09T17:30:00+08:00')

    def test_half_day_keeps_explicit_evening_slot_and_skips_holidays(self):
        self.evening('20261224','20261228')
        result=self.prepare()
        self.assertEqual(result['status'],'PREPARED_M06_CANDIDATE',result)
        self.assertTrue(result['job']['half_day_bound'])
        self.assertEqual(result['job']['owner_request']['signal_date'],'20261224')
        self.assertEqual(result['job']['identity']['target_date'],'20261228')
        self.assertEqual(result['job']['scheduled_at'],'2026-12-24T17:30:00+08:00')

    def test_non_m06_cross_day_remains_rejected_before_owner(self):
        import test_daily_dispatch as dispatch_support
        fixture=dispatch_support.DailyDispatchTests();fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.mock.now.return_value=datetime.fromisoformat('2026-10-09T17:35:00+08:00')
        for lane in ('announcement','us_mapping','rebound'):
            job=fixture.job(lane);job['identity']['target_date']='20261012'
            job.update(scheduled_at='2026-10-09T17:30:00+08:00',deadline='2026-10-09T18:30:00+08:00')
            with self.subTest(lane=lane):
                result=daily_dispatch.dispatch_due([job],{},fixture.root)
                self.assertEqual(result['lanes'][0]['status'],'NOT_CURRENT_TARGET_DATE')

    def test_rejects_arbitrary_future_signal_master_and_cutoff_dates(self):
        self.evening()
        request={key:self.delivery[key] for key in ('target_date','signal_date','eligibility_source_date','files','source_files')}
        request.update(date_contract='CLOSE_TO_NEXT_HK_SESSION_V1',scheduled_date='20261009',
            admission_cutoff=self.now.isoformat(),execution_deadline='2026-10-09T18:30:00+08:00',
            owner_contract_cutoff='2026-10-12T09:20:00+08:00',execution_mode='RECORDED_INPUT_REPLAY',production_method='EXISTING_VERIFIED_POOL')
        for key,value in [('target_date','20261013'),('signal_date','20261008'),('eligibility_source_date','20261012'),
            ('scheduled_date','20261008'),('execution_deadline','2026-10-12T18:30:00+08:00'),
            ('owner_contract_cutoff','2026-10-09T19:00:00+08:00'),('admission_cutoff','2026-10-12T08:00:00+08:00')]:
            with self.subTest(key=key),self.assertRaises(ValueError):m06._request(dict(request,**{key:value}))

    def test_m06_wrong_future_target_is_rejected_by_real_admission_before_claim(self):
        self.evening()
        candidate=self.prepare();job=candidate['job'];binding=candidate['binding']
        job['owner_request']['target_date']='20261013';job['identity']['target_date']='20261013'
        job['identity']['input_sha256']=sha256_json(job['owner_request'])
        with patch('v5_shadow.daily_dispatch.datetime') as clock:
            clock.now.return_value=self.now
            row=daily_dispatch.dispatch_due([job],{'hk_preselection':binding},self.config['ledger_root'])['lanes'][0]
        self.assertEqual(row['status'],'BLOCKED_M06_REGISTRATION')
        self.assertEqual(len(list((self.root/'ledger').iterdir())),1)

    def test_future_owner_cutoff_cannot_extend_actual_execution_budget(self):
        self.evening();candidate=self.prepare()
        self.now=datetime.fromisoformat('2026-10-09T18:25:00+08:00')
        reason=m06.admission_reason(candidate['job'],candidate['binding'],self.now,self.config['ledger_root'])
        self.assertEqual(reason,'M06_EXECUTION_BUDGET_INSUFFICIENT')
        self.assertEqual(len(list((self.root/'ledger').iterdir())),1)

    def test_evening_policy_has_no_default_owner_cutoff_or_midday_half_slot(self):
        self.evening();self.policy.pop('owner_contract_cutoff_time')
        with self.assertRaises(ValueError):self.prepare()
        self.policy['owner_contract_cutoff_time']='09:20'
        self.evening('20261224','20261228')
        self.now=datetime.fromisoformat('2026-12-24T12:15:00+08:00')
        self.assertEqual(self.prepare()['status'],'WAITING_M06_WINDOW')

    def test_finished_after_execution_deadline_never_counts_as_current_success(self):
        job=dict(owner_request=dict(date_contract='CLOSE_TO_NEXT_HK_SESSION_V1',execution_deadline='2026-10-09T18:30:00+08:00'))
        state=dict(latest_success=dict(finished_at='2026-10-09T18:30:01+08:00'))
        with patch.object(m06,'_utc_now',return_value=datetime.fromisoformat('2026-10-09T18:29:00+08:00')):
            with self.assertRaises(TimeoutError):m06.verify_finished_state(job,state)

    def test_request_separates_signal_day_admission_from_target_day_owner_cutoff(self):
        self.evening()
        request={key:self.delivery[key] for key in ('target_date','signal_date','eligibility_source_date','files','source_files')}
        request.update(date_contract='CLOSE_TO_NEXT_HK_SESSION_V1',scheduled_date='20261009',
                       admission_cutoff=self.now.isoformat(),execution_deadline='2026-10-09T18:30:00+08:00',
                       owner_contract_cutoff='2026-10-12T09:20:00+08:00',
                       execution_mode='RECORDED_INPUT_REPLAY',production_method='EXISTING_VERIFIED_POOL')
        try:result=m06._request(request)
        except ValueError as error:self.fail('Valid separate dates rejected: '+str(error))
        self.assertIsNone(result)


if __name__=='__main__':unittest.main()
