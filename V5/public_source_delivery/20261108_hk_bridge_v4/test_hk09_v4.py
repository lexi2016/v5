import dataclasses,datetime as dt,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import bridge,capture
import test_capture
class HK09V4(unittest.TestCase):
 def test_seconds_late_and_reuse(self):
  for seconds,expected in [(20,'ON_TIME'),(30,'ON_TIME'),(31,'LATE')]:
   with tempfile.TemporaryDirectory() as t:
    f=test_capture.Test();b,x=f.binding('hk-open',t)
    start=f'2026-11-06T09:00:{seconds:02}+08:00';end=f'2026-11-06T09:00:{seconds+1:02}+08:00'
    x.update(observed_at=start,available_at=end)
    clocks=iter([dt.datetime.fromisoformat(start),dt.datetime.fromisoformat(end)])
    b=dataclasses.replace(b,clock=lambda:next(clocks));r=f.call(b)
    self.assertEqual(r['status'],'OBSERVATION_SAVED');self.assertEqual(r['timing_status'],expected)
    self.assertEqual(r['source']['observed_at'],start);self.assertEqual(r['source']['available_at'],end)
    b=dataclasses.replace(b,clock=lambda:dt.datetime.fromisoformat(end));self.assertTrue(f.call(b)['reused']);self.assertEqual(f.count,1)
    p=next(Path(t).glob('*.json'));saved=json.loads(p.read_text());saved['timing_status']='FAKE';p.write_text(json.dumps(saved));self.assertEqual(f.call(b)['status'],'BLOCKED');self.assertEqual(f.count,1)
 def test_cutoff_refuses_before_collect(self):
  with tempfile.TemporaryDirectory() as t:
   f=test_capture.Test();b,x=f.binding('hk-open',t);b=dataclasses.replace(b,clock=lambda:dt.datetime.fromisoformat('2026-11-06T09:02:00+08:00'))
   self.assertEqual(f.call(b)['status'],'BLOCKED');self.assertEqual(f.count,0)
 def test_real_registration_cannot_activate(self):
  with tempfile.TemporaryDirectory() as t:
   f=test_capture.Test();b,x=f.binding('hk-open',t);b=dataclasses.replace(b,synthetic=False)
   r=f.call(b);self.assertEqual(r['reason'],'HK09_REAL_SCOPE_OWNER_RESOURCE_LOCK_UNBOUND');self.assertEqual(f.count,0)
 def test_empty_registry(self):
  self.assertEqual(bridge.TRUSTED_RUNS,{})
  self.assertEqual(bridge.dispatch('hk-open','not_registered')['reason'],'TRUSTED_RUN_NOT_REGISTERED')
 def test_other_branches_have_no_hk09_dependency(self):
  with patch.object(capture,'hk09_times',side_effect=AssertionError('must not call HK09')):
   for node in ['hk-continuous-close','hk-auction-final']:
    with tempfile.TemporaryDirectory() as t:
     f=test_capture.Test();b,x=f.binding(node,t);r=f.call(b);self.assertEqual(r['status'],'OBSERVATION_SAVED');self.assertNotIn('timing_status',r)
if __name__=='__main__':unittest.main()
