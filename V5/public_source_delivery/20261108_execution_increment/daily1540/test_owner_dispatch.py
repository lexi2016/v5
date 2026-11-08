"""Synthetic private-registry integration; no live owner or source is registered."""
import contextlib
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import types
import unittest

from synthetic_owner_fixture import SyntheticOwner


class OwnerDispatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.owner = SyntheticOwner(Path(self.tmp.name) / 'owner', initialize=True)
        self.entered = False
        self.lockpath = self.owner.root / 'ORIGINAL_LOCK_FIXTURE'
        self.lockpath.touch()

    def bridge(self):
        path = Path(__file__).with_name('owner_bridge.py')
        self.assertTrue(path.exists(), 'registered original-owner stage seam is missing')
        spec = importlib.util.spec_from_file_location('test_registered_daily_owner', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def record(self):
        @contextlib.contextmanager
        def owner_context():
            fd = os.open(self.lockpath, os.O_RDWR | os.O_NOFOLLOW)
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                self.entered = True
                st = os.fstat(fd)
                yield [(self.lockpath, fd, st.st_dev, st.st_ino)]
            finally:
                self.entered = False
                os.close(fd)
        def verify_contracts(record):
            if not self.entered:
                raise ValueError('VERIFY_OUTSIDE_OWNER_CONTEXT')
            for key in ('source_contract_ref', 'source_review_ref', 'calendar_ref'):
                self.owner.checked(record[key])
        return {'stage': 'compute_persist', 'owner_context': owner_context,
                'verify_contracts': verify_contracts, 'runtime_for_item': lambda item: self.owner,
                'lock_bindings': [{'path': str(self.lockpath), 'device': self.lockpath.stat().st_dev,
                                   'inode': self.lockpath.stat().st_ino}],
                'checkpoint_binding': self.owner.checkpoint_binding,
                'source_contract_ref': self.owner.input_ref,
                'source_review_ref': self.owner.input_ref,
                'calendar_ref': self.owner.input_ref,
                'items': [{'symbol': self.owner.symbol, 'target_date': self.owner.target,
                    'prior_selection': self.owner.prior, 'input_ref': self.owner.input_ref,
                    'expected_input_sha256': self.owner.input_ref['sha256']}]}

    def test_missing_registry_does_not_construct_owner(self):
        bridge = self.bridge()
        result = bridge.dispatch('fixture', 'env')
        self.assertEqual(result['status'], 'BLOCKED_NO_TRUSTED_OWNER_BINDING')
        self.assertEqual(result['jobs_started'], 0)
        self.assertFalse(self.entered)

    def test_exact_run_environment_binding_required(self):
        bridge = self.bridge()
        bridge.TRUSTED_RUNS[('fixture', 'env')] = self.record()
        result = bridge.dispatch('fixture', 'other-env')
        self.assertEqual(result['jobs_started'], 0)
        self.assertEqual(self.owner.compute_calls, 0)

    def test_missing_source_contract_blocks_before_owner_context(self):
        bridge = self.bridge()
        record = self.record()
        del record['source_review_ref']
        bridge.TRUSTED_RUNS[('fixture', 'env')] = record
        result = bridge.dispatch('fixture', 'env')
        self.assertEqual(result['status'], 'BLOCKED_OWNER_CONTRACT')
        self.assertEqual(result['jobs_started'], 0)
        self.assertEqual(list((self.owner.root / 'claims').iterdir()), [])

    def test_requested_stage_cannot_advance_capture_to_compute(self):
        bridge = self.bridge()
        bridge.TRUSTED_RUNS[('fixture', 'env')] = self.record()
        result = bridge.dispatch('fixture', 'env', stage='capture_convert')
        self.assertEqual(result['jobs_started'], 0)
        self.assertEqual(result['status'], 'BLOCKED_OWNER_STAGE')

    def test_valid_private_binding_preserves_pending_business_acceptance(self):
        bridge = self.bridge()
        bridge.TRUSTED_RUNS[('fixture', 'env')] = self.record()
        result = bridge.dispatch('fixture', 'env')
        self.assertEqual(result['status'], 'OWNER_STAGES_AWAIT_SEAL_AND_INDEPENDENT_REVIEW')
        self.assertEqual(result['items'][0]['phase'], 'PERSISTED_AWAIT_OWNER_SEAL_AND_INDEPENDENT_SAMPLE')
        self.assertFalse(result['production_allowed'])
        self.assertFalse(result['business_accepted'])
        self.assertFalse(result['natural_verified'])
        self.assertEqual((self.owner.compute_calls, self.owner.writer_calls), (1, 1))
        self.assertFalse(self.entered)

    def test_failed_writer_is_unknown_and_never_blindly_replayed(self):
        bridge = self.bridge()
        self.owner.fail_writer = True
        bridge.TRUSTED_RUNS[('fixture', 'env')] = self.record()
        first = bridge.dispatch('fixture', 'env')
        self.assertEqual(first['status'], 'UNKNOWN_RECONCILIATION_REQUIRED')
        self.assertEqual(first['items'][0]['phase'], 'UNKNOWN_NO_BLIND_RETRY')
        second = bridge.dispatch('fixture', 'env')
        self.assertEqual(second['status'], 'UNKNOWN_RECONCILIATION_REQUIRED')
        self.assertEqual((self.owner.compute_calls, self.owner.writer_calls), (1, 1))

    def test_changed_source_snapshot_blocks_before_stock_start(self):
        bridge = self.bridge()
        bridge.TRUSTED_RUNS[('fixture', 'env')] = self.record()
        (self.owner.root / self.owner.input_ref['path']).write_bytes(b'changed')
        result = bridge.dispatch('fixture', 'env')
        self.assertEqual(result['status'], 'BLOCKED_OWNER_CONTRACT')
        self.assertEqual(result['jobs_started'], 0)
        self.assertEqual(list((self.owner.root / 'claims').iterdir()), [])

    def test_different_parent_directory_cannot_substitute_original_lock(self):
        bridge = self.bridge()
        record = self.record()
        other = self.owner.root / 'different_parent'
        other.mkdir()
        self.lockpath = other / 'OTHER_LOCK'
        self.lockpath.touch()
        bridge.TRUSTED_RUNS[('fixture', 'env')] = record
        result = bridge.dispatch('fixture', 'env')
        self.assertEqual(result['status'], 'BLOCKED_OWNER_CONTRACT')
        self.assertEqual(result['jobs_started'], 0)
        self.assertEqual((self.owner.compute_calls, self.owner.writer_calls), (0, 0))

    def test_descriptor_without_lock_is_not_owner_evidence(self):
        bridge = self.bridge()
        record = self.record()
        @contextlib.contextmanager
        def unheld():
            fd = os.open(self.lockpath, os.O_RDWR)
            try:
                st = os.fstat(fd)
                yield [(self.lockpath, fd, st.st_dev, st.st_ino)]
            finally:
                os.close(fd)
        record['owner_context'] = unheld
        bridge.TRUSTED_RUNS[('fixture', 'env')] = record
        result = bridge.dispatch('fixture', 'env')
        self.assertEqual(result['status'], 'BLOCKED_OWNER_CONTRACT')
        self.assertEqual(result['jobs_started'], 0)

    def test_other_open_description_lock_cannot_prove_owner_descriptor(self):
        bridge = self.bridge()
        record = self.record()
        @contextlib.contextmanager
        def wrong_descriptor():
            actual = os.open(self.lockpath, os.O_RDWR)
            unheld = os.open(self.lockpath, os.O_RDWR)
            try:
                fcntl.flock(actual, fcntl.LOCK_EX | fcntl.LOCK_NB)
                self.entered = True
                st = os.fstat(unheld)
                yield [(self.lockpath, unheld, st.st_dev, st.st_ino)]
            finally:
                self.entered = False
                os.close(unheld)
                os.close(actual)
        record['owner_context'] = wrong_descriptor
        bridge.TRUSTED_RUNS[('fixture', 'env')] = record
        result = bridge.dispatch('fixture', 'env')
        self.assertEqual(result['status'], 'BLOCKED_OWNER_CONTRACT')
        self.assertEqual(result['jobs_started'], 0)
        self.assertEqual((self.owner.compute_calls, self.owner.writer_calls), (0, 0))

    def test_finalize_requires_independent_sample_and_never_runs_compute(self):
        bridge = self.bridge()
        record = self.record()
        record.update(stage='finalize', owner_runtime=self.owner,
                      prior_catalog_ref=self.owner.input_ref, owner_manifest_ref=self.owner.input_ref,
                      destination='SYNTHETIC_CATALOG.json')
        bridge.TRUSTED_RUNS[('fixture', 'env')] = record
        result = bridge.dispatch('fixture', 'env', stage='finalize')
        self.assertEqual(result['status'], 'BLOCKED_OWNER_CONTRACT')
        self.assertEqual((self.owner.compute_calls, self.owner.writer_calls), (0, 0))

    def test_finalize_route_calls_original_stage_without_claiming_delivery(self):
        bridge = self.bridge()
        record = self.record()
        record.update(stage='finalize', owner_runtime=self.owner,
                      prior_catalog_ref=self.owner.input_ref, owner_manifest_ref=self.owner.input_ref,
                      independent_sample_ref=self.owner.input_ref, destination='SYNTHETIC_CATALOG.json')
        calls = []
        self.owner.finalizer = types.SimpleNamespace(
            build=lambda *refs: calls.append(refs) or {'schema': 'SYNTHETIC_ONLY', 'production_allowed': False},
            write_new=lambda destination, value: self.owner.save(destination, value))
        bridge.TRUSTED_RUNS[('fixture', 'env')] = record
        result = bridge.dispatch('fixture', 'env', stage='finalize')
        self.assertEqual(result['status'], 'CATALOG_WRITTEN_AWAIT_DOWNSTREAM_REVIEW')
        self.assertEqual(calls, [(self.owner.input_ref,) * 3])
        self.assertEqual(json.loads(self.owner.checked(result['result_ref']))['schema'], 'SYNTHETIC_ONLY')
        self.assertFalse(result['business_accepted'])
        self.assertEqual((self.owner.compute_calls, self.owner.writer_calls), (0, 0))

    def test_select_route_requires_separate_catalog_and_review_binding(self):
        bridge = self.bridge()
        record = self.record()
        record.update(stage='select', owner_runtime=self.owner,
                      selector_args=types.SimpleNamespace(execute=True, review='SYNTHETIC'))
        self.owner.selector = types.SimpleNamespace(run=lambda args: self.fail('unbound selection'))
        bridge.TRUSTED_RUNS[('fixture', 'env')] = record
        result = bridge.dispatch('fixture', 'env', stage='select')
        self.assertEqual(result['status'], 'BLOCKED_OWNER_CONTRACT')
        record.update(catalog_ref=self.owner.input_ref, selection_review_ref=self.owner.input_ref)
        self.owner.selector = types.SimpleNamespace(run=lambda args: {'status': 'SYNTHETIC_SELECTED'})
        result = bridge.dispatch('fixture', 'env', stage='select')
        self.assertEqual(result['status'], 'SELECTOR_RETURNED_AWAIT_DOWNSTREAM_REVIEW')
        self.assertEqual(result['result']['status'], 'SYNTHETIC_SELECTED')
        self.assertFalse(result['business_accepted'])


if __name__ == '__main__':
    unittest.main()
