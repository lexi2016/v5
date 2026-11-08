import pathlib,tempfile,unittest
import isolated_owner as owner
class Tests(unittest.TestCase):
 def test_existing_attempt_rejected_before_loading(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)
   with self.assertRaisesRegex(ValueError,'EXISTING_ATTEMPT'):owner.run(None,None,None,None,p)
   self.assertEqual(list(p.iterdir()),[])
 def test_code_pin_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'bad.py';p.write_text('raise RuntimeError("must not execute")')
   with self.assertRaisesRegex(ValueError,'SOURCE_PIN'):owner.load(p,'bad','0'*64)
if __name__=='__main__':unittest.main()
