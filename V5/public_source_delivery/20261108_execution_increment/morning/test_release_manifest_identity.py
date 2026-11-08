import pathlib,json,hashlib,unittest,os,re
class ReleaseIdentity(unittest.TestCase):
 def test_morning_identity(self):
  root=pathlib.Path(os.environ.get('MORNING_RELEASE_ROOT',str(pathlib.Path(__file__).resolve().parents[1])))
  manifest=json.loads((root/'MANIFEST.json').read_text());provenance=json.loads((root/'PROVENANCE.json').read_text())
  for obj in (manifest,provenance):
   refs=[v for v in obj['files'] if v['path']=='morning/registered.py'];self.assertEqual(len(refs),1)
   ref=refs[0];raw=(root/ref['path']).read_bytes();self.assertEqual(ref['bytes'],len(raw));self.assertEqual(ref['sha256'],hashlib.sha256(raw).hexdigest())
  ref=next(v for v in manifest['files'] if v['path']=='PROVENANCE.json');raw=(root/'PROVENANCE.json').read_bytes();self.assertEqual(ref['bytes'],len(raw));self.assertEqual(ref['sha256'],hashlib.sha256(raw).hexdigest())
 def test_actual_call_dependencies(self):
  root=pathlib.Path(os.environ.get('MORNING_RELEASE_ROOT',str(pathlib.Path(__file__).resolve().parents[1])))
  entry=(root/'morning/registered.py').read_text();raw=(root/'morning/code_bindings.json').read_bytes()
  self.assertEqual(hashlib.sha256(raw).hexdigest(),re.search("CODE_BINDINGS_SHA='([^']+)'",entry).group(1))
  for ref in json.loads(raw).values():
   self.assertEqual(hashlib.sha256((root.parent/ref['path']).read_bytes()).hexdigest(),ref['sha256'])
if __name__=='__main__':unittest.main()
