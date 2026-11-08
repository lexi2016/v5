"""Synthetic stage/owner integration; original provider continuation function only."""
import ast
import copy
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import types
import unittest

import stages
from synthetic_owner_fixture import SyntheticOwner, binding_module, canonical, sha


class StageChainTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'owner'
        self.owner = SyntheticOwner(self.root, initialize=True)

    def run_stage(self, owner=None):
        owner = owner or self.owner
        attempt = stages.Attempt(owner.symbol, owner.target)
        result = stages.advance_stock(attempt, owner, owner.prior, owner.input_ref, owner.input_ref['sha256'])
        return attempt, result

    def bridge(self):
        path = Path(__file__).with_name('owner_bridge.py')
        self.assertTrue(path.exists(), 'original owner API bridge has not been wired')
        spec = importlib.util.spec_from_file_location('daily1540_test_bridge', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_stage_persists_next_checkpoint_bound_to_new_continuation(self):
        attempt, result_ref = self.run_stage()
        result = json.loads(self.owner.checked(result_ref))
        self.assertIn('checkpoint_ref', result, 'daily output cannot seed the next reviewed session')
        checkpoint = json.loads(self.owner.checked(result['checkpoint_ref']))
        bundle = json.loads(gzip.decompress(self.owner.checked(result['continuation_ref'])))
        self.assertEqual(checkpoint['prior_continuation_sha256'], result['continuation_ref']['sha256'])
        self.assertEqual(checkpoint['state'], bundle['component109'])
        self.assertEqual(checkpoint['prefix_sha256'], sha(canonical(self.owner.rows)))
        self.assertEqual(attempt.phase, 'PERSISTED_AWAIT_OWNER_SEAL_AND_INDEPENDENT_SAMPLE')
        self.assertFalse(result['production_allowed'])

    def test_new_checkpoint_can_be_read_after_restart_only_if_owner_registers_it(self):
        _, result_ref = self.run_stage()
        result = json.loads(self.owner.checked(result_ref))
        self.assertIn('checkpoint_ref', result)
        with self.assertRaisesRegex(ValueError, 'UNREGISTERED_PRIOR'):
            self.owner.checkpoint_binding.bound_checkpoint_ref({'continuation_ref': result['continuation_ref']})
        registry = {'schema': 'OWNER_CHECKPOINT_REGISTRY_V1', 'entries': [{
            'continuation_ref': result['continuation_ref'], 'checkpoint_ref': result['checkpoint_ref']}]}
        raw = canonical(registry)
        pin = {'path': 'FIXTURE_ONLY_REVIEWED_NEXT_REGISTRY', 'bytes': len(raw), 'sha256': sha(raw)}
        cold = binding_module.Binding(raw, pin, self.owner.checked, self.owner.gate)
        ref = cold.bound_checkpoint_ref({'continuation_ref': result['continuation_ref']})
        self.assertEqual(cold.checked(ref), self.owner.checked(result['checkpoint_ref']))

    def test_new_attempt_reuses_verified_success_without_compute_or_writer(self):
        _, result_ref = self.run_stage()
        result = json.loads(self.owner.checked(result_ref))
        self.assertIn('checkpoint_ref', result)
        self.owner.seal_for_fixture(result_ref)
        fresh = SyntheticOwner(self.root)
        attempt, result = self.run_stage(fresh)
        self.assertEqual(attempt.phase, 'REUSE_COMPLETED_NO_RECOMPUTE')
        self.assertEqual(result['status'], 'REUSE_VERIFIED')
        self.assertEqual((fresh.compute_calls, fresh.writer_calls), (0, 0))

    def test_changed_compute_version_cannot_reuse_old_success(self):
        _, result_ref = self.run_stage()
        result = json.loads(self.owner.checked(result_ref))
        self.assertIn('checkpoint_ref', result)
        self.owner.seal_for_fixture(result_ref)
        fresh = SyntheticOwner(self.root)
        fresh.code_sha = 'f' * 64
        with self.assertRaisesRegex(ValueError, 'IDENTITY_CONFLICT'):
            self.run_stage(fresh)
        self.assertEqual((fresh.compute_calls, fresh.writer_calls), (0, 0))

    def test_partial_writer_failure_keeps_obligation_and_artifacts(self):
        self.owner.fail_writer = True
        attempt = stages.Attempt(self.owner.symbol, self.owner.target)
        with self.assertRaisesRegex(OSError, 'SYNTHETIC_PARTIAL_WRITE'):
            stages.advance_stock(attempt, self.owner, self.owner.prior,
                                 self.owner.input_ref, self.owner.input_ref['sha256'])
        self.assertEqual(attempt.phase, 'UNKNOWN_NO_BLIND_RETRY')
        self.assertTrue((self.owner.parquet_dir / 'SYNTHETIC_PARTIAL_MARKER.txt').exists())
        self.assertFalse((self.root / 'outputs/SUCCESS.json').exists())
        self.assertFalse((self.root / 'outputs/CHECKPOINT.json').exists())
        fresh = SyntheticOwner(self.root)
        with self.assertRaisesRegex(ValueError, 'UNKNOWN_RECONCILIATION_REQUIRED'):
            self.run_stage(fresh)
        self.assertEqual((fresh.compute_calls, fresh.writer_calls), (0, 0))

    def test_unsealed_persisted_result_is_not_verified_success(self):
        self.run_stage()
        fresh = SyntheticOwner(self.root)
        with self.assertRaisesRegex(ValueError, 'UNKNOWN_RECONCILIATION_REQUIRED'):
            self.run_stage(fresh)
        self.assertEqual((fresh.compute_calls, fresh.writer_calls), (0, 0))

    def test_target_mismatch_blocks_before_compute(self):
        self.owner.prepared['context']['asof'] = '20261109'
        self.owner.prepared['rows'][-1]['event_date'] = '20261109'
        with self.assertRaisesRegex(ValueError, 'PREPARED_TARGET'):
            self.run_stage()
        self.assertEqual((self.owner.compute_calls, self.owner.writer_calls), (0, 0))

    def test_missing_input_blocks_before_started(self):
        (self.root / self.owner.input_ref['path']).unlink()
        with self.assertRaises(FileNotFoundError):
            self.run_stage()
        self.assertEqual(list((self.root / 'claims').iterdir()), [])
        self.assertEqual((self.owner.compute_calls, self.owner.writer_calls), (0, 0))

    def test_history_count_requires_integer_zero_before_writer(self):
        for index, invalid in enumerate((False, 0.0)):
            with self.subTest(value=invalid):
                owner = SyntheticOwner(Path(self.tmp.name) / ('history_type_' + str(index)), initialize=True)
                compute = owner.compute
                def wrong_count(*args, **kwargs):
                    row, facts = compute(*args, **kwargs)
                    facts['historical109_rows_evaluated'] = invalid
                    return row, facts
                owner.compute = wrong_count
                with self.assertRaisesRegex(ValueError, 'LATEST_ONLY_PRIOR_COMPONENTS'):
                    self.run_stage(owner)
                self.assertEqual(owner.writer_calls, 0)

    def test_writer_counts_require_exact_integers(self):
        for index, (field, invalid) in enumerate((('metadata_rows', True), ('metadata_rows', 1.0),
                                                ('field_rows', 109.0))):
            with self.subTest(field=field, value=invalid):
                owner = SyntheticOwner(Path(self.tmp.name) / ('writer_type_' + str(index)), initialize=True)
                write_stock = owner.writer.write_stock
                def wrong_count(*args, **kwargs):
                    receipt = write_stock(*args, **kwargs)
                    receipt[field] = invalid
                    return receipt
                owner.writer.write_stock = wrong_count
                with self.assertRaisesRegex(ValueError, 'ORIGINAL_PARQUET_ROUNDTRIP'):
                    self.run_stage(owner)
                self.assertFalse((owner.root / 'outputs/CHECKPOINT.json').exists())
                self.assertFalse((owner.root / 'outputs/SUCCESS.json').exists())

    def test_no_valid_bar_keeps_actual_date_and_does_not_create_checkpoint(self):
        self.owner.prepared = {'status': 'RETAINED_NO_VALID_BAR', 'symbol': self.owner.symbol,
            'event_date': '20261105', 'requested_date': '20261106'}
        attempt, result_ref = self.run_stage()
        self.assertEqual(attempt.phase, 'RETAINED_NO_VALID_BAR')
        self.assertEqual(json.loads(self.owner.checked(result_ref))['event_date'], '20261105')
        self.assertFalse((self.root / 'outputs/CHECKPOINT.json').exists())
        self.assertEqual((self.owner.compute_calls, self.owner.writer_calls), (0, 0))

    def test_owner_bridge_uses_same_monitor_writer_and_bound_snapshot(self):
        bridge = self.bridge()
        bound = bridge.bind_runtime(self.owner, self.owner.checkpoint_binding)
        self.assertIs(bound.monitor, self.owner.monitor)
        self.assertIs(bound.writer, self.owner.writer)
        ref = bound.bound_checkpoint_ref(self.owner.prior)
        (self.root / ref['path']).write_bytes(b'changed after owner snapshot')
        self.assertNotEqual(bound.checked(ref), b'changed after owner snapshot')

    def test_owner_bridge_runs_stage_and_keeps_failure_attempt(self):
        bridge = self.bridge()
        self.owner.fail_writer = True
        with self.assertRaisesRegex(OSError, 'SYNTHETIC_PARTIAL_WRITE') as caught:
            bridge.advance_from_owner(self.owner, self.owner.checkpoint_binding,
                symbol=self.owner.symbol, target_date=self.owner.target, prior_selection=self.owner.prior,
                input_ref=self.owner.input_ref, expected_input_sha256=self.owner.input_ref['sha256'])
        self.assertEqual(caught.exception.daily1540_attempt.phase, 'UNKNOWN_NO_BLIND_RETRY')
        self.assertFalse((self.root / 'outputs/SUCCESS.json').exists())

    def test_original_owner_compute_prepared_signature_accepts_checkpoint_adapter(self):
        bridge = self.bridge()
        source = Path(stages.original_provider().__file__).with_name('daily_owner.py')
        self.assertTrue(source.exists(), 'exact original owner source is missing')
        raw = source.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),
                         '8f8fd8e67c10355ab3ff9ab14d7b7e61eae8ca35e2a4dba60abf071dbdaadadc')
        tree = ast.parse(raw)
        seam = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                    and node.name == 'compute_prepared')
        namespace = {'need': stages.need, 'c': stages.original_provider()}
        exec(compile(ast.Module(body=[seam], type_ignores=[]), str(source), 'exec'), namespace)
        compute = bridge.compute_for_original_owner(self.owner.compute, self.owner.checkpoint_binding,
                                                    self.owner.prior, self.owner.gate)
        row, facts, continuation = namespace['compute_prepared'](self.owner.prepared, compute)
        self.assertEqual(row['event_date'], '20261106')
        self.assertEqual(continuation['asof'], '20261106')
        self.assertEqual(continuation['component109']['count'], 2)
        self.assertNotIn('component_state', facts)

    def test_owner_bridge_missing_services_is_blocked_before_writes(self):
        bridge = self.bridge()
        with self.assertRaisesRegex(ValueError, 'ORIGINAL_OWNER_SERVICES_REQUIRED'):
            bridge.bind_runtime(types.SimpleNamespace(), self.owner.checkpoint_binding)
        self.assertEqual(list((self.root / 'claims').iterdir()), [])

    def test_owner_resource_gate_false_blocks_before_compute_or_write(self):
        bridge = self.bridge()
        self.owner.gate = lambda: False
        with self.assertRaisesRegex(ValueError, 'ORIGINAL_RESOURCE_GATE_REJECTED'):
            bridge.advance_from_owner(self.owner, self.owner.checkpoint_binding,
                symbol=self.owner.symbol, target_date=self.owner.target, prior_selection=self.owner.prior,
                input_ref=self.owner.input_ref, expected_input_sha256=self.owner.input_ref['sha256'])
        self.assertEqual((self.owner.compute_calls, self.owner.writer_calls), (0, 0))
        self.assertEqual(list((self.root / 'claims').iterdir()), [])

    def test_original_owner_compute_adapter_rejects_false_gate(self):
        bridge = self.bridge()
        with self.assertRaisesRegex(ValueError, 'ORIGINAL_RESOURCE_GATE_REJECTED'):
            bridge.compute_for_original_owner(self.owner.compute, self.owner.checkpoint_binding,
                                               self.owner.prior, lambda: False)
        self.assertEqual(self.owner.compute_calls, 0)


if __name__ == '__main__':
    unittest.main()
