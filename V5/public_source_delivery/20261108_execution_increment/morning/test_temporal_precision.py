import unittest,copy
import registered as m
import test_material_consumer as fixtures
from test_freeze_fact_timing import fixture as fact_fixture
class TemporalPrecision(unittest.TestCase):
 def test_common_time_parser_does_not_truncate(self):
  for value in ('2026-11-09T08:00:00.0000001+08:00','2026-11-09T08:00:00.0000000Z','2026-11-09T08:00:00,0000001Z','2026-11-09T08:00:00+08:00:00.0000001','20261109T080000Z'):
   with self.subTest(value=value),self.assertRaisesRegex(ValueError,'PRECISION'):m.time(value)
 def test_exact_supported_microseconds(self):
  for n in range(1,7):self.assertEqual(m.time('2026-11-09T08:00:00.'+'1'*n+'Z').microsecond,int(('1'*n).ljust(6,'0')))
 def test_actual_semantic_fact_after_cutoff_rejected(self):
  doc,policy,cutoff=fact_fixture();doc['sources']['s1']['facts'][0]['available_at']='2026-11-09T06:30:00.0000001+08:00'
  with self.assertRaisesRegex(ValueError,'PRECISION|FACT_TIME'):m.semantic_compare(doc,policy,cutoff)
class ProducerPrecision(unittest.TestCase):
 setUp=fixtures.Consumer.setUp
 make=fixtures.Consumer.make
 runone=fixtures.Consumer.runone
 resign=fixtures.Consumer.resign
 def test_producer_all_timestamp_boundaries_reject_truncation(self):
  for field in ('event_at','observed_at','available_at'):
   with self.subTest(field=field):
    old=self.doc['records'][0][field];self.doc['records'][0][field]='2026-11-09T08:00:00.0000001+08:00'
    with self.assertRaisesRegex(ValueError,'PRECISION'):self.make()
    self.doc['records'][0][field]=old
  self.policy['cutoff']='2026-11-09T08:00:00.0000001+08:00'
  with self.assertRaisesRegex(ValueError,'PRECISION'):self.make()
 def test_old_producer_manifest_cannot_bypass_consumer(self):
  self.doc['records'][0]['available_at']='2026-11-09T08:00:00+08:00';self.manifest=self.make()
  self.manifest['records'][0]['columns']['announcements'][0]['available_at']='2026-11-09T08:00:00.0000001+08:00';self.resign()
  with self.assertRaisesRegex(ValueError,'PRECISION'):self.runone()
 def test_exact_boundary_and_late_microsecond_preserved(self):
  self.doc['records'][0]['available_at']='2026-11-09T08:00:00.000000+08:00';self.manifest=self.make();self.assertEqual(self.runone()['sections'][1]['content']['late_count'],0)
  self.doc['records'][0]['available_at']='2026-11-09T08:00:00.000001+08:00';self.manifest=self.make();out=self.runone();self.assertEqual(out['sections'][1]['content']['late_count'],1);self.assertNotIn('LATE_SECRET_SENTINEL',str(out))
