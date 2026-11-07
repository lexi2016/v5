import unittest
import window_adapter_candidate as m
import tempfile, hashlib
from pathlib import Path
from unittest.mock import patch
SYNTHETIC_RUNNER = """def verify_review(*args): pass
def window_state(t,slot):
 seconds=t.hour*3600+t.minute*60+t.second-9*3600
 return 'EARLY' if seconds<0 else 'ON_TIME' if seconds<=30 else 'LATE' if seconds<120 else 'MISSED'
"""
class Window(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  root=Path(self.tmp.name);(root/'runner.py').write_text(SYNTHETIC_RUNNER)
  p=patch.multiple(m,ROOT=root,RUNNER_SHA=hashlib.sha256(SYNTHETIC_RUNNER.encode()).hexdigest());p.start();self.addCleanup(p.stop)
 def test_closed_by_default(self):
  with patch.object(m,'ROOT',None),self.assertRaisesRegex(ValueError,'ORIGINAL_DEPENDENCIES_UNBOUND'):self.call()

 def call(self,start='09:00:20',source='09:00:10',received='09:00:25',day='20261109'):
  date=day[:4]+'-'+day[4:6]+'-'+day[6:];stamp=lambda x:date+'T'+x+'+08:00'
  return m.inspect_window(day,started_at=stamp(start),observed_at=stamp(source),received_at=stamp(received),checked_at=stamp('09:03:00'))
 def test_twenty_seconds_preserved(self):
  r=self.call();self.assertEqual(r['timing_status'],'ON_TIME');self.assertTrue(r['started_at'].endswith('09:00:20+08:00'));self.assertFalse(r['business_accepted']);self.assertTrue(r['status'].startswith('BLOCKED'))
 def test_late_preserved(self):
  self.assertEqual(self.call('09:00:31',received='09:00:40')['timing_status'],'LATE')
  self.assertEqual(self.call('09:00:30',received='09:00:40')['timing_status'],'ON_TIME')
 def test_cutoff_and_early(self):
  for a in [dict(start='09:02:00',received='09:02:01'),dict(start='08:59:59'),dict(received='09:02:00'),dict(source='08:59:59')]:
   with self.assertRaises(ValueError):self.call(**a)
 def test_changed_day_and_naive_rejected(self):
  for stamp in ['2026-11-08T09:00:20+08:00','2026-11-09T09:00:20']:
   with self.assertRaises(ValueError):m.inspect_window('20261109',started_at=stamp,observed_at='2026-11-09T09:00:10+08:00',received_at='2026-11-09T09:00:25+08:00',checked_at='2026-11-09T09:01:00+08:00')
 def test_other_date_same_rule(self):self.assertEqual(self.call(day='20261110')['day'],'20261110')
if __name__=='__main__':unittest.main()
