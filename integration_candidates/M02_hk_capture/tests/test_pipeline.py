"""Synthetic-only collector -> strict capture -> recovery -> independent reader.

No Futu import, sockets, real market inputs, scoring, or qualification claims.
"""
import copy
from datetime import datetime
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import socket
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'collector'))
sys.path.insert(0, str(ROOT / 'recovery/V5/src'))
from ops import macos_research_panel_daily as facade
from ops._macos_research_panel_daily_parts import hk_market_capture as candidate
from v5_shadow import hk_membership_recovery as recovery
from v5_shadow.membership_reader import read_private


class Frame:
    def __init__(self, rows):
        self.rows = rows
        self.columns = list(rows[0])
    def to_dict(self, orient):
        assert orient == 'records'
        return [dict(row) for row in self.rows]


class FakeContext:
    def __init__(self, target, owner):
        self.plate_calls = []
        self.quote_calls = []
        self.closed = False
        self.rows = [dict(code=f'HK.{i:05d}', name='SYNTHETIC TEST ISSUER',
            update_time=target, open_price=10.0, high_price=12.0, low_price=9.0,
            last_price=11.0, volume=1000, turnover=11000.0,
            outstanding_shares=1000000, circular_market_val=11000000.0,
            listing_date='2020-01-01', lot_size=100, stock_owner=None,
            stock_child_type='STOCK', sec_status='NORMAL') for i in range(1, 601)]
        self.rows[0]['stock_owner'] = owner
        self.lookup = {r['code']: r for r in self.rows}
    def get_plate_stock(self, plate):
        self.plate_calls.append(plate)
        return 0, Frame([dict(code=r['code'], stock_name=r['name']) for r in self.rows])
    def get_market_snapshot(self, codes):
        self.quote_calls.append(list(codes))
        return 0, Frame([self.lookup[c] for c in codes])
    def close(self):
        self.closed = True


