"""Evening current-success reads retain original publication and cold verification."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import test_m06_current_success_reader as support
from v5_shadow import m06_readonly, p0_hk_preselection, run_ledger
from v5_shadow.digests import canonical_bytes, sha256_json


class M06EveningReaderTests(unittest.TestCase):
    # Reuse helpers without importing another discoverable TestCase class.
    tearDownClass = classmethod(support.M06CurrentSuccessReaderTests.tearDownClass.__func__)
    write_pointer = support.M06CurrentSuccessReaderTests.write_pointer
    inventory = support.M06CurrentSuccessReaderTests.inventory
    venv_binding = support.M06CurrentSuccessReaderTests.venv_binding
    request = support.M06CurrentSuccessReaderTests.request

    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='m06-evening-reader-')
        cls.root = Path(cls.temporary.name).resolve()
        cls.python_sha256 = hashlib.sha256(Path(sys.executable).resolve().read_bytes()).hexdigest()
        cls.output = cls.root / 'output'
        cls.output.mkdir()
        (cls.output / '.v5-shadow-root').write_bytes(b'v5.shadow-root.v1\n')
        script = '''import sys,json,hashlib
from pathlib import Path
sys.path[:0]=[sys.argv[1],sys.argv[2]]
from fixtures.hk_preselection_verified_factory import create_verified_fixture
from v5_shadow.hk_preselection_publication import publish_verified_hk_preselection
from v5_shadow.digests import canonical_bytes,sha256_json
root=Path(sys.argv[3])
r=create_verified_fixture(root,eligibility='20261007',master_capture_time='17:30:15')
entry=json.loads((root/'latest.json').read_bytes())['entries']['20261008/HK_CONNECT_D1_TOP100_0_2']
m=json.loads((root/entry['manifest_relative']).read_bytes());m['captured_at']='2026-10-07T17:31:00+08:00'
(root/entry['manifest_relative']).write_bytes(canonical_bytes(m))
s=json.loads((root/entry['receipt_relative']).read_bytes());s.update(finished_at='2026-10-07T17:32:00+08:00',manifest_sha256=sha256_json(m))
(root/entry['receipt_relative']).write_bytes(canonical_bytes(s))
r['files']={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}
r['expected_source'].update(manifest_sha256=sha256_json(m),receipt_sha256=sha256_json(s))
i=dict(lane='hk_preselection',target_date=r['target_date'],research_cutoff=r['research_cutoff'],input_sha256='a'*64,code_sha256='b'*64,config_sha256='c'*64,dependency_sha256='d'*64)
p=dict(schema_version='v5.hk_preselection_producer_receipt.v1',status='READY',verified_source_reference=r['expected_source'],production_method='EXISTING_VERIFIED_POOL',original_result=dict(r['expected_source'],status='READY'),model_weights_reverified=False,fixture_only=True,computation_identity=i)
reference=publish_verified_hk_preselection(r,bound_root=Path(sys.argv[4]),producer_receipt=p)
print(json.dumps(dict(reference=reference,producer=p,identity=i)))
'''
        process = subprocess.run([sys.executable, '-I', '-B', '-c', script,
            str(support.BASE / 'source_owners/m06/V5/src'), str(support.BASE / 'tests'),
            str(cls.root / 'source'), str(cls.output)], capture_output=True, text=True)
        if process.returncode:
            raise AssertionError(process.stderr)
        fixture = json.loads(process.stdout)
        cls.reference, cls.producer, cls.m06_identity = [fixture[k] for k in ('reference', 'producer', 'identity')]
        cls.m06_root = cls.output / '.m06-ledger'
        cls.m06_root.mkdir()
        (cls.m06_root / '.v5-daily-run-ledger').write_bytes(run_ledger.MARKER)
        claim = run_ledger.claim_run(str(cls.m06_root), cls.m06_identity)
        cls.m06_state = run_ledger.finish_run(str(cls.m06_root), claim, dict(status='SUCCEEDED',
            product_reference=dict(committed_reference=cls.reference, producer_receipt=cls.producer),
            readback_verified=True, retry_safe_without_external_effect=False, reason_codes=[]))
        for saved in (cls.m06_state['latest_success'], *cls.m06_state['attempts']):
            saved.update(started_at='2026-10-07T17:35:00+08:00', finished_at='2026-10-07T17:40:00+08:00')
        cls.m06_path = cls.m06_root / 'hk_preselection/20261008' / (run_ledger.identity_key(cls.m06_identity) + '.json')
        cls.expected = json.loads((cls.output / cls.reference['artifact_relative']).read_bytes())

    def setUp(self):
        support.M06CurrentSuccessReaderTests.setUp(self)
        # Only test-owned ledger metadata changes; original publication bytes stay fixed.
        self.p0_identity = dict(self.p0_identity, research_cutoff='2026-10-07T17:35:00+08:00')
        self.p0_state['identity'] = self.p0_identity
        self.p0_state['identity_sha256'] = run_ledger.identity_key(self.p0_identity)
        self.p0_path = self.p0_path.with_name(self.p0_state['identity_sha256'] + '.json')
        self.pointer['p0_identity'] = self.p0_identity
        self.product.pop('completion_cutoff')
        self.product.update(date_contract='CLOSE_TO_NEXT_HK_SESSION_V1', scheduled_date='20261007',
            admission_cutoff=self.p0_identity['research_cutoff'], execution_deadline='2026-10-07T18:30:00+08:00',
            owner_contract_cutoff=self.reference['research_cutoff'])
        for saved in (self.p0_state['latest_success'], *self.p0_state['attempts']):
            saved.update(started_at='2026-10-07T17:35:00+08:00', finished_at='2026-10-07T17:45:00+08:00',
                product_reference=self.product)
        self.save_product(self.product)

    def save_product(self, product):
        state = copy.deepcopy(self.p0_state)
        state['latest_success']['product_reference'] = product
        self.p0_path.write_bytes(canonical_bytes(state))
        self.pointer['product_sha256'] = sha256_json(product)
        return state

    def validate(self):
        return m06_readonly.validate_current_success(self.binding, self.pointer)

    def test_expired_valid_evening_success_reads_identical_original_artifact_readonly(self):
        self.write_pointer()
        before = self.inventory()
        fixed = dict(bound_root=self.binding['bound_root'], python_executable=self.binding['python_executable'],
            committed_reference=self.reference)
        with patch.object(p0_hk_preselection, '_utc_now', side_effect=AssertionError('GET cannot gate on current time')):
            try:
                self.assertEqual(self.validate(), fixed)
            except ValueError as error:
                self.fail('Valid evening current success rejected: ' + str(error))
            actual = m06_readonly.read_record(self.config, {})
        self.assertEqual(actual, m06_readonly.read_record(dict(self.config, m06_hk_preselection_binding=fixed), {}))
        self.assertEqual(actual[0]['payload']['artifact'], self.expected)
        status, value, headers = self.request()
        self.assertEqual(status, 200, value)
        self.assertEqual(value['artifact'], self.expected)
        self.assertEqual(headers['Cache-Control'], 'no-store')
        self.assertEqual(self.inventory(), before)

    def test_evening_exact_deadline_completion_is_rejected_for_each_ledger(self):
        for path, original in ((self.p0_path, self.p0_state), (self.m06_path, self.m06_state)):
            state = copy.deepcopy(original)
            state['latest_success']['finished_at'] = self.product['execution_deadline']
            path.write_bytes(canonical_bytes(state))
            try:
                with self.subTest(path=path.name), self.assertRaisesRegex(ValueError, 'M06_CURRENT_EXECUTION_DEADLINE'):
                    self.validate()
            finally:
                path.write_bytes(canonical_bytes(original))

    def test_evening_dates_and_cutoff_fields_fail_closed_even_when_rehashed(self):
        changes = [('date_contract', 'ARBITRARY_FUTURE'), ('scheduled_date', '20261006'),
            ('scheduled_date', '2026-10-07'), ('admission_cutoff', '2026-10-08T08:01:00+08:00'),
            ('execution_deadline', '2026-10-08T08:30:00+08:00'),
            ('execution_deadline', '2026-10-07T17:35:00+08:00'),
            ('execution_deadline', '2026-10-07T17:30:00+08:00'),
            ('execution_deadline', '2026-10-07T18:30:00'),
            ('owner_contract_cutoff', '2026-10-08T09:21:00+08:00'),
            ('owner_contract_cutoff', '2026-10-07T19:00:00+08:00'),
            ('completion_cutoff', self.reference['research_cutoff'])]
        for field, value in changes:
            with self.subTest(field=field, value=value):
                self.save_product(dict(self.product, **{field: value}))
                with self.assertRaises(ValueError):
                    self.validate()
        for field in ('date_contract', 'scheduled_date', 'execution_deadline', 'owner_contract_cutoff'):
            with self.subTest(missing=field):
                product = dict(self.product)
                product.pop(field)
                self.save_product(product)
                with self.assertRaises(ValueError):
                    self.validate()

    def test_reference_signal_and_eligibility_must_equal_scheduled_date(self):
        for field in ('signal_date', 'eligibility_source_date'):
            reference = dict(self.reference, **{field: '20261006'})
            product = dict(self.product, committed_reference=reference)
            self.save_product(product)
            self.pointer['committed_reference'] = reference
            state = copy.deepcopy(self.m06_state)
            state['latest_success']['product_reference']['committed_reference'] = reference
            self.m06_path.write_bytes(canonical_bytes(state))
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.validate()

    def test_target_must_be_exact_next_original_hk_session(self):
        # Align all requested date fields but choose D whose next session is Oct 7, not Oct 8.
        scheduled = '20261006'
        identity = dict(self.p0_identity, research_cutoff='2026-10-06T17:35:00+08:00')
        reference = dict(self.reference, signal_date=scheduled, eligibility_source_date=scheduled)
        product = dict(self.product, scheduled_date=scheduled, admission_cutoff=identity['research_cutoff'],
            execution_deadline='2026-10-06T18:30:00+08:00', committed_reference=reference)
        state = self.save_product(product)
        state.update(identity=identity, identity_sha256=run_ledger.identity_key(identity))
        state['latest_success']['finished_at'] = '2026-10-06T17:45:00+08:00'
        self.p0_path.with_name(state['identity_sha256'] + '.json').write_bytes(canonical_bytes(state))
        self.pointer.update(p0_identity=identity, committed_reference=reference)
        m06 = copy.deepcopy(self.m06_state)
        m06['latest_success']['finished_at'] = '2026-10-06T17:40:00+08:00'
        m06['latest_success']['product_reference']['committed_reference'] = reference
        self.m06_path.write_bytes(canonical_bytes(m06))
        with self.assertRaises(ValueError):
            self.validate()

    def test_both_saved_finished_at_values_must_meet_real_execution_deadline(self):
        for path, original in ((self.p0_path, self.p0_state), (self.m06_path, self.m06_state)):
            for finished in ('2026-10-07T18:30:00.000001+08:00', '2026-10-08T09:19:00+08:00',
                    '2026-10-07T17:40:00', None, 'invalid'):
                state = copy.deepcopy(original)
                state['latest_success']['finished_at'] = finished
                # A fabricated alternate key cannot conceal the actual ledger timestamp.
                state['latest_success']['completed_at'] = '2026-10-07T17:40:00+08:00'
                path.write_bytes(canonical_bytes(state))
                try:
                    with self.subTest(path=path.name, finished=finished), self.assertRaises(ValueError):
                        self.validate()
                finally:
                    path.write_bytes(canonical_bytes(original))
            state = copy.deepcopy(original)
            state['latest_success'].pop('finished_at')
            path.write_bytes(canonical_bytes(state))
            try:
                with self.subTest(path=path.name, missing=True), self.assertRaises(ValueError):
                    self.validate()
            finally:
                path.write_bytes(canonical_bytes(original))

    def test_rehashed_evening_product_retains_exact_identity_and_producer_mapping(self):
        changes = dict(owner='OTHER', bound_root=str(self.p0_root), p0_ledger_run_id='0' * 32,
            m06_ledger_run_id='0' * 32, request_sha256='0' * 64, producer_receipt_sha256='0' * 64,
            m06_computation_identity=dict(self.m06_identity, dependency_sha256='0' * 64))
        for field, value in changes.items():
            self.save_product(dict(self.product, **{field: value}))
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.validate()

    def test_evening_producer_identity_tampering_cannot_be_rehashed_away(self):
        state = copy.deepcopy(self.m06_state)
        producer = state['latest_success']['product_reference']['producer_receipt']
        producer['computation_identity'] = dict(self.m06_identity, dependency_sha256='0' * 64)
        digest = sha256_json(producer)
        reference = copy.deepcopy(self.reference)
        reference['producer_reference']['sha256'] = digest
        state['latest_success']['product_reference']['committed_reference'] = reference
        self.m06_path.write_bytes(canonical_bytes(state))
        self.save_product(dict(self.product, committed_reference=reference, producer_receipt_sha256=digest))
        self.pointer['committed_reference'] = reference
        with self.assertRaisesRegex(ValueError, 'M06_CURRENT_PRODUCT_IDENTITY'):
            self.validate()

    def test_evening_calendar_keeps_original_raw_source_pin(self):
        with patch.object(m06_readonly, 'MANIFEST_SHA256', '0' * 64), self.assertRaisesRegex(ValueError, 'M06_OWNER_MANIFEST_SHA'):
            self.validate()

    def test_evening_preserves_venv_pin_and_post_read_snapshot_checks(self):
        binding = self.venv_binding()
        self.write_pointer()
        config = dict(self.config, m06_hk_preselection_binding=binding)
        self.assertEqual(m06_readonly.read_record(config, {})[0]['payload']['artifact'], self.expected)
        original = subprocess.run
        def changed(*args, **kwargs):
            result = original(*args, **kwargs)
            state = copy.deepcopy(self.p0_state)
            state['attempts'][0]['finished_at'] = '2026-10-07T17:46:00+08:00'
            self.p0_path.write_bytes(canonical_bytes(state))
            return result
        with patch.object(m06_readonly.subprocess, 'run', side_effect=changed), self.assertRaisesRegex(ValueError, 'M06_CURRENT_SUCCESS_CHANGED'):
            m06_readonly.read_record(config, {})


if __name__ == '__main__':
    unittest.main(verbosity=2)
