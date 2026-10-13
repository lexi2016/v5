import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

BASE=Path(__file__).resolve().parents[1]
class DeliveryTests(unittest.TestCase):
 def test_default_launcher_exists(self):
  self.assertTrue((BASE/'run_mapping.py').is_file(), 'Default standalone launcher missing')
 def test_help_runs_outside_repository(self):
  r=subprocess.run([sys.executable,'-I',str(BASE/'run_mapping.py'),'--help'],cwd='/tmp',capture_output=True,text=True)
  self.assertEqual(r.returncode,0,r.stderr)
  self.assertIn('prepare',r.stdout);self.assertIn('read',r.stdout)

sys.path.insert(0,str(BASE/'runtime/V5/src'))
from v5_shadow import m15_delivery as delivery
class ContractTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
 def test_init_does_not_adopt_existing_directory(self):
  p=self.root/'output';p.mkdir();(p/'old').write_text('keep')
  self.assertTrue(callable(getattr(delivery,'initialize',None)),'Missing protected output initialization')
  with self.assertRaises(ValueError):delivery.initialize(p)
  self.assertEqual((p/'old').read_text(),'keep')
 def test_prepare_hashes_source_files_and_never_invents_sources(self):
  self.assertTrue(callable(getattr(delivery,'prepare',None)),'Missing input preparation')
  source=self.root/'input';source.mkdir()
  spec=dict(mode='seed',target_date='20261012',cutoff='2026-10-10T01:00:00+00:00',us_root=str(source),session_date='20261009')
  with self.assertRaises((ValueError,FileNotFoundError)):delivery.prepare(spec)
 def test_seal_and_cold_read_are_bound_to_original_bytes(self):
  self.assertTrue(callable(getattr(delivery,'save_result',None)),'Missing saved independent reader')
  root=self.root/'output';delivery.initialize(root)
  owner=root/'owners';owner.mkdir();artifact=owner/'original.json';artifact.write_text('{"run_id":"original"}')
  ref=delivery.save_result(root,dict(target_date='20261012',mode='seed',seed={'run_id':'original'},material=None),[artifact])
  self.assertEqual(delivery.read_result(root,ref)['seed']['run_id'],'original')
  artifact.write_text('{}')
  with self.assertRaisesRegex(ValueError,'OWNER_BYTES_CHANGED'):delivery.read_result(root,ref)
 def test_wrong_reference_and_symlink_rejected(self):
  self.assertTrue(callable(getattr(delivery,'read_result',None)),'Missing saved independent reader')
  root=self.root/'output';delivery.initialize(root)
  ref=delivery.save_result(root,dict(target_date='20261012',mode='seed',seed=None,material=None),[])
  with self.assertRaises(ValueError):delivery.read_result(root,dict(ref,sha256='0'*64))
  alias=self.root/'alias';alias.symlink_to(root,target_is_directory=True)
  with self.assertRaises(ValueError):delivery.read_result(alias,ref)

class OwnerEndToEndTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
 def request(self,mode):
  materials=self.root/'material_inputs';materials.mkdir(exist_ok=True)
  spec=dict(mode=mode,target_date='20261012',cutoff='2026-10-10T01:00:00+00:00',
            us_root=str(BASE/'tests/fixtures/quote_only'),session_date='20261009')
  if mode=='both':spec.update(materials=dict(root=str(materials),files=[]),native_master=None)
  return delivery.prepare(spec)
 def test_quote_only_seed_uses_market_snapshot_not_news_count(self):
  root=self.root/'out';delivery.initialize(root)
  output=delivery.execute(self.request('seed'),root)
  result=delivery.read_result(root,output['reference']);daily=result['seed']['persisted_daily']
  self.assertEqual(daily['source_status'],'READY')
  self.assertEqual(daily['coverage']['configured_us_universe_count'],33)
  self.assertFalse(result['formal_eligible']);self.assertFalse(result['natural_verified'])
  reference=self.root/'reference.json';reference.write_text(json.dumps(output['reference']))
  child=subprocess.run([sys.executable,'-I',str(BASE/'run_mapping.py'),'read','--reference',str(reference),'--root',str(root)],cwd='/tmp',capture_output=True,text=True)
  self.assertEqual(child.returncode,0,child.stderr+child.stdout)
  self.assertEqual(json.loads(child.stdout),result)
 def test_both_paths_execute_original_material_owner_and_preserve_missing_identity(self):
  root=self.root/'out';delivery.initialize(root)
  output=delivery.execute(self.request('both'),root)
  result=delivery.read_result(root,output['reference'])
  material=result['material'];self.assertIsNotNone(material)
  self.assertEqual(material['readback']['status'],'MATCHED')
  coverage=material['coverage_paths']
  self.assertFalse(coverage['formal_eligible'])
  self.assertIsNotNone(coverage['combined_material_assessment_state'])
  self.assertNotEqual(coverage['combined_material_assessment_state'],'COMPLETE')
  self.assertFalse(coverage['industry_material']['explicit_us_ticker_required'])
  self.assertTrue(coverage['individual_material']['explicit_us_ticker_required'])
 def test_changed_source_refused_before_attempt_and_old_success_unchanged(self):
  root=self.root/'out';delivery.initialize(root);request=self.request('seed')
  good=delivery.execute(request,root);before=list((root/'attempts').iterdir())
  request['us']['files']['research/peripherals/manifest.json']='0'*64
  with self.assertRaises(ValueError):delivery.execute(request,root)
  self.assertEqual(list((root/'attempts').iterdir()),before)
  self.assertEqual(delivery.read_result(root,good['reference'])['seed']['persisted_daily']['source_status'],'READY')

