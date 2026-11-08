import unittest,os,pathlib,shutil,tempfile,importlib.util,copy

def fixture():
 reg={'node':'jk-verify','source_date':'20261109','business_date':'20261109','cutoff':'2026-11-09T08:00:00+08:00'}
 urls={s:'https://'+s+'.example.invalid/quote' for s in ('s1','s2')}
 policy={'required_comparisons':[{'symbol':'JK','field':'open','source_ids':['s1','s2'],'semantic_contract':{'unit':'index_points','basis':'unadjusted','currency':'JPY','raw_fields':{s:['open'] for s in urls}}}],'max_observation_age_seconds':60,'provider_catalog':{s:{'independence_group':s,'allowed_urls':[urls[s]]} for s in urls}}
 doc={'source_day':'2026-11-09','records':[{'id':'observation-'+s,'source_id':s,'source_date':'2026-11-09','symbol':'JK','field':'open','comparison_group':'open','unit':'index_points','basis':'unadjusted','currency':'JPY','value':'1','url':urls[s],'observed_at':'2026-11-09T07:59:00+08:00','available_at':'2026-11-09T07:59:30+08:00'} for s in urls]}
 return reg,policy,{'observations':doc}
class Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  package=os.environ.get('MORNING_PACKAGE_ROOT')
  if not package:raise unittest.SkipTest('explicit package root required')
  cls.temp=tempfile.TemporaryDirectory();root=pathlib.Path(cls.temp.name)/'public';shutil.copytree(package,root);entry=root/'20261108_execution_increment/morning/registered.py';shutil.copyfile(pathlib.Path(__file__).with_name('registered.py'),entry)
  spec=importlib.util.spec_from_file_location('jk_semantic_registered',entry);cls.m=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.m);cls.safe=cls.m.module('safeio')
 @classmethod
 def tearDownClass(cls):cls.temp.cleanup()
 def run_case(self,a,b,c):return self.m.calculate(a,b,c,self.safe)
 def test_original_reconcile_success_ids(self):
  x=self.run_case(*fixture());self.assertEqual(x['status'],'RECONCILED');r=x['observations']['comparisons'][0];self.assertEqual(r['provider_ids'],['s1','s2']);self.assertEqual(r['observation_ids'],['observation-s1','observation-s2']);self.assertNotIn('source_ids',r);self.assertFalse(x['source_admission'])
 def test_raw_field_attack(self):
  for value in ('close',None,'UNKNOWN'):
   a,b,c=fixture()
   for row in c['observations']['records']:row['field']=value
   with self.assertRaises(ValueError):self.run_case(a,b,c)
 def test_identical_url_two_ids(self):
  a,b,c=fixture();url=c['observations']['records'][0]['url'];c['observations']['records'][1]['url']=url;b['provider_catalog']['s2']['allowed_urls']=[url]
  with self.assertRaises(ValueError):self.run_case(a,b,c)
 def test_shared_upstream(self):
  a,b,c=fixture();b['provider_catalog']['s2']['independence_group']='s1'
  with self.assertRaises(ValueError):self.run_case(a,b,c)
 def test_url_not_in_catalog(self):
  a,b,c=fixture();c['observations']['records'][0]['url']='https://unknown.invalid'
  with self.assertRaises(ValueError):self.run_case(a,b,c)
 def test_unit_basis_currency(self):
  for field in ('unit','basis','currency'):
   a,b,c=fixture();c['observations']['records'][0][field]='wrong'
   with self.assertRaises(ValueError):self.run_case(a,b,c)
 def test_explicit_alias(self):
  a,b,c=fixture();b['required_comparisons'][0]['semantic_contract']['raw_fields']['s1']=['session_open'];c['observations']['records'][0]['field']='session_open';x=self.run_case(a,b,c);self.assertEqual(x['status'],'RECONCILED');self.assertEqual(x['observations']['comparisons'][0]['raw_source_fields'],['open','session_open']);self.assertEqual(c['observations']['records'][0]['field'],'session_open')
 def test_unknown_values_structured(self):
  for v in (None,'UNKNOWN',True,'NaN','-1'):
   a,b,c=fixture();c['observations']['records'][0]['value']=v;x=self.run_case(a,b,c);self.assertEqual(x['status'],'BLOCKED_MISSING_OR_CONFLICTING_SOURCE');self.assertEqual(len(x['value_gaps']),1)
 def test_required_policy(self):
  a,b,c=fixture();del b['provider_catalog']
  with self.assertRaises(ValueError):self.run_case(a,b,c)
 def test_duplicate_observation(self):
  a,b,c=fixture();c['observations']['records'][1]['id']=c['observations']['records'][0]['id']
  with self.assertRaises(ValueError):self.run_case(a,b,c)
if __name__=='__main__':unittest.main()
