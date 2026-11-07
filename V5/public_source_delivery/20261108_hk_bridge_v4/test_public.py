"""Public suite uses a synthetic timing stub, NOT original helper verification."""
import datetime as dt,unittest
from unittest.mock import patch
import capture,bridge,test_capture,test_hk09_v4

def synthetic_time(day,started,observed,received,checked):
 values=[dt.datetime.fromisoformat(s) for s in (started,observed,received,checked)]
 if any(t.tzinfo is None or t.strftime('%Y%m%d')!=day for t in values):raise ValueError('TEST_TIME')
 a,o,r,c=values
 if not a<=r<=c or not o<=r:raise ValueError('TEST_ORDER')
 seconds=lambda t:t.hour*3600+t.minute*60+t.second-32400
 if any(not 0<=seconds(t)<120 for t in (a,o,r)):raise ValueError('TEST_WINDOW')
 return {'timing_status':'ON_TIME' if seconds(a)<=30 else 'LATE'}

class Defaults(unittest.TestCase):
 def test_unbound_original(self):
  with self.assertRaisesRegex(ValueError,'ORIGINAL_DEPENDENCY_UNBOUND'):bridge.original()
 def test_unbound_helper(self):
  with self.assertRaisesRegex(ValueError,'HK09_WINDOW_DEPENDENCY_UNBOUND'):capture.hk09_times(None,None,None,None,None)

def load_tests(loader,tests,pattern):
 suite=unittest.TestSuite([loader.loadTestsFromTestCase(Defaults)])
 class WithSynthetic(unittest.TestSuite):
  def run(self,result,debug=False):
   with patch.object(capture,'hk09_times',side_effect=synthetic_time):return super().run(result,debug)
 suite.addTest(WithSynthetic([loader.loadTestsFromModule(test_capture),loader.loadTestsFromModule(test_hk09_v4)]))
 return suite
if __name__=='__main__':unittest.main()
