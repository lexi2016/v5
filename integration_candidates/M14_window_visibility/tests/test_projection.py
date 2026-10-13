import copy,importlib.util,unittest
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'files/V5/src/v5_shadow/m14_readonly.py'
spec=importlib.util.spec_from_file_location('v5_shadow.m14_visibility_candidate',p);m=importlib.util.module_from_spec(spec)
import sys
sys.modules[spec.name]=m;spec.loader.exec_module(m)
class Projection(unittest.TestCase):
 def state(self,native):
  artifact={'formal_status':'WAITING','run_id':'a'*32,'reason_codes':[],**m.SAFETY}
  observation={'coverage':{'panel_row_count':40930,'panel_code_count':690},'native_evidence':native}
  before=copy.deepcopy(observation)
  result=m._state(artifact,observation,m.SavedBinding(Path('/unused'),{'run_id':'a'*32}),{})
  self.assertEqual(before,observation)
  return result['observation']
 def test_saved_fields_and_private_filter(self):
  native={'research_cutoff':'2026-10-13T18:40:58.776354Z','source_contract':{'name':'SYNTHETIC_TEST','provider':'PYTDX_EXHQ_SDK','volume_unit':None,'private_root':'/secret','endpoint':'not_projected'},'pending_reasons':{'HK.00376':['SOURCE_ROW_INVALID'],'HK.00001':['PRIOR60_KEYS_MISSING']}}
  o=self.state(native);self.assertEqual(o['coverage']['panel_row_count'],40930);self.assertEqual(o['native_evidence']['research_cutoff'],native['research_cutoff']);self.assertEqual(o['native_evidence']['pending_reasons'],native['pending_reasons']);self.assertNotIn('private_root',o['native_evidence']['source_contract']);self.assertNotIn('endpoint',o['native_evidence']['source_contract'])
 def test_missing_stays_missing(self):
  o=self.state({});self.assertNotIn('research_cutoff',o['native_evidence']);self.assertNotIn('pending_reasons',o['native_evidence'])
 def test_invalid_reason_shape_fails_closed(self):
  for reasons in [{'__proto__':[]},{'HK.00001':'not-list'},{'HK.00001':[{'path':'/secret'}]}]:
   with self.assertRaises(m.M14ReadonlyError):self.state({'pending_reasons':reasons})
 def test_private_path_in_allowed_value_redacted(self):
  o=self.state({'source_contract':{'name':'/secret'},'pending_reasons':{'HK.00001':['/secret']}});self.assertEqual(o['native_evidence']['source_contract']['name'],'[PRIVATE_PATH_REDACTED]');self.assertEqual(o['native_evidence']['pending_reasons']['HK.00001'],['[PRIVATE_PATH_REDACTED]'])
if __name__=='__main__':unittest.main()
