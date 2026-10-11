"""Regenerate M09 source/parity evidence without changing candidate files."""
from __future__ import annotations

import ast
from datetime import datetime, timezone, timedelta
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import traceback

sys.dont_write_bytecode = True
WORK = Path(__file__).absolute().parents[2]
OUT = Path(__file__).absolute().parent
AFTER = WORK / "after"
ORIGINAL = WORK / "original/source"
DONOR = ORIGINAL / "handoff/v4-running-source-20261005/canonical"
HANDOFF = WORK.parent / "m09_input/m09_handoff_20261011"
F = "f7cb731c384ee6890a87d16c19a5b5a621779477"
H = "782bfc9ae91ff9cfe897afffc52aad43b7c1b78c"
T = "20261009"


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def relative(path):
    try:
        return str(path.relative_to(WORK))
    except ValueError:
        return str(path)


def ref(path, *, role=None):
    raw = path.read_bytes()
    result = {"path": relative(path), "sha256": digest(raw), "bytes": len(raw)}
    if role:
        result["role"] = role
    return result


def sources_snapshot():
    return {str(p.relative_to(AFTER)): digest(p.read_bytes()) for p in sorted((AFTER / "V5").rglob("*.py"))}


def exact_comparison(left, right, path="$"):
    """Compare complete JSON objects, scalar types and every list position."""
    inventory, differences = [], []
    if type(left) is not type(right):
        differences.append({"path": path, "kind": "TYPE", "original": type(left).__name__, "candidate": type(right).__name__})
        return inventory, differences
    if isinstance(left, dict):
        inventory.append({"path": path, "type": "object", "keys": sorted(left)})
        if set(left) != set(right):
            differences.append({"path": path, "kind": "KEY_SET", "original": sorted(left), "candidate": sorted(right)})
        for key in sorted(set(left) & set(right)):
            rows, changed = exact_comparison(left[key], right[key], path + "." + key)
            inventory.extend(rows); differences.extend(changed)
    elif isinstance(left, list):
        inventory.append({"path": path, "type": "array", "length": len(left), "order_compared": True})
        if len(left) != len(right):
            differences.append({"path": path, "kind": "LENGTH", "original": len(left), "candidate": len(right)})
        for index, (a, b) in enumerate(zip(left, right)):
            rows, changed = exact_comparison(a, b, f"{path}[{index}]")
            inventory.extend(rows); differences.extend(changed)
    else:
        inventory.append({"path": path, "type": type(left).__name__, "equal": left == right})
        if left != right:
            differences.append({"path": path, "kind": "VALUE", "original": left, "candidate": right})
    return inventory, differences


def run_logged(command, request, directory, stem):
    start = datetime.now(timezone.utc)
    result = subprocess.run(command, input=canonical(request), capture_output=True, cwd=WORK, timeout=60)
    end = datetime.now(timezone.utc)
    stdout, stderr = directory / (stem + ".stdout.json"), directory / (stem + ".stderr.txt")
    stdout.write_bytes(result.stdout); stderr.write_bytes(result.stderr)
    metadata = {
        "command": command, "cwd": str(WORK), "started_at_utc": start.isoformat(), "ended_at_utc": end.isoformat(),
        "started_at_shanghai": start.astimezone(timezone(timedelta(hours=8))).isoformat(),
        "ended_at_shanghai": end.astimezone(timezone(timedelta(hours=8))).isoformat(),
        "exit_code": result.returncode, "stdout": ref(stdout), "stderr": ref(stderr),
        "input_canonical_sha256": digest(canonical(request)),
    }
    execution = directory / (stem + ".execution.json")
    write_json(execution, metadata)
    return result, ref(execution)


def candidate_import_inventory():
    directory = AFTER / "V5/src/v5_shadow"
    sources = {"v5_shadow." + p.stem: p for p in directory.glob("*.py") if p.name != "__init__.py"}
    sources["v5_shadow"] = directory / "__init__.py"
    roots = ["v5_shadow." + name for name in ("a_close_daily", "a_close_daily_sources", "a_close_daily_worker", "a_close_daily_api", "a_close_review")]
    queue, seen, result, unresolved = list(roots), set(), [], []
    while queue:
        module = queue.pop()
        if module in seen:
            continue
        seen.add(module)
        path = sources.get(module)
        if path is None:
            unresolved.append(module); continue
        imports = []
        for node in ast.walk(ast.parse(path.read_bytes())):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    base = "v5_shadow" + ("." + node.module if node.module else "")
                else:
                    base = node.module or ""
                imports.append(base)
                if base == "v5_shadow":
                    imports.extend(base + "." + alias.name for alias in node.names if base + "." + alias.name in sources)
        internal = sorted({name for name in imports if name == "v5_shadow" or name.startswith("v5_shadow.")})
        queue.extend(internal)
        raw = path.read_bytes(); prior = ORIGINAL / path.relative_to(AFTER)
        result.append({"module": module, "candidate": ref(path), "imports": sorted(set(imports)), "internal_imports": internal,
                       "fixed_F_file_sha256": digest(prior.read_bytes()) if prior.is_file() else None,
                       "byte_equal_fixed_F": prior.read_bytes() == raw if prior.is_file() else None,
                       "origin": "EXISTING_FIXED_F_FILE" if prior.is_file() else "LOCAL_M09_CANDIDATE_NEW_FILE"})
    return {"entry_modules": roots, "method": "AST import closure plus explicit subprocess worker entry; dynamic donor imports enumerated separately", "modules": sorted(result, key=lambda row: row["module"]), "unresolved_internal_imports": sorted(set(unresolved))}


