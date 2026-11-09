import datetime as dt
import unittest
import test_subset as fixture
from subset_plan import aware

class ZeroOffsetTests(unittest.TestCase):
    def test_lossy_offset_rejected(self):
        for sign in ('+', '-'):
            for offset in ('00','0000','00:00','000000','00:00:00'):
                for sep in ('.', ','):
                    for fraction in ('1','000001','123456'):
                        with self.subTest(sign=sign,offset=offset,sep=sep,fraction=fraction):
                            with self.assertRaisesRegex(ValueError,'UNSUPPORTED_ZERO_FRACTIONAL_OFFSET'):
                                aware('2026-11-09T07:40:00'+sign+offset+sep+fraction)

    def test_cooldown_ended_at_two_nodes(self):
        for node,local,utc in [('retry-1610','16:10:00','07:40:00'),('retry-1640','16:40:00','08:10:00')]:
            for sep in ('.',','):
                t=fixture.Tests();t.setUp();t.now=dt.datetime.fromisoformat('2026-11-09T'+local+'+08:00')
                t.e['ended_at']='2026-11-09T'+utc+'-00:00:00'+sep+'000001'
                # Oracle constructed without string offset parser.
                ended=dt.datetime.combine(dt.date(2026,11,9),dt.time.fromisoformat(utc),dt.timezone(-dt.timedelta(microseconds=1)))
                self.assertEqual(t.now-ended,dt.timedelta(minutes=30,microseconds=-1))
                with self.assertRaisesRegex(ValueError,'UNSUPPORTED_ZERO_FRACTIONAL_OFFSET'):t.run_plan(node)

    def test_available_after_shared_parser(self):
        for utc in ('08:10:00','08:40:00'):
            for sep in ('.',','):
                with self.assertRaisesRegex(ValueError,'UNSUPPORTED_ZERO_FRACTIONAL_OFFSET'):
                    aware('2026-11-09T'+utc+'-00:00:00'+sep+'000001')

    def test_preserved_representable_offsets(self):
        for sign in (-1,1):
            for offset,seconds in [('00:00:01',1),('00:01',60),('01:00',3600),('000001',1)]:
                for sep in ('.',','):
                    s='2026-11-09T07:40:00'+('+' if sign==1 else '-')+offset+sep+'000001'
                    self.assertEqual(aware(s).utcoffset(),sign*dt.timedelta(seconds=seconds,microseconds=1))
        for s in ('2026-11-09T07:40:00Z','2026-11-09T07:40:00+00:00:00.000000','2026-11-09T07:40:00.000001+08:00'):
            self.assertEqual(aware(s),dt.datetime.fromisoformat(s))

if __name__=='__main__':unittest.main()
