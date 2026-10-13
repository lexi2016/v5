"""All generated local owner inputs/products are explicitly SYNTHETIC."""
import copy,hashlib,importlib.util,json,subprocess,sys,tempfile,threading,unittest
from pathlib import Path
from urllib.request import urlopen,Request
from urllib.error import HTTPError
BASE=Path(__file__).resolve().parents[1]
ROUTE='/api/v5/source-bundle/a-stage-saved'
class M07P0Tests(unittest.TestCase):
 def test_actual_entry_and_reader_are_present(self):
  self.assertIsNotNone(importlib.util.find_spec('v5_shadow.p0_a_stage'));self.assertIsNotNone(importlib.util.find_spec('v5_shadow.m07_readonly'))
 def test_registry_names_the_executable_gate(self):
  from v5_shadow.main_registry import registry_by_id
  row=registry_by_id()['M07_A_STAGE'];self.assertEqual(row.owner_entry,'p0_a_stage.run_explicit');self.assertEqual(row.status,'CALLABLE_CANDIDATE_REQUIRES_INPUT')
 def test_unbound_http_is_specific_waiting_and_never_writes(self):
  from v5_shadow.module_api import create_module_server
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'.v5-module-root').write_text('v5.module-root.v1:source_bundle\n')
   cfg=dict(schema_version='v5.module_api.v1',module_id='source_bundle',release_id='test',data_root=str(root),routes=[ROUTE])
   before={p.name:p.read_bytes() for p in root.iterdir()};server=create_module_server(cfg);threading.Thread(target=server.serve_forever,daemon=True).start()
   try:
    url='http://127.0.0.1:'+str(server.server_address[1])+ROUTE
    with urlopen(url) as r:payload=json.load(r)
    self.assertEqual(payload['status'],'WAITING');self.assertEqual(set(payload['missing_inputs']),{'M05_SIX_PHYSICAL_POOLS','M01_RAW_TRIO_AND_RECORDING_CLOCKS','M04_HOURLY_SOURCE_WITNESS_AND_MORNING','M07_VERIFIED_SAVED_REFERENCE'});self.assertIsNone(payload['selection'])
    with self.assertRaises(HTTPError) as ctx:urlopen(Request(url,method='POST',data=b'{}'))
    self.assertEqual(ctx.exception.code,405);self.assertEqual(before,{p.name:p.read_bytes() for p in root.iterdir()})
   finally:server.shutdown();server.server_close()
 def test_server_disables_bytecode_before_get(self):
  from v5_shadow.module_api import create_module_server
  prior=sys.dont_write_bytecode
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'.v5-module-root').write_text('v5.module-root.v1:source_bundle\n')
   sys.dont_write_bytecode=False
   server=create_module_server(dict(schema_version='v5.module_api.v1',module_id='source_bundle',release_id='test',data_root=str(root),routes=[ROUTE]))
   try:self.assertTrue(sys.dont_write_bytecode)
   finally:server.server_close();sys.dont_write_bytecode=prior
 def test_other_saved_readers_still_wait_independently(self):
  from v5_shadow.module_api import read_response
  for route in ('/api/v5/source-bundle/intraday-research','/api/v5/source-bundle/video-fupan','/api/v5/source-bundle/manager-public-research'):
   cfg=dict(schema_version='v5.module_api.v1',module_id='source_bundle',release_id='cross',routes=[ROUTE,route])
   record,_=read_response(cfg,None,route,{})
   self.assertEqual(record['payload']['status'],'WAITING')
   self.assertIs(record['payload']['production_allowed'],False)
 def test_execution_default_and_missing_binding_are_closed(self):
  from v5_shadow.p0_a_stage import run_explicit
  self.assertEqual(run_explicit(None,None)['status'],'WAITING');self.assertEqual(run_explicit(None,None,allow_execution=True)['status'],'WAITING')