PREPARE_ORACLE = r'''
import hashlib,importlib.util,json,pathlib,sys
import pandas as pd
request=json.loads(sys.stdin.read())
path=pathlib.Path(request['model_path'])
assert hashlib.sha256(path.read_bytes()).hexdigest()==request['model_sha256']
spec=importlib.util.spec_from_file_location('_m09_original_model_evidence',path)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
frame=pd.DataFrame(request['rows'],columns=request['columns'])
prepared=module.prepare_close_rows(frame,request['trade_date'])
print(json.dumps({'columns':list(prepared.columns),'dtypes':[str(kind) for kind in prepared.dtypes],
                  'rows':prepared.to_dict('records'),'industry_metrics':module._sector_rows(prepared)},
                 ensure_ascii=False,sort_keys=True,allow_nan=False))
'''


def parity_case(sources, tests, identity, directory, name, context, *, expected_error=None):
    case = directory / name; case.mkdir(parents=True, exist_ok=False)
    frame = tests.fixture_frame(); rows = frame.to_dict("records")
    raw = json.dumps({"kind": "ENGINEERING_SYNTHETIC", "rows": rows}, sort_keys=True).encode()
    panel, pointer = case / "engineering_panel.json", case / "panel_pointer.txt"
    panel.write_bytes(raw); pointer.write_text(str(panel), encoding="utf-8")
    run_id = "m09-source-parity-" + name
    request = {
        "donor_root": str(DONOR), "source_files": {key: value["sha256"] for key, value in identity["files"].items()},
        "rows": rows, "trade_date": T, "panel_path": str(panel), "panel_pointer": str(pointer),
        "run_root": str(case / "original"), "run_id": run_id, "context": context,
    }
    request_file = case / "original_producer_request.json"; write_json(request_file, request)
    command = [sys.executable, "-I", "-B", str(AFTER / "V5/tests/test_a_close_daily_sources.py"), "--original-producer-worker"]
    original_process, execution = run_logged(command, request, case, "original_producer")
    candidate_error, candidate_result = None, None
    start = datetime.now(timezone.utc)
    try:
        candidate_result = sources.build_from_admitted_panel(case / "candidate", T, pointer, frame, digest(raw), run_id, context)
    except Exception as error:
        candidate_error = {"type": type(error).__name__, "message": str(error), "traceback": traceback.format_exc()}
    end = datetime.now(timezone.utc)
    write_json(case / "candidate_execution.json", {"call": "v5_shadow.a_close_daily_sources.build_from_admitted_panel", "started_at_utc": start.isoformat(), "ended_at_utc": end.isoformat(), "exception": candidate_error})
    inputs = {"trade_date": T, "run_id": run_id, "data_kind": "SYNTHETIC", "execution_kind": "ENGINEERING", "columns_in_order": list(frame.columns), "dtypes": [str(kind) for kind in frame.dtypes], "rows_in_order": rows, "ordered_codes": list(frame["ts_code"]), "row_count": len(frame), "context": context, "source_panel": ref(panel), "source_pointer": ref(pointer), "original_request": ref(request_file), "parquet_decoding": "NOT_RUN; these bytes are explicitly engineering JSON consumed through the admitted-frame I/O bridge"}
    write_json(case / "native_inputs.json", inputs)
    if expected_error is not None:
        original_last_line = original_process.stderr.decode(errors="replace").strip().splitlines()[-1] if original_process.stderr else ""
        expected_line = "ValueError: " + expected_error
        equal = original_process.returncode != 0 and original_last_line == expected_line and candidate_error is not None and candidate_error["type"] == "ValueError" and candidate_error["message"] == expected_error
        report = {"case": name, "classification": "SYNTHETIC_ORIGINAL_EXCEPTION_PARITY", "inputs": inputs, "expected_exception": {"type": "ValueError", "message": expected_error}, "same_original_and_candidate_exception": equal, "original_execution": execution, "original_trace": ref(case / "original_producer.stderr.txt"), "candidate_trace": candidate_error, "product_created": (case / "original/a_share_reviews").exists() or (case / "candidate/a_share_reviews").exists(), "field_normalization": None}
        write_json(case / "detail.json", report)
        if not equal:
            raise AssertionError("Original exception parity failed; preserved traces in " + str(case))
        return report, ref(case / "detail.json")
    if original_process.returncode or candidate_error:
        raise AssertionError("Original/candidate producer failed; preserved traces in " + str(case))
    original = json.loads(original_process.stdout)
    candidate_read = sources.read_original_review(case / "candidate", T)
    write_json(case / "candidate_result.json", candidate_result); write_json(case / "candidate_independent_read.json", candidate_read)
    original_prepare_request = {"model_path": str(DONOR / "domains/a_share_close_model.py"), "model_sha256": identity["files"]["domains/a_share_close_model.py"]["sha256"], "rows": rows, "columns": list(frame.columns), "trade_date": T}
    original_prepare, prepare_execution = run_logged([sys.executable, "-I", "-B", "-c", PREPARE_ORACLE], original_prepare_request, case, "original_prepared_rows")
    if original_prepare.returncode:
        raise AssertionError("Original prepare failed; preserved trace in " + str(case))
    original_prepared = json.loads(original_prepare.stdout)
    model_module = sources.load_frozen_module("domains.a_share_close_model")
    prepared = model_module.prepare_close_rows(frame.copy(deep=True), T)
    candidate_prepared = {"columns": list(prepared.columns), "dtypes": [str(kind) for kind in prepared.dtypes], "rows": prepared.to_dict("records"), "industry_metrics": model_module._sector_rows(prepared)}
    checks, field_inventory, differences = {}, [], []
    for label, left, right in (("full_producer_result", original["result"], candidate_result), ("independent_store_reader", original["independent_reader"], candidate_read), ("prepared_input_rows_and_all_industries", original_prepared, candidate_prepared)):
        fields, changes = exact_comparison(left, right, "$" + label)
        checks[label] = not changes; field_inventory.extend(fields); differences.extend(changes)
    review = candidate_result["review"]; model = review["model_review"]
    market = model["market_summary"]
    groups = {
        "declared_input_codes_and_order": {"input": inputs["ordered_codes"], "original_prepared": [row["ts_code"] for row in original_prepared["rows"]], "candidate_prepared": [row["ts_code"] for row in candidate_prepared["rows"]], "all_declared_rows_retained": inputs["ordered_codes"] == [row["ts_code"] for row in original_prepared["rows"]] == [row["ts_code"] for row in candidate_prepared["rows"]]},
        "breadth_conservation": {"up": market["up_count"], "down": market["down_count"], "flat": market["flat_count"], "admitted_rows": len(rows), "sum_equals_admitted_rows": sum(market[key] for key in ("up_count", "down_count", "flat_count")) == len(rows)},
        "industries": {"all_original_industry_metrics": original_prepared["industry_metrics"], "all_candidate_industry_metrics": candidate_prepared["industry_metrics"], "board_order": [row["board_name"] for row in model["board_rows"]], "full_board_rows": model["board_rows"]},
        "roles": {"rows_in_original_order": model["anchor_role_rows"], "numeric_score_field_status": "NOT_PRESENT_IN_FIXED_DONOR; absent on both sides, no score invented", "all_explanations_triggers_invalidations_evidence_refs_compared": True},
        "scenarios": {"by_direction": model["scenario_tree"], "frozen_probabilities": {"stronger": .12, "inline": .28, "weaker": .60}, "probabilities_equal_frozen_constants": {key: value["probability"] for key, value in model["scenario_tree"].items()} == {"stronger": .12, "inline": .28, "weaker": .60}, "review_trigger_order": [row["direction"] for row in review["next_day_trigger_tree"]], "calibration_claim": False},
        "regime_and_risk": {"market_regime": review["market_regime"], "risk_tone": review["risk_tone"], "model_regime": market["regime"]},
        "core_and_watch": {"core_stocks": review["core_stocks"], "observation_pool": review["observation_pool"], "shadow_watch_pool": model["shadow_watch_pool"], "no_core_promotion": review["core_stocks"] == [] and model["shadow_watch_pool"]["core"] == []},
        "quality_provenance_refusals": {"quality_gate": review["quality_gate"], "source_role": review["source_role"], "source_sha256": review["source_sha256"], "source_evidence": review["source_evidence"], "cannot_confirm": review["cannot_confirm"], "previous_plan_realization": model["previous_plan_realization"], "target_video_review_status": model["target_video_review_status"], "legacy_as_of": model["as_of"]},
        "research_and_safety": {"model_safety": model["safety"], "review_safety": {key: review[key] for key in ("production_allowed", "buy_gate_updated", "orders_sent")}, "semantic_model_status": model["semantic_model_status"], "semantic_model_call_count": model["semantic_model_call_count"], "learning_status": model["learning_status"], "formal_generalization": model["formal_generalization"], "model_promotion": model["model_promotion"], "video_augmented_review_complete": model["video_augmented_review_complete"]},
        "close_chain": review["close_chain"],
    }
    store_files = {}
    for side in ("original", "candidate"):
        store_files[side] = {name: ref(case / side / name) for name in (f"a_share_reviews/{T}.json", f"a_share_reviews/receipts/{T}.json", "a_share_reviews/manifest.json")}
    report = {"case": name, "classification": "SYNTHETIC_FULL_ORIGINAL_PRODUCER_STORE_READER_PARITY", "inputs": inputs, "original_execution": execution, "original_prepared_execution": prepare_execution, "original_code_commit": F, "source_identity": identity, "comparison_rule": "Exact JSON scalar types and values; complete object key sets; all array lengths and positions. JSON object insertion order is not semantic. No excluded fields or value normalization.", "excluded_fields": [], "normalization": None, "run_id_mapping": "IDENTICAL_RUN_ID_ON_BOTH_SIDES", "checks": checks, "field_inventory": field_inventory, "field_inventory_count": len(field_inventory), "differences": differences, "obligation_groups": groups, "original_full_result": original["result"], "candidate_full_result": candidate_result, "original_independent_reader": original["independent_reader"], "candidate_independent_reader": candidate_read, "original_prepared_rows": original_prepared, "candidate_prepared_rows": candidate_prepared, "store_evidence_files": store_files}
    write_json(case / "detail.json", report)
    if differences or not groups["breadth_conservation"]["sum_equals_admitted_rows"] or not groups["declared_input_codes_and_order"]["all_declared_rows_retained"]:
        raise AssertionError("Full algorithm parity failed; complete differences retained in " + str(case))
    return report, ref(case / "detail.json")


