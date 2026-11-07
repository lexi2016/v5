import unittest,tempfile
from pathlib import Path
import synthetic_check as s
class Tests(unittest.TestCase):
 def test_unbound_refused(self):
  with self.assertRaisesRegex(ValueError,'EXPLICIT'):s.verify(None)
 def test_missing_owner_refused(self):
  with tempfile.TemporaryDirectory() as t:
   with self.assertRaises(FileNotFoundError):s.verify(Path(t))
if __name__=='__main__':unittest.main()
