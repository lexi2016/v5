"""Actual module server tests; temporary loopback, synthetic data only."""
import hashlib,http.client,json,os,sys,tempfile,threading,unittest,subprocess
from pathlib import Path
ROOT=Path(os.environ['RESEARCH_INTEGRATED_ROOT'])
sys.path.insert(0,str(ROOT/'V5/src'))
from v5_shadow.module_api import create_module_server
class HttpTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
  (self.root/'.v5-module-root').write_text('v5.module-root.v1:source_bundle\n')
  self.config=dict(schema_version='v5.module_api.v1',module_id='source_bundle',release_id='RESEARCH_SYNTHETIC_TEST',data_root=str(self.root),routes=['/api/v5/research/lane','/api/v5/research/wechat/materials'])
 def start(self):
  self.server=create_module_server(self.config);self.thread=threading.Thread(target=self.server.serve_forever);self.thread.start()
  self.addCleanup(self.stop)
 def stop(self):self.server.shutdown();self.thread.join();self.server.server_close()
 def get(self,path,method='GET'):
  c=http.client.HTTPConnection('127.0.0.1',self.server.server_address[1],timeout=40);c.request(method,path);r=c.getresponse();body=json.loads(r.read());c.close();return r.status,body
 def test_get_missing_latest_and_readonly(self):
  self.start();before={str(p):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
  status,p=self.get('/api/v5/research/lane?research_date=20261012');self.assertEqual(status,200);self.assertEqual(p['research_date'],'20261012');self.assertEqual(p['status'],'NOT_MATERIALIZED')
  status,p=self.get('/api/v5/research/lane');self.assertEqual(p['endpoint_mode'],'LATEST');self.assertEqual(p['research_date'],'')
  self.assertEqual(self.get('/api/v5/research/lane','POST')[0],405)
  self.assertEqual(self.get('/api/v5/research/lane?research_date=20261012&research_date=20261013')[0],400)
  self.assertEqual(self.get('/api/v5/research/lane?research_date=20260230')[0],409)
  status,p=self.get('/api/v5/research/wechat/materials?date=20261012&limit=20');self.assertEqual(status,200);self.assertEqual(p['status'],'NOT_CONFIGURED')
  self.assertEqual(before,{str(p):p.read_bytes() for p in self.root.rglob('*') if p.is_file()})
 def test_real_m04_cli_cold_reader_with_synthetic_owner_archive(self):
  package=Path(os.environ['M04_CAPTURE_PACKAGE'])
  code="""import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(sys.argv[1])/'tests'));import test_capture
fixture=test_capture.CaptureTests();fixture.setUp()
try:
 result=fixture.run_capture();print(json.dumps(dict(binding=result['archive_binding'],day=fixture.day,body=fixture.body)),flush=True);sys.stdin.read()
finally:fixture.doCleanups()
"""
  proc=subprocess.Popen([sys.executable,'-I','-B','-c',code,str(package)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
  self.addCleanup(lambda: proc.communicate('',timeout=15))
  data=json.loads(proc.stdout.readline());binding=data['binding']
  self.config['m04_research_lane_binding']=dict(package_root=str(package),package_manifest_sha256=hashlib.sha256((package/'RELEASE.json').read_bytes()).hexdigest(),archive_binding=binding,python_executable=str(Path(sys.executable).resolve()))
  before={str(p):p.read_bytes() for p in Path(binding['root']).rglob('*') if p.is_file()}
  self.start();status,p=self.get('/api/v5/research/lane?research_date='+data['day'])
  self.assertEqual(status,200,p);self.assertEqual(p['archive_materials']['articles'][0]['body_text'],data['body']);self.assertFalse(p['orders_sent'])
  self.assertEqual(p['endpoint_mode'],'EXACT');self.assertEqual(self.get('/api/v5/research/lane')[1]['archive_materials'],p['archive_materials'])
  status,p=self.get('/api/v5/research/lane?research_date=20260101');self.assertEqual(status,200);self.assertEqual(p['status'],'NOT_MATERIALIZED')
  self.assertEqual(before,{str(p):p.read_bytes() for p in Path(binding['root']).rglob('*') if p.is_file()})
if __name__=='__main__':unittest.main()
