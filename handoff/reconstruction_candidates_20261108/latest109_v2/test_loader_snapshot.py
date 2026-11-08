import tempfile,pathlib,hashlib,unittest
from unittest.mock import patch
import latest109_rebuild as a
class SnapshotTests(unittest.TestCase):
 def test_path_replacement_after_read_never_executes_replacement(self):
  with tempfile.TemporaryDirectory() as t:
   p=pathlib.Path(t)/'code.py';q=pathlib.Path(t)/'rules.json';raw=b'VALUE=1\n';p.write_bytes(raw);q.write_bytes(b'{}');read=pathlib.Path.read_bytes
   def snapshot(path):
    result=read(path)
    if path==p:p.write_text('VALUE=2\n')
    return result
   with patch.object(a,'CANDIDATE_SHA',hashlib.sha256(raw).hexdigest()),patch.object(a,'ACTION_SHA',hashlib.sha256(b'{}').hexdigest()),patch.object(pathlib.Path,'read_bytes',snapshot):
    self.assertEqual(a.load(p,q).VALUE,1)
 def test_bad_rules_never_execute_candidate(self):
  with tempfile.TemporaryDirectory() as t:
   p=pathlib.Path(t)/'code.py';q=pathlib.Path(t)/'rules.json';p.write_text("raise RuntimeError('EXECUTED')");q.write_text('{}')
   with patch.object(a,'CANDIDATE_SHA',hashlib.sha256(p.read_bytes()).hexdigest()):
    with self.assertRaisesRegex(ValueError,'CODE_OR_RULE_PIN'):a.load(p,q)
 def test_bad_code_never_executes(self):
  with tempfile.TemporaryDirectory() as t:
   p=pathlib.Path(t)/'code.py';p.write_text("raise RuntimeError('EXECUTED')")
   with self.assertRaisesRegex(ValueError,'CODE_OR_RULE_PIN'):a.load(p,p)
if __name__=='__main__':unittest.main()
