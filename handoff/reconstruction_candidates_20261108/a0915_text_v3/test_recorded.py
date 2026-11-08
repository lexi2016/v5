import copy,hashlib,json,unittest
import recorded as m
class Tests(unittest.TestCase):
 def setUp(self):
  self.d={'schema':'A0915_RECORDED_DISPLAY_INPUT_V1','market':'A_SHARE','target_date':'20261109','observed_at':'2026-11-09T09:14:00+08:00','available_at':'2026-11-09T09:14:30+08:00','scope':['A.000001','A.000002'],'rows':[{'symbol':'A.000001','observation':'provided text only'}],'source_reference':'fixture-source','data_kind':'RECORDED_UNVERIFIED'}
  self.c={'schema':'A0915_TEXT_READER_CONTRACT_V3','target_date':'20261109','scope':self.d['scope'][:],'source_reference':'fixture-source','input_sha256':'0'*64,'cutoff':'2026-11-09T09:15:00+08:00','max_age_seconds':120}
 def runone(self):
  raw=json.dumps(self.d).encode();self.c['input_sha256']=hashlib.sha256(raw).hexdigest();return m.read_recorded_bytes(raw,self.c)
 def test_partial_preserves_unknown(self):
  r=self.runone();self.assertEqual(r['missing_symbols'],['A.000002']);self.assertFalse(r['production_allowed']);self.assertEqual(r['source_admission'],'UNKNOWN')
 def test_complete_does_not_admit(self):
  self.d['rows'].append({'symbol':'A.000002','observation':'other text'});r=self.runone();self.assertEqual(r['status'],'RECORDED_TEXT_VALIDATED_NOT_ADMITTED');self.assertFalse(r['business_accepted'])
 def test_synthetic_label_preserved(self):
  self.d['data_kind']='SYNTHETIC_TEST';self.assertEqual(self.runone()['recorded_input']['data_kind'],'SYNTHETIC_TEST')
 def test_wrong_pin(self):
  with self.assertRaisesRegex(ValueError,'INPUT_CHANGED'):m.read_recorded_bytes(json.dumps(self.d).encode(),self.c)
 def test_future_or_stale_or_reverse(self):
  for key,value in [('available_at','2026-11-09T09:15:01+08:00'),('observed_at','2026-11-09T09:00:00+08:00'),('available_at','2026-11-09T09:13:00+08:00')]:
   with self.subTest(key=key,value=value):
    old=self.d[key];self.d[key]=value
    with self.assertRaises(ValueError):self.runone()
    self.d[key]=old
 def test_naive_time(self):
  self.d['observed_at']='2026-11-09T09:14:00'
  with self.assertRaisesRegex(ValueError,'TIMEZONE'):self.runone()
 def test_policy_required_not_boolean(self):
  self.c['max_age_seconds']=True
  with self.assertRaisesRegex(ValueError,'FRESHNESS'):self.runone()
 def test_wrong_source_scope(self):
  for key,value in [('source_reference','other'),('scope',['A.000002'])]:
   old=self.c[key];self.c[key]=value
   with self.assertRaisesRegex(ValueError,'IDENTITY'):self.runone()
   self.c[key]=old
 def test_duplicate_rows(self):
  self.d['rows']*=2
  with self.assertRaisesRegex(ValueError,'DUPLICATE'):self.runone()
 def test_no_quote_fields_or_authority(self):
  self.d['rows'][0]['price']=1
  with self.assertRaisesRegex(ValueError,'TEXT_ROW'):self.runone()
 def test_detached_result(self):
  r=self.runone();self.c['scope'].clear();self.d['rows'][0]['observation']='changed';self.assertEqual(r['scope_count'],2);self.assertEqual(r['recorded_input']['rows'][0]['observation'],'provided text only')
 def test_duplicate_json(self):
  raw=b'{"x":1,"x":2}';self.c['input_sha256']=hashlib.sha256(raw).hexdigest()
  with self.assertRaisesRegex(ValueError,'DUPLICATE_KEY'):m.read_recorded_bytes(raw,self.c)
 def test_cutoff_not_shiftable(self):
  self.c['cutoff']='2026-11-09T09:25:00+08:00'
  with self.assertRaisesRegex(ValueError,'CUTOFF'):self.runone()
if __name__=='__main__':unittest.main()
