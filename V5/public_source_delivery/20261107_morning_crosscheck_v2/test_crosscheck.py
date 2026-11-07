import copy,datetime as dt,unittest
from crosscheck import audit,GROUPS

def fixture():
 rows=[]
 for symbol,owner,date,family,state in [('000001.SZ','COMPUTED_CURRENT','20261106','TDX','TRUE'),('000002.SZ','SOURCE_BLOCKED','20261105','UNKNOWN','UNKNOWN')]:rows.append({'symbol':symbol,'owner_outcome':owner,'actual_date':date,'source_family':family,'layers':{g:{'after_risk':state} for g in GROUPS},'reasons':['fixture']})
 return {'schema':'PAR_SCREEN_DISPLAY_V1','source_date':'20261106','scope_count':2,'rows':rows,'partitions':{'COMPUTED_CURRENT':1,'SOURCE_BLOCKED':1},'dedup_selected':1,'dedup_pending':1,'counts':{g:{'after_risk':{'TRUE':1,'FALSE':0,'UNKNOWN':1}} for g in GROUPS}}
class Tests(unittest.TestCase):
 def check(self,d=None):return audit(fixture() if d is None else d,'20261107')
 def test_real_date_preserved(self):
  r=self.check();self.assertEqual(r['source_date'],'20261106');self.assertFalse(r['target_day_complete'])
 def test_queues(self):
  q=self.check()['queues'];self.assertEqual(len(q['stale_or_missing_date']),1);self.assertEqual(len(q['not_consumed']),1);self.assertEqual(len(q['unknown_groups']),1)
 def test_computed_stale_contradiction(self):
  d=fixture();d['rows'][0]['actual_date']='20261105';self.assertEqual(self.check(d)['status'],'FAILED_CONSISTENCY')
 def test_future_source(self):
  d=fixture();d['source_date']='20261108';self.assertEqual(self.check(d)['status'],'FAILED_CONSISTENCY')
 def test_unknown_source_not_approved(self):
  r=self.check();self.assertEqual(len(r['queues']['unknown_source']),1);self.assertFalse(r['source_admission'])
 def test_duplicate(self):
  d=fixture();d['rows'][1]['symbol']='000001.SZ';self.assertEqual(self.check(d)['status'],'FAILED_CONSISTENCY')
 def test_bad_count(self):
  d=fixture();d['partitions']['COMPUTED_CURRENT']=2;self.assertEqual(self.check(d)['status'],'FAILED_CONSISTENCY')
 def test_group_count(self):
  d=fixture();d['counts']['original']['after_risk']['TRUE']=2;self.assertEqual(self.check(d)['status'],'FAILED_CONSISTENCY')
 def test_bad_enum(self):
  d=fixture();d['rows'][0]['layers']['original']['after_risk']='ACCEPTED';self.assertEqual(self.check(d)['status'],'FAILED_CONSISTENCY')
 def test_unchanged(self):
  d=fixture();before=copy.deepcopy(d);self.check(d);self.assertEqual(d,before)
 def test_missing_date(self):
  d=fixture();d['rows'][1]['actual_date']=None;self.assertEqual(len(self.check(d)['queues']['stale_or_missing_date']),1)
 def test_actual_future(self):
  d=fixture();d['rows'][1]['actual_date']='20261109';self.assertEqual(self.check(d)['status'],'FAILED_CONSISTENCY')
 def test_unknown_owner(self):
  d=fixture();d['rows'][1]['owner_outcome']='NEW';self.assertEqual(self.check(d)['status'],'FAILED_CONSISTENCY')
if __name__=='__main__':unittest.main()

class EntryTests(unittest.TestCase):
 def test_schema_required(self):
  d=fixture();del d['schema']
  with self.assertRaises(ValueError):audit(d,'20261107')
 def test_schema_wrong(self):
  d=fixture();d['schema']='OTHER'
  with self.assertRaises(ValueError):audit(d,'20261107')
 def test_failed_consistency_exits_nonzero_without_freeze(self):
  import crosscheck,io
  from unittest.mock import patch
  from contextlib import redirect_stdout
  d=fixture();d['partitions']['COMPUTED_CURRENT']=2
  with patch.object(crosscheck,'load',return_value=d) as loader,patch.object(crosscheck.safeio,'freeze') as freeze,redirect_stdout(io.StringIO()) as out:
   code=crosscheck.main()
  self.assertEqual(code,2);loader.assert_called_once_with();freeze.assert_not_called();self.assertIn('FAILED_CONSISTENCY',out.getvalue());self.assertNotIn('byte_readback',out.getvalue())
 def test_load_refusal_nonzero_without_audit_or_freeze(self):
  import crosscheck,io
  from unittest.mock import patch
  from contextlib import redirect_stdout
  with patch.object(crosscheck,'load',side_effect=ValueError('INPUT_PIN_CHANGED')),patch.object(crosscheck,'audit') as a,patch.object(crosscheck.safeio,'freeze') as f,redirect_stdout(io.StringIO()) as out:
   code=crosscheck.main()
  self.assertEqual(code,3);a.assert_not_called();f.assert_not_called();self.assertNotIn('byte_readback',out.getvalue())
 def test_freeze_refusal_nonzero_no_success_receipt(self):
  import crosscheck,io
  from unittest.mock import patch
  from contextlib import redirect_stdout
  with patch.object(crosscheck,'load',return_value=fixture()),patch.object(crosscheck.safeio,'freeze',side_effect=ValueError('READBACK_CHANGED')),redirect_stdout(io.StringIO()) as out:
   code=crosscheck.main()
  self.assertEqual(code,3);self.assertNotIn('byte_readback',out.getvalue())
