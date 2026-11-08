import pathlib,tempfile,json,unittest,types,hashlib
from unittest.mock import patch
import latest109_rebuild as a
class SchemaPinTests(unittest.TestCase):
 def test_equal_field_count_cannot_replace_pinned_schema(self):
  with tempfile.TemporaryDirectory() as t:
   p=pathlib.Path(t);(p/'FIELD_SCHEMA_109.json').write_text(json.dumps({str(i):{} for i in range(109)}))
   candidate=types.SimpleNamespace(__file__='/fixture/handoff/candidate.py',build=lambda *args,**kw:None)
   with patch.object(a,'checked',return_value=None):
    with self.assertRaisesRegex(ValueError,'SCHEMA_PIN'):a.build(candidate,types.SimpleNamespace(H=p),{},original_monitor_gate=lambda:None)
 def test_exact_registered_schema_snapshot(self):
  with tempfile.TemporaryDirectory() as t:
   p=pathlib.Path(t)/'FIELD_SCHEMA_109.json';raw=json.dumps({str(i):{} for i in range(109)}).encode();p.write_bytes(raw)
   with patch.object(a,'SCHEMA_SHA',hashlib.sha256(raw).hexdigest()),patch.object(a,'SCHEMA_BYTES',len(raw)):
    self.assertEqual(len(a.load_schema(p)),109)
 def test_post_read_replacement_uses_verified_snapshot(self):
  with tempfile.TemporaryDirectory() as t:
   p=pathlib.Path(t)/'FIELD_SCHEMA_109.json';raw=json.dumps({str(i):{} for i in range(109)}).encode();p.write_bytes(raw);read=pathlib.Path.read_bytes
   def snap(path):
    data=read(path);path.write_text('{}');return data
   with patch.object(a,'SCHEMA_SHA',hashlib.sha256(raw).hexdigest()),patch.object(a,'SCHEMA_BYTES',len(raw)),patch.object(pathlib.Path,'read_bytes',snap):
    self.assertEqual(len(a.load_schema(p)),109)
if __name__=='__main__':unittest.main()
