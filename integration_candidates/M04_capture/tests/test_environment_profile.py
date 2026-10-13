import json,sys,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import environment_profile as env

class EnvironmentProfileTests(unittest.TestCase):
 def test_exact_capture_profile_imports_actual_dependency_modules(self):
  modules={'pandas':SimpleNamespace(__version__='2.3.3'),'pyarrow':SimpleNamespace(__version__='23.0.1'),'pyarrow.dataset':object(),'pyarrow.parquet':object()}
  with patch.object(env.platform,'python_implementation',return_value='CPython'),patch.object(env.platform,'python_version',return_value='3.13.12'),patch.object(env.importlib,'import_module',side_effect=modules.__getitem__) as load:
   result=env.check_environment();self.assertEqual(result['status'],'M04_ENVIRONMENT_MATCHED');self.assertEqual(load.call_count,4)
   self.assertEqual(result['official_cli_fulltext'],'UNVERIFIED')
 def test_untested_python_rejected_before_dependency_import(self):
  with patch.object(env.platform,'python_version',return_value='3.14.6'),patch.object(env.importlib,'import_module') as load:
   with self.assertRaisesRegex(RuntimeError,'PYTHON_UNTESTED'):env.check_environment()
   load.assert_not_called()
 def test_dependency_drift_rejected(self):
  with patch.object(env.platform,'python_version',return_value='3.13.12'),patch.object(env.importlib,'import_module',return_value=SimpleNamespace(__version__='3.0.5')):
   with self.assertRaisesRegex(RuntimeError,'VERSION_UNTESTED:pandas'):env.check_environment()
 def test_dependency_import_failure_rejected(self):
  with patch.object(env.platform,'python_version',return_value='3.13.12'),patch.object(env.importlib,'import_module',side_effect=ImportError('synthetic')):
   with self.assertRaisesRegex(RuntimeError,'IMPORT_FAILED:pandas'):env.check_environment()
 def test_readonly_does_not_require_or_import_dependencies(self):
  for version in ('3.12.14','3.13.12','3.14.6'):
   with self.subTest(version=version),patch.object(env.platform,'python_version',return_value=version),patch.object(env.importlib,'import_module') as load:
    self.assertEqual(env.check_environment('readonly')['status'],'M04_ENVIRONMENT_MATCHED');load.assert_not_called()
 def test_launcher_rejects_environment_before_stdin_or_capture(self):
  import launch
  with patch.object(sys,'argv',['launch.py','capture','--execute-acquisition']),patch.object(env,'check_environment',side_effect=RuntimeError('M04_ENVIRONMENT_IMPORT_FAILED:synthetic')),patch.object(sys,'stdin') as stdin,patch.object(launch.runtime,'capture') as capture,patch('builtins.print'):
   self.assertEqual(launch.main(),1);stdin.buffer.read.assert_not_called();capture.assert_not_called()
