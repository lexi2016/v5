"""Current-success projection uses exact saved ledgers and the original cold reader."""
import copy
import hashlib
import http.client
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

BASE = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(BASE / 'src'), str(BASE / 'tests')]
from v5_shadow import m06_readonly, run_ledger
from v5_shadow.digests import canonical_bytes, sha256_json

POINTER = '.m06-current-success.json'


class M06CurrentSuccessReaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='m06-current-reader-')
        cls.root = Path(cls.temporary.name).resolve()
        cls.python_sha256 = hashlib.sha256(Path(sys.executable).resolve().read_bytes()).hexdigest()
        cls.output = cls.root / 'output'
        cls.output.mkdir()
        (cls.output / '.v5-shadow-root').write_bytes(b'v5.shadow-root.v1\n')
        owner = BASE / 'source_owners/m06'
        script = '''import sys,json
from pathlib import Path
sys.path[:0]=[sys.argv[1],sys.argv[2]]
from fixtures.hk_preselection_verified_factory import create_verified_fixture
from v5_shadow.hk_preselection_publication import publish_verified_hk_preselection
r=create_verified_fixture(Path(sys.argv[3]))
i=dict(lane='hk_preselection',target_date=r['target_date'],research_cutoff=r['research_cutoff'],input_sha256='a'*64,code_sha256='b'*64,config_sha256='c'*64,dependency_sha256='d'*64)
p=dict(schema_version='v5.hk_preselection_producer_receipt.v1',status='READY',verified_source_reference=r['expected_source'],production_method='EXISTING_VERIFIED_POOL',original_result=dict(r['expected_source'],status='READY'),model_weights_reverified=False,fixture_only=True,computation_identity=i)
reference=publish_verified_hk_preselection(r,bound_root=Path(sys.argv[4]),producer_receipt=p)
print(json.dumps(dict(reference=reference,producer=p,identity=i)))
'''
        process = subprocess.run([sys.executable, '-I', '-B', '-c', script,
            str(owner / 'V5/src'), str(BASE / 'tests'), str(cls.root / 'source'), str(cls.output)],
            capture_output=True, text=True)
        if process.returncode:
            raise AssertionError(process.stderr)
        fixture = json.loads(process.stdout)
        cls.reference, cls.producer, cls.m06_identity = [fixture[key] for key in ('reference', 'producer', 'identity')]
        cls.m06_root = cls.output / '.m06-ledger'
        cls.m06_root.mkdir()
        (cls.m06_root / '.v5-daily-run-ledger').write_bytes(run_ledger.MARKER)
        claim = run_ledger.claim_run(str(cls.m06_root), cls.m06_identity)
        cls.m06_state = run_ledger.finish_run(str(cls.m06_root), claim, dict(status='SUCCEEDED',
            product_reference=dict(committed_reference=cls.reference, producer_receipt=cls.producer),
            readback_verified=True, retry_safe_without_external_effect=False, reason_codes=[]))
        cls.m06_path = cls.m06_root / 'hk_preselection/20261008' / (run_ledger.identity_key(cls.m06_identity) + '.json')
        cls.expected = json.loads((cls.output / cls.reference['artifact_relative']).read_bytes())

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='m06-current-p0-')
        self.addCleanup(self.temp.cleanup)
        self.p0_root = Path(self.temp.name).resolve()
        (self.p0_root / '.v5-daily-run-ledger').write_bytes(run_ledger.MARKER)
        self.m06_path.write_bytes(canonical_bytes(self.m06_state))
        self.addCleanup(self.m06_path.write_bytes, canonical_bytes(self.m06_state))
        self.pointer_path = self.output / POINTER
        self.addCleanup(lambda: self.pointer_path.unlink(missing_ok=True))
        self.p0_identity = dict(self.m06_identity, input_sha256='e' * 64,
            research_cutoff='2026-10-08T08:01:00+08:00')
        claim = run_ledger.claim_run(str(self.p0_root), self.p0_identity)
        self.product = dict(owner='M06', p0_ledger_run_id=claim['run_id'],
            m06_ledger_run_id=self.m06_state['latest_success']['run_id'],
            m06_computation_identity=self.m06_identity, committed_reference=self.reference,
            bound_root=str(self.output), request_sha256=self.p0_identity['input_sha256'],
            admission_cutoff=self.p0_identity['research_cutoff'], completion_cutoff=self.reference['research_cutoff'],
            producer_receipt_sha256=sha256_json(self.producer), row_count=100, fixture_only=True)
        self.p0_state = run_ledger.finish_run(str(self.p0_root), claim, dict(status='SUCCEEDED',
            product_reference=self.product, readback_verified=True,
            retry_safe_without_external_effect=False, reason_codes=[]))
        self.p0_path = self.p0_root / 'hk_preselection/20261008' / (run_ledger.identity_key(self.p0_identity) + '.json')
        self.pointer = dict(schema_version='v5.m06_current_success.v1', p0_identity=self.p0_identity,
            p0_run_id=claim['run_id'], m06_identity=self.m06_identity,
            m06_run_id=self.m06_state['latest_success']['run_id'], committed_reference=self.reference,
            product_sha256=sha256_json(self.product))
        self.binding = dict(bound_root=str(self.output), python_executable=str(Path(sys.executable).resolve()),
            python_sha256=self.python_sha256, current_success_ledger_root=str(self.p0_root))
        api = self.p0_root / 'api'
        api.mkdir()
        (api / '.v5-module-root').write_bytes(b'v5.module-root.v1:source_bundle\n')
        self.config = dict(schema_version='v5.module_api.v1', module_id='source_bundle',
            release_id='m06-current-fixture', data_root=str(api), routes=[m06_readonly.ROUTE],
            m06_hk_preselection_binding=self.binding)

    def api(self):
        for name in ('read_current_success', 'validate_current_success'):
            self.assertTrue(callable(getattr(m06_readonly, name, None)), name + ' is missing')
        return m06_readonly

    def write_pointer(self, pointer=None):
        self.pointer_path.write_bytes(canonical_bytes(self.pointer if pointer is None else pointer))

    def venv_binding(self):
        root = self.p0_root / 'reader-venv'
        (root / 'bin').mkdir(parents=True)
        realpath = Path(sys.executable).resolve()
        cfg = root / 'pyvenv.cfg'
        cfg.write_text('home = ' + str(realpath.parent) + '\ninclude-system-site-packages = true\n')
        launch = root / 'bin/python'
        launch.symlink_to(realpath)
        return dict(self.binding, python_executable=str(launch), python_venv=dict(root=str(root),
            realpath=str(realpath), pyvenv_cfg_sha256=hashlib.sha256(cfg.read_bytes()).hexdigest(),
            symlink_sha256=hashlib.sha256(os.readlink(launch).encode()).hexdigest()))

    def inventory(self):
        return {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
            for root in (self.root, self.p0_root) for path in root.rglob('*') if path.is_file()}

    def request(self, path=None, method='GET'):
        from v5_shadow.module_api import create_module_server
        server = create_module_server(self.config)
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        try:
            client = http.client.HTTPConnection('127.0.0.1', server.server_address[1], timeout=60)
            client.request(method, path or m06_readonly.ROUTE)
            response = client.getresponse()
            value = json.loads(response.read())
            result = response.status, value, dict(response.getheaders())
            client.close()
            return result
        finally:
            server.shutdown()
            thread.join()
            server.server_close()

    def test_current_binding_is_accepted(self):
        try:
            m06_readonly.validate_binding(self.config)
        except ValueError as error:
            self.fail('Exclusive current-success binding is missing: ' + str(error))

    def test_binding_modes_are_exclusive_and_fixed_binding_is_unchanged(self):
        fixed = dict(bound_root=str(self.output), python_executable=sys.executable, committed_reference=self.reference)
        m06_readonly.validate_binding(dict(self.config, m06_hk_preselection_binding=fixed))
        for extras in ({'committed_reference': self.reference}, {'pointer_relative': 'other.json'}, {'command': 'invoke'}):
            with self.subTest(extras=extras), self.assertRaises(ValueError):
                m06_readonly.validate_binding(dict(self.config, m06_hk_preselection_binding=dict(self.binding, **extras)))
        for field in self.binding:
            binding = dict(self.binding, **{field: '../relative'})
            with self.subTest(field=field), self.assertRaises(ValueError):
                m06_readonly.validate_binding(dict(self.config, m06_hk_preselection_binding=binding))

    def test_current_binding_requires_an_executable_pin(self):
        binding = dict(self.binding)
        binding.pop('python_sha256')
        with self.assertRaises(ValueError):
            m06_readonly.validate_binding(dict(self.config, m06_hk_preselection_binding=binding))

    def test_pinned_venv_leaf_retains_original_cold_reader_projection(self):
        api = self.api()
        binding = self.venv_binding()
        config = dict(self.config, m06_hk_preselection_binding=binding)
        try:
            api.validate_binding(config)
        except ValueError as error:
            self.fail('Pinned venv reader binding is not supported: ' + str(error))
        self.write_pointer()
        before = self.inventory()
        fixed = api.validate_current_success(binding, self.pointer)
        self.assertEqual(fixed['python_executable'], binding['python_executable'])
        self.assertEqual(set(fixed), {'bound_root', 'python_executable', 'committed_reference'})
        result = api.read_record(config, {})
        self.assertEqual(result[0]['payload']['artifact'], self.expected)
        self.assertEqual(self.inventory(), before)

    def test_venv_pin_tampering_is_rejected(self):
        api = self.api()
        binding = self.venv_binding()
        api.validate_current_success(binding, self.pointer)
        candidates = [dict(binding, python_sha256='0' * 64)]
        for field in ('pyvenv_cfg_sha256', 'symlink_sha256'):
            value = copy.deepcopy(binding)
            value['python_venv'][field] = '0' * 64
            candidates.append(value)
        for candidate in candidates:
            with self.subTest(candidate=candidate), self.assertRaises(ValueError):
                api.validate_current_success(candidate, self.pointer)

    def test_same_byte_venv_launch_replacement_during_cold_read_is_rejected(self):
        api = self.api()
        binding = self.venv_binding()
        api.validate_current_success(binding, self.pointer)
        self.write_pointer()
        original = subprocess.run
        def replaced(*args, **kwargs):
            result = original(*args, **kwargs)
            launch = Path(binding['python_executable'])
            temporary = launch.with_name('replacement-python')
            temporary.symlink_to(os.readlink(launch))
            os.replace(temporary, launch)
            return result
        with patch.object(api.subprocess, 'run', side_effect=replaced), self.assertRaisesRegex(ValueError, 'M06_PYTHON_LAUNCH_CHANGED'):
            api.read_record(dict(self.config, m06_hk_preselection_binding=binding), {})

    def test_missing_pointer_is_none_without_starting_original_reader(self):
        api = self.api()
        before = self.inventory()
        with patch.object(api, 'owner_root', side_effect=AssertionError('Missing pointer started a reader')):
            self.assertIsNone(api.read_current_success(self.binding))
            self.assertIsNone(api.read_record(self.config, {}))
        self.assertEqual(self.inventory(), before)

    def test_exact_dual_ledger_success_returns_fixed_binding_readonly(self):
        api = self.api()
        self.write_pointer()
        before = self.inventory()
        self.assertEqual(api.read_current_success(self.binding), self.pointer)
        self.assertEqual(api.validate_current_success(self.binding, self.pointer),
            dict(bound_root=self.binding['bound_root'], python_executable=self.binding['python_executable'],
                committed_reference=self.reference))
        self.assertEqual(self.inventory(), before)

    def test_pointer_rejects_extra_missing_or_wrong_schema(self):
        api = self.api()
        candidates = [dict(self.pointer, unexpected='invoke'), dict(self.pointer, schema_version='v5.wrong.v1')]
        for field in self.pointer:
            candidate = copy.deepcopy(self.pointer)
            candidate.pop(field)
            candidates.append(candidate)
        for candidate in candidates:
            with self.subTest(candidate=candidate), self.assertRaises(ValueError):
                api.validate_current_success(self.binding, candidate)

    def test_pointer_requires_exact_m06_lane_target_and_cutoff(self):
        api = self.api()
        for identity in ('p0_identity', 'm06_identity'):
            for key, value in (('lane', 'us_mapping'), ('target_date', '20261009'),
                    ('research_cutoff', '2026-10-07T09:20:00+08:00')):
                candidate = copy.deepcopy(self.pointer)
                candidate[identity][key] = value
                with self.subTest(identity=identity, key=key), self.assertRaises(ValueError):
                    api.validate_current_success(self.binding, candidate)

    def test_pointer_run_reference_or_product_digest_mismatch_is_rejected(self):
        api = self.api()
        for key in ('p0_run_id', 'm06_run_id', 'product_sha256'):
            candidate = copy.deepcopy(self.pointer)
            candidate[key] = '0' * (64 if key == 'product_sha256' else 32)
            with self.subTest(key=key), self.assertRaises(ValueError):
                api.validate_current_success(self.binding, candidate)
        candidate = copy.deepcopy(self.pointer)
        candidate['committed_reference']['artifact_sha256'] = '0' * 64
        with self.assertRaises(ValueError):
            api.validate_current_success(self.binding, candidate)

    def test_each_ledger_must_contain_exact_verified_latest_success(self):
        api = self.api()
        for path, state in ((self.p0_path, self.p0_state), (self.m06_path, self.m06_state)):
            for change in ({'status': 'FAILED'}, {'status': 'RUNNING'}, {'readback_verified': False},
                    {'readback_verified': 1}, {'run_id': '0' * 32}):
                value = copy.deepcopy(state)
                value['latest_success'].update(change)
                path.write_bytes(canonical_bytes(value))
                try:
                    with self.subTest(path=path, change=change), self.assertRaises(ValueError):
                        api.validate_current_success(self.binding, self.pointer)
                finally:
                    path.write_bytes(canonical_bytes(state))
            value = copy.deepcopy(state)
            value['latest_success'] = None
            path.write_bytes(canonical_bytes(value))
            try:
                with self.subTest(path=path, missing=True), self.assertRaises(ValueError):
                    api.validate_current_success(self.binding, self.pointer)
            finally:
                path.write_bytes(canonical_bytes(state))

    def test_rehashed_p0_product_cannot_change_identity_mapping(self):
        api = self.api()
        changes = {'bound_root': str(self.p0_root), 'p0_ledger_run_id': '0' * 32,
            'm06_ledger_run_id': '0' * 32, 'request_sha256': '0' * 64,
            'admission_cutoff': '2026-10-08T08:02:00+08:00', 'completion_cutoff': '2026-10-08T09:21:00+08:00',
            'm06_computation_identity': dict(self.m06_identity, dependency_sha256='0' * 64)}
        for field, value in changes.items():
            state = copy.deepcopy(self.p0_state)
            state['latest_success']['product_reference'][field] = value
            pointer = dict(self.pointer, product_sha256=sha256_json(state['latest_success']['product_reference']))
            self.p0_path.write_bytes(canonical_bytes(state))
            try:
                with self.subTest(field=field), self.assertRaises(ValueError):
                    api.validate_current_success(self.binding, pointer)
            finally:
                self.p0_path.write_bytes(canonical_bytes(self.p0_state))

    def test_entire_p0_product_is_hashed(self):
        api = self.api()
        state = copy.deepcopy(self.p0_state)
        state['latest_success']['product_reference']['row_count'] = 99
        self.p0_path.write_bytes(canonical_bytes(state))
        with self.assertRaises(ValueError):
            api.validate_current_success(self.binding, self.pointer)

    def test_m06_producer_receipt_hash_must_equal_committed_reference(self):
        api = self.api()
        state = copy.deepcopy(self.m06_state)
        state['latest_success']['product_reference']['producer_receipt']['forged_evidence'] = True
        self.m06_path.write_bytes(canonical_bytes(state))
        with self.assertRaises(ValueError):
            api.validate_current_success(self.binding, self.pointer)

    def test_rehashed_ledgers_cannot_admit_unsafe_reference_paths(self):
        api = self.api()
        for field in ('artifact_relative', 'manifest_relative', 'receipt_relative', 'producer_reference', 'reader_reference'):
            for relative in ('../outside.json', '/tmp/outside.json', 'other/artifact.json'):
                reference = copy.deepcopy(self.reference)
                if field.endswith('_reference'):
                    reference[field]['relative'] = relative
                else:
                    reference[field] = relative
                p0 = copy.deepcopy(self.p0_state)
                m06 = copy.deepcopy(self.m06_state)
                for state in (p0, m06):
                    state['latest_success']['product_reference']['committed_reference'] = reference
                pointer = dict(self.pointer, committed_reference=reference,
                    product_sha256=sha256_json(p0['latest_success']['product_reference']))
                self.p0_path.write_bytes(canonical_bytes(p0))
                self.m06_path.write_bytes(canonical_bytes(m06))
                try:
                    with self.subTest(field=field, relative=relative), self.assertRaises(ValueError):
                        api.validate_current_success(self.binding, pointer)
                finally:
                    self.p0_path.write_bytes(canonical_bytes(self.p0_state))
                    self.m06_path.write_bytes(canonical_bytes(self.m06_state))

    def test_shared_p0_and_m06_ledger_root_is_rejected(self):
        api = self.api()
        with self.assertRaises(ValueError):
            api.validate_current_success(dict(self.binding, current_success_ledger_root=str(self.m06_root)), self.pointer)

    def test_marker_symlink_pointer_symlink_and_nonregular_pointer_fail_closed(self):
        api = self.api()
        target = self.p0_root / 'pointer.json'
        target.write_bytes(canonical_bytes(self.pointer))
        self.pointer_path.symlink_to(target)
        with self.assertRaises((ValueError, OSError)):
            api.read_current_success(self.binding)
        self.pointer_path.unlink()
        os.mkfifo(self.pointer_path)
        with self.assertRaises((ValueError, OSError)):
            api.read_current_success(self.binding)
        self.pointer_path.unlink()
        marker = self.output / '.v5-shadow-root'
        raw = marker.read_bytes()
        marker.unlink()
        external_marker = self.p0_root / 'marker'
        external_marker.write_bytes(raw)
        marker.symlink_to(external_marker)
        try:
            with self.assertRaises((ValueError, OSError)):
                api.read_current_success(self.binding)
        finally:
            marker.unlink()
            marker.write_bytes(raw)

    def test_current_binding_rejects_symlink_roots_and_executable(self):
        api = self.api()
        for field in ('bound_root', 'python_executable', 'current_success_ledger_root'):
            link = self.p0_root / ('link-' + field)
            link.symlink_to(self.binding[field])
            binding = dict(self.binding, **{field: str(link)})
            with self.subTest(field=field), self.assertRaises((ValueError, OSError)):
                api.validate_current_success(binding, self.pointer)

    def test_symlink_ledger_files_are_rejected_without_writes(self):
        api = self.api()
        for path, state in ((self.p0_path, self.p0_state), (self.m06_path, self.m06_state)):
            target = self.p0_root / ('external-' + path.name)
            target.write_bytes(canonical_bytes(state))
            path.unlink()
            path.symlink_to(target)
            try:
                with self.subTest(path=path), self.assertRaises((ValueError, OSError)):
                    api.validate_current_success(self.binding, self.pointer)
            finally:
                path.unlink()
                path.write_bytes(canonical_bytes(state))

    def test_corrupt_json_and_unmarked_root_are_rejected(self):
        api = self.api()
        self.pointer_path.write_bytes(b'{bad json')
        with self.assertRaises(ValueError):
            api.read_current_success(self.binding)
        self.pointer_path.unlink()
        with self.assertRaises((ValueError, OSError)):
            api.read_current_success(dict(self.binding, bound_root=str(self.p0_root)))

    def test_original_cold_record_is_identical_and_get_is_readonly(self):
        api = self.api()
        self.write_pointer()
        fixed = dict(bound_root=self.binding['bound_root'], python_executable=self.binding['python_executable'],
            committed_reference=self.reference)
        before = self.inventory()
        actual = api.read_record(self.config, {})
        expected = api.read_record(dict(self.config, m06_hk_preselection_binding=fixed), {})
        self.assertEqual(actual, expected)
        self.assertEqual(actual[0]['payload']['artifact'], self.expected)
        self.assertEqual(self.inventory(), before)
        self.assertNotIn('v5_shadow.hk_preselection_publication', sys.modules)

    def test_missing_pointer_api_is_not_configured_and_never_writes(self):
        self.api()
        before = self.inventory()
        status, value, _ = self.request()
        self.assertEqual(status, 200)
        self.assertEqual(value['status'], 'NOT_CONFIGURED')
        self.assertEqual(self.inventory(), before)

    def test_each_get_rereads_current_pointer_and_never_uses_stale_payload(self):
        self.api()
        self.write_pointer()
        from v5_shadow.module_api import create_module_server
        server = create_module_server(self.config)
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        def get():
            client = http.client.HTTPConnection('127.0.0.1', server.server_address[1], timeout=60)
            client.request('GET', m06_readonly.ROUTE)
            response = client.getresponse()
            result = response.status, json.loads(response.read()), dict(response.getheaders())
            client.close()
            return result
        try:
            status, value, headers = get()
            self.assertEqual(status, 200, value)
            self.assertEqual(value['artifact'], self.expected)
            self.assertEqual(headers['Cache-Control'], 'no-store')
            identity = dict(self.p0_identity, config_sha256='f' * 64)
            claim = run_ledger.claim_run(str(self.p0_root), identity)
            product = dict(self.product, p0_ledger_run_id=claim['run_id'])
            run_ledger.finish_run(str(self.p0_root), claim, dict(status='SUCCEEDED',
                product_reference=product, readback_verified=True,
                retry_safe_without_external_effect=False, reason_codes=[]))
            next_pointer = dict(self.pointer, p0_identity=identity, p0_run_id=claim['run_id'],
                product_sha256=sha256_json(product))
            self.write_pointer(next_pointer)
            self.p0_path.unlink()
            status, value, _ = get()
            self.assertEqual(status, 200, value)
            self.assertEqual(value['artifact'], self.expected)
            self.write_pointer(dict(next_pointer, product_sha256='0' * 64))
            status, value, _ = get()
            self.assertEqual(status, 409, value)
            self.assertNotIn('artifact', value)
            self.pointer_path.unlink()
            status, value, _ = get()
            self.assertEqual(status, 200, value)
            self.assertEqual(value['status'], 'NOT_CONFIGURED')
        finally:
            server.shutdown()
            thread.join()
            server.server_close()

    def test_pointer_change_during_original_cold_read_fails_closed(self):
        api = self.api()
        self.write_pointer()
        original = subprocess.run
        def changed(*args, **kwargs):
            result = original(*args, **kwargs)
            self.pointer_path.unlink()
            return result
        with patch.object(api.subprocess, 'run', side_effect=changed), self.assertRaises(ValueError):
            api.read_record(self.config, {})

    def test_each_ledger_change_during_original_cold_read_fails_closed(self):
        api = self.api()
        self.write_pointer()
        original = subprocess.run
        for path, state in ((self.p0_path, self.p0_state), (self.m06_path, self.m06_state)):
            def changed(*args, **kwargs):
                result = original(*args, **kwargs)
                value = copy.deepcopy(state)
                value['attempts'][0]['finished_at'] = '2026-10-08T02:00:01+00:00'
                path.write_bytes(canonical_bytes(value))
                return result
            try:
                with self.subTest(path=path), patch.object(api.subprocess, 'run', side_effect=changed), self.assertRaises(ValueError):
                    api.read_record(self.config, {})
            finally:
                path.write_bytes(canonical_bytes(state))

    def test_queries_and_post_cannot_select_publish_or_generate(self):
        self.api()
        self.write_pointer()
        before = self.inventory()
        for query in ('?target_date=20261009', '?reference=latest', '?pointer=other.json'):
            status, value, _ = self.request(path=m06_readonly.ROUTE + query)
            self.assertEqual(status, 409, value)
            self.assertNotIn('artifact', value)
        status, value, _ = self.request(method='POST')
        self.assertEqual(status, 405)
        self.assertEqual(value['reason_codes'], ['MODULE_READ_ONLY'])
        self.assertEqual(self.inventory(), before)


if __name__ == '__main__':
    unittest.main(verbosity=2)
