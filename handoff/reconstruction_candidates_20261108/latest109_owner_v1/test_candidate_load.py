import hashlib
import pathlib
import tempfile
import types
import unittest
from unittest.mock import patch

import isolated_owner as owner


class CandidateLoadTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        self.code = self.root / 'candidate.py'
        self.rule = self.root / 'rules.json'
        self.raw = b'VALUE = "verified"\n'
        self.code.write_bytes(self.raw)
        self.rule.write_bytes(b'{}')
        def checked(path, pin):
            if hashlib.sha256(path.read_bytes()).hexdigest() != pin:
                raise ValueError('RULE_PIN')
            return path
        self.adapter = types.SimpleNamespace(CANDIDATE_SHA=hashlib.sha256(self.raw).hexdigest(), ACTION_SHA=hashlib.sha256(b'{}').hexdigest(), checked=checked)

    def tearDown(self):
        self.tmp.cleanup()

    def test_executes_checked_candidate_snapshot(self):
        original = pathlib.Path.read_bytes
        def replace(path):
            raw = original(path)
            if path == self.code:
                path.write_text('VALUE = "unverified"\n')
            return raw
        with patch.object(pathlib.Path, 'read_bytes', replace):
            module = owner.load_candidate(self.adapter, self.code, self.rule)
        self.assertEqual(module.VALUE, 'verified')

    def test_bad_rule_prevents_candidate_execution(self):
        self.rule.write_bytes(b'{"changed":true}')
        with patch.object(owner, 'load') as load:
            with self.assertRaisesRegex(ValueError, 'RULE_PIN'):
                owner.load_candidate(self.adapter, self.code, self.rule)
            load.assert_not_called()

    def test_bad_candidate_pin_prevents_execution(self):
        self.code.write_text('raise RuntimeError("unverified")\n')
        with self.assertRaisesRegex(ValueError, 'SOURCE_PIN'):
            owner.load_candidate(self.adapter, self.code, self.rule)

    def test_module_name_and_file_preserved(self):
        module = owner.load_candidate(self.adapter, self.code, self.rule)
        self.assertEqual(module.__name__, 'registered_latest109_candidate')
        self.assertEqual(module.__file__, str(self.code))


if __name__ == '__main__':
    unittest.main()
