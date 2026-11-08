import copy,importlib.util,os,pathlib,unittest
BASE=pathlib.Path(__file__).parent
path=pathlib.Path(os.environ.get('JK_ENTRY',str(BASE/'isolated/handoff/morning_registered_execution_v2_20261107/registered.py')))
s=importlib.util.spec_from_file_location('entry',path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Tests(unittest.TestCase):
 def setUp(self):
  self.reg={'node':'jk-verify','source_date':'20261109','business_date':'20261109','cutoff':'2026-11-09T08:10:00+08:00'}
  self.policy={'required_comparisons':[{'symbol':'X','field':'open','source_ids':['S1','S2']}],'max_observation_age_seconds':600}
  self.doc={'source_day':'2026-11-09','records':[{'id':s,'source_id':s,'symbol':'X','field':'open','source_date':'2026-11-09','value':'1','url':'https://example.org/'+s,'observed_at':'2026-11-09T08:05:00+08:00','available_at':'2026-11-09T08:06:00+08:00'} for s in ('S1','S2')]}
 def run_case(self):return m.calculate(self.reg,self.policy,{'observations':self.doc},m.module('safeio'))
 def reject(self):
  try:r=self.run_case()
  except ValueError:return
  self.assertNotEqual(r['status'],'RECONCILED')
 def test_valid(self):
  r=self.run_case();self.assertEqual(r['status'],'RECONCILED');self.assertFalse(r['source_admission'])
 def test_empty(self):self.policy['required_comparisons']=[];self.doc['records']=[];self.reject()
 def test_one_source(self):self.doc['records'].pop();self.reject()
 def test_same_source_twice(self):self.doc['records'][1]['source_id']='S1';self.reject()
 def test_future_event(self):self.doc['records'][0]['observed_at']='2026-11-09T09:00:00+08:00';self.reject()
 def test_both_future(self):
  self.doc['records'][0]['observed_at']='2026-11-09T09:00:00+08:00'
  self.doc['records'][0]['available_at']='2026-11-09T09:01:00+08:00'
  with self.assertRaisesRegex(ValueError,'JK_AFTER_CUTOFF'):self.run_case()
 def test_future_available(self):self.doc['records'][0]['available_at']='2026-11-09T09:01:00+08:00';self.reject()
 def test_naive(self):self.doc['records'][0]['available_at']='2026-11-09T08:06:00';self.reject()
 def test_missing_time(self):del self.doc['records'][0]['available_at'];self.reject()
 def test_stale(self):self.doc['records'][0]['observed_at']='2026-11-09T07:00:00+08:00';self.reject()
 def test_missing_age(self):del self.policy['max_observation_age_seconds'];self.reject()
 def test_negative_age(self):self.policy['max_observation_age_seconds']=-1;self.reject()
 def test_bad_order(self):self.doc['records'][0]['available_at']='2026-11-09T08:04:00+08:00';self.reject()
 def test_conflict(self):self.doc['records'][0]['value']='2';self.reject()
 def test_scope(self):self.doc['records'][0]['symbol']='Y';self.reject()
 def test_duplicate_policy(self):self.policy['required_comparisons']*=2;self.reject()
 def test_unknown_source(self):self.doc['records'][0]['source_id']='S3';self.reject()
 def test_missing_source_policy(self):del self.policy['required_comparisons'][0]['source_ids'];self.reject()
 def test_cutoff_boundary(self):
  for r in self.doc['records']:r['observed_at']=r['available_at']=self.reg['cutoff']
  self.assertEqual(self.run_case()['status'],'RECONCILED')
 def test_age_boundary(self):
  for r in self.doc['records']:r['observed_at']='2026-11-09T08:00:00+08:00'
  self.assertEqual(self.run_case()['status'],'RECONCILED')
 def test_equivalent_timezone(self):
  for r in self.doc['records']:r['observed_at']='2026-11-09T00:05:00+00:00';r['available_at']='2026-11-09T00:06:00+00:00'
  self.assertEqual(self.run_case()['status'],'RECONCILED')
 def test_unregistered(self):self.assertEqual(m.dispatch('jk-verify','X','Y',lambda:None)['jobs_started'],0)
if __name__=='__main__':unittest.main()
