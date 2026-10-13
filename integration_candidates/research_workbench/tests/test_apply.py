import hashlib,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]));import apply_candidate as a
class ApplyTests(unittest.TestCase):
 def test_observed_bytes_required(self):
  content='actual current source\n';expected={'file':hashlib.sha256(content.encode()).hexdigest()}
  a.validate_preimages({'file':content},expected)
  with self.assertRaisesRegex(ValueError,'UNKNOWN_MAC_PREIMAGE'):a.validate_preimages({'file':content+' '},expected)
  with self.assertRaisesRegex(ValueError,'UNKNOWN_MAC_PREIMAGE'):a.validate_preimages({},expected)
 def test_patch_preserves_crlf_and_all_other_bytes(self):
  before='unrelated\r\nUNIQUE\r\nM14_KEEP\r\n'
  self.assertEqual(a.once(before,'UNIQUE','UNIQUE\nADDED'), 'unrelated\r\nUNIQUE\r\nADDED\r\nM14_KEEP\r\n')
 def test_ambiguous_anchor_fails(self):
  with self.assertRaises(ValueError):a.once('x x','x','y')
if __name__=='__main__':unittest.main()
