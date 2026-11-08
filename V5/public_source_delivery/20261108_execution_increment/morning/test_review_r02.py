import unittest
import registered as r
from test_panel_freshness import fixture
class ReviewR02(unittest.TestCase):
 def test_duplicate_and_reordered_calendar(self):
  for change in ('duplicate','reverse'):
   a,b,c=fixture();s=c['market_calendar']['sessions']
   if change=='duplicate':s.insert(1,s[0].copy())
   else:s.reverse()
   with self.assertRaises(ValueError):r.validate_freeze_panel_freshness(a,b,c)
 def test_bool_and_negative_limits(self):
  for k in ('max_completed_session_lag','max_observation_age_seconds','max_available_age_seconds'):
   for v in (True,-1,1.0):
    a,b,c=fixture();b['panel_freshness'][k]=v
    with self.assertRaises(ValueError):r.validate_freeze_panel_freshness(a,b,c)
 def test_event_must_match_declared_close(self):
  a,b,c=fixture();c['panel_evidence']['event_at']='2026-11-06T14:59:00+08:00'
  with self.assertRaises(ValueError):r.validate_freeze_panel_freshness(a,b,c)
 def test_stale_availability_independent(self):
  a,b,c=fixture();b['panel_freshness']['max_available_age_seconds']=60
  with self.assertRaisesRegex(ValueError,'STALE'):r.validate_freeze_panel_freshness(a,b,c)
 def test_equivalent_utc_event_and_no_admission(self):
  a,b,c=fixture();c['panel_evidence']['event_at']='2026-11-06T07:00:00Z';v=r.validate_freeze_panel_freshness(a,b,c);self.assertFalse(v['source_admission']);self.assertEqual(v['completed_session_lag'],0)
if __name__=='__main__':unittest.main()
