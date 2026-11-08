import hashlib
import pathlib
import tempfile
import unittest
from unittest.mock import patch

import isolated_owner as owner


class CheckedLoaderTests(unittest.TestCase):
    def test_executes_exact_checked_bytes_after_path_replacement(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / 'fixture.py'
            original = b'VALUE = "checked"\n'
            path.write_bytes(original)
            read_bytes = pathlib.Path.read_bytes

            def replace_after_read(candidate):
                result = read_bytes(candidate)
                if candidate == path:
                    path.write_text('VALUE = "unchecked"\n')
                return result

            with patch.object(pathlib.Path, 'read_bytes', replace_after_read):
                module = owner.load(path, 'checked_loader_fixture', hashlib.sha256(original).hexdigest())
            self.assertEqual(module.VALUE, 'checked')

    def test_module_identity_retained(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / 'fixture.py'
            path.write_text('IDENTITY = (__name__, __file__)\n')
            module = owner.load(path, 'identity_fixture')
            self.assertEqual(module.IDENTITY, ('identity_fixture', str(path)))

    def test_bad_pin_never_executes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / 'fixture.py'
            path.write_text('raise RuntimeError("must not execute")\n')
            with self.assertRaisesRegex(ValueError, 'SOURCE_PIN'):
                owner.load(path, 'bad_fixture', '0' * 64)


if __name__ == '__main__':
    unittest.main()
