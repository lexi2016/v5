import unittest,json,tempfile,hashlib
from pathlib import Path
from unittest.mock import patch,Mock
import controlled_node_execution as c
import workflow_node_api as w
M=json.loads(Path(__file__).with_name('NODE_MATRIX.json').read_text())['nodes']
class Tests(unittest.TestCase):
 def entries(self):return {r['node']:{'code':{'path':'synthetic.py','sha256':'0'*64},'scope':'SYNTHETIC_ONLY'} for r in M}
 def test_21_unique_paths(self):self.assertEqual(len(M),21);self.assertEqual(len({r['node'] for r in M}),21)
 def test_default_unbound(self):
  for node in [r['node'] for r in M]:
   with self.assertRaisesRegex(ValueError,'NO_APPROVED'):c.dispatch(node,'SYNTHETIC','SYNTHETIC',lambda:None)
  with self.assertRaisesRegex(ValueError,'NO_APPROVED'):w.WorkflowNodeService(lambda:None).get('night','20000101','inspect')
 def test_empty_trust_all_21_no_execution(self):
  with patch.object(c,'bindings',return_value=self.entries()),patch.object(c,'checked',return_value=b''),patch.object(c,'load')as load:
   for node in self.entries():
    r=c.dispatch(node,'SYNTHETIC','SYNTHETIC',lambda:None);self.assertEqual(r['status'],'BLOCKED_NO_TRUSTED_EXECUTOR_BINDING');self.assertFalse(r['business_accepted'])
   load.assert_not_called()
 def test_synthetic_21_dispatch_groups(self):
  entries=self.entries()
  for row in M:
   node=row['node'];reg=dict(node=node,run_id='SYNTHETIC',environment_id='SYNTHETIC',adapter_sha256='0'*64,mode='SYNTHETIC',run_key='SYNTHETIC',automation_id='SYNTHETIC',config_ref={},review_ref={},contract_ref={});module=Mock();gate=Mock()
   with self.subTest(node=node),patch.object(c,'bindings',return_value=entries),patch.object(c,'TRUSTED_RUNS',(reg,)),patch.object(c,'load',return_value=module),patch.object(c,'dispatch_m07',return_value={'synthetic':True})as m07,patch.object(c,'dispatch_remaining',return_value={'synthetic':True})as remaining,patch.object(c,'dispatch_evening',return_value={'synthetic':True})as evening:
    c.dispatch(node,'SYNTHETIC','SYNTHETIC',gate);gate.assert_called_once();self.assertFalse(c.LOCK.locked())
    selected={'m07':m07,'remaining':remaining,'evening':evening}.get(row['dispatch_group'])
    if selected:selected.assert_called_once()
    else:
     self.assertEqual(module.method_calls.__len__(),1)
 def test_resource_and_pin_failure(self):
  reg=dict(node='daily-update',run_id='SYNTHETIC',environment_id='SYNTHETIC',adapter_sha256='0'*64)
  with patch.object(c,'bindings',return_value=self.entries()),patch.object(c,'TRUSTED_RUNS',(reg,)),patch.object(c,'load')as load:
   with self.assertRaisesRegex(ValueError,'RESOURCE'):c.dispatch('daily-update','SYNTHETIC','SYNTHETIC',Mock(side_effect=ValueError('RESOURCE')))
   self.assertFalse(c.LOCK.locked());load.assert_not_called();reg['adapter_sha256']='1'*64
   with self.assertRaisesRegex(ValueError,'CODE_BINDING_CHANGED'):c.dispatch('daily-update','SYNTHETIC','SYNTHETIC',lambda:None)
 def test_research_list_prompt_only(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t)
   def pin(name,data):
    raw=json.dumps(data).encode();(root/name).write_bytes(raw);return dict(path=name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
   contract=pin('contract.json',{});research=pin('research.json',{'rows':[{'symbol':'SYNTHETIC'+str(i),'rank':i,'actual_date':'20000101'}for i in range(200)]})
   registry={'contract':contract,'research_list':research,'nodes':{'night':{'code_refs':[],'historical_refs':{},'definition':'SYNTHETIC','missing_current':['UNBOUND']}}}
   with patch.multiple(w,ROOT=root,REGISTRY=registry,HISTORY_DATE='20000101'),patch.object(c,'inspect',return_value={'status':'SYNTHETIC_BLOCKED'}):r=w.WorkflowNodeService(lambda:None).get('night','20000102','research_request')
   self.assertEqual(r['research_request']['count'],200);self.assertEqual(r['research_request']['external_requests_sent'],0);self.assertFalse(r['execution_enabled']);self.assertFalse(r['research_request']['list_is_current'])
 def test_source_tamper_refuses(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);(root/'a').write_bytes(b'x')
   with patch.object(w,'ROOT',root):
    with self.assertRaisesRegex(ValueError,'SOURCE_PIN_CHANGED'):w.checked({'path':'a','bytes':1,'sha256':'0'*64})
if __name__=='__main__':unittest.main()
