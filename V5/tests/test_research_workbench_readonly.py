import unittest

from v5_shadow.research_workbench_readonly import validate_payload


class ResearchWorkbenchReadonlyTests(unittest.TestCase):
    def payload(self, **changes):
        value = dict(
            schema_version="v3_5.research_lane.v1",
            endpoint_mode="EXACT",
            requested_date="20261016",
            research_date=None,
            status="NOT_MATERIALIZED",
            reason="V5_M04_RESEARCH_BINDING_NOT_CONFIGURED",
            cannot_confirm=["V5_M04_RESEARCH_BINDING_NOT_CONFIGURED"],
            write_policy="read_only",
            recommendation_status="RESEARCH_ONLY",
            production_allowed=False,
            buy_gate_updated=False,
            orders_sent=False,
        )
        value.update(changes)
        return value

    def test_exact_request_date_is_not_misrepresented_as_source_date(self):
        value = self.payload()
        result = validate_payload(value, {"research_date": "20261016"})
        self.assertIsNone(result["research_date"])
        self.assertEqual(result["requested_date"], "20261016")
        self.assertEqual(result["status"], "NOT_MATERIALIZED")

    def test_unbound_source_rejects_mismatched_requested_date(self):
        value = self.payload(requested_date="20261015")
        with self.assertRaisesRegex(ValueError, "RESEARCH_DATE_MISMATCH"):
            validate_payload(value, {"research_date": "20261016"})

    def test_materialized_source_must_match_exact_request(self):
        value = self.payload(status="READY", research_date="20261015", requested_date="20261016")
        with self.assertRaisesRegex(ValueError, "RESEARCH_DATE_MISMATCH"):
            validate_payload(value, {"research_date": "20261016"})


if __name__ == "__main__":
    unittest.main()
