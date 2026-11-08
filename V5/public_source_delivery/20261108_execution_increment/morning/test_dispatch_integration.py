"""Synthetic in-memory registry only; real existing verify/module/freeze, no production binding."""
import contextlib, hashlib, importlib.util, json, os, pathlib, shutil, tempfile, unittest
from test_assembly_preview import fixture
class DispatchIntegration(unittest.TestCase):
 def test_actual_dispatch_readback_and_reuse(self):
  root=os.environ.get('MORNING_PACKAGE_ROOT')
  if not root:self.skipTest('requires explicit existing morning package root')
  with tempfile.TemporaryDirectory() as tmp:
   target=pathlib.Path(tmp)/'public_source_delivery';shutil.copytree(root,target)
   here=target/'20261108_execution_increment/morning'
   shutil.copyfile(pathlib.Path(__file__).with_name('registered.py'),here/'registered.py')
   spec=importlib.util.spec_from_file_location('isolated_morning_dispatch',here/'registered.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
   reg,policy,docs=fixture();events=[]
   @contextlib.contextmanager
   def guard(identity):
    self.assertEqual(identity,'SYNTHETIC_TEST_OWNER');events.append('enter')
    try:yield
    finally:events.append('exit')
   def write(name,doc):
    raw=m.canonical(doc);p=target/name;p.write_bytes(raw);return {'path':name,'bytes':len(raw),'sha256':m.sha(raw)}
   policy.update(node='morning-delivery',domain='synthetic',version=1,original_policy_reference='NEW_SYNTHETIC_TEST_NOT_ORIGINAL_POLICY')
   ref=write('sections.json',docs['assembly_sections']);pit={'business_date':reg['business_date'],'source_date':reg['source_date'],'known_by_cutoff':True,'source_admission':True,'latest_available_at':'2026-11-09T08:01:00+08:00','input_sha256':{'assembly_sections':ref['sha256']}}
   reg.update(run_id='SYNTHETIC_TEST',environment_id='TEMP_ONLY',owner_identity='SYNTHETIC_TEST_OWNER',owner_guard_factory=guard,inputs={'assembly_sections':ref,'pit':write('pit.json',pit)},policy=write('policy.json',policy),output_relative='out',adapter_sha256=m.sha((here/'registered.py').read_bytes()))
   reg['review']=write('review.json',{'verdict':'APPROVED','domain':'synthetic','contract_sha256':m.contract_identity(reg),'independent_reviewer_identity':'SYNTHETIC_TEST_FIXTURE_NOT_REAL_AUTHORITY','policy_sha256':reg['policy']['sha256']})
   m.TRUSTED_RUNS=(reg,) # private module object, never source or live registry
   x=m.dispatch('morning-delivery','SYNTHETIC_TEST','TEMP_ONLY',lambda:events.append('gate'))
   self.assertEqual(x['saved']['byte_readback'],'PASS');saved=pathlib.Path(x['saved']['path']);raw=saved.read_bytes();report=json.loads(raw)
   self.assertEqual(report['result']['status'],'PREVIEW_ASSEMBLED_NOT_ADMITTED');self.assertFalse(report['business_accepted']);self.assertEqual(report['delivery_status'],'NOT_SENT');self.assertEqual(events.count('enter'),1);self.assertEqual(events.count('exit'),1);self.assertGreaterEqual(events.count('gate'),4)
   y=m.dispatch('morning-delivery','SYNTHETIC_TEST','TEMP_ONLY',lambda:None);self.assertTrue(y['saved']['reused']);self.assertEqual(saved.read_bytes(),raw)
if __name__=='__main__':unittest.main()
