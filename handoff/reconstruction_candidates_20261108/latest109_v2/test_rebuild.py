import copy, unittest
from unittest.mock import patch
import tempfile,json,pathlib,types
import latest109_rebuild as m
REAL_CHECKED=m.checked
ROWS=[{'symbol':'000001.SZ','event_date':'20261105'},{'symbol':'000001.SZ','event_date':'20261106'}]
CTX={'symbol':'000001.SZ','asof':'20261106'}
STATE={'symbol':'000001.SZ','count':1,'last_date':'20261105'}
class Candidate:
 __file__='/fake/handoff/latest109_rebuild_v1_20261106/latest109_candidate.py'
 def build(self,p,mods,gate):
  def f(rows,context,prior_state):
   gate();return {'symbol':context['symbol'],'event_date':context['asof'],'fields':{str(i):{'value':None,'status':'UNKNOWN','reason':'SYNTHETIC'} for i in range(109)}},{'component_state':{'symbol':context['symbol'],'count':len(rows),'last_date':context['asof']},'production_allowed':True}
  return f
class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  pathlib.Path(self.tmp.name,"FIELD_SCHEMA_109.json").write_text(json.dumps({str(i):{} for i in range(109)}))
  import hashlib
  raw=pathlib.Path(self.tmp.name,"FIELD_SCHEMA_109.json").read_bytes()
  for key,value in [('SCHEMA_SHA',hashlib.sha256(raw).hexdigest()),('SCHEMA_BYTES',len(raw))]:
   fixture_pin=patch.object(m,key,value);fixture_pin.start();self.addCleanup(fixture_pin.stop)
  self.producer=types.SimpleNamespace(H=pathlib.Path(self.tmp.name),core=types.SimpleNamespace(check_field=lambda value,spec:None))
  self.pinpatch=patch.object(m,"checked",side_effect=lambda path,sha:path);self.pinpatch.start();self.addCleanup(self.pinpatch.stop)
 def test_positive_synthetic_interface(self):
  calls=[];run=m.build(Candidate(),self.producer,None,original_monitor_gate=lambda:calls.append(1))
  row,facts=run(ROWS,CTX,STATE,checkpoint_prefix_sha256=m.digest(ROWS[:-1]));self.assertFalse(facts['production_allowed']);self.assertGreaterEqual(len(calls),4)
 def test_no_gate(self):
  with self.assertRaisesRegex(ValueError,'MONITOR'):m.build(Candidate(),self.producer,None,original_monitor_gate=None)
 def test_low_resource_propagates(self):
  def gate():raise ValueError('ORIGINAL_MEMORY_FLOOR')
  with self.assertRaisesRegex(ValueError,'MEMORY'):m.build(Candidate(),self.producer,None,original_monitor_gate=gate)
 def test_missing_state(self):
  with self.assertRaises(ValueError):m.validate_checkpoint(ROWS,CTX,None,m.digest(ROWS[:-1]))
 def test_wrong_symbol(self):
  with self.assertRaises(ValueError):m.validate_checkpoint(ROWS,CTX,{**STATE,'symbol':'000002.SZ'},m.digest(ROWS[:-1]))
 def test_wrong_count(self):
  with self.assertRaises(ValueError):m.validate_checkpoint(ROWS,CTX,{**STATE,'count':2},m.digest(ROWS[:-1]))
 def test_wrong_date(self):
  with self.assertRaises(ValueError):m.validate_checkpoint(ROWS,{**CTX,'asof':'20261109'},STATE,m.digest(ROWS[:-1]))
 def test_input_changed_invalidates_identity(self):
  with self.assertRaisesRegex(ValueError,'PREFIX'):
   m.validate_checkpoint([{**ROWS[0],'x':1},ROWS[1]],CTX,STATE,m.digest(ROWS[:-1]))
 def test_real_pin_rejects_changed_file(self):
  p=pathlib.Path(self.tmp.name,'code.py');p.write_text('changed')
  with self.assertRaisesRegex(ValueError,'PIN'):REAL_CHECKED(p,'0'*64)
 def test_real_pin_accepts_exact_bytes(self):
  p=pathlib.Path(self.tmp.name,'code.py');p.write_bytes(b'original')
  import hashlib
  self.assertEqual(REAL_CHECKED(p,hashlib.sha256(b'original').hexdigest()),p)
 def test_nonfinite(self):
  with self.assertRaises(ValueError):m.digest({'x':float('nan')})
if __name__=='__main__':unittest.main()
