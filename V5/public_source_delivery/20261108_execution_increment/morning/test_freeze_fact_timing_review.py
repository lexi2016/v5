import unittest
import registered as r
from test_freeze_fact_timing import fixture
class Review(unittest.TestCase):
 def test_null_does_not_bypass_timing(self):
  a,b,c=fixture();row=a['sources']['s1']['facts'][0];row['value']=None;row.pop('available_at')
  with self.assertRaises(ValueError):r.semantic_compare(a,b,c)
 def test_conflict_not_erased_by_valid_time(self):
  a,b,c=fixture();a['sources']['s1']['facts'][0]['value']=2;v=r.semantic_compare(a,b,c);self.assertFalse(v['passed']);self.assertEqual(v['conflicts'],['x'])
 def test_utc_equivalence(self):
  a,b,c=fixture();row=a['sources']['s1']['facts'][0];row['observed_at']='2026-11-08T22:29:00Z';row['available_at']='2026-11-08T22:29:30Z';self.assertTrue(r.semantic_compare(a,b,c)['passed'])
 def test_negative_float_age_and_bad_types(self):
  for age in (-1,60.0,'60'):
   a,b,c=fixture();b['semantic_max_age_seconds']['x']=age
   with self.assertRaises(ValueError):r.semantic_compare(a,b,c)
  for bad in (None,True,{},[]):
   a,b,c=fixture();a['sources']['s1']['facts'][0]['observed_at']=bad
   with self.assertRaises(ValueError):r.semantic_compare(a,b,c)
if __name__=='__main__':unittest.main()
