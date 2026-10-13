"""Native saved import tests. Every input is SYNTHETIC and sockets are blocked."""
import hashlib,importlib.util,json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
REPO=Path(__file__).resolve().parents[2]
DATE='20261011'

class NativeSavedImportTests(unittest.TestCase):
 def setUp(self):
  self.assertIsNotNone(importlib.util.find_spec('v5_shadow.m12_native_import'),'explicit native import adapter missing')
  from v5_shadow import m12_native_import as m
  self.m=m;tmp=tempfile.TemporaryDirectory(prefix='v5-m12-native-');self.addCleanup(tmp.cleanup)
  self.root=Path(tmp.name).resolve();self.source=self.root/'native-source';self.destination=self.root/'v5-import'
  script='''import json,sys,socket
from pathlib import Path
sys.path[:0]=[sys.argv[1],sys.argv[1]+'/tests/m12']
socket.socket.connect=lambda *a,**k: (_ for _ in ()).throw(AssertionError('network forbidden'))
socket.create_connection=socket.socket.connect
from test_video_fupan_default_chain import SimulatedOwner
from V5.vendor.video_fupan_baseline.review_core.config import ProducerConfig
from V5.vendor.video_fupan_baseline.review_core.core import run_video
root=Path(sys.argv[2]);result=run_video('20261011',mode='acquire',data_root=root,config=ProducerConfig(data_root=root,network_allowed=True),tools=SimulatedOwner().tools(),allow_network=True)
print(json.dumps({'run_id':result['run_id']}))
'''
  p=subprocess.run([sys.executable,'-I','-B','-c',script,str(REPO),str(self.source)],cwd=REPO,capture_output=True,text=True,check=True)
  self.run=json.loads(p.stdout)['run_id'];self.manifest=self.source/'review'/DATE/'runs'/self.run/'manifest.json';self.receipt=self.manifest.with_name('receipt.json')
  self.request=dict(source_root=str(self.source),destination_root=str(self.destination),trade_date=DATE,run_id=self.run,owner_manifest_sha256=self.sha(self.manifest),owner_receipt_sha256=self.sha(self.receipt),data_kind='SYNTHETIC',python_executable=sys.executable)
 @staticmethod
 def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
 def snapshot(self,root):return {str(p.relative_to(root)):(self.sha(p),p.stat().st_size,p.stat().st_mtime_ns) for p in root.rglob('*') if p.is_file()}
 def reseal(self,change):
  owner=json.loads(self.manifest.read_bytes());change(owner);self.manifest.write_text(json.dumps(owner));receipt=json.loads(self.receipt.read_bytes());receipt['manifest_sha256']=self.sha(self.manifest);self.receipt.write_text(json.dumps(receipt));self.request.update(owner_manifest_sha256=self.sha(self.manifest),owner_receipt_sha256=self.sha(self.receipt))
 def test_original_bytes_and_existing_reader_preserve_unreviewed_content(self):
  before=self.snapshot(self.source);result=self.m.import_saved_native(self.request);binding=result['binding'];target=Path(binding['private_root'])
  self.assertEqual(result['status'],'IMPORTED_SAVED_NATIVE');self.assertFalse(result['producer_invoked']);self.assertFalse(result['natural_verified']);self.assertEqual(target,self.destination/'data')
  self.assertEqual(before,self.snapshot(self.source));self.assertFalse((self.source/'video_fupan').exists())
  owner=json.loads(self.manifest.read_bytes());files={r['path'] for r in owner['artifact_refs']}|{str(p.relative_to(self.source)) for p in (self.manifest,self.receipt)}
  for relative in files:self.assertEqual((self.source/relative).read_bytes(),(target/relative).read_bytes())
  self.assertFalse((target/'review'/DATE/'current.json').exists());self.assertFalse((target/'video_fupan'/DATE/'latest_success.json').exists())
  envelope=json.loads((target/'video_fupan/runs'/DATE/self.run/'manifest.json').read_bytes());self.assertEqual(envelope['import_kind'],'NATIVE_SAVED_IMPORT');self.assertEqual(envelope['owner_manifest'],owner);self.assertNotIn('attempt_id',envelope);self.assertEqual(envelope['imported_at'],result['imported_at'])
  from datetime import datetime,timezone
  self.assertLess(abs((datetime.now(timezone.utc)-datetime.fromisoformat(result['imported_at'])).total_seconds()),60)
  from v5_shadow.m12_readonly import read_record,ROUTE,BINDING
  config=dict(schema_version='v5.module_api.v1',module_id='source_bundle',release_id='synthetic-native-import',routes=[ROUTE]);config[BINDING]=binding
  record,_=read_record(config,{'trade_date':DATE});v=record['payload'];self.assertEqual(v['status'],'SAVED_ASR_REVIEW_REQUIRED');self.assertEqual(v['transcript']['text'],'SIMULATED');self.assertFalse(v['review_completed']);self.assertEqual(v['data_kind'],'SYNTHETIC')
  self.assertFalse(any(n.endswith('review_core.producer') for n in sys.modules))
 def test_pinned_original_modules_are_not_imported_before_verification(self):
  script="import sys;sys.path.insert(0,sys.argv[1]+'/V5/src');import v5_shadow.m12_native_import;assert 'v5_shadow.video_fupan_store' not in sys.modules;assert 'v5_shadow.video_fupan_reader' not in sys.modules"
  result=subprocess.run([sys.executable,'-I','-B','-c',script,str(REPO)],capture_output=True)
  self.assertEqual(result.returncode,0,result.stderr)
 def test_dot_ref_rejects_cleanly(self):
  self.reseal(lambda owner:owner['artifact_refs'].append(dict(kind='error',path='.',sha256='0'*64)))
  with self.assertRaises(ValueError):self.m.import_saved_native(self.request)
  self.assertFalse(self.destination.exists())
 def test_malformed_or_missing_receipt_safety_mapping_rejects(self):
  for safety in (None,[],{},dict(production_allowed=False,buy_gate_updated=False,orders_sent=True)):
   receipt=json.loads(self.receipt.read_bytes());receipt['safety_flags']=safety;self.receipt.write_text(json.dumps(receipt));self.request['owner_receipt_sha256']=self.sha(self.receipt)
   with self.subTest(safety=safety),self.assertRaises(ValueError):self.m.import_saved_native(self.request)
   self.assertFalse(self.destination.exists())
 def test_ref_size_must_match_when_present(self):
  for bad_size in (-1,True,'12',10**9):
   self.reseal(lambda owner:owner['artifact_refs'][0].update(size=bad_size))
   with self.subTest(size=bad_size),self.assertRaises(ValueError):self.m.import_saved_native(self.request)
   self.assertFalse(self.destination.exists())
 def test_total_limit_stops_before_reading_remaining_artifacts(self):
  with patch.object(self.m,'MAX_TOTAL',1),patch.object(self.m,'_digest',wraps=self.m._digest) as digest,self.assertRaises(ValueError):self.m.import_saved_native(self.request)
  self.assertEqual(digest.call_count,1);self.assertFalse(self.destination.exists())
 def test_opaque_source_path_is_preserved_without_following(self):
  self.reseal(lambda owner:owner['artifact_refs'][0].update(source_path='/nonexistent-private-origin/opaque'))
  original=self.manifest.read_bytes();result=self.m.import_saved_native(self.request)
  self.assertEqual(original,(Path(result['binding']['private_root'])/'review'/DATE/'runs'/self.run/'manifest.json').read_bytes())
 def test_reuse_requires_own_import_schema_and_preserves_timestamp(self):
  result=self.m.import_saved_native(self.request);path=self.destination/'data/native_import.json';receipt=json.loads(path.read_bytes());receipt['schema_version']='UNKNOWN';path.write_text(json.dumps(receipt));commit=self.destination/'import.json';value=json.loads(commit.read_bytes());value['receipt_sha256']=self.sha(path);commit.write_text(json.dumps(value))
  with self.assertRaises(ValueError):self.m.import_saved_native(self.request)
 def test_same_import_reuses_committed_root_without_writes(self):
  first=self.m.import_saved_native(self.request);before=self.snapshot(self.destination);second=self.m.import_saved_native(self.request)
  self.assertEqual(second['status'],'REUSED_SAVED_NATIVE');self.assertEqual(first['binding'],second['binding']);self.assertEqual(first['imported_at'],second['imported_at']);self.assertEqual(before,self.snapshot(self.destination))
 def test_wrong_pins_date_or_run_reject_before_destination_creation(self):
  for change in ({'owner_manifest_sha256':'0'*64},{'owner_receipt_sha256':'0'*64},{'trade_date':'20261012'},{'run_id':'../escape'}):
   with self.subTest(change=change),self.assertRaises(ValueError):self.m.import_saved_native(dict(self.request,**change))
   self.assertFalse(self.destination.exists())
 def test_missing_owner_flag_is_not_invented(self):
  self.reseal(lambda owner:owner.pop('production_allowed'))
  with self.assertRaises(ValueError):self.m.import_saved_native(self.request)
  self.assertNotIn('production_allowed',json.loads(self.manifest.read_bytes()));self.assertFalse(self.destination.exists())
 def test_missing_stockdict_remains_missing(self):
  self.reseal(lambda owner:owner.pop('stockdict_status'));original=self.manifest.read_bytes();result=self.m.import_saved_native(self.request)
  self.assertEqual(original,(Path(result['binding']['private_root'])/'review'/DATE/'runs'/self.run/'manifest.json').read_bytes())
  from v5_shadow.m12_readonly_worker import project
  self.assertIsNone(project(result['binding'])['video']['stockdict_status'])
 def test_failed_native_receipt_cannot_be_success(self):
  receipt=json.loads(self.receipt.read_bytes());receipt['status']='ACQUIRE_FAILED';self.receipt.write_text(json.dumps(receipt));self.request['owner_receipt_sha256']=self.sha(self.receipt)
  with self.assertRaises(ValueError):self.m.import_saved_native(self.request)
  self.assertFalse(self.destination.exists())
 def test_changed_artifact_is_rejected_before_copy(self):
  owner=json.loads(self.manifest.read_bytes());(self.source/owner['artifact_refs'][0]['path']).write_bytes(b'CORRUPTED')
  with self.assertRaises(ValueError):self.m.import_saved_native(self.request)
  self.assertFalse(self.destination.exists())
 def test_source_symlinks_are_rejected(self):
  alias=self.root/'alias';alias.symlink_to(self.source,target_is_directory=True)
  with self.assertRaises(ValueError):self.m.import_saved_native(dict(self.request,source_root=str(alias)))
  owner=json.loads(self.manifest.read_bytes());path=self.source/owner['artifact_refs'][0]['path'];outside=self.root/'outside';outside.write_bytes(path.read_bytes());path.unlink();path.symlink_to(outside)
  with self.assertRaises(ValueError):self.m.import_saved_native(self.request)
  self.assertFalse(self.destination.exists())
 def test_escaping_ref_is_rejected(self):
  self.reseal(lambda owner:owner['artifact_refs'].append(dict(kind='error',path='../outside',sha256='0'*64)))
  with self.assertRaises(ValueError):self.m.import_saved_native(self.request)
  self.assertFalse(self.destination.exists())
 def test_existing_destination_and_overlapping_roots_never_overwrite(self):
  self.destination.mkdir();sentinel=self.destination/'keep';sentinel.write_bytes(b'KEEP')
  with self.assertRaises(ValueError):self.m.import_saved_native(self.request)
  self.assertEqual(sentinel.read_bytes(),b'KEEP')
  with self.assertRaises(ValueError):self.m.import_saved_native(dict(self.request,destination_root=str(self.source/'v5-import')))
  self.assertFalse((self.source/'v5-import').exists())
 def test_interrupted_copy_keeps_unpublished_staging(self):
  actual=self.m._copy_exact;count=0
  def fail(*args,**kwargs):
   nonlocal count
   count+=1
   if count==2:raise OSError('synthetic disk failure')
   return actual(*args,**kwargs)
  with patch.object(self.m,'_copy_exact',side_effect=fail),self.assertRaises(ValueError):self.m.import_saved_native(self.request)
  self.assertFalse((self.destination/'data').exists());self.assertFalse((self.destination/'import.json').exists())
  with self.assertRaises(ValueError):self.m.import_saved_native(self.request)
 def test_copied_artifact_tamper_is_rejected_before_publication(self):
  actual=self.m._copy_exact
  def tamper(source,target,*args,**kwargs):
   result=actual(source,target,*args,**kwargs)
   if str(target).endswith('asr/raw_path'):Path(target).write_bytes(b'TAMPERED')
   return result
  with patch.object(self.m,'_copy_exact',side_effect=tamper),self.assertRaises(ValueError):self.m.import_saved_native(self.request)
  self.assertFalse((self.destination/'data').exists());self.assertFalse((self.destination/'import.json').exists())
 def test_source_change_after_copy_cannot_publish(self):
  actual=self.m._cold_check
  def change(binding):
   actual(binding);self.manifest.write_bytes(self.manifest.read_bytes()+b' ')
  with patch.object(self.m,'_cold_check',side_effect=change),self.assertRaises(ValueError):self.m.import_saved_native(self.request)
  self.assertFalse((self.destination/'data').exists());self.assertFalse((self.destination/'import.json').exists())
 def test_failed_promotion_keeps_complete_stage_unbound(self):
  actual=self.m.os.rename
  def fail(source,target,*args,**kwargs):
   if Path(source)==self.destination/'staging':raise OSError('synthetic rename failure')
   return actual(source,target,*args,**kwargs)
  with patch.object(self.m.os,'rename',side_effect=fail),self.assertRaises(ValueError):self.m.import_saved_native(self.request)
  self.assertTrue((self.destination/'staging/native_import.json').is_file());self.assertFalse((self.destination/'data').exists());self.assertFalse((self.destination/'import.json').exists())
 def test_failed_commit_after_promotion_returns_no_binding_and_cannot_reuse(self):
  self.m.verify_runtime()
  from v5_shadow import video_fupan_store as store
  actual=store.safe_replace_json
  def fail(path,value):
   if Path(path)==self.destination/'import.json':raise OSError('synthetic commit failure')
   return actual(path,value)
  with patch.object(store,'safe_replace_json',side_effect=fail),self.assertRaises(ValueError):self.m.import_saved_native(self.request)
  self.assertTrue((self.destination/'data/native_import.json').is_file());self.assertFalse((self.destination/'import.json').exists())
  before=self.snapshot(self.destination)
  with self.assertRaises(ValueError):self.m.import_saved_native(self.request)
  self.assertEqual(before,self.snapshot(self.destination))

if __name__=='__main__':unittest.main()
