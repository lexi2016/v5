"""M09-only read projection contracts; every market row here is SYNTHETIC.

These tests exercise the read boundary and pure composition, not a browser,
the Mac API, natural scheduler receipts, or real panel admission.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import importlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from v5_shadow.digests import sha256_json

try:
    api = importlib.import_module("v5_shadow.a_close_daily_api")
except ModuleNotFoundError as error:
    if error.name != "v5_shadow.a_close_daily_api":
        raise
    api = None


DATE = "20261009"
FLAGS = {"production_allowed": False, "buy_gate_updated": False, "orders_sent": False}
CHAIN_TASKS = (
    "FUPAN_CLOSE_MATERIALS", "FUPAN_REVIEW_START", "FUPAN_A_SHARE_STRUCTURE", "FUPAN_VIDEO_CHECK",
    "FUPAN_VIDEO_DOWNLOAD_ASR", "FUPAN_STOCKDICT", "FUPAN_VIDEO_TABLE_OCR_ALIGN", "FUPAN_VIDEO_GAP",
    "FUPAN_V3_PUBLISH", "FUPAN_8771_VERIFY",
)


def committed_fixture():
    """An explicit engineering fixture, with independently sealed JSON layers."""
    source = hashlib.sha256(b"SYNTHETIC_TEST_INPUT_ONLY").hexdigest()
    role = {"trade_date": DATE, "stock_code": "600001", "stock_name": "Fixture One",
            "board_name": "Fixture Board", "primary_role": "capacity_anchor",
            "role_explanation": "fixture explanation", "recommendation_status": "WATCH_ONLY"}
    board = {"trade_date": DATE, "board_name": "Fixture Board", "board_rank": 1,
             "board_role": "strong_branch", "median_pct_change": 2.0, "up_ratio": 1.0}
    model = {
        "schema_version": "replay_model_v1", "status": "INDEPENDENT_CLOSE_REVIEW_READY",
        "run_id": "m09-read-contract-fixture-20261009", "review_date": DATE,
        "producer_type": "DETERMINISTIC_PYTHON", "as_of": "2026-10-09T15:30:00+08:00",
        "visibility_stage": "POST_CLOSE_REVIEW_ONLY", "semantic_model_call_count": 0,
        "semantic_model_status": "DISABLED_BY_V3_5_NO_LLM_PRODUCTION_RULE",
        "learning_status": "LEARNING_HYPOTHESIS_FAIL", "formal_generalization": "FORMAL_GENERALIZATION_PENDING",
        "model_promotion": "NO_MODEL_PROMOTED",
        "target_video_review_status": "CANNOT_CONFIRM_TARGET_VIDEO_NOT_CONSUMED",
        "target_video_evidence_count": 0, "video_augmented_review_complete": False,
        "market_summary": {"up_count": 1, "down_count": 1, "flat_count": 1,
                           "market_width": 0.333333, "regime": "fixture-regime"},
        "board_rows": [board], "anchor_role_rows": [role],
        "scenario_tree": {
            "stronger": {"probability": 0.12, "open_trigger": ["stronger trigger"], "invalidation": ["stronger invalidation"]},
            "inline": {"probability": 0.28, "open_trigger": ["inline trigger"], "invalidation": ["inline invalidation"]},
            "weaker": {"probability": 0.60, "open_trigger": ["weaker trigger"], "invalidation": ["weaker invalidation"]},
        },
        "shadow_watch_pool": {"boundary": "SHADOW_ONLY", "abstain": True, "core": [],
                              "conditional": [role], "observation_or_risk": []},
        "safety": {"SHADOW_ONLY": True, "NOT_BUY_ADVICE": True, "NO_BUY_GATE": True,
                   "HOLDOUT_ACCESS_COUNT": 0, "FORMAL_GENERALIZATION_PENDING": True, "NO_MODEL_PROMOTED": True},
    }
    review = {
        "schema_version": "v3_5.a_share_review.v1", "trade_date": DATE,
        "headline": "Synthetic read contract fixture", "market_regime": "fixture-regime", "risk_tone": "fixture-risk",
        "big_picture": [{"trade_date": DATE, "title": "Fixture breadth", **model["market_summary"]}],
        "mainlines": [board], "core_stocks": [], "observation_pool": [role],
        "next_day_trigger_tree": [{"trade_date": DATE, "direction": direction, "probability": row["probability"]}
                                  for direction, row in model["scenario_tree"].items()],
        "quality_gate": [{"trade_date": DATE, "item": "15:00 PIT", "status": "CANNOT_CONFIRM_STRICT_D0_1500_PANEL"}],
        "cannot_confirm": ["CANNOT_CONFIRM_TARGET_VIDEO_NOT_CONSUMED", "CANNOT_CONFIRM_STRICT_D0_1500_PANEL", "FORMAL_GENERALIZATION_PENDING"],
        "model_review": model,
        "source_evidence": [{"trade_date": DATE, "source_id": "fixture-panel", "raw_sha256": source, "row_count": 3}],
        "source_role": "V3_5_NATIVE_CLOSE_MODEL", "source_sha256": source,
        "close_chain": {"schema_version": "v3_5.close_review_chain.v1", "trade_date": DATE,
                        "status": "PARTIAL_REVIEW", "nodes": [
                            {"task_id": task, "business_date": DATE, "status": "READY" if index < 3 else "NOT_MATERIALIZED",
                             "label": "fixture node", "reason": "fixture evidence state", "evidence": []}
                            for index, task in enumerate(CHAIN_TASKS)],
                        "cannot_confirm": list(CHAIN_TASKS[3:8]), **FLAGS},
        "write_policy": "review_only_read_only", **FLAGS,
    }
    raw_review = (json.dumps(review, ensure_ascii=False, indent=2) + "\n").encode()
    raw_store = {
        "a_share_reviews/" + DATE + ".json": raw_review,
        "a_share_reviews/receipts/" + DATE + ".json": b'{"synthetic_fixture":"receipt"}',
        "a_share_reviews/manifest.json": b'{"synthetic_fixture":"manifest"}',
    }
    record = {
        "schema_version": "v5.m09.record.v1", "trade_date": DATE, "run_id": model["run_id"],
        "review_sha256": sha256_json(review), "source_sha256": source,
        "store_files": {name: {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
                        for name, raw in raw_store.items()},
        "data_kind": "SYNTHETIC", "execution_kind": "ENGINEERING", "business_status": "PARTIAL",
        "computed_at": "2026-10-11T10:00:00+00:00",
        "provenance": {"source_available_at": None, "strict_pit_as_of": None, "declared_scope": "ENGINEERING_FIXTURE"},
        "evidence_status": {"price_model": "READY", "video_consumption": "CANNOT_CONFIRM"},
        "scope": "DECLARED_UNIVERSE_ONLY", "natural_verified": False,
        "source_provenance_independently_verified": False,
        "cannot_confirm": ["FULL_MARKET_MEMBERSHIP_NOT_VERIFIED", "STRICT_1500_PIT_NOT_VERIFIED", "NATURAL_TRIGGER_NOT_INDEPENDENTLY_VERIFIED"],
        "membership": {"scope": "DECLARED_UNIVERSE", "source_id": "fixture-member-list"},
        "strict_1500_pit_verified": False, "safety": {"research_only": True, **FLAGS},
    }
    generation = {"schema_version": "v5.m09.generation.v1", "trade_date": DATE, "run_id": model["run_id"],
                  "record_sha256": sha256_json(record), "previous_generation_sha256": None}
    return {"review": review, "record": record, "generation": generation,
            "identity": {"trade_date": DATE, "model_run_id": model["run_id"],
                         "canonical_review_sha256": sha256_json(review),
                         "raw_review_sha256": hashlib.sha256(raw_review).hexdigest(),
                         "source_sha256": source, "record_sha256": sha256_json(record),
                         "generation_sha256": sha256_json(generation)}}


def reseal(value):
    """Rehash altered fixtures without repairing their date/source/safety links."""
    value["record"]["review_sha256"] = sha256_json(value["review"])
    value["identity"]["canonical_review_sha256"] = sha256_json(value["review"])
    value["identity"]["record_sha256"] = sha256_json(value["record"])
    value["generation"]["record_sha256"] = value["identity"]["record_sha256"]
    value["identity"]["generation_sha256"] = sha256_json(value["generation"])


class M09ReadProjectionTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(api, "M09-only committed read adapter is not implemented")
        self.committed = committed_fixture()

    def test_preserves_native_algorithm_and_date_fields(self):
        preview = api.project_committed_review(self.committed, DATE)
        for key, value in self.committed["review"].items():
            self.assertEqual(value, preview[key], key)
        self.assertEqual("PARTIAL", preview["status"])
        self.assertEqual("COMPACT_NATIVE", preview["review_surface"]["tier"])
        self.assertEqual(["stronger", "inline", "weaker"], list(preview["model_review"]["scenario_tree"]))
        self.assertEqual([0.12, 0.28, 0.60], [r["probability"] for r in preview["next_day_trigger_tree"]])

    def test_metadata_names_distinct_digest_layers_and_computation_classification(self):
        preview = api.project_committed_review(self.committed, DATE)
        evidence = preview["m09_publication"]
        self.assertEqual("v5.m09.read_evidence.v1", evidence["schema_version"])
        self.assertEqual("VERIFIED", evidence["read_status"])
        for key, value in self.committed["identity"].items():
            self.assertEqual(value, evidence[key], key)
        self.assertNotEqual(evidence["canonical_review_sha256"], evidence["raw_review_sha256"])
        self.assertEqual("SYNTHETIC", evidence["data_kind"])
        self.assertEqual("ENGINEERING", evidence["execution_kind"])
        self.assertEqual("FROZEN_LEGACY_CONSTANTS_NOT_CALIBRATED", evidence["scenario_probabilities_status"])
        self.assertFalse(evidence["strict_1500_pit_verified"])
        self.assertNotIn("slot", evidence)
        self.assertIs(evidence.get("natural_verified"), False)

    def test_real_source_data_may_be_read_as_historical_replay_without_becoming_natural(self):
        value = deepcopy(self.committed)
        value["record"].update(data_kind="REAL", execution_kind="HISTORICAL_REPLAY")
        reseal(value)
        preview = api.project_committed_review(value, DATE)
        self.assertEqual("VERIFIED", preview["m09_publication"]["read_status"])
        self.assertEqual("REAL", preview["m09_publication"]["data_kind"])
        self.assertEqual("HISTORICAL_REPLAY", preview["m09_publication"]["execution_kind"])
        self.assertFalse(preview["m09_publication"]["natural_verified"])

    def test_record_scope_provenance_and_natural_limitations_are_visible(self):
        preview = api.project_committed_review(self.committed, DATE)
        evidence = preview["m09_publication"]
        self.assertEqual(self.committed["record"]["cannot_confirm"], evidence.get("record_cannot_confirm"))
        self.assertEqual("DECLARED_UNIVERSE_ONLY", evidence["scope"])
        self.assertFalse(evidence["source_provenance_independently_verified"])
        self.assertFalse(evidence["natural_verified"])
        self.assertEqual(self.committed["record"]["membership"], evidence["membership"])
        evidence["record_cannot_confirm"].append("local-copy-change")
        self.assertNotIn("local-copy-change", self.committed["record"]["cannot_confirm"])

    def test_latest_failed_or_unknown_attempt_is_separate_from_served_success(self):
        for status in ("FAILED", "UNKNOWN"):
            value = deepcopy(self.committed)
            value["latest_attempt"] = {
                "schema_version": "v5.m09.trigger_receipt.v1", "trade_date": DATE,
                "status": status, "slot": "17:10", "run_id": "different-later-attempt",
                "previous_success_generation_sha256": value["identity"]["generation_sha256"],
                "reason": "LATER_ATTEMPT_INCOMPLETE", "issues": ["input gap"],
                "natural_verified": False, "safety": {"research_only": True, **FLAGS},
            }
            before = deepcopy(value)
            with self.subTest(status=status):
                preview = api.project_committed_review(value, DATE)
                evidence = preview["m09_publication"]
                self.assertEqual(status, evidence.get("latest_attempt_status"))
                self.assertEqual(value["latest_attempt"], evidence.get("latest_attempt"))
                self.assertEqual("VERIFIED", evidence["read_status"])
                self.assertEqual("PARTIAL", evidence["business_status"])
                self.assertEqual(value["review"]["model_review"], preview["model_review"])
                for key, expected in value["identity"].items():
                    self.assertEqual(expected, evidence[key], key)
                evidence["latest_attempt"]["issues"].append("changed copy")
                self.assertEqual(before, value)

    def test_no_latest_attempt_does_not_invent_a_trigger_status(self):
        for value in (self.committed, None):
            with self.subTest(committed=value is not None):
                evidence = api.project_committed_review(value, DATE)["m09_publication"]
                self.assertIn("latest_attempt", evidence)
                self.assertIsNone(evidence["latest_attempt"])
                self.assertIn("latest_attempt_status", evidence)
                self.assertIsNone(evidence["latest_attempt_status"])

    def test_publication_recovery_stays_separate_from_served_generation_identity(self):
        value = deepcopy(self.committed)
        value["publication_recovery"] = {
            "status": "PREVIOUS_SUCCESS_SERVED", "unreceipted_generation_sha256": "a" * 64,
            "served_generation_sha256": value["identity"]["generation_sha256"],
            "reason_codes": ["HEAD_HAS_NO_COMPLETED_RECEIPT"],
        }
        before = deepcopy(value)
        preview = api.project_committed_review(value, DATE)
        evidence = preview["m09_publication"]
        self.assertEqual(value["publication_recovery"], evidence.get("publication_recovery"))
        self.assertEqual("VERIFIED", evidence["read_status"])
        self.assertEqual("PARTIAL", evidence["business_status"])
        self.assertEqual(value["review"]["model_review"], preview["model_review"])
        for key, expected in value["identity"].items():
            self.assertEqual(expected, evidence[key], key)
        evidence["publication_recovery"]["reason_codes"].append("changed copy")
        self.assertEqual(before, value)

    def test_unexpected_identity_fields_cannot_override_schema_or_leak_into_metadata(self):
        value = deepcopy(self.committed)
        value["identity"].update(schema_version="untrusted-schema", unrelated_path="/Users/private/unrelated")
        preview = api.project_committed_review(value, DATE)
        self.assertEqual("v5.m09.read_evidence.v1", preview["m09_publication"]["schema_version"])
        self.assertNotIn("unrelated_path", preview["m09_publication"])

    def test_projection_does_not_alias_or_mutate_committed_result(self):
        before = deepcopy(self.committed)
        preview = api.project_committed_review(self.committed, DATE)
        preview["model_review"]["board_rows"][0]["board_name"] = "changed copy"
        preview["m09_publication"]["provenance"]["source_available_at"] = "changed copy"
        self.assertEqual(before, self.committed)

    def test_unknown_source_times_remain_unknown_and_legacy_as_of_is_preserved(self):
        preview = api.project_committed_review(self.committed, DATE)
        self.assertIsNone(preview["m09_publication"]["provenance"]["source_available_at"])
        self.assertEqual("2026-10-09T15:30:00+08:00", preview["model_review"]["as_of"])
        self.assertEqual(self.committed["review"]["cannot_confirm"], preview["cannot_confirm"])
        self.assertEqual("CANNOT_CONFIRM_TARGET_VIDEO_NOT_CONSUMED", preview["model_review"]["target_video_review_status"])

    def test_missing_result_has_exact_date_empty_arrays_and_no_fake_counts(self):
        preview = api.project_committed_review(None, DATE)
        self.assertEqual("MISSING", preview["status"])
        self.assertEqual(DATE, preview["trade_date"])
        self.assertEqual("NOT_MATERIALIZED", preview["model_review"]["status"])
        self.assertEqual("MISSING", preview["m09_publication"]["read_status"])
        self.assertEqual([], preview["core_stocks"])
        self.assertEqual([], preview["observation_pool"])
        self.assertNotIn("market_summary", preview["model_review"])
        self.assertIsNone(preview["m09_publication"]["generation_sha256"])

    def test_bad_request_dates_are_rejected_before_reading(self):
        for target in ("20261032", "2026-10-09", "", 20261009):
            with self.subTest(target=target), self.assertRaises(ValueError):
                api.project_committed_review(self.committed, target)

    def test_changed_review_record_or_generation_is_not_served(self):
        for layer in ("review", "record", "generation"):
            value = deepcopy(self.committed)
            value[layer]["unverified_mutation"] = True
            with self.subTest(layer=layer):
                preview = api.project_committed_review(value, DATE)
                self.assertEqual("CANNOT_CONFIRM", preview["status"])
                self.assertNotIn("market_summary", preview["model_review"])

    def test_raw_review_identity_is_bound_to_the_recorded_original_file(self):
        value = deepcopy(self.committed)
        value["identity"]["raw_review_sha256"] = "f" * 64
        preview = api.project_committed_review(value, DATE)
        self.assertEqual("CANNOT_CONFIRM", preview["m09_publication"]["read_status"])
        self.assertIsNone(preview["m09_publication"]["raw_review_sha256"])

    def test_original_store_metadata_requires_exact_paths_hashes_and_sizes(self):
        for case in ("absent", "missing_receipt", "wrong_date", "bool_size", "bad_hash", "extra_path"):
            value = deepcopy(self.committed)
            files = value["record"]["store_files"]
            review_path = "a_share_reviews/" + DATE + ".json"
            if case == "absent":
                del value["record"]["store_files"]
            elif case == "missing_receipt":
                del files["a_share_reviews/receipts/" + DATE + ".json"]
            elif case == "wrong_date":
                files["a_share_reviews/20261008.json"] = files.pop(review_path)
            elif case == "bool_size":
                files[review_path]["bytes"] = True
            elif case == "bad_hash":
                files["a_share_reviews/manifest.json"]["sha256"] = "invalid"
            else:
                files["../unrelated.json"] = {"sha256": "f" * 64, "bytes": 1}
            reseal(value)
            with self.subTest(case=case):
                self.assertEqual("CANNOT_CONFIRM", api.project_committed_review(value, DATE)["status"])

    def test_resealed_cross_date_evidence_is_not_served(self):
        for layer in ("review", "record", "generation", "identity"):
            value = deepcopy(self.committed)
            value[layer]["trade_date"] = "20261008"
            reseal(value)
            with self.subTest(layer=layer):
                self.assertEqual("CANNOT_CONFIRM", api.project_committed_review(value, DATE)["status"])

    def test_resealed_model_date_and_run_mismatches_are_not_served(self):
        cases = (("review_date", "20261008"), ("run_id", "different-run"))
        for field, bad_value in cases:
            value = deepcopy(self.committed)
            value["review"]["model_review"][field] = bad_value
            reseal(value)
            with self.subTest(field=field):
                self.assertEqual("CANNOT_CONFIRM", api.project_committed_review(value, DATE)["status"])

    def test_resealed_source_mismatch_is_not_served(self):
        value = deepcopy(self.committed)
        value["record"]["source_sha256"] = "f" * 64
        reseal(value)
        self.assertEqual("CANNOT_CONFIRM", api.project_committed_review(value, DATE)["status"])

    def test_resealed_unsafe_boundaries_are_not_served(self):
        mutations = (("review", "orders_sent", True), ("record_safety", "research_only", False),
                     ("model_safety", "NO_BUY_GATE", False))
        for layer, key, unsafe in mutations:
            value = deepcopy(self.committed)
            target = value["review"] if layer == "review" else value["record"]["safety"] if layer == "record_safety" else value["review"]["model_review"]["safety"]
            target[key] = unsafe
            reseal(value)
            with self.subTest(layer=layer):
                self.assertEqual("CANNOT_CONFIRM", api.project_committed_review(value, DATE)["status"])

    def test_missing_required_ui_array_is_not_repaired_into_success(self):
        value = deepcopy(self.committed)
        del value["review"]["core_stocks"]
        reseal(value)
        self.assertEqual("CANNOT_CONFIRM", api.project_committed_review(value, DATE)["status"])

    def test_native_model_status_and_research_limits_are_enforced(self):
        cases = (("status", "READY"), ("semantic_model_call_count", 1),
                 ("model_promotion", "PROMOTED"), ("target_video_evidence_count", 1),
                 ("semantic_model_status", "ENABLED"), ("formal_generalization", "PROMOTED"),
                 ("learning_status", "LEARNING_PROVEN"))
        for key, bad_value in cases:
            value = deepcopy(self.committed)
            value["review"]["model_review"][key] = bad_value
            reseal(value)
            with self.subTest(key=key):
                self.assertEqual("CANNOT_CONFIRM", api.project_committed_review(value, DATE)["status"])

    def test_missing_incomplete_or_unsafe_native_chain_is_not_verified(self):
        for alteration in ("absent", "schema", "order", "node_date", "safety"):
            value = deepcopy(self.committed)
            chain = value["review"]["close_chain"]
            if alteration == "absent":
                value["review"]["close_chain"] = None
            elif alteration == "schema":
                chain["schema_version"] = "other.chain.v1"
            elif alteration == "order":
                chain["nodes"] = list(reversed(chain["nodes"]))
            elif alteration == "node_date":
                chain["nodes"][0]["business_date"] = "20261008"
            else:
                chain["orders_sent"] = True
            reseal(value)
            with self.subTest(alteration=alteration):
                self.assertEqual("CANNOT_CONFIRM", api.project_committed_review(value, DATE)["status"])

    def test_nonfinite_payload_fails_closed(self):
        value = deepcopy(self.committed)
        value["review"]["model_review"]["market_summary"]["market_width"] = float("nan")
        self.assertEqual("CANNOT_CONFIRM", api.project_committed_review(value, DATE)["status"])

    def test_invalid_schema_and_data_kind_pair_fail_closed(self):
        for key, bad_value in (("schema_version", "other.record.v1"), ("execution_kind", "NATURAL"), ("data_kind", "OWNER_RESULT")):
            value = deepcopy(self.committed)
            value["record"][key] = bad_value
            reseal(value)
            with self.subTest(key=key):
                self.assertEqual("CANNOT_CONFIRM", api.project_committed_review(value, DATE)["status"])

    def test_single_pinned_reader_result_is_consumed_without_writes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "absent-read-root"
            with patch.object(api, "_read_committed", return_value=self.committed) as reader, \
                    patch.object(api, "_read_latest_attempt", create=True) as latest_reader:
                preview = api.read_a_close_preview(root, DATE)
            reader.assert_called_once_with(root, DATE)
            latest_reader.assert_not_called()
            self.assertEqual(self.committed["identity"]["generation_sha256"], preview["m09_publication"]["generation_sha256"])
            self.assertFalse(root.exists())

    def test_first_failed_attempt_remains_visible_without_a_committed_generation(self):
        receipt = {"schema_version": "v5.m09.trigger_receipt.v1", "trade_date": DATE,
                   "status": "FAILED", "slot": "16:05", "reason": "INPUT_GAP",
                   "issues": ["NO_ADMITTED_PANEL"], "natural_verified": False,
                   "safety": {"research_only": True, **FLAGS}}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "absent-read-root"
            with patch.object(api, "_read_committed", return_value=None) as reader, \
                    patch.object(api, "_read_latest_attempt", return_value=receipt, create=True) as latest_reader:
                preview = api.read_a_close_preview(root, DATE)
            reader.assert_called_once_with(root, DATE)
            latest_reader.assert_called_once_with(root, DATE)
            self.assertFalse(root.exists())
        evidence = preview["m09_publication"]
        self.assertEqual("MISSING", preview["status"])
        self.assertEqual("MISSING", evidence["read_status"])
        self.assertEqual("FAILED", evidence["latest_attempt_status"])
        self.assertEqual(receipt, evidence["latest_attempt"])
        self.assertIsNone(evidence["generation_sha256"])
        self.assertNotIn("market_summary", preview["model_review"])
        evidence["latest_attempt"]["issues"].append("changed copy")
        self.assertEqual(["NO_ADMITTED_PANEL"], receipt["issues"])

    def test_latest_attempt_read_failure_does_not_turn_missing_product_into_success(self):
        with patch.object(api, "_read_committed", return_value=None) as reader, \
                patch.object(api, "_read_latest_attempt", side_effect=ValueError("bad /Users/private/attempt"), create=True) as latest_reader:
            preview = api.read_a_close_preview(Path("/nonexistent-m09-root"), DATE)
        reader.assert_called_once()
        latest_reader.assert_called_once()
        self.assertEqual("MISSING", preview["status"])
        evidence = preview["m09_publication"]
        self.assertEqual("MISSING", evidence["read_status"])
        self.assertIn("M09_LATEST_ATTEMPT_READ_FAILED", evidence["reason_codes"])
        self.assertIsNone(evidence["latest_attempt"])
        self.assertIsNone(evidence["latest_attempt_status"])
        self.assertNotIn("/Users/private", json.dumps(preview))

    def test_reader_error_is_explicit_and_does_not_leak_local_path(self):
        with patch.object(api, "_read_committed", side_effect=ValueError("bad /Users/private/root/file.json")) as reader:
            preview = api.read_a_close_preview(Path("/nonexistent-m09-root"), DATE)
        reader.assert_called_once()
        self.assertEqual("CANNOT_CONFIRM", preview["status"])
        self.assertNotIn("/Users/private", json.dumps(preview))
        self.assertNotIn("market_summary", preview["model_review"])

    def test_invalid_request_never_calls_generation_reader(self):
        with patch.object(api, "_read_committed") as reader, self.assertRaises(ValueError):
            api.read_a_close_preview(Path("/nonexistent-m09-root"), "20261032")
        reader.assert_not_called()


class M09EnvelopeCompositionTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(api, "M09-only committed read adapter is not implemented")
        self.preview = api.project_committed_review(committed_fixture(), DATE)
        self.envelope = {
            "schema_version": "v3_5.review_envelope.v1", "trade_date": DATE,
            "market_reviews": {"A": {"old-a": True}, "HK": {"market": "HK", "model_selection_review": {"trade_date": DATE, "rows": [3, 1, 2], "source_sha256": "hk-original-source"}}},
            "fupan_review_v3": {"old-a": True, "source_run_id": "old-core-run", "board_rows": [{"stale": True}]},
            "review_core_bundle": {"source_role": "REVIEW_CORE_BUNDLE_V1", "status": "READY"},
            "review_evidence_layers": {"daily_independent_replay": {"run_id": "old-core-run"}},
            "research_review": {"unknown_preserved": ["research"]}, "intraday_research": {"slots": ["existing"]},
            "reference_snapshot": True, "mixed_market_unknown": {"HK": "preserve", "A": "do not guess"}, **FLAGS,
        }

    def test_merge_preserves_hk_and_every_unrelated_top_key_exactly(self):
        before = deepcopy(self.envelope)
        merged = api.merge_a_close_preview(self.envelope, self.preview)
        self.assertEqual(before, self.envelope)
        self.assertEqual(before["market_reviews"]["HK"], merged["market_reviews"]["HK"])
        for key in ("schema_version", "trade_date", "research_review", "intraday_research", "reference_snapshot", "mixed_market_unknown", *FLAGS):
            self.assertEqual(before[key], merged[key], key)
        merged["market_reviews"]["HK"]["model_selection_review"]["rows"].append(99)
        self.assertEqual(before, self.envelope)

    def test_merge_updates_a_legacy_aliases_and_removes_only_proven_a_attribution(self):
        merged = api.merge_a_close_preview(self.envelope, self.preview)
        legacy = merged["fupan_review_v3"]
        aliases = {"first_screen_big_picture": "big_picture", "next_day_trigger_tree_v2": "next_day_trigger_tree",
                   "human_video_gap_scorecard": "quality_gate", "localized_role_rows": "core_stocks", "replay_model_v1": "model_review"}
        for old, new in aliases.items():
            self.assertEqual(self.preview[new], legacy[old])
        self.assertNotIn("old-a", legacy)
        self.assertNotIn("board_rows", legacy)
        self.assertNotIn("review_core_bundle", merged)
        self.assertNotIn("review_evidence_layers", merged)
        self.assertEqual(self.preview["m09_publication"], merged["m09_publication"])
        self.assertEqual(self.preview, merged["market_reviews"]["A"])

    def test_merge_missing_a_keeps_hk_and_never_reuses_old_a(self):
        missing = api.project_committed_review(None, DATE)
        merged = api.merge_a_close_preview(self.envelope, missing)
        self.assertEqual("MISSING", merged["market_reviews"]["A"]["status"])
        self.assertEqual(self.envelope["market_reviews"]["HK"], merged["market_reviews"]["HK"])
        self.assertEqual([], merged["fupan_review_v3"]["core_stocks"])

    def test_merge_refuses_cross_date_or_unsafe_preview(self):
        for change in ({"trade_date": "20261008"}, {"orders_sent": True}):
            preview = deepcopy(self.preview)
            preview.update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                api.merge_a_close_preview(self.envelope, preview)


if __name__ == "__main__":
    unittest.main()
