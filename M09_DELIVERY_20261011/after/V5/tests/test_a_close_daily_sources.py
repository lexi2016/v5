"""M09 engineering tests; admitted-frame parity does not test parquet decoding."""
from __future__ import annotations

import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd


T = "20261009"
COLUMNS = [
    "trade_date", "ts_code", "name", "pct_chg", "amount", "bar_close_pos",
    "tdx_industry_code", "tdx_industry_name",
]


def fixture_frame():
    """Synthetic declared-membership fixture, never real market evidence."""
    return pd.DataFrame([
        [T, "600001.SH", "Alpha", 4.0, 500_000_000.0, 0.9, "A", "Resilient"],
        [T, "000002.SZ", "Beta", 2.0, 800_000_000.0, 0.8, "A", "Resilient"],
        [T, "600003.SH", "Gamma", -10.0, 400_000_000.0, 0.1, "B", "Risk"],
        [T, "000004.SZ", "Delta", -6.0, 200_000_000.0, 0.2, "B", "Risk"],
        [T, "830005.BJ", "Epsilon", 0.0, 100_000_000.0, 0.5, "C", "Flat"],
    ], columns=COLUMNS)


def _original_producer_worker():
    """Isolated oracle: compile original bytes, never import candidate loader.

    This explicit engineering adapter replaces only pyarrow dataset decoding
    because this execution environment has no pyarrow. It does not claim raw
    parquet reader parity. All business/product/store modules are original.
    """
    import builtins
    import types

    request = json.loads(sys.stdin.read())
    donor = Path(request["donor_root"])
    for relative, expected in request["source_files"].items():
        raw = (donor / relative).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == expected
    sys.path.insert(0, str(donor))
    frame = pd.DataFrame(request["rows"], columns=COLUMNS)

    class Field:
        def __init__(self, name):
            self.name = name

        def __eq__(self, value):
            return self.name, value

    class Table:
        num_rows = len(frame)

        def to_pandas(self):
            return frame.copy(deep=True)

    class Dataset:
        def to_table(self, *, columns, filter):
            assert list(columns) == COLUMNS
            assert filter == ("trade_date", request["trade_date"])
            return Table()

    def dataset(path, *, format):
        assert path == request["panel_path"] and format == "parquet"
        return Dataset()

    private_pyarrow = types.ModuleType("original_worker_admitted_pyarrow")
    private_dataset = types.ModuleType("original_worker_admitted_pyarrow.dataset")
    private_dataset.dataset, private_dataset.field = dataset, Field
    private_pyarrow.dataset = private_dataset
    original_import = builtins.__import__

    def producer_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "pyarrow.dataset":
            return private_dataset if fromlist else private_pyarrow
        return original_import(name, globals, locals, fromlist, level)

    path = donor / "ops/build_a_share_close_review.py"
    raw = path.read_bytes()
    namespace = {"__name__": "m09_original_producer_oracle", "__file__": str(path),
                 "__builtins__": dict(vars(builtins), __import__=producer_import)}
    exec(compile(raw, str(path), "exec"), namespace)
    result = namespace["build_review_from_panel"](
        Path(request["run_root"]), request["trade_date"],
        panel_pointer=Path(request["panel_pointer"]), run_id=request["run_id"],
        **request["context"],
    )
    from infrastructure.a_share_review_store import AShareReviewStore
    independent = AShareReviewStore(Path(request["run_root"])).read_review(request["trade_date"])
    assert independent == result["review"]
    print(json.dumps({"result": result, "independent_reader": independent,
                      "producer_sha256": hashlib.sha256(raw).hexdigest(),
                      "mode": "ORIGINAL_PRODUCER_ADMITTED_FRAME_IO", "parquet_decode": "NOT_RUN"},
                     ensure_ascii=False, sort_keys=True, allow_nan=False))


