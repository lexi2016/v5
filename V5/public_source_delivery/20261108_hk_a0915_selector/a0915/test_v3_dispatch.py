import unittest,tempfile,pathlib,importlib.util,shutil,os,json,hashlib,contextlib
H=pathlib.Path(__file__).resolve().parent
class Dispatch(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.repo=pathlib.Path(self.t.name)/'repo';public=self.repo/'V5/public_source_delivery';entry=public/'20261108_hk_a0915_selector/a0915/execution.py';entry.parent.mkdir(parents=True);shutil.copyfile(H/'execution.py',entry)
  spec=importlib.util.spec_from_file_location('tested_a0915_entry',entry);self.e=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.e)
  safe=public/'handoff/timeline_material_pack_v2_20261107/material_pack.py';safe.parent.mkdir(parents=True);shutil.copyfile(os.environ['SAFEIO_SOURCE'],safe)
  legacy=self.e.ORIGINAL/'safeio.py';legacy.parent.mkdir(parents=True);shutil.copyfile(os.environ['SAFEIO_SOURCE'],legacy)
  self.reader=self.repo/'handoff/reconstruction_candidates_20261108/a0915_text_v3/recorded.py';self.reader.parent.mkdir(parents=True);shutil.copyfile(os.environ['V3_READER_SOURCE'],self.reader)
  self.root=self.repo/'input';self.root.mkdir();self.events=[]
  self.data={'schema':'A0915_RECORDED_DISPLAY_INPUT_V1','market':'A_SHARE','target_date':'20261109','observed_at':'2026-11-09T09:14:00+08:00','available_at':'2026-11-09T09:14:30+08:00','scope':['A.000001','A.000002'],'rows':[{'symbol':'A.000001','observation':'SYNTHETIC ONLY'}],'source_reference':'SYNTHETIC_ONLY','data_kind':'SYNTHETIC_TEST'}
  raw=json.dumps(self.data).encode();(self.root/'input.json').write_bytes(raw);digest=hashlib.sha256(raw).hexdigest();self.policy={'schema':'A0915_TEXT_READER_CONTRACT_V3','target_date':'20261109','scope':self.data['scope'][:],'source_reference':'SYNTHETIC_ONLY','input_sha256':digest,'cutoff':'2026-11-09T09:15:00+08:00','max_age_seconds':120}
  @contextlib.contextmanager
  def owner():
   self.events.append('enter')
   try:yield
   finally:self.events.append('exit')
  self.r={'run_id':'TEST','environment_id':'TEMP','reader_mode':'TEXT_V3_ISOLATED','domain':'synthetic','trigger':'SYNTHETIC_TEST','natural':False,'gate':lambda:self.events.append('gate'),'owner_context':owner,'input_root':self.root,'input_relative':'input.json','input_sha256':digest,'target_date':'20261109','scope':tuple(self.data['scope']),'output':self.repo/'out'};self.pin_policy();self.e.REGISTRY[('TEST','TEMP')]=self.r
 def pin_policy(self):
  raw=json.dumps(self.policy).encode();(self.root/'contract.json').write_bytes(raw);self.r['text_contract']={'path':'contract.json','sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
 def runone(self):return self.e.dispatch('TEST','TEMP')
 def test_actual_entry_original_safeio_freeze_reuse(self):
  x=self.runone();y=self.runone();self.assertEqual(x['status'],'TEXT_V3_RECEIPT_SAVED_BUSINESS_BLOCKED');self.assertEqual(x['saved']['byte_readback'],'PASS');self.assertTrue(y['saved']['reused']);self.assertEqual(x['saved']['sha256'],y['saved']['sha256']);self.assertEqual(self.events,['gate','enter','gate','exit']*2);self.assertEqual(x['report']['result']['missing_symbols'],['A.000002']);self.assertFalse(x['report']['result']['quote_fields_validated']);self.assertEqual(x['report']['source_admission'],'UNKNOWN')
 def test_default_original_still_requires_old_reader(self):
  self.r.pop('reader_mode')
  with self.assertRaises(FileNotFoundError):self.runone()
  self.assertEqual(self.e.PINS['a0915.py'],'be03158ad98d050c6692f035f56e3f2bcb753f22118b6a3dbe838fc941b3433f');self.assertFalse(self.r['output'].exists())
 def test_unregistered_no_work(self):
  self.e.REGISTRY.clear();self.assertEqual(self.runone()['status'],'BLOCKED_UNREGISTERED');self.assertEqual(self.events,[])
 def test_production_and_natural_denied(self):
  self.r['domain']='production'
  with self.assertRaisesRegex(ValueError,'ISOLATED_ONLY'):self.runone()
  self.r['domain']='synthetic';self.r['natural']=True
  with self.assertRaisesRegex(ValueError,'ISOLATED_ONLY'):self.runone()
  self.assertFalse(self.r['output'].exists())
 def test_code_pin_change(self):
  self.reader.write_bytes(self.reader.read_bytes()+b'\n')
  with self.assertRaisesRegex(ValueError,'CODE_PIN'):self.runone()
 def test_contract_identity_bound_to_registry(self):
  self.policy['scope']=['A.000001'];self.pin_policy()
  with self.assertRaisesRegex(ValueError,'REGISTERED_BINDING'):self.runone()
 def test_contract_mutation_before_save(self):
  count=0
  def gate():
   nonlocal count
   count+=1
   if count==2:(self.root/'contract.json').write_bytes(b'{}')
  self.r['gate']=gate
  with self.assertRaisesRegex(ValueError,'CHANGED_BEFORE_SAVE'):self.runone()
  self.assertFalse(self.r['output'].exists());self.assertEqual(self.events,['enter','exit'])
 def test_output_tampering_rejected(self):
  x=self.runone();pathlib.Path(x['saved']['path']).write_bytes(b'{}')
  with self.assertRaises(ValueError):self.runone()
 def test_late_precision_not_bypassed_by_entry(self):
  self.data['available_at']='2026-11-09T09:15:00.0000001+08:00';raw=json.dumps(self.data).encode();(self.root/'input.json').write_bytes(raw);self.r['input_sha256']=hashlib.sha256(raw).hexdigest();self.policy['input_sha256']=self.r['input_sha256'];self.pin_policy()
  with self.assertRaisesRegex(ValueError,'PRECISION'):self.runone()
