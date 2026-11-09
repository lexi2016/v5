import unittest,copy
import registered as r

def add_contract(reg,policy,docs):
 policy['panel_freshness']={'schema':'FREEZE_PANEL_FRESHNESS_V1','market':'A_SHARE','timezone':'Asia/Shanghai','calendar_version':'SYNTHETIC_CAL','max_completed_session_lag':0,'max_observation_age_seconds':300000,'max_available_age_seconds':300000}
 docs['market_calendar']={'schema':'MARKET_SESSION_CALENDAR_V1','market':'A_SHARE','timezone':'Asia/Shanghai','version':'SYNTHETIC_CAL','coverage_start':'20261001','coverage_end':'20261110','source_reference':'SYNTHETIC_FIXTURE_NOT_REAL_CALENDAR','sessions':[{'trade_date':d,'close_at':d[:4]+'-'+d[4:6]+'-'+d[6:]+'T15:00:00+08:00'} for d in ['20261001','20261105','20261106','20261109','20261110']]}
 docs['panel_evidence']={'schema':'FREEZE_PANEL_EVIDENCE_V1','panel_identity':r.sha(r.canonical(docs['panel'])),'source_date':reg['source_date'],'calendar_version':'SYNTHETIC_CAL','event_at':'2026-11-06T15:00:00+08:00','observed_at':'2026-11-06T15:01:00+08:00','available_at':'2026-11-06T15:02:00+08:00','source_reference':'SYNTHETIC_PROVIDER_RECEIPT'}
 return reg,policy,docs

def fixture():return add_contract({'business_date':'20261109','source_date':'20261106','cutoff':'2026-11-09T06:30:00+08:00'},{},{'panel':{'source_date':'20261106','rows':[{'symbol':'000001.SZ','actual_date':'20261106'}]}})
def rebind_source(reg,docs,day):
 # Keep all identities consistent so stale-source tests reach the intended guard.
 reg['source_date']=day
 docs['panel']['source_date']=day
 for row in docs['panel']['rows']:row['actual_date']=day
 stamp=day[:4]+'-'+day[4:6]+'-'+day[6:]
 docs['panel_evidence'].update(source_date=day,panel_identity=r.sha(r.canonical(docs['panel'])),event_at=stamp+'T15:00:00+08:00',observed_at=stamp+'T15:01:00+08:00',available_at=stamp+'T15:02:00+08:00')

class Test(unittest.TestCase):
 def test_monday_premarket_uses_completed_friday(self):x=r.validate_freeze_panel_freshness(*fixture());self.assertEqual(x['latest_completed_session'],'20261106');self.assertEqual(x['completed_session_lag'],0)
 def test_old_panel(self):
  a,b,c=fixture();rebind_source(a,c,'20261001')
  with self.assertRaisesRegex(ValueError,'^PANEL_SOURCE_SESSION_STALE_OR_INCOMPLETE$'):r.validate_freeze_panel_freshness(a,b,c)
 def test_uncompleted_current_session(self):
  a,b,c=fixture();rebind_source(a,c,'20261109')
  with self.assertRaisesRegex(ValueError,'^PANEL_SOURCE_SESSION_STALE_OR_INCOMPLETE$'):r.validate_freeze_panel_freshness(a,b,c)
 def test_two_completed_sessions_lag_rejected(self):
  a,b,c=fixture();day='20261104';rebind_source(a,c,day)
  c['market_calendar']['sessions'].insert(1,{'trade_date':day,'close_at':'2026-11-04T15:00:00+08:00'})
  # Exact error checks the session gate even though receipt age is also excessive.
  with self.assertRaisesRegex(ValueError,'^PANEL_SOURCE_SESSION_STALE_OR_INCOMPLETE$'):r.validate_freeze_panel_freshness(a,b,c)
 def test_weekend_business_date_is_not_monday_test(self):
  a,b,c=fixture();a.update(business_date='20261108',cutoff='2026-11-08T06:30:00+08:00')
  with self.assertRaisesRegex(ValueError,'^PANEL_BUSINESS_SESSION$'):r.validate_freeze_panel_freshness(a,b,c)
 def test_two_session_threshold_with_recent_retrieval(self):
  a,b,c=fixture();rebind_source(a,c,'20261104')
  c['market_calendar']['sessions'].insert(1,{'trade_date':'20261104','close_at':'2026-11-04T15:00:00+08:00'})
  c['panel_evidence'].update(observed_at='2026-11-09T06:28:00+08:00',available_at='2026-11-09T06:29:00+08:00')
  b['panel_freshness']['max_completed_session_lag']=1
  with self.assertRaisesRegex(ValueError,'^PANEL_SOURCE_SESSION_STALE_OR_INCOMPLETE$'):
   r.validate_freeze_panel_freshness(a,b,c)
  b['panel_freshness']['max_completed_session_lag']=2
  result=r.validate_freeze_panel_freshness(a,b,c)
  self.assertEqual(result['completed_session_lag'],2)
  self.assertEqual(result['event_at'],'2026-11-04T15:00:00+08:00')
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
