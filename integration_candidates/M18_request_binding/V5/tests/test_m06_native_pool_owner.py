"""Original-schema compatibility evidence, using synthetic eight-file pools.

This exercises the fixed original owner and fresh readers, never a model or
provider. It is not an end-to-end test of the input adapter or automatic method
selection: the delivery is explicit EXISTING_VERIFIED_POOL / RECORDED_INPUT_REPLAY.
"""
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import test_m06_evening_cycle as support
from v5_shadow import m06_readonly, p0_hk_preselection as m06, run_ledger
from v5_shadow.digests import canonical_bytes, sha256_json


SAFETY = ('production_allowed', 'buy_gate_updated', 'orders_sent')
ROLE = 'HK_CONNECT_D1_TOP100_0_2'


class M06NativePoolOwnerTests(unittest.TestCase):
    write_delivery = support.M06EveningCycleTests.write_delivery
    evening = support.M06EveningCycleTests.evening
    prepare = support.M06EveningCycleTests.prepare
    tick = support.M06EveningCycleTests.tick

    def setUp(self):
        support.M06EveningCycleTests.setUp(self)
        scheduled = datetime.now(m06.TZ).strftime('%Y%m%d')
        cycle = m06.calendar_day(scheduled, evening=True)
        if cycle['state'] not in ('FULL_TRADING_DAY', 'HALF_TRADING_DAY_AM'):
            self.skipTest('Actual clock is outside the fixed 2026 HK session calendar')
        self.evening(scheduled, cycle['target_date'], live_clock=True)
        self.source = Path(self.registration['store_root'])
        latest = json.loads((self.source / 'latest.json').read_bytes())
        self.entry = latest['entries'][cycle['target_date'] + '/' + ROLE]
        self.manifest_path = self.source / self.entry['manifest_relative']
        self.receipt_path = self.source / self.entry['receipt_relative']
        manifest = json.loads(self.manifest_path.read_bytes())
        # Only synthetic fixture bytes change. This is the original manifest.v1
        # shape: safety assertions live in its bound receipt, not this manifest.
        for key in SAFETY:
            manifest.pop(key)
        self.manifest_path.write_bytes(canonical_bytes(manifest))
        receipt = json.loads(self.receipt_path.read_bytes())
        receipt['manifest_sha256'] = sha256_json(manifest)
        self.receipt_path.write_bytes(canonical_bytes(receipt))
        self._sync_inventory()
        self.assertEqual(len(self.delivery['source_files']), 8)
        self.assertEqual(self.delivery['files'], {})
        self.assertEqual(self.policy['production_method'], 'EXISTING_VERIFIED_POOL')
        self.assertEqual(self.policy['execution_mode'], 'RECORDED_INPUT_REPLAY')

    def _sync_inventory(self):
        self.delivery['source_files'] = {
            str(path.relative_to(self.source)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in self.source.rglob('*') if path.is_file()
        }
        self.write_delivery()

    def _cold_reader(self):
        manifest = json.loads(self.manifest_path.read_bytes())
        target = self.delivery['target_date']
        request = dict(
            schema_version='v5.hk_preselection_verified_request.v1',
            target_date=target, signal_date=self.delivery['signal_date'],
            eligibility_source_date=self.delivery['eligibility_source_date'],
            research_cutoff=f'{target[:4]}-{target[4:6]}-{target[6:]}T09:20:00+08:00',
            data_kind='SOURCE_SNAPSHOT', input_root=str(self.source),
            files=self.delivery['source_files'], expected_source=dict(
                role=ROLE, run_id=self.entry['run_id'],
                artifact_relative=self.entry['artifact_relative'],
                artifact_sha256=self.delivery['source_files'][self.entry['artifact_relative']],
                manifest_sha256=sha256_json(manifest),
                receipt_sha256=self.delivery['source_files'][self.entry['receipt_relative']],
            ),
        )
        # owner_root rechecks the complete fixed source closure before launch.
        worker = m06_readonly.owner_root() / 'V5/src/v5_shadow/hk_preselection_verified.py'
        with tempfile.TemporaryDirectory(prefix='native-reader-cache-', dir=self.root) as cache:
            process = subprocess.run(
                [sys.executable, '-I', '-B', '-X', 'pycache_prefix=' + cache,
                 str(worker), '--worker'],
                input=canonical_bytes(request), stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, timeout=120,
            )
        self.assertEqual(process.returncode, 0,
                         (process.stdout + process.stderr).decode(errors='replace'))
        self.assertEqual(process.stderr, b'')
        result = json.loads(process.stdout)
        self.assertEqual(result['request_sha256'], sha256_json(request))
        self.assertIs(result['model_weights_reverified'], False)
        return result

    def _assert_rejected_before_claim(self, reason):
        result = self._cold_reader()
        self.assertEqual(result['status'], 'CANNOT_CONFIRM', result)
        self.assertIn(reason, result['reason'])
        self.assertIsNone(result['artifact'])
        self.assertIsNone(result['verified_source_reference'])
        with self.assertRaisesRegex(ValueError, 'M06_EXISTING_POOL_REJECTED'):
            self.prepare()
        self.assertEqual(list((self.root / 'ledger').iterdir()),
                         [self.root / 'ledger/.v5-daily-run-ledger'])
        self.assertFalse((self.root / 'output/.m06-ledger').exists())
        self.assertFalse((self.root / 'output/.m06-current-success.json').exists())

    def test_native_manifest_original_owner_two_ledgers_fresh_reader_and_reuse(self):
        before = dict(self.delivery['source_files'])
        result = self._cold_reader()
        self.assertEqual(result['status'], 'ASSEMBLED', result)
        self.assertEqual(len(result['artifact']['rows']), 100)
        self.assertTrue(result['fixture_only'])
        with patch.object(m06, 'run_owner', wraps=m06.run_owner) as owner:
            first = self.tick()['lanes'][0]
            self.assertEqual(first['status'], 'SUCCEEDED', first)
            self.assertEqual(first['current_success']['status'], 'CURRENT_SUCCESS_PROMOTED', first)
            state = first['state']
            product = state['latest_success']['product_reference']
            self.assertEqual(product['row_count'], 100)
            self.assertTrue(product['fixture_only'])
            self.assertEqual(product['production_method'], 'EXISTING_VERIFIED_POOL')
            self.assertIs(product['producer_model_weights_reverified'], False)
            self.assertIs(product['reader_model_weights_reverified'], False)
            self.assertNotEqual(product['producer_pid'], product['reader_pid'])
            self.assertNotEqual(product['p0_ledger_run_id'], product['m06_ledger_run_id'])
            self.assertEqual(run_ledger.read_run(str(self.root / 'ledger'), state['identity']), state)
            original = run_ledger.read_run(str(self.root / 'output/.m06-ledger'),
                                          product['m06_computation_identity'])
            self.assertEqual(original['latest_success']['run_id'], product['m06_ledger_run_id'])
            self.assertEqual(original['latest_success']['status'], 'SUCCEEDED')
            self.assertIs(original['latest_success']['readback_verified'], True)
            self.assertEqual(len(original['attempts']), 1)
            binding = m06._current_binding(self.config)
            pointer = m06_readonly.read_current_success(binding)
            m06_readonly.validate_current_success(binding, pointer)
            self.now += timedelta(minutes=5)
            second = self.tick()['lanes'][0]
            self.assertEqual(second['status'], 'REUSED_SUCCESS', second)
            self.assertEqual(second['state']['latest_success'], state['latest_success'])
            self.assertEqual(len(second['state']['attempts']), 1)
            self.assertEqual(owner.call_count, 1)
            self.assertEqual(m06_readonly.read_current_success(binding), pointer)
            self.assertEqual(run_ledger.read_run(str(self.root / 'output/.m06-ledger'),
                                                product['m06_computation_identity']), original)
        self._sync_inventory()
        self.assertEqual(self.delivery['source_files'], before)
        manifest = json.loads(self.manifest_path.read_bytes())
        self.assertFalse(any(key in manifest for key in SAFETY))

    def test_native_manifest_receipt_missing_or_true_safety_rejected_by_cold_reader(self):
        baseline = json.loads(self.receipt_path.read_bytes())
        for key in SAFETY:
            for missing in (True, False):
                with self.subTest(key=key, missing=missing):
                    receipt = dict(baseline)
                    if missing:
                        receipt.pop(key)
                    else:
                        receipt[key] = True
                    self.receipt_path.write_bytes(canonical_bytes(receipt))
                    self._sync_inventory()
                    self._assert_rejected_before_claim('safety flag')

    def test_native_manifest_receipt_manifest_hash_mismatch_rejected_by_cold_reader(self):
        receipt = json.loads(self.receipt_path.read_bytes())
        receipt['manifest_sha256'] = '0' * 64
        self.receipt_path.write_bytes(canonical_bytes(receipt))
        self._sync_inventory()
        self._assert_rejected_before_claim('manifest sha mismatch')


if __name__ == '__main__':
    unittest.main(verbosity=2)
