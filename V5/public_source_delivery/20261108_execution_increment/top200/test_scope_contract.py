"""Small synthetic contracts; no full pool, source calls or ranking changes."""
import copy
import datetime as dt
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
import registered as m


class ScopeContractTests(unittest.TestCase):
    def scope(self):
        symbols = ['000001.SZ', '000002.SZ']
        pin = {'path': 'authorized.json', 'bytes': 100, 'sha256': 'a' * 64}
        reg = {'domain': 'production', 'source_date': 20261106,
               'inputs': {'authorized_scope': pin}}
        document = {'schema': 'TOP200_AUTHORIZED_SCOPE_V1', 'source_date': 20261106,
                    'scope_kind': 'AUTHORIZED_COMPLETE_RESEARCH_UNIVERSE',
                    'authority_identity': 'SYNTHETIC_AUTHORITY_NOT_APPROVAL',
                    'universe_version': 'synthetic-v1', 'symbols': symbols,
                    'scope_count': 2, 'symbols_sha256': m.sha(m.canonical(symbols))}
        docs = {'authorized_scope': document,
                'source_review': {'authorized_scope_ref': pin}}
        return reg, docs, symbols

    def validator(self):
        function = getattr(m, 'validate_authorized_scope', None)
        self.assertTrue(callable(function), 'Authorized pool contract is not enforced')
        return function

    def test_production_missing_authorization_is_blocked(self):
        reg, docs, symbols = self.scope()
        del docs['authorized_scope']
        with self.assertRaisesRegex(ValueError, 'AUTHORIZED_SCOPE_CONTRACT_REQUIRED'):
            self.validator()(reg, docs, symbols)

    def test_exact_reviewed_scope_is_preserved_without_pit_promotion(self):
        reg, docs, symbols = self.scope()
        result = self.validator()(reg, docs, symbols)
        self.assertEqual(result['status'], 'MATCHED_REVIEWED_SCOPE_CONTRACT')
        self.assertEqual(result['scope_count'], 2)
        self.assertEqual(result['reference'], reg['inputs']['authorized_scope'])
        self.assertFalse(result['source_admission'])

    def test_subset_duplicate_and_changed_authorization_are_rejected(self):
        reg, docs, symbols = self.scope()
        for mutation in ('subset', 'duplicate', 'review', 'date', 'digest', 'count_bool'):
            with self.subTest(mutation=mutation):
                bad = copy.deepcopy(docs)
                if mutation == 'subset': bad['authorized_scope']['symbols'] = symbols[:1]
                if mutation == 'duplicate': bad['authorized_scope']['symbols'] = [symbols[0]] * 2
                if mutation == 'review': bad['source_review']['authorized_scope_ref']['sha256'] = 'b' * 64
                if mutation == 'date': bad['authorized_scope']['source_date'] = 20261105
                if mutation == 'digest': bad['authorized_scope']['symbols_sha256'] = 'c' * 64
                if mutation == 'count_bool': bad['authorized_scope']['scope_count'] = True
                with self.assertRaises(ValueError): self.validator()(reg, bad, symbols)

    def test_explicit_unknown_authority_or_version_cannot_be_matched(self):
        reg, docs, symbols = self.scope()
        for field in ('authority_identity', 'universe_version'):
            bad = copy.deepcopy(docs); bad['authorized_scope'][field] = 'UNKNOWN'
            with self.assertRaisesRegex(ValueError, 'AUTHORIZED_SCOPE_AUTHORITY'):
                self.validator()(reg, bad, symbols)

    def availability(self, times):
        function = getattr(m, 'source_availability', None)
        self.assertTrue(callable(function), 'Available time is conflated with capture time')
        return function(times, dt.datetime.fromisoformat('2026-11-06T15:00:00+08:00'),
                        dt.date(2026, 11, 6),
                        dt.datetime.fromisoformat('2026-11-06T19:00:00+08:00'))

    def test_later_availability_stays_late(self):
        result = self.availability({'capture_started': '2026-11-06T14:59:00+08:00',
                                    'capture_ended': '2026-11-06T14:59:30+08:00',
                                    'available_at': '2026-11-06T17:16:00+08:00'})
        self.assertTrue(result['late_source'])
        self.assertEqual(result['available_at'], '2026-11-06T17:16:00+08:00')

    def test_missing_availability_is_unknown_and_impossible_order_is_rejected(self):
        times = {'capture_started': '2026-11-06T14:59:00+08:00',
                 'capture_ended': '2026-11-06T14:59:30+08:00'}
        self.assertIsNone(self.availability(times)['late_source'])
        with self.assertRaises(ValueError):
            self.availability(dict(times, available_at='2026-11-06T14:58:00+08:00'))

    def test_exact_packaged_dependencies_load_without_running_resources(self):
        for key in ('ranking', 'original_rank', 'safeio'):
            with self.subTest(key=key):
                module = m.module(key)
                expected = {'ranking': 'project_rows', 'original_rank': 'resources', 'safeio': 'freeze'}[key]
                self.assertTrue(callable(getattr(module, expected)))

    def test_explicit_owner_gate_denial_blocks_before_input_reads(self):
        reg = {'run_id': 'synthetic-run', 'environment_id': 'synthetic-env',
               'domain': 'synthetic', 'trigger_source': 'MANUAL_TEST',
               'adapter_sha256': m.sha(Path(m.__file__).read_bytes()),
               'guard_factory': lambda _: None, 'owner_identity': 'SYNTHETIC_ONLY',
               'review': {}}
        for denied in (False, 0, 1, 'TRUE'):
            with self.subTest(denied=denied):
                reg['gate'] = lambda: denied
                with mock.patch.object(m, 'TRUSTED_RUNS', (reg,)), \
                     mock.patch.object(m, 'module', return_value=SimpleNamespace(resources=lambda: None)), \
                     mock.patch.object(m, 'read', side_effect=RuntimeError('INPUT_WAS_READ')) as read:
                    with self.assertRaisesRegex(ValueError, 'ORIGINAL_RESOURCE_GATE_DENIED'):
                        m.dispatch(reg['run_id'], reg['environment_id'])
                    read.assert_not_called()


if __name__ == '__main__':
    unittest.main()
