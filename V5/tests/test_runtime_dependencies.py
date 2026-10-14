"""Locked-runtime checks; M17 imports original owner code, never a provider."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import tomllib
import unittest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / 'src'))
from v5_shadow.health import observe_dependencies


class RuntimeDependenciesTests(unittest.TestCase):
    def test_installed_runtime_matches_complete_lock(self):
        result = observe_dependencies(BASE / 'uv.lock')
        self.assertEqual(result['status'], 'MATCH', result)
        self.assertIn('fastapi', {row['name'] for row in result['packages']})

    def test_missing_fastapi_lock_entry_is_unverified(self):
        parts = (BASE / 'uv.lock').read_text().split('[[package]]')
        text = parts[0] + ''.join('[[package]]' + part for part in parts[1:]
                                 if tomllib.loads(part)['name'] != 'fastapi')
        with tempfile.TemporaryDirectory() as directory:
            lock = Path(directory) / 'uv.lock'
            lock.write_text(text)
            result = observe_dependencies(lock)
        self.assertEqual(result['status'], 'UNVERIFIED')
        self.assertIn('DEPENDENCY_LOCK_INCOMPLETE', result['reason_codes'])

    def test_fastapi_version_mismatch_is_unverified(self):
        text = (BASE / 'uv.lock').read_text()
        packages = tomllib.loads(text)['package']
        version = next(row['version'] for row in packages if row['name'] == 'fastapi')
        text = text.replace(f'name = "fastapi"\nversion = "{version}"',
                            'name = "fastapi"\nversion = "0.0.0"')
        with tempfile.TemporaryDirectory() as directory:
            lock = Path(directory) / 'uv.lock'
            lock.write_text(text)
            result = observe_dependencies(lock)
        self.assertEqual(result['status'], 'UNVERIFIED')
        self.assertIn('DEPENDENCY_VERSION_MISMATCH:fastapi', result['reason_codes'])

    def test_m17_original_owner_and_reader_cold_import_outside_checkout(self):
        owner = BASE / 'vendor/close_discovery_baseline'
        code = '''import json, sys
sys.path.insert(0, sys.argv[1])
from ops import materialize_manager_close_discovery as producer
from apps.api.v35_api import manager_workbench_router as reader
print(json.dumps([str(producer.APP_ROOT), producer.__file__, reader.__file__]))
'''
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([sys.executable, '-I', '-B', '-c', code, str(owner)],
                                    cwd=directory, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        paths = json.loads(result.stdout)
        self.assertEqual(Path(paths[0]), owner)
        self.assertTrue(all(Path(p).is_relative_to(owner) for p in paths))

    def test_m17_original_and_adapter_cli_help_outside_checkout(self):
        # The frozen owner's CLI is a module entry requiring its package root,
        # which the production adapter also supplies before importing the owner.
        code = '''import runpy, sys
sys.path.insert(0, sys.argv[1])
sys.argv = ['ops.materialize_manager_close_discovery', '--help']
runpy.run_module('ops.materialize_manager_close_discovery', run_name='__main__')
'''
        commands = ([sys.executable, '-I', '-B', '-c', code,
                     str(BASE / 'vendor/close_discovery_baseline')],
                    [sys.executable, '-I', '-B',
                     str(BASE / 'src/v5_shadow/daily_close_recapture_owner.py'), '--help'])
        for command in commands:
            with self.subTest(entry=command[-1]), tempfile.TemporaryDirectory() as directory:
                result = subprocess.run(command,
                                        cwd=directory, capture_output=True, text=True, timeout=15)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn('usage:', result.stdout)


if __name__ == '__main__':
    unittest.main()
