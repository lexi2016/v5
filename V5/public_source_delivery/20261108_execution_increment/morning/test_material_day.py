import unittest
import test_material_consumer as fixtures
class DayIdentity(unittest.TestCase):
 def fixture(self):
  c=fixtures.Consumer();c.setUp();c.doc['records']=[];c.manifest=c.make();return c
 def test_old_cutoff_cannot_be_relabelled_current(self):
  c=self.fixture();c.policy['cutoff']='2026-11-08T08:00:00+08:00'
  with self.assertRaisesRegex(ValueError,'RESULT_VERSION_OR_DAY'):c.make()
  c.manifest['cutoff']=c.policy['cutoff'];c.resign()
  with self.assertRaisesRegex(ValueError,'MATERIAL_CUTOFF_TARGET_DATE'):c.runone()
 def test_prior_local_day_even_when_utc_date_matches(self):
  c=self.fixture();c.policy['cutoff']='2026-11-08T15:59:59Z'
  with self.assertRaises(ValueError):c.make()
  c.manifest['cutoff']=c.policy['cutoff'];c.resign()
  with self.assertRaisesRegex(ValueError,'MATERIAL_CUTOFF_TARGET_DATE'):c.runone()
 def test_current_local_day_with_previous_utc_date(self):
  c=self.fixture();c.policy['cutoff']='2026-11-08T16:00:00Z';c.manifest=c.make();out=c.runone()['sections'][1]['content']
  self.assertEqual(out['target_date'],'20261109');self.assertEqual(out['cutoff'],'2026-11-08T16:00:00Z')
if __name__=='__main__':unittest.main()
