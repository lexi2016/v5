import unittest
import recorded as m
import test_recorded as fixtures
class Precision(unittest.TestCase):
 def test_seventh_digit_rejected_at_each_boundary(self):
  for field in ('cutoff','observed_at','available_at'):
   x=fixtures.Tests();x.setUp()
   (x.c if field=='cutoff' else x.d)[field]='2026-11-09T09:15:00.0000001+08:00'
   with self.subTest(field=field),self.assertRaisesRegex(ValueError,'TIME_FORMAT_OR_PRECISION'):x.runone()
 def test_supported_precision_exact(self):
  for digits in range(1,7):
   value='2026-11-09T09:14:00.'+'1'*digits+'+08:00'
   self.assertEqual(m.timestamp(value).microsecond,int(('1'*digits).ljust(6,'0')))
 def test_exact_cutoff_and_microsecond_after(self):
  x=fixtures.Tests();x.setUp();x.d['available_at']='2026-11-09T09:15:00.000000+08:00';self.assertFalse(x.runone()['production_allowed'])
  x.d['available_at']='2026-11-09T09:15:00.000001+08:00'
  with self.assertRaisesRegex(ValueError,'NOT_AVAILABLE'):x.runone()
 def test_utc_equivalent(self):
  x=fixtures.Tests();x.setUp();x.c['cutoff']='2026-11-09T01:15:00Z';self.assertTrue(x.runone()['temporal_policy_checked'])
 def test_noncanonical_variants_rejected(self):
  for value in ('20261109T091500+0800','2026-11-09 09:15:00+08:00','2026-11-09T09:15:00,0000001+08:00','2026-11-09T09:15:00+08:00:00.0000001','2026-11-09T09:15+08:00'):
   with self.subTest(value=value),self.assertRaisesRegex(ValueError,'TIME_FORMAT_OR_PRECISION'):m.timestamp(value)
