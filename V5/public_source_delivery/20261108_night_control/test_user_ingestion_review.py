import unittest,copy
import night_handoff as n
from test_user_ingestion import fixture
class Review(unittest.TestCase):
 def go(self,p,d,parent=None):return n.ingest_user_results('20261109','a'*64,['000001.SZ'],p,d,parent)
 def test_naive_timestamps_rejected(self):
  for key in ('event_at','observed_at','available_at'):
   p,d=fixture();d['records'][0][key]='2026-11-09T07:00:00'
   with self.assertRaises(ValueError):self.go(p,d)
 def test_source_credentials_rejected(self):
  p,d=fixture();d['records'][0]['details']['source_url']='https://u:p@example.invalid/'
  with self.assertRaises(ValueError):self.go(p,d)
 def test_all_missing_no_success_upgrade(self):
  p,d=fixture();d['records']=[];x=self.go(p,d);self.assertEqual(x['missing_count'],4);self.assertFalse(x['research_complete']);self.assertEqual(x['source_admission'],'UNKNOWN')
 def test_parent_time_and_mapping_bound(self):
  p,d=fixture();old=self.go(p,d);p.update(version='v2',expected_parent_identity=old['identity'],cutoff='2026-11-09T07:59:00+08:00');d['version']='v2'
  with self.assertRaises(ValueError):self.go(p,d,old)
  p['cutoff']=old['cutoff'];p['column_map']=dict(p['column_map'],announcements='different')
  with self.assertRaises(ValueError):self.go(p,d,old)
 def test_copied_input_and_late_details_not_effective(self):
  p,d=fixture();d['records'][0]['available_at']='2026-11-09T08:01:00+08:00';x=self.go(p,d);d['records'][0]['details']['facts']='changed';p['column_map']['announcements']='changed';self.assertNotEqual(x['late_records'][0]['details']['facts'],'changed');self.assertEqual(x['column_map']['announcements'],'announcements');self.assertIsNone(x['records'][0]['columns']['announcements'][0]['details'])
if __name__=='__main__':unittest.main()