def strict_load(raw):
    def reject(value):
        raise ValueError('NONFINITE:' + value)
    return json.loads(raw, parse_constant=reject)


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.target = datetime.now(ZoneInfo('Asia/Hong_Kong')).strftime('%Y%m%d')
        self.addCleanup(patch.stopall)
        patch.object(socket, 'socket', side_effect=AssertionError('LIVE_NETWORK_FORBIDDEN')).start()
        patch.dict(sys.modules, {'futu': None}).start()

    def capture(self, owner, module=candidate, suffix='capture'):
        directory = self.root / suffix
        directory.mkdir()
        manifest = directory / 'capture.json'
        context = FakeContext(self.target, owner)
        try:
            before = candidate._canonical_capture_bytes(candidate._sdk_json_value(context.rows))
        except TypeError:
            before = None  # Invalid-object case must reach the real collector.
        with patch.dict(os.environ, {'V35_HK_CAPTURE_PATH': str(manifest),
                'V35_HK_CAPTURE_RUN_ID': 'SYNTHETIC_TEST_ONLY_' + suffix}):
            result = module._collect_hk_futu_rows_body(facade.__dict__, self.target,
                context_factory=lambda: context, batch_size=200,
                minimum_universe_count=600, required_coverage_ratio=0.0)
        if before is not None:
            self.assertEqual(before, candidate._canonical_capture_bytes(candidate._sdk_json_value(context.rows)))
        self.assertEqual(context.plate_calls, list(facade.HKCONNECT_PLATE_CODES))
        self.assertEqual(len(context.quote_calls), 3)
        self.assertTrue(context.closed)
        raw = (directory / 'capture.capture.json').read_bytes()
        capture = strict_load(raw)
        seal = capture.pop('capture_sha256')
        self.assertEqual(seal, facade._canonical_sha(capture))
        capture['capture_sha256'] = seal
        self.assertEqual(candidate._canonical_capture_bytes(capture), raw)
        sdk = directory / 'capture.sdk.capture.json'
        self.assertEqual(strict_load(sdk.read_bytes())['status'], 'RAW_CAPTURED')
        self.assertEqual(result['row_count'], 600)
        for flag in facade.SAFETY_FLAGS:
            self.assertIs(result[flag], False)
        return capture, sdk, context

    def recover(self, sdk, suffix='membership'):
        output = self.root / suffix
        output.mkdir(mode=0o700)
        (output / '.v5-hk-membership-root').write_bytes(b'v5.hk-membership-root.v1\n')
        request = dict(sdk_path=str(sdk), sdk_sha256=hashlib.sha256(sdk.read_bytes()).hexdigest(),
                       output_root=str(output), target_date=self.target)
        result = recovery.run_recovery(request)
        self.assertEqual(result['status'], 'PRIVATE_MEMBERSHIP_PUBLISHED')
        self.assertEqual(result['code_count'], 600)
        self.assertEqual(len(result['files']), 7)
        self.assertFalse(result['natural_verified'])
        readback = read_private(output, result['files'], self.target)
        self.assertNotIn('error', readback)
        self.assertEqual(len(readback['codes']), 600)
        self.assertEqual(readback['source']['sha256'], result['readback']['source']['sha256'])
        self.assertEqual(readback['source']['producer_owner'], strict_load(sdk.read_bytes())['producer_owner'])
        for relative, sha in result['files'].items():
            self.assertEqual(hashlib.sha256((output / relative).read_bytes()).hexdigest(), sha)
        return result, output

    def test_nan_metadata_has_strict_json_and_matching_seal(self):
        try:
            capture, _, context = self.capture(float('nan'))
        except ValueError as error:
            self.fail('Missing metadata must serialize as null: ' + str(error))
        self.assertIsNone(capture['security_master_rows'][0]['stock_owner'])
        self.assertTrue(math.isnan(context.rows[0]['stock_owner']))
        self.assertEqual(capture['rows'][0]['close'], 11.0)
        self.assertEqual(capture['rows'][0]['volume'], 1000)

    def test_none_and_valid_string_preserved(self):
        for index, value in enumerate((None, 'HK.00700')):
            with self.subTest(value=value):
                capture, _, _ = self.capture(value, suffix='valid' + str(index))
                self.assertEqual(capture['security_master_rows'][0]['stock_owner'], value)

    def test_infinite_metadata_rejected_without_ready_capture(self):
        for index, value in enumerate((float('inf'), float('-inf'))):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'HK_SECURITY_MASTER_INFINITE_METADATA'):
                self.capture(value, suffix='inf' + str(index))
            self.assertFalse((self.root / ('inf' + str(index)) / 'capture.capture.json').exists())

    def test_unknown_object_rejected_not_made_known(self):
        with self.assertRaisesRegex(TypeError, 'not JSON serializable'):
            self.capture(object(), suffix='unknown')
        self.assertFalse((self.root / 'unknown/capture.capture.json').exists())

    def test_helper_preserves_finite_and_literal_text_without_qualification(self):
        for value in (None, 0, 123, 1.5, 'HK.00700', 'NaN', ''):
            self.assertEqual(candidate._normalize_security_master_metadata(value), value)
        # This helper is serialization, not security type/field admission.
        from v5_shadow.provider_evidence import normalize_security_references
        row = FakeContext(self.target, float('nan')).rows[0]
        normalized = normalize_security_references([row], captured_at=datetime.now(ZoneInfo('Asia/Hong_Kong')).isoformat())
        self.assertEqual(normalized['rows'][0]['field_status']['stock_owner'], 'UNKNOWN')
        self.assertEqual(normalized['rows'][0]['security_type'], 'UNVERIFIED')
        self.assertFalse(normalized['membership_verified'])

    def test_producer_contract_tamper_rejected(self):
        tampered = self.root / 'tampered-contract.json'
        tampered.write_bytes(recovery.PRODUCER_CONTRACT.read_bytes() + b' ')
        with patch.object(recovery, 'PRODUCER_CONTRACT', tampered):
            with self.assertRaisesRegex(ValueError, 'SDK_PRODUCER_CONTRACT_SHA'):
                recovery._producer_contract()

    def test_candidate_sdk_recovers_and_independently_reads(self):
        _, sdk, _ = self.capture(float('nan'))
        result, _ = self.recover(sdk)
        self.assertEqual(result['producer_version'], 'hk-capture-v2-metadata-null-v1')

    def test_real_launcher_closure_and_recovery_without_sdk_import(self):
        # Exercise the actual launcher with all real candidate dependencies,
        # separate from test_launcher's intentionally small control fixtures.
        bundle = self.root / 'sealed-candidate'
        bundle.mkdir()
        shutil.copyfile(ROOT / 'launcher.py', bundle / 'launcher.py')
        for tree in ('collector', 'recovery'):
            shutil.copytree(ROOT / tree, bundle / tree, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        files = {}
        for path in sorted(bundle.rglob('*')):
            if path.is_file():
                raw = path.read_bytes()
                files[path.relative_to(bundle).as_posix()] = dict(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))
        raw = json.dumps(dict(schema_version='v5.m02.capture_candidate.sources.v1', files=files), sort_keys=True).encode()
        (bundle / 'SOURCE_MANIFEST.json').write_bytes(raw)
        pin = hashlib.sha256(raw).hexdigest()
        # Actual frozen facade import is safe offline; never call its default context.
        script = """import importlib.util,json,socket,sys
from pathlib import Path
root=Path(sys.argv[1]); spec=importlib.util.spec_from_file_location('candidate_launcher',root/'launcher.py')
launcher=importlib.util.module_from_spec(spec);spec.loader.exec_module(launcher)
def blocked(*a,**k):raise AssertionError('LIVE_NETWORK_FORBIDDEN')
socket.socket=blocked;sys.modules['futu']=None
frozen=launcher.verify_sources(sys.argv[2])
with launcher.pinned_imports(frozen,'collector',{'ops','infrastructure'}):
 import ops.macos_research_panel_daily as facade
 import ops._macos_research_panel_daily_parts.hk_market_capture as capture
 assert Path(facade.__file__).is_relative_to(root/'collector')
 assert Path(capture.__file__).is_relative_to(root/'collector')
 assert callable(facade.collect_hk_futu_rows)
print('BUNDLED_IMPORT_ONLY')
"""
        imported = subprocess.run([sys.executable, '-I', '-B', '-c', script, str(bundle), pin], capture_output=True, text=True, timeout=20)
        self.assertEqual(imported.returncode, 0, imported.stdout + imported.stderr)
        self.assertEqual(imported.stdout.strip(), 'BUNDLED_IMPORT_ONLY')
        _, sdk, _ = self.capture(float('nan'))
        output = self.root / 'launcher-membership'
        output.mkdir(mode=0o700)
        (output / '.v5-hk-membership-root').write_bytes(b'v5.hk-membership-root.v1\n')
        request = self.root / 'recovery-request.json'
        request.write_text(json.dumps(dict(sdk_path=str(sdk), sdk_sha256=hashlib.sha256(sdk.read_bytes()).hexdigest(),
            output_root=str(output), target_date=self.target)))
        process = subprocess.run([sys.executable, '-I', '-B', str(bundle / 'launcher.py'), 'recover',
            '--request', str(request), '--expected-manifest-sha', pin], capture_output=True, text=True, timeout=120)
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
        result = strict_load(process.stdout)
        self.assertEqual(result['status'], 'RECOVERY_COMPLETED')
        self.assertEqual(result['recovery']['producer_version'], 'hk-capture-v2-metadata-null-v1')
        readback = read_private(output, result['recovery']['files'], self.target)
        self.assertEqual(len(readback['codes']), 600)

    def test_exact_old_source_sdk_still_recovers(self):
        path = ROOT / 'reference/hk_market_capture.original.py'
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), recovery.PRODUCER_SHA)
        spec = importlib.util.spec_from_file_location('ops._macos_research_panel_daily_parts.original_capture', path)
        original = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(original)
        _, sdk, _ = self.capture(None, module=original)
        result, _ = self.recover(sdk)
        self.assertEqual(result['producer_version'], 'hk-capture-v2-original-0a9651')

    def test_unknown_producer_rejected_before_publication(self):
        _, sdk, _ = self.capture(None)
        value = strict_load(sdk.read_bytes())
        value['producer_owner']['code_sha256'] = '1' * 64
        # Explicit synthetic negative fixture, never production evidence.
        negative = self.root / 'unknown-producer.synthetic.json'
        negative.write_bytes(candidate._canonical_capture_bytes(value))
        with self.assertRaisesRegex(ValueError, 'SDK_PRODUCER_SHA'):
            self.recover(negative)
        self.assertEqual([p.name for p in (self.root / 'membership').iterdir()], ['.v5-hk-membership-root'])

    def test_sdk_hash_mismatch_is_rejected(self):
        _, sdk, _ = self.capture(None)
        output = self.root / 'bad-sha'
        output.mkdir()
        (output / '.v5-hk-membership-root').write_bytes(b'v5.hk-membership-root.v1\n')
        with self.assertRaisesRegex(ValueError, 'SDK_SHA_MISMATCH'):
            recovery.run_recovery(dict(sdk_path=str(sdk), sdk_sha256='0'*64,
                output_root=str(output), target_date=self.target))

    def test_seven_file_reader_rejects_missing_sdk(self):
        _, sdk, _ = self.capture(None)
        result, output = self.recover(sdk)
        bad = dict(result['files']); bad.pop(result['sdk_relative'])
        with self.assertRaisesRegex(ValueError, 'MEMBERSHIP_SEVEN_FILES_REQUIRED'):
            read_private(output, bad, self.target)

    def test_readback_rejects_sdk_mutation_and_recovery_does_not_overwrite(self):
        _, sdk, _ = self.capture(None)
        result, output = self.recover(sdk)
        request = dict(sdk_path=str(sdk), sdk_sha256=hashlib.sha256(sdk.read_bytes()).hexdigest(),
                       output_root=str(output), target_date=self.target)
        with self.assertRaisesRegex(ValueError, 'MEMBERSHIP_FRESH_PRIVATE_OUTPUT_REQUIRED'):
            recovery.run_recovery(request)
        persisted_sdk = output / result['sdk_relative']
        persisted_sdk.write_bytes(persisted_sdk.read_bytes() + b' ')
        with self.assertRaisesRegex(ValueError, 'MEMBERSHIP_INPUT_SHA'):
            read_private(output, result['files'], self.target)


if __name__ == '__main__':
    unittest.main()
