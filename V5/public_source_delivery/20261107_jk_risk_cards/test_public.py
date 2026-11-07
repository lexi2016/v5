import unittest,tempfile,json,hashlib
from pathlib import Path
from unittest.mock import patch
import node_results_api as a
class Tests(unittest.TestCase):
 def call(self,result,gate=lambda:None):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);pins={}
   for role,data in {'jk_result':result,'jk_observations':{'records':[]}}.items():
    raw=json.dumps(data).encode();(root/role).write_bytes(raw);pins[role]={'path':role,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
   with patch.multiple(a,ROOT=root,RECORD_DATE='20000102',SOURCE_DATE='20000101',ISO_SOURCE_DATE='2000-01-01',PRIVATE_BINDINGS={'jk-verify':pins}):return a.NodeResultsService(gate).get('jk-verify','20000102')
 def result(self):return {'source_date':'2000-01-01','source_admission':False,'natural_verified':False,'business_accepted':False,'comparisons':[{'field':'post_session_reference','value':None,'status':'CROSS_SEMANTIC_DISCREPANCY_UNRESOLVED'}]}
 def test_default_refusal(self):
  for node in ['jk-verify','morning-materials']:
   with self.assertRaisesRegex(ValueError,'PRIVATE_BINDING'):a.NodeResultsService(lambda:None).get(node,'20000102')
 def test_jk_unresolved_preserved(self):
  r=self.call(self.result());self.assertEqual(r['business_acceptance'],'NOT_GRANTED');self.assertFalse(r['natural_verified'])
 def test_cross_semantic_cannot_merge(self):
  r=self.result();r['comparisons'][0]['value']=1
  with self.assertRaisesRegex(ValueError,'CROSS_SEMANTIC'):self.call(r)
 def test_strict_false(self):
  r=self.result();r['source_admission']=0
  with self.assertRaisesRegex(ValueError,'JK_SCOPE'):self.call(r)
 def test_resource_gate_retained(self):
  def gate():raise ValueError('RESOURCE')
  with self.assertRaisesRegex(ValueError,'RESOURCE'):self.call(self.result(),gate)
if __name__=='__main__':unittest.main()
