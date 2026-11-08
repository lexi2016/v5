import unittest,copy
import registered as r
from test_jk_semantics import fixture
class ReviewR01(unittest.TestCase):
 def norm(self,p,d):return r.normalize_jk_semantics(d['observations'],p)
 def test_no_guess_alias_when_policy_missing(self):
  a,p,d=fixture();p['required_comparisons'][0].pop('semantic_contract')
  with self.assertRaises(ValueError):self.norm(p,d)
 def test_provider_urls_without_https_or_with_credentials_refused(self):
  for url in ('http://x.invalid/','https://user:password@x.invalid/','https://x.invalid/#part'):
   a,p,d=fixture();p['provider_catalog']['s1']['allowed_urls']=[url];d['observations']['records'][0]['url']=url
   with self.assertRaises(ValueError):self.norm(p,d)
 def test_detached_normalization_and_explicit_raw_evidence(self):
  a,p,d=fixture();p['required_comparisons'][0]['semantic_contract']['raw_fields']['s1']=['session_open'];d['observations']['records'][0]['field']='session_open';before=copy.deepcopy(d);normalized,evidence,gaps=self.norm(p,d)
  self.assertEqual(d,before);self.assertEqual(normalized['records'][0]['field'],'open');self.assertEqual(evidence[('JK','open')][0]['raw_field'],'session_open');self.assertEqual(gaps,[])
 def test_invalid_values_all_remain_gaps(self):
  for v in (0,False,'Infinity','sNaN',{},[]):
   a,p,d=fixture();d['observations']['records'][0]['value']=v;n,e,g=self.norm(p,d);self.assertEqual(len(g),1)
 def test_missing_unit_and_extra_provider_refused(self):
  a,p,d=fixture();del d['observations']['records'][0]['unit']
  with self.assertRaises(ValueError):self.norm(p,d)
  a,p,d=fixture();p['provider_catalog']['s3']=copy.deepcopy(p['provider_catalog']['s1'])
  with self.assertRaises(ValueError):self.norm(p,d)
if __name__=='__main__':unittest.main()
