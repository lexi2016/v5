import ast
import unittest
from v5_shadow.us_source_daily import _reader_child_code, read_cold_snapshot

class T(unittest.TestCase):
    def test_child_script_parses(self):
        ast.parse(_reader_child_code())

    def test_reader_exists(self):
        self.assertTrue(callable(read_cold_snapshot))

if __name__ == "__main__":
    unittest.main()