class OriginalMaterialContractTests(unittest.TestCase):
 def test_original_body_parser_positive_and_refusals(self):
  child=subprocess.run([sys.executable,'-I',str(BASE/'tests/material_owner_probe.py')],cwd='/tmp',capture_output=True,text=True)
  self.assertEqual(child.returncode,0,child.stderr+child.stdout[-1500:])
  self.assertIn('PASS original material',child.stdout)

class PublicationTests(unittest.TestCase):
 def test_three_paths_and_unknown_are_preserved_without_private_roots(self):
  self.assertTrue(callable(getattr(delivery,'publication_records',None)),'Missing ordinary module API publication')
  with tempfile.TemporaryDirectory() as temporary:
   root=Path(temporary)/'root';delivery.initialize(root)
   result=dict(mode='both',target_date='20261012',seed=dict(persisted_daily=dict(status='VALID_EMPTY',run_id='a'*32,artifact_sha256='b'*64,
       matches=[],gaps=[],source_status='READY',coverage={'available_us_universe_count':None},target_date_eligibility='CANNOT_CONFIRM')),
       material=dict(coverage_paths={'combined_material_assessment_state':'INSUFFICIENT'},workspace=dict(us_market_attention=dict(mapping_diagnostics=dict(
       assessment_state='INSUFFICIENT',assessment_reasons=['MISSING'],industry=[{'label':'CPO','reason':'NO_RELATION','source_root':'/private/do-not-show'}],individual=[])))))
   ref=delivery.save_result(root,result,[])
   config=dict(module_id='source_bundle',release_id='test')
   records=delivery.publication_records(root,ref,config,data_kind='SYNTHETIC')
   self.assertNotIn('/private/do-not-show',json.dumps(records))
   summary=next(r['payload'] for r in records if r['query']=={'date':'20261012'})
   self.assertEqual(summary['lanes'],{'seed':0,'industry':1,'individual':0})
   self.assertEqual(summary['material_status'],'INSUFFICIENT')
   self.assertIsNone(summary['seed_coverage']['available_us_universe_count'])
   self.assertTrue(all(r['path']=='/api/v5/source-bundle/us-mapping-saved' for r in records))

class MoreRejections(unittest.TestCase):
 setUp=OwnerEndToEndTests.setUp
 request=OwnerEndToEndTests.request
 def test_wrong_session_request_rejected(self):
  root=self.root/'out';delivery.initialize(root);r=self.request('seed')
  r['target_date']='20261014'
  r['cutoff']='2026-10-13T13:00:00+00:00'
  with self.assertRaisesRegex(RuntimeError,'SOURCE_SESSION_MISMATCH'):delivery.execute(r,root)
  self.assertEqual(list((root/'results').iterdir()),[])
 def test_news_only_payload_is_not_market_snapshot(self):
  import shutil,hashlib
  source=self.root/'news';shutil.copytree(BASE/'tests/fixtures/quote_only',source)
  path=source/'research/peripherals/20261009/external_finance.json'
  value=json.loads(path.read_text());value.pop('market_snapshot',None);path.write_text(json.dumps(value))
  r=self.request('seed');r['us']['root']=str(source)
  r['us']['files'][str(path.relative_to(source))]=hashlib.sha256(path.read_bytes()).hexdigest()
  root=self.root/'out';delivery.initialize(root)
  result=delivery.read_result(root,delivery.execute(r,root)['reference'])
  self.assertNotEqual(result['seed']['persisted_daily']['source_status'],'READY')
  self.assertEqual(result['seed']['persisted_daily']['matches'],[])
 def test_future_and_missing_material_binding_rejected(self):
  r=self.request('both');r['cutoff']='2999-01-01T00:00:00Z'
  root=self.root/'out';delivery.initialize(root)
  with self.assertRaisesRegex(ValueError,'FUTURE_CUTOFF'):delivery.execute(r,root)
  r=self.request('both');r['inputs'].pop('materials')
  with self.assertRaisesRegex(ValueError,'MATERIAL_STORE_BINDING_REQUIRED'):delivery.execute(r,root)

