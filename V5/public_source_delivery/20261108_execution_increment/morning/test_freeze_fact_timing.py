import unittest,copy
import registered as r

def fixture():
 key='x';definition={'symbol':'000001.SZ','field':'close','unit':'price','basis':'raw','currency':'CNY','asof':'2026-11-09T06:29:00+08:00'}
 policy={'semantic_keys':[key],'source_ids':['s1','s2'],'key_definitions':{key:definition},'semantic_max_age_seconds':{key:60}}
 row={'key':key,'definition':definition,'value':1,'observed_at':'2026-11-09T06:29:00+08:00','available_at':'2026-11-09T06:29:30+08:00'}
 doc={'sources':{s:{'available_at':'2026-11-09T06:29:30+08:00','facts':[copy.deepcopy(row)]} for s in ['s1','s2']}}
 return doc,policy,r.time('2026-11-09T06:30:00+08:00')
class Tests(unittest.TestCase):
 def test_matching_values(self):self.assertTrue(r.semantic_compare(*fixture())['passed'])
 def test_postcutoff_fact_in_early_envelope(self):
  a,b,c=fixture();a['sources']['s1']['facts'][0]['available_at']='2026-11-09T06:31:00+08:00'
  with self.assertRaises(ValueError):r.semantic_compare(a,b,c)
 def test_stale(self):
  a,b,c=fixture();a['sources']['s1']['facts'][0]['observed_at']='2026-11-09T06:28:59+08:00'
  with self.assertRaises(ValueError):r.semantic_compare(a,b,c)
 def test_missing_timing(self):
  for field in ('observed_at','available_at'):
   a,b,c=fixture();del a['sources']['s1']['facts'][0][field]
   with self.assertRaises(ValueError):r.semantic_compare(a,b,c)
 def test_policy_required(self):
  for value in (None,{}, {'x':True},{'x':0},{'x':60,'other':60}):
   a,b,c=fixture();b['semantic_max_age_seconds']=value
   with self.assertRaises(ValueError):r.semantic_compare(a,b,c)
 def test_impossible_and_naive(self):
  for field,value in [('observed_at','2026-11-09T06:29:31+08:00'),('available_at','2026-11-09T06:29:30')]:
   a,b,c=fixture();a['sources']['s1']['facts'][0][field]=value
   with self.assertRaises(ValueError):r.semantic_compare(a,b,c)
 def test_envelope_before_row(self):
  a,b,c=fixture();a['sources']['s1']['available_at']='2026-11-09T06:29:29+08:00'
  with self.assertRaises(ValueError):r.semantic_compare(a,b,c)
 def test_null_remains_unknown(self):
  a,b,c=fixture();a['sources']['s1']['facts'][0]['value']=None;x=r.semantic_compare(a,b,c);self.assertFalse(x['passed']);self.assertEqual(x['unknown'],[['s1','x']])
if __name__=='__main__':unittest.main()
