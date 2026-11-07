import unittest,json,hashlib
from adapter import adapt
class Tests(unittest.TestCase):
 def setUp(self):
  self.day='2030-01-02';self.code='00001'
  self.scope={'source_date':self.day,'complete_structural_check':True,'rows':[{'code':self.code,'security_type':'UNKNOWN'}]}
  self.obj={'rc':0,'data':{'code':self.code,'market':116,'name':'SYNTHETIC ONLY','preKPrice':999,'klines':[self.day+',10,11,12,9,100,1000,0,0,0,0']}}
  self.url='https://push2his.eastmoney.com/api/qt/stock/kline/get?secid=116.00001&klt=101&fqt=0&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61&beg=20300102&end=20300102'
 def runone(self,raw=True,url=None,digest=None):
  b=json.dumps(self.obj).encode();receipt={'url':url or self.url,'sha256':digest or hashlib.sha256(b).hexdigest(),'status':200}
  return adapt({self.code:b} if raw else {},self.scope,self.day,[self.code],{self.code:receipt})
 def test_synthetic_not_admitted(self):
  r=self.runone();self.assertEqual(r['parsed_count'],1);self.assertIsNone(r['rows'][0]['pre_close']);self.assertEqual(r['rows'][0]['security_type'],'UNKNOWN')
  for k in ['production_allowed','original_contract_export_allowed','natural_verified','orders_sent']:self.assertFalse(r[k])
  self.assertEqual(r['gates']['cas_event'],'UNKNOWN');self.assertEqual(r['gates']['futu_scope_equivalence'],'UNKNOWN')
 def test_missing(self):self.assertEqual(self.runone(False)['failures'][0]['reason'],'RESPONSE_MISSING')
 def test_provenance(self):
  for kw in [dict(url=self.url.replace('fqt=0','fqt=1')),dict(digest='0'*64)]:self.assertEqual(self.runone(**kw)['parsed_count'],0)
 def test_scope_and_date(self):
  self.scope['source_date']='2030-01-01'
  with self.assertRaises(ValueError):self.runone()
  self.scope['source_date']=self.day;self.scope['rows'].append(self.scope['rows'][0])
  with self.assertRaises(ValueError):self.runone()
 def test_bad_values_and_identity(self):
  self.obj['data']['code']='00002';self.assertEqual(self.runone()['parsed_count'],0)
  self.obj['data']['code']=self.code;self.obj['data']['klines']=[self.day+',NaN,11,12,9,100,1000,0,0,0,0'];self.assertEqual(self.runone()['parsed_count'],0)
 def test_duplicate_target(self):
  self.obj['data']['klines']*=2;self.assertEqual(self.runone()['parsed_count'],0)
if __name__=='__main__':unittest.main()
