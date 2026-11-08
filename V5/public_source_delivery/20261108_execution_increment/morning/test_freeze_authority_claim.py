import unittest,os,pathlib,tempfile,shutil,importlib.util
from test_freeze_fact_timing import fixture
from test_panel_freshness import add_contract
class AuthorityClaim(unittest.TestCase):
 def test_real_crosscheck_and_freeze_branch(self):
  package=os.environ.get('MORNING_PACKAGE_ROOT')
  if not package:self.skipTest('explicit package root required')
  with tempfile.TemporaryDirectory() as tmp:
   root=pathlib.Path(tmp)/'public';shutil.copytree(package,root);here=root/'20261108_execution_increment/morning';shutil.copyfile(pathlib.Path(__file__).with_name('registered.py'),here/'registered.py')
   spec=importlib.util.spec_from_file_location('frozen_fact_module',here/'registered.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
   multi,policy,cutoff=fixture();groups=('original','nav_smallk','nav_pullback','nav_breakout')
   panel={'schema':'PAR_SCREEN_DISPLAY_V1','source_date':'20261106','scope_count':1,'partitions':{'COMPUTED_CURRENT':1},'dedup_selected':0,'dedup_pending':1,'counts':{g:{'after_risk':{'TRUE':0,'FALSE':0,'UNKNOWN':1}} for g in groups},'rows':[{'symbol':'000001.SZ','owner_outcome':'COMPUTED_CURRENT','source_family':'SYNTHETIC','actual_date':'20261106','layers':{g:{'after_risk':'UNKNOWN'} for g in groups}}]}
   policy['panel_denominator']=1
   policy['freeze_chain']={'schema':'FREEZE_CHAIN_POLICY_V1','version':'SYNTHETIC_V1','mode':'GENESIS','expected_parent_identity':None}
   reg={'node':'freeze','run_id':'SYNTHETIC','environment_id':'TEMP','domain':'production','business_date':'20261109','source_date':'20261106','cutoff':cutoff.isoformat(),'inputs':{},'policy':{},'review':{},'owner_identity':'SYNTHETIC','output_relative':'unused','adapter_sha256':m.sha((here/'registered.py').read_bytes())}
   docs={'panel':panel,'multi_source':multi,'freeze_changes':{'000001.SZ':'SYNTHETIC initial snapshot'}};add_contract(reg,policy,docs);safe=m.module('safeio');x=m.calculate(reg,policy,docs,safe)
   self.assertEqual(x['status'],'REVIEWED_FREEZE_MANIFEST_READY');self.assertFalse(x['formal_freeze']);self.assertEqual(x['row_audit']['pending_count'],1)
   parent=x['lineage'];policy['freeze_chain'].update(mode='DELTA',version='SYNTHETIC_V2',expected_parent_identity=parent['identity']);docs['freeze_parent']=parent;docs['freeze_changes']={};y=m.calculate(reg,policy,docs,safe);self.assertEqual(y['lineage']['changes'],[]);self.assertEqual(y['lineage']['parent_identity'],parent['identity'])
   multi['sources']['s1']['facts'][0]['available_at']='2026-11-09T06:31:00+08:00'
   with self.assertRaises(ValueError):m.calculate(reg,policy,docs,safe)
if __name__=='__main__':unittest.main()
