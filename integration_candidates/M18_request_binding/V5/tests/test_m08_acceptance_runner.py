import subprocess,unittest
from unittest.mock import patch
import run_m08_readonly_acceptance as acceptance
class M08AcceptanceRunnerTests(unittest.TestCase):
 def test_bound_python_is_probed_without_installing(self):
  with patch.object(acceptance.subprocess,'run',return_value=subprocess.CompletedProcess([],0,'{"python":"3.12.14","supported":false}','')) as probe:
   self.assertFalse(acceptance.probe('/existing/python')['supported']);self.assertEqual(probe.call_args.args[0][:3],['/existing/python','-I','-B'])
 def test_failed_runtime_probe_cannot_pass(self):
  with patch.object(acceptance.subprocess,'run',return_value=subprocess.CompletedProcess([],1,'','')):
   with self.assertRaisesRegex(ValueError,'PROBE_FAILED'):acceptance.probe('/existing/python')
 def test_real_acceptance_requires_commit_baseline_and_frontend(self):
  with patch('sys.argv',['accept','--source-config','private.json','--evidence-dir','unused']):
   with self.assertRaises(SystemExit) as ctx:acceptance.main()
   self.assertEqual(ctx.exception.code,2)
