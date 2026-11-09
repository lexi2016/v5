"""Real pinned-owner admission in temporary SYNTHETIC inputs; no live source."""
import hashlib
import json
import copy
import datetime as dt
from contextlib import nullcontext
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import adapter
import verify_worker as worker

V5 = Path(__file__).absolute().parents[2]
OWNER = V5 / 'source_owners/m07'
FACTORY = '''import json,sys
from pathlib import Path
owner=Path(sys.argv[1]);root=Path(sys.argv[2]);stage=sys.argv[3]
sys.path[:0]=[str(owner/'V5/src'),str(owner/'V5/tests')]
from m07_fixture import make_case
request=make_case(root,count=2,stage=stage)
print(json.dumps({k:request[k] for k in ('target_date','stage_id','cutoff','pool_source_dates','inputs','recording')}))
'''


class RepositoryClosureTests(unittest.TestCase):
    def verify_stage(self, stage):
        with tempfile.TemporaryDirectory(prefix='m07-repository-regression-') as temp:
            root = Path(temp)
            factory = subprocess.run(
                [sys.executable, '-I', '-B', '-c', FACTORY, str(OWNER), str(root), stage],
                capture_output=True, text=True, timeout=30)
            self.assertEqual(factory.returncode, 0, factory.stderr)
            request = json.loads(factory.stdout)
            inventory = lambda: {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                                 for p in root.rglob('*') if p.is_file()}
            before = inventory()
            scope = ('A.000001', 'A.000002')
            binding = adapter.Binding(
                'SYNTHETIC_TEST_JOB', 'SYNTHETIC_TEMP_ENV', 'SYNTHETIC_A_QUOTES',
                scope, adapter.digest(list(scope)), 'a' * 64, 'b' * 64,
                request, lambda: None, lambda: nullcontext(), True)
            result = adapter.verify_registered_recording(binding)
            self.assertEqual(result['status'], 'SOURCE_RECORDING_VERIFIED_ONLY')
            self.assertEqual(result['rows'], 2)
            self.assertEqual(result['source_id'], 'SYNTHETIC_A_QUOTES')
            self.assertEqual(result['data_kind'], 'SYNTHETIC')
            self.assertEqual(result['source_authority'], 'UNKNOWN')
            for key in ('production_allowed', 'natural_verified', 'business_verified', 'collector_executed'):
                self.assertIs(result[key], False)
            self.assertEqual(inventory(), before)
            # Parent -O is not inherited by adapter's fixed -I/-B subprocess.
            # Exercise the actual worker explicitly under optimized Python too.
            optimized = subprocess.run(
                [sys.executable, '-I', '-B', '-O', str(Path(__file__).parent / 'verify_worker.py')],
                input=json.dumps(request), capture_output=True, text=True, timeout=30)
            self.assertEqual(optimized.returncode, 0, optimized.stdout + optimized.stderr)
            observed = json.loads(optimized.stdout)
            self.assertEqual(observed['status'], 'VERIFIED')
            self.assertTrue(observed['known_synthetic'])
            self.assertEqual(observed['rows'], 2)
            self.assertEqual(observed['pool_codes'], list(scope))
            self.assertEqual(inventory(), before)

    def test_real_owner_0925_admission_and_no_original_input_writes(self):
        self.verify_stage('STAGE_0925')

    def test_real_owner_0930_admission_and_no_original_input_writes(self):
        self.verify_stage('STAGE_0930_0935')

    def test_lossy_request_times_refused_by_actual_adapter_and_optimized_worker(self):
        for stage in ('STAGE_0925', 'STAGE_0930_0935'):
            with tempfile.TemporaryDirectory(prefix='m07-time-regression-') as temp:
                root = Path(temp)
                factory = subprocess.run(
                    [sys.executable, '-I', '-B', '-c', FACTORY, str(OWNER), str(root), stage],
                    capture_output=True, text=True, timeout=30)
                self.assertEqual(factory.returncode, 0, factory.stderr)
                request = json.loads(factory.stdout)
                before = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in root.rglob('*') if p.is_file()}
                utc = dt.datetime.fromisoformat(request['cutoff']).astimezone(dt.timezone.utc)
                stamp = utc.strftime('%Y-%m-%dT%H:%M:%S')
                for field in ('cutoff', 'captured_at', 'acquired_at'):
                    for suffix, error in (('.0000001+00:00', 'M07_SOURCE_TIME_PRECISION_UNSUPPORTED'),
                                          ('-00:00:00.000001', 'M07_SOURCE_OFFSET_PRECISION_UNSUPPORTED')):
                        with self.subTest(stage=stage, field=field, suffix=suffix):
                            changed = copy.deepcopy(request)
                            target = changed if field == 'cutoff' else changed['recording']
                            target[field] = stamp + suffix
                            scope = ('A.000001', 'A.000002')
                            binding = adapter.Binding(
                                'SYNTHETIC_TEST_JOB', 'SYNTHETIC_TEMP_ENV', 'SYNTHETIC_A_QUOTES',
                                scope, adapter.digest(list(scope)), 'a' * 64, 'b' * 64,
                                changed, lambda: None, lambda: nullcontext(), True)
                            with self.assertRaisesRegex(ValueError, error):
                                adapter.verify_registered_recording(binding)
                            process = subprocess.run(
                                [sys.executable, '-I', '-B', '-O', str(Path(__file__).parent / 'verify_worker.py')],
                                input=json.dumps(changed), capture_output=True, text=True, timeout=30)
                            self.assertEqual(process.returncode, 2, process.stdout + process.stderr)
                            self.assertEqual(json.loads(process.stdout)['reason'], error)
                after = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in root.rglob('*') if p.is_file()}
                self.assertEqual(after, before)

    def test_manifest_change_is_refused(self):
        with patch.object(worker, '_bytes', return_value=b'{}'):
            with self.assertRaisesRegex(ValueError, 'M07_REPOSITORY_MANIFEST_CHANGED'):
                worker._repository_sources()

    def test_changed_original_entry_or_owner_dependency_is_refused(self):
        original = worker._bytes
        targets = [OWNER / 'V5/src/v5_shadow/a_stage_daily.py',
                   OWNER / 'owner/stage_center/raw_store.py']
        for target in targets:
            with self.subTest(path=target.relative_to(OWNER)):
                def changed(path):
                    raw = original(path)
                    return raw + b'\n# changed\n' if Path(path) == target else raw
                with patch.object(worker, '_bytes', side_effect=changed):
                    with self.assertRaisesRegex(ValueError, 'M07_REPOSITORY_DEPENDENCY_CHANGED'):
                        worker._repository_sources()

    def test_symlink_input_to_code_reader_is_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'alias.py'
            path.symlink_to(OWNER / 'V5/src/v5_shadow/a_stage_daily.py')
            with self.assertRaisesRegex(ValueError, 'M07_REPOSITORY_DEPENDENCY_SYMLINK'):
                worker._bytes(path)

    def test_original_natural_execution_gate_is_unchanged(self):
        script = '''import json,sys
sys.path.insert(0,sys.argv[1])
import verify_worker as w
sys.meta_path.insert(0,w._PinnedShadowLoader(w._repository_sources()))
from v5_shadow import a_stage_daily as m
request=dict(schema_version='v5.m07_daily_request.v1',target_date='20261012',stage_id='STAGE_0925',cutoff='2026-10-12T09:25:00+08:00',data_kind='RECORDED_INPUT_REPLAY',trigger='NATURAL',natural=True,pool_source_dates={},inputs={},recording={},expected_generation=None)
try:m._request(request)
except ValueError as error:print(json.dumps({'reason':str(error)}))
else:raise SystemExit('UNEXPECTED_NATURAL_ADMISSION')
'''
        process = subprocess.run([sys.executable, '-I', '-B', '-c', script,
                                  str(Path(__file__).parent)], capture_output=True,
                                 text=True, timeout=30)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(json.loads(process.stdout)['reason'], 'M07_NATURAL_EXECUTION_NOT_BOUND')


if __name__ == '__main__':
    unittest.main()
