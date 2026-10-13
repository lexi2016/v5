import unittest

from v5_shadow.market_snapshot_adapter import materialize_market_snapshot


class TestMarketSnapshotAdapter(unittest.TestCase):
    def test_only_news_rejected(self):
        with self.assertRaises(ValueError):
            materialize_market_snapshot(
                {"status": "READY", "news": ["x"]},
                session="20261010",
                phase="POST_CLOSE",
                cutoff="2026-10-10T22:00:00Z",
            )

    def test_snapshot_contract(self):
        result = materialize_market_snapshot(
            {
                "market_snapshot": {
                    "status": "READY",
                    "capture_session_date": "20261010",
                    "capture_phase": "POST_CLOSE",
                    "captured_at": "2026-10-10T20:00:00Z",
                }
            },
            session="20261010",
            phase="POST_CLOSE",
            cutoff="2026-10-10T22:00:00Z",
        )
        self.assertEqual(result["status"], "READY")


if __name__ == "__main__":
    unittest.main()
