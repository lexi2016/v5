"""Launch existing module API outside repo cwd with synthetic saved artifacts."""
import json
import os
from pathlib import Path
import select
import subprocess
import sys
import unittest
from urllib.request import urlopen
import test_m14_saved_rebound as fixture


class StandaloneSavedLaunchTests(unittest.TestCase):
    setUp = fixture.M14SavedTests.setUp
    snapshot = fixture.M14SavedTests.snapshot

    def test_module_cli_in_fresh_process_only_reads_exact_synthetic_reference(self):
        config = self.root/'source-api.json';config.write_text(json.dumps(self.config))
        before = self.snapshot()
        checkout = Path(__file__).resolve().parents[2]
        # The command uses the existing module entry; no app dependencies or
        # provider setup are installed, and no original owner is executed.
        command = [sys.executable, '-B', '-c',
                   "import sys;sys.dont_write_bytecode=True;sys.path.insert(0,sys.argv.pop(1));"
                   "from v5_shadow.module_api import main;main()",
                   str(checkout/'V5/src'), '--config', str(config), '--port', '0']
        process = subprocess.Popen(command, cwd=self.root, env={'PATH':os.defpath,'PYTHONDONTWRITEBYTECODE':'1'},
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            self.assertTrue(select.select([process.stdout],[],[],10)[0], 'module launch timed out')
            url = process.stdout.readline().strip()
            self.assertTrue(url.startswith('http://127.0.0.1:'),url)
            with urlopen(url+fixture.ROUTE+'?group=pending',timeout=10) as response:
                page=json.load(response)
            self.assertEqual(page['reference'],self.reference)
            self.assertEqual(page['rebound']['group_counts']['pending'],70)
            self.assertEqual(page['entries'][0]['value']['code'],'HK.00000')
            self.assertFalse(page['natural_verified'])
        finally:
            process.terminate()
            _,error=process.communicate(timeout=10)
        self.assertEqual(error,'')
        self.assertEqual(before,self.snapshot())

if __name__=='__main__':unittest.main()
