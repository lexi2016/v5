import unittest,tempfile,pathlib,json,hashlib,os,subprocess,sys
from ledger import Ledger,initialize
class Tests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.root=initialize(pathlib.Path(self.t.name)/'isolated');self.l=Ledger(self.root);self.i={'symbol':'FIXTURE','event_date':'20261106','input_sha256':'input','code_sha256':'code','checkpoint_sha256':'checkpoint'}
 def tearDown(self):self.t.cleanup()
 def artifact(self):
  p=self.root/'sample.txt';p.write_bytes(b'isolated fixture');return {'path':p.name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
 def test_cross_directory_unknown_no_restart(self):
  self.assertEqual(self.l.claim(self.i,'a/out')['status'],'CLAIMED');self.assertEqual(self.l.claim(self.i,'b/out')['status'],'UNKNOWN_INSPECT_NO_RETRY')
 def test_success_reuse_checks_bytes(self):
  self.l.claim(self.i,'a');a=self.artifact();self.l.finish(self.i,[a]);self.assertEqual(self.l.claim(self.i,'b')['status'],'REUSE_VERIFIED');(self.root/a['path']).write_bytes(b'bad')
  with self.assertRaises(ValueError):self.l.claim(self.i,'c')
 def test_failure_not_retried(self):
  self.l.claim(self.i,'a');self.l.finish(self.i,error='injected');self.assertEqual(self.l.claim(self.i,'b')['status'],'FAILED_INSPECT_NO_RETRY')
 def test_changed_version_cannot_bypass(self):
  self.l.claim(self.i,'a')
  for k in ('input_sha256','code_sha256','checkpoint_sha256'):
   with self.assertRaises(ValueError):self.l.claim({**self.i,k:'changed'},'b')
 def test_no_terminal_overwrite(self):
  self.l.claim(self.i,'a');self.l.finish(self.i,error='failure')
  with self.assertRaises(ValueError):self.l.finish(self.i,[self.artifact()])
 def test_conflicting_terminals_fail_closed(self):
  c=pathlib.Path(self.l.claim(self.i,'a')['claim']);self.l.finish(self.i,[self.artifact()]);(c/'FAILED.json').write_text('{}')
  with self.assertRaisesRegex(ValueError,'CONFLICTING_TERMINALS'):self.l.claim(self.i,'b')
 def test_partial_record_fail_closed(self):
  c=self.l.location(self.i);c.mkdir();(c/'STARTED.json').write_text('{partial')
  with self.assertRaises(ValueError):self.l.claim(self.i,'new')
  self.assertEqual((c/'STARTED.json').read_text(),'{partial')
 def test_symlink_claim_rejected(self):
  c=self.l.location(self.i);outside=self.root.parent/'outside';outside.mkdir();c.symlink_to(outside,target_is_directory=True)
  with self.assertRaises(ValueError):self.l.claim(self.i,'new')
  self.assertEqual(list(outside.iterdir()),[])
 def test_process_lock(self):
  with self.l.lock():
   c=subprocess.run([sys.executable,'-c',"from ledger import Ledger;import sys;Ledger(sys.argv[1]).claim({'symbol':'FIXTURE','event_date':'20261106','input_sha256':'input','code_sha256':'code','checkpoint_sha256':'checkpoint'},'out')",str(self.root)],capture_output=True)
  self.assertNotEqual(c.returncode,0);self.assertIn(b'BlockingIOError',c.stderr)
 def test_process_death_preserves_claim(self):
  cmd="from ledger import Ledger;import sys,os,json;Ledger(sys.argv[1]).claim(json.loads(sys.argv[2]),'child/out');os._exit(7)"
  c=subprocess.run([sys.executable,'-c',cmd,str(self.root),json.dumps(self.i)]);self.assertEqual(c.returncode,7);self.assertEqual(self.l.claim(self.i,'recovery/out')['status'],'UNKNOWN_INSPECT_NO_RETRY')
 def test_unmarked_root_and_outside_artifact_reject(self):
  with self.assertRaises(FileNotFoundError):Ledger(self.root.parent)
  self.l.claim(self.i,'a')
  with self.assertRaises(ValueError):self.l.finish(self.i,[{'path':'../outside','bytes':0,'sha256':'x'}])
if __name__=='__main__':unittest.main(verbosity=2)
