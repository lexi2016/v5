import copy,datetime as dt,hashlib,unittest
from subset_plan import canonical,plan
class Tests(unittest.TestCase):
 def setUp(self):
  self.raw=b'original-success-output';self.sha=hashlib.sha256(self.raw).hexdigest()
  self.b={'run_id':'fixture-run','data_date':'20261109','input_version':'fixture-input','code_version':'fixture-code','symbols':['000001.SZ','600027.SH'],'original_binding':{'contract_ref':{'path':'fixture','sha256':'a'*64},'identity':'fixture-identity','date':'20261109','node':'owner','input_refs':[{'fixture':True}],'code_refs':[{'fixture':True}],'argv':['unchanged-owner'],'resources':{'fixture':'not-live'},'locks':['unchanged-lock']}}
  self.e={'schema':'ISOLATED_SUBSET_RECONCILIATION_V1','reviewer_role':'independent_reviewer','binding':copy.deepcopy(self.b),'activity':'CONFIRMED_ENDED','unresolved_attempts':[],'attempt_ids':['a1'],'last_attempt_id':'a1','ended_at':'2026-11-09T15:40:00+08:00','stocks':[{'symbol':'000001.SZ','attempt_id':'a1','status':'SUCCESS','output_sha256':self.sha},{'symbol':'600027.SH','attempt_id':'a1','status':'FAILED_CLEAN','retryable':True,'effects':'INDEPENDENTLY_CONFIRMED_NO_PERSISTED_EFFECTS'}]}
  self.now=dt.datetime.fromisoformat('2026-11-09T16:10:00+08:00')
 def run_plan(self,node='retry-1610'):
  raw=canonical(self.e);return plan(self.b,raw,hashlib.sha256(raw).hexdigest(),{self.sha:self.raw},node,self.now)
 def test_subset(self):
  p=self.run_plan();self.assertEqual(p['retry_symbols'],['600027.SH']);self.assertEqual(len(p['reuse_success']),1);self.assertFalse(p['dispatchable'])
 def test_identity(self):
  for k in ['run_id','data_date','input_version','code_version']:
   with self.subTest(k=k):
    old=self.e['binding'][k];self.e['binding'][k]='changed'
    with self.assertRaises(ValueError):self.run_plan()
    self.e['binding'][k]=old
 def test_unknown(self):
  self.e['stocks'][1]['status']='UNKNOWN'
  with self.assertRaisesRegex(ValueError,'UNKNOWN'):self.run_plan()
 def test_failed_effects(self):
  self.e['stocks'][1]['effects']='PARTIAL'
  with self.assertRaises(ValueError):self.run_plan()
 def test_missing_success(self):
  self.raw=b'changed'
  with self.assertRaises(ValueError):self.run_plan()
 def test_running(self):
  self.e['activity']='RUNNING'
  with self.assertRaises(ValueError):self.run_plan()
 def test_unresolved(self):
  self.e['unresolved_attempts']=['a0']
  with self.assertRaises(ValueError):self.run_plan()
 def test_count(self):
  self.e['attempt_ids']=['a0','a1','a2']
  with self.assertRaises(ValueError):self.run_plan()
 def test_duplicate(self):
  self.e['stocks'][1]=self.e['stocks'][0]
  with self.assertRaises(ValueError):self.run_plan()
 def test_missing_scope(self):
  self.e['stocks'].pop()
  with self.assertRaises(ValueError):self.run_plan()
 def test_cross_stock_attempt(self):
  self.e['stocks'][1]['attempt_id']='other'
  with self.assertRaises(ValueError):self.run_plan()
 def test_cooldown(self):
  self.e['ended_at']='2026-11-09T15:41:00+08:00'
  with self.assertRaises(ValueError):self.run_plan()
 def test_1640_gate(self):
  with self.assertRaises(ValueError):self.run_plan('retry-1640')
  p1=self.run_plan();self.now+=dt.timedelta(minutes=30);p2=self.run_plan('retry-1640');self.assertEqual(p1['intent_id'],p2['intent_id'])
 def test_changed_guard_identity(self):
  self.e['binding']['original_binding']['locks']=['new-lock']
  with self.assertRaises(ValueError):self.run_plan()
 def test_all_success(self):
  self.e['stocks'][1]={'symbol':'600027.SH','attempt_id':'a1','status':'SUCCESS','output_sha256':self.sha}
  self.assertEqual(self.run_plan()['status'],'NO_RETRY_NEEDED')
 def test_bad_pin(self):
  with self.assertRaises(ValueError):plan(self.b,canonical(self.e),'0'*64,{},'retry-1610',self.now)
 def test_naive(self):
  self.now=self.now.replace(tzinfo=None)
  with self.assertRaises(ValueError):self.run_plan()
 def test_caller_mutation_cannot_change_plan(self):
  result=self.run_plan();before=copy.deepcopy(result)
  self.b['original_binding']['locks']=['different']
  self.assertEqual(result,before)
 def test_repeat_no_mutation(self):
  old=copy.deepcopy(self.e);self.assertEqual(self.run_plan(),self.run_plan());self.assertEqual(old,self.e)
if __name__=='__main__':unittest.main()
