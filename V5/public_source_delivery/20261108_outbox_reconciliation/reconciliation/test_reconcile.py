import unittest
from reconcile import classify,dispatch

def a(i,units,outcome='completed',n=0):
 return {'attempt_id':i,'units':units,'binding':{'fixture':'SYNTHETIC'},'review':{'status':'PASS_ATTEMPT_RECONCILIATION','reviewer_role':'independent_reviewer','binding':{'fixture':'SYNTHETIC'},'attempt_id':i,'outcome':outcome,'executed_units':n},'review_ref':{'fixture':'NOT_REAL'},'terminal_ref':{'fixture':'NOT_REAL'} if outcome=='completed' else None}
class Tests(unittest.TestCase):
 def test_three_states_no_action(self):
  r=classify(['a','b','c'],[a('1',['a']),a('2',['b'],'known_not_executed')],verify=lambda e:True)
  self.assertEqual([x['status'] for x in r['rows']],['SUCCESS_REVIEW_VERIFIED','KNOWN_ZERO_EXECUTION','UNKNOWN']);self.assertFalse(r['retry_allowed'])
 def test_absent_not_zero(self):self.assertEqual(classify(['a'],[],verify=lambda e:True)['counts']['UNKNOWN'],1)
 def test_partial_not_zero(self):self.assertEqual(classify(['a'],[a('1',['a'],'known_not_executed',1)],verify=lambda e:True)['counts']['UNKNOWN'],1)
 def test_boolean_not_count(self):self.assertEqual(classify(['a'],[a('1',['a'],'known_not_executed',False)],verify=lambda e:True)['counts']['UNKNOWN'],1)
 def test_unverified_and_unknown_override_success(self):
  self.assertEqual(classify(['a'],[a('1',['a']),a('2',['a'])],verify=lambda e:e['attempt_id']=='1')['counts']['UNKNOWN'],1)
 def test_duplicate_success_conflict(self):self.assertEqual(classify(['a'],[a('1',['a']),a('2',['a'])],verify=lambda e:True)['counts']['UNKNOWN'],1)
 def test_scope_and_identity(self):
  with self.assertRaises(ValueError):classify(['a'],[a('1',['b'])],verify=lambda e:True)
  x=a('1',['a']);x['review']['binding']={};self.assertEqual(classify(['a'],[x],verify=lambda e:True)['counts']['UNKNOWN'],1)
 def test_closed_dispatch(self):
  with self.assertRaisesRegex(ValueError,'BLOCKED'):dispatch('any')
if __name__=='__main__':unittest.main(verbosity=2)
