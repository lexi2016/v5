"""Synthetic contract tests only; no original research inputs or natural events."""
import unittest,sys,tempfile,json,hashlib,datetime as dt,os,fcntl
from pathlib import Path
from unittest.mock import patch
BASE=Path(__file__).parent/'handoff'
sys.path.insert(0,str(BASE/'evening_nodes_candidate_v3_20261107'))
sys.path.insert(0,str(BASE/'evening_target_date_guard_20261107'))
import adapter,evening,guard
class PublicContract(unittest.TestCase):
 def report(self,rows=[]):return evening.build('1700','20261107',dt.datetime(2026,11,7,9,tzinfo=dt.timezone.utc),rows)
 def test_private_adapter_blocked(self):
  with self.assertRaisesRegex(ValueError,'NO_APPROVED_PRIVATE'):adapter.inspect()
 def test_runtime_blocked(self):
  with self.assertRaisesRegex(ValueError,'NO_APPROVED_RUNTIME'):adapter.snapshot({})
 def test_no_false_success(self):
  r=self.report([{'status':'COMPLETED','data_date':'20261107'}]);self.assertEqual(r['observations'][0]['status'],'UNKNOWN');self.assertEqual(r['report_sections']['done'],[])
 def test_running_not_proven(self):self.assertEqual(self.report([{'status':'RUNNING'}])['observations'][0]['status'],'UNKNOWN')
 def test_empty_never_accepts(self):
  r=self.report();self.assertFalse(r['natural_verified']);self.assertEqual(r['business_status'],'UNKNOWN');self.assertEqual(r['delivery_status'],'NOT_SENT')
 def test_input_identity(self):self.assertNotEqual(self.report()['identity'],self.report([{'status':'FAILED'}])['identity'])
 def test_calendar_original(self):self.assertEqual(self.report()['markets']['a_share'],'NON_TRADING_DAY')
 def test_calendar_pin_failure(self):
  with patch.dict(evening.PINS,{'trading_calendar.py':'0'*64}):
   with self.assertRaisesRegex(ValueError,'CALENDAR_PIN_CHANGED'):self.report()
 def test_target_date(self):
  with self.assertRaisesRegex(ValueError,'TARGET_DATE_NOT_RUNTIME_DATE'):guard.check('20261109',dt.datetime(2026,11,7,tzinfo=dt.timezone.utc))
 def test_synthetic_future_not_natural(self):
  r=guard.check('20261109',dt.datetime(2026,11,9,9,tzinfo=dt.timezone.utc));self.assertEqual(r['target_day_status'],'UNKNOWN');self.assertEqual(r['historical_source_date'],'UNKNOWN');self.assertFalse(r['natural_verified'])
 def test_candidate_version_rejected(self):
  original=Path.read_bytes
  def fake(p):return b'changed' if p==adapter.HERE/'adapter.py' else original(p)
  with patch.object(Path,'read_bytes',fake):
   with self.assertRaisesRegex(ValueError,'V3_CHANGED'):guard.check('20261109',dt.datetime(2026,11,9,9,tzinfo=dt.timezone.utc))
 def test_integrity_and_mutation(self):
  with tempfile.TemporaryDirectory(dir=adapter.HERE) as t:
   p=Path(t)/'fixture.json';p.write_text('{"synthetic":true}');pin=adapter.ref(p);self.assertEqual(adapter.checked(pin),{'synthetic':True});p.write_text('{}')
   with self.assertRaisesRegex(ValueError,'PIN_CHANGED'):adapter.checked(pin)
 def test_escape(self):
  with self.assertRaises(ValueError):adapter.raw_read('../forbidden')
 def test_symlink(self):
  with tempfile.TemporaryDirectory(dir=adapter.HERE) as t:
   p=Path(t);(p/'a').write_text('{}');(p/'b').symlink_to(p/'a')
   with self.assertRaises(OSError):adapter.raw_read(p/'b')
 def test_freeze_idempotence_and_corruption(self):
  with tempfile.TemporaryDirectory(dir=adapter.HERE) as t:
   p=Path(t);r=adapter.freeze({'synthetic':True},p);self.assertEqual(r,adapter.freeze({'synthetic':True},p));m=json.loads((r/'manifest.json').read_text());self.assertFalse(m['uploaded']);self.assertFalse(m['natural_verified']);(r/'report.json').write_text('{}')
   with self.assertRaisesRegex(ValueError,'FROZEN_CONFLICT'):adapter.freeze({'synthetic':True},p)
 def test_active_lock(self):
  with tempfile.TemporaryDirectory(dir=adapter.HERE) as t:
   p=Path(t);fd=os.open(p/'WRITER.lock',os.O_CREAT|os.O_RDWR,0o600)
   try:
    fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
    with self.assertRaises(BlockingIOError):adapter.freeze({'synthetic':True},p)
   finally:os.close(fd)
 def test_partial_never_overwritten(self):
  with tempfile.TemporaryDirectory(dir=adapter.HERE) as t:
   p=Path(t);(p/hashlib.sha256(adapter.canonical({})).hexdigest()).mkdir()
   with self.assertRaises(FileNotFoundError):adapter.freeze({},p)
if __name__=='__main__':unittest.main()
