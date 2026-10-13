"""Real frozen-oracle zero-row regression, using synthetic Parquet input only.

RED base: 2f16d60499e3b230036ae7f716f6776ededb3422 (runtime 2c5d1eb2).
Run with the existing Python that has numpy, pandas and pyarrow; never skip or
substitute a runner when a dependency is missing:
  PYTHONPATH=V5/src:V5/tests "$PYTHON" -B -m unittest -v test_m05_v192_valid_empty

The default oracle computes the fixture's zero candidates. No hand-built output
rows, callback replacement, mock reader, source mutation, network or V4 access.
The permit below applies only to this disposable SYNTHETIC test root.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from v5_shadow.a_preselection import BASE, run_a_preselection
from v5_shadow.a_preselection_daily import build_m05_daily
from v5_shadow.digests import canonical_bytes, sha256_json

TARGET = '20261008'
SIGNAL = '20260930'
POOL = 'a_d1_premarket_pool'
OLD_STATUS = 'V192_CANDIDATE_READY_EMPTY'
ADAPTER_SCHEMA = 'v5.m05.v192_empty_adapter.v1'

# This is executed in a fresh process to retain the real frozen namespaces.
FIXTURE_WORKER = r'''
import hashlib, importlib, json, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import pandas as pd
import pyarrow
from v5_shadow.a_preselection import _FrozenLoader, _source_bytes
from v5_shadow.digests import sha256_json
sys.meta_path.insert(0, _FrozenLoader(_source_bytes()))
owner = importlib.import_module('upstreams.v3_shared_data.shared_data.v192_selector')
bundle = importlib.import_module('upstreams.v3_shared_data.shared_data.v192_oracle_bundle')
materializer = importlib.import_module('domains.preselection_materializer')
validator = importlib.import_module('infrastructure.preselection_pool_store').validate_pool_artifact
root = Path(sys.argv[2]); signal = sys.argv[3]; target = sys.argv[4]
panel = root / 'synthetic-selector.parquet'; shared = root / 'v192'

# All 61 frozen base fields plus the eight additional exact source fields.
# Every entry-pool signal is false, so the unmodified role function's final
# exclusion yields TEST_ONLY_POLLUTION_OR_BOUNDARY, regardless of score/rank.
columns = list(dict.fromkeys(bundle.REQUIRED_BASE_COLUMNS + list(owner._PREMARKET_SOURCE_FIELDS)))
row = {name: 0.0 for name in columns}
for name in bundle.BOOL_COLUMNS:
    row[name] = False
row.update(trade_date=int(signal), ts_code='000001.SZ', name='SYNTHETIC_ZERO_ONLY',
    open=10.0, high=10.5, low=9.5, close=10.0, pre_close=10.0,
    volume=1000.0, amount=10000.0, amount_ratio_20=1.0,
    BBI=10.0, zge_white_line=10.0, zge_yellow_line=10.0, ma20=10.0,
    high_20_prev=10.5, J=50.0, zge_rsi3=50.0, amplitude_pct=10.0,
    bar_close_pos=0.5, gold_brick_context='none',
    brick_resonance1=0, brick_resonance2=0, brick_resonance=0,
    ref_hold_score=0.0, route_context='', brick_context='none',
    formula_source=owner.CANONICAL_FORMULA_SOURCE,
    field_contract_version='SYNTHETIC_ZERO_FIXTURE_V1')
frame = pd.DataFrame([row], columns=columns)
numeric = [name for name in bundle.REQUIRED_BASE_COLUMNS
           if name not in bundle.BOOL_COLUMNS and name not in ('trade_date', 'ts_code', 'name')]
dtypes = {name: 'float64' for name in numeric + ['ref_hold_score']}
dtypes.update({name: 'bool' for name in bundle.BOOL_COLUMNS if name != 'gold_brick_context'})
dtypes.update({name: 'int64' for name in
               ('trade_date', 'brick_resonance1', 'brick_resonance2', 'brick_resonance')})
dtypes.update({name: 'object' for name in ('ts_code', 'name', 'gold_brick_context',
               'route_context', 'brick_context', 'formula_source', 'field_contract_version')})
frame = frame.astype(dtypes)
assert len(columns) == 69 and len(frame) == 1
frame.to_parquet(panel, index=False, engine='pyarrow')
before = hashlib.sha256(panel.read_bytes()).hexdigest()

# Crucially no runner= argument and no direct publish_v192_rows call.
owner.materialize_frozen_v192_selector(shared, panel_path=panel,
    signal_date=signal, target_date=target)
verified = owner.read_verified_v192_pool(shared, target_date=target,
    expected_signal_date=signal)
assert list(verified.rows) == [] and verified.run.verification['row_count'] == 0
assert verified.run.manifest['provenance']['panel_sha256'] == before
assert hashlib.sha256(panel.read_bytes()).hexdigest() == before
artifact = materializer.build_shared_v192_premarket_pool(shared,
    trade_date=target, signal_date=signal, reader=owner.read_verified_v192_pool)
assert artifact['status'] == 'V192_CANDIDATE_READY_EMPTY'
assert artifact['rows'] == [] and artifact['source_row_count'] == 0
try:
    validator(artifact)
except ValueError as error:
    assert str(error) == 'empty pool requires an explicit status'
    legacy_rejection = str(error)
else:
    raise AssertionError('the unchanged original store no longer reproduces the contract mismatch')
for name in ('production_allowed', 'buy_gate_updated', 'orders_sent'):
    assert verified.run.receipt[name] is False and artifact[name] is False
print(json.dumps(dict(original_artifact=artifact,
    original_artifact_sha256=sha256_json(artifact),
    reader_row_count=verified.run.verification['row_count'],
    panel_sha256=before, panel_columns=len(columns), input_rows=len(frame),
    legacy_rejection=legacy_rejection), sort_keys=True, allow_nan=False))
'''

COLD_READER_WORKER = r'''
import json, sys
sys.path.insert(0, sys.argv[1])
from v5_shadow.a_preselection_store_factory import build_strict_store
from v5_shadow.digests import canonical_bytes
runtime = build_strict_store(sys.argv[2], json.loads(sys.argv[3]))
snapshot = runtime.store.read_pool_snapshot(sys.argv[4], sys.argv[5])
sys.stdout.buffer.write(canonical_bytes(snapshot))
'''


class V192ValidEmptyTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='m05-zero-synthetic-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.source = self.root / 'source'
        self.out = self.root / 'shadow'
        self.control = self.root / 'control'
        self.v4 = self.root / 'synthetic-v4-sentinel'
        for path in (self.source, self.out, self.control, self.v4):
            path.mkdir()
        (self.out / '.v5-shadow-root').write_bytes(b'v5.shadow-root.v1\n')
        (self.v4 / 'untouched').write_bytes(b'SYNTHETIC_SENTINEL_ONLY\n')
        self.original = self.worker(FIXTURE_WORKER, str(self.source), SIGNAL, TARGET)
        self.shared = self.source / 'v192'
        self.lane = dict(kind='v192', input_root=str(self.shared), paths={},
                         files=self.file_hashes(self.shared))
        self.request = dict(target_date=TARGET, signal_date=SIGNAL,
                            data_kind='SYNTHETIC', lanes=[self.lane])
        keys = [dict(business_key='SYNTHETIC:V192_ZERO', trade_date=TARGET, pool_id=POOL)]
        permit = dict(schema_version='v4.preselection.exact_scope.v1',
            decision_id='SYNTHETIC_ZERO_TEST_ONLY', owner_id='SYNTHETIC_M05_ZERO_TEST',
            source_release_sha256='1' * 64, target_release_sha256='2' * 64,
            source_root=str(self.source), target_root=str(self.out), keys=keys,
            business_key_set_sha256=sha256_json(keys))
        permit_raw = canonical_bytes(permit)
        (self.control / 'permit.json').write_bytes(permit_raw)
        self.context = dict(control_dir=str(self.control),
            expected_permit_sha256=hashlib.sha256(permit_raw).hexdigest(),
            expected_owner_id='SYNTHETIC_M05_ZERO_TEST',
            expected_release_sha256='2' * 64, expected_root=str(self.out))
        (self.control / 'gate.json').write_bytes(canonical_bytes(dict(
            schema_version='v4.preselection.gate.v1',
            permit_sha256=self.context['expected_permit_sha256'], revision=1, state='OPEN')))

    def worker(self, code, *args):
        completed = subprocess.run([sys.executable, '-I', '-B', '-c', code,
            str(BASE / 'src'), *args], capture_output=True, text=True, timeout=120)
        self.assertEqual(completed.returncode, 0,
            'frozen worker failed; this is not the expected RED:\n' + completed.stderr)
        return json.loads(completed.stdout)

    @staticmethod
    def tree(root):
        return {str(path.relative_to(root)): path.read_bytes()
                for path in root.rglob('*') if path.is_file()}

    @staticmethod
    def file_hashes(root):
        return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in root.rglob('*') if path.is_file()}

    def daily(self):
        return build_m05_daily(self.request, source_root=str(self.source),
            private_root=str(self.out), code_root=str(BASE), v4_root=str(self.v4),
            write_gate_context=self.context)

    def assert_preserved_evidence(self, artifact):
        self.assertEqual(artifact['status'], 'VALID_EMPTY')
        self.assertEqual(artifact['rows'], [])
        self.assertEqual(artifact['source_row_count'], 0)
        evidence = artifact['coverage_evidence']
        self.assertEqual(evidence['schema_version'], ADAPTER_SCHEMA)
        self.assertEqual(evidence['original_status'], OLD_STATUS)
        self.assertEqual(evidence['original_artifact'], self.original['original_artifact'])
        self.assertEqual(evidence['original_artifact_sha256'],
                         self.original['original_artifact_sha256'])
        self.assertEqual(sha256_json(evidence['original_artifact']),
                         evidence['original_artifact_sha256'])
        # The adapter may change only status and add its declared evidence.
        expected = dict(self.original['original_artifact'], status='VALID_EMPTY',
                        coverage_evidence=evidence)
        self.assertEqual(artifact, expected)

    def test_default_oracle_zero_rows_publish_and_cold_read(self):
        before = self.tree(self.source), self.tree(self.control), self.tree(self.v4)
        self.assertEqual(self.original['reader_row_count'], 0)
        self.assertEqual(self.original['legacy_rejection'], 'empty pool requires an explicit status')
        print('DEFAULT_ORACLE_AND_STRICT_READER_ZERO; ORIGINAL_OWNER_EMPTY_STATUS_REJECTED', flush=True)
        assembly = run_a_preselection(self.request)
        lane = assembly['lanes'][0]
        self.assertTrue(lane['accepted'], 'EXPECTED_RED:' + lane['reason'])
        self.assertEqual(assembly['status'], 'ASSEMBLED')
        self.assertEqual(assembly['row_count'], 0)
        self.assert_preserved_evidence(lane['artifact'])
        result = self.daily()
        self.assertEqual(result['status'], 'READY')
        self.assertEqual(result['row_count'], 0)
        self.assertEqual(len(result['receipts']), 1)
        receipt = result['receipts'][0]
        self.assert_preserved_evidence(receipt['artifact'])
        snapshot = self.worker(COLD_READER_WORKER, str(self.out),
                               json.dumps(self.context), TARGET, POOL)
        self.assertEqual(snapshot['artifact'], receipt['artifact'])
        for kind in ('artifact', 'manifest', 'receipt'):
            raw = (self.out / receipt[kind + '_relative_path']).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), receipt[kind + '_raw_sha256'])
        # Original artifact identity is canonical JSON; stored file identities
        # above are the separately checked actual raw-byte hashes.
        self.assertEqual(sha256_json(receipt['artifact']), receipt['artifact_sha256'])
        self.assertEqual(before, (self.tree(self.source), self.tree(self.control), self.tree(self.v4)))
        repeated = self.daily()
        self.assertEqual(repeated['batch_identity'], result['batch_identity'])
        self.assertEqual(repeated['receipts'], result['receipts'])


if __name__ == '__main__':
    unittest.main()
