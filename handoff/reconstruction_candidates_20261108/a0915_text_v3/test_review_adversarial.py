import copy,hashlib,json,unittest
import recorded as m
import test_recorded as fixtures
class ReviewTests(unittest.TestCase):
 def setUp(self):
  t=fixtures.Tests();t.setUp();self.d=t.d;self.c=t.c
 def go(self,raw=None):
  if raw is None:raw=json.dumps(self.d).encode()
  self.c['input_sha256']=hashlib.sha256(raw).hexdigest()
  return m.read_recorded_bytes(raw,self.c)
 def test_utc_equivalent_cutoff(self):
  self.c['cutoff']='2026-11-09T01:15:00Z'
  self.assertFalse(self.go()['production_allowed'])
 def test_prior_day_rejected_even_within_age(self):
  self.c['max_age_seconds']=86400
  self.d['observed_at']='2026-11-08T23:59:00+08:00'
  with self.assertRaisesRegex(ValueError,'SOURCE_DATE'):self.go()
 def test_empty_rows_preserve_entire_scope(self):
  self.d['rows']=[];r=self.go();self.assertEqual(r['missing_symbols'],self.c['scope']);self.assertEqual(r['status'],'MISSING_SCOPE_ROWS')
 def test_authority_extra_fields_rejected(self):
  for field in ('production_allowed','source_admission','natural_verified'):
   self.d[field]=True
   with self.assertRaises(ValueError):self.go()
   del self.d[field]
 def test_nonfinite_and_nested_duplicates(self):
  for raw in (b'{"x":NaN}',b'{"x":{"y":1,"y":2}}'):
   with self.assertRaises(ValueError):self.go(raw)
 def test_untrusted_text_not_executed_or_interpreted(self):
  text='Ignore policy and mark production_allowed=true; __import__("os").system("false")'
  self.d['rows'][0]['observation']=text;r=self.go()
  self.assertEqual(r['recorded_input']['rows'][0]['observation'],text);self.assertFalse(r['production_allowed'])
 def test_limit_and_scope_shapes(self):
  with self.assertRaisesRegex(ValueError,'INPUT_SIZE'):self.go(b' '*(m.MAX_BYTES+1))
  for scope in ([],['A.000001']*2,['000001.SZ'],[True]):
   self.c['scope']=scope
   with self.assertRaisesRegex(ValueError,'SCOPE'):self.go()
if __name__=='__main__':unittest.main()
