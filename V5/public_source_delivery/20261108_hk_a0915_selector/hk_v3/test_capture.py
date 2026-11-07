import dataclasses,datetime as dt,json,tempfile,unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
import bridge
from capture import Binding,encode,sha,TZ
class Test(unittest.TestCase):
 def binding(self,node,root):
  time={'hk-open':'09:00:00','hk-continuous-close':'16:00:00','hk-auction-final':'16:09:11'}[node]
  stamp='2026-11-06T'+time+'+08:00';self.count=0;self.locked=False
  x={'schema':'HK_OBSERVATION_V1','node':node,'day':'20261106','scope':['HK.00001'],'source_reference':'SYNTHETIC ONLY','observed_at':stamp,'available_at':stamp,'actual_cas_end':stamp if node=='hk-auction-final' else None,'rows':[{'symbol':'HK.00001','observation':'SYNTHETIC TEST ONLY'}],'data_kind':'SYNTHETIC_TEST'}
  @contextmanager
  def lock():
   self.locked=True
   try:yield
   finally:self.locked=False
  def collect():
   if not self.locked:raise ValueError('LOCK_REQUIRED')
   self.count+=1;return encode(x)
  b=Binding(node,'20261106',('HK.00001',),'SYNTHETIC ONLY','a'*64,'b'*64,sha(encode(x['scope'])),'c'*64,'SYNTHETIC_ENV','SYNTHETIC_JOB',Path(root),lambda day:True,lambda:None,lock,collect,lambda:dt.datetime.fromisoformat(stamp),True)
  return b,x
 def call(self,b):
  with patch.object(bridge,'TRUSTED_RUNS',{'test':b}):return bridge.dispatch(b.node,'test')
 def test_three_real_code_paths_and_dedupe(self):
  for node in ['hk-open','hk-continuous-close','hk-auction-final']:
   with self.subTest(node=node),tempfile.TemporaryDirectory() as t:
    b,x=self.binding(node,t);r=self.call(b)
    self.assertEqual(r['status'],'OBSERVATION_SAVED');self.assertEqual(len(list(Path(t).glob('*.json'))),1);self.assertFalse(r['business_verified'])
    self.assertTrue(self.call(b)['reused']);self.assertEqual(self.count,1)
 def test_refusals(self):
  for reason in ['cas','calendar','date','source','resource','scope']:
   with self.subTest(reason=reason),tempfile.TemporaryDirectory() as t:
    b,x=self.binding('hk-auction-final',t)
    if reason=='cas':x['actual_cas_end']=None
    if reason=='calendar':b=dataclasses.replace(b,calendar=lambda day:None)
    if reason=='date':b=dataclasses.replace(b,day='20261109')
    if reason=='source':x['source_reference']='UNKNOWN'
    if reason=='resource':
     def deny():raise ValueError('ORIGINAL_RESOURCE_GATE')
     b=dataclasses.replace(b,gate=deny)
    if reason=='scope':x['rows'][0]['symbol']='HK.00002'
    r=self.call(b);self.assertEqual(r['status'],'BLOCKED');self.assertEqual(list(Path(t).glob('*.json')),[])
 def test_changed_output_refuses_reuse(self):
  with tempfile.TemporaryDirectory() as t:
   b,x=self.binding('hk-open',t);r=self.call(b);p=next(Path(t).glob('*.json'));v=json.loads(p.read_text());v['source']['rows']=[];p.write_text(json.dumps(v));self.assertEqual(self.call(b)['status'],'BLOCKED');self.assertEqual(self.count,1)
 def test_result_metadata_tampering(self):
  for key,value in [('schema','FAKE'),('run_id','OTHER'),('status','BUSINESS_COMPLETE'),('missing_symbols',['HK.00001']),('business_verified',True),('natural_verified',True),('production_allowed',True),('orders_sent',True),('reused',True)]:
   with self.subTest(key=key),tempfile.TemporaryDirectory() as t:
    b,x=self.binding('hk-open',t);self.call(b);p=next(Path(t).glob('*.json'));v=json.loads(p.read_text());v[key]=value;p.write_text(json.dumps(v))
    self.assertEqual(self.call(b)['status'],'BLOCKED');self.assertEqual(self.count,1)
 def test_post_collection_clock(self):
  with tempfile.TemporaryDirectory() as t:
   b,x=self.binding('hk-continuous-close',t);x['available_at']='2026-11-06T16:00:01+08:00'
   times=iter([dt.datetime.fromisoformat(s) for s in ['2026-11-06T16:00:00+08:00','2026-11-06T16:00:02+08:00']]);b=dataclasses.replace(b,clock=lambda:next(times));r=self.call(b)
   self.assertEqual(r['status'],'OBSERVATION_SAVED');self.assertEqual(r['started_at'],'2026-11-06T16:00:00+08:00');self.assertEqual(r['finished_at'],'2026-11-06T16:00:02+08:00')
 def test_clock_day_and_order_refusal(self):
  for after in ['2026-11-07T00:00:00+08:00','2026-11-06T15:59:59+08:00']:
   with self.subTest(after=after),tempfile.TemporaryDirectory() as t:
    b,x=self.binding('hk-continuous-close',t);times=iter([dt.datetime.fromisoformat('2026-11-06T16:00:00+08:00'),dt.datetime.fromisoformat(after)]);b=dataclasses.replace(b,clock=lambda:next(times));self.assertEqual(self.call(b)['status'],'BLOCKED');self.assertEqual(list(Path(t).glob('*.json')),[])
 def test_unregistered(self):self.assertEqual(bridge.dispatch('hk-open','unregistered')['status'],'BLOCKED')
if __name__=='__main__':unittest.main()
