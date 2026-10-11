import unittest
from v5_shadow.us_source_daily import parse_utc, collector_argv
class T(unittest.TestCase):
    def test_time(self):
        self.assertEqual(parse_utc("2026-10-10T04:00:00+02:00").hour,2)
    def test_naive(self):
        with self.assertRaises(ValueError):
            parse_utc("2026-10-10T01:00:00")
if __name__=="__main__":
    unittest.main()
