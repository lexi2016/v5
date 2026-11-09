import unittest,copy
import registered as r
from test_panel_freshness import fixture,add_coverage
class BusinessDay(unittest.TestCase):
 def test_weekend_target_rejected(self):
  a,b,c=fixture();a.update(business_date='20261108',cutoff='2026-11-08T06:30:00+08:00')
  with self.assertRaisesRegex(ValueError,'PANEL_BUSINESS_SESSION'):r.validate_freeze_panel_freshness(a,b,c)
 def test_weekday_closed_target_rejected(self):
  a,b,c=fixture();c['market_calendar']['sessions']=[s for s in c['market_calendar']['sessions'] if s['trade_date']!='20261109']
  add_coverage(c)
  with self.assertRaisesRegex(ValueError,'PANEL_BUSINESS_SESSION'):r.validate_freeze_panel_freshness(a,b,c)
 def test_target_cutoff_mismatch_rejected(self):
  a,b,c=fixture();a['business_date']='20261110'
  with self.assertRaisesRegex(ValueError,'PANEL_BUSINESS_DATE'):r.validate_freeze_panel_freshness(a,b,c)
 def test_explicit_calendar_session_not_weekday_heuristic(self):
  a,b,c=fixture();a.update(business_date='20261108',cutoff='2026-11-08T06:30:00+08:00')
  c['market_calendar']['sessions'].insert(3,{'trade_date':'20261108','close_at':'2026-11-08T15:00:00+08:00'})
  add_coverage(c)
  self.assertEqual(r.validate_freeze_panel_freshness(a,b,c)['completed_session_lag'],0)
 def test_timezone_equivalent_cutoff(self):
  a,b,c=fixture();a['cutoff']='2026-11-08T22:30:00Z'
  self.assertEqual(r.validate_freeze_panel_freshness(a,b,c)['completed_session_lag'],0)
if __name__=='__main__':unittest.main()
