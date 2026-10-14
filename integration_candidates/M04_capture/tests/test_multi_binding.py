import hashlib,importlib.util,json,subprocess,sys,unittest
from pathlib import Path
import test_capture as fixtures
import research_lane

class MultiBindingTests(unittest.TestCase):
 def setUp(self):
  c=fixtures.CaptureTests();c.setUp();self.addCleanup(c.doCleanups);self.c=c
  self.new=c.run_capture()['archive_binding'];self.old=self.historical('20200102','older')
  self.bundle={'schema_version':'v5.m04_archive_bindings.v1','bindings':[self.new,self.old]}
 def historical(self,day,name):
  c=self.c;built=json.loads(next((c.runtime/'ingest/runs').glob('*/builder.json')).read_bytes())
  # Synthetic original-v1 store publication, not a fake reader dictionary.
  source=json.dumps(built['archive_v1'],ensure_ascii=False).replace(c.day,day).replace(c.day[:4]+'-'+c.day[4:6]+'-'+c.day[6:],day[:4]+'-'+day[4:6]+'-'+day[6:])
  root=c.root/name;root.mkdir()
  code="""import sys,json
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from v5_shadow.archive_reader import _Loader,sources
sys.meta_path.insert(0,_Loader(sources()))
from infrastructure.research_store import ResearchArchiveStore
ResearchArchiveStore(Path(sys.argv[2])).publish(json.load(sys.stdin),mode='REPLAY')
"""
  p=subprocess.run([sys.executable,'-I','-B','-c',code,str(fixtures.ROOT/'source/V5/src'),str(root)],input=source.encode(),capture_output=True)
  self.assertEqual(p.returncode,0,p.stdout+p.stderr)
  files={str(p.relative_to(root)):self.c.sha(p) for p in root.rglob('*') if p.is_file() and (str(p.relative_to(root))=='manifest.json' or str(p.relative_to(root)).endswith(day+'.json'))}
  return {'root':str(root),'files':files}
 def test_exact_old_new_latest_and_no_writes(self):
  before={str(p):p.read_bytes() for b in self.bundle['bindings'] for p in Path(b['root']).rglob('*') if p.is_file()}
  old=research_lane.research_lane(self.bundle,{'research_date':'20200102'});new=research_lane.research_lane(self.bundle,{'research_date':self.c.day})
  self.assertEqual(old['archive_materials']['source_reference']['archive_binding'],self.old)
  self.assertEqual(new['archive_materials']['source_reference']['archive_binding'],self.new)
  self.assertEqual(old['archive_materials']['acquisition_status'],'UNKNOWN')
  latest=research_lane.research_lane(self.bundle,{});self.assertEqual(latest['research_date'],self.c.day)
  reverse={**self.bundle,'bindings':list(reversed(self.bundle['bindings']))}
  self.assertEqual(research_lane.research_lane(reverse,{})['archive_materials'],latest['archive_materials'])
  self.assertEqual(research_lane.research_lane(self.bundle,{'research_date':'19990101'})['status'],'NOT_MATERIALIZED')
  self.assertEqual(before,{str(p):p.read_bytes() for b in self.bundle['bindings'] for p in Path(b['root']).rglob('*') if p.is_file()})
 def test_duplicate_root_unknown_fields_and_empty_rejected(self):
  for b in ({'schema_version':'v5.m04_archive_bindings.v1','bindings':[]},{**self.bundle,'other':1},{**self.bundle,'bindings':[self.new,self.new]}):
   with self.subTest(binding=b),self.assertRaises(ValueError):research_lane.research_lane(b,{})
 def test_same_day_independent_roots_rejected(self):
  other=self.historical('20200102','collision')
  with self.assertRaisesRegex(ValueError,'DATE_CONFLICT'):research_lane.research_lane({**self.bundle,'bindings':[self.old,other]}, {})
 def test_unselected_root_tamper_also_rejected(self):
  p=Path(self.old['root'])/'manifest.json';p.write_bytes(p.read_bytes()+b' ')
  with self.assertRaises(ValueError):research_lane.research_lane(self.bundle,{'research_date':self.c.day})
 def test_candidate_bridge_strict_shape_and_original_passthrough(self):
  path=fixtures.ROOT/'page_bridge/research_workbench_readonly.py'
  spec=importlib.util.spec_from_file_location('multi_binding_bridge',path);bridge=importlib.util.module_from_spec(spec);spec.loader.exec_module(bridge)
  config={'module_id':'source_bundle','routes':[bridge.LANE],bridge.KEY:{'package_root':str(fixtures.ROOT),'package_manifest_sha256':self.c.sha(fixtures.ROOT/'RELEASE.json'),'archive_binding':self.bundle,'python_executable':str(Path(sys.executable).resolve())}}
  bridge.validate_binding(config)
  self.assertEqual(bridge._lane(config,{'research_date':'20200102'})['archive_materials']['source_reference']['archive_binding'],self.old)
  bad={**config,bridge.KEY:{**config[bridge.KEY],'archive_binding':{**self.bundle,'bindings':[self.new,self.new]}}}
  with self.assertRaisesRegex(ValueError,'DUPLICATE_ROOT'):bridge.validate_binding(bad)
 def test_config_preparation_preserves_other_bindings_and_requires_pin(self):
  path=fixtures.ROOT/'page_bridge/prepare_binding.py';spec=importlib.util.spec_from_file_location('prepare_multi_binding',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  config={'module_id':'source_bundle','release_id':'KEEP','data_root':'KEEP_ROOT','routes':['/existing'],'m14_binding':{'unchanged':True}}
  digest=self.c.sha(fixtures.ROOT/'RELEASE.json')
  out=module.prepare(config,str(fixtures.ROOT),sys.executable,self.bundle,digest)
  for key in ('release_id','data_root','m14_binding'):self.assertEqual(out[key],config[key])
  self.assertEqual(config['routes'],['/existing']);self.assertEqual(out['m04_research_lane_binding']['archive_binding'],self.bundle)
  with self.assertRaisesRegex(ValueError,'PACKAGE_PIN'):module.prepare(config,str(fixtures.ROOT),sys.executable,self.bundle,'0'*64)
