import copy, unittest
from bundle import render
G=('original','nav_smallk','nav_pullback','nav_breakout')
def fixture():
 d={'source_date':'20261106','calculation_date':'20261106','observation_date':'20261109','scope_count':2,'dedup_selected':1,'dedup_pending':1,'rows':[],'counts':{},'qualifications':{'no_buy':True,'production_allowed':False,'research_display_allowed':True}}
 for symbol,states in [('000001.SZ',['TRUE','FALSE','FALSE','FALSE']),('000002.SZ',['FALSE','UNKNOWN','FALSE','FALSE'])]:d['rows'].append({'symbol':symbol,'name':'测试','actual_date':'20261106','source_family':'fixture','layers':{g:{'after_risk':s} for g,s in zip(G,states)}})
 for g in G:d['counts'][g]={'after_risk':{s:sum(r['layers'][g]['after_risk']==s for r in d['rows']) for s in ('TRUE','FALSE','UNKNOWN')}}
 return d
class Tests(unittest.TestCase):
 def test_render(self):
  o=render(fixture());self.assertIn(b'000001.SZ',o['selected.csv']);self.assertNotIn(b'000002.SZ',o['selected.csv']);self.assertIn(b'000002.SZ',o['pending.csv'])
 def test_dedup_bad(self):
  d=fixture();d['dedup_selected']=2
  with self.assertRaises(ValueError):render(d)
 def test_unknown_not_selected(self):self.assertNotIn(b'000002.SZ',render(fixture())['selected.csv'])
 def test_group_count_bad(self):
  d=fixture();d['counts']['original']['after_risk']['TRUE']=2
  with self.assertRaises(ValueError):render(d)
 def test_duplicate(self):
  d=fixture();d['rows'][1]['symbol']=d['rows'][0]['symbol']
  with self.assertRaises(ValueError):render(d)
 def test_unknown_state(self):
  d=fixture();d['rows'][0]['layers']['original']['after_risk']='PASS'
  with self.assertRaises(ValueError):render(d)
 def test_qualification(self):
  d=fixture();d['qualifications']['production_allowed']=True
  with self.assertRaises(ValueError):render(d)
 def test_input_unchanged(self):
  d=fixture();old=copy.deepcopy(d);render(d);self.assertEqual(d,old)
 def test_csv_injection(self):
  d=fixture();d['rows'][0]['name']='=1+1';self.assertIn(b"'=1+1",render(d)['selected.csv'])
 def test_date_retained(self):
  o=render(fixture());self.assertIn(b'20261106',o['selected.csv']);self.assertIn(b'20261109',o['summary.json'])
if __name__=='__main__':unittest.main()

class PackageTests(unittest.TestCase):
 def setUp(self):
  import bundle,tempfile
  from pathlib import Path
  from unittest.mock import patch
  self.bundle=bundle;self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name);(self.root/'bundle.py').write_bytes(Path(bundle.__file__).read_bytes());self.patch1=patch.object(bundle,'HERE',self.root);self.patch1.start();self.addCleanup(self.patch1.stop);self.patch2=patch.object(bundle,'load',return_value=render(fixture()));self.patch2.start();self.addCleanup(self.patch2.stop)
 def test_package_repeat_reuses(self):
  a=self.bundle.prepare();b=self.bundle.prepare();self.assertEqual(a['package_id'],b['package_id']);self.assertTrue(b['reused'])
 def test_tampered_csv_fails(self):
  a=self.bundle.prepare();(self.root/'frozen'/a['package_id']/'selected.csv').write_bytes(b'bad')
  with self.assertRaises(ValueError):self.bundle.check(a['package_id'])
 def test_changed_code_fails(self):
  a=self.bundle.prepare();(self.root/'bundle.py').write_bytes(b'new')
  with self.assertRaises(ValueError):self.bundle.check(a['package_id'])
 def test_changed_input_fails(self):
  a=self.bundle.prepare();self.patch2.return_value=None
  from unittest.mock import patch
  fresh=render(fixture());fresh['delivery.txt']=b'changed'
  with patch.object(self.bundle,'load',return_value=fresh):
   with self.assertRaises(ValueError):self.bundle.check(a['package_id'])
 def test_package_id_traversal_fails(self):
  with self.assertRaises(ValueError):self.bundle.check('../x')

class ManifestForgeryTests(PackageTests):
 def test_forged_manifest_fields_rejected(self):
  import json,shutil
  for field,value in [('schema','FORGED'),('sent',True),('uploaded',True),('formal_freeze',True),('natural_verified',True),('extra_acceptance','PASS')]:
   with self.subTest(field=field):
    a=self.bundle.prepare();source=self.root/'frozen'/a['package_id'];m=json.loads((source/'manifest.json').read_bytes());m[field]=value;raw=self.bundle.canonical(m);key=self.bundle.sha(raw);target=self.root/'frozen'/key;shutil.copytree(source,target);(target/'manifest.json').write_bytes(raw)
    with self.assertRaisesRegex(ValueError,'MANIFEST_SEMANTICS'):self.bundle.check(key)