def _parity_report(sources, root, *, context=None):
    donor = Path(os.environ.get("M09_ORIGINAL_SOURCE_ROOT", str(
        Path(__file__).absolute().parents[3] / "original/source/handoff/v4-running-source-20261005/canonical"
    )))
    if not (donor / "ops/build_a_share_close_review.py").is_file():
        raise FileNotFoundError("Original F donor tree missing; set M09_ORIGINAL_SOURCE_ROOT")
    raw = json.dumps({"kind": "ENGINEERING_SYNTHETIC", "rows": fixture_frame().to_dict("records")}, sort_keys=True).encode()
    panel = root / "engineering_panel.json"
    panel.write_bytes(raw)
    pointer = root / "panel_pointer.txt"
    pointer.write_text(str(panel), encoding="utf-8")
    context = context or {}
    identity = sources.sources_identity()
    request = {
        "donor_root": str(donor), "source_files": {name: row["sha256"] for name, row in identity["files"].items()},
        "rows": fixture_frame().to_dict("records"), "trade_date": T,
        "panel_path": str(panel), "panel_pointer": str(pointer), "run_root": str(root / "original"),
        "run_id": "m09-full-product-parity", "context": context,
    }
    worker = subprocess.run(
        [sys.executable, "-I", "-B", str(Path(__file__).absolute()), "--original-producer-worker"],
        input=json.dumps(request).encode(), capture_output=True, timeout=30,
    )
    if worker.returncode:
        raise AssertionError("Original producer exception preserved:\n" + worker.stderr.decode(errors="replace"))
    original = json.loads(worker.stdout)
    candidate = sources.build_from_admitted_panel(
        root / "candidate", T, pointer, fixture_frame(), hashlib.sha256(raw).hexdigest(), request["run_id"], context,
    )
    independently_read = sources.read_original_review(root / "candidate", T)
    return {
        "schema_version": "v5.m09.algorithm_parity.v1", "data_kind": "SYNTHETIC",
        "mode": "FULL_ORIGINAL_PRODUCER_PRODUCT_STORE_READER_WITH_ADMITTED_FRAME_IO",
        "raw_parquet_decode_parity": "NOT_RUN_PYARROW_UNAVAILABLE_IN_THIS_ENVIRONMENT",
        "source_identity": identity, "original_producer_sha256": original["producer_sha256"],
        "comparison_rule": "Exact JSON data equality; preserve every field and list order; no field exclusions",
        "review_equal": original["result"]["review"] == candidate["review"],
        "publication_equal": original["result"]["publication"] == candidate["publication"],
        "independent_reader_equal": original["independent_reader"] == independently_read == candidate["review"],
        "original_result": original["result"], "candidate_result": candidate,
    }


