import contextlib,copy,json,pathlib,tempfile,unittest
from unittest.mock import patch
import registered as m
class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(dir=m.HERE);self.folder=pathlib.Path(self.tmp.name)
  self.gate_calls=0;self.lock_entries=0
 def tearDown(self):self.tmp.cleanup()
 def gate(self):self.gate_calls+=1
 @contextlib.contextmanager
 def guard(self,identity):
  if identity!='SYNTHETIC_TEST_OWNER':raise ValueError('OWNER')
  self.lock_entries+=1;yield
 def put(self,name,obj):
  f=self.folder/name;b=m.canonical(obj);f.write_bytes(b)
  return {'path':str(f.relative_to(m.ROOT)),'sha256':m.sha(b),'bytes':len(b)}
 def fixture(self,node):
  day='20261109';groups=('original','nav_smallk','nav_pullback','nav_breakout')
  panel={'schema':'PAR_SCREEN_DISPLAY_V1','source_date':day,'scope_count':5575,'partitions':{'COMPUTED_CURRENT':5575},'counts':{g:{'after_risk':{'TRUE':0,'FALSE':5575,'UNKNOWN':0}} for g in groups},'dedup_selected':0,'dedup_pending':0,'rows':[{'symbol':f'{i:06}.SZ','name':'SYNTHETIC','owner_outcome':'COMPUTED_CURRENT','source_family':'SYNTHETIC','actual_date':day,'layers':{g:{'after_risk':'FALSE'} for g in groups}} for i in range(5575)]}
  top={'schema':'DATED_FIXED_REFERENCE_TOP200_V1','source_date':day,'scope_count':5575,'rows':[{'symbol':f'{i:06}.SZ','rank':i+1,'actual_date':day,'change_pct_display':'0'} for i in range(200)]}
  policy={'node':node,'domain':'synthetic','version':'fixture1','original_policy_reference':'SYNTHETIC_NOT_ORIGINAL_AUTHORITY','panel_denominator':5575,'top_schema':'DATED_FIXED_REFERENCE_TOP200_V1','semantic_keys':['X.close'], 'key_definitions':{'X.close':{'symbol':'X','field':'close','unit':'points','basis':'unadjusted','currency':None,'asof':day}},'source_ids':['S1','S2'],'required_comparisons':[{'symbol':'X','field':'open','source_ids':['S1','S2']}],'max_observation_age_seconds':600}
  obs={'source_day':'2026-11-09','records':[{'id':s,'source_id':s,'observed_at':'2026-11-09T06:55:00+08:00','available_at':'2026-11-09T06:56:00+08:00','source_date':'2026-11-09','symbol':'X','field':'open','value':'1','url':'https://example.org/'+s} for s in ['S1','S2']]}
  multi={'sources':{s:{'available_at':'2026-11-09T06:00:00+08:00','facts':[{'key':'X.close','definition':policy['key_definitions']['X.close'],'value':'1'}]} for s in ['S1','S2']}}
  docs={'panel':panel,'top':top,'observations':obs,'multi_source':multi}
  inputs={k:self.put(k+'.json',v) for k,v in docs.items()}
  inputs['pit']=self.put('pit.json',{'business_date':day,'source_date':day,'input_sha256':{k:v['sha256'] for k,v in inputs.items()},'known_by_cutoff':True,'source_admission':True,'latest_available_at':'2026-11-09T06:00:00+08:00'})
  reg={'node':node,'run_id':'SYNTHETIC_'+node,'environment_id':'SYNTHETIC_ENV','domain':'synthetic','business_date':day,'source_date':day,'cutoff':'2026-11-09T06:59:00+08:00','inputs':inputs,'policy':self.put('policy.json',policy),'owner_identity':'SYNTHETIC_TEST_OWNER','owner_guard_factory':self.guard,'output_relative':str((self.folder/'outputs').relative_to(m.ROOT)),'adapter_sha256':m.sha((m.HERE/'registered.py').read_bytes())}
  reg['review']=self.put('review.json',{'verdict':'APPROVED','contract_sha256':m.contract_identity(reg),'domain':'synthetic','independent_reviewer_identity':'SYNTHETIC_FIXTURE_NOT_HUMAN_REVIEW','policy_sha256':reg['policy']['sha256']})
  return reg
 def runreg(self,reg):
  with patch.object(m,'TRUSTED_RUNS',(reg,)):return m.dispatch(reg['node'],reg['run_id'],reg['environment_id'],self.gate)
 def test_four_dated_paths_and_reuse(self):
  for n in m.NODES:
   with self.subTest(n=n):
    reg=self.fixture(n);a=self.runreg(reg);b=self.runreg(reg)
    self.assertIn(a['status'],('REVIEWED_FREEZE_MANIFEST_READY','RECONCILED','LIST_AND_PROMPT_READY','BLOCKED_DELIVERY_ASSEMBLY_NOT_BOUND'))
    self.assertTrue(b['saved']['reused']);self.assertFalse(a['natural_verified'])
    d=json.loads(pathlib.Path(a['saved']['path']).read_text());self.assertEqual(d['business_date'],'20261109')
    if n=='freeze':self.assertFalse(d['result']['formal_freeze'])
    if n=='opening-prep':self.assertEqual(len(d['result']['rows']),200)
    if n=='morning-delivery':
     self.assertEqual(d['result']['status'],'BLOCKED_DELIVERY_ASSEMBLY_NOT_BOUND');self.assertEqual(d['result']['delivery_status'],'NOT_SENT');self.assertFalse(d['result']['business_accepted']);self.assertNotIn('rows',d['result'])
 def test_unregistered(self):self.assertEqual(m.dispatch('freeze','x','y',self.gate)['jobs_started'],0)
 def test_missing_review(self):
  r=self.fixture('freeze');r['review']['sha256']='0'*64
  with self.assertRaisesRegex(ValueError,'PIN'):self.runreg(r)
  self.assertEqual(self.lock_entries,0)
 def test_missing_guard(self):
  r=self.fixture('freeze');r.pop('owner_guard_factory')
  with self.assertRaisesRegex(ValueError,'GUARD_MISSING'):self.runreg(r)
 def test_pin_change(self):
  r=self.fixture('freeze');(m.ROOT/r['inputs']['panel']['path']).write_text('{}')
  with self.assertRaisesRegex(ValueError,'PIN'):self.runreg(r)
 def test_review_invalid_after_date_change(self):
  r=self.fixture('freeze');r['source_date']='20261106'
  with self.assertRaisesRegex(ValueError,'REVIEW_REQUIRED'):self.runreg(r)
 def test_after_cutoff_blocked(self):
  r=self.fixture('freeze');safe=m.module('safeio');p,d=m.verify(r,safe);d['multi_source']['sources']['S1']['available_at']='2026-11-09T17:16:00+08:00'
  with self.assertRaisesRegex(ValueError,'SOURCE_AFTER_CUTOFF'):m.calculate(r,p,d,safe)
 def test_conflict_and_unknown_block_freeze(self):
  r=self.fixture('freeze');safe=m.module('safeio');p,d=m.verify(r,safe)
  for value in ('2',None):
   d['multi_source']['sources']['S1']['facts'][0]['value']=value
   self.assertEqual(m.calculate(r,p,d,safe)['status'],'BLOCKED_SOURCE_REVIEW')
 def test_gate_prevents_work(self):
  r=self.fixture('freeze')
  def bad():raise ValueError('MEMORY')
  with patch.object(m,'TRUSTED_RUNS',(r,)):
   with self.assertRaisesRegex(ValueError,'MEMORY'):m.dispatch(r['node'],r['run_id'],r['environment_id'],bad)
  self.assertEqual(self.lock_entries,0)
if __name__=='__main__':unittest.main()
