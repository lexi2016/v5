import copy, unittest
from candidate import inspect_synthetic
class Tests(unittest.TestCase):
 def setUp(self):
  self.x={'schema':'A0915_RECORDED_DISPLAY_INPUT_V1','market':'A_SHARE','target_date':'20261106','observed_at':'2026-11-06T09:15:00+08:00','available_at':'2026-11-06T09:15:00+08:00','scope':['A.000001','A.000002'],'rows':[{'symbol':'A.000001','observation':'SYNTHETIC ONLY'}],'source_reference':'SYNTHETIC ONLY','data_kind':'SYNTHETIC_TEST'}
 def runone(self):return inspect_synthetic(self.x, target_date='20261106', registered_scope=('A.000001','A.000002'))
 def test_missing_scope_is_preserved(self):
  r=self.runone();self.assertEqual(r['missing_symbols'],['A.000002']);self.assertIn('MISSING_SCOPE_ROWS',r['blocking_reasons']);self.assertFalse(r['production_allowed']);self.assertEqual(r['source_admission'],'UNKNOWN')
 def test_complete_still_not_admitted(self):
  self.x['rows'].append({'symbol':'A.000002','observation':'SYNTHETIC ONLY'});r=self.runone();self.assertEqual(r['missing_symbols'],[]);self.assertFalse(r['business_accepted'])
 def test_scope(self):
  self.x['scope'].reverse()
  with self.assertRaisesRegex(ValueError,'SCOPE'):self.runone()
 def test_late(self):
  self.x['available_at']='2026-11-06T09:25:00+08:00'
  with self.assertRaisesRegex(ValueError,'NOT_AVAILABLE'):self.runone()
 def test_real_rejected(self):
  self.x['data_kind']='REAL'
  with self.assertRaisesRegex(ValueError,'SYNTHETIC_ONLY'):self.runone()
 def test_duplicates_rejected(self):
  self.x['rows']*=2
  with self.assertRaisesRegex(ValueError,'DUPLICATE'):self.runone()
 def test_outside_scope(self):
  self.x['rows'][0]['symbol']='A.000003'
  with self.assertRaisesRegex(ValueError,'ROW_SCOPE'):self.runone()
 def test_naive_time(self):
  self.x['observed_at']='2026-11-06T09:15:00'
  with self.assertRaisesRegex(ValueError,'TIMEZONE'):self.runone()
 def test_wrong_date(self):
  self.x['target_date']='20261105'
  with self.assertRaisesRegex(ValueError,'DATE'):self.runone()
 def test_observation_type(self):
  self.x['rows'][0]['observation']=123
  with self.assertRaisesRegex(ValueError,'TEXT'):self.runone()
 def test_inverted_time(self):
  self.x['available_at']='2026-11-06T09:14:59+08:00'
  with self.assertRaisesRegex(ValueError,'TIME_ORDER'):self.runone()
 def test_source_missing(self):
  self.x['source_reference']=''
  with self.assertRaisesRegex(ValueError,'SOURCE'):self.runone()

class ReviewRegression(unittest.TestCase):
 setUp=Tests.setUp
 runone=Tests.runone
 def test_missing_timestamp(self):
  del self.x['observed_at']
  with self.assertRaisesRegex(ValueError,'TIMESTAMP_REQUIRED'):self.runone()
 def test_wrong_timestamp_type(self):
  self.x['available_at']=42
  with self.assertRaisesRegex(ValueError,'TIMESTAMP_REQUIRED'):self.runone()
 def test_malformed_timestamp(self):
  self.x['available_at']='not a time'
  with self.assertRaisesRegex(ValueError,'TIMESTAMP_INVALID'):self.runone()
 def test_freshness_remains_unknown(self):
  self.x['observed_at']=self.x['available_at']='2026-11-06T00:00:00+08:00'
  r=self.runone();self.assertEqual(r['freshness_admission'],'UNKNOWN');self.assertIn('FRESHNESS_CONTRACT_UNKNOWN',r['blocking_reasons'])
 def test_output_provenance_detached(self):
  import hashlib,json
  original=copy.deepcopy(self.x);r=self.runone()
  self.assertEqual(r['recorded_input'], original)
  self.assertEqual(r['input_canonical_sha256'],hashlib.sha256(json.dumps(original,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest())
  self.x['rows'][0]['observation']='changed';self.assertEqual(r['recorded_input'],original)
 def test_schema_market(self):
  for key in ('schema','market'):
   x=copy.deepcopy(self.x);self.x[key]='wrong'
   with self.assertRaisesRegex(ValueError,'SCHEMA_MARKET'):self.runone()
   self.x=x
 def test_empty_duplicate_scope(self):
  for scope in ([],['A.000001','A.000001']):
   self.x['scope']=scope
   with self.assertRaisesRegex(ValueError,'SCOPE'):self.runone()
 def test_cross_date(self):
  self.x['observed_at']='2026-11-05T09:15:00+08:00'
  with self.assertRaisesRegex(ValueError,'SOURCE_DATE'):self.runone()
 def test_boundary_after_cutoff(self):
  self.x['available_at']='2026-11-06T09:15:00.000001+08:00'
  with self.assertRaisesRegex(ValueError,'NOT_AVAILABLE'):self.runone()
 def test_utc_equivalent(self):
  self.x['observed_at']=self.x['available_at']='2026-11-06T01:15:00+00:00'
  self.assertFalse(self.runone()['production_allowed'])
 def test_target_type(self):
  self.x['target_date']=42
  with self.assertRaisesRegex(ValueError,'TARGET_DATE'):inspect_synthetic(self.x,target_date=42,registered_scope=self.x['scope'])
 def test_unexpected_fields(self):
  self.x['price']=float('nan')
  with self.assertRaisesRegex(ValueError,'FIELDS'):self.runone()
 def test_error_code(self):
  try:inspect_synthetic({},target_date='20261106',registered_scope=())
  except ValueError as e:self.assertEqual(e.code,'SYNTHETIC_ONLY')
  else:self.fail('accepted')
