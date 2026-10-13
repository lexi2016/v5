import contextlib,hashlib,importlib.util,io,json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

class CaptureTests(unittest.TestCase):
 def setUp(self):
  self.assertIsNotNone(importlib.util.find_spec('capture_runtime'),'independent capture runtime is missing')
  import capture_runtime as m
  self.m=m
  from unittest.mock import patch
  original_datetime=datetime
  class TestWindowClock(datetime):
   @classmethod
   def now(cls,tz=None):return original_datetime.now(tz).replace(hour=23,minute=0)
  clock_patch=patch.object(m,'datetime',TestWindowClock);clock_patch.start();self.addCleanup(clock_patch.stop)
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
  self.runtime=self.root/'runtime';self.runtime.mkdir()
  self.panel=self.root/'selector.parquet';self.panel.write_bytes(b'synthetic selector; dependency acceptance NOT_RUN')
  self.body='合成科技（000001）与 NASDAQ:AVGO 签署光模块供货协议并交付光互连设备。'+'此处为独立测试合成正文，没有真实业务含义。'*20
  now=datetime.now(ZoneInfo('Asia/Shanghai'));self.day=now.strftime('%Y%m%d')
  self.published=(now.replace(hour=0,minute=0,second=0,microsecond=0)-timedelta(hours=1)).isoformat()
  response={'topics':[{'topic_id':'12345678901234567','create_time':self.published,'content':self.body}],'has_more':False}
  self.cli=self.root/'synthetic-cli';self.cli.write_text('#!'+sys.executable+'\nimport json\nprint('+repr(json.dumps(response,ensure_ascii=False))+')\n');self.cli.chmod(0o700)
  self.config={'schema_version':'v5.m04_capture_config.v1','runtime_root':str(self.runtime),'cli':{'path':str(self.cli),'sha256':self.sha(self.cli)},'selector_panel':{'path':str(self.panel),'sha256':self.sha(self.panel)},'groups':[['123','synthetic']],'page_limit':30,'max_pages':1,'lookback_days':4}
  self.m.initialize(self.config)
 def sha(self,p):return hashlib.sha256(p.read_bytes()).hexdigest()
 def run_capture(self):return self.m.capture(self.config,self.day,'0900','case1')
 def test_capture_real_owner_default_analyzer_import_and_cold_reference(self):
  result=self.run_capture();self.assertEqual(result['status'],'SUCCEEDED');self.assertGreater(result['article_count'],0)
  product=self.m.materials(result['archive_binding']);a=product['articles'][0]
  self.assertEqual(a['body_text'],self.body);self.assertEqual(a['published_at'],self.published)
  self.assertTrue(a['retrieved_at']);self.assertTrue(a['available_at']);self.assertEqual(a['acquisition_status'],'RECORDED')
  self.assertFalse(product['historical_pit_claimed']);self.assertEqual(product['archive_binding'],result['archive_binding'])
  self.assertIn(a['archive_file'],result['archive_binding']['files']);self.assertEqual(a['archive_sha256'],result['archive_binding']['files'][a['archive_file']])
  p=subprocess.run([sys.executable,'-B',str(ROOT/'launch.py'),'read'],input=json.dumps(result['archive_binding']).encode(),capture_output=True)
  self.assertEqual(p.returncode,0,p.stdout+p.stderr);self.assertEqual(json.loads(p.stdout)['articles'],product['articles'])
 def test_repeated_capture_and_resume_never_refetch(self):
  result=self.run_capture();self.cli.write_text('broken');before=(self.runtime/'captures/case1/status.json').read_bytes()
  self.assertEqual(self.m.resume(self.config,'case1'),result)
  self.assertEqual((self.runtime/'captures/case1/status.json').read_bytes(),before)
 def test_bad_cli_pin_rejected_before_any_capture(self):
  self.cli.write_text('broken')
  with self.assertRaisesRegex(ValueError,'INPUT_SHA'):self.run_capture()
  self.assertEqual(list((self.runtime/'captures').iterdir()),[])
 def test_config_unknown_field_and_overlap_rejected(self):
  with self.assertRaisesRegex(ValueError,'CONFIG_FIELDS'):self.m.validate({**self.config,'token':'forbidden'})
  c=dict(self.config);c['selector_panel']=dict(path=str(self.runtime/'selector'),sha256='0'*64)
  with self.assertRaisesRegex(ValueError,'INPUT_IN_RUNTIME'):self.m.validate(c)
 def test_failed_capture_is_not_blindly_refetched(self):
  self.cli.write_text('#!'+sys.executable+'\nraise SystemExit(3)\n');self.cli.chmod(0o700);self.config['cli']['sha256']=self.sha(self.cli)
  with self.assertRaises(Exception):self.run_capture()
  with self.assertRaisesRegex(ValueError,'CAPTURE_INCOMPLETE'):self.m.resume(self.config,'case1')
  with self.assertRaisesRegex(ValueError,'CAPTURE_INCOMPLETE'):self.run_capture()
 def test_status_saved_response_lost_recovers_without_cli(self):
  original=self.m._checkpoint
  def fail(path,data):
   if path.name=='request.json':raise OSError('synthetic response loss')
   return original(path,data)
  from unittest.mock import patch
  with patch.object(self.m,'_checkpoint',side_effect=fail):
   with self.assertRaisesRegex(OSError,'response loss'):self.run_capture()
  self.cli.write_text('broken')
  recovered=self.m.resume(self.config,'case1');self.assertEqual(recovered['status'],'SUCCEEDED')
 def test_ingest_saved_response_lost_resumes_original_success(self):
  original=self.m._checkpoint
  def fail(path,data):
   if path.name=='result.json':raise OSError('synthetic result loss')
   return original(path,data)
  from unittest.mock import patch
  with patch.object(self.m,'_checkpoint',side_effect=fail):
   with self.assertRaisesRegex(OSError,'result loss'):self.run_capture()
  before=list((self.runtime/'ingest').glob('runs/*/imports/*'))
  self.assertEqual(self.m.resume(self.config,'case1')['status'],'SUCCEEDED');self.assertEqual(before,list((self.runtime/'ingest').glob('runs/*/imports/*')))
 def test_material_tamper_and_unsafe_run_id_rejected(self):
  result=self.run_capture();b=result['archive_binding'];p=Path(b['root'])/'manifest.json';p.write_bytes(p.read_bytes()+b' ')
  with self.assertRaises(ValueError):self.m.materials(b)
  with self.assertRaisesRegex(ValueError,'RUN_ID'):self.m.resume(self.config,'../escape')
 def test_cli_capture_requires_explicit_execution_flag(self):
  p=subprocess.run([sys.executable,'-B',str(ROOT/'launch.py'),'capture','--date',self.day,'--slot','0900','--run-id','case2'],input=json.dumps(self.config).encode(),capture_output=True)
  self.assertNotEqual(p.returncode,0);self.assertIn(b'EXPLICIT_ACQUISITION_REQUIRED',p.stdout)
  self.assertEqual(list((self.runtime/'captures').iterdir()),[])
 def test_initialize_recovers_only_marked_partial_layout(self):
  import shutil
  root=self.root/'partial';root.mkdir();(root/'.v5-m04-capture').write_bytes(self.m.MARKER)
  config=dict(self.config,runtime_root=str(root))
  self.assertEqual(self.m.initialize(config)['status'],'EXISTS')
  self.assertTrue((root/'ingest/.v5-research-ingest').is_file())
 def test_concurrent_capture_rejected_without_owner(self):
  import fcntl
  with (self.runtime/'capture.lock').open('a+b') as lock:
   fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
   with self.assertRaisesRegex(ValueError,'CAPTURE_BUSY'):self.run_capture()
  self.assertEqual(list((self.runtime/'captures').iterdir()),[])
 def test_old_acquisition_never_runs(self):
  with self.assertRaisesRegex(ValueError,'NEW_CAPTURE_DATE_REQUIRED'):self.m.capture(self.config,'20200101','0900','old')
  self.assertEqual(list((self.runtime/'captures').iterdir()),[])
 def test_reused_capture_id_requires_same_date_slot_and_claim_id(self):
  self.run_capture()
  for day,slot in [('20200101','0900'),(self.day,'1000')]:
   with self.assertRaisesRegex(ValueError,'CAPTURE_REQUEST_IDENTITY'):self.m.capture(self.config,day,slot,'case1')
  path=self.runtime/'captures/case1/claim.json';claim=json.loads(path.read_bytes());claim['run_id']='other';path.write_text(json.dumps(claim))
  with self.assertRaisesRegex(ValueError,'CAPTURE_CLAIM_IDENTITY'):self.m.resume(self.config,'case1')
 def test_interrupted_checkpoint_never_publishes_partial_final_file(self):
  from unittest.mock import patch
  path=self.runtime/'result.json';original=Path.open
  class BrokenWrite:
   def __init__(self,stream):self.stream=stream
   def __enter__(self):return self
   def __exit__(self,*args):return self.stream.__exit__(*args)
   def write(self,data):self.stream.write(data[:10]);self.stream.flush();raise OSError('synthetic partial write')
  def opened(p,*args,**kwargs):
   stream=original(p,*args,**kwargs)
   return BrokenWrite(stream) if args and args[0]=='xb' else stream
  with patch.object(Path,'open',opened):
   with self.assertRaisesRegex(OSError,'partial write'):self.m._checkpoint(path,{'payload':'synthetic checkpoint'})
  self.assertFalse(path.exists())
  self.m._checkpoint(path,{'payload':'synthetic checkpoint'})
  with self.assertRaises(FileExistsError):self.m._checkpoint(path,{'payload':'changed'})
  self.assertEqual(json.loads(path.read_bytes()),{'payload':'synthetic checkpoint'})
 def test_unknown_legacy_time_is_not_backfilled(self):
  result=self.run_capture();payload=self.m.materials(result['archive_binding'])
  a=payload['articles'][0];self.assertEqual(a['source_article']['retrieved_at'],a['retrieved_at'])
  # The projection alone must preserve unknown historical fields. Its caller
  # still requires the independent original reader before calling it.
  old=dict(a['source_article']);old.pop('retrieved_at');old.pop('available_at')
  projected=self.m._article(old,a['archive_file'],a['archive_sha256'])
  self.assertEqual(projected['acquisition_status'],'UNKNOWN');self.assertIsNone(projected['retrieved_at']);self.assertIsNone(projected['available_at'])
if __name__=='__main__':unittest.main()
