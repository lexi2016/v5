"""Synthetic Git controls for fixed-commit acceptance provenance."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import run_m09_readonly_acceptance as acceptance


class M09AcceptanceRunnerTests(unittest.TestCase):
    def test_fixed_commit_requires_clean_tracked_and_untracked_sources(self):
        with tempfile.TemporaryDirectory(prefix='m09-git-test-') as temp:
            root=Path(temp).resolve();(root/'V5/tests').mkdir(parents=True);source=root/'V5/tests/synthetic.py';source.write_text('value=1\n')
            (root/'frontend').mkdir();html=root/'frontend/index.html';html.write_text('<html>synthetic</html>\n')
            env=dict(os.environ,GIT_CONFIG_NOSYSTEM='1',GIT_CONFIG_GLOBAL=os.devnull)
            def git(*args):
                return subprocess.run(['git',*args],cwd=root,env=env,check=True,capture_output=True,text=True).stdout.strip()
            git('init','-q');git('add','.');git('-c','user.name=Synthetic','-c','user.email=synthetic@example.invalid','commit','-qm','synthetic test')
            head=git('rev-parse','HEAD')
            self.assertEqual(acceptance.verify_checkout(root,head),head)
            html.write_text('<html>changed</html>\n')
            with self.assertRaisesRegex(ValueError,'DIRTY'):acceptance.verify_checkout(root,head)
            html.write_text('<html>synthetic</html>\n')
            source.write_text('value=2\n')
            with self.assertRaisesRegex(ValueError,'DIRTY'):acceptance.verify_checkout(root,head)
            source.write_text('value=1\n');extra=root/'V5/tests/extra.py';extra.write_text('value=3\n')
            with self.assertRaisesRegex(ValueError,'UNTRACKED'):acceptance.verify_checkout(root,head)
            extra.unlink()
            with self.assertRaisesRegex(ValueError,'MISMATCH'):acceptance.verify_checkout(root,'0'*40)

    def test_worker_runtime_is_probed_and_unsupported_binding_cannot_pass(self):
        import json
        from unittest.mock import patch
        self.assertTrue(hasattr(acceptance,'worker_environment'),'The bound Python must be checked independently')
        with patch.object(acceptance.subprocess,'run',return_value=subprocess.CompletedProcess([],0,
                json.dumps(dict(python='3.12.14',pandas='2.2.3',supported=False)),'')) as probe:
            worker=acceptance.worker_environment('/existing/python')
        self.assertEqual(probe.call_args.args[0][:3],['/existing/python','-I','-B'])
        self.assertFalse(worker['supported'])
        with self.assertRaisesRegex(ValueError,'SUPPORTED'):
            acceptance.require_supported_environments(dict(supported=True),worker)
        with self.assertRaisesRegex(ValueError,'SUPPORTED'):
            acceptance.require_supported_environments(dict(supported=False),dict(supported=True))
        acceptance.require_supported_environments(dict(supported=True),dict(supported=True))


if __name__=='__main__':unittest.main()
