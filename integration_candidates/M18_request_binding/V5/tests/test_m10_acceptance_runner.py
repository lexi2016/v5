"""Synthetic Git controls for fixed-commit acceptance provenance."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import run_m10_readonly_acceptance as acceptance


class M10AcceptanceRunnerTests(unittest.TestCase):
    def test_fixed_commit_requires_clean_tracked_and_untracked_sources(self):
        with tempfile.TemporaryDirectory(prefix='m10-git-test-') as temp:
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


if __name__=='__main__':unittest.main()
