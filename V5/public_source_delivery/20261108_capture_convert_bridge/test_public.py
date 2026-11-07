import unittest,datetime,types,sys,tempfile,os
from pathlib import Path
from unittest.mock import Mock,patch
import pipeline as p
# Explicit synthetic substitute for excluded previously published workflow dependency.
fake=types.ModuleType('workflow_node_api');fake.checked=Mock(return_value=b'')
with patch.dict(sys.modules,{'workflow_node_api':fake}):import controlled_node_execution as c
class Tests(unittest.TestCase):
 def test_unbound_pipeline_refuses(self):
  with self.assertRaisesRegex(ValueError,'NO_APPROVED'):p.run({},'capture_convert')
 def test_empty_trust_refuses(self):
  with self.assertRaisesRegex(ValueError,'NO_APPROVED'):c.dispatch('daily-update','SYNTHETIC','SYNTHETIC',lambda:None)
 def test_stage_requires_independent_inputs(self):
  with patch.object(c,'load')as load:
   for reg in [{},{'stage':'capture_convert','binding_ref':{'synthetic':True}},{'stage':'prepare','binding_ref':{'synthetic':True}}]:
    r=c.dispatch_daily_capture(reg,{},lambda:None);self.assertFalse(r['pipeline_called']);self.assertFalse(r['source_admission'])
   load.assert_not_called()
 def test_each_stage_no_automatic_next(self):
  for stage,keys in [('capture_convert',['capture_review','conversion_review']),('prepare',['prepare_config','prepare_review'])]:
   reg=dict(stage=stage,binding_ref={'synthetic':True},run_id='SYNTHETIC',environment_id='SYNTHETIC',**{k:{'synthetic':True} for k in keys});module=Mock();module.run.return_value={'synthetic':True}
   with patch.object(c,'load',return_value=module):r=c.dispatch_daily_capture(reg,{'code':{},'scope':'SYNTHETIC'},lambda:None)
   module.run.assert_called_once_with(reg['binding_ref'],stage,**{k:reg[k]for k in keys});self.assertFalse(r['automatic_next_stage']);self.assertFalse(r['source_admission'])
 def test_window(self):
  cal={'target_date':20000103,'observation_date':20000104}
  with self.assertRaisesRegex(ValueError,'TARGET_SESSION'):p.window(cal,datetime.datetime(2000,1,3,7,29,tzinfo=datetime.timezone.utc))
  p.window(cal,datetime.datetime(2000,1,3,7,30,tzinfo=datetime.timezone.utc))
 def test_guard_resource_refuses_before_write(self):
  cap=types.SimpleNamespace(measure_resources=lambda root:(1,1),new_json=Mock(),portable=types.SimpleNamespace(resource_check=lambda *a,**k:{'passed':False}));p.install_guarded_writes(cap,None,lambda:None,['prepare',None])
  with self.assertRaisesRegex(ValueError,'RECEIPT_RESOURCE_GATE'):cap.new_json(0,'RECEIPT.json',{})
 def test_guard_missing_migration_lock_refuses(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);fd=os.open(root,os.O_RDONLY);writer=Mock();cap=types.SimpleNamespace(measure_resources=lambda root:(1,1),new_json=writer,portable=types.SimpleNamespace(resource_check=lambda *a,**k:{'passed':True}),_migration_verifier=None,_initializing=False)
   try:
    with patch.object(p,'ROOT',root):
     p.install_guarded_writes(cap,None,lambda:None,['prepare',None])
     with self.assertRaisesRegex(ValueError,'MIGRATION_LOCK_NOT_HELD'):cap.new_json(fd,'RECEIPT.json',{})
    writer.assert_not_called()
   finally:os.close(fd)
if __name__=='__main__':unittest.main()
