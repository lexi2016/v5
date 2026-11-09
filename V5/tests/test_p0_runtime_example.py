import json
import unittest
from pathlib import Path


class P0RuntimeExampleTests(unittest.TestCase):
    def test_example_uses_complete_module_api_schema_and_read_only_routes(self):
        root = Path(__file__).resolve().parents[1]
        config = json.loads((root / "examples" / "p0_runtime_config.json").read_text())
        self.assertTrue(Path(config["runtime_root"]).is_absolute())
        self.assertTrue(Path(config["composition"]).is_absolute())
        module = config["module_api"]
        self.assertEqual(
            set(module),
            {"schema_version", "module_id", "release_id", "data_root", "routes"},
        )
        self.assertEqual(module["schema_version"], "v5.module_api.v1")
        self.assertEqual(module["module_id"], "source_bundle")
        self.assertTrue(Path(module["data_root"]).is_absolute())
        self.assertNotIn("host", module)
        self.assertNotIn("mode", module)
        self.assertEqual(len(module["routes"]), len(set(module["routes"])))
        self.assertIn("/api/v3/research/day", module["routes"])
        self.assertIn("/api/v1/runs/date-list", module["routes"])
        self.assertIn("/api/v5/source-bundle/capture-status", module["routes"])
        self.assertEqual(config["daily"]["close_recapture"], {"enabled": False})
        self.assertEqual(config["daily"]["hk_preselection"], {"enabled": False})


if __name__ == "__main__":
    unittest.main()
