import unittest, copy, importlib.util
from pathlib import Path
import registered_candidate as reg
class BranchTest(unittest.TestCase):
 def test_delivery_is_not_list_prompt(self):
  # Missing input must identify delivery assembly, not fall into panel/list handling.
  try: got=reg.calculate({'node':'morning-delivery'}, {}, {}, None)
  except KeyError as e: self.fail('delivery incorrectly reached list branch: '+str(e))
  self.assertEqual(got['status'],'BLOCKED_DELIVERY_ASSEMBLY_NOT_BOUND')
if __name__=='__main__':unittest.main()
