import hashlib
import inspect
import pathlib
import re
import unittest
import isolated_owner as owner


class AdapterPinTests(unittest.TestCase):
    def test_owner_pin_matches_sibling_adapter(self):
        source = inspect.getsource(owner.run)
        match = re.search(r"'registered_rebuild','([0-9a-f]{64})'", source)
        self.assertIsNotNone(match)
        path = pathlib.Path(__file__).resolve().parent.parent / 'latest109_v2/latest109_rebuild.py'
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), match.group(1))
        module = owner.load(path, 'pin_checked_adapter_fixture', match.group(1))
        self.assertFalse(module.FLAGS['production_allowed'])


if __name__ == '__main__':
    unittest.main()
