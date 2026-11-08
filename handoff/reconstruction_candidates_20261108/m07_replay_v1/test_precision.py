import json,unittest
import test_replay as fixtures
class Precision(unittest.TestCase):
 setUp=fixtures.Tests.setUp
 fixture=fixtures.Tests.fixture
 runone=fixtures.Tests.runone
 def check(self,stage,field,stamp):
  x=self.fixture(stage)
  if field=='cutoff':x[field]=stamp
  else:x['recording'][field]=stamp
  p=self.runone(x);self.assertEqual(p.returncode,2,p.stdout);r=json.loads(p.stdout)
  self.assertIn('M07_TIME_PRECISION_UNSUPPORTED',r['reason']);self.assertFalse(r['production_allowed']);self.assertFalse(r['natural_verified'])
 def test_auction_acquired_late_submicro(self):self.check('STAGE_0925','acquired_at','2026-10-12T09:25:05.0000001+08:00')
 def test_open_acquired_late_submicro(self):self.check('STAGE_0930_0935','acquired_at','2026-10-12T09:35:05.0000001+08:00')
 def test_auction_nonexact_cutoff(self):self.check('STAGE_0925','cutoff','2026-10-12T09:25:05.0000001+08:00')
 def test_open_nonexact_cutoff(self):self.check('STAGE_0930_0935','cutoff','2026-10-12T09:35:05.0000001+08:00')
 def test_captured_submicro(self):self.check('STAGE_0925','captured_at','2026-10-12T09:25:00.0000001+08:00')
 def test_comma_fraction(self):self.check('STAGE_0925','acquired_at','2026-10-12T09:25:05,0000001+08:00')
 def test_offset_fraction(self):self.check('STAGE_0925','acquired_at','2026-10-12T09:25:05+08:00:00.0000001')
 def test_supported_microseconds_retained(self):
  x=self.fixture('STAGE_0925');x['recording']['acquired_at']='2026-10-12T09:25:04.999999+08:00'
  p=self.runone(x);self.assertEqual(p.returncode,0,p.stdout);r=json.loads(p.stdout);self.assertFalse(r['production_allowed']);self.assertFalse(r['natural_verified'])
 def test_one_microsecond_late_still_original_rejection(self):
  x=self.fixture('STAGE_0930_0935');x['recording']['acquired_at']='2026-10-12T09:35:05.000001+08:00'
  p=self.runone(x);self.assertEqual(p.returncode,2,p.stdout);self.assertIn('M07_RECORDING_OUTSIDE_WINDOW_OR_FUTURE',p.stdout)
if __name__=='__main__':unittest.main()
