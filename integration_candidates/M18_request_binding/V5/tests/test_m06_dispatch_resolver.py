"""Bounded real-file receipt discovery; no provider, model, or live roots."""
from copy import deepcopy
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

import test_m06_input_delivery as support

digest = support.digest


class M06DispatchResolverTests(unittest.TestCase):
    setUp = support.M06InputDeliveryTests.setUp
    write = support.M06InputDeliveryTests.write
    upstream = support.M06InputDeliveryTests.upstream
    write_dispatch = support.M06InputDeliveryTests.write_dispatch
    capture = support.M06InputDeliveryTests.capture
    def prepare(self, **kwargs):
        try:
            return support.M06InputDeliveryTests.prepare(self, **kwargs)
        except ValueError as error:
            if str(error) == 'CONTRACT_FIELDS_INVALID':
                self.fail('The explicit UUID discovery configuration is not implemented')
            raise

    def discovery(self):
        self.upstream()
        self.config.pop('dispatch_receipt_relative')
        self.config['dispatch_receipt_discovery'] = 'DAY_SLOT_UUID_V1'

    def receipt(self, token='1'*32, value=None):
        return self.write('dispatch', self.signal+'/1720/'+token+'.dispatch-receipt.json',
                          self.dispatch if value is None else value)

    def evidence(self, result):
        return json.loads((Path(result['store_root']).parent/'seal.json').read_bytes())['upstream_evidence']

    def assert_unpublished(self):
        self.assertFalse((self.root/'deliveries'/(self.target+'.json')).exists())
        self.assertFalse((self.root/'snapshots'/(self.target+'.json')).exists())

    def test_uuid_discovery_seals_actual_relative_bytes_without_invented_run_id(self):
        self.discovery(); path = self.receipt()
        self.assertNotIn('run_id', self.dispatch)
        result = self.prepare()
        self.assertEqual(result['status'], 'READY')
        evidence = self.evidence(result)
        self.assertEqual(evidence['dispatch_relative'], path.relative_to(self.root/'dispatch').as_posix())
        self.assertEqual(evidence['dispatch_sha256'], digest(path.read_bytes()))
        self.assertEqual((Path(result['store_root']).parent/'dispatch'/evidence['dispatch_relative']).read_bytes(), path.read_bytes())

    def test_absent_day_directory_waits_before_old_panel_is_misclassified(self):
        self.discovery()
        self.panel['panel_max_date'] = '20261009'
        self.write('assets', 'panels/panel/manifest.json', self.panel)
        self.assertEqual(self.prepare()['status'], 'WAITING_M06_INPUT_DELIVERY')
        self.assert_unpublished()

    def test_no_matching_success_is_waiting_and_never_uses_latest_or_other_day(self):
        self.discovery()
        wrong = dict(self.dispatch, status='FAILED')
        self.receipt(value=wrong)
        self.write('dispatch', 'latest.json', self.dispatch)
        self.write('dispatch', '20261009/1720/'+('2'*32)+'.dispatch-receipt.json', self.dispatch)
        self.assertEqual(self.prepare()['status'], 'WAITING_M06_INPUT_DELIVERY')
        self.assert_unpublished()

    def test_multiple_matches_order_by_finish_then_raw_hash_then_path_not_mtime(self):
        self.discovery()
        earlier = dict(self.dispatch, finished_at='2026-10-12T17:22:00+08:00')
        first = self.receipt('f'*32, earlier)
        self.receipt('0'*32)
        os.utime(first, (1, 1))
        result = self.prepare()
        self.assertEqual(self.evidence(result)['dispatch_relative'], first.relative_to(self.root/'dispatch').as_posix())

    def test_equal_finish_uses_raw_sha_tie_break_and_sealed_choice_never_drifts(self):
        self.discovery()
        files = [self.receipt('f'*32, dict(self.dispatch, diagnostic='a')),
                 self.receipt('0'*32, dict(self.dispatch, diagnostic='b'))]
        expected = min(files, key=lambda p:(digest(p.read_bytes()), str(p)))
        result = self.prepare()
        self.assertEqual(self.evidence(result)['dispatch_relative'], expected.relative_to(self.root/'dispatch').as_posix())
        self.receipt('2'*32, dict(self.dispatch, finished_at='2026-10-12T17:21:00+08:00'))
        with patch.object(self.adapter, '_utc_now', side_effect=AssertionError('sealed reuse cannot mint clock')):
            again = self.prepare()
        self.assertEqual(again['status'], 'REUSED_M06_INPUT_DELIVERY')
        self.assertEqual(again['seal_sha256'], result['seal_sha256'])

    def test_candidate_must_match_every_existing_date_workload_and_hash_check(self):
        self.discovery()
        mutations = [lambda d:d.update(scheduled_date=self.target),
                     lambda d:d['resolved_dates']['research_panel_daily_hk'].update(target_date=self.target),
                     lambda d:d.update(invoked_workload_ids=[]),
                     lambda d:d['workload_results'][0].update(exit_code=1),
                     lambda d:d['workload_results'][0]['_authoritative_payload']['lanes']['HK'].update(receipt_sha256='0'*64)]
        for change in mutations:
            value = deepcopy(self.dispatch); change(value)
            self.receipt(value=value)
            self.assertEqual(self.prepare()['status'], 'WAITING_M06_INPUT_DELIVERY')
            self.assert_unpublished()

    def test_future_finished_candidate_is_not_admitted(self):
        self.discovery(); self.receipt()
        with patch.object(self.adapter, '_utc_now', return_value=self.now.replace(minute=23)):
            self.assertEqual(self.prepare()['status'], 'WAITING_M06_INPUT_DELIVERY')
        self.assert_unpublished()

    def test_exact_and_discovery_are_mutually_exclusive(self):
        self.discovery(); self.receipt()
        self.config['dispatch_receipt_relative'] = '{scheduled_date}/1720.json'
        with self.assertRaisesRegex(ValueError, 'LOCATOR'):
            self.prepare()
        self.assert_unpublished()

    def test_uuid_symlink_file_and_directory_are_rejected(self):
        self.discovery(); path = self.receipt()
        path.unlink(); path.symlink_to(self.root/'dispatch'/self.signal/'1720.json')
        with self.assertRaises((OSError, ValueError)):
            self.prepare()
        self.assert_unpublished()
        path.unlink(); path.parent.rmdir(); path.parent.symlink_to(self.root/'assets', target_is_directory=True)
        with self.assertRaises((OSError, ValueError)):
            self.prepare()
        self.assert_unpublished()

    def test_candidate_limit_is_bounded(self):
        self.discovery(); self.receipt('1'*32); self.receipt('2'*32)
        with patch.object(self.adapter, 'MAX_DISPATCH_RECEIPTS', 1):
            with self.assertRaisesRegex(ValueError, 'LIMIT'):
                self.prepare()
        self.assert_unpublished()

    def test_selected_receipt_mutation_during_copy_cannot_seal(self):
        self.discovery(); path = self.receipt()
        copy = self.adapter._copy_capture
        def changed(capture, snapshot):
            copy(capture, snapshot)
            path.write_bytes(path.read_bytes()+b' ')
        with patch.object(self.adapter, '_copy_capture', side_effect=changed):
            with self.assertRaisesRegex(ValueError, 'CHANGED'):
                self.prepare()
        self.assert_unpublished()

    def test_directory_addition_during_copy_cannot_redefine_selection(self):
        self.discovery(); self.receipt()
        copy = self.adapter._copy_capture
        def changed(capture, snapshot):
            copy(capture, snapshot)
            self.receipt('2'*32, dict(self.dispatch, finished_at='2026-10-12T17:21:00+08:00'))
        with patch.object(self.adapter, '_copy_capture', side_effect=changed):
            with self.assertRaisesRegex(ValueError, 'CHANGED'):
                self.prepare()
        self.assert_unpublished()

    def test_unselected_receipt_mutation_during_copy_also_blocks_seal(self):
        self.discovery(); self.receipt('1'*32)
        later = self.receipt('2'*32, dict(self.dispatch, finished_at='2026-10-12T17:26:00+08:00'))
        copy = self.adapter._copy_capture
        def changed(capture, snapshot):
            copy(capture, snapshot)
            later.write_bytes(later.read_bytes()+b' ')
        with patch.object(self.adapter, '_copy_capture', side_effect=changed):
            with self.assertRaisesRegex(ValueError, 'CHANGED'):
                self.prepare()
        self.assert_unpublished()

    def test_same_bytes_directory_replacement_is_rejected(self):
        self.discovery(); path = self.receipt()
        copy = self.adapter._copy_capture
        def changed(capture, snapshot):
            copy(capture, snapshot)
            raw = path.read_bytes(); path.parent.rename(path.parent.with_name('old-1720'))
            self.receipt(value=raw)
        with patch.object(self.adapter, '_copy_capture', side_effect=changed):
            with self.assertRaisesRegex(ValueError, 'CHANGED'):
                self.prepare()
        self.assert_unpublished()

    def test_byte_budget_and_malformed_candidate_fail_closed(self):
        self.discovery(); path = self.receipt()
        with patch.object(self.adapter, 'MAX_DISPATCH_BYTES', 1):
            with self.assertRaisesRegex(ValueError, 'LIMIT'):
                self.prepare()
        self.assert_unpublished()
        path.write_bytes(b'{"broken":')
        with self.assertRaises(ValueError):
            self.prepare()
        self.assert_unpublished()

    def test_identical_receipt_ties_use_stable_relative_path(self):
        self.discovery(); self.receipt('f'*32); expected = self.receipt('0'*32)
        result = self.prepare()
        self.assertEqual(self.evidence(result)['dispatch_relative'], expected.relative_to(self.root/'dispatch').as_posix())

    def test_lane_mutation_between_candidates_cannot_mix_two_validations(self):
        self.discovery(); self.receipt('1'*32); self.receipt('2'*32)
        validate = self.adapter._capture_exact_upstream
        calls = 0
        def changing_lane(*args, **kwargs):
            nonlocal calls
            validate(*args, **kwargs)
            calls += 1
            if calls == 1:
                lane = self.root/'lane'/('hk-'+self.signal+'.json')
                lane.write_bytes(lane.read_bytes()+b' ')
        with patch.object(self.adapter, '_capture_exact_upstream', side_effect=changing_lane):
            with self.assertRaisesRegex(ValueError, 'CHANGED'):
                self.prepare()
        self.assert_unpublished()

    def test_example_remains_disabled_with_confirmed_new_evening_policy(self):
        example = json.loads((support.BASE/'examples/m06_daily_runtime.template.json').read_text())['daily']
        policy = example['hk_preselection_daily']
        self.assertIs(example['enabled'], False)
        self.assertIs(policy['enabled'], False)
        self.assertIs(example['hk_preselection']['enabled'], False)
        self.assertEqual(policy['input_delivery']['dispatch_receipt_discovery'], 'DAY_SLOT_UUID_V1')
        self.assertNotIn('dispatch_receipt_relative', policy['input_delivery'])
        self.assertEqual(policy['full_day_window'], dict(start='17:30', end='18:30'))
        self.assertEqual(policy['half_day_window'], policy['full_day_window'])
        self.assertEqual(policy['execution_budget_seconds'], 1200)
        self.assertEqual(policy['owner_contract_cutoff_time'], '09:00')
        self.assertEqual(example['hk_preselection']['timeout_seconds'], 600)

    def test_existing_pool_missing_safety_is_not_repaired_or_ignored(self):
        self.discovery(); self.receipt()
        manifest = dict(trade_date=self.target, artifact_relative='pool.csv', artifact_sha256=digest(b'pool'),
                        captured_at='2026-10-12T17:30:00+08:00')
        receipt = dict(trade_date=self.target, status='READY', role='HK_CONNECT_D1_TOP100_0_2', run_id='old',
                       manifest_sha256=self.adapter.sha256_json(manifest), artifact_sha256=manifest['artifact_sha256'],
                       finished_at='2026-10-12T17:30:00+08:00', **self.safety)
        self.write('store','latest.json',dict(entries={self.target+'/HK_CONNECT_D1_TOP100_0_2':dict(
            run_id='old',manifest_relative='pool-manifest.json',receipt_relative='pool-receipt.json',artifact_relative='pool.csv')}))
        path = self.write('store','pool-manifest.json',manifest)
        self.write('store','pool-receipt.json',receipt); self.write('store','pool.csv',b'pool')
        before = path.read_bytes()
        with self.assertRaisesRegex(ValueError, 'SAFETY'):
            self.prepare()
        self.assertEqual(path.read_bytes(),before); self.assert_unpublished()


if __name__ == '__main__':
    unittest.main()
