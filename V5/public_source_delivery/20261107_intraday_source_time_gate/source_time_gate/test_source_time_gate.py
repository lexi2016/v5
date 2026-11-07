import ast,copy,unittest
from pathlib import Path
from source_time_gate import partition_materials,validate_availability
class Tests(unittest.TestCase):
 def setUp(self):self.row={k:'2026-11-07T08:00:00+08:00' for k in ('event_time','published_at','observed_at','available_at')};self.cutoff='2026-11-07T08:10:00+08:00'
 def test_on_time(self):self.assertEqual(len(partition_materials([self.row],self.cutoff)['on_time']),1)
 def test_late_preserved(self):
  self.row['available_at']='2026-11-07T08:11:00+08:00';r=partition_materials([self.row],self.cutoff);self.assertEqual(r['late'][0]['record'],self.row)
 def test_missing(self):
  del self.row['published_at'];self.assertEqual(len(partition_materials([self.row],self.cutoff)['unknown']),1)
 def test_naive(self):
  self.row['available_at']='2026-11-07T08:00:00';self.assertEqual(len(partition_materials([self.row],self.cutoff)['unknown']),1)
 def test_bad_order(self):
  self.row['observed_at']='2026-11-07T08:01:00+08:00';self.assertEqual(len(partition_materials([self.row],self.cutoff)['unknown']),1)
 def test_exact_cutoff(self):
  self.row['available_at']=self.cutoff;self.assertTrue(validate_availability([self.row],self.cutoff))
 def test_no_materials_blocked(self):self.assertEqual(partition_materials([],self.cutoff)['status'],'BLOCKED_NO_MATERIALS')
 def test_record_unchanged(self):
  old=copy.deepcopy(self.row);partition_materials([self.row],self.cutoff);self.assertEqual(old,self.row)
 def test_original_ast_unchanged(self):
  root=Path(__file__).parent
  for name in ('_time','validate_availability'):
   a=[x for x in ast.parse((root/'original_time_predicates.py').read_text()).body if isinstance(x,ast.FunctionDef) and x.name==name][0]
   b=[x for x in ast.parse((root/'source_time_gate.py').read_text()).body if isinstance(x,ast.FunctionDef) and x.name==name][0]
   self.assertEqual(ast.dump(a),ast.dump(b))
if __name__=='__main__':unittest.main()
