"""TEST-ONLY owner services: real local files/ledger; synthetic provider and writer.

No fixture file is a real Parquet or market observation. Native computation and
source acquisition are never invoked. The real checkpoint Binding and isolated
claim ledger exercise the integration boundary without manufacturing authority.
"""
import contextlib
import copy
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import types

import stages


ROOT = Path(__file__).resolve().parents[4]


def load_test_dependency(name, relative):
    path = ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    exec(compile(path.read_bytes(), str(path), 'exec'), module.__dict__)
    return module


binding_module = load_test_dependency('test_daily_checkpoint_binding',
    'handoff/reconstruction_candidates_20261108/checkpoint_binding_v1/binding.py')
ledger_module = load_test_dependency('test_daily_ledger',
    'handoff/reconstruction_candidates_20261108/isolated_coordinator_v1/ledger.py')
adapter = load_test_dependency('test_daily_adapter',
    'handoff/reconstruction_candidates_20261108/latest109_v2/latest109_rebuild.py')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


class SyntheticOwner:
    def __init__(self, root, *, initialize=False, fail_writer=False, prepared=None):
        self.root = Path(root)
        if initialize:
            ledger_module.initialize(self.root)
        self.ledger = ledger_module.Ledger(self.root)
        self.flags = dict(stages.original_provider().FLAGS)
        self.compute_calls = 0
        self.writer_calls = 0
        self.fail_writer = fail_writer
        self.connections = 0
        self.monitor = object()
        self.mods, self.schema = {}, {}
        self.parquet_dir = self.root / 'writer_marker_only'
        self.symbol, self.target = '000001.SZ', 20261106
        self.code_sha = sha((Path(__file__).parent / 'stages.py').read_bytes())
        self.rows = [{'symbol': self.symbol, 'event_date': '20261105', 'close': '10'},
                     {'symbol': self.symbol, 'event_date': '20261106', 'close': '11'}]
        pins = copy.deepcopy(stages.original_provider().LATEST_PINS)
        self.prior_state = {'schema': 'ORIGINAL109_LATEST_COMPONENT_STATE_V1',
            'symbol': self.symbol, 'count': 1, 'last_date': '20261105', 'original_pins': pins}
        bundle = {'schema': 'SAME_BASIS_CONTINUATION_BUNDLE_V1', 'symbol': self.symbol,
                  'asof': '20261105', 'component109': self.prior_state, 'state51': {'count': 1}}
        self.prior_ref = self.source('prior.gz', gzip.compress(canonical(bundle), mtime=0))
        self.prior = {'symbol': self.symbol, 'event_date': '20261105', 'continuation_ref': self.prior_ref}
        checkpoint = {'schema': 'OWNER_CHECKPOINT_PREFIX_V1',
            'prior_continuation_sha256': self.prior_ref['sha256'], 'state': self.prior_state,
            'prefix_sha256': sha(canonical(self.rows[:-1]))}
        self.checkpoint_ref = self.source('checkpoint.json', canonical(checkpoint))
        registry = {'schema': 'OWNER_CHECKPOINT_REGISTRY_V1',
                    'entries': [{'continuation_ref': self.prior_ref, 'checkpoint_ref': self.checkpoint_ref}]}
        registry_raw = canonical(registry)
        registry_ref = self.source('registry.json', registry_raw)
        self.checkpoint_binding = binding_module.Binding(registry_raw, registry_ref, self.checked, self.gate)
        self.bound_checkpoint_ref = self.checkpoint_binding.bound_checkpoint_ref
        self.input_ref = self.source('input.json', canonical({'schema': 'SYNTHETIC_SOURCE_INPUT',
            'symbol': self.symbol, 'target_date': self.target, 'status': 'VERIFIED_SAME_BASIS_BAR'}))
        self.prepared = prepared or {'status': 'PREPARED_ONE_SESSION', 'symbol': self.symbol,
            'rows': copy.deepcopy(self.rows),
            'context': {'symbol': self.symbol, 'asof': '20261106', 'observation_date': '20261109'},
            'prior_component_state': copy.deepcopy(self.prior_state), 'daily': {'fixture': True},
            'state': {'count': 2}, 'history_refs': {'parent_continuation_ref': self.prior_ref},
            'provenance': {'data_kind': 'SYNTHETIC_NO_NATIVE_NO_REAL_PARQUET'}}
        self.provider = types.SimpleNamespace(prepare=lambda *args: copy.deepcopy(self.prepared))
        self.writer = types.SimpleNamespace(write_stock=self.write_stock)

    def source(self, name, raw):
        path = self.root / 'inputs' / name
        path.parent.mkdir(exist_ok=True)
        if not path.exists():
            path.write_bytes(raw)
        elif path.read_bytes() != raw:
            raise ValueError('FIXTURE_SOURCE_CONFLICT')
        return self.ref(path)

    def ref(self, path):
        raw = path.read_bytes()
        return {'path': str(path.relative_to(self.root)), 'bytes': len(raw), 'sha256': sha(raw)}

    def gate(self):
        pass  # Synthetic resource callback; not proof of the original resource gate.

    def checked(self, ref):
        path = self.root / ref['path']
        if path != path.resolve() or not path.is_relative_to(self.root):
            raise ValueError('FIXTURE_REFERENCE_SCOPE')
        raw = path.read_bytes()
        if len(raw) != ref['bytes'] or sha(raw) != ref['sha256']:
            raise ValueError('FIXTURE_INPUT_CHANGED')
        return raw

    def identity(self):
        return {'symbol': self.symbol, 'event_date': str(self.target),
                'input_sha256': self.input_ref['sha256'], 'code_sha256': self.code_sha,
                'checkpoint_sha256': self.checkpoint_ref['sha256']}

    def completed(self, symbol, target, input_ref):
        with self.ledger.lock():
            claim = self.ledger.location(self.identity())
            return self.ledger.inspect_locked(claim, self.identity()) if claim.exists() else None

    def verify_completed(self, result, symbol, target, input_ref):
        if result['status'] != 'REUSE_VERIFIED':
            raise ValueError('UNKNOWN_RECONCILIATION_REQUIRED')

    def verify_inputs(self, prior, input_ref, expected):
        raw = self.checked(input_ref)
        if sha(raw) != expected or input_ref != self.input_ref:
            raise ValueError('FIXTURE_INPUT_IDENTITY')

    def started(self, symbol, target):
        claim = self.ledger.claim(self.identity(), self.parquet_dir)
        if claim['status'] != 'CLAIMED':
            raise ValueError('FIXTURE_PREVIOUS_ATTEMPT')
        return claim

    def compute(self, rows, context, prior_state, *, checkpoint_prefix_sha256):
        adapter.validate_checkpoint(rows, context, prior_state, checkpoint_prefix_sha256)
        self.compute_calls += 1
        state = dict(prior_state, count=len(rows), last_date=context['asof'])
        return {'symbol': self.symbol, 'event_date': context['asof'], 'fields': {}}, {
            'historical109_rows_evaluated': 0, 'prior_component_state_reused': True,
            'component_state': state, 'native_raw_prefix_rows': len(rows),
            'native_prefix_required': True, 'data_kind': 'SYNTHETIC_NOT_FORMULA_VALIDATION'}

    @contextlib.contextmanager
    def connection(self):
        self.connections += 1
        yield object()

    def write_stock(self, con, rows, provenance, directory, mods, schema, monitor):
        self.writer_calls += 1
        self.parquet_dir.mkdir(exist_ok=True)
        (self.parquet_dir / 'SYNTHETIC_PARTIAL_MARKER.txt').write_text('NO REAL PARQUET')
        if self.fail_writer:
            raise OSError('SYNTHETIC_PARTIAL_WRITE')
        receipt = {'symbol': self.symbol, 'event_dates': [str(self.target)],
                   'calculation_asof': str(self.target), 'field_rows': 109, 'metadata_rows': 1,
                   'full_objects_context_types_ieee_bits_key_orders_exact': True,
                   'data_kind': 'SYNTHETIC_RECEIPT_NOT_REAL_PARQUET'}
        self.receipt = self.save('SYNTHETIC_RECEIPT.json', receipt)
        return receipt

    def remove_committed_temporary_links(self, receipt):
        return {'removed': [], 'data_kind': 'SYNTHETIC_NO_PARQUET'}

    def receipt_ref(self):
        return self.receipt

    def save(self, name, value):
        folder = self.root / 'outputs'
        folder.mkdir(exist_ok=True)
        path = folder / name
        raw = value if isinstance(value, bytes) else canonical(value)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        return self.ref(path)

    def seal_for_fixture(self, result_ref):
        result = json.loads(self.checked(result_ref))
        self.ledger.finish(self.identity(), artifacts=[result_ref, result['continuation_ref'],
            result['checkpoint_ref'], result['parquet_receipt_ref']])
