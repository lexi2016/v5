import unittest,observation_api as api
class Binding(unittest.TestCase):
 def test_unbound_refused(self):
  self.assertIsNone(api.PINS_SHA)
  with self.assertRaisesRegex(ValueError,'PUBLIC_EXPORT_NO_APPROVED_PRIVATE_BINDING'):api.load()
 def test_unmodified_server_cannot_start(self):
  with self.assertRaisesRegex(ValueError,'PUBLIC_EXPORT_NO_APPROVED_PRIVATE_BINDING'):api.create_server()
if __name__=='__main__':unittest.main()