class M07P0OwnerTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();cls.root=Path(cls.tmp.name);cls.owner=BASE/'source_owners/m07'
  script='''import json,sys
from pathlib import Path
root=Path(sys.argv[1]);owner=Path(sys.argv[2]);sys.path[:0]=[str(owner/'V5/src'),str(owner/'V5/tests')]
from m07_fixture import make_case
from v5_shadow.a_stage_daily import run_a_stage_daily
inputs=root/'inputs';inputs.mkdir();request=make_case(inputs)
out=root/'output';out.mkdir();(out/'.v5-m07-output').write_bytes(b'v5.m07-private-output.v1\\n');(out/'ledger').mkdir();(out/'ledger/.v5-daily-run-ledger').write_bytes(b'v5.daily-run-ledger.v1\\n')
result=run_a_stage_daily(request,output_root=out);assert result['status']=='SUCCEEDED',result
print(json.dumps(dict(request=request,result=result)))
'''
  proc=subprocess.run([sys.executable,'-I','-B','-c',script,str(cls.root),str(cls.owner)],capture_output=True,text=True)
  if proc.returncode:raise AssertionError(proc.stderr+proc.stdout)
  value=json.loads(proc.stdout);cls.request=value['request'];cls.result=value['result']
  cls.binding=dict(output_root=str(cls.root/'output'),python_executable=sys.executable,python_sha256=hashlib.sha256(Path(sys.executable).resolve().read_bytes()).hexdigest(),data_kind='SYNTHETIC',references=[cls.result['state']['latest_success']['product_reference']])
 @classmethod
 def tearDownClass(cls):cls.tmp.cleanup()
 def config(self,binding=None):return dict(schema_version='v5.module_api.v1',module_id='source_bundle',release_id='test',routes=[ROUTE],m07_a_stage_binding=binding or self.binding)
 def test_cold_original_readback_preserves_partial_without_any_writes(self):
  from v5_shadow.m07_runtime import read_reference
  inventory=lambda:{str(p.relative_to(self.root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in self.root.rglob('*') if p.is_file()}
  before=inventory();value=read_reference(self.binding,self.binding['references'][0]);self.assertEqual(value['selection'],self.result['selection']);self.assertEqual(value['selection']['selection_status'],'PARTIAL_WITH_ROWS');self.assertEqual(before,inventory())
 def test_synthetic_reference_cannot_be_exposed_as_real_saved_page(self):
  from v5_shadow.m07_readonly import read_record
  record,_=read_record(self.config(),{});self.assertEqual(record['payload']['status'],'WAITING');self.assertIn('M07_SYNTHETIC_NOT_DISPLAYABLE',record['payload']['reason_codes']);self.assertIsNone(record['payload']['selection'])
 def test_recorded_label_cannot_override_explicit_synthetic_owner_evidence(self):
  from v5_shadow.m07_readonly import read_record
  binding=copy.deepcopy(self.binding);binding['data_kind']='RECORDED_INPUT_REPLAY';record,_=read_record(self.config(binding),{});self.assertEqual(record['payload']['status'],'WAITING');self.assertIsNone(record['payload']['selection'])
 def test_internal_worker_still_rejects_synthetic_execution(self):
  from v5_shadow.m07_runtime import invoke
  with self.assertRaisesRegex(ValueError,'REJECTED'):
   invoke(self.binding,'run',dict(request=self.request,execution_authorized=True))
 def test_wrong_python_pin_is_rejected(self):
  from v5_shadow.m07_runtime import read_reference
  binding=copy.deepcopy(self.binding);binding['python_sha256']='0'*64
  with self.assertRaisesRegex(ValueError,'PYTHON_IDENTITY'):read_reference(binding,binding['references'][0])
 def test_wrong_saved_hash_is_rejected_by_real_reader(self):
  from v5_shadow.m07_runtime import read_reference
  ref=copy.deepcopy(self.binding['references'][0]);ref['receipt_sha256']='0'*64
  with self.assertRaisesRegex(ValueError,'READBACK|REFERENCE'):read_reference(self.binding,ref)
 def test_optional_date_or_stage_filters(self):
  from v5_shadow.m07_readonly import read_record
  for query in ({'date':'20261012'},{'stage':'STAGE_0930_0935'}):
   record,_=read_record(self.config(),query);self.assertEqual(record['payload']['status'],'WAITING');self.assertIn('M07_SYNTHETIC_NOT_DISPLAYABLE',record['payload']['reason_codes'])
 def test_wrong_date_stage_never_reads_another_slot(self):
  from v5_shadow.m07_readonly import read_record
  binding=copy.deepcopy(self.binding);binding['data_kind']='RECORDED_INPUT_REPLAY';record,_=read_record(self.config(binding),dict(date='20261009',stage='STAGE_0930_0935'));self.assertEqual(record['payload']['status'],'WAITING');self.assertIn('M07_NO_SAVED_RESULT_FOR_SLOT',record['payload']['reason_codes'])
 def test_explicit_gate_still_rejects_synthetic_and_natural(self):
  from v5_shadow.p0_a_stage import run_explicit
  registration={k:self.binding[k] for k in ('output_root','python_executable','python_sha256')};registration['enabled']=True
  before=list((self.root/'output/generations').iterdir());value=run_explicit(registration,self.request,allow_execution=True);self.assertEqual(value['status'],'WAITING')
  request=copy.deepcopy(self.request);request.update(data_kind='RECORDED_INPUT_REPLAY',natural=True);value=run_explicit(registration,request,allow_execution=True);self.assertEqual(value['status'],'WAITING');self.assertEqual(before,list((self.root/'output/generations').iterdir()))
if __name__=='__main__':unittest.main()
