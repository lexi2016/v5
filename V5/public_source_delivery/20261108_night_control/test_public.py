import importlib.util,pathlib,sys,types,unittest
from unittest.mock import patch
HERE=pathlib.Path(__file__).resolve().parent

def load(name,path):
 s=importlib.util.spec_from_file_location(name,HERE/path);m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m
class Tests(unittest.TestCase):
 def controller(self):
  stub=types.ModuleType('workflow_node_api');stub.checked=lambda pin:b'# synthetic only'
  with patch.dict(sys.modules,{'workflow_node_api':stub}):return load('public_control','controlled_node_execution.py')
 def test_missing_bindings(self):
  m=self.controller()
  with self.assertRaisesRegex(ValueError,'NO_APPROVED'):m.bindings()
 def test_resource_required(self):
  m=self.controller()
  with self.assertRaisesRegex(ValueError,'RESOURCE'):m.dispatch('night','r','e',None)
 def test_handoff_unregistered(self):
  m=load('public_night','night_handoff.py');m.load_safe=lambda _:self.fail('must not load')
  for n in m.NODES:
   r=m.dispatch(n,'r','e');self.assertEqual(r['status'],'BLOCKED');self.assertEqual(r['source_calls'],0)
 def test_only_identity_forwarded(self):
  m=self.controller();m.ROOT=HERE;m.ADAPTER_BINDINGS={n:{'code':{'path':'synthetic.py','sha256':'x'},'scope':'SYNTHETIC'} for n in ('night','morning-materials')}
  m.TRUSTED_RUNS=tuple({'node':n,'run_id':'r','environment_id':'e','adapter_sha256':'x'} for n in m.ADAPTER_BINDINGS)
  calls=[];m.load=lambda _:types.SimpleNamespace(dispatch=lambda *a:calls.append(a) or {'status':'BLOCKED'})
  for n in m.ADAPTER_BINDINGS:
   x=m.dispatch(n,'r','e',lambda:None);self.assertFalse(x['business_accepted']);self.assertFalse(x['natural_verified'])
  self.assertEqual(calls,[('night','r','e'),('morning-materials','r','e')])
 def test_daily_internal_kernel_refuses(self):
  m=self.controller();m.ROOT=HERE
  for stage in ('compute','persist','finalize','select','compute_persist'):
   r=m.dispatch_daily_capture({'stage':stage},{},lambda:None);self.assertEqual(r['status'],'BLOCKED_ORIGINAL_RUNTIME_E1_OWNER_BINDING');self.assertFalse(r['kernel_called'])
if __name__=='__main__':unittest.main()
