import unittest,json,types
from contextlib import nullcontext
from dataclasses import replace
from unittest.mock import patch
import adapter as a
class Tests(unittest.TestCase):
 def binding(self):
  d=dict(target_date='20261109',stage_id='STAGE_0925',cutoff='synthetic',pool_source_dates={},inputs=dict.fromkeys(('pool','live','research','morning'),{}),recording={})
  return a.Binding('synthetic-job','synthetic-env','SYNTHETIC',('A.000001',),a.digest(['A.000001']),'a'*64,'b'*64,d,lambda:None,lambda:nullcontext(),True)
 def response(self,**kw):
  x=dict(status='VERIFIED',known_synthetic=True,source_id='SYNTHETIC',pool_codes=['A.000001'],recording={},rows=1,missing_symbols=[]);x.update(kw);return types.SimpleNamespace(stdout=json.dumps(x).encode(),returncode=0)
 def test_empty(self):
  with patch.object(a.subprocess,'run',side_effect=AssertionError('no process')):self.assertEqual(a.dispatch('x','y')['status'],'BLOCKED')
 def test_source_only(self):
  with patch.object(a.subprocess,'run',return_value=self.response()):
   r=a.verify_registered_recording(self.binding());self.assertEqual(r['status'],'SOURCE_RECORDING_VERIFIED_ONLY');self.assertEqual(r['source_authority'],'UNKNOWN');self.assertFalse(r['collector_executed']);self.assertFalse(r['natural_verified'])
 def test_relabel(self):
  with patch.object(a.subprocess,'run',return_value=self.response()):
   with self.assertRaisesRegex(ValueError,'SYNTHETIC_RELABEL'):a.verify_registered_recording(replace(self.binding(),synthetic=False))
 def test_wrong_scope(self):
  with patch.object(a.subprocess,'run',return_value=self.response(pool_codes=['A.000002'])):
   with self.assertRaisesRegex(ValueError,'SCOPE_MISMATCH'):a.verify_registered_recording(self.binding())
 def test_wrong_source(self):
  with patch.object(a.subprocess,'run',return_value=self.response(source_id='UNKNOWN')):
   with self.assertRaisesRegex(ValueError,'SOURCE_IDENTITY'):a.verify_registered_recording(self.binding())
 def test_gate(self):
  def deny():raise ValueError('SYNTHETIC_GATE')
  with patch.object(a.subprocess,'run',side_effect=AssertionError('no process')):
   with self.assertRaisesRegex(ValueError,'SYNTHETIC_GATE'):a.verify_registered_recording(replace(self.binding(),gate=deny))
 def test_worker_missing_manifest_stays_closed(self):
  import verify_worker as w
  import tempfile
  from pathlib import Path
  with tempfile.TemporaryDirectory() as temp, patch.object(w,'MANIFEST',Path(temp)/'missing-manifest.json'):
   with self.assertRaises(OSError):w.main()
if __name__=='__main__':unittest.main()
