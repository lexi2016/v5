import unittest
import registered as m
import test_material_consumer as f
class ReviewDay(unittest.TestCase):
 def fixture(self):
  c=f.Consumer();c.setUp();c.doc['records']=[];c.manifest=c.make();return c
 def test_next_local_day_rejected_before_temporal_order(self):
  c=self.fixture();c.manifest['cutoff']='2026-11-09T16:00:00Z';c.resign()
  with self.assertRaisesRegex(ValueError,'CUTOFF_TARGET_DATE'):c.runone()
 def test_target_midnight_microsecond_boundary(self):
  c=self.fixture();c.manifest['cutoff']='2026-11-08T15:59:59.999999Z';c.resign()
  with self.assertRaisesRegex(ValueError,'CUTOFF_TARGET_DATE'):c.runone()
  c.manifest['cutoff']='2026-11-08T16:00:00.000000Z';c.resign();out=c.runone();self.assertFalse(out['business_accepted']);self.assertEqual(out['sections'][1]['content']['source_admission'],'UNKNOWN')
if __name__=='__main__':unittest.main()
