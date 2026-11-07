"""Public-export tests: synthetic values and missing-registration refusal only."""
import importlib.util, pathlib, sys, unittest
HERE=pathlib.Path(__file__).resolve().parent

def load(name,path):
 s=importlib.util.spec_from_file_location(name,HERE/path);m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m

class Tests(unittest.TestCase):
 def test_us_bridge_unregistered(self):
  m=load('public_us','us_v3/bridge.py');m.load=lambda: self.fail('must not load')
  x=m.dispatch('synthetic','synthetic','synthetic');self.assertEqual(x['network_requests'],0);self.assertFalse(x['state_written'])
 def test_us_launcher_no_session(self):
  m=load('public_launcher','us_v3/launcher.py');m.load_bundle=lambda: self.fail('must not load')
  self.assertEqual(m.execute()['status'],'BLOCKED_NO_EXECUTION_ADMISSION')
 def test_morning_unregistered(self):
  m=load('public_morning','morning/registered.py');m.module=lambda *_:self.fail('must not load')
  for n in m.NODES:self.assertEqual(m.dispatch(n,'synthetic','synthetic',None)['jobs_started'],0)
 def test_evening_unregistered(self):
  m=load('public_evening','evening/execution.py');m.helpers=lambda:self.fail('must not load')
  for n in ('1830','1850','1900'):
   x=m.run(n,'synthetic');self.assertEqual(x['status'],'BLOCKED');self.assertFalse(x['sent'])
 def test_top200_unregistered(self):
  m=load('public_top','top200/registered.py');m.module=lambda *_:self.fail('must not load')
  self.assertEqual(m.dispatch('synthetic','synthetic')['status'],'BLOCKED_NO_TRUSTED_REGISTRATION')
 def test_kernel_phase_guard(self):
  m=load('public_kernel','daily1540/stages.py');a=m.Attempt('SYNTHETIC',20261109)
  with self.assertRaises(ValueError):a.enter('WRONG','NEXT',None)
  self.assertEqual(a.phase,'INPUT_BOUND')
 def test_rank_synthetic_date_and_unknown(self):
  m=load('public_rank','top200/ranking.py')
  row=dict(symbol='000001.SZ',source_date=20261109,status='EXPLICIT_ZERO_BAR_NO_VALID_OHLCV',original_block={})
  p=m.project_rows([row],['000001.SZ'],20261109);self.assertEqual(p['unknown_count'],1)
  with self.assertRaises(ValueError):m.project_rows([row],['000001.SZ'],20261110)

if __name__=='__main__':unittest.main()
