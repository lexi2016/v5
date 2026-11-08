import unittest,copy
import registered as r
from test_freeze_lineage import fixture
class Review(unittest.TestCase):
 def delta(self):
  a,b,c=fixture();parent=r.build_freeze_lineage(a,b,c);b['freeze_chain'].update(mode='DELTA',version='v2',expected_parent_identity=parent['identity']);c.update(freeze_parent=parent,freeze_changes={});return a,b,c
 def test_genesis_cannot_accept_parent(self):
  a,b,c=fixture();c['freeze_parent']={}
  with self.assertRaises(ValueError):r.build_freeze_lineage(a,b,c)
 def test_same_version_refused(self):
  a,b,c=self.delta();b['freeze_chain']['version']='v1'
  with self.assertRaisesRegex(ValueError,'VERSION'):r.build_freeze_lineage(a,b,c)
 def test_reason_required_for_deletion(self):
  a,b,c=self.delta();c['panel']['rows']=[]
  with self.assertRaisesRegex(ValueError,'REASONS'):r.build_freeze_lineage(a,b,c)
 def test_rehashed_future_parent_still_rejected(self):
  a,b,c=self.delta();p=c['freeze_parent'];p['cutoff']='2026-11-09T06:31:00+08:00';p['identity']=r.sha(r.canonical({k:v for k,v in p.items() if k!='identity'}));b['freeze_chain']['expected_parent_identity']=p['identity']
  with self.assertRaisesRegex(ValueError,'DATE_ORDER'):r.build_freeze_lineage(a,b,c)
 def test_canonical_order_and_detachment(self):
  a,b,c=fixture();x=r.build_freeze_lineage(a,b,c);c['panel']['rows'][0]={'value':1,'symbol':'000001.SZ'};self.assertEqual(x,r.build_freeze_lineage(a,b,c));c['panel']['rows'][0]['value']=2;self.assertEqual(x['row_sha256']['000001.SZ'],x['changes'][0]['after'])
if __name__=='__main__':unittest.main()
