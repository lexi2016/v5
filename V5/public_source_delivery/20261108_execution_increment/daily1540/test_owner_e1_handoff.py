import contextlib
import unittest
import test_owner_dispatch as fixtures

class E1HandoffTests(unittest.TestCase):
    setUp = fixtures.OwnerDispatchTests.setUp
    bridge = fixtures.OwnerDispatchTests.bridge
    record = fixtures.OwnerDispatchTests.record
    def test_failed_writer_reaches_owner_context_with_exact_attempt(self):
        bridge = self.bridge()
        record = self.record()
        original_context = record['owner_context']
        observed = []
        @contextlib.contextmanager
        def reconcile_context():
            with original_context() as held:
                try:
                    yield held
                except Exception as error:
                    observed.append((error.daily1540_attempt, self.entered))
                    raise
        record['owner_context'] = reconcile_context
        runtime_calls = []
        record['runtime_for_item'] = lambda item: runtime_calls.append(item['symbol']) or self.owner
        record['items'].append(dict(record['items'][0], symbol='UNREACHED_SYNTHETIC'))
        self.owner.fail_writer = True
        bridge.TRUSTED_RUNS[('fixture', 'env')] = record
        result = bridge.dispatch('fixture', 'env')
        self.assertEqual(result['status'], 'UNKNOWN_RECONCILIATION_REQUIRED')
        self.assertEqual(len(observed), 1)
        self.assertEqual(runtime_calls, [self.owner.symbol])
        self.assertEqual(len(result['items']), 1)
        attempt, still_locked = observed[0]
        self.assertTrue(still_locked)
        self.assertEqual(attempt.phase, 'UNKNOWN_NO_BLIND_RETRY')
        self.assertIn('state_ref', attempt.objects)
        self.assertIsNotNone(attempt.error)

    def test_owner_context_suppression_cannot_relabel_unknown(self):
        bridge = self.bridge()
        record = self.record()
        original_context = record['owner_context']
        observed = []
        @contextlib.contextmanager
        def suppress_context():
            with original_context() as held:
                try:
                    yield held
                except Exception as error:
                    observed.append(error.daily1540_attempt)
        record['owner_context'] = suppress_context
        self.owner.fail_writer = True
        bridge.TRUSTED_RUNS[('fixture', 'env')] = record
        result = bridge.dispatch('fixture', 'env')
        self.assertEqual(len(observed), 1)
        self.assertEqual(result['status'], 'UNKNOWN_RECONCILIATION_REQUIRED')
        self.assertFalse(result['automatic_retry_allowed'])
        self.assertEqual(result['jobs_started'], 1)
        self.assertEqual(len(result['items']), 1)
