import importlib.util,json,subprocess,sys,unittest
from pathlib import Path
from datetime import datetime,timedelta
import test_capture as fixtures
ROOT=fixtures.ROOT

class ResearchLaneTests(unittest.TestCase):
 def setUp(self):
  self.assertIsNotNone(importlib.util.find_spec('research_lane'),'ResearchLane adapter is missing')
  import research_lane
  self.m=research_lane
  self.fixture=fixtures.CaptureTests();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
  self.result=self.fixture.run_capture();self.binding=self.result['archive_binding'];self.day=self.fixture.day
 def test_latest_and_exact_only_archive_lane_preserve_original(self):
  first=self.m.research_lane(self.binding,{})
  exact=self.m.research_lane(self.binding,{'research_date':self.day})
  self.assertEqual(first['endpoint_mode'],'LATEST');self.assertEqual(exact['endpoint_mode'],'EXACT')
  self.assertEqual(exact['status'],'LIVE_PERIPHERAL_ONLY');self.assertEqual(exact['research_date'],self.day)
  self.assertEqual(first['archive_materials'],exact['archive_materials'])
  self.assertEqual(exact['archive_materials']['articles'][0]['body_text'],self.fixture.body)
  self.assertNotIn('morning_news',exact);self.assertNotIn('zsxq',exact)
  self.assertFalse(exact['production_allowed']);self.assertIn('M04_OTHER_LANES_NOT_CONFIGURED',exact['cannot_confirm'])
  self.assertEqual(exact['archive_materials']['source_reference']['archive_binding'],self.binding)
 def test_empty_latest_has_no_invented_date(self):
  root=self.fixture.root/'empty';root.mkdir();(root/'manifest.json').write_text('{}')
  binding={'root':str(root),'files':{'manifest.json':self.fixture.sha(root/'manifest.json')}}
  out=self.m.research_lane(binding,{})
  self.assertEqual(out['research_date'],'');self.assertEqual(out['status'],'NOT_MATERIALIZED')
  self.assertIsNone(out['archive_materials']);self.assertIsNone(out['source_run_id'])
 def test_exact_missing_never_falls_back(self):
  missing='20260101';r=self.m.research_lane(self.binding,{'research_date':missing})
  self.assertEqual(r['research_date'],missing);self.assertEqual(r['status'],'NOT_MATERIALIZED');self.assertIsNone(r['archive_materials']);self.assertIsNone(r['source_run_id'])
 def test_unknown_query_and_invalid_dates_rejected(self):
  for query in ({'research_date':None},{'date':self.day},{'research_date':'20260230'},{'research_date':[self.day]},{'research_date':self.day,'run':'x'}):
   with self.assertRaises(ValueError):self.m.research_lane(self.binding,query)
 def test_bad_selected_archive_rejected_and_read_has_no_writes(self):
  root=Path(self.binding['root']);before={str(p):p.read_bytes() for p in root.rglob('*') if p.is_file()}
  self.m.research_lane(self.binding,{})
  self.assertEqual(before,{str(p):p.read_bytes() for p in root.rglob('*') if p.is_file()})
  p=root/'manifest.json';p.write_bytes(p.read_bytes()+b' ')
  with self.assertRaises(ValueError):self.m.research_lane(self.binding,{})
 def legacy(self):
  f=self.fixture;built=json.loads(next((f.runtime/'ingest').glob('runs/*/builder.json')).read_bytes())
  root=f.root/'legacy';root.mkdir()
  code="""import sys,json
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from v5_shadow.archive_reader import _Loader,sources
sys.meta_path.insert(0,_Loader(sources()))
from infrastructure.research_store import ResearchArchiveStore
p=json.load(sys.stdin)
ResearchArchiveStore(Path(sys.argv[2])).publish(p,mode='REPLAY')
"""
  p=subprocess.run([sys.executable,'-I','-B','-c',code,str(ROOT/'source/V5/src'),str(root)],input=json.dumps(built['archive_v1']).encode(),capture_output=True)
  self.assertEqual(p.returncode,0,p.stderr)
  # Simulate a scoped migration: a whole original manifest, only the selected
  # original daily trio present. Out-of-scope misses are diagnostics, not success.
  manifest=json.loads((root/'manifest.json').read_bytes())
  for i in range(53):
   day=(datetime(2025,1,1)+timedelta(days=i)).strftime('%Y%m%d');manifest['research/archives/'+day+'.json']='a'*64
  (root/'manifest.json').write_text(json.dumps(manifest))
  names=['manifest.json',f'research/archives/{self.day}.json',f'receipts/research/archives/{self.day}.json']
  return {'root':str(root),'files':{name:f.sha(root/name) for name in names}}
 def test_original_v1_unknown_clocks_and_53_outside_errors_preserved(self):
  binding=self.legacy();out=self.m.research_lane(binding,{})
  self.assertEqual(out['research_date'],self.day)
  self.assertEqual(len(out['out_of_scope_record_errors']),53)
  self.assertEqual(out['archive_materials']['acquisition_status'],'UNKNOWN')
  self.assertIsNone(out['source_run_id']);self.assertIn('M04_SOURCE_RUN_UNKNOWN',out['cannot_confirm'])
  original=out['archive_materials']['articles'][0]
  self.assertNotIn('retrieved_at',original);self.assertNotIn('available_at',original)
  cards=self.fixture.m.materials(binding)
  self.assertEqual(len(cards['out_of_scope_record_errors']),53);self.assertEqual(cards['articles'][0]['acquisition_status'],'UNKNOWN')
if __name__=='__main__':unittest.main()
