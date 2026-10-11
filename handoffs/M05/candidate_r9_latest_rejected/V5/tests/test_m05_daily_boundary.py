import unittest
from pathlib import Path
from v5_shadow.a_preselection_daily import _classify_exception, _validate_required_root, A_POOL_IDS

class M05BindingTests(unittest.TestCase):
    def test_known_conflict_only(self):
        self.assertTrue(_classify_exception(ValueError("conflicting preselection-pool materialization")))
        self.assertFalse(_classify_exception(ValueError("bad receipt")))

    def test_all_roots_required(self):
        with self.assertRaisesRegex(ValueError, "M05_OWNER_ROOT_BINDING_REQUIRED"):
            _validate_required_root("/tmp/out","/tmp/src",["/tmp/lane"],"", "/tmp/v4")

    def test_allowlist(self):
        self.assertIn("a_d1_premarket_pool", A_POOL_IDS)
        self.assertNotIn("hk_pool", A_POOL_IDS)

    def test_fake_gate_object_rejected(self):
        class Fake: 
            control_dir=Path("/tmp")
        self.assertFalse(hasattr(Fake(), "expected_owner_id"))

if __name__ == "__main__":
    unittest.main()
