"""Synthetic checkpoint contract regressions; no quotes, native or writer calls."""
import copy
import hashlib
import json
import types
import unittest

import stages


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                    ensure_ascii=False, allow_nan=False).encode()).hexdigest()


class CheckpointContractTests(unittest.TestCase):
    def setUp(self):
        self.state = {'symbol': '000001.SZ', 'count': 2, 'last_date': '20261105'}
        self.rows = [
            {'symbol': '000001.SZ', 'event_date': '20261104', 'close': '10'},
            {'symbol': '000001.SZ', 'event_date': '20261105', 'close': '11'},
            {'symbol': '000001.SZ', 'event_date': '20261106', 'close': '12'},
        ]
        self.prepared = {'rows': self.rows, 'context': {'symbol': '000001.SZ', 'asof': '20261106'},
                         'prior_component_state': self.state}
        self.prior = {'continuation_ref': {'sha256': 'a' * 64}}
        self.cp = {'schema': 'OWNER_CHECKPOINT_PREFIX_V1',
                   'prior_continuation_sha256': 'a' * 64,
                   'state': copy.deepcopy(self.state), 'prefix_sha256': digest(self.rows[:-1])}
        self.calls = []

    def runtime(self):
        raw = json.dumps(self.cp).encode()
        ref = {'path': 'SYNTHETIC/checkpoint.json', 'bytes': len(raw),
               'sha256': hashlib.sha256(raw).hexdigest()}
        def compute(rows, context, prior_state, *, checkpoint_prefix_sha256):
            self.calls.append((rows, context, prior_state, checkpoint_prefix_sha256))
            return 'SYNTHETIC_COMPUTE_RESULT'
        return types.SimpleNamespace(bound_checkpoint_ref=lambda prior: ref, checked=lambda ref: raw,
                                     compute=compute)

    def call(self, runtime=None):
        self.assertTrue(hasattr(stages, 'compute_with_checkpoint'),
                        'public stage has not integrated the reviewed checkpoint adapter')
        return stages.compute_with_checkpoint(self.prepared, self.prior, runtime or self.runtime())

    def reject(self, code):
        with self.assertRaisesRegex(ValueError, code):
            self.call()
        self.assertEqual(self.calls, [])

    def test_required_keyword_uses_saved_prefix_and_same_objects(self):
        self.assertEqual(self.call(), 'SYNTHETIC_COMPUTE_RESULT')
        rows, context, state, prefix = self.calls[0]
        self.assertIs(rows, self.rows)
        self.assertIs(context, self.prepared['context'])
        self.assertIs(state, self.state)
        self.assertEqual(prefix, self.cp['prefix_sha256'])

    def test_missing_binding_never_synthesizes_checkpoint(self):
        self.assertTrue(hasattr(stages, 'compute_with_checkpoint'))
        with self.assertRaisesRegex(ValueError, 'CHECKPOINT_BINDING_REQUIRED'):
            self.call(types.SimpleNamespace())

    def test_changed_prefix_rejected(self):
        self.rows[0]['close'] = '999'
        self.reject('CHECKPOINT_PREFIX')

    def test_changed_state_rejected(self):
        self.state['count'] = 5
        self.reject('CHECKPOINT_STATE')

    def test_cross_prior_rejected(self):
        self.cp['prior_continuation_sha256'] = 'b' * 64
        self.reject('CHECKPOINT_PRIOR')

    def test_prior_sha_is_not_just_a_64_character_label(self):
        self.prior['continuation_ref']['sha256'] = 'z' * 64
        self.cp['prior_continuation_sha256'] = 'z' * 64
        self.reject('CHECKPOINT_PRIOR')

    def test_tampered_checkpoint_snapshot_rejected(self):
        self.assertTrue(hasattr(stages, 'compute_with_checkpoint'))
        runtime = self.runtime()
        runtime.checked = lambda ref: b'{}'
        with self.assertRaisesRegex(ValueError, 'CHECKPOINT_BYTES'):
            self.call(runtime)

    def test_boolean_component_count_rejected(self):
        self.state['count'] = True
        self.cp['state'] = copy.deepcopy(self.state)
        self.reject('PRIOR_COUNT_TYPE')

    def test_all_historical_dates_are_validated(self):
        self.rows[0]['event_date'] = '20260230'
        self.cp['prefix_sha256'] = digest(self.rows[:-1])
        self.reject('CHECKPOINT_DATE_FORMAT')

    def test_full_prefix_order_checked(self):
        self.rows[0]['event_date'] = '20261107'
        self.cp['prefix_sha256'] = digest(self.rows[:-1])
        self.reject('CHECKPOINT_DATE_ORDER')

    def test_full_prefix_symbol_checked(self):
        self.rows[0]['symbol'] = '000002.SZ'
        self.cp['prefix_sha256'] = digest(self.rows[:-1])
        self.reject('CHECKPOINT_ROW_SYMBOL')

    def test_target_context_checked(self):
        self.prepared['context']['asof'] = '20261109'
        self.reject('TARGET_IDENTITY')

    def test_preserved_original_provider_dependency_is_loadable(self):
        try:
            provider = stages.original_provider()
        except FileNotFoundError as error:
            self.fail('packaged stage lacks the exact original continuation dependency: ' + str(error))
        self.assertFalse(provider.FLAGS['production_allowed'])
        self.assertEqual(provider.LATEST_PINS['producer.py'],
                         '3b0d1685d4652133826dfa32148a4adfadabd6932d1dfb2ff2882fe91ab0bfaf')


if __name__ == '__main__':
    unittest.main()