class SourceTests(unittest.TestCase):
    def sources(self):
        name = "v5_shadow.a_close_daily_sources"
        self.assertIsNotNone(importlib.util.find_spec(name), "M09 source adapter is not implemented")
        return importlib.import_module(name)

    def stage(self, root, frame=None):
        # Deliberately JSON bytes: only the explicitly admitted-frame producer
        # adapter is under test here; no claim of pyarrow/parquet decode.
        staged_frame = fixture_frame() if frame is None else frame
        raw = json.dumps({"kind": "ENGINEERING_SYNTHETIC", "rows": staged_frame.to_dict("records")}, sort_keys=True).encode()
        panel = root / "input" / "engineering_panel.json"
        panel.parent.mkdir()
        panel.write_bytes(raw)
        pointer = root / "input" / "panel_pointer.txt"
        pointer.write_text(str(panel), encoding="utf-8")
        return panel, pointer, hashlib.sha256(raw).hexdigest()

    def build(self, sources, root, **changes):
        panel, pointer, digest = self.stage(root, changes.get("admitted_frame"))
        arguments = dict(
            run_root=root / "run", trade_date=T, panel_pointer=pointer,
            admitted_frame=fixture_frame(), expected_panel_sha256=digest,
            run_id="m09-engineering-run", context={},
        )
        arguments.update(changes)
        return sources.build_from_admitted_panel(**arguments)

    def test_identity_covers_original_producer_store_calendar_and_dynamic_json(self):
        sources = self.sources()
        identity = sources.sources_identity()
        self.assertEqual(identity["donor_commit"], "f7cb731c384ee6890a87d16c19a5b5a621779477")
        self.assertEqual(len(identity["files"]), 16)
        self.assertIn("numpy", identity["runtime_dependencies"])
        for relative in ("ops/build_a_share_close_review.py", "infrastructure/a_share_review_store.py", "contracts/market_calendar_2026.json"):
            self.assertIn(relative, identity["files"])
            self.assertEqual(len(identity["files"][relative]["sha256"]), 64)
        self.assertEqual(identity, sources.sources_identity())

    def test_loading_does_not_occupy_or_replace_bare_application_packages(self):
        sources = self.sources()
        bare = ("domains", "contracts", "infrastructure", "ops", "pyarrow", "pyarrow.dataset")
        before = {name: sys.modules.get(name) for name in bare}
        path_before, finders_before = list(sys.path), list(sys.meta_path)
        module = sources.load_frozen_module("ops.build_a_share_close_review")
        self.assertTrue(module.__name__.startswith("v5_shadow._m09_"))
        self.assertEqual(before, {name: sys.modules.get(name) for name in bare})
        self.assertEqual(path_before, sys.path)
        self.assertEqual(finders_before, sys.meta_path)

    def test_synthetic_namespace_packages_do_not_claim_missing_donor_initializers(self):
        sources = self.sources()
        for name in ("domains", "ops"):
            self.assertFalse(hasattr(sources.load_frozen_module(name), "__file__"))

    def test_calendar_uses_original_2026_contract_and_refuses_future_year(self):
        sources = self.sources()
        self.assertEqual(sources.market_states(T)["a_share"], "FULL_TRADING_DAY")
        self.assertEqual(sources.market_states("20261011")["a_share"], "NON_TRADING_DAY")
        self.assertEqual(sources.market_states("20271009")["a_share"], "UNKNOWN")

    def test_full_original_product_writer_and_independent_reader_keep_all_boundaries(self):
        sources = self.sources()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = self.build(sources, root)
            review = sources.read_original_review(root / "run", T)
            self.assertEqual(review, result["review"])
            self.assertIsNone(sources.read_original_review(root / "run", "20261008"))
            self.assertEqual(review["model_review"]["as_of"], "2026-10-09T15:30:00+08:00")
            self.assertEqual(review["core_stocks"], [])
            self.assertEqual(review["source_role"], "V3_5_NATIVE_CLOSE_MODEL")
            self.assertEqual(review["close_chain"]["status"], "PARTIAL_REVIEW")
            model = review["model_review"]
            self.assertEqual(model["target_video_review_status"], "CANNOT_CONFIRM_TARGET_VIDEO_NOT_CONSUMED")
            self.assertEqual(model["semantic_model_call_count"], 0)
            self.assertEqual({key: row["probability"] for key, row in model["scenario_tree"].items()}, {"stronger": 0.12, "inline": 0.28, "weaker": 0.60})
            self.assertEqual([row["direction"] for row in review["next_day_trigger_tree"]], ["stronger", "inline", "weaker"])
            self.assertEqual(sum(model["market_summary"][key] for key in ("up_count", "down_count", "flat_count")), 5)
            self.assertTrue(all(row["recommendation_status"] == "WATCH_ONLY" for row in review["observation_pool"]))
            for key in ("production_allowed", "buy_gate_updated", "orders_sent"):
                self.assertIs(review[key], False)

    def test_ready_context_does_not_claim_ui_acceptance_or_model_video_consumption(self):
        sources = self.sources()
        context = {
            "video_acceptance": {"trade_date": T, "today_bv_status": "TODAY_BV_LOCKED", "asr_status": "ASR_READY", "checks": {"same_day_video_count": 1}},
            "video_capture": {"trade_date": T, "status": "ASR_READY", "videos": [{}]},
            "stockdict_pointer": {"trade_date": T, "status": "CURRENT_ASR_STOCKDICT_READY_EXACT_ONLY"},
            "ocr_alignment_pointer": {"trade_date": T, "status": "VIDEO_TABLE_ASR_NEWS_ALIGNMENT_READY", "row_count": 1},
            "video_gap_pointer": {"trade_date": T, "status": "VIDEO_GAP_AUDIT_READY", "gap_row_count": 1},
        }
        with tempfile.TemporaryDirectory() as temporary:
            result = self.build(sources, Path(temporary), context=context)
            chain = result["review"]["close_chain"]
            self.assertEqual(chain["nodes"][8]["status"], "READY")
            self.assertEqual(chain["nodes"][9]["reason"], "UI_ACCEPTANCE_PENDING")
            self.assertEqual(chain["status"], "PARTIAL_REVIEW")
            self.assertFalse(result["review"]["model_review"]["video_augmented_review_complete"])

    def test_wrong_panel_sha_is_rejected_before_any_store_write(self):
        sources = self.sources()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaisesRegex(ValueError, "PANEL.*SHA|PANEL.*DIGEST"):
                self.build(sources, root, expected_panel_sha256="0" * 64)
            self.assertFalse((root / "run").exists())

    def test_cross_date_frame_is_rejected_before_silent_original_filter(self):
        sources = self.sources()
        frame = fixture_frame()
        frame.loc[0, "trade_date"] = "20261008"
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaisesRegex(ValueError, "FRAME|DATE"):
                self.build(sources, root, admitted_frame=frame)
            self.assertFalse((root / "run").exists())

    def test_unknown_context_argument_cannot_reach_producer(self):
        sources = self.sources()
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, "CONTEXT"):
                self.build(sources, Path(temporary), context={"ui_acceptance": True})

    def test_symlink_pointer_cannot_redirect_reads(self):
        sources = self.sources()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            panel, pointer, digest = self.stage(root)
            alternate = pointer.with_name("redirect.txt")
            alternate.symlink_to(pointer)
            with self.assertRaises((ValueError, OSError)):
                sources.build_from_admitted_panel(root / "run", T, alternate, fixture_frame(), digest, "m09-test", {})
            self.assertFalse((root / "run").exists())

    def test_capsule_mutation_cannot_bypass_verification_through_module_cache(self):
        sources = self.sources()
        sources.load_frozen_module("domains.a_share_close_model")
        with tempfile.TemporaryDirectory() as temporary:
            copied = Path(temporary) / "capsule"
            shutil.copytree(sources.CAPSULE, copied)
            target = copied / "domains/a_share_close_model.py"
            target.write_bytes(target.read_bytes() + b"\n# tampered\n")
            with patch.object(sources, "CAPSULE", copied):
                with self.assertRaisesRegex(ValueError, "SOURCE"):
                    sources.load_frozen_module("domains.a_share_close_model")

    def test_loader_source_change_requires_process_restart(self):
        sources = self.sources()
        sources.load_frozen_module("domains.a_share_close_model")
        with tempfile.TemporaryDirectory() as temporary:
            changed = Path(temporary) / "a_close_daily_sources.py"
            changed.write_bytes(Path(sources.__file__).read_bytes() + b"\n# changed live code\n")
            with patch.object(sources, "__file__", str(changed)):
                with self.assertRaisesRegex(ValueError, "SOURCE_LOADER_CHANGED"):
                    sources.load_frozen_module("domains.a_share_close_model")

    def test_original_reader_rejects_modified_payload(self):
        sources = self.sources()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = self.build(sources, root)
            path = root / "run" / result["publication"]["payload_path"]
            payload = json.loads(path.read_bytes())
            payload["headline"] = "changed"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "SHA"):
                sources.read_original_review(root / "run", T)

    def test_frozen_safe_root_rejects_symlink_destination(self):
        sources = self.sources()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            outside = root / "outside"
            outside.mkdir()
            owned = root / "owned"
            owned.mkdir()
            (owned / "escape").symlink_to(outside, target_is_directory=True)
            with self.assertRaises((ValueError, OSError)):
                sources.safe_root(owned).write_bytes("escape/payload.json", b"{}")
            self.assertEqual(list(outside.iterdir()), [])

    def test_entire_original_product_and_writer_match_separate_process_oracle(self):
        sources = self.sources()
        with tempfile.TemporaryDirectory() as temporary:
            try:
                report = _parity_report(sources, Path(temporary))
            except FileNotFoundError as error:
                self.skipTest(str(error))
            for key in ("review_equal", "publication_equal", "independent_reader_equal"):
                self.assertTrue(report[key], key)

    def test_parallel_admitted_frames_remain_bound_to_their_own_run(self):
        from concurrent.futures import ThreadPoolExecutor

        sources = self.sources()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            def produce(index):
                run = root / str(index)
                run.mkdir()
                frame = fixture_frame()
                frame.loc[0, "pct_chg"] = float(index + 10)
                result = self.build(sources, run, admitted_frame=frame, run_id="parallel-" + str(index))
                return result["review"]["model_review"]
            with ThreadPoolExecutor(max_workers=2) as executor:
                models = list(executor.map(produce, (0, 1)))
            self.assertEqual([model["run_id"] for model in models], ["parallel-0", "parallel-1"])
            self.assertEqual([model["anchor_role_rows"][0]["pct_change"] for model in models], [10.0, 11.0])

    def test_mutation_of_admitted_frame_during_original_model_fails(self):
        sources = self.sources()
        producer = sources.load_frozen_module("ops.build_a_share_close_review")
        original = producer.build_close_model
        frame = fixture_frame()
        def mutate(rows, date, run_id):
            result = original(rows, date, run_id)
            frame.loc[0, "pct_chg"] = 99.0
            return result
        with tempfile.TemporaryDirectory() as temporary, patch.object(producer, "build_close_model", mutate):
            with self.assertRaisesRegex(ValueError, "FRAME_MUTATED"):
                self.build(sources, Path(temporary), admitted_frame=frame)

    def test_same_size_raw_mutation_with_restored_mtime_is_still_rejected(self):
        sources = self.sources()
        producer = sources.load_frozen_module("ops.build_a_share_close_review")
        original = producer.build_close_model
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            panel, pointer, digest = self.stage(root)
            before = panel.stat()
            def mutate(rows, date, run_id):
                result = original(rows, date, run_id)
                raw = panel.read_bytes()
                panel.write_bytes(raw.replace(b"Alpha", b"Omega"))
                os.utime(panel, ns=(before.st_atime_ns, before.st_mtime_ns))
                return result
            with patch.object(producer, "build_close_model", mutate):
                with self.assertRaisesRegex(ValueError, "PANEL_SNAPSHOT_CHANGED"):
                    sources.build_from_admitted_panel(root / "run", T, pointer, fixture_frame(), digest, "m09-mutation", {})


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--original-producer-worker":
        _original_producer_worker()
    elif len(sys.argv) == 2 and sys.argv[1] == "--parity-report":
        from v5_shadow import a_close_daily_sources
        with tempfile.TemporaryDirectory() as temporary:
            print(json.dumps(_parity_report(a_close_daily_sources, Path(temporary)), ensure_ascii=False, indent=2, allow_nan=False))
    else:
        unittest.main()
