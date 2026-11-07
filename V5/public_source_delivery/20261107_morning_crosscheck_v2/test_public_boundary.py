import unittest,io,json
from unittest.mock import patch
from contextlib import redirect_stdout
import crosscheck as c
class PublicBoundary(unittest.TestCase):
 def test_no_private_binding(self):
  for v in (c.DATA_PATH,c.DATA_SHA,c.DATA_BYTES,c.AD_PATH,c.AD_SHA,c.AD_BYTES):self.assertIsNone(v)
  with self.assertRaisesRegex(ValueError,'PUBLIC_EXPORT_NO_APPROVED_PRIVATE_BINDING'):c.load()
 def test_cli_refuses_without_audit_or_freeze(self):
  with patch.object(c,'audit') as audit,patch.object(c.safeio,'freeze') as freeze,redirect_stdout(io.StringIO()) as out:
   result=c.main()
  self.assertEqual(result,3);audit.assert_not_called();freeze.assert_not_called();r=json.loads(out.getvalue());self.assertFalse(r['saved_success_receipt']);self.assertFalse(r['business_accepted']);self.assertFalse(r['natural_verified'])
if __name__=='__main__':unittest.main()
