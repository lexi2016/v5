"""Synthetic retry -> actual stage bridge; no native/real Parquet/market data."""
import builtins
import copy
import dataclasses
import datetime as dt
import json
from pathlib import Path
import sys
import types
import unittest

from subset_plan import canonical, digest
import test_entrypoint


ROOT = Path(__file__).resolve().parents[3]
DAILY = ROOT / 'V5/public_source_delivery/20261108_execution_increment/daily1540'


def load_test_module(name, path, imports=None):
    module = types.ModuleType(name)
    module.__file__ = str(path)
    builtins_map = dict(vars(builtins))
    def importer(requested, globals=None, locals=None, fromlist=(), level=0):
        if level == 0 and imports and requested in imports:
            return imports[requested]
        return builtins.__import__(requested, globals, locals, fromlist, level)
    builtins_map['__import__'] = importer
    module.__dict__['__builtins__'] = builtins_map
    sys.modules[name] = module
    try:
        exec(compile(path.read_bytes(), str(path), 'exec'), module.__dict__)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return module


class DailyBridgeIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.modules = []
        self.fixture = test_entrypoint.EntryTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.tearDown)
        stages = load_test_module('retry_integration_daily_stages', DAILY / 'stages.py')
        self.modules.append(stages.__name__)
        bridge = load_test_module('retry_integration_daily_bridge', DAILY / 'owner_bridge.py')
        self.modules.append(bridge.__name__)
        helper = load_test_module('retry_integration_synthetic_owner',
            DAILY / 'synthetic_owner_fixture.py', {'stages': stages})
        self.modules.append(helper.__name__)
        self.bridge = bridge
        self.runtime = helper.SyntheticOwner(self.fixture.home / 'original-owner', initialize=True)
        self.runtime.prepared['context']['observation_date'] = '20261106'
        self.daily_results = []
        self.exception_attempt = None
        self.configure()

    def tearDown(self):
        for name in self.modules:
            sys.modules.pop(name, None)

    def configure(self):
        f = self.fixture
        f.binding['data_date'] = '20261106'
        original = f.binding['original_binding']
        body = json.loads(Path(original['contract_ref']['path']).read_bytes())
        body.update(date='20261106', source_date='20261106',
                    available_after='2026-11-06T15:40:00+08:00')
        original['date'] = '20261106'
        original['contract_ref'] = f.put('daily-original-contract.json', canonical(body)).as_dict()
        original['identity'] = digest({'date': '20261106', 'node': 'owner', 'inputs': body['input_refs']})
        f.now = dt.datetime.fromisoformat('2026-11-06T16:10:00+08:00')
        f.evidence.update(binding=copy.deepcopy(f.binding), ended_at='2026-11-06T15:40:00+08:00')
        f.evidence['stocks'] = [
            {'symbol': '000001.SZ', 'attempt_id': 'a1', 'status': 'FAILED_CLEAN',
             'retryable': True, 'effects': 'INDEPENDENTLY_CONFIRMED_NO_PERSISTED_EFFECTS'},
            {'symbol': '600027.SH', 'attempt_id': 'a1', 'status': 'SUCCESS',
             'output_sha256': f.success.sha256},
        ]
        f.contract['binding'] = copy.deepcopy(f.binding)
        for name in ('owner_bridge.py', 'stages.py', 'synthetic_owner_fixture.py'):
            f.contract['dependencies'].append(f.pin(DAILY / name).as_dict())
        for relative in ('handoff/reconstruction_candidates_20261108/checkpoint_binding_v1/binding.py',
                         'handoff/reconstruction_candidates_20261108/isolated_coordinator_v1/ledger.py',
                         'handoff/reconstruction_candidates_20261108/latest109_v2/latest109_rebuild.py',
                         'V5/public_source_delivery/handoff/par_daily_chain_repair_20261106/provider/continuation_provider.py'):
            f.contract['dependencies'].append(f.pin(ROOT / relative).as_dict())
        contract = f.put('daily-subset-contract.json', canonical(f.contract))
        f.approval.update(contract_ref=contract.as_dict(), binding=copy.deepcopy(f.binding))
        approval = f.put('daily-approval.json', canonical(f.approval))
        review = f.put('daily-review.json', canonical(f.evidence))

        def owner_subset(symbols, context, pulse):
            self.assertEqual(symbols, ('000001.SZ',))
            self.assertTrue(f.guard_active)
            f.calls.append((symbols, copy.deepcopy(context)))
            try:
                value = self.bridge.advance_from_owner(self.runtime, self.runtime.checkpoint_binding,
                    symbol=self.runtime.symbol, target_date=self.runtime.target,
                    prior_selection=self.runtime.prior, input_ref=self.runtime.input_ref,
                    expected_input_sha256=self.runtime.input_ref['sha256'], lock_guard=pulse)
            except BaseException as error:
                self.exception_attempt = getattr(error, 'daily1540_attempt', None)
                raise
            self.daily_results.append(value)
            # Persisted but not independently sealed is unresolved for retry.
            return {symbol: None for symbol in symbols}

        f.registration = dataclasses.replace(f.registration, contract_ref=contract,
            approval_ref=approval, reconciliation_refs={'retry-1610': review, 'retry-1640': review},
            owner=dataclasses.replace(f.hooks, execute_subset=owner_subset))

    def test_failed_stock_reaches_bridge_and_success_is_excluded(self):
        result = self.fixture.dispatch()
        self.assertEqual(result['status'], 'RETURNED_AWAIT_INDEPENDENT_RECONCILIATION')
        self.assertEqual(self.daily_results[0]['phase'], 'PERSISTED_AWAIT_OWNER_SEAL_AND_INDEPENDENT_SAMPLE')
        self.assertEqual(result['success'], [])
        self.assertEqual(self.runtime.compute_calls, 1)
        self.assertEqual(self.runtime.writer_calls, 1)
        self.assertEqual(self.fixture.dispatch()['status'], 'UNKNOWN_RECONCILIATION_REQUIRED')
        self.assertEqual(self.runtime.writer_calls, 1)

    def test_partial_writer_side_effect_is_preserved_and_not_retried(self):
        self.runtime.fail_writer = True
        result = self.fixture.dispatch()
        self.assertEqual(result['status'], 'UNKNOWN_RECONCILIATION_REQUIRED')
        self.assertEqual(self.exception_attempt.phase, 'UNKNOWN_NO_BLIND_RETRY')
        self.assertTrue((self.runtime.parquet_dir / 'SYNTHETIC_PARTIAL_MARKER.txt').exists())
        self.assertEqual(self.fixture.dispatch()['status'], 'UNKNOWN_RECONCILIATION_REQUIRED')
        self.assertEqual(self.runtime.writer_calls, 1)

    def test_missing_checkpoint_registration_never_computes_replacement(self):
        path = self.runtime.root / self.runtime.checkpoint_ref['path']
        before = path.read_bytes()
        empty = canonical({'schema': 'OWNER_CHECKPOINT_REGISTRY_V1', 'entries': []})
        empty_ref = self.runtime.source('empty-registry.json', empty)
        self.runtime.checkpoint_binding = type(self.runtime.checkpoint_binding)(
            empty, empty_ref, self.runtime.checked, self.runtime.gate)
        self.assertEqual(self.fixture.dispatch()['status'], 'UNKNOWN_RECONCILIATION_REQUIRED')
        self.assertEqual(self.runtime.compute_calls, 0)
        self.assertEqual(self.runtime.writer_calls, 0)
        self.assertEqual(path.read_bytes(), before)

    def test_cold_checkpoint_binding_rejects_changed_checkpoint_bytes(self):
        path = self.runtime.root / self.runtime.checkpoint_ref['path']
        registry = self.runtime.root / 'inputs/registry.json'
        registry_ref = self.runtime.ref(registry)
        raw = registry.read_bytes()
        path.write_bytes(b'{}')
        with self.assertRaisesRegex(ValueError, 'FIXTURE_INPUT_CHANGED'):
            type(self.runtime.checkpoint_binding)(raw, registry_ref, self.runtime.checked, self.runtime.gate)
        self.assertEqual(self.runtime.compute_calls, 0)
        self.assertEqual(self.runtime.writer_calls, 0)
        self.assertEqual(path.read_bytes(), b'{}')

    def test_independently_reviewed_sealed_output_reuses_without_compute(self):
        f = self.fixture
        first = f.dispatch()
        result_ref = self.daily_results[0]['result_ref']
        self.runtime.seal_for_fixture(result_ref)
        output = f.pin(self.runtime.root / result_ref['path'])
        f.outputs[output.sha256] = output
        f.evidence['attempt_ids'].append(first['attempt_id'])
        f.evidence['last_attempt_id'] = first['attempt_id']
        f.evidence['ended_at'] = f.now.isoformat()
        f.evidence['stocks'][0] = {'symbol': '000001.SZ', 'status': 'SUCCESS',
                                  'attempt_id': first['attempt_id'], 'output_sha256': output.sha256}
        review = f.put('sealed-daily-review.json', canonical(f.evidence))
        f.registration = dataclasses.replace(f.registration,
            reconciliation_refs={'retry-1610': review, 'retry-1640': review})
        f.now += dt.timedelta(minutes=30)
        self.assertEqual(f.dispatch('retry-1640')['status'], 'NO_RETRY_NEEDED')
        self.assertEqual(self.runtime.compute_calls, 1)
        self.assertEqual(self.runtime.writer_calls, 1)


if __name__ == '__main__':
    unittest.main()
