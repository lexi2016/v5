import importlib.util,json,sys,unittest,tempfile,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bridge'))
try: import research_workbench_readonly as bridge
except ImportError: bridge=None
class BridgeTests(unittest.TestCase):
 def test_missing_source_is_explicit_not_ready(self):
  self.assertIsNotNone(bridge,'read-only bridge not implemented')
  status,payload=bridge.response({},'/api/v5/research/lane',{'research_date':'20261012'})
  self.assertEqual(status,200);self.assertEqual(payload['status'],'NOT_MATERIALIZED');self.assertEqual(payload['research_date'],'20261012')
  self.assertIs(payload['production_allowed'],False)
 def test_no_wechat_index_is_explicit(self):
  self.assertIsNotNone(bridge,'read-only bridge not implemented')
  status,payload=bridge.response({},'/api/v5/research/wechat/materials',{'date':'20261012','date_basis':'article','q':'','limit':'20'})
  self.assertEqual(payload['status'],'NOT_CONFIGURED');self.assertEqual(payload['query']['date'],'20261012')
 def test_query_guard(self):
  self.assertIsNotNone(bridge,'read-only bridge not implemented')
  for query in [{'date':'20261012'},{'research_date':'20260230'},{'research_date':'20261012','run':'x'}]:
   with self.assertRaises(ValueError):bridge.response({},'/api/v5/research/lane',query)
 def test_unsafe_adapter_payload_rejected(self):
  self.assertIsNotNone(bridge,'read-only bridge not implemented')
  with self.assertRaises(ValueError):bridge.validate_payload({'production_allowed':True},{})
 def test_modified_launch_never_executes_before_source_validation(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'launch.py').write_text("raise RuntimeError('must not execute')")
   manifest=json.dumps({'files':{'launch.py':'a'*64,'research_lane.py':'b'*64,'capture_runtime.py':'c'*64}}).encode();(root/'RELEASE.json').write_bytes(manifest)
   b=dict(package_root=str(root),package_manifest_sha256=hashlib.sha256(manifest).hexdigest(),archive_binding={'root':str(root),'files':{}},python_executable=str(Path(sys.executable).resolve()))
   config={'module_id':'source_bundle','routes':[bridge.LANE],bridge.KEY:b}
   with self.assertRaisesRegex(ValueError,'RESEARCH_PACKAGE_BYTES'):bridge.response(config,bridge.LANE,{})
 def test_unpinned_bytecode_is_rejected_before_launch(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);files={}
   for name in ['launch.py','research_lane.py','capture_runtime.py']:
    (root/name).write_text('# immutable source\n');files[name]=hashlib.sha256((root/name).read_bytes()).hexdigest()
   (root/'__pycache__').mkdir();(root/'__pycache__/capture_runtime.cpython-314.pyc').write_bytes(b'unpinned')
   manifest=json.dumps({'files':files}).encode();(root/'RELEASE.json').write_bytes(manifest)
   b=dict(package_root=str(root),package_manifest_sha256=hashlib.sha256(manifest).hexdigest(),archive_binding={'root':str(root),'files':{}},python_executable=str(Path(sys.executable).resolve()))
   with self.assertRaisesRegex(ValueError,'RESEARCH_PACKAGE_UNPINNED_CODE'):bridge.response({'module_id':'source_bundle','routes':[bridge.LANE],bridge.KEY:b},bridge.LANE,{})
if __name__=='__main__':unittest.main()