def test_inventory():
    result = {}
    for filename in ("test_a_close_daily.py", "test_a_close_daily_api.py", "test_a_close_daily_sources.py", "test_a_close_review.py", "test_daily_close_plan.py"):
        path = AFTER / "V5/tests" / filename; tree = ast.parse(path.read_bytes())
        tests = []
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                conditional = any(isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute) and dec.func.attr in ("skipUnless", "skipIf") for dec in node.decorator_list)
                for child in node.body:
                    if isinstance(child, ast.FunctionDef) and child.name.startswith("test_"):
                        tests.append({"id": filename[:-3] + "." + node.name + "." + child.name, "name": child.name, "class": node.name, "conditional_skip": conditional})
        result[filename] = {"source": ref(path), "test_count": len(tests), "tests": tests}
    return result


def regression_evidence():
    for filename in ("final_candidate_regression.json", "final_fixed_candidate_unittest.json", "shared_helper_guard_full_candidate.json"):
        path = WORK / "evidence/logs" / filename
        if not path.is_file():
            continue
        data = json.loads(path.read_bytes()); stderr = path.parent / data["stderr"]["path"]
        raw = stderr.read_bytes()
        if digest(raw) != data["stderr"]["sha256"]:
            raise ValueError("Regression evidence SHA mismatch")
        text = raw.decode(); count = re.search(r"\nRan (\d+) tests in ([0-9.]+)s", text)
        if count and data["exit_code"] == 0:
            skipped = re.search(r"OK \(skipped=(\d+)\)", text)
            skip_count = int(skipped.group(1)) if skipped else 0
            names = [line.strip() for line in text.splitlines() if " ... skipped " in line]
            return {"status": "COMMAND_COMPLETED", "metadata": ref(path), "stderr": ref(stderr), "command": data["command"], "cwd": data["cwd"], "exit_code": 0, "discovered": int(count.group(1)), "passed": int(count.group(1)) - skip_count, "skipped": skip_count, "failed": 0, "errors": 0, "skipped_details": names, "started_at_utc": data.get("start_utc"), "ended_at_utc": data.get("end_utc")}
    return {"status": "NOT_RUN_CURRENT_FINAL_REGRESSION_NOT_AVAILABLE"}


