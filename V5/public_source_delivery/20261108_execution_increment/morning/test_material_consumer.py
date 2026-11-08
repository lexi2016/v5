import unittest,json,pathlib,os,types,hashlib,copy,tempfile
import registered as m
class Consumer(unittest.TestCase):
 def setUp(self):
  raw=pathlib.Path(os.environ['USER_INGESTION_SOURCE']).read_bytes()
  self.assertEqual(hashlib.sha256(raw).hexdigest(),'4d8f360a6f0f388079ad218c2039bd5d7679447b9807601e2bc204dd3ceab05d')
  producer=types.ModuleType('original_user_ingestion');exec(compile(raw,'user_ingestion','exec'),producer.__dict__)
  mapping={'announcements':'announcements','essential_news':'news','preopen_memo':'notes','preopen_analysis':'notes'}
  self.policy={'schema':'USER_RESULT_INGESTION_POLICY_V1','version':'v1','cutoff':'2026-11-09T08:00:00+08:00','column_map':mapping,'expected_parent_identity':None}
  row={'symbol':'000001.SZ','category':'announcements','status':'AVAILABLE','event_at':'2026-11-09T07:00:00+08:00','observed_at':'2026-11-09T07:01:00+08:00','available_at':'2026-11-09T08:01:00+08:00','details':{'source_url':'https://example.invalid/fixture','title':'SYNTHETIC','body_reference':'fixture','facts':'LATE_SECRET_SENTINEL','inferences':'UNKNOWN','counterevidence':'UNKNOWN'}}
  self.doc={'schema':'USER_RESEARCH_RETURN_V1','target_date':'20261109','list_sha256':'a'*64,'version':'v1','records':[row]}
  self.producer=producer;self.symbols=[f'{i:06d}.SZ' for i in range(1,201)];self.manifest=self.make()
  self.reg={'node':'morning-delivery','business_date':'20261109','domain':'synthetic','cutoff':'2026-11-09T08:10:00+08:00'}
  self.assembly={'assembly_schema':'MORNING_0810_PREVIEW_V1','section_max_age_seconds':{k:3600 for k in ('freeze','morning-materials','jk-verify')}}
 def make(self,parent=None):return self.producer.ingest_user_results('20261109','a'*64,self.symbols,self.policy,self.doc,parent)
 def runone(self):
  envelope={'business_date':'20261109','source_date':'20261109','observed_at':'2026-11-09T08:02:00+08:00','available_at':'2026-11-09T08:03:00+08:00','status':self.manifest['status'],'content':self.manifest,'source_reference':'SYNTHETIC_USER_RETURN'}
  return m.calculate(self.reg,self.assembly,{'assembly_sections':{'morning-materials':envelope}},None)
 def resign(self):self.manifest['identity']=m.sha(m.canonical({k:v for k,v in self.manifest.items() if k!='identity'}))
 def test_real_producer_late_not_in_consumer_content(self):
  original=copy.deepcopy(self.manifest);out=self.runone();content=out['sections'][1]['content']
  self.assertEqual(content['schema'],'MORNING_USER_MATERIAL_PROJECTION_V1');self.assertNotIn('LATE_SECRET_SENTINEL',json.dumps(out));self.assertEqual(content['late_count'],1);self.assertEqual(content['source_manifest_identity'],original['identity']);self.assertEqual(self.manifest,original);self.assertFalse(out['business_accepted']);self.assertEqual(content['scope_count'],200)
 def test_tampered_identity_rejected(self):
  self.manifest['version']='evil'
  with self.assertRaisesRegex(ValueError,'IDENTITY'):self.runone()
 def test_late_content_in_effective_cell_rejected(self):
  self.manifest['records'][0]['columns']['announcements'][0]['details']={'facts':'leak'};self.resign()
  with self.assertRaisesRegex(ValueError,'LATE_ISOLATION'):self.runone()
 def test_missing_late_index_rejected(self):
  self.manifest['late_records']=[];self.resign()
  with self.assertRaisesRegex(ValueError,'LATE_INDEX'):self.runone()
 def test_scope_and_state_not_promoted(self):
  self.manifest['business_accepted']=True;self.resign()
  with self.assertRaisesRegex(ValueError,'UNVERIFIED_STATE'):self.runone()
 def test_parent_version_becomes_available_only_at_later_cutoff(self):
  old=copy.deepcopy(self.manifest);self.policy.update(version='v2',cutoff='2026-11-09T08:02:00+08:00',expected_parent_identity=old['identity']);self.doc['version']='v2';self.manifest=self.make(old);out=self.runone()['sections'][1]['content'];self.assertEqual(out['late_count'],0);self.assertEqual(out['parent_identity'],old['identity']);self.assertIn('LATE_SECRET_SENTINEL',json.dumps(out));self.assertEqual(old['late_records'][0]['details']['facts'],'LATE_SECRET_SENTINEL')
 def test_future_producer_cutoff_rejected(self):
  self.manifest['cutoff']='2026-11-09T08:04:00+08:00';self.resign()
  with self.assertRaisesRegex(ValueError,'CUTOFF_ORDER'):self.runone()
 def test_projected_handoff_original_freeze_readback(self):
  result=self.runone();safe=m.module('safeio')
  with tempfile.TemporaryDirectory() as folder:
   first=safe.freeze(folder,result);again=safe.freeze(folder,result)
   self.assertEqual(first['byte_readback'],'PASS');self.assertTrue(again['reused'])
   for path in pathlib.Path(folder).rglob('*'):
    if path.is_file():self.assertNotIn(b'LATE_SECRET_SENTINEL',path.read_bytes())
