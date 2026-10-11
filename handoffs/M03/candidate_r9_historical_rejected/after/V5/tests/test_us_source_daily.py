import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from v5_shadow.us_source_daily import parse_utc, source_paths

class TestM03R9(unittest.TestCase):
    def test_utc(self):
        self.assertEqual(parse_utc("2026-10-10T04:00:00+02:00").hour, 2)

    def test_paths(self):
        with TemporaryDirectory() as d:
            p = source_paths(d, "20261010")
            self.assertEqual(
                p["manifest"],
                Path(d)/"research/peripherals/manifest.json"
            )

    def test_naive_time(self):
        with self.assertRaises(ValueError):
            parse_utc("2026-10-10T01:00:00")

if __name__ == "__main__":
    unittest.main()
