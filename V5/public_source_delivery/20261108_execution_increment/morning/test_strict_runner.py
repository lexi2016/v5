import unittest,subprocess,sys,pathlib,io,tempfile
from unittest.mock import patch
import run_r02_acceptance as r
class StrictRunner(unittest.TestCase):
 def result(self,count):
  result=unittest.TestResult();result.testsRun=count;return result
 def test_skip_rejected_even_when_unittest_successful(self):
  result=self.result(1);result.skipped=[('fixture','skip')]
  self.assertTrue(result.wasSuccessful());self.assertFalse(r.acceptable(result,1))
 def test_zero_tests_rejected(self):self.assertFalse(r.acceptable(self.result(0),0))
 def test_missing_package_argument_is_failure(self):
  result=subprocess.run([sys.executable,str(pathlib.Path(r.__file__))],capture_output=True,text=True,timeout=5)
  self.assertNotEqual(result.returncode,0)
 def test_missing_dependencies_are_failure(self):
  with tempfile.TemporaryDirectory() as tmp:
   with self.assertRaisesRegex(ValueError,'DEPENDENCY_MISSING'):r.preflight(pathlib.Path(tmp))
 def test_incomplete_count_rejected(self):self.assertFalse(r.acceptable(self.result(25),26))
 def test_unreviewed_count_growth_rejected(self):self.assertFalse(r.acceptable(self.result(27),26))
 def test_wrong_existing_root_rejected(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=pathlib.Path(tmp);(root/'unrelated.py').write_text('# synthetic')
   with self.assertRaisesRegex(ValueError,'DEPENDENCY_MISSING'):r.preflight(root)
 def test_pin_tamper_rejected(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=pathlib.Path(tmp);(root/'file.py').write_text('# synthetic tamper')
   with patch.object(r,'PINS',{'file.py':'0'*64}):
    with self.assertRaisesRegex(ValueError,'DEPENDENCY_SHA_MISMATCH'):r.preflight(root)
 def test_normal_failure_preserved_and_optimized_still_runs(self):
  with patch.object(r.subprocess,'run',side_effect=[subprocess.CompletedProcess([],1),subprocess.CompletedProcess([],0)]) as run:
   self.assertEqual(r.run_modes(pathlib.Path('/synthetic'),'pass'),[1,0]);self.assertEqual(run.call_count,2)
   self.assertNotIn('-O',run.call_args_list[0].args[0]);self.assertIn('-O',run.call_args_list[1].args[0])
 def test_optimized_failure_preserved(self):
  with patch.object(r.subprocess,'run',side_effect=[subprocess.CompletedProcess([],0),subprocess.CompletedProcess([],1)]) as run:
   self.assertEqual(r.run_modes(pathlib.Path('/synthetic'),'pass'),[0,1]);self.assertEqual(run.call_count,2)
 def test_actual_timeout_is_failure_in_both_modes(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=pathlib.Path(tmp);(root/'20261108_execution_increment/morning').mkdir(parents=True)
   self.assertEqual(r.run_modes(root,'import time;time.sleep(10)',timeout=0.05),[124,124])
 def test_runner_policy_tests_included_in_child(self):
  self.assertEqual(r.EXPECTED_COUNTS['test_strict_runner'],13)
  self.assertIn('test_strict_runner',r.child_code(pathlib.Path('/synthetic')));self.assertIn('TEST_COUNT_MISMATCH',r.child_code(pathlib.Path('/synthetic')))
 def test_module_source_must_match_pinned_root(self):
  code=r.child_code(pathlib.Path('/synthetic'))
  prefix="import sys,types\nm=types.ModuleType('test_panel_freshness');m.__file__='/shadow/test_panel_freshness.py';sys.modules['test_panel_freshness']=m\n"
  result=subprocess.run([sys.executable,'-B','-c',prefix+code],capture_output=True,text=True,timeout=5)
  self.assertNotEqual(result.returncode,0)
  self.assertIn('TEST_MODULE_PATH_MISMATCH:test_panel_freshness',result.stderr)
if __name__=='__main__':unittest.main()
