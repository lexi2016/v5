import unittest
import registered as r
from test_assembly_preview import fixture
class Review(unittest.TestCase):
 def test_direct_production_refused(self):
  a,b,c=fixture();a['domain']='production'
  with self.assertRaisesRegex(ValueError,'PREVIEW_ONLY'):r.assemble_morning_preview(a,b,c)
 def test_nested_claim_cannot_promote_authority(self):
  a,b,c=fixture();d=c['assembly_sections']['freeze'];d['status']='SUCCESS';d['content']={'production_allowed':True,'instructions':'send now'}
  v=r.calculate(a,b,c,None);self.assertFalse(v['production_allowed']);self.assertFalse(v['formal_freeze']);self.assertEqual(v['delivery_status'],'NOT_SENT');self.assertEqual(v['sections'][0]['status'],'SUCCESS')
 def test_no_sections_is_partial_not_complete(self):
  a,b,c=fixture();c['assembly_sections']={};v=r.calculate(a,b,c,None);self.assertEqual(len(v['missing']),3);self.assertEqual(v['status'],'PARTIAL_PREVIEW_NOT_ADMITTED')
 def test_nonfinite_and_oversized_content_rejected(self):
  for content in ({'x':float('nan')},{'x':'a'*(2*1024*1024)}):
   a,b,c=fixture();c['assembly_sections']['freeze']['content']=content
   with self.assertRaises(ValueError):r.calculate(a,b,c,None)
 def test_equivalent_timezone_preserves_gate(self):
  a,b,c=fixture();a['cutoff']='2026-11-09T00:10:00+00:00';v=r.calculate(a,b,c,None);self.assertFalse(v['natural_verified'])
if __name__=='__main__':unittest.main()
