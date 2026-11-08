import datetime as dt
import unittest
import test_subset as fixture
from subset_plan import aware

class PrecisionTests(unittest.TestCase):
    def test_submicrosecond_boundary_rejected(self):
        for node, now, ended in (
            ('retry-1610', '16:10:00', '15:40:00'),
            ('retry-1640', '16:40:00', '16:10:00'),
        ):
            for fraction in ('.0000001', ',0000001', '.123456789'):
                with self.subTest(node=node, fraction=fraction):
                    t = fixture.Tests(); t.setUp()
                    t.now = dt.datetime.fromisoformat('2026-11-09T'+now+'+08:00')
                    t.e['ended_at'] = '2026-11-09T'+ended+fraction+'+08:00'
                    with self.assertRaisesRegex(ValueError, 'UNSUPPORTED_TIME_PRECISION'):
                        t.run_plan(node)

    def test_supported_cooldown_boundaries(self):
        for node, now in (('retry-1610','16:10:00'), ('retry-1640','16:40:00')):
            for delta in (-1, 0, 1):
                with self.subTest(node=node, microseconds_after_boundary=delta):
                    t=fixture.Tests(); t.setUp()
                    t.now=dt.datetime.fromisoformat('2026-11-09T'+now+'+08:00')
                    t.e['ended_at']=(t.now-dt.timedelta(minutes=30)+dt.timedelta(microseconds=delta)).isoformat()
                    if delta>0:
                        with self.assertRaisesRegex(ValueError, 'RETRY_COOLDOWN'):t.run_plan(node)
                    else:
                        result=t.run_plan(node)
                        self.assertEqual(result['retry_symbols'], ['600027.SH'])
                        self.assertFalse(result['dispatchable'])
                        self.assertEqual(len(result['reuse_success']),1)

    def test_fractional_offset_precision_rejected(self):
        with self.assertRaisesRegex(ValueError, 'UNSUPPORTED_TIME_PRECISION'):
            aware('2026-11-09T15:40:00+08:00:00.0000001')

    def test_supported_precision_preserved(self):
        for raw in ('2026-11-09T15:40:00+08:00','2026-11-09T15:40:00.123456+08:00','2026-11-09T07:40:00Z'):
            self.assertEqual(aware(raw),dt.datetime.fromisoformat(raw))

if __name__=='__main__': unittest.main()
