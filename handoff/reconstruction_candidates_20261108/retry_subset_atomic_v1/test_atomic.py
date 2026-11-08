import copy,datetime as dt,hashlib,json,multiprocessing as mp,os,tempfile,unittest
from pathlib import Path
from coordinator import Coordinator,initialize
from subset_plan import canonical
import test_subset as fixtures

def worker(root,b,e,now,mode,ready=None,release=None):
 c=Coordinator(root);raw=canonical(e);outputs={r['output_sha256']:b'original-success-output' for r in e['stocks'] if r['status']=='SUCCESS'}
 def fake(symbols):
  if ready:ready.set()
  if mode=='crash':os._exit(71)
  if release:release.wait(10)
  return {s:b'new-output' for s in symbols}
 c.execute(b,raw,hashlib.sha256(raw).hexdigest(),outputs,'retry-1610',now,fake)
 c.close()

class AtomicTests(unittest.TestCase):
 def setUp(self):
  f=fixtures.Tests();f.setUp();self.b=f.b;self.e=f.e;self.now=f.now;self.outputs={f.sha:f.raw}
  self.tmp=tempfile.TemporaryDirectory();self.root=initialize(Path(self.tmp.name)/'owner');self.c=Coordinator(self.root);self.calls=[]
 def tearDown(self):self.c.close();self.tmp.cleanup()
 def run_case(self,fake=None,node='retry-1610'):
  raw=canonical(self.e)
  def default(symbols):self.calls.append(symbols);return {s:None for s in symbols}
  return self.c.execute(self.b,raw,hashlib.sha256(raw).hexdigest(),self.outputs,node,self.now,fake or default)
 def approve_second(self,terminal,success=False):
  self.e['attempt_ids'].append(terminal['attempt_id']);self.e['last_attempt_id']=terminal['attempt_id'];self.e['ended_at']='2026-11-09T16:10:00+08:00';self.e['stocks'][1]['attempt_id']=terminal['attempt_id'];self.now=dt.datetime.fromisoformat('2026-11-09T16:40:00+08:00')
  if success:
   raw=b'new-output';sha=hashlib.sha256(raw).hexdigest();self.outputs[sha]=raw;self.e['stocks'][1]={'symbol':'600027.SH','status':'SUCCESS','attempt_id':terminal['attempt_id'],'output_sha256':sha}
 def test_success_excluded(self):
  self.run_case();self.assertEqual(self.calls,[('600027.SH',)])
 def test_repeat_unknown_blocks(self):
  self.run_case()
  with self.assertRaisesRegex(ValueError,'UNKNOWN_CLAIM'):self.run_case()
  self.assertEqual(len(self.calls),1)
 def test_shared_retry_count(self):
  first=self.run_case();self.approve_second(first);second=self.run_case(node='retry-1640')
  self.assertNotEqual(first['attempt_id'],second['attempt_id']);self.assertEqual(len(self.calls),2)
  self.e['attempt_ids'].append(second['attempt_id']);self.e['last_attempt_id']=second['attempt_id']
  with self.assertRaises(ValueError):self.run_case(node='retry-1640')
 def test_failure_not_auto_approved(self):
  self.run_case()
  self.now+=dt.timedelta(minutes=30)
  with self.assertRaises(ValueError):self.run_case(node='retry-1640')
 def test_success_never_recomputed(self):
  first=self.run_case(lambda symbols:{s:b'new-output' for s in symbols});self.approve_second(first,success=True)
  self.assertEqual(self.run_case(node='retry-1640')['status'],'NO_RETRY_NEEDED');self.assertEqual(self.calls,[])
 def test_success_downgrade_rejected(self):
  first=self.run_case(lambda symbols:{s:b'new-output' for s in symbols});self.approve_second(first)
  with self.assertRaisesRegex(ValueError,'SUCCESS_CANNOT'):self.run_case(node='retry-1640')
 def test_identity_change_no_new_budget(self):
  self.run_case();self.b['run_id']='new';self.e['binding']=copy.deepcopy(self.b)
  with self.assertRaisesRegex(ValueError,'IDENTITY_CONFLICT'):self.run_case()
 def test_unknown_no_executor(self):
  self.e['stocks'][1]['status']='UNKNOWN'
  with self.assertRaises(ValueError):self.run_case()
  self.assertEqual(self.calls,[])
 def test_exception_stays_unknown(self):
  def boom(s):raise RuntimeError('synthetic partial work')
  with self.assertRaises(RuntimeError):self.run_case(boom)
  with self.assertRaisesRegex(ValueError,'UNKNOWN_CLAIM'):self.run_case()
 def test_real_process_crash(self):
  p=mp.Process(target=worker,args=(str(self.root),self.b,self.e,self.now,'crash'));p.start();p.join(10);self.assertEqual(p.exitcode,71)
  with self.assertRaisesRegex(ValueError,'UNKNOWN_CLAIM'):self.run_case()
 def test_crash_independent_reconciliation(self):
  p=mp.Process(target=worker,args=(str(self.root),self.b,self.e,self.now,'crash'));p.start();p.join(10);self.assertEqual(p.exitcode,71)
  claim=json.loads(next(self.root.glob('day-*/CLAIM-2.json')).read_text());self.approve_second(claim)
  self.run_case(node='retry-1640');self.assertEqual(len(self.calls),1)
 def test_process_competition(self):
  ready=mp.Event();release=mp.Event();p=mp.Process(target=worker,args=(str(self.root),self.b,self.e,self.now,'wait',ready,release));p.start()
  try:
   self.assertTrue(ready.wait(10))
   with self.assertRaises(BlockingIOError):self.run_case()
  finally:release.set();p.join(10)
  self.assertEqual(p.exitcode,0);self.assertEqual(self.calls,[])
 def test_malformed_claim_blocks(self):
  self.run_case();next(self.root.glob('day-*/CLAIM-2.json')).write_text('{')
  with self.assertRaises(ValueError):self.run_case()
 def test_symlink_lock(self):
  (self.root/'OWNER.lock').unlink()
  (self.root/'OWNER.lock').symlink_to(self.root/'ISOLATED_ONLY.json')
  with self.assertRaises(OSError):self.run_case()
 def test_day_rename_no_fresh_budget(self):
  self.run_case();(self.root/'day-20261109').rename(self.root/'archived-day')
  with self.assertRaises(OSError):self.run_case()
  self.assertEqual(len(self.calls),1)
 def test_day_replace_no_fresh_budget(self):
  self.run_case();(self.root/'day-20261109').rename(self.root/'archived-day');(self.root/'day-20261109').mkdir()
  with self.assertRaisesRegex(ValueError,'DAY_REPLACED'):self.run_case()
  self.assertEqual(len(self.calls),1)
 def test_day_removed_no_fresh_budget(self):
  import shutil
  self.run_case();shutil.rmtree(self.root/'day-20261109')
  with self.assertRaises(OSError):self.run_case()
  self.assertEqual(len(self.calls),1)
 def test_day_swap_during_executor_blocks_terminal(self):
  def swap(symbols):
   (self.root/'day-20261109').rename(self.root/'archived-day');(self.root/'day-20261109').mkdir()
   return {s:b'data' for s in symbols}
  with self.assertRaisesRegex(ValueError,'DAY_REPLACED'):self.run_case(swap)
  self.assertEqual(list(self.root.glob('**/RETURNED-*')),[])
 def test_lock_rename_no_recreate(self):
  (self.root/'OWNER.lock').rename(self.root/'old-lock')
  with self.assertRaises(OSError):self.run_case()
  self.assertFalse((self.root/'OWNER.lock').exists())
 def test_lock_replacement_rejected(self):
  (self.root/'OWNER.lock').rename(self.root/'old-lock');(self.root/'OWNER.lock').touch()
  with self.assertRaisesRegex(ValueError,'LOCK_REPLACED'):self.run_case()
 def test_lock_swap_during_execution_blocks_second_and_terminal(self):
  def swap(symbols):
   (self.root/'OWNER.lock').rename(self.root/'old-lock');(self.root/'OWNER.lock').touch()
   with self.assertRaisesRegex(ValueError,'LOCK_REPLACED'):self.run_case()
   return {s:b'data' for s in symbols}
  with self.assertRaisesRegex(ValueError,'LOCK_REPLACED'):self.run_case(swap)
  self.assertEqual(list(self.root.glob('**/RETURNED-*')),[])
 def test_wrong_executor_scope(self):
  with self.assertRaises(ValueError):self.run_case(lambda s:{'000001.SZ':b'wrong'})
  with self.assertRaisesRegex(ValueError,'UNKNOWN_CLAIM'):self.run_case()
if __name__=='__main__':unittest.main()
