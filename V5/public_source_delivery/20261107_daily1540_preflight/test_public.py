import unittest,tempfile,json,hashlib,subprocess
from pathlib import Path
from unittest.mock import patch
import preflight as p
class Tests(unittest.TestCase):
 def fixture(self,root,approved='{}'):
  files={'coordinator.py':'APPROVED = '+approved+'\n','dated.py':'# synthetic only\n'};refs=[]
  for name,text in files.items():
   raw=text.encode();(root/name).write_bytes(raw);refs.append({'path':name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
  raw=json.dumps(refs).encode();(root/'pins.json').write_bytes(raw)
  return dict(ROOT=root,PINS_FILE='pins.json',PINS_SHA=hashlib.sha256(raw).hexdigest(),COORDINATOR='coordinator.py',DATED_PREFLIGHT='dated.py')
 def test_default_refused(self):
  with self.assertRaisesRegex(ValueError,'NO_APPROVED'):p.inspect('20000101')
 def test_explicit_date_required(self):
  for date in [None,'','200001',12345678]:
   with self.assertRaises(ValueError):p.inspect(date)
 def test_synthetic_reuse_never_dispatches(self):
  with tempfile.TemporaryDirectory() as t,patch.object(p.subprocess,'run',return_value=subprocess.CompletedProcess([],0,json.dumps({'result':{'status':'REUSE_COMPLETED_DATE_NO_COMPUTE'}}),'')) as run:
   with patch.multiple(p,**self.fixture(Path(t))):r=p.inspect('20000101')
   self.assertEqual(run.call_count,1);self.assertEqual(r['status'],'REUSE_COMPLETED_NO_DISPATCH');self.assertIs(r['execution_permitted'],False);self.assertFalse(r['natural_run_verified']);self.assertEqual(r['live_command_whitelist_entries'],0)
 def test_nonempty_approved_rejected_before_subprocess(self):
  with tempfile.TemporaryDirectory() as t,patch.object(p.subprocess,'run') as run:
   with patch.multiple(p,**self.fixture(Path(t),"{'x':'not allowed'}")):
    with self.assertRaisesRegex(ValueError,'LIVE_DISPATCH_CHANGED'):p.inspect('20000101')
   run.assert_not_called()
 def test_tampered_source_rejected(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);b=self.fixture(root);(root/'dated.py').write_text('changed')
   with patch.multiple(p,**b):
    with self.assertRaisesRegex(ValueError,'STAGE_SOURCE_DRIFT'):p.inspect('20000101')
 def test_partial_binding_and_unpinned_executable(self):
  with tempfile.TemporaryDirectory() as t:
   b=self.fixture(Path(t))
   for override in [dict(DATED_PREFLIGHT=None),dict(COORDINATOR='not_pinned.py')]:
    with patch.multiple(p,**dict(b,**override)):
     with self.assertRaises(ValueError):p.verify()
 def test_new_date_stays_blocked(self):
  with tempfile.TemporaryDirectory() as t,patch.object(p.subprocess,'run',return_value=subprocess.CompletedProcess([],0,json.dumps({'result':{'status':'UNKNOWN'}}),'')):
   with patch.multiple(p,**self.fixture(Path(t))):r=p.inspect('20000102')
   self.assertEqual(r['status'],'BLOCKED_NO_DATED_EXECUTION_ADMISSION');self.assertIs(r['execution_permitted'],False)
if __name__=='__main__':unittest.main()