def build_matrix(inventory, regression):
    mapping = [
        ("DATE_CALENDAR_TIMEZONE", "T is an actual A trading day; correct Shanghai day, exact row date/type and only two slots", ["test_nontrading_or_invalid_date_and_third_slot_rejected", "test_wrong_date_type_or_day_rejected", "test_natural_trigger_cannot_claim_historical_day", "test_calendar_uses_original_2026_contract_and_refuses_future_year", "test_utc_day_not_used_as_target_day", "test_naive_time_rejected"], "Live scheduler/business calendar acceptance is NOT_RUN; frozen 2026 contract and engineering clock checks exercised."),
        ("EIGHT_COLUMNS_NUMERIC_QUALITY", "Every required column, finite numeric types, no silent fill/drop, amount and close-position bounds, required industry/name", ["test_missing_each_of_eight_required_columns_is_rejected", "test_missing_field_rejected_before_algorithm", "test_bad_numeric_types_and_quality_are_not_normalized", "test_nonfinite_numeric_rejected", "test_missing_industry_not_filled", "test_invalid_price_change_not_dropped"], "Real parquet schema/decode tests are separately SKIPPED in this environment."),
        ("MEMBERSHIP_SCOPE", "Unique valid A codes and complete declared membership; a Top subset cannot claim full market", ["test_duplicate_and_invalid_suffix_rejected", "test_missing_declared_members_rejected", "test_top_subset_cannot_claim_full_market", "test_duplicate_code_rejected", "test_cross_date_frame_is_rejected_before_silent_original_filter"], "Synthetic membership does not establish real full-market authority."),
        ("POINTER_RAW_SHA_ROOT", "Pointer containment, symlinks, manifest/panel SHA and changes during calculation fail closed", ["test_pointer_traversal_and_symlink_fail_closed", "test_panel_digest_and_manifest_digest_checked", "test_source_changed_during_compute_never_publishes", "test_same_size_raw_mutation_with_restored_mtime_is_still_rejected", "test_wrong_panel_sha_is_rejected_before_any_store_write", "test_symlink_pointer_cannot_redirect_reads", "test_unmarked_and_source_overlapping_roots_are_rejected", "test_worker_rejects_unbound_external_product_root"], "No V4 root was written; engineering path boundaries do not certify a live Mac deployment root."),
        ("SOURCE_TIME_AND_AUTHORITY", "Unknown/unverified sources remain unconfirmed; source receipt and capture/available/cutoff consistency", ["test_unverified_or_unknown_source_is_not_promoted", "test_source_receipt_time_disagreement_rejected", "test_late_or_naive_source_time_rejected", "test_research_request_cannot_claim_a_future_slot", "test_unknown_source_times_remain_unknown_and_legacy_as_of_is_preserved"], "Historical source available_at/PIT remain unknown; real natural admission NOT_RUN."),
        ("TWO_SLOT_IDENTITIES", "Same admitted inputs reuse a calculation but produce distinct 16:05/17:10 receipts; changed configuration/material causes new run", ["test_two_slots_reuse_one_calculation_and_keep_two_receipts", "test_configuration_change_creates_a_new_immutable_run", "test_late_stage_reference_only_enters_second_slot", "test_a_slots_are_separate", "test_second_slot_is_not_automatically_successful"], "Actual scheduler slot receipts and continuous natural days NOT_RUN."),
        ("IDEMPOTENCY_CONCURRENCY", "Same attempt is side-effect-free; concurrent attempts share the calculation while keeping independent receipts", ["test_exact_same_attempt_returns_receipt_without_producing", "test_two_concurrent_attempts_share_one_calculation", "test_parallel_admitted_frames_remain_bound_to_their_own_run"], "Local engineering concurrency only; no live distributed/network filesystem claim."),
        ("LATER_FAILURE_TIMEOUT", "A failed/timeout later attempt keeps the previous success visible", ["test_later_failure_keeps_previous_success", "test_real_worker_timeout_keeps_old_generation", "test_latest_failed_attempt_is_separate_from_served_success", "test_latest_failed_or_unknown_attempt_is_separate_from_served_success"], "Timeout test uses an actual isolated process; it is an engineering fault, not a natural missed slot."),
        ("WRITER_READBACK_CAS", "Payload/receipt/manifest interruption, readback mismatch and CAS conflict never replace an existing served success", ["test_each_original_store_write_interruption_preserves_success", "test_original_writer_failure_does_not_replace_old_run", "test_independent_readback_mismatch_keeps_old_generation", "test_cas_conflict_keeps_served_generation", "test_original_reader_rejects_modified_payload", "test_tampered_payload_is_rejected_by_independent_reader"], "Faults are deliberately injected against private engineering stores."),
        ("HEAD_AND_RECEIPT_CRASH", "Failed head activation, final receipt failure and hard process exit do not serve unreceipted runs", ["test_error_after_head_replace_restores_previous_generation", "test_final_receipt_write_failure_preserves_previous_success", "test_hard_exit_after_head_never_serves_unreceipted_run", "test_publication_recovery_stays_separate_from_served_generation_identity"], "Actual Mac power loss/sleep filesystem behavior NOT_RUN."),
        ("PARTIAL_STAGE_VIDEO_CHAIN", "M07/M12 gaps remain visible; after-17:10 material is not backfilled; metadata readiness never implies model video consumption", ["test_available_unknown_evidence_remains_partial", "test_post_1710_video_is_not_even_read_for_either_old_slot", "test_ready_context_does_not_claim_ui_acceptance_or_model_video_consumption", "test_missing_incomplete_or_unsafe_native_chain_is_not_verified", "test_price_chain_writer_reader_preserves_native_fields"], "No M12 collection/rebuild or real video semantic consumption was performed."),
        ("ALGORITHM_PARITY_RESEARCH", "Complete original algorithms, field/order parity, constant probabilities, no core promotion, disabled LLM and research gates", ["test_entire_original_product_and_writer_match_separate_process_oracle", "test_full_original_product_writer_and_independent_reader_keep_all_boundaries", "test_preserves_native_algorithm_and_date_fields", "test_native_model_status_and_research_limits_are_enforced", "test_original_summary_and_explicit_boundaries"], "Fresh full parity detail is SYNTHETIC and uses admitted-frame I/O; raw parquet decoder parity NOT_RUN."),
        ("CODE_DEPENDENCY_IDENTITY", "All donor bytes and manifest are pinned; altered cached capsule or changed loader is rejected", ["test_identity_covers_original_producer_store_calendar_and_dynamic_json", "test_capsule_mutation_cannot_bypass_verification_through_module_cache", "test_loader_source_change_requires_process_restart", "test_loading_does_not_occupy_or_replace_bare_application_packages", "test_synthetic_namespace_packages_do_not_claim_missing_donor_initializers"], "Independent helper-identity regressions are additional evidence outside the 125 discovered tests."),
        ("DIGEST_DATE_RUN_CHAIN", "Source, raw review, canonical review, record, generation and run/date links retain their distinct meanings", ["test_metadata_names_distinct_digest_layers_and_computation_classification", "test_raw_review_identity_is_bound_to_the_recorded_original_file", "test_original_store_metadata_requires_exact_paths_hashes_and_sizes", "test_changed_review_record_or_generation_is_not_served", "test_resealed_cross_date_evidence_is_not_served", "test_resealed_model_date_and_run_mismatches_are_not_served", "test_resealed_source_mismatch_is_not_served"], "These are committed-reader and projection proofs; active ordinary HTTP routing NOT_RUN."),
        ("READ_ONLY_EXACT_DATE", "Reads never compute/collect, do not change files, and do not substitute another date or fabricate values", ["test_read_is_exact_date_and_has_no_file_side_effects", "test_single_pinned_reader_result_is_consumed_without_writes", "test_missing_result_has_exact_date_empty_arrays_and_no_fake_counts", "test_invalid_request_never_calls_generation_reader", "test_actual_generation_connects_to_pure_existing_page_projection"], "Browser refresh/back/date-switch click behavior and active ordinary endpoint NOT_RUN."),
        ("A_HK_ISOLATION", "Pure A projection/merge keeps HK and unrelated envelope values intact", ["test_merge_preserves_hk_and_every_unrelated_top_key_exactly", "test_merge_updates_a_legacy_aliases_and_removes_only_proven_a_attribution", "test_merge_missing_a_keeps_hk_and_never_reuses_old_a", "test_merge_refuses_cross_date_or_unsafe_preview"], "Live A/H shared URL upgrade/rollback, HK response and V4 service checks NOT_RUN."),
        ("ROLLBACK_AND_RESTART", "Local rollback preserves old/new runs and restores the previous head; interrupted attempts remain unknown until new recovery", ["test_rollback_preserves_both_runs_and_switches_only_this_date", "test_rollback_activation_exception_restores_previous_head", "test_restarted_unfinished_attempt_is_unknown_and_new_attempt_can_recover", "test_first_failed_attempt_remains_visible_without_fabricating_product", "test_first_failed_attempt_remains_visible_without_a_committed_generation"], "Mac sleep/restart/deployment rollback NOT_RUN."),
        ("REPLAY_IS_NOT_NATURAL", "Synthetic JSON or historical replay cannot claim real natural success; old replay and schedule guardrails remain", ["test_synthetic_json_cannot_be_presented_as_real", "test_real_source_data_may_be_read_as_historical_replay_without_becoming_natural", "test_plan_is_not_a_success_receipt", "test_actual_capture_distinct_from_frozen_label", "test_job_identity_stable_across_ticks", "test_next_day_has_different_identity"], "Retained V5 replay/schedule tests are 23 PASS; original donor pytest suites are separately BLOCKED."),
    ]
    lookup = {test["name"]: test for group in inventory.values() for test in group["tests"]}
    rows = []
    for identifier, obligation, names, limit in mapping:
        missing = [name for name in names if name not in lookup]
        if missing:
            raise ValueError("Missing matrix tests: " + str(missing))
        rows.append({"id": identifier, "obligation": obligation, "engineering_tests": [lookup[name]["id"] for name in names], "status": "PASS_ENGINEERING" if regression.get("passed") == 121 else "AWAITING_FINAL_REGRESSION", "limit": limit})
    skipped = [test["id"] for group in inventory.values() for test in group["tests"] if test["conditional_skip"]]
    return {"schema_version": "v5.m09.failure_matrix.v1", "method": "Exact existing unittest method names mapped to contract obligations; observed regression outcomes kept separate from test source inventory", "final_regression": regression, "suite_inventory": inventory, "count_breakdown": {"daily": {"pass_expected": 47, "conditional_real_parquet_skipped": len(skipped)}, "api": {"pass_expected": 33}, "sources": {"pass_expected": 18}, "unchanged_original_v5_replay_and_schedule": {"pass_expected": 23, "replay": 9, "schedule": 14}, "all": {"passed_observed": regression.get("passed"), "skipped_observed": regression.get("skipped"), "discovered_observed": regression.get("discovered")}}, "matrix": rows, "conditional_real_parquet_tests": {"status": "SKIPPED_PYARROW_ABSENT", "tests": skipped, "purpose": "Real parquet I/O on ENGINEERING/SYNTHETIC rows when an already-approved pyarrow environment exists; not market/natural acceptance"}, "not_run_layers": [{"layer": "Original donor pytest suites", "status": "BLOCKED_ENVIRONMENT_PYTEST_NOT_INSTALLED", "evidence": ref(WORK / "evidence/project_pytest_availability.json")}, {"layer": "Real historical full parquet/model parity", "status": "NOT_RUN_PYARROW_ABSENT_AND_REAL_SOURCE_QUALITY_TIME_GAPS"}, {"layer": "Mac runtime and filesystem acceptance", "status": "NOT_RUN_NO_MAC_EXECUTION"}, {"layer": "Active ordinary HTTP API and original ReviewView browser consumption", "status": "NOT_RUN_INTEGRATION_NOT_ACTIVATED"}, {"layer": "Live A/H isolation and module rollback", "status": "NOT_RUN_NO_ACTIVE_DEPLOYMENT"}, {"layer": "Natural two-slot execution and two consecutive eligible trading days", "status": "NOT_RUN_NO_NATURAL_RECEIPTS"}]}


