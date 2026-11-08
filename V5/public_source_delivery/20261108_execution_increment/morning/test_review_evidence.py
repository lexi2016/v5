import unittest
import test_material_consumer as fixtures
class ReviewEvidence(unittest.TestCase):
 def fixture(self):
  c=fixtures.Consumer();c.setUp();c.doc['records'][0]['available_at']='2026-11-09T07:02:00+08:00';return c
 def test_producer_and_consumer_both_refuse_same_bad_details(self):
  for field,value in [('facts',False),('title','\t\n'),('source_url','https://user@example.invalid'),('source_url','https://:pass@example.invalid')]:
   c=self.fixture();c.manifest=c.make();c.doc['records'][0]['details'][field]=value
   with self.assertRaises(ValueError):c.make()
   c.manifest['records'][0]['columns']['announcements'][0]['details'][field]=value;c.resign()
   with self.assertRaises(ValueError):c.runone()
 def test_unknown_text_is_preserved_not_upgraded(self):
  c=self.fixture();c.doc['records'][0]['details']['facts']='UNKNOWN';c.manifest=c.make();out=c.runone();self.assertEqual(out['sections'][1]['content']['records'][0]['columns']['announcements'][0]['details']['facts'],'UNKNOWN');self.assertFalse(out['business_accepted'])
 def test_nonavailable_empty_object_matches_producer(self):
  c=self.fixture();c.doc['records'][0].update(status='NOT_OBSERVED',event_at=None,details={});c.manifest=c.make();out=c.runone();self.assertEqual(out['sections'][1]['content']['records'][0]['columns']['announcements'][0]['details'],{})
if __name__=='__main__':unittest.main()
