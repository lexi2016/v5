import json,subprocess,sys,unittest
import test_replay as fixtures
class QuoteTime(unittest.TestCase):
 setUp=fixtures.Tests.setUp
 runone=fixtures.Tests.runone
 def mutated(self,stage,value):
  code="""import sys,json,pathlib
sys.path.insert(0,sys.argv[1]);import m07_fixture as f
old=f.RawStore.publish
def publish(self,**kwargs):
 for row in kwargs['rows']:row['update_time']=sys.argv[4]
 return old(self,**kwargs)
f.RawStore.publish=publish
print(json.dumps(f.make_case(pathlib.Path(sys.argv[2]),count=2,stage=sys.argv[3])))
"""
  p=subprocess.run([sys.executable,'-B','-c',code,str(fixtures.ROOT/'V5/tests'),str(self.folder),stage,value],capture_output=True,text=True,timeout=30);self.assertEqual(p.returncode,0,p.stderr);return json.loads(p.stdout)
 def probe(self,stage,value):
  x=self.mutated(stage,value);p=self.runone(x);self.assertEqual(p.returncode,2,p.stdout);r=json.loads(p.stdout);self.assertEqual(r['status'],'BLOCKED_NEW_REPLAY');self.assertFalse(r['production_allowed']);self.assertFalse(r['natural_verified']);self.assertIn('M07_RAW_COVERAGE_NOT_EXACT',r['reason'])
 def test_0925_future_date_rejected(self):self.probe('STAGE_0925','2026-10-13 09:25:00')
 def test_0930_future_date_rejected(self):self.probe('STAGE_0930_0935','2026-10-13 09:35:00')
 def test_0925_old_date_rejected(self):self.probe('STAGE_0925','2026-10-09 09:25:00')
 def test_0930_after_window_rejected(self):self.probe('STAGE_0930_0935','2026-10-12 09:35:01')
