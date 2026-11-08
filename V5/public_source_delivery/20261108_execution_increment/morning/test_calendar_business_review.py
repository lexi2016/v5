import unittest
import registered as r
from test_panel_freshness import fixture
class Review(unittest.TestCase):
 def test_target_session_does_not_admit_unclosed_source(self):
  a,b,c=fixture();a['source_date']=a['business_date']
  with self.assertRaisesRegex(ValueError,'SOURCE_SESSION'):r.validate_freeze_panel_freshness(a,b,c)
 def test_malformed_business_date_rejected(self):
  for day in ('2026119','20260230',None):
   a,b,c=fixture();a['business_date']=day
   with self.assertRaises(ValueError):r.validate_freeze_panel_freshness(a,b,c)
 def test_utc_date_not_used_as_business_date(self):
  a,b,c=fixture();a.update(business_date='20261108',cutoff='2026-11-08T22:30:00Z')
  with self.assertRaisesRegex(ValueError,'BUSINESS_DATE'):r.validate_freeze_panel_freshness(a,b,c)
 def test_added_future_session_does_not_increment_lag(self):
  a,b,c=fixture();v=r.validate_freeze_panel_freshness(a,b,c);self.assertEqual(v['latest_completed_session'],'20261106');self.assertFalse(v['source_admission'])
if __name__=='__main__':unittest.main()
