import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile
import types
import unittest

import isolated_owner as owner


class ContractRunner:
    def __init__(self, monitor, expected):
        self.monitor = monitor
        self.expected = expected
        self.calls = 0

    def run(self, args, **kwargs):
        if args != self.expected:
            raise ValueError('unexpected bootstrap')
        self.monitor()
        self.calls += 1
        return subprocess.run(args, **kwargs)


class NativeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        self.path = self.root / 'worker.py'
        self.raw = b'import json,sys\nprint(json.dumps([__name__, __file__, sys.argv, sys.stdin.read()]))\n'
        self.path.write_bytes(self.raw)
        self.sha = hashlib.sha256(self.raw).hexdigest()
        self.gates = []

    def tearDown(self):
        self.tmp.cleanup()

    def make(self):
        return owner.checked_native_runner(types.SimpleNamespace(NativeRunner=ContractRunner), lambda: self.gates.append(True), self.path, self.sha)

    def execute(self, callback, args=None):
        return callback(args if args is not None else [sys.executable, '-B', str(self.path), '--worker'], input='sample', text=True, capture_output=True, timeout=5)

    def test_original_worker_contract_and_monitor_preserved(self):
        native, callback = self.make()
        result = self.execute(callback)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), ['__main__', str(self.path), [str(self.path), '--worker'], 'sample'])
        self.assertEqual(native.calls, 1)
        self.assertEqual(self.gates, [True])

    def test_changed_worker_rejected_before_execution(self):
        native, callback = self.make()
        self.path.write_text('print("UNVERIFIED_EXECUTED")\n')
        result = self.execute(callback)
        self.assertEqual(result.returncode, 73)
        self.assertNotIn('UNVERIFIED_EXECUTED', result.stdout)

    def test_changed_argv_rejected_before_launch(self):
        native, callback = self.make()
        with self.assertRaisesRegex(ValueError, 'EXACT_ORIGINAL_NATIVE_ARGV'):
            self.execute(callback, [sys.executable, str(self.path)])
        self.assertEqual(native.calls, 0)

    def test_script_directory_import_semantics_preserved(self):
        (self.root / 'fixture_dependency.py').write_text('VALUE = 42\n')
        self.path.write_text('import fixture_dependency\nprint(fixture_dependency.VALUE)\n')
        self.sha = hashlib.sha256(self.path.read_bytes()).hexdigest()
        _, callback = self.make()
        result = self.execute(callback)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), '42')

    def test_invalid_pin_rejected(self):
        self.sha = None
        with self.assertRaisesRegex(ValueError, 'NATIVE_CODE_PIN'):
            self.make()


if __name__ == '__main__':
    unittest.main()
