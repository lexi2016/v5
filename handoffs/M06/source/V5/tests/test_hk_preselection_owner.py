"""Original-owner boundary tests using explicitly synthetic, offline input.

These tests exercise publication/storage/readback, not frozen-model scoring.
The genuine materializer is exercised only on a missing-asset rejection.
No owner callback, model hash, vendor source, clock, or runtime is patched.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest


BASE = Path(__file__).resolve().parents[1]
OWNER_PREFIX = "upstreams/v3_shared_data/shared_data/"
OWNER_FILES = (
    "__init__.py", "allowlist.py", "collectors.py", "constants.py",
    "consumer.py", "hashing.py", "hk_0_2.py", "hk_security_master.py",
    "paths.py", "store.py",
)


def _inventory(root):
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*")) if path.is_file()
    }


def _owner_worker():
    import csv
    from datetime import datetime
    import importlib
    import platform
    import shutil
    import tempfile
    from zoneinfo import ZoneInfo

    sys.path.insert(0, str(BASE / "src"))
    sys.path.insert(0, str(BASE / "tests"))
    from fixtures.hk_preselection_verified_factory import create_verified_fixture
    from v5_shadow import hk_preselection as consumer
    from v5_shadow.hk_preselection_verified import run_verified_hk_preselection

    if any(name in sys.modules for name in ("domains", "infrastructure", "contracts", "upstreams")):
        raise AssertionError("Owner test requires a cold worker")
    pinned_sources = consumer._source_bytes()
    closure = {OWNER_PREFIX + name: pinned_sources[OWNER_PREFIX + name] for name in OWNER_FILES}
    sys.meta_path.insert(0, consumer._HKLoader(closure))
    owner = importlib.import_module("upstreams.v3_shared_data.shared_data.hk_0_2")
    master_owner = importlib.import_module("upstreams.v3_shared_data.shared_data.hk_security_master")
    store_owner = importlib.import_module("upstreams.v3_shared_data.shared_data.store")

    with tempfile.TemporaryDirectory(prefix="m06-original-owner-") as temporary:
        root = Path(temporary).resolve()
        synthetic_root = root / "synthetic-input"
        output_root = root / "original-owner-output"
        fixture = create_verified_fixture(synthetic_root)
        # Only the explicitly synthetic master is an input to the real publisher.
        # Never pre-create a successful pool in the owner's output store.
        shutil.copytree(synthetic_root / "assets", output_root / "assets")
        with (synthetic_root / fixture["expected_source"]["artifact_relative"]).open(
            encoding="utf-8-sig", newline=""
        ) as stream:
            rows = list(csv.DictReader(stream))
        for row in rows:
            row.update(
                bar_time="17:30", code=row["code_norm"], production_allowed=False,
                research_only=True, cannot_confirm="", trade_status_contract="WATCH_ONLY",
                recommendation_status="WATCH_ONLY_BACKTEST_GATED",
                freeze_status="D1_POOL_V1_FROZEN_RESEARCH_ONLY",
            )
        dates = dict(signal_date="20261007", eligibility_source_date="20260930", target_date="20261008")
        publication = owner.publish_hk_0_2_rows(
            output_root, **dates, rows=rows, panel_sha256="f" * 64
        )
        pool = owner.read_verified_hk_0_2_pool(
            output_root, target_date=dates["target_date"],
            expected_signal_date=dates["signal_date"],
            expected_eligibility_source_date=dates["eligibility_source_date"],
        )
        master, master_manifest = master_owner.load_verified_hk_security_master(
            output_root, dates["eligibility_source_date"]
        )
        expected_rows = [
            {field: owner._cell(row.get(field)) for field in owner._OUTPUT_FIELDS}
            for row in rows
        ]
        initial_inventory = _inventory(output_root)
        repeated = owner.publish_hk_0_2_rows(
            output_root, **dates, rows=rows, panel_sha256="f" * 64
        )
        idempotent_inventory = _inventory(output_root)

        missing_asset_results = []
        for target_store in (root / "uncreated-store", output_root):
            before = _inventory(target_store)
            existed_before = target_store.exists()
            try:
                owner.materialize_frozen_hk_0_2(
                    target_store, root / "absent-assets", **dates
                )
            except store_owner.StoreError as error:
                missing_asset_results.append(dict(
                    error_type=type(error).__name__, error=str(error),
                    existed_before=existed_before, exists_after=target_store.exists(),
                    unchanged=before == _inventory(target_store),
                ))
            else:
                raise AssertionError("Original materializer accepted absent assets")

        versions = dict(
            python=platform.python_version(), sklearn=owner._package_version("scikit-learn"),
            joblib=owner._package_version("joblib"),
        )
        pins = dict(python=owner.HK_0_2_PYTHON_VERSION, sklearn=owner.HK_0_2_SKLEARN_VERSION,
                    joblib=owner.HK_0_2_JOBLIB_VERSION)
        expected_error = next((message for key, message in (
            ("python", "HK 0.2 requires Python 3.13.12"),
            ("sklearn", "HK 0.2 requires scikit-learn 1.9.0"),
            ("joblib", "HK 0.2 requires joblib 1.5.3"),
        ) if versions[key] != pins[key]), None)
        runtime = dict(actual=versions, pins=pins, expected_error=expected_error)
        if expected_error is not None:
            absent_model = root / "absent-models.joblib"
            assets = owner.FrozenHK02Assets(
                root=root, panel_path=root / "absent-panel.parquet", panel_manifest={},
                model_path=absent_model,
                model_manifest={"trained_through": owner.HK_0_2_MODEL_TRAINED_THROUGH},
                name_dictionary_path=None,
            )
            try:
                owner._load_models(assets, signal_date=dates["signal_date"])
            except store_owner.StoreError as error:
                runtime.update(error_type=type(error).__name__, error=str(error),
                               model_still_absent=not absent_model.exists())
            else:
                raise AssertionError("Original model loader accepted a nonmatching runtime")

        request = dict(
            schema_version="v5.hk_preselection_verified_request.v1",
            target_date=dates["target_date"], signal_date=dates["signal_date"],
            eligibility_source_date=dates["eligibility_source_date"],
            research_cutoff="2026-10-08T09:20:00+08:00", data_kind="SOURCE_SNAPSHOT",
            input_root=str(output_root), files=_inventory(output_root),
            expected_source=dict(role=owner.HK_0_2_ROLE, **{
                field: pool.run.verification[field]
                for field in ("run_id", "artifact_relative", "artifact_sha256",
                              "manifest_sha256", "receipt_sha256")
            }),
        )
        cutoff = datetime.fromisoformat(request["research_cutoff"])
        captured = datetime.fromisoformat(pool.run.manifest["captured_at"])
        # Use the real wall clock. Historical output cannot acquire fabricated
        # early timestamps just to fit the consumer's PIT admission window.
        late_result = run_verified_hk_preselection(request) if captured > cutoff else None

        # Independently admit an actual current-date owner publication using
        # the unchanged frozen calendar and the unmodified wall clock.
        sys.meta_path.insert(0, consumer._HKLoader(pinned_sources))
        calendars = importlib.import_module("contracts.trading_calendar")
        calendar_path = root / "frozen-market-calendar-2026.json"
        calendar_path.write_bytes(pinned_sources["contracts/market_calendar_2026.json"])
        calendar = calendars.load_market_calendar(calendar_path)
        target = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y%m%d")
        state = calendars.resolve_market_states(calendar, target)["hk_securities"].value
        current_result = dict(target_date=target, market_state=state, skip_reason="")
        if state not in ("FULL_TRADING_DAY", "HALF_TRADING_DAY_AM"):
            current_result["skip_reason"] = "Current HK date is not a securities session in the frozen 2026 calendar"
        else:
            signal = calendars.previous_session(calendar, target, market="hk_securities")
            current_fixture_root = root / "current-synthetic-input"
            current_output_root = root / "current-owner-output"
            current_fixture = create_verified_fixture(
                current_fixture_root, target=target, signal=signal, eligibility=signal,
                master_capture_time="16:30:00",
            )
            shutil.copytree(current_fixture_root / "assets", current_output_root / "assets")
            with (current_fixture_root / current_fixture["expected_source"]["artifact_relative"]).open(
                encoding="utf-8-sig", newline=""
            ) as stream:
                current_rows = list(csv.DictReader(stream))
            for row in current_rows:
                row.update(
                    bar_time="17:30", code=row["code_norm"], production_allowed=False,
                    research_only=True, cannot_confirm="", trade_status_contract="WATCH_ONLY",
                    recommendation_status="WATCH_ONLY_BACKTEST_GATED",
                    freeze_status="D1_POOL_V1_FROZEN_RESEARCH_ONLY",
                )
            current_publication = owner.publish_hk_0_2_rows(
                current_output_root, signal_date=signal, target_date=target,
                eligibility_source_date=signal, rows=current_rows, panel_sha256="f" * 64,
            )
            current_pool = owner.read_verified_hk_0_2_pool(
                current_output_root, target_date=target, expected_signal_date=signal,
                expected_eligibility_source_date=signal,
            )
            current_master, current_master_manifest = master_owner.load_verified_hk_security_master(
                current_output_root, signal
            )
            current_cutoff = f"{target[:4]}-{target[4:6]}-{target[6:]}T23:59:59+08:00"
            current_request = dict(
                schema_version="v5.hk_preselection_verified_request.v1",
                target_date=target, signal_date=signal, eligibility_source_date=signal,
                research_cutoff=current_cutoff, data_kind="SOURCE_SNAPSHOT",
                input_root=str(current_output_root), files=_inventory(current_output_root),
                expected_source=dict(role=owner.HK_0_2_ROLE, **{
                    field: current_pool.run.verification[field]
                    for field in ("run_id", "artifact_relative", "artifact_sha256",
                                  "manifest_sha256", "receipt_sha256")
                }),
            )
            current_captured = datetime.fromisoformat(current_pool.run.manifest["captured_at"])
            if current_captured > datetime.fromisoformat(current_cutoff):
                current_result["skip_reason"] = "Actual clock crossed the target cutoff during publication"
            else:
                verified = run_verified_hk_preselection(current_request)
                legacy_request = {
                    key: value for key, value in current_request.items()
                    if key not in ("schema_version", "expected_source")
                }
                legacy_request["data_kind"] = "SYNTHETIC"
                legacy_result = consumer.run_hk_preselection(legacy_request)
                current_result.update(
                    signal_date=signal, eligibility_source_date=signal,
                    research_cutoff=current_cutoff, publication=current_publication,
                    captured_at=current_pool.run.manifest["captured_at"],
                    finished_at=current_pool.run.receipt["finished_at"],
                    master_captured_at=current_master_manifest["captured_at"],
                    owner=current_pool.run.receipt["owner"],
                    pool_fixture_only=current_pool.run.manifest.get("fixture_only"),
                    master_fixture_only=current_master_manifest.get("fixture_only"),
                    master_sources=sorted({row["source"] for row in current_master.values()}),
                    expected_source=current_request["expected_source"],
                    verified=verified, legacy=legacy_result,
                )
        return dict(
            evidence_scope="SYNTHETIC_PUBLISH_STORE_READ_ONLY",
            model_scoring_executed=False, model_weights_reverified=False,
            panel_read=False, closure_files=list(closure),
            closure_bytes=sum(map(len, closure.values())),
            original_owner_sha256=hashlib.sha256(closure[OWNER_PREFIX + "hk_0_2.py"]).hexdigest(),
            publication=publication, verification=pool.run.verification,
            receipt=pool.run.receipt, rows=list(pool.rows), expected_rows=expected_rows,
            master_sources=sorted({row["source"] for row in master.values()}),
            master_fixture_only=master_manifest.get("fixture_only"),
            idempotent=repeated,
            idempotent_bytes_unchanged=initial_inventory == idempotent_inventory,
            missing_asset_results=missing_asset_results, runtime=runtime,
            captured_at=pool.run.manifest["captured_at"], late_result=late_result,
            current_result=current_result,
        )


class HKOriginalOwnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        process = subprocess.run(
            [sys.executable, "-I", "-B", str(Path(__file__).resolve()), "--owner-worker"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=120,
        )
        if process.returncode:
            raise AssertionError(f"Cold original-owner worker failed: {process.stderr}\n{process.stdout}")
        cls.result = json.loads(process.stdout)
        # The retained test log records actual runtime and source identity.
        print("ORIGINAL_OWNER_EVIDENCE " + json.dumps({
            key: cls.result[key] for key in (
                "evidence_scope", "model_scoring_executed", "model_weights_reverified",
                "panel_read", "closure_files", "closure_bytes", "original_owner_sha256",
                "publication", "master_sources", "runtime", "captured_at",
            )
        }, sort_keys=True), flush=True)
        current = cls.result["current_result"]
        summary = {key: value for key, value in current.items() if key not in ("verified", "legacy")}
        if not current["skip_reason"]:
            summary.update(
                verified_status=current["verified"]["status"],
                legacy_status=current["legacy"]["status"],
                verified_fixture_only=current["verified"].get("fixture_only"),
                complete_artifacts_equal=current["verified"]["artifact"] == current["legacy"]["artifact"],
            )
        print("CURRENT_DATE_ORIGINAL_OWNER_EVIDENCE " + json.dumps(summary, sort_keys=True), flush=True)

    def test_real_owner_publishes_and_reads_all_100_synthetic_rows(self):
        result = self.result
        self.assertEqual(result["publication"]["status"], "READY")
        self.assertEqual(result["receipt"]["owner"], "v3_shared_data")
        self.assertEqual(result["verification"]["row_count"], 100)
        self.assertEqual(result["rows"], result["expected_rows"])
        self.assertEqual([row["rank"] for row in result["rows"]], [str(i) for i in range(1, 101)])
        self.assertEqual(len({row["code_norm"] for row in result["rows"]}), 100)
        for field in ("run_id", "artifact_sha256", "manifest_sha256", "receipt_sha256"):
            self.assertEqual(result["publication"][field], result["verification"][field])
        for key in ("production_allowed", "buy_gate_updated", "orders_sent"):
            self.assertIs(result["receipt"][key], False)
        self.assertEqual(result["master_sources"], ["SYNTHETIC_FIXTURE"])
        self.assertIs(result["master_fixture_only"], True)
        self.assertIs(result["model_scoring_executed"], False)
        self.assertIs(result["model_weights_reverified"], False)
        self.assertIs(result["panel_read"], False)

    def test_real_owner_same_input_is_idempotent(self):
        self.assertIs(self.result["idempotent"]["already_exists"], True)
        self.assertIs(self.result["idempotent_bytes_unchanged"], True)
        for field in ("run_id", "artifact_sha256", "manifest_sha256", "receipt_sha256"):
            self.assertEqual(self.result["idempotent"][field], self.result["verification"][field])

    def test_real_materializer_missing_assets_creates_no_output(self):
        rejection = self.result["missing_asset_results"][0]
        self.assertEqual(rejection["error_type"], "StoreError")
        self.assertIn("panel_latest.json", rejection["error"])
        self.assertIs(rejection["existed_before"], False)
        self.assertIs(rejection["exists_after"], False)
        self.assertIs(rejection["unchanged"], True)

    def test_real_materializer_failure_preserves_existing_success(self):
        rejection = self.result["missing_asset_results"][1]
        self.assertEqual(rejection["error_type"], "StoreError")
        self.assertIs(rejection["existed_before"], True)
        self.assertIs(rejection["exists_after"], True)
        self.assertIs(rejection["unchanged"], True)

    def test_original_model_loader_rejects_actual_nonpinned_runtime(self):
        runtime = self.result["runtime"]
        if runtime["expected_error"] is None:
            self.skipTest("Installed runtime matches every original pin; mismatch case is inapplicable")
        self.assertEqual(runtime["error_type"], "StoreError")
        self.assertEqual(runtime["error"], runtime["expected_error"])
        self.assertIs(runtime["model_still_absent"], True)

    def test_actual_late_publication_is_not_historical_pit_evidence(self):
        result = self.result["late_result"]
        if result is None:
            self.skipTest("Actual publication clock does not postdate the fixed historical cutoff")
        self.assertEqual(result["status"], "CANNOT_CONFIRM")
        self.assertIsNone(result["artifact"])
        self.assertIn("HK_SOURCE_AFTER_CUTOFF", result["reason"])

    def test_current_real_owner_matches_legacy_and_retains_synthetic_master_provenance(self):
        from datetime import datetime

        result = self.result["current_result"]
        if result["skip_reason"]:
            self.skipTest(result["skip_reason"])
        self.assertEqual(result["publication"]["status"], "READY")
        self.assertEqual(result["owner"], "v3_shared_data")
        self.assertIsNone(result["pool_fixture_only"])
        self.assertIs(result["master_fixture_only"], True)
        self.assertEqual(result["master_sources"], ["SYNTHETIC_FIXTURE"])
        self.assertEqual(result["signal_date"], result["eligibility_source_date"])
        self.assertLessEqual(datetime.fromisoformat(result["master_captured_at"]),
                             datetime.fromisoformat(result["captured_at"]))
        self.assertLessEqual(datetime.fromisoformat(result["captured_at"]),
                             datetime.fromisoformat(result["finished_at"]))
        self.assertLessEqual(datetime.fromisoformat(result["finished_at"]),
                             datetime.fromisoformat(result["research_cutoff"]))
        verified = result["verified"]
        legacy = result["legacy"]
        self.assertEqual(verified["status"], "ASSEMBLED")
        self.assertEqual(legacy["status"], "ASSEMBLED")
        self.assertEqual(verified["artifact"], legacy["artifact"])
        self.assertEqual(len(verified["artifact"]["rows"]), 100)
        self.assertEqual(verified["verified_source_reference"], result["expected_source"])
        self.assertIs(verified["model_weights_reverified"], False)
        self.assertIs(verified["formal_eligibility_verified"], False)
        self.assertIs(verified["natural_verified"], False)
        self.assertIs(verified["fixture_only"], True)


if __name__ == "__main__":
    if sys.argv[1:] == ["--owner-worker"]:
        print(json.dumps(_owner_worker(), sort_keys=True))
    else:
        unittest.main()
