import unittest
from pathlib import Path
from v5_shadow.a_preselection_daily import _classify_exception, _validate_required_root, A_POOL_IDS

class M05BindingTests(unittest.TestCase):
    def test_known_conflict_only(self):
        self.assertTrue(_classify_exception(ValueError("conflicting preselection-pool materialization")))
        self.assertFalse(_classify_exception(ValueError("bad receipt")))

    def test_all_roots_required(self):
        with self.assertRaises(ValueError) as cm:
            _validate_required_root("/tmp/out","/tmp/src",["/tmp/lane"],"", "/tmp/v4")
        self.assertEqual(str(cm.exception),"M05_OWNER_ROOT_BINDING_REQUIRED")

    def test_allowlist(self):
        self.assertIn("a_d1_premarket_pool", A_POOL_IDS)
        self.assertNotIn("hk_pool", A_POOL_IDS)

if __name__ == "__main__":
    unittest.main()
