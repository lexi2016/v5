import unittest
import registered as m
import test_material_consumer as f
class Review(unittest.TestCase):
 setUp=f.Consumer.setUp
 make=f.Consumer.make
 runone=f.Consumer.runone
 resign=f.Consumer.resign
 def test_producer_offset_fraction_and_comma_refused(self):
  for value in ('2026-11-09T08:00:00,0000001Z','2026-11-09T08:00:00+08:00:00.0000001','2026-11-09 08:00:00+08:00'):
   self.doc['records'][0]['available_at']=value
   with self.assertRaisesRegex(ValueError,'PRECISION'):self.make()
 def test_consumer_envelope_precision_refused(self):
  self.reg['cutoff']='2026-11-09T08:10:00.0000001+08:00'
  with self.assertRaisesRegex(ValueError,'PRECISION'):self.runone()
 def test_parser_non_string_and_trailing_input_refused(self):
  for value in (True,None,123,'2026-11-09T08:10:00Z\n','2026-W46-1T08:10:00Z'):
   with self.assertRaises(ValueError):m.time(value)
if __name__=='__main__':unittest.main()
