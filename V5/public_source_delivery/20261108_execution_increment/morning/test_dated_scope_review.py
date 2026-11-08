import unittest
from test_dated_scope import fixture,p
class Review(unittest.TestCase):
 def test_panel_duplicate_rejected(self):
  t,s,c=fixture();s['rows'][-1]=s['rows'][0]
  with self.assertRaises(ValueError):p.annotate_dated(t,s,c)
 def test_partial_panel_rejected(self):
  t,s,c=fixture();s['rows'].pop()
  with self.assertRaises(ValueError):p.annotate_dated(t,s,c)
 def test_missing_dates_preserved(self):
  t,s,c=fixture();t['rows'][0]['actual_date']=None;s['rows'][0]['actual_date']=None;r=p.annotate_dated(t,s,c)
  self.assertIsNone(r[0]['rank_actual_date']);self.assertIsNone(r[0]['selection_actual_date']);self.assertTrue(r[0]['no_buy'])
 def test_invalid_state_rejected(self):
  t,s,c=fixture();s['rows'][0]['layers']['original']['after_risk']=True
  with self.assertRaises(ValueError):p.annotate_dated(t,s,c)
 def test_source_date_shape_and_calendar(self):
  for day in ('2026119','20260230'):
   t,s,c=fixture();c['source_date']=day
   with self.assertRaises(ValueError):p.annotate_dated(t,s,c)
if __name__=='__main__':unittest.main()
