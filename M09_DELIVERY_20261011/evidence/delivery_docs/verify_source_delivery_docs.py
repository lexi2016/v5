"""Verify retained source evidence against its files without running candidate code."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

WORK = Path(__file__).absolute().parents[2]
OUT = Path(__file__).absolute().parent
AFTER = WORK / "after"
ORIGINAL = WORK / "original/source"
HANDOFF = WORK.parent / "m09_input/m09_handoff_20261011"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def resolve(path):
    candidate = Path(path)
    if candidate.is_absolute():
        assert candidate.is_file(), path
        return candidate
    choices = [root / path for root in (WORK, AFTER, ORIGINAL, HANDOFF)]
    present = [item for item in choices if item.is_file()]
    assert present, path
    return present[0]


checked = {}


def verify_refs(value):
    if isinstance(value, dict):
        if {"path", "sha256", "bytes"} <= value.keys():
            path = resolve(value["path"])
            raw = path.read_bytes()
            assert len(raw) == value["bytes"], path
            assert sha(raw) == value["sha256"], path
            checked[str(path.relative_to(WORK)) if path.is_relative_to(WORK) else str(path)] = sha(raw)
        for child in value.values():
            verify_refs(child)
    elif isinstance(value, list):
        for child in value:
            verify_refs(child)


def compare(left, right):
    assert type(left) is type(right)
    if isinstance(left, dict):
        assert set(left) == set(right)
        for key in left:
            compare(left[key], right[key])
    elif isinstance(left, list):
        assert len(left) == len(right)
        for a, b in zip(left, right):
            compare(a, b)
    else:
        assert left == right


source = read(OUT / "SOURCE_DEPENDENCIES.json")
parity = read(OUT / "ALGORITHM_PARITY.json")
matrix = read(OUT / "FAILURE_MATRIX.json")
for document in (source, parity, matrix):
    verify_refs(document)

for name, reference in source["exact_original_references"].items():
    assert resolve(reference["path"]).read_bytes() == (HANDOFF / (name + ".json")).read_bytes()
assert source["original_producer_static_count"] == 12
assert source["original_unresolved_internal_imports"] == []
assert source["candidate_internal_import_closure"]["unresolved_internal_imports"] == []
assert len(source["new_m09_capsule_mapping"]) == 16
for row in source["new_m09_capsule_mapping"]:
    original = (ORIGINAL / row["source_path"]).read_bytes()
    candidate = (AFTER / row["target_path"]).read_bytes()
    assert original == candidate
    assert sha(candidate) == row["sha256"]
    blob = hashlib.sha1(b"blob " + str(len(candidate)).encode() + b"\0" + candidate).hexdigest()
    assert blob == row["source_git_blob_sha1"] == row["candidate_blob_sha1"]

candidate_files = source["local_candidate"]["candidate_python_files"]
assert candidate_files == parity["candidate_python_files"]
for path, expected in candidate_files.items():
    assert sha((AFTER / path).read_bytes()) == expected, path

case_results = []
for case in parity["successful_cases"]:
    detail = read(resolve(case["detail"]["path"]))
    verify_refs(detail)
    assert detail["excluded_fields"] == []
    assert detail["normalization"] is None
    assert detail["differences"] == []
    assert detail["field_inventory_count"] == len(detail["field_inventory"])
    compare(detail["original_full_result"], detail["candidate_full_result"])
    compare(detail["original_independent_reader"], detail["candidate_independent_reader"])
    compare(detail["original_prepared_rows"], detail["candidate_prepared_rows"])
    groups = detail["obligation_groups"]
    assert groups["declared_input_codes_and_order"]["all_declared_rows_retained"] is True
    assert groups["breadth_conservation"]["sum_equals_admitted_rows"] is True
    assert groups["scenarios"]["probabilities_equal_frozen_constants"] is True
    assert groups["core_and_watch"]["no_core_promotion"] is True
    assert groups["research_and_safety"]["video_augmented_review_complete"] is False
    assert groups["close_chain"]["status"] == "PARTIAL_REVIEW"
    assert len(groups["close_chain"]["nodes"]) == 10
    assert groups["quality_provenance_refusals"]["source_role"] == "V3_5_NATIVE_CLOSE_MODEL"
    stores = detail["store_evidence_files"]
    assert set(stores["original"]) == set(stores["candidate"])
    for path in stores["original"]:
        assert resolve(stores["original"][path]["path"]).read_bytes() == resolve(stores["candidate"][path]["path"]).read_bytes()
    case_results.append({"case": case["case"], "full_exact_comparison": "PASS", "store_payload_receipt_manifest_raw_bytes_equal": True, "fields_compared": detail["field_inventory_count"]})

rejection = read(resolve(parity["original_exception_case"]["detail"]["path"]))
verify_refs(rejection)
assert rejection["same_original_and_candidate_exception"] is True
assert rejection["product_created"] is False

regression = matrix["final_regression"]
stderr = resolve(regression["stderr"]["path"]).read_text()
observed = {}
for line in stderr.splitlines():
    matched = re.match(r"(test_[^ ]+) \(([^)]+)\) \.\.\. (ok|skipped .*|FAIL|ERROR)$", line)
    if matched:
        method, identifier, status = matched.groups()
        assert identifier.rsplit(".", 1)[-1] == method
        observed[identifier] = status
suite_results = {}
for filename, suite in matrix["suite_inventory"].items():
    counts = {"discovered": 0, "passed": 0, "skipped": 0}
    for test in suite["tests"]:
        status = observed[test["id"]]
        assert (status.startswith("skipped ")) == test["conditional_skip"]
        counts["discovered"] += 1
        counts["skipped" if test["conditional_skip"] else "passed"] += 1
        if not test["conditional_skip"]:
            assert status == "ok"
    suite_results[filename] = counts
assert sum(item["discovered"] for item in suite_results.values()) == 125 == regression["discovered"]
assert sum(item["passed"] for item in suite_results.values()) == 121 == regression["passed"]
assert sum(item["skipped"] for item in suite_results.values()) == 4 == regression["skipped"]

result = {
    "schema_version": "v5.m09.source_delivery_evidence_validation.v1",
    "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    "status": "PASS",
    "operation": "Read-only revalidation of generated evidence, exact original files, candidate SHA snapshot and retained test output; no candidate execution or source mutation",
    "byte_exact_donor_files": 16,
    "original_static_closure_count": 12,
    "candidate_python_files_unchanged_count": len(candidate_files),
    "verified_reference_count": len(checked),
    "verified_references": checked,
    "full_parity_cases": case_results,
    "same_original_exception_and_no_product": True,
    "per_suite_observed_results": suite_results,
    "not_run_claims_preserved": matrix["not_run_layers"],
}
(OUT / "SOURCE_EVIDENCE_VALIDATION.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({key: value for key, value in result.items() if key != "verified_references"}, ensure_ascii=False, indent=2))
