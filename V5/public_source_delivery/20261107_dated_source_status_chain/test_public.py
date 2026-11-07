import unittest,json,datetime
from unittest.mock import patch
import source_chain as c
import dated_source_decision as d
class Reader:
 def checked(self,pin):return json.dumps(pin['synthetic']).encode()
class Tests(unittest.TestCase):
 def test_chain_unbound(self):
  with self.assertRaisesRegex(ValueError,'NO_APPROVED'):c.bind()
 def test_decision_unbound(self):
  with self.assertRaisesRegex(ValueError,'NO_APPROVED'):d.decision_context(None,None,None,None)
 def test_date_type_refused(self):
  with self.assertRaisesRegex(ValueError,'TARGET_DATE_TYPE'):c.inspect('20000101')
 def inspect(self,target):
  pins=[{}, {}, {}, {'synthetic':{'target_date':20000104}}, {'synthetic':{'target_date':20000103,'scope_count':3,'status':'SOURCE_CANDIDATE_PREPARED_PENDING_INDEPENDENT_REVIEW','ready_inputs':2,'blocked_count':1,'contract_ref':{'synthetic':{'inputs':[1,2],'source_blocked':[3]}}}}]
  with patch.multiple(c,HISTORICAL_DATE=20000103,SCOPE_COUNT=3),patch.object(c,'bind',return_value=(Reader(),pins,None)):return c.inspect(target)
 def test_reuse_status_not_execution(self):
  r=self.inspect(20000103);self.assertEqual(r['status'],'REUSE_HISTORICAL_SOURCE_PREPARATION_NO_RERUN');self.assertFalse(r['scheduler_business_execution_ready']);self.assertFalse(r['locks_acquired']);self.assertEqual(r['historical_source_preparation']['recomputed_stocks'],0)
 def test_new_date_stays_blocked(self):
  r=self.inspect(20000104);self.assertEqual(r['status'],'BLOCKED_DATED_SOURCE_NOT_BOUND');self.assertFalse(r['natural_business_verified']);self.assertTrue(r['blockers'])
if __name__=='__main__':unittest.main()
