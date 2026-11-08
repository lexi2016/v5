import copy, unittest
import registered as m
import test_material_consumer as fixtures
class LateIndex(unittest.TestCase):
 def make(self):
  fixture=fixtures.Consumer();fixture.setUp();return fixture.manifest
 def call(self,x):
  x['identity']=m.sha(m.canonical({k:v for k,v in x.items() if k!='identity'}))
  return m.project_user_materials(x,'20261109',m.time('2026-11-09T08:02:00+08:00'),m.time('2026-11-09T08:10:00+08:00'))
 def test_original_producer(self):
  x=self.make();r=self.call(x);self.assertEqual(r['late_count'],1);self.assertNotIn('LATE_SECRET_SENTINEL',str(r));self.assertFalse(r['business_accepted'])
 def test_late_status_conflict(self):
  x=self.make();x['late_records'][0]['status']='UNKNOWN'
  with self.assertRaisesRegex(ValueError,'MATERIAL_LATE_INDEX_BINDING'):self.call(x)
 def test_late_timestamp_conflict(self):
  x=self.make();x['late_records'][0]['available_at']='2026-11-09T08:09:00+08:00'
  with self.assertRaisesRegex(ValueError,'MATERIAL_LATE_INDEX_BINDING'):self.call(x)
 def test_placeholder_timestamp_conflict(self):
  x=self.make();x['records'][0]['columns']['announcements'][0]['available_at']='2026-11-09T08:09:00+08:00'
  with self.assertRaisesRegex(ValueError,'MATERIAL_LATE_INDEX_BINDING'):self.call(x)
if __name__=='__main__':unittest.main()
