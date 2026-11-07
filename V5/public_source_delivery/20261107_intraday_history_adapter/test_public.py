import unittest,json,tempfile
from pathlib import Path
from unittest.mock import patch
import intraday_history_api as a
class Tests(unittest.TestCase):
 def test_current_always_409(self):
  code,raw=a.IntradayHistoryService(lambda:None).get('/api/intraday/current');d=json.loads(raw);self.assertEqual(code,409);self.assertIsNone(d['current_rows']);self.assertIs(d['historical_fallback_used'],False)
 def test_history_missing_binding_refused(self):
  with self.assertRaisesRegex(ValueError,'NO_APPROVED'):a.IntradayHistoryService(lambda:None).get('/api/intraday/history/2000-01-01/1400')
 def test_resource_and_lock_retained(self):
  with tempfile.TemporaryDirectory() as t:
   with patch.multiple(a,READER_ROOT=Path(t),CODE_PINS={'safeio.py':{},'observation_api.py':{}},HISTORY_DATE='2000-01-01',HISTORY_SLOT='1400'):
    def gate():raise ValueError('RESOURCE_BLOCK')
    s=a.IntradayHistoryService(gate)
    with self.assertRaisesRegex(ValueError,'RESOURCE_BLOCK'):s.get('/api/intraday/history/2000-01-01/1400')
    self.assertFalse(s.lock.locked())
 def test_unsupported_never_loads_reader(self):
  with tempfile.TemporaryDirectory() as t,patch.multiple(a,READER_ROOT=Path(t),CODE_PINS={'safeio.py':{},'observation_api.py':{}},HISTORY_DATE='2000-01-01',HISTORY_SLOT='1400'):
   self.assertEqual(a.IntradayHistoryService(lambda:None).get('/api/intraday/history/2000-01-02/1400')[0],404)
if __name__=='__main__':unittest.main()
