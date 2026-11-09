import unittest,subprocess,sys,pathlib,io
import run_r02_acceptance as r
class StrictRunner(unittest.TestCase):
 def test_skip_rejected_even_when_unittest_successful(self):
  class Skipped(unittest.TestCase):
   @unittest.skip('synthetic policy probe')
   def test_one(self):pass
  result=unittest.TextTestRunner(stream=io.StringIO()).run(unittest.defaultTestLoader.loadTestsFromTestCase(Skipped))
  self.assertTrue(result.wasSuccessful());self.assertFalse(r.acceptable(result))
 def test_zero_tests_rejected(self):
  result=unittest.TestResult();self.assertFalse(r.acceptable(result))
 def test_missing_package_argument_is_failure(self):
  result=subprocess.run([sys.executable,str(pathlib.Path(r.__file__))],capture_output=True,text=True)
  self.assertNotEqual(result.returncode,0)
 def test_missing_dependencies_are_failure(self):
  import tempfile
  with tempfile.TemporaryDirectory() as tmp:
   result=subprocess.run([sys.executable,str(pathlib.Path(r.__file__)),'--package-root',tmp],capture_output=True,text=True)
  self.assertEqual(result.returncode,2);self.assertIn('BLOCKED_PREFLIGHT',result.stdout)
if __name__=='__main__':unittest.main()
