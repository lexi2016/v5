import datetime as dt,tempfile,unittest,socket
from unittest.mock import patch
import runner as r
class Tests(unittest.TestCase):
 def setUp(self):
  self.p1=patch.object(socket.socket,'connect',side_effect=AssertionError('NO_NETWORK'));self.p1.start();self.addCleanup(self.p1.stop)
  self.p2=patch.object(socket,'getaddrinfo',side_effect=AssertionError('NO_DNS'));self.p2.start();self.addCleanup(self.p2.stop)
 def test_time_window(self):
  for minute,second,expected in [(0,20,'ON_TIME'),(0,31,'LATE'),(2,0,'MISSED')]:self.assertEqual(r.window_state(dt.datetime(2026,11,9,9,minute,second,tzinfo=r.TZ['HK']),'0900'),expected)
 def test_naive_rejected(self):
  with self.assertRaises(ValueError):r.window_state(dt.datetime(2026,11,9,9),'0900')
 def test_missing_quote_unknown(self):
  x=r.parse(b'','HK',['hk00001'],'0900',dt.datetime(2026,11,9,9,0,20,tzinfo=r.TZ['HK']));self.assertEqual(x[0]['status'],'UNKNOWN');self.assertEqual(x[0]['error'],'MISSING_IDENTITY')
 def test_missed_never_fetch(self):
  c=dict(date='2026-11-09',market='HK',scope_sha256='a'*64,keys=['hk00001'],source_id=r.SOURCE_ID)
  with tempfile.TemporaryDirectory() as d:
   x=r.capture(d,c,'0900',lambda:dt.datetime(2026,11,9,9,2,tzinfo=r.TZ['HK']),lambda _:self.fail('no late fetch'))
   self.assertEqual(x['status'],'MISSED');self.assertEqual(x['request_count'],0);self.assertEqual(x['analysis_admission'],'NOT_GRANTED')
 def test_scope_escape_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(ValueError):r.safe(d,'../escape')
if __name__=='__main__':unittest.main()
