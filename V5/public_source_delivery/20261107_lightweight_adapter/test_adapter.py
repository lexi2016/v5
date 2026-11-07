import unittest,tempfile,hashlib
from pathlib import Path
from unittest.mock import patch
import preview_adapter as a
class Tests(unittest.TestCase):
 def fixture(self,root):
  names=['serve_workbench.py','catalog_api.py','node_results_api.py','local/public/research-system/index.html','local/public/research-system/timeline-view.mjs','local/public/research-system/shared-par-store.mjs','local/public/research-system/workbench.css','local/public/research-system/timeline.css']
  pins={}
  for name in names:
   p=root/name;p.parent.mkdir(parents=True,exist_ok=True);raw=b'# synthetic fixture only';p.write_bytes(raw);pins[name]={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
  return dict(root=str(root),business_date='20000101',selection_version='SYNTHETIC',catalog_version='SYNTHETIC',pins=pins)
 def test_default_refusal(self):
  with self.assertRaisesRegex(ValueError,'NO_APPROVED'):a.prepare(None)
 def test_complete_synthetic_pin_validation(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);self.assertEqual(a.verify_binding(self.fixture(root)),root)
 def test_missing_identity_refuses(self):
  with tempfile.TemporaryDirectory() as d:
   b=self.fixture(Path(d))
   for field in ['root','business_date','selection_version','catalog_version','pins']:
    changed=dict(b);changed[field]=None
    with self.assertRaisesRegex(ValueError,'INCOMPLETE'):a.verify_binding(changed)
 def test_changed_source_refuses(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);b=self.fixture(root);(root/'catalog_api.py').write_text('changed')
   with self.assertRaisesRegex(ValueError,'SOURCE_PIN_CHANGED'):a.verify_binding(b)
 def test_unpinned_and_symlink_refuse(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);b=self.fixture(root);extra=root/'unbound.py';extra.write_text('x')
   with self.assertRaisesRegex(ValueError,'UNPINNED'):a.verify_binding(b)
   extra.unlink();extra.symlink_to(root/'catalog_api.py')
   with self.assertRaisesRegex(ValueError,'SYMLINK'):a.verify_binding(b)
 def test_host_origin_identity(self):
  self.assertTrue(a.identity_allowed('localhost:8779','http://127.0.0.1:8779',8779))
  for host,origin in [('evil.test:8779',None),('localhost:8779','https://evil.test'),('localhost:80',None)]:self.assertFalse(a.identity_allowed(host,origin,8779))
 def test_resource_floor(self):
  original=Path.read_text
  def read(p,*args,**kwargs):
   if str(p)=='/proc/meminfo':return 'MemAvailable: 1 kB\n'
   return original(p,*args,**kwargs)
  with patch.object(Path,'read_text',read):
   with self.assertRaisesRegex(ValueError,'RESOURCE_MEMORY_HEADROOM'):a.resource_check(Path.cwd())
 def test_existing_dependency_identity_refuses(self):
  with tempfile.TemporaryDirectory() as d:
   b=self.fixture(Path(d))
   with patch.dict(a.sys.modules,{'catalog_api':object()}):
    with self.assertRaisesRegex(ValueError,'DEPENDENCY_ALREADY_LOADED'):a.prepare(b)
if __name__=='__main__':unittest.main()
