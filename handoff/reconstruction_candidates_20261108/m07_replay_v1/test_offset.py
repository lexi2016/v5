import json,unittest
import test_replay as fixtures
class Offset(unittest.TestCase):
 setUp=fixtures.Tests.setUp
 fixture=fixtures.Tests.fixture
 runone=fixtures.Tests.runone
 def test_fractional_offset_late_rejected(self):
  for stage,minute in [('STAGE_0925','25'),('STAGE_0930_0935','35')]:
   for field in ['cutoff','acquired_at']:
    with self.subTest(stage=stage,field=field):
     self.folder=self.folder/(stage+field);self.folder.mkdir();x=self.fixture(stage)
     stamp=f'2026-10-12T01:{minute}:05-00:00:00.5'
     if field=='cutoff':x[field]=stamp
     else:x['recording'][field]=stamp
     p=self.runone(x);self.assertEqual(p.returncode,2,p.stdout);self.assertIn('M07_OFFSET_PRECISION_UNSUPPORTED',p.stdout)
 def test_utc_and_minute_offsets_preserved(self):
  for suffix in ['Z','+00:00','-00:00']:
   self.folder=self.folder/str(len(suffix));self.folder.mkdir();x=self.fixture('STAGE_0925');x['recording']['acquired_at']='2026-10-12T01:25:05'+suffix;p=self.runone(x);self.assertEqual(p.returncode,0,p.stdout)
if __name__=='__main__':unittest.main()
