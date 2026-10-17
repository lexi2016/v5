from datetime import datetime, timezone
import unittest

from v5_shadow.daily_tick import manager_plan_window_status


class ManagerPlanWindowTests(unittest.TestCase):
    def setUp(self):
        self.slots = {
            "plan_at": "2026-10-17T08:45:00+08:00",
            "plan_deadline": "2026-10-17T09:00:00+08:00",
        }

    def status(self, value):
        return manager_plan_window_status(
            datetime.fromisoformat(value).astimezone(timezone.utc),
            self.slots,
        )

    def test_before_window_waits(self):
        self.assertEqual(
            self.status("2026-10-17T08:44:59+08:00"),
            "WAITING_0845_PLAN_WINDOW",
        )

    def test_window_start_is_inclusive(self):
        self.assertIsNone(self.status("2026-10-17T08:45:00+08:00"))

    def test_inside_window_is_allowed(self):
        self.assertIsNone(self.status("2026-10-17T08:52:30+08:00"))

    def test_deadline_is_exclusive_and_never_backfills(self):
        self.assertEqual(
            self.status("2026-10-17T09:00:00+08:00"),
            "MISSED_PLAN_WINDOW_NO_BACKFILL",
        )
        self.assertEqual(
            self.status("2026-10-17T09:10:00+08:00"),
            "MISSED_PLAN_WINDOW_NO_BACKFILL",
        )


if __name__ == "__main__":
    unittest.main()
