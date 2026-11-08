import hashlib,json,pathlib,subprocess,sys,tempfile,unittest,os
H=pathlib.Path(__file__).resolve().parent
ROOT=pathlib.Path(os.environ['M07_TEST_ROOT'])
class Tests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.folder=pathlib.Path(self.t.name)
 def fixture(self,stage):
  # Existing fixture runs in a separate process; cannot contaminate replay imports.
  code="import sys,json,pathlib;sys.path.insert(0,sys.argv[1]);from m07_fixture import make_case;print(json.dumps(make_case(pathlib.Path(sys.argv[2]),count=2,stage=sys.argv[3])))"
  p=subprocess.run([sys.executable,'-B','-c',code,str(ROOT/'V5/tests'),str(self.folder),stage],capture_output=True,text=True,timeout=30);self.assertEqual(p.returncode,0,p.stderr);return json.loads(p.stdout)
 def runone(self,request):
  return subprocess.run([sys.executable,*(['-O'] if sys.flags.optimize else []),'-I','-B',str(H/'replay.py'),'--m07-root',str(ROOT)],input=json.dumps(request),capture_output=True,text=True,timeout=60)
 def test_both_original_selectors(self):
  for stage in ('STAGE_0925','STAGE_0930_0935'):
   with self.subTest(stage=stage):
    if stage!='STAGE_0925':self.folder=self.folder/'second';self.folder.mkdir()
    request=self.fixture(stage);before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in self.folder.rglob('*') if p.is_file()};p=self.runone(request);self.assertEqual(p.returncode,0,p.stdout+p.stderr);r=json.loads(p.stdout);self.assertEqual(r['status'],'ORIGINAL_SELECTOR_REPLAY_NOT_ADMITTED');self.assertFalse(r['production_allowed']);self.assertFalse(r['activation_performed']);self.assertTrue(r['known_synthetic']);self.assertLessEqual(len(r['selection']['rows']),10);self.assertEqual(before,{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in self.folder.rglob('*') if p.is_file()})
 def test_synthetic_cannot_be_relabelled(self):
  x=self.fixture('STAGE_0925');x['data_kind']='RECORDED_INPUT_REPLAY';p=self.runone(x);self.assertEqual(p.returncode,2);self.assertIn('SYNTHETIC_RELABEL',p.stdout)
 def test_changed_bytes_rejected(self):
  x=self.fixture('STAGE_0925');binding=x['inputs']['live'];name=next(iter(binding['files']));f=pathlib.Path(binding['root'])/name;f.write_bytes(f.read_bytes()+b' ');p=self.runone(x);self.assertEqual(p.returncode,2)
 def test_natural_rejected(self):
  x=self.fixture('STAGE_0925');x['natural']=True;p=self.runone(x);self.assertEqual(p.returncode,2);self.assertIn('NATURAL_EXECUTION_NOT_BOUND',p.stdout)
 def test_other_stage_rejected_before_loading(self):
  p=self.runone({'stage_id':'STAGE_1500'});self.assertEqual(p.returncode,2);self.assertIn('STAGE_SCOPE',p.stdout)
if __name__=='__main__':unittest.main()
