import unittest
import execution
class Tests(unittest.TestCase):
 def test_unbound_blocks(self):
  self.assertEqual(execution.run('1830','missing')['status'],'BLOCKED')
 def test_wrong_stage(self):
  with self.assertRaises(ValueError):execution.run('1700','missing')

import contextlib,tempfile,json
from pathlib import Path
class DynamicTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.calls=0
  @contextlib.contextmanager
  def owner():
   self.calls+=1
   yield
  self.owner=owner;self.configure('20261109','20261110')
 def tearDown(self):execution.REGISTRY.clear();self.tmp.cleanup()
 def configure(self,date,obs):
  groups=('original','nav_smallk','nav_pullback','nav_breakout')
  self.d={'qualifications':{'no_buy':True,'production_allowed':False,'research_display_allowed':True},'source_date':date,'calculation_date':date,'observation_date':obs,'scope_count':2,'dedup_selected':1,'dedup_pending':1,'rows':[{'symbol':'000001.SZ','layers':{g:{'after_risk':'TRUE' if g=='original' else 'FALSE'} for g in groups}},{'symbol':'000002.SZ','layers':{g:{'after_risk':'UNKNOWN'} for g in groups}}],'counts':{g:{'after_risk':{'TRUE':1 if g=='original' else 0,'FALSE':0 if g=='original' else 1,'UNKNOWN':1}} for g in groups}}
  self.ad={'status':'PASS_RESEARCH_MERGE_DISPLAY_ONLY','production_allowed':False,'research_display_allowed':True,'scope_count':2,'dedup_selected':1,'dedup_pending':1,'group_true':[1,0,0,0]}
  execution.REGISTRY['synthetic']={'input_root':self.root,'output_root':self.root/'out','owner_context':self.owner,'data_date':date,'observation_date':obs,'scope_count':2,'binding_version':'MOCK_ONLY','data':self.pin('data.json',self.d),'admission':self.pin('ad.json',self.ad)}
 def pin(self,name,obj):
  raw=json.dumps(obj).encode();(self.root/name).write_bytes(raw)
  return {'path':name,'sha256':execution.sha(raw),'bytes':len(raw)}
 def test_three_stages_reuse_and_dates(self):
  a=execution.run('1830','synthetic');b=execution.run('1830','synthetic');self.assertTrue(b['reused'])
  for stage in ('1850','1900'):
   r=execution.run(stage,'synthetic',a['package_id']);self.assertFalse(r['sent']);self.assertFalse(r['natural_verified'])
  self.assertEqual(self.calls,4)
  summary=json.loads((Path(a['path'])/'summary.json').read_text());self.assertEqual(summary['pending'],1)
  self.configure('20261110','20261111');c=execution.run('1830','synthetic');self.assertNotEqual(c['package_id'],a['package_id'])
 def test_input_change_invalidates(self):
  a=execution.run('1830','synthetic');self.d['rows'][0]['name']='changed'
  execution.REGISTRY['synthetic']['data']=self.pin('data.json',self.d)
  with self.assertRaisesRegex(ValueError,'PACKAGE_VERSION'):execution.run('1850','synthetic',a['package_id'])
 def test_manifest_cannot_grant_delivery(self):
  a=execution.run('1830','synthetic');p=Path(a['path'])/'manifest.json';m=json.loads(p.read_text());m['sent']=True;p.write_text(json.dumps(m))
  with self.assertRaisesRegex(ValueError,'OUTPUT_CHANGED'):execution.run('1900','synthetic',a['package_id'])
 def test_missing_prepare(self):
  with self.assertRaises(ValueError):execution.run('1850','synthetic','a'*64)
 def test_wrong_date(self):
  execution.REGISTRY['synthetic']['data_date']='20261110'
  with self.assertRaisesRegex(ValueError,'DATE_BINDING'):execution.run('1830','synthetic')
 def test_gate_failure(self):
  @contextlib.contextmanager
  def fail():raise ValueError('ORIGINAL_RESOURCE_OR_LOCK_GATE');yield
  execution.REGISTRY['synthetic']['owner_context']=fail
  with self.assertRaisesRegex(ValueError,'ORIGINAL_RESOURCE'):execution.run('1830','synthetic')
  self.assertFalse((self.root/'out').exists())
 def test_bad_qualification(self):
  self.d['qualifications']['no_buy']=False;execution.REGISTRY['synthetic']['data']=self.pin('data.json',self.d)
  with self.assertRaisesRegex(ValueError,'DISPLAY_ONLY'):execution.run('1830','synthetic')

if __name__=='__main__':unittest.main()
