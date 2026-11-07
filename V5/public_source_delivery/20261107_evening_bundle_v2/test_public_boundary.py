import unittest
from pathlib import Path
import bundle
class PublicBoundary(unittest.TestCase):
 def test_private_binding_absent(self):
  self.assertIsNone(bundle.DATA);self.assertIsNone(bundle.ADMISSION)
  with self.assertRaisesRegex(ValueError,'PUBLIC_EXPORT_NO_APPROVED_PRIVATE_BINDING'):bundle.load()
 def test_prepare_refuses_no_binding(self):
  before=(Path(bundle.HERE)/'frozen').exists()
  with self.assertRaisesRegex(ValueError,'PUBLIC_EXPORT_NO_APPROVED_PRIVATE_BINDING'):bundle.prepare()
  self.assertEqual((Path(bundle.HERE)/'frozen').exists(),before)
if __name__=='__main__':unittest.main()
