import importlib.util,pathlib,sys,types,unittest
from unittest.mock import patch
HERE=pathlib.Path(__file__).resolve().parent

def load(name,path):
 s=importlib.util.spec_from_file_location(name,HERE/path);m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m
class Tests(unittest.TestCase):
 def test_exporter_unregistered(self):
  m=load('public_intraday','intraday/exporter.py')
  with self.assertRaisesRegex(ValueError,'BLOCKED_NO_REVIEWED'):m.dispatch('test','test')
 def test_native_controller_no_binding(self):
  m=load('public_controller','native_probe/controller.py');m.load=lambda *a:self.fail('must not load or start')
  with self.assertRaises(FileNotFoundError):m.run()
 def test_native_memory_refusal(self):
  m=load('public_worker','native_probe/worker.py')
  with patch.object(pathlib.Path,'read_text',return_value='MemAvailable: 1 kB\n'),patch.object(pathlib.Path,'exists',return_value=False),patch.object(m.shutil,'disk_usage',return_value=types.SimpleNamespace(free=m.DISK+1)):
   with self.assertRaisesRegex(RuntimeError,'NATIVE_FULL_RESOURCE_GATE'):m.gate()
 def test_native_disk_refusal(self):
  m=load('public_worker2','native_probe/worker.py')
  with patch.object(pathlib.Path,'read_text',return_value='MemAvailable: 999999999 kB\n'),patch.object(pathlib.Path,'exists',return_value=False),patch.object(m.shutil,'disk_usage',return_value=types.SimpleNamespace(free=1)):
   with self.assertRaisesRegex(RuntimeError,'NATIVE_FULL_RESOURCE_GATE'):m.gate()
if __name__=='__main__':unittest.main()
