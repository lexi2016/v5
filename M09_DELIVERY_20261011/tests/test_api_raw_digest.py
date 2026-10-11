"""Independent raw-review digest-link check, using an actual synthetic run."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parent))
from test_review_findings import daily, make_input, make_request
from v5_shadow.a_close_daily_api import project_committed_review


class RawDigestLinkReview(unittest.TestCase):
    def test_api_rejects_unbound_raw_review_digest(self):
        with tempfile.TemporaryDirectory(prefix="m09-raw-digest-review-") as temp:
            base = Path(temp)
            source, root = base / "source", base / "m09"
            make_input(source)
            daily.initialize_a_close_root(root)
            result = daily.run_a_close_daily(root, make_request(source))
            self.assertEqual(result["status"], "SUCCEEDED", result)
            committed = daily.read_a_close_daily(root, "20261009")
            original = committed["identity"]["raw_review_sha256"]
            committed["identity"]["raw_review_sha256"] = "0" * 64
            projected = project_committed_review(committed, "20261009")
            evidence = projected["m09_publication"]
            print(json.dumps({"original_raw_review_sha256":original,
                              "projected_raw_review_sha256":evidence["raw_review_sha256"],
                              "read_status":evidence["read_status"]}), flush=True)
            self.assertNotEqual(evidence["read_status"], "VERIFIED",
                                "The pure API projection accepts a raw review digest unrelated to the hashed record")


if __name__ == "__main__":
    unittest.main(verbosity=2)
