import unittest,copy
import registered as r

def add_contract(reg,policy,docs):
 policy['panel_freshness']={'schema':'FREEZE_PANEL_FRESHNESS_V1','market':'A_SHARE','timezone':'Asia/Shanghai','calendar_version':'SYNTHETIC_CAL','max_completed_session_lag':0,'max_observation_age_seconds':300000,'max_available_age_seconds':300000}
 docs['market_calendar']={'schema':'MARKET_SESSION_CALENDAR_V1','market':'A_SHARE','timezone':'Asia/Shanghai','version':'SYNTHETIC_CAL','coverage_start':'20261001','coverage_end':'20261110','source_reference':'SYNTHETIC_FIXTURE_NOT_REAL_CALENDAR','sessions':[{'trade_date':d,'close_at':d[:4]+'-'+d[4:6]+'-'+d[6:]+'T15:00:00+08:00'} for d in ['20261001','20261105','20261106','20261109','20261110']]}
 docs['panel_evidence']={'schema':'FREEZE_PANEL_EVIDENCE_V1','panel_identity':r.sha(r.canonical(docs['panel'])),'source_date':reg['source_date'],'calendar_version':'SYNTHETIC_CAL','event_at':'2026-11-06T15:00:00+08:00','observed_at':'2026-11-06T15:01:00+08:00','available_at':'2026-11-06T15:02:00+08:00','source_reference':'SYNTHETIC_PROVIDER_RECEIPT'}
 return reg,policy,docs

def fixture():return add_contract({'business_date':'20261109','source_date':'20261106','cutoff':'2026-11-09T06:30:00+08:00'},{},{'panel':{'source_date':'20261106','rows':[{'symbol':'000001.SZ','actual_date':'20261106'}]}})
class Test(unittest.TestCase):
 def test_weekend_uses_friday(self):x=r.validate_freeze_panel_freshness(*fixture());self.assertEqual(x['latest_completed_session'],'20261106');self.assertEqual(x['completed_session_lag'],0)
 def test_old_panel(self):
  a,b,c=fixture();a['source_date']='20261001'
  with self.assertRaises(ValueError):r.validate_freeze_panel_freshness(a,b,c)
 def test_uncompleted_current_session(self):
  a,b,c=fixture();a['source_date']='20261109'
  with self.assertRaises(ValueError):r.validate_freeze_panel_freshness(a,b,c)
 def test_panel_identity(self):
  a,b,c=fixture();c['panel']['rows'][0]['actual_date']='20261001'
  with self.assertRaises(ValueError):r.validate_freeze_panel_freshness(a,b,c)
 def test_stale_receipt(self):
  a,b,c=fixture();b['panel_freshness']['max_observation_age_seconds']=60
  with self.assertRaises(ValueError):r.validate_freeze_panel_freshness(a,b,c)
 def test_future_or_before_event(self):
  for k,v in [('available_at','2026-11-09T06:31:00+08:00'),('observed_at','2026-11-06T14:59:00+08:00')]:
   a,b,c=fixture();c['panel_evidence'][k]=v
   with self.assertRaises(ValueError):r.validate_freeze_panel_freshness(a,b,c)
 def test_calendar_version_coverage(self):
  for key,value in [('version','OTHER'),('coverage_end','20261108')]:
   a,b,c=fixture();c['market_calendar'][key]=value
   with self.assertRaises(ValueError):r.validate_freeze_panel_freshness(a,b,c)
 def test_no_default(self):
  a,b,c=fixture();b.clear()
  with self.assertRaises(ValueError):r.validate_freeze_panel_freshness(a,b,c)
if __name__=='__main__':unittest.main()
