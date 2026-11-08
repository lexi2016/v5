import hashlib,pathlib,tempfile,types,unittest
import replay as m
class LoaderReview(unittest.TestCase):
 def make(self,root,raw):
  rel='V5/src/v5_shadow/demo.py';p=root/rel;p.parent.mkdir(parents=True);p.write_bytes(raw)
  return p,{'path':rel,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
 def test_executes_verified_snapshot_not_reopened_path(self):
  with tempfile.TemporaryDirectory() as t:
   root=pathlib.Path(t);p,ref=self.make(root,b'VALUE=1\n');loader=m.FrozenV5(root,[ref]);p.write_bytes(b'VALUE=2\n');mod=types.ModuleType('v5_shadow.demo');loader.exec_module(mod);self.assertEqual(mod.VALUE,1)
 def test_code_change_and_unpinned_import_fail(self):
  with tempfile.TemporaryDirectory() as t:
   root=pathlib.Path(t);p,ref=self.make(root,b'VALUE=1\n');loader=m.FrozenV5(root,[ref])
   with self.assertRaisesRegex(ImportError,'UNPINNED'):loader.find_spec('v5_shadow.bad')
   p.write_bytes(b'VALUE=2\n')
   with self.assertRaisesRegex(ValueError,'CODE_PIN'):m.FrozenV5(root,[ref])
 def test_path_escape_and_duplicate_ref_fail(self):
  with tempfile.TemporaryDirectory() as t:
   root=pathlib.Path(t);p,ref=self.make(root,b'VALUE=1\n')
   with self.assertRaisesRegex(ValueError,'DUPLICATE_CODE'):m.FrozenV5(root,[ref,ref])
   ref['path']='V5/src/v5_shadow/../../bad.py'
   with self.assertRaisesRegex(ValueError,'CODE_PATH'):m.FrozenV5(root,[ref])
 def test_request_shape_and_size(self):
  for raw in (b'{}',b'{"stage_id":"STAGE_0925","stage_id":"STAGE_0925"}',b' '*(m.MAX_REQUEST+1)):
   with self.assertRaises(ValueError):m.replay('/unused',raw)
if __name__=='__main__':unittest.main()
