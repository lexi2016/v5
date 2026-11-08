"""Regression for completed third attempts; synthetic evidence only."""
import datetime as dt
import hashlib
import unittest

from subset_plan import canonical, plan
import test_subset as fixtures


class CompletionReuseTests(unittest.TestCase):
    def setUp(self):
        f = fixtures.Tests()
        f.setUp()
        self.binding = f.b
        self.review = f.e
        self.outputs = {f.sha: f.raw}
        self.review['attempt_ids'] = ['a1', 'a2', 'a3']
        self.review['last_attempt_id'] = 'a3'
        self.review['ended_at'] = '2026-11-09T16:40:00+08:00'
        self.review['stocks'][1] = {'symbol': '600027.SH', 'attempt_id': 'a3',
                                   'status': 'SUCCESS', 'output_sha256': f.sha}
        self.now = dt.datetime.fromisoformat('2026-11-09T16:40:01+08:00')

    def run_plan(self):
        raw = canonical(self.review)
        return plan(self.binding, raw, hashlib.sha256(raw).hexdigest(),
                    self.outputs, 'retry-1640', self.now)

    def test_third_attempt_success_is_reused_without_fourth_budget(self):
        result = self.run_plan()
        self.assertEqual(result['status'], 'NO_RETRY_NEEDED')
        self.assertEqual(result['retry_symbols'], [])
        self.assertIsNone(result['next_attempt_ordinal'])

    def test_complete_reuse_does_not_wait_for_retry_cooldown(self):
        self.review['attempt_ids'] = ['a1', 'a3']
        self.assertEqual(self.run_plan()['status'], 'NO_RETRY_NEEDED')

    def test_future_completion_is_not_reused(self):
        self.review['ended_at'] = '2026-11-09T16:41:00+08:00'
        with self.assertRaises(ValueError):
            self.run_plan()

    def test_third_attempt_failure_remains_blocked(self):
        self.review['stocks'][1] = {'symbol': '600027.SH', 'attempt_id': 'a3',
                                   'status': 'FAILED_CLEAN', 'retryable': True,
                                   'effects': 'INDEPENDENTLY_CONFIRMED_NO_PERSISTED_EFFECTS'}
        self.now += dt.timedelta(hours=1)
        with self.assertRaises(ValueError):
            self.run_plan()


if __name__ == '__main__':
    unittest.main()
