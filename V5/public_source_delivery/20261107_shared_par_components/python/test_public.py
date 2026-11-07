import tempfile,pathlib,sqlite3,unittest
from unittest.mock import patch
import database,catalog_api
class Public(unittest.TestCase):
 def test_build_refuses_without_creating_file(self):
  with tempfile.TemporaryDirectory() as t:
   p=pathlib.Path(t)/'catalog.sqlite3'
   with self.assertRaisesRegex(ValueError,'NO_APPROVED_PRIVATE'):database.build(p)
   self.assertEqual(list(p.parent.iterdir()),[])
 def test_default_read_refuses(self):
  with self.assertRaises(ValueError):database.connect()
  with self.assertRaises(ValueError):database.summary('20261106','MAIN_PLUS_SINA69_407')
 def test_catalog_refuses_binding(self):
  called=[]
  with self.assertRaisesRegex(ValueError,'NO_APPROVED_PRIVATE'):catalog_api.CatalogService(lambda:called.append(True)).get('20261106','merge407')
  self.assertEqual(called,[True])
 def test_resource_failure_preserved(self):
  def gate():raise ValueError('RESOURCE_MEMORY_HEADROOM')
  with self.assertRaisesRegex(ValueError,'RESOURCE_MEMORY'):catalog_api.CatalogService(gate).get('20261106','merge407')
 def test_version_not_fallback(self):
  with self.assertRaisesRegex(ValueError,'CATALOG_VERSION'):catalog_api.CatalogService(lambda:None).get('20000101','other')
 def test_lock_bounded(self):
  class Lock:
   def acquire(self,**kw):self.timeout=kw['timeout'];return False
  c=catalog_api.CatalogService(lambda:None);c.lock=Lock()
  with self.assertRaisesRegex(ValueError,'RESOURCE_BUSY'):c.get('20261106','merge407')
  self.assertEqual(c.lock.timeout,95)
 def test_synthetic_sqlite_schema_readonly(self):
  with tempfile.TemporaryDirectory() as t:
   p=pathlib.Path(t)/'synthetic.sqlite3';c=sqlite3.connect(p);c.executescript(database.SCHEMA)
   c.execute("insert into panel(symbol,record_json) values('SYNTHETIC','{}')");c.execute("insert into layer values('SYNTHETIC','original','after_risk','UNKNOWN')");c.commit();c.close()
   with database.connect(p) as reader:
    self.assertEqual(reader.execute('select count(*) from pending').fetchone()[0],1)
    self.assertEqual(reader.execute('select count(*) from selected').fetchone()[0],0)
    with self.assertRaises(sqlite3.OperationalError):reader.execute("delete from panel")
if __name__=='__main__':unittest.main()