class OrdinaryApiTests(unittest.TestCase):
 def test_original_module_server_serves_same_identity_and_never_runs_owner(self):
  import http.client,threading,hashlib
  from v5_shadow.module_api import create_module_server
  from v5_shadow.module_artifacts import publish_generation
  with tempfile.TemporaryDirectory() as temporary:
   root=Path(temporary)/'saved';delivery.initialize(root)
   result=dict(mode='seed',target_date='20261012',seed=dict(persisted_daily=dict(status='PARTIAL',run_id='a'*32,artifact_sha256='b'*64,matches=[{'us_symbol':'SYN','hk_symbol':'HK.00001'}],gaps=['SYNTHETIC'],source_status='PARTIAL',coverage={},target_date_eligibility='CANNOT_CONFIRM')),material=None)
   ref=delivery.save_result(root,result,[])
   api=Path(temporary)/'api';api.mkdir();(api/'.v5-module-root').write_text('v5.module-root.v1:source_bundle\n')
   (api/'responses').mkdir()
   config=dict(schema_version='v5.module_api.v1',module_id='source_bundle',release_id='m15-test',data_root=str(api),routes=[delivery.ROUTE])
   publication=publish_generation(config,delivery.publication_records(root,ref,config,data_kind='SYNTHETIC'),expected_generation=None)
   server=create_module_server(config);thread=threading.Thread(target=server.serve_forever);thread.start()
   def snapshot():return {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(temporary).rglob('*') if p.is_file()}
   before=snapshot()
   try:
    conn=http.client.HTTPConnection('127.0.0.1',server.server_address[1],timeout=5)
    conn.request('GET',delivery.ROUTE+'?date=20261012');response=conn.getresponse();payload=json.loads(response.read());self.assertEqual(response.status,200);self.assertEqual(payload['reference'],ref)
    conn.request('GET',delivery.ROUTE+'?date=20261012&run_id='+ref['run_id']+'&lane=seed&offset=0');response=conn.getresponse();page=json.loads(response.read());self.assertEqual(response.status,200);self.assertEqual(page['rows'],result['seed']['persisted_daily']['matches'])
    conn.request('POST',delivery.ROUTE);response=conn.getresponse();response.read();self.assertEqual(response.status,405)
    conn.request('GET',delivery.ROUTE+'?date=20261013');response=conn.getresponse();response.read();self.assertEqual(response.status,503)
    conn.close();self.assertEqual(snapshot(),before)
   finally:server.shutdown();server.server_close();thread.join()

class FullMaterialOwnerTests(unittest.TestCase):
 def test_source_triplet_archive_body_native_identity_to_original_saved_both_paths(self):
  with tempfile.TemporaryDirectory() as temporary:
   root=Path(temporary);material=root/'materialstore';material.mkdir();out=root/'out';delivery.initialize(out)
   fixture=BASE/'tests/fixtures/materials';context=json.loads((fixture/'fixture_context.json').read_text())
   def bind(directory):return dict(root=str(directory),files=sorted(str(p.relative_to(directory)) for p in directory.rglob('*') if p.is_file() and not p.name.startswith('.')))
   archive=bind(fixture/'archive');native=bind(fixture/'native')
   spec=dict(mode='both',target_date=context['target_date'],cutoff=context['cutoff'],us_root=str(BASE/'tests/fixtures/quote_only_20261012'),session_date='20261012',materials=dict(root=str(material),files=[]),native_master=native,archives=archive)
   result=delivery.read_result(out,delivery.execute(delivery.prepare(spec),out)['reference'])
   workspace=result['material']['workspace'];diagnostics=workspace['us_market_attention']['mapping_diagnostics']
   self.assertEqual(diagnostics['assessment_state'],'ASSESSED_WITH_RELATIONS',json.dumps(diagnostics,ensure_ascii=False))
   self.assertTrue(any(row['accepted_mapping_count']>0 for row in diagnostics['industry']))
   self.assertTrue(any(row['symbol']=='AVGO' and row['accepted_mapping_count']>0 for row in diagnostics['individual']))
   self.assertFalse(result['formal_eligible']);self.assertFalse(result['natural_verified'])
   self.assertEqual(result['material']['readback']['status'],'MATCHED')

class ReceiptRecoveryTests(unittest.TestCase):
 def test_lost_stdout_reference_can_be_recovered_without_repeating_owner(self):
  self.assertTrue(callable(getattr(delivery,'list_results',None)),'Missing immutable receipt recovery')
  with tempfile.TemporaryDirectory() as temporary:
   root=Path(temporary)/'out';delivery.initialize(root)
   reference=delivery.save_result(root,dict(target_date='20261012',mode='seed',seed=None,material=None),[])
   before={str(p):p.read_bytes() for p in root.rglob('*') if p.is_file()}
   self.assertEqual(delivery.list_results(root),[reference])
   self.assertEqual({str(p):p.read_bytes() for p in root.rglob('*') if p.is_file()},before)
