import unittest,tempfile,pathlib,hashlib,os,fcntl,json,multiprocessing
from unittest.mock import patch
import owner_candidate as owner
class Tests(unittest.TestCase):
 def test_loader_executes_checked_bytes(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'m.py';raw=b'VALUE=1\n';p.write_bytes(raw)
   original=pathlib.Path.read_bytes
   def read(q):
    result=original(q)
    if q==p:q.write_text('VALUE=2\n')
    return result
   with patch.object(pathlib.Path,'read_bytes',read):m=owner.load(p,'race_sample',hashlib.sha256(raw).hexdigest())
   self.assertEqual(m.VALUE,1)
 def test_output_cannot_choose_lock_root(self):
  self.assertTrue(hasattr(owner,'COORDINATION_ROOT'))
 def test_terminal_protocol_is_atomic(self):
  self.assertTrue(hasattr(owner,'seal_terminal'))

class ProtocolTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.base=pathlib.Path(self.tmp.name)
  self.root=self.base/'coord';self.swap=patch.object(owner,'COORDINATION_ROOT',self.root);self.swap.start()
  self.wire=self.base/'in.gz';import gzip
  self.wire.write_bytes(gzip.compress(json.dumps({'symbol':'FAKE','actual_last_date':'20261106'}).encode()))
 def tearDown(self):self.swap.stop();self.tmp.cleanup()
 def test_arbitrary_output_rejected(self):
  with self.assertRaisesRegex(ValueError,'OUTPUT_OUTSIDE'):owner.run(None,None,None,self.wire,self.base/'elsewhere')
 def test_same_task_cannot_change_output(self):
  with patch.object(owner,'_run_locked',return_value={'simulated':True}) as run:
   owner.run(None,None,None,self.wire,self.root/'runs'/'a')
   with self.assertRaisesRegex(ValueError,'EXISTING_TASK'):owner.run(None,None,None,self.wire,self.root/'runs'/'b')
   self.assertEqual(run.call_count,1)
 def test_unknown_claim_survives_failure(self):
  with patch.object(owner,'_run_locked',side_effect=RuntimeError('simulated crash')):
   with self.assertRaises(RuntimeError):owner.run(None,None,None,self.wire,self.root/'runs'/'a')
  with self.assertRaisesRegex(ValueError,'EXISTING_TASK'):owner.run(None,None,None,self.wire,self.root/'runs'/'b')
 def test_lock_held_while_inner_runs(self):
  def body(*args):
   fd=os.open(self.root/'OWNER.lock',os.O_RDWR)
   try:
    with self.assertRaises(BlockingIOError):fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
   finally:os.close(fd)
   return {'fixture':True}
  with patch.object(owner,'_run_locked',side_effect=body):owner.run(None,None,None,self.wire,self.root/'runs'/'a')
 def test_atomic_failure_leaves_no_terminal(self):
  p=self.base/'RESULT.json';fd=os.open(self.base/'lock',os.O_CREAT|os.O_RDWR,0o600)
  try:
   with patch.object(os,'link',side_effect=OSError('fault')):
    with self.assertRaises(OSError):owner.seal_terminal(p,{'status':'fixture'},fd)
   self.assertFalse(p.exists());self.assertTrue(p.with_name('RESULT.json.pending').exists())
  finally:os.close(fd)
 def test_no_overwrite_terminal(self):
  p=self.base/'RESULT.json';fd=os.open(self.base/'lock',os.O_CREAT|os.O_RDWR,0o600)
  try:
   owner.seal_terminal(p,{'v':1},fd)
   with self.assertRaises(FileExistsError):owner.seal_terminal(p,{'v':2},fd)
   self.assertEqual(json.loads(p.read_text()),{'v':1})
  finally:os.close(fd)
 def test_symlink_output_rejected(self):
  self.root.mkdir();(self.root/'runs').symlink_to(self.base,target_is_directory=True)
  with self.assertRaisesRegex(ValueError,'SYMLINK'):owner.run(None,None,None,self.wire,self.root/'runs'/'a')

 def test_symlink_claims_rejected(self):
  self.root.mkdir();(self.root/'claims').symlink_to(self.base,target_is_directory=True)
  with self.assertRaisesRegex(ValueError,'SYMLINK'):owner.run(None,None,None,self.wire,self.root/'runs'/'a')

if __name__=='__main__':unittest.main()
