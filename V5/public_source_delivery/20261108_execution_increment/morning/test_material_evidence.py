import unittest
import test_material_consumer as fixtures
class Evidence(unittest.TestCase):
 def fixture(self):
  c=fixtures.Consumer();c.setUp();c.doc['records'][0]['available_at']='2026-11-09T07:02:00+08:00';c.manifest=c.make();return c
 def effective(self,c):return c.manifest['records'][0]['columns']['announcements'][0]
 def test_empty_or_nonstring_available_evidence(self):
  for field in ('source_url','title','body_reference','facts','inferences','counterevidence'):
   for bad in ('', ' ',None,{},1):
    with self.subTest(field=field,bad=bad):
     c=self.fixture();self.effective(c)['details'][field]=bad;c.resign()
     with self.assertRaises(ValueError):c.runone()
 def test_source_url_consumer_enforces_producer_contract(self):
  for url in ('http://example.invalid','https:///absent','https://user:pass@example.invalid','javascript:example'):
   with self.subTest(url=url):
    c=self.fixture();self.effective(c)['details']['source_url']=url;c.resign()
    with self.assertRaises(ValueError):c.runone()
 def test_nonavailable_details_still_must_be_object(self):
  c=self.fixture();row=self.effective(c);row.update(status='BODY_UNAVAILABLE',details='unstructured');c.resign()
  with self.assertRaises(ValueError):c.runone()
 def test_valid_effective_evidence_passes(self):
  c=self.fixture();out=c.runone();self.assertEqual(out['sections'][1]['content']['records'][0]['columns']['announcements'][0]['status'],'AVAILABLE');self.assertFalse(out['business_accepted'])
if __name__=='__main__':unittest.main()
