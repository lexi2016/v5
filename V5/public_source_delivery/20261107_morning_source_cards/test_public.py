import tempfile,sqlite3,json,hashlib,unittest
from pathlib import Path
from build_cards import build
from node_results_api import NodeResultsService
class Synthetic(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.p=Path(self.t.name);self.db=self.p/'synthetic.sqlite3';c=sqlite3.connect(self.db);c.executescript('create table panel(symbol text,name text,actual_date text);create table top200(symbol text,rank integer,actual_date text);')
  for i in range(200):c.execute('insert into panel values(?,?,?)',(f'SYNTHETIC{i:03}',f'SyntheticName{i:03}','20000101'));c.execute('insert into top200 values(?,?,?)',(f'SYNTHETIC{i:03}',i+1,'20000101'))
  c.commit();c.close();self.digest=hashlib.sha256(self.db.read_bytes()).hexdigest();self.texts=self.p/'texts';self.texts.mkdir();records=[]
  for i in range(3):
   f=self.texts/f'synthetic{i}.txt';f.write_text('SyntheticName000 <not real source>');b=f.read_bytes();records.append({'file':f.name,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'url':'https://example.invalid/synthetic','published_time_raw':'2000-01-02T09:00:00','timezone':'UNKNOWN'})
  (self.texts/'RECEIPT.json').write_text(json.dumps({'data_date':'2000-01-01','records':records}))
 def runbuild(self):return build(self.db,self.texts,self.p/'out',self.digest)
 def test_synthetic_name_association_not_identity(self):
  r=self.runbuild();self.assertEqual((r['denominator'],r['matched_symbols'],r['mention_lines']),(200,1,3));self.assertFalse(r['business_accepted']);self.assertFalse(r['natural_verified']);self.assertTrue(all(x['identity_review']=='UNKNOWN' and x['factual_verification']=='UNKNOWN' for x in r['cards']));self.assertIn('&lt;not real source&gt;',(self.p/'out/index.html').read_text())
 def test_database_changed_refuses(self):
  with self.assertRaises(ValueError):build(self.db,self.texts,self.p/'out','0'*64)
  self.assertFalse((self.p/'out').exists())
 def test_text_changed_refuses(self):
  (self.texts/'synthetic0.txt').write_text('modified')
  with self.assertRaises(ValueError):self.runbuild()
 def test_no_overwrite(self):
  self.runbuild();before=(self.p/'out/cards.json').read_bytes()
  with self.assertRaises(FileExistsError):self.runbuild()
  self.assertEqual(before,(self.p/'out/cards.json').read_bytes())
 def test_wrong_denominator(self):
  c=sqlite3.connect(self.db);c.execute('delete from top200 where rank=200');c.commit();c.close();self.digest=hashlib.sha256(self.db.read_bytes()).hexdigest()
  with self.assertRaisesRegex(ValueError,'denominator'):self.runbuild()
 def test_missing_inputs(self):
  (self.texts/'RECEIPT.json').unlink()
  with self.assertRaises(FileNotFoundError):self.runbuild()
 def test_api_private_binding_refused(self):
  with self.assertRaisesRegex(ValueError,'NO_APPROVED_PRIVATE'):NodeResultsService(lambda:None).get('morning-materials','20000102')
if __name__=='__main__':unittest.main()
