import unittest
import recorded as r
class ReviewPrecision(unittest.TestCase):
 def test_zero_extra_digits_rejected(self):
  for suffix in ('0000000','1234560','000000000000000000000001'):
   with self.assertRaisesRegex(ValueError,'PRECISION'):r.timestamp('2026-11-09T09:15:00.'+suffix+'Z')
 def test_separator_and_offset_precision_bypasses_rejected(self):
  for value in ('2026-11-09X09:15:00.0000001Z','2026-11-09T09:15:00.0000001+0800','2026-11-09T09:15:00+08:00:00.0000001','2026-W46-1T09:15:00.0000001Z','2026-11-09T09:15:00.0000001Z\n'):
   with self.assertRaises(ValueError):r.timestamp(value)
 def test_calendar_and_clock_rejected(self):
  for value in ('2026-02-30T09:15:00Z','2026-11-09T24:00:00Z','2026-11-09T09:15:60Z'):
   with self.assertRaises(ValueError):r.timestamp(value)
 def test_negative_offset_and_microseconds_exact(self):
  value=r.timestamp('2026-11-08T20:15:00.123456-05:00');self.assertEqual(value.microsecond,123456);self.assertEqual(value.utcoffset().total_seconds(),-18000)
if __name__=='__main__':unittest.main()
