import datetime as dt
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from material_pack import assemble, freeze

class MaterialPackTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  self.now=dt.datetime(2026,11,7,0,0,tzinfo=dt.timezone.utc)
  self.records=[]
  for kind in ('announcements','essential_news','preopen_memo','preopen_analysis'):
   p=self.root/(kind+'.txt');p.write_text('actual fixture, not market evidence')
   self.records.append(dict(category=kind,path=p.name,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),source_date='2026-11-07',source_url='https://example.test/source',published_at='2026-11-07T07:00:00+08:00',retrieved_at='2026-11-07T07:10:00+08:00',title=kind))
 def pack(self,records=None,**kw):
  return assemble(self.root,'morning-materials','2026-11-07',self.records if records is None else records,self.now,**kw)
 def test_complete_is_review_only(self):
  p=self.pack();self.assertEqual(p['assembly_status'],'READY_FOR_REVIEW');self.assertFalse(p['business_accepted']);self.assertFalse(p['natural_verified'])
 def test_missing(self):self.assertEqual(self.pack([])['assembly_status'],'BLOCKED')
 def test_bad_hash(self):
  self.records[0]['sha256']='0'*64;self.assertEqual(self.pack()['assembly_status'],'BLOCKED')
 def test_missing_file(self):
  (self.root/self.records[0]['path']).unlink();self.assertEqual(self.pack()['assembly_status'],'BLOCKED')
 def test_old_date(self):
  self.records[0]['source_date']='2026-11-06';self.assertEqual(self.pack()['assembly_status'],'BLOCKED')
 def test_naive_time(self):
  with self.assertRaises(ValueError):assemble(self.root,'night','2026-11-07',[],self.now.replace(tzinfo=None))
 def test_wrong_target_day(self):
  with self.assertRaises(ValueError):assemble(self.root,'night','2026-11-06',[],self.now)
 def test_traversal(self):
  self.records[0]['path']='../x';self.assertEqual(self.pack()['assembly_status'],'BLOCKED')
 def test_symlink(self):
  p=self.root/self.records[0]['path'];p.unlink();p.symlink_to(self.root/self.records[1]['path']);self.assertEqual(self.pack()['assembly_status'],'BLOCKED')
 def test_duplicate_dedup(self):self.assertEqual(len(self.pack(self.records+self.records)['items']),4)
 def test_future_publication(self):
  self.records[0]['published_at']='2026-11-08T07:00:00+08:00';self.assertEqual(self.pack()['assembly_status'],'BLOCKED')
 def test_missing_source(self):
  del self.records[0]['source_url'];self.assertEqual(self.pack()['assembly_status'],'BLOCKED')
 def test_conflicting_record(self):
  other=dict(self.records[0],title='changed');p=self.pack(self.records+[other]);self.assertEqual(p['assembly_status'],'BLOCKED')
 def test_changed_input_new_identity(self):
  first=self.pack();self.records[0]['title']='updated';self.assertNotEqual(first['identity'],self.pack()['identity'])
 def test_unknown_node_refuses(self):
  with self.assertRaises(ValueError):assemble(self.root,'invented','2026-11-07',[],self.now)
 def test_freeze_readback(self):
  r=freeze(self.root/'outputs',self.pack());self.assertEqual(r['byte_readback'],'PASS');self.assertFalse(r['uploaded'])
 def test_freeze_idempotent(self):
  a=freeze(self.root/'outputs',self.pack());b=freeze(self.root/'outputs',self.pack());self.assertEqual(a['path'],b['path']);self.assertTrue(b['reused'])
 def test_freeze_changed_bytes_refuses(self):
  a=freeze(self.root/'outputs',self.pack());Path(a['path']).write_text('changed')
  with self.assertRaises(ValueError):freeze(self.root/'outputs',self.pack())
 def test_night_categories_not_morning(self):
  p=assemble(self.root,'night','2026-11-07',self.records,self.now);self.assertEqual(p['assembly_status'],'BLOCKED')
 def test_input_not_modified(self):
  before=[(self.root/r['path']).read_bytes() for r in self.records];self.pack();self.assertEqual(before,[(self.root/r['path']).read_bytes() for r in self.records])
if __name__=='__main__':unittest.main()