def main():
    before = sources_snapshot()
    sys.path.insert(0, str(AFTER / "V5/src"))
    from v5_shadow import a_close_daily_sources as sources
    test_path = AFTER / "V5/tests/test_a_close_daily_sources.py"
    spec = importlib.util.spec_from_file_location("_m09_delivery_parity_tests", test_path)
    tests = importlib.util.module_from_spec(spec); spec.loader.exec_module(tests)
    identity = sources.sources_identity()
    original_dependencies = json.loads((HANDOFF / "DEPENDENCY_MANIFEST.json").read_bytes())
    original_manifest = json.loads((HANDOFF / "ORIGINAL_SOURCE_MANIFEST.json").read_bytes())
    manifest = json.loads(sources.DESCRIPTOR.read_bytes())
    refs = OUT / "source_references"; refs.mkdir(exist_ok=True)
    for name in ("DEPENDENCY_MANIFEST.json", "ORIGINAL_SOURCE_MANIFEST.json"):
        shutil.copyfile(HANDOFF / name, refs / name)
    generated = datetime.now(timezone.utc)
    label = "parity_" + generated.strftime("%Y%m%dT%H%M%S%fZ")
    directory = OUT / label; directory.mkdir()
    ready_context = {
        "video_acceptance": {"trade_date": T, "today_bv_status": "TODAY_BV_LOCKED", "status": "VIDEO_METADATA_READY", "asr_status": "ASR_READY", "checks": {"same_day_video_count": 1}},
        "video_capture": {"trade_date": T, "status": "ASR_READY", "videos": [{"fixture": "SYNTHETIC"}]},
        "stockdict_pointer": {"trade_date": T, "status": "CURRENT_ASR_STOCKDICT_READY_EXACT_ONLY"},
        "ocr_alignment_pointer": {"trade_date": T, "status": "VIDEO_TABLE_ASR_NEWS_ALIGNMENT_READY", "row_count": 1},
        "video_gap_pointer": {"trade_date": T, "status": "VIDEO_GAP_AUDIT_READY", "gap_row_count": 1},
    }
    cases = []
    for name, context in (("missing_context", {}), ("ready_context_model_not_consumed", ready_context)):
        report, evidence = parity_case(sources, tests, identity, directory, name, context)
        cases.append({"case": name, "status": "PASS", "detail": evidence, "checks": report["checks"], "field_inventory_count": report["field_inventory_count"], "differences": report["differences"], "breadth_conservation": report["obligation_groups"]["breadth_conservation"], "close_chain_status": report["obligation_groups"]["close_chain"]["status"], "model_video_consumption": False})
    rejection, rejection_ref = parity_case(sources, tests, identity, directory, "cross_date_video_original_exception", {"video_acceptance": {"trade_date": "20261008", "checks": {}}}, expected_error="video acceptance date does not match close-review date")
    after = sources_snapshot()
    if before != after:
        raise ValueError("Candidate Python files changed during evidence generation; preserve this run and regenerate after freeze")
    by_original_path = {item["path"]: item for item in original_manifest["files"]}
    source_entries = []
    for entry in manifest["entries"]:
        original_entry = by_original_path[entry["source_path"]]
        original_raw = (ORIGINAL / entry["source_path"]).read_bytes()
        candidate_raw = (AFTER / entry["target_path"]).read_bytes()
        if original_raw != candidate_raw or digest(candidate_raw) != entry["sha256"]:
            raise ValueError("Donor-copy mismatch")
        source_entries.append({**entry, "fixed_F_manifest_entry": original_entry, "byte_exact_copy_verified": True, "candidate_blob_sha1": hashlib.sha1(b"blob " + str(len(candidate_raw)).encode() + b"\0" + candidate_raw).hexdigest()})
    candidate_inventory = candidate_import_inventory()
    dependency_report = {
        "schema_version": "v5.m09.source_dependencies.delivery.v1", "generated_at_utc": generated.isoformat(),
        "fixed_donor": {"repository": "lexi2016/v4", "commit": F, "role": "Immutable historical algorithm source; never a candidate destination"},
        "published_handoff": {"repository": "lexi2016/v5", "branch": "v5/m09-handoff-20261011", "commit": H, "role": "Parent-verified published handoff identity; distinct from new local candidate"},
        "local_candidate": {"commit": None, "commit_status": "FINAL_PACKAGING_OWNER_BINDS_CANDIDATE_COMMIT; THIS_REPORT_IDENTIFIES_EXACT_LOCAL_BYTES", "candidate_python_files": after},
        "exact_original_references": {"DEPENDENCY_MANIFEST": ref(refs / "DEPENDENCY_MANIFEST.json", role="BYTE_EXACT_ORIGINAL_ATTACHMENT_MEMBER"), "ORIGINAL_SOURCE_MANIFEST": ref(refs / "ORIGINAL_SOURCE_MANIFEST.json", role="BYTE_EXACT_ORIGINAL_ATTACHMENT_MEMBER")},
        "original_producer_static_closure": original_dependencies["producer_static_internal_import_closure"],
        "original_producer_static_count": original_dependencies["producer_static_internal_import_count"], "original_unresolved_internal_imports": original_dependencies["producer_unresolved_internal_imports"],
        "new_m09_capsule_manifest": ref(sources.DESCRIPTOR), "new_m09_capsule_mapping": source_entries,
        "candidate_internal_import_closure": candidate_inventory, "dynamic_reads": manifest["dynamic_reads"],
        "external_imports_original_producer": original_dependencies["producer_external_imports"], "declared_environment": manifest["external_dependencies"], "actual_source_execution_identity": identity,
        "prior_verified_dependency_report": ref(WORK / "evidence/sources_dependency_report.json"),
        "project_declaration": ref(AFTER / "V5/pyproject.toml"), "attached_reference_locks": [ref(path, role="MAC_REFERENCE_LOCK_NOT_CLOUD_ENVIRONMENT_LOCK") for path in sorted((WORK / "runtime_inputs").rglob("uv.lock"))],
        "scope_limits_from_original_inventory": original_dependencies["limits"], "reference_only_missing_from_original_inventory": original_dependencies["known_reference_only_missing"],
        "scope_limit_update": "Original static inventory is preserved verbatim. R2/R3 supplied active API/UI reference pieces, but active Mac/API/UI integration remains unexecuted here. Missing reference-only video/orchestration modules are not dependencies of the 12-module original producer closure.",
        "evidence_status": {"static_presence_and_byte_mapping": "VERIFIED", "private_donor_imports": "EXERCISED", "full_producer_original_store_independent_reader": "EXERCISED_WITH_ADMITTED_FRAME_IO", "real_parquet_decode": "NOT_RUN_PYARROW_ABSENT", "original_donor_pytest_suites": "BLOCKED_PYTEST_ABSENT", "declared_environment_acceptance": "NOT_SATISFIED_PYTHON_3_12_PANDAS_2_2_AND_NO_PYARROW", "mac_runtime": "NOT_RUN"},
        "io_adaptation": {"algorithm_bytes_changed": False, "description": "Only original producer pyarrow.dataset binding is replaced privately by a checked admitted-frame capability. Default real daily admission must decode actual parquet using real installed pyarrow before this call.", "global_bare_modules_installed": False, "loader_sys_path_mutation": False, "worker_bootstrap": "Separate isolated subprocess adds its own candidate V5/src path to import its private entry; this is distinct from the namespaced donor loader."},
    }
    write_json(OUT / "SOURCE_DEPENDENCIES.json", dependency_report)
    parity = {"schema_version": "v5.m09.algorithm_parity.delivery.v1", "generated_at_utc": generated.isoformat(), "status": "PASS_SYNTHETIC_ADMITTED_FRAME_FULL_CHAIN", "fixed_donor_commit": F, "original_model_sha256": identity["files"]["domains/a_share_close_model.py"]["sha256"], "original_producer_sha256": identity["files"]["ops/build_a_share_close_review.py"]["sha256"], "candidate_source_loader_sha256": identity["loader_sha256"], "candidate_donor_capsule_descriptor_sha256": identity["descriptor_sha256"], "candidate_python_files": after, "comparison": {"field_exclusions": [], "normalization": None, "scalar_types": "EXACT", "scalar_values": "EXACT", "objects": "COMPLETE_KEY_SETS_AND_VALUES; JSON object insertion order is not semantic", "lists": "ALL_LENGTHS_AND_POSITIONS_EXACT", "run_id": "IDENTICAL_ON_BOTH_SIDES; NO_METADATA_EXCLUSION"}, "successful_cases": cases, "original_exception_case": {"status": "PASS", "detail": rejection_ref, "same_exception_type_and_message": rejection["same_original_and_candidate_exception"], "original_trace_retained": True, "candidate_trace_retained": True, "product_created": rejection["product_created"]}, "full_field_scope": ["all same-day declared stock codes and row order before/after original preparation", "up/down/flat conservation equals admitted input count", "all industry metrics plus selected board order/ranks", "role membership/order/amounts/pct/explanations/evidence/triggers/invalidation; original has no numeric score field", "scenario 0.12/0.28/0.60 fixed constants and all trigger/invalidation text", "market_regime/risk_tone", "empty core_stocks and model core pool; observation/conditional/risk rows never promoted", "quality_gate/source_role/source_evidence/source_sha256", "all cannot_confirm/refusal/unknown/PIT/learning/generalization/video/LLM safety fields", "all close_chain tasks/order/status/reasons/evidence", "original writer publication and complete independent reader payloads"], "probabilities_calibrated": False, "video_semantically_consumed": False, "legacy_model_as_of": "2026-10-09T15:30:00+08:00; preserved original model label, not actual availability or strict PIT proof", "prior_matching_parity_artifact": ref(WORK / "evidence/sources_full_parity.stdout.json"), "qualified_limits": {"input_kind": "SYNTHETIC_ENGINEERING_ONLY", "raw_parquet_decode_and_decoder_parity": "NOT_RUN_PYARROW_ABSENT", "real_historical_original_model_exception_or_product": "NOT_RUN; no cleaning or substitute rows were used", "declared_python_pandas_pyarrow_environment": "NOT_SATISFIED", "full_natural_or_active_UI_acceptance": "NOT_RUN", "coverage": "Two complete valid-input product cases and one original rejection case; no claim of exhaustive behavior over all possible market inputs"}}
    write_json(OUT / "ALGORITHM_PARITY.json", parity)
    inventory = test_inventory(); regression = regression_evidence(); matrix = build_matrix(inventory, regression)
    write_json(OUT / "FAILURE_MATRIX.json", matrix)
    lines = ["# M09 contract failure matrix", "", f"Observed final regression: {regression.get('discovered')} discovered, {regression.get('passed')} PASS, {regression.get('skipped')} SKIPPED. Skips and NOT_RUN layers are not counted as PASS.", "", "| Contract obligation | Existing engineering evidence | Remaining qualification |", "|---|---|---|"]
    for row in matrix["matrix"]:
        names = "; ".join("`" + name.rsplit(".", 1)[-1] + "`" for name in row["engineering_tests"])
        lines.append("| " + row["id"] + " | " + names + " | " + row["limit"] + " |")
    lines.extend(["", "## Four conditional parquet tests", "", "These are SKIPPED because pyarrow is absent. They use engineering data and do not establish real market or natural-run acceptance.", ""])
    lines.extend("- `" + name + "`" for name in matrix["conditional_real_parquet_tests"]["tests"])
    lines.extend(["", "## Unexecuted acceptance layers", ""])
    lines.extend("- " + row["layer"] + ": **" + row["status"] + "**." for row in matrix["not_run_layers"])
    (OUT / "FAILURE_MATRIX.md").write_text("\n".join(lines) + "\n")
    print(json.dumps({"status": "DELIVERY_EVIDENCE_WRITTEN", "source_dependencies": ref(OUT / "SOURCE_DEPENDENCIES.json"), "algorithm_parity": ref(OUT / "ALGORITHM_PARITY.json"), "failure_matrix": ref(OUT / "FAILURE_MATRIX.json"), "fresh_parity_directory": relative(directory), "successful_full_cases": 2, "original_exception_cases": 1, "regression": regression}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
