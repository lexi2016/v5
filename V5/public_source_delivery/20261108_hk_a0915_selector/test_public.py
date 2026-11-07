import importlib.util,pathlib,sys,unittest
HERE=pathlib.Path(__file__).resolve().parent

def load(name,path):
 s=importlib.util.spec_from_file_location(name,HERE/path);m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m
class Tests(unittest.TestCase):
 def test_a0915_unregistered(self):
  m=load('public_a0915','a0915/execution.py');m._load=lambda:self.fail('no source load allowed')
  r=m.dispatch('synthetic','synthetic');self.assertEqual(r['status'],'BLOCKED_UNREGISTERED');self.assertEqual(r['source_calls'],0)
 def test_hk_unregistered(self):
  m=load('public_hk','hk_v3/bridge.py');m.original=lambda:self.fail('no source load allowed')
  for n in ('hk-open','hk-continuous-close','hk-auction-final'):
   r=m.dispatch(n,'synthetic');self.assertEqual(r['status'],'BLOCKED');self.assertFalse(r['production_allowed'])
 def test_selector_invalid_calendar(self):
  m=load('public_selector','four_groups/adapter.py')
  with self.assertRaises(ValueError):m.validate_calendar({},20261109,20261110)
  with self.assertRaises(ValueError):m.day(True)
 def test_selector_no_private_dependencies(self):
  m=load('public_selector2','four_groups/adapter.py')
  with self.assertRaises((OSError,ValueError)):m._clone(20261109,20261110,{})
if __name__=='__main__':unittest.main()
