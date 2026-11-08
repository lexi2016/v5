import unittest,copy
import registered as r

def fixture():
 reg={'business_date':'20261109','source_date':'20261106','cutoff':'2026-11-09T06:30:00+08:00'}
 policy={'freeze_chain':{'schema':'FREEZE_CHAIN_POLICY_V1','version':'v1','mode':'GENESIS','expected_parent_identity':None}}
 docs={'panel':{'rows':[{'symbol':'000001.SZ','value':1}]},'freeze_changes':{'000001.SZ':'Initial explicit snapshot'}}
 return reg,policy,docs
class Test(unittest.TestCase):
 def test_genesis(self):
  x=r.build_freeze_lineage(*fixture());self.assertIsNone(x['parent_identity']);self.assertEqual(x['changes'][0]['kind'],'ADDED')
 def test_delta_changes(self):
  a,b,c=fixture();parent=r.build_freeze_lineage(a,b,c);b['freeze_chain'].update(mode='DELTA',version='v2',expected_parent_identity=parent['identity']);c['freeze_parent']=parent;c['panel']['rows'][0]['value']=2;c['freeze_changes']={'000001.SZ':'Corrected source'};x=r.build_freeze_lineage(a,b,c);self.assertEqual(x['parent_identity'],parent['identity']);self.assertEqual(x['changes'][0]['kind'],'CHANGED');self.assertNotEqual(x['changes'][0]['before'],x['changes'][0]['after'])
 def test_reasons_exact(self):
  for reasons in ({},{'000001.SZ':''},{'000001.SZ':'ok','000002.SZ':'extra'}):
   a,b,c=fixture();c['freeze_changes']=reasons
   with self.assertRaises(ValueError):r.build_freeze_lineage(a,b,c)
 def test_parent_tamper(self):
  a,b,c=fixture();parent=r.build_freeze_lineage(a,b,c);b['freeze_chain'].update(mode='DELTA',version='v2',expected_parent_identity=parent['identity']);c['freeze_parent']=parent;c['freeze_changes']={};parent['row_sha256']['000001.SZ']='0'*64
  with self.assertRaises(ValueError):r.build_freeze_lineage(a,b,c)
 def test_wrong_expected_parent(self):
  a,b,c=fixture();parent=r.build_freeze_lineage(a,b,c);b['freeze_chain'].update(mode='DELTA',version='v2',expected_parent_identity='0'*64);c['freeze_parent']=parent;c['freeze_changes']={}
  with self.assertRaises(ValueError):r.build_freeze_lineage(a,b,c)
 def test_no_auto_genesis(self):
  a,b,c=fixture();b.clear()
  with self.assertRaises(ValueError):r.build_freeze_lineage(a,b,c)
 def test_remove_add_noop(self):
  a,b,c=fixture();parent=r.build_freeze_lineage(a,b,c);b['freeze_chain'].update(mode='DELTA',version='v2',expected_parent_identity=parent['identity']);c['freeze_parent']=parent;c['freeze_changes']={};self.assertEqual(r.build_freeze_lineage(a,b,c)['changes'],[])
  c['panel']['rows']=[{'symbol':'000002.SZ','value':2}];c['freeze_changes']={'000001.SZ':'Removed from source','000002.SZ':'Added to source'};self.assertEqual([x['kind'] for x in r.build_freeze_lineage(a,b,c)['changes']],['ADDED','REMOVED'])
 def test_duplicate_and_backward(self):
  a,b,c=fixture();c['panel']['rows']*=2
  with self.assertRaises(ValueError):r.build_freeze_lineage(a,b,c)
  a,b,c=fixture();parent=r.build_freeze_lineage(a,b,c);b['freeze_chain'].update(mode='DELTA',version='v2',expected_parent_identity=parent['identity']);c['freeze_parent']=parent;c['freeze_changes']={};a['business_date']='20261108';a['cutoff']='2026-11-08T06:30:00+08:00'
  with self.assertRaises(ValueError):r.build_freeze_lineage(a,b,c)
if __name__=='__main__':unittest.main()
