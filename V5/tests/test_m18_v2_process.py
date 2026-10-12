"""Synthetic resource acceptance in fresh processes; fixed production budgets."""
import importlib.util,json,os,tempfile,unittest
from pathlib import Path
from test_m18_offline_pages import fixture,digest
from v5_shadow import m18_offline_v2 as m
if importlib.util.find_spec('v5_shadow.m18_offline_v2_process'):
 from v5_shadow import m18_offline_v2_process as proc
else:proc=None

class ProcessTests(unittest.TestCase):
 def setUp(self):self.assertIsNotNone(proc,'M18_V2_SUPERVISOR_MISSING')
 def test_build_then_fresh_reader_large_synthetic(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td)
   # About 30MB, >1.1M lexical nodes, one indexed nested field. No source data.
   raw,saved,identity=fixture(extra={'dense':{'rows':[{'a':i,'b':'S'*110} for i in range(220000)]}})
   (root/'response').write_bytes(raw);(root/'saved').write_bytes(saved)
   request=dict(action='build',response_path=str(root/'response'),saved_path=str(root/'saved'),output_root=str(root/'bundle'),identity=identity,profile_sha256=m.PROFILE_SHA256)
   del raw,saved
   built=proc.run(request);self.assertEqual(built['status'],'OK',built)
   read=proc.run(dict(action='read',bundle_root=str(root/'bundle'),manifest_sha256=built['manifest_sha256'],output_root=str(root/'read'),identity=identity,profile_sha256=m.PROFILE_SHA256))
   self.assertEqual(read['status'],'OK',read);self.assertNotEqual(built['pid'],read['pid'])
   self.assertEqual(digest((root/'read/reassembled.json').read_bytes()),identity['response_sha256'])
   self.assertGreater(read['counts']['response_nodes'],1000000)
   self.assertEqual(read['gaps'],3250)
   for phase in [built,read]:m.enforce_usage(phase['usage'])
   self.assertTrue((root/'bundle/ACCEPTED.json').is_file());self.assertTrue((root/'read/ACCEPTED.json').is_file())
   if os.environ.get('M18_RESOURCE_EVIDENCE'):
    Path(os.environ['M18_RESOURCE_EVIDENCE']).write_text(json.dumps(dict(build=built,read=read),indent=2)+'\n')
 def test_rejected_source_has_no_accepted_generation(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);raw,saved,identity=fixture(extra={'deep':'x'*(32*1024*1024)})
   (root/'response').write_bytes(raw);(root/'saved').write_bytes(saved);del raw,saved
   result=proc.run(dict(action='build',response_path=str(root/'response'),saved_path=str(root/'saved'),output_root=str(root/'out'),identity=identity,profile_sha256=m.PROFILE_SHA256))
   self.assertEqual(result['status'],'REJECTED');self.assertEqual(result['error'],'M18_V2_STRING_TOKEN')
   self.assertFalse((root/'out/ACCEPTED.json').exists())
 def test_unknown_action_and_profile_fail_closed(self):
  for request in [dict(action='shell'),dict(action='build',profile_sha256='f'*64)]:
   with self.subTest(request=request):self.assertEqual(proc.run(request)['status'],'REJECTED')
 def test_real_generation_byte_overflow_rejected(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);raw,saved,identity=fixture(extra={'a_body':'x'*(24*1024*1024),'b_body':'y'*(24*1024*1024)})
   (root/'response').write_bytes(raw);(root/'saved').write_bytes(saved);del raw,saved
   result=proc.run(dict(action='build',response_path=str(root/'response'),saved_path=str(root/'saved'),output_root=str(root/'out'),identity=identity,profile_sha256=m.PROFILE_SHA256))
   self.assertEqual(result['status'],'REJECTED',result);self.assertEqual(result['error'],'M18_V2_STORED_BYTES',result)
   self.assertFalse((root/'out/ACCEPTED.json').exists())
