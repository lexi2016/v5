import ast
import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest
from test_rebound_pytdx_window import ROOT

class PrepareWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path=ROOT/'preparation/prepare_pytdx_window.py'
    def test_offline_cli_exists_with_journal_context_and_plan_sha_inputs(self):
        self.assertTrue(self.path.exists(),'offline journal-to-window preparation CLI is missing')
        result=subprocess.run([sys.executable,'-B',str(self.path),'--help'],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        for option in ['--batch-helper','--capture-helper','--plan-sha256','--context-file','--capture-dir','--output-dir']:
            self.assertIn(option,result.stdout)
    def test_preparation_does_not_call_owner_or_connector_or_rewrite_input(self):
        self.assertTrue(self.path.exists())
        tree=ast.parse(self.path.read_text())
        called={n.func.attr if isinstance(n.func,ast.Attribute) else n.func.id for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,(ast.Name,ast.Attribute))}
        self.assertFalse(called & {'run_rebound_owner','capture_plan','_connect','get_instrument_bars','connect','unlink','remove','replace'})
        self.assertTrue({'_validated','_Journal','_state','_check_context_unchanged'}<=called)

if __name__=='__main__':unittest.main()

class PrepareJournalIntegrationTests(unittest.TestCase):
    def test_pinned_batch_journal_to_manifest_request_with_parquet_seam(self):
        import os,shutil
        from test_rebound_pytdx_window import BASE,RUNTIME_SRC
        runtime=ROOT/'test-runtime/V5'
        if not runtime.exists():shutil.copytree(BASE,runtime)
        for name in ('rebound_owner.py','rebound_pytdx_window.py'):
            shutil.copy2(RUNTIME_SRC/'v5_shadow'/name,runtime/'src/v5_shadow'/name)
        batch=os.environ.get('M14_BATCH_MODULE','/workspace/shared/m14-history-batch-20261014/delivery/integration_candidates/M14_history_batch/batch/rebound_history_batch.py')
        helper=os.environ.get('M14_CAPTURE_HELPER','/workspace/shared/m14-history-recovery-20261014/delivery/integration_candidates/M14_history_recovery/capture/v5_shadow/rebound_history_capture.py')
        env=dict(os.environ,M14_WINDOW_RUNTIME=str(runtime),M14_ORIGINAL_RUNTIME=str(BASE),M14_BATCH_MODULE=batch,M14_CAPTURE_HELPER=helper,PYTHONDONTWRITEBYTECODE='1')
        result=subprocess.run([sys.executable,'-B',str(ROOT/'tests/prepare_journal_probe.py')],capture_output=True,text=True,env=env)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn('PREPARE_SYNTHETIC_JOURNAL_PASS',result.stdout)
