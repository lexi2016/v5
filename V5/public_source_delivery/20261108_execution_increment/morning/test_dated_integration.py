import unittest,os,pathlib,shutil,tempfile,importlib.util,json
from test_dated_scope import fixture,PREP_PATH
class Integration(unittest.TestCase):
 def test_packaged_calculate(self):
  package=os.environ.get('MORNING_PACKAGE_ROOT')
  if not package:self.skipTest('explicit existing package root required')
  with tempfile.TemporaryDirectory() as tmp:
   root=pathlib.Path(tmp)/'public_source_delivery';shutil.copytree(package,root);here=root/'20261108_execution_increment/morning';local=pathlib.Path(__file__).parent
   for name in ('registered.py','code_bindings.json'):shutil.copyfile(local/name,here/name)
   shutil.copyfile(PREP_PATH,root/'handoff/preopen_top200_group_review_20261107/prepare.py')
   spec=importlib.util.spec_from_file_location('packaged_dated',here/'registered.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
   top,panel,scope=fixture();reg={'node':'opening-prep','source_date':'20261109','business_date':'20261109','cutoff':'2026-11-09T08:50:00+08:00'};policy={'top_schema':top['schema']};docs={'top':top,'panel':panel,'pool_scope':scope}
   x=m.calculate(reg,policy,docs,m.module('safeio'))
   self.assertEqual(x['status'],'LIST_AND_PROMPT_READY');self.assertEqual(len(x['rows']),200);self.assertFalse(x['monitor_list_frozen']);self.assertEqual(x['delivery_status'],'NOT_SENT');self.assertIn('000001.SZ',x['prompt']);self.assertEqual(top['schema'],'DATED_FIXED_REFERENCE_TOP200_V1')
   del docs['pool_scope']
   with self.assertRaises(KeyError):m.calculate(reg,policy,docs,m.module('safeio'))
if __name__=='__main__':unittest.main()
