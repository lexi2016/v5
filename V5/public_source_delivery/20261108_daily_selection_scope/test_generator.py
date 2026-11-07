import json,unittest
from generator import build,sha
class Tests(unittest.TestCase):
 def setUp(self):
  self.rows=[{'symbol':'000001.SZ','source_date':20300104,'observation_date':20300107,'selected_groups':['original','nav_smallk']},{'symbol':'600000.SH','source_date':20300104,'observation_date':20300107,'selected_groups':['nav_smallk']},{'symbol':'000002.SZ','source_date':20300104,'observation_date':20300107,'selected_groups':[]}]
  self.days=[20300103,20300104,20300107]
 def invoke(self,verify=None):
  def synthetic(*args):return {r:{'path':'SYNTHETIC_'+r,'sha256':sha(r.encode())} for r in ('freeze','source_review','calendar_review')}
  return build(b'\n'.join(json.dumps(x).encode() for x in self.rows),json.dumps({'trading_days':self.days}).encode(),20300104,20300107,verify or synthetic)
 def test_union_preserves_groups(self):
  r=self.invoke();self.assertEqual(r['dedup_selected_count'],2);self.assertEqual(r['group_counts']['nav_smallk'],2);self.assertFalse(r['approved_for_capture']);self.assertEqual(r['scope_to_intraday_mapping'],'UNKNOWN');self.assertEqual(r,self.invoke())
 def test_default_production_blocked(self):
  from generator import production_verifier
  with self.assertRaisesRegex(ValueError,'BLOCKED_NO_REVIEWED'):self.invoke(production_verifier)
 def test_missing_review(self):
  with self.assertRaisesRegex(ValueError,'MISSING_freeze'):self.invoke(lambda *a:{})
 def test_stale_date(self):
  self.rows[0]['source_date']=20300103
  with self.assertRaisesRegex(ValueError,'ROW_DATE'):self.invoke()
 def test_intervening_day(self):
  self.days.insert(2,20300105)
  with self.assertRaisesRegex(ValueError,'PREVIOUS_TRADING_DAY'):self.invoke()
 def test_duplicate_calendar(self):
  self.days.insert(1,20300103)
  with self.assertRaisesRegex(ValueError,'CALENDAR_ORDER_DUPLICATE'):self.invoke()
 def test_duplicate_symbol(self):
  self.rows.append(self.rows[0])
  with self.assertRaisesRegex(ValueError,'DUPLICATE_SYMBOL'):self.invoke()
 def test_unknown_group(self):
  self.rows[0]['selected_groups']=['UNKNOWN']
  with self.assertRaisesRegex(ValueError,'GROUP_SCHEMA'):self.invoke()
 def test_unicode(self):
  self.rows[0]['symbol']='０００００１.SZ'
  with self.assertRaisesRegex(ValueError,'IDENTITY'):self.invoke()
 def test_changed_input_changes_candidate(self):
  old=self.invoke()['candidate_sha256'];self.rows[0]['selected_groups']=['original'];self.assertNotEqual(old,self.invoke()['candidate_sha256'])
if __name__=='__main__':unittest.main()
