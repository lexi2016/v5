import unittest
import test_material_consumer as f
class Review(unittest.TestCase):
 setUp=f.Consumer.setUp
 make=f.Consumer.make
 runone=f.Consumer.runone
 resign=f.Consumer.resign
 def test_late_extra_body_refused(self):
  self.manifest['records'][0]['columns']['announcements'][0]['raw_body']='LATE_SENTINEL';self.resign()
  with self.assertRaises(ValueError):self.runone()
 def test_missing_extra_body_refused(self):
  self.manifest['records'][1]['columns']['announcements'][0]['raw_body']='LATE_SENTINEL';self.resign()
  with self.assertRaises(ValueError):self.runone()
 def test_effective_missing_time_refused(self):
  self.doc['records'][0]['available_at']='2026-11-09T07:02:00+08:00';self.manifest=self.make();del self.manifest['records'][0]['columns']['announcements'][0]['available_at'];self.resign()
  with self.assertRaises(ValueError):self.runone()
 def test_effective_future_rehashed_refused(self):
  self.doc['records'][0]['available_at']='2026-11-09T07:02:00+08:00';self.manifest=self.make();self.manifest['records'][0]['columns']['announcements'][0]['observed_at']='2026-11-09T08:01:00+08:00';self.resign()
  with self.assertRaises(ValueError):self.runone()
 def test_late_reported_status_not_body_carrier(self):
  self.manifest['records'][0]['columns']['announcements'][0]['reported_status']='LATE_SENTINEL_BODY';self.resign()
  with self.assertRaises(ValueError):self.runone()
 def test_scope_omission_refused(self):
  self.manifest['records'].pop();self.resign()
  with self.assertRaises(ValueError):self.runone()
if __name__=='__main__':unittest.main()
