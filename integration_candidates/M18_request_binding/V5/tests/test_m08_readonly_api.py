"""New P0 seam tests only; original M08/M06 suites are not rerun."""
import copy,hashlib,http.client,json,os,subprocess,sys,tempfile,threading,unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlencode
ROUTE='/api/v5/source-bundle/hk-stage-observed';BINDING='m08_hk_stage_observed_binding'
class M08ReadOnlyTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup);cls.base=Path(cls.tmp.name).resolve()
  from fixtures.hk_stage_observed_factory import create_fixture
  cls.binding,cls.expected=create_fixture(cls.base/'fixture')
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name).resolve();api=self.root/'api';api.mkdir();(api/'.v5-module-root').write_text('v5.module-root.v1:source_bundle\n')
  self.config=dict(schema_version='v5.module_api.v1',module_id='source_bundle',release_id='m08-test',data_root=str(api),routes=[ROUTE,'/api/v5/source-bundle/hk-preselection','/api/v5/source-bundle/hk-close-review','/api/v5/source-bundle/a-close-replay'])
 def request(self,path=ROUTE,method='GET'):
  from v5_shadow.module_api import create_module_server
  server=create_module_server(self.config);t=threading.Thread(target=server.serve_forever);t.start()
  try:return self.get(server,path,method)
  finally:server.shutdown();t.join();server.server_close()
 def get(self,server,path,method='GET'):
  c=http.client.HTTPConnection('127.0.0.1',server.server_address[1],timeout=90);c.request(method,path);r=c.getresponse();v=json.loads(r.read());status=r.status;c.close();return status,v
 def bind(self):self.config[BINDING]=copy.deepcopy(self.binding)
 def query(self,index=0):
  r=self.config[BINDING]['references'][index];return ROUTE+'?'+urlencode(dict(date=r['target_date'],stage=r['stage_id'],run_id=r['run_id'],import_sha256=r['import_sha256']))
 def inventory(self,root):return {str(p.relative_to(root)):(hashlib.sha256(p.read_bytes()).hexdigest(),p.stat().st_mtime_ns) for p in root.rglob('*') if p.is_file()}
 def test_unconfigured_is_explicit(self):
  status,v=self.request();self.assertEqual(status,200);self.assertEqual(v['status'],'NOT_CONFIGURED');self.assertNotIn('artifact',v)
 def test_catalog_retains_all_ten_references_and_duplicate_stages(self):
  self.bind();status,v=self.request();self.assertEqual(status,200);self.assertEqual(v['references'],self.binding['references']);self.assertEqual(len(v['references']),10);self.assertEqual(len({r['stage_id'] for r in v['references']}),8);self.assertIs(v['references_verified'],False);self.assertNotIn('artifact',v)
 def test_each_exact_reference_preserves_original_rows_fields_status_and_bytes(self):
  self.bind();before=self.inventory(self.base);responses=self.inventory(self.root)
  for i in range(10):
   status,v=self.request(self.query(i));self.assertEqual(status,200,v);self.assertEqual(v['artifact'],self.expected[i]['artifact']);self.assertEqual(v['reference'],self.binding['references'][i]);self.assertEqual(v['provenance'],self.expected[i]['provenance']);self.assertEqual(len(v['artifact']['rows']),10);self.assertIsNone(v['provenance']['captured_at']);self.assertEqual(v['status'],self.expected[i]['artifact']['selection_status']);self.assertNotIn(str(self.base),json.dumps(v));self.assertEqual(v['stage_group']=='HK_STAGE8_SEPARATE',i==7)
  self.assertEqual(before,self.inventory(self.base));self.assertEqual(responses,self.inventory(self.root));self.assertNotIn('v5_shadow.hk_stage_observed',sys.modules)
 def test_unknown_partial_and_duplicate_query_rejected(self):
  self.bind()
  for query in ['?run_id=latest','?date=20261008','?date=x&date=y',self.query().removeprefix(ROUTE).replace('import_sha256=','bad='),self.query().removeprefix(ROUTE)+'&extra=x',self.query().removeprefix(ROUTE).replace('20261008','20261009')]:
   status,v=self.request(ROUTE+query);self.assertIn(status,(400,409));self.assertNotIn('artifact',v)
 def test_binding_requires_ten_exact_distinct_references_all_eight_stages(self):
  from v5_shadow.m08_readonly import validate_binding
  self.bind()
  for mutate in [lambda b:b['references'].pop(),lambda b:b['references'].append(copy.deepcopy(b['references'][0])),lambda b:b['references'].__setitem__(1,copy.deepcopy(b['references'][0])),lambda b:b['references'][1].update(import_receipt_sha256='bad'),lambda b:b.update(recorded_root='../old'),lambda b:b.update(source_root='/old')]:
   c=copy.deepcopy(self.config);mutate(c[BINDING])
   with self.assertRaises((ValueError,TypeError)):validate_binding(c)
 def test_tampered_import_rejected_and_original_restored(self):
  self.bind();ref=self.binding['references'][0];p=Path(self.binding['recorded_root'])/'imports'/ref['import_sha256']/'receipt.json';raw=p.read_bytes();meta=p.stat()
  try:
   p.write_bytes(raw+b' ');status,v=self.request(self.query());self.assertEqual(status,409);self.assertNotIn('artifact',v)
  finally:p.write_bytes(raw);os.utime(p,ns=(meta.st_atime_ns,meta.st_mtime_ns))
 def test_old_source_absence_and_latest_pointer_do_not_affect_exact_read(self):
  self.bind();source=self.base/'fixture/original';offline=self.base/'fixture/original-offline';source.rename(offline)
  recorded=Path(self.binding['recorded_root']);before=self.inventory(recorded)
  try:
   status,value=self.request(self.query(9));self.assertEqual(status,200,value);self.assertEqual(value['artifact'],self.expected[9]['artifact']);self.assertEqual(before,self.inventory(recorded));self.assertEqual(value['status'],'CANNOT_CONFIRM');self.assertEqual(value['artifact']['rows'][0]['source_mode'],'HK_CONNECT_D1_PRESELECT_REFERENCE')
  finally:offline.rename(source)
 def test_rebound_receipt_hash_is_rejected_without_any_fallback(self):
  self.bind();self.config[BINDING]['references'][0]['import_receipt_sha256']='0'*64
  status,value=self.request(self.query());self.assertEqual(status,409);self.assertNotIn('artifact',value)
 def test_no_mutating_http_method(self):
  self.bind()
  for method in ('POST','PUT','PATCH','DELETE','OPTIONS'):
   status,v=self.request(self.query(),method);self.assertEqual(status,405);self.assertEqual(v['reason_codes'],['MODULE_READ_ONLY'])
 def test_m08_busy_never_blocks_other_module_read_slots(self):
  from v5_shadow.module_api import create_module_server
  from v5_shadow import m08_readonly
  entered=threading.Event();release=threading.Event();original=m08_readonly.read_record
  def blocked(config,query):entered.set();release.wait(8);return original(config,query)
  server=create_module_server(self.config);t=threading.Thread(target=server.serve_forever);t.start();responses=[]
  try:
   with patch.object(m08_readonly,'read_record',side_effect=blocked):
    one=threading.Thread(target=lambda:responses.append(self.get(server,ROUTE)));one.start();self.assertTrue(entered.wait(2))
    self.assertEqual(self.get(server,ROUTE)[0],503)
    for route in self.config['routes'][1:]:self.assertEqual(self.get(server,route)[1]['status'],'NOT_CONFIGURED')
    release.set();one.join();self.assertEqual(responses[0][0],200)
  finally:release.set();server.shutdown();t.join();server.server_close()
 def test_owner_closure_is_pinned_and_cold_worker_has_only_reader_entry(self):
  from v5_shadow.m08_readonly import owner_root
  root=owner_root();self.assertTrue((root/'V5/src/v5_shadow/hk_stage_observed.py').is_file())
  worker=(Path(__file__).resolve().parents[1]/'src/v5_shadow/m08_readonly_worker.py').read_text()
  self.assertNotIn('import_hk_stage_observed(',worker);self.assertNotIn('prepare_hk_stage_observed_reference(',worker);self.assertNotIn('publish_hk_stage_observed_response(',worker)
