"""Independent M01 R6 engineering boundary reproductions, synthetic data only."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
import traceback
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq


TASK_ROOT = Path(sys.argv[1]).resolve()
ACCEPTANCE = TASK_ROOT / "m01-r6-github-20261011" / "acceptance"
REPO = ACCEPTANCE / "isolated_repo"
FIXED = ACCEPTANCE / "fixed_original"
OUTPUT = ACCEPTANCE / "rawlogs" / "boundary_results.json"
DATE = "20261010"
RELATIVE = f"m01/a_source/{DATE}"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


safeio = load_module("m01_fixed_owned_io", FIXED / "infrastructure" / "owned_io.py")
reader_module = load_module("m01_fixed_formula_generation", FIXED / "infrastructure" / "formula_generation.py")
candidate_root = REPO / "V5" / "src"
sys.path.insert(0, str(candidate_root))
from v5_shadow import a_source_daily as candidate


SafeRoot = safeio.SafeRoot
read_formula_generation = reader_module.read_formula_generation
CASES: list[dict] = []


def record(case: str, status: str, evidence: dict | str):
    CASES.append({"case": case, "status": status, "evidence": evidence})
    print(f"{status} {case}: {json.dumps(evidence, sort_keys=True, default=str)}")


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical_bytes(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def detail(root: Path, name: str) -> dict:
    path = root / name
    raw = path.read_bytes()
    return {"path": name, "bytes": len(raw), "sha256": sha(raw)}


def write_parquet(path: Path):
    table = pa.table({"trade_date": [DATE], "synthetic_value": [1]})
    pq.write_table(table, path)


def make_generation(root: Path, identity: str) -> Path:
    """Build a reader-valid strict generation with one synthetic date row."""
    root.mkdir(parents=True, exist_ok=True)
    for name in ("selector.parquet", "backtest.parquet", "selector-source.parquet", "selector-sidecar.parquet"):
        write_parquet(root / name)

    source_raw = f"synthetic-source:{identity}".encode()
    source_sha = sha(source_raw)
    manifest_basis = {"target_date": DATE, "source_sha256": source_sha, "fixture": identity}
    manifest_sha = sha(canonical_bytes(manifest_basis))
    manifest_raw = canonical_bytes({**manifest_basis, "manifest_sha256": manifest_sha})
    (root / "input-manifest.json").write_bytes(manifest_raw)

    receipt_raw = canonical_bytes({
        "status": "READY",
        "target_date": DATE,
        "fixture_identity": identity,
        "production_allowed": False,
        "buy_gate_updated": False,
        "orders_sent": False,
    })
    (root / "sync-receipt.json").write_bytes(receipt_raw)

    selector_detail = detail(root, "selector.parquet")
    backtest_detail = detail(root, "backtest.parquet")
    identity_pair = {"selector": selector_detail, "backtest": backtest_detail}
    generation_id = sha(canonical_bytes(identity_pair))
    payload = {
        "schema": reader_module.FORMULA_GENERATION_SCHEMA,
        "status": "READY",
        "generation_id": generation_id,
        "target_date": DATE,
        "run_id": f"synthetic-run-{identity}",
        "selector": selector_detail,
        "backtest": backtest_detail,
        "source": {
            "name": f"synthetic-source-{identity}",
            "sha256": source_sha,
            "sync_receipt_sha256": sha(receipt_raw),
            "sync_receipt_path": str(root / "sync-receipt.json"),
        },
        "input_manifest": {**detail(root, "input-manifest.json"), "manifest_sha256": manifest_sha},
        "selector_source": detail(root, "selector-source.parquet"),
        "selector_sidecar": detail(root, "selector-sidecar.parquet"),
    }
    pointer = root / reader_module.FORMULA_GENERATION_POINTER_NAME
    pointer.write_bytes(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode())
    return pointer


def read(pointer: Path):
    return read_formula_generation(str(pointer), expected_target_date=DATE, require_source=True)


def relative_for(generation: dict) -> str:
    return f"m01/a_source/{generation['target_date']}/{generation['generation_id']}/binding.json"


def private_root(path: Path, *, marker: bool = True) -> SafeRoot:
    path.mkdir(parents=True, exist_ok=True)
    if marker:
        (path / ".v5-shadow-root").write_text("v5.shadow-root.v1\n", encoding="utf-8")
    return SafeRoot(path)


def check_normal_round_trip(source_a: Path, base: Path):
    pointer = make_generation(source_a, "a")
    root = private_root(base / "private-normal")
    first = candidate.create_binding(private_root=root, generation_pointer=str(pointer), target_date=DATE, read_formula_generation=read_formula_generation)
    relative = relative_for(read(pointer))
    before = root.read_bytes(relative)
    second = candidate.create_binding(private_root=root, generation_pointer=str(pointer), target_date=DATE, read_formula_generation=read_formula_generation)
    after = root.read_bytes(relative)
    assert first == second
    assert before == after
    assert first.generation_path == str(pointer.resolve())
    record("normal SafeRoot write -> disk read_and_verify -> same identity reuse", "PASS", {
        "binding_path": relative,
        "disk_bytes_stable_on_reuse": before == after,
        "generation_path": first.generation_path,
    })


def reproduce_same_id_different_source(source_base: Path, base: Path):
    pointer_a = make_generation(source_base / "source-a", "a")
    pointer_b = make_generation(source_base / "source-b", "b")
    expected_a = candidate._project(read(pointer_a))
    expected_b = candidate._project(read(pointer_b))
    assert expected_a.generation_id == expected_b.generation_id
    assert expected_a != expected_b
    root = private_root(base / "private-same-id")
    first = candidate.create_binding(private_root=root, generation_pointer=str(pointer_a), target_date=DATE, read_formula_generation=read_formula_generation)
    actual = candidate.create_binding(private_root=root, generation_pointer=str(pointer_b), target_date=DATE, read_formula_generation=read_formula_generation)
    assert actual == first == expected_a
    assert actual != expected_b
    record("same generation_id with different complete source identity and pointer", "REPRODUCED", {
        "generation_id_equal": True,
        "pointer_a": str(pointer_a.resolve()),
        "pointer_b": str(pointer_b.resolve()),
        "returned_pointer": actual.generation_path,
        "returned_old_binding": actual == expected_a,
        "request_identity_ignored": actual != expected_b,
    })


def reproduce_corrupt_binding_masking(source_base: Path, base: Path):
    pointer = make_generation(source_base / "source-corrupt", "corrupt")
    root = private_root(base / "private-corrupt")
    binding = candidate.create_binding(private_root=root, generation_pointer=str(pointer), target_date=DATE, read_formula_generation=read_formula_generation)
    relative = relative_for(read(pointer))
    damaged = b"{\"truncated\":"
    root.write_bytes(relative, damaged)
    surfaced = None
    try:
        candidate.create_binding(private_root=root, generation_pointer=str(pointer), target_date=DATE, read_formula_generation=read_formula_generation)
    except Exception as exc:
        surfaced = {"type": type(exc).__name__, "message": str(exc)}
    assert surfaced and surfaced["type"] == "FileExistsError"
    assert root.read_bytes(relative) == damaged
    record("corrupt existing binding error is masked while old bytes are preserved", "REPRODUCED", {
        "corruption": "invalid JSON binding bytes",
        "surfaced_error": surfaced,
        "old_bytes_preserved": root.read_bytes(relative) == damaged,
        "initial_pointer": binding.generation_path,
    })


def reproduce_source_drift_masking(source_base: Path, base: Path):
    pointer_a = make_generation(source_base / "source-drift-a", "drift-a")
    pointer_b = make_generation(source_base / "source-drift-b", "drift-b")
    root = private_root(base / "private-drift")
    binding_a = candidate.create_binding(private_root=root, generation_pointer=str(pointer_a), target_date=DATE, read_formula_generation=read_formula_generation)
    relative = relative_for(read(pointer_a))
    original_binding_bytes = root.read_bytes(relative)
    receipt = pointer_a.parent / "sync-receipt.json"
    receipt_payload = json.loads(receipt.read_text())
    receipt_payload["fixture_identity"] = "drifted-after-binding"
    receipt.write_bytes(canonical_bytes(receipt_payload))
    direct_error = None
    try:
        read(pointer_a)
    except Exception as exc:
        direct_error = {"type": type(exc).__name__, "message": str(exc)}
    assert direct_error and "sync receipt SHA mismatch" in direct_error["message"]
    surfaced = None
    try:
        candidate.create_binding(private_root=root, generation_pointer=str(pointer_b), target_date=DATE, read_formula_generation=read_formula_generation)
    except Exception as exc:
        surfaced = {"type": type(exc).__name__, "message": str(exc)}
    assert surfaced and surfaced["type"] == "FileExistsError"
    assert root.read_bytes(relative) == original_binding_bytes
    record("existing source drift error is masked as no-replace collision", "REPRODUCED", {
        "direct_original_reader_error": direct_error,
        "candidate_surfaced_error": surfaced,
        "old_binding_bytes_preserved": root.read_bytes(relative) == original_binding_bytes,
        "initial_pointer": binding_a.generation_path,
    })


def reproduce_uninitialized_root(source_base: Path, base: Path):
    pointer = make_generation(source_base / "source-no-marker", "no-marker")
    root_path = base / "private-no-marker"
    root = private_root(root_path, marker=False)
    binding = candidate.create_binding(private_root=root, generation_pointer=str(pointer), target_date=DATE, read_formula_generation=read_formula_generation)
    assert not (root_path / ".v5-shadow-root").exists()
    assert binding.status == "BOUND"
    record("binding accepted with missing .v5-shadow-root marker", "REPRODUCED", {
        "marker_exists": False,
        "private_root": str(root_path),
        "binding_status": binding.status,
    })


def reproduce_overlapping_roots(source_base: Path, base: Path):
    pointer = make_generation(source_base / "source-overlap", "overlap")
    source_output_root = pointer.parent
    root = SafeRoot(source_output_root)
    binding = candidate.create_binding(private_root=root, generation_pointer=str(pointer), target_date=DATE, read_formula_generation=read_formula_generation)
    stored_path = source_output_root / relative_for(read(pointer))
    assert stored_path.is_file()
    assert stored_path.is_relative_to(source_output_root)
    assert not (source_output_root / ".v5-shadow-root").exists()
    record("binding accepted when private output root overlaps formula source root", "REPRODUCED", {
        "source_output_root": str(source_output_root),
        "binding_path": str(stored_path),
        "same_root": True,
        "marker_exists": False,
        "binding_status": binding.status,
    })


def reproduce_outside_generation_path(source_base: Path, base: Path):
    authorized_pointer = make_generation(source_base / "source-authorized", "authorized")
    outside_pointer = make_generation(source_base / "source-outside", "outside")
    root = private_root(base / "private-outside-generation")
    outside_binding = candidate._project(read(outside_pointer))
    relative = f"{RELATIVE}/manual-outside/binding.json"
    raw = json.dumps(asdict(outside_binding), sort_keys=True).encode()
    root.write_bytes(relative, raw, require_absent=True)
    accepted = candidate.read_and_verify_binding(safe_root=root, relative=relative, read_formula_generation=read_formula_generation)
    assert accepted.generation_path == str(outside_pointer.resolve())
    assert not Path(accepted.generation_path).is_relative_to(authorized_pointer.parent)
    record("read_and_verify accepted valid generation_path outside the designated source root", "REPRODUCED", {
        "designated_source_root": str(authorized_pointer.parent),
        "accepted_generation_path": accepted.generation_path,
        "candidate_api_has_source_root_argument": "source_root" in candidate.read_and_verify_binding.__kwdefaults__ if candidate.read_and_verify_binding.__kwdefaults__ else False,
    })


def reproduce_strict_integer(source_base: Path, base: Path):
    pointer = make_generation(source_base / "source-strict-int", "strict-int")
    root = private_root(base / "private-strict-int")
    binding = candidate.create_binding(private_root=root, generation_pointer=str(pointer), target_date=DATE, read_formula_generation=read_formula_generation)
    relative = relative_for(read(pointer))
    payload = json.loads(root.read_bytes(relative))
    payload["strict_source_verified"] = 1
    root.write_bytes(relative, json.dumps(payload, sort_keys=True).encode())
    accepted = candidate.read_and_verify_binding(safe_root=root, relative=relative, read_formula_generation=read_formula_generation)
    assert type(accepted.strict_source_verified) is int and accepted.strict_source_verified == 1
    record("binding parser accepted JSON strict_source_verified=1 as True", "REPRODUCED", {
        "returned_value": accepted.strict_source_verified,
        "returned_type": type(accepted.strict_source_verified).__name__,
        "compares_equal_to_true": accepted.strict_source_verified == True,
    })


def check_safe_root_rejects_symlink_and_traversal(source_base: Path, base: Path):
    pointer = make_generation(source_base / "source-safe-root", "safe-root")
    root_path = base / "private-safe-root"
    root = private_root(root_path)
    outside = base / "outside-sentinel"
    outside.mkdir(parents=True, exist_ok=True)
    (outside / "sentinel.json").write_text("outside", encoding="utf-8")
    (root_path / "m01").symlink_to(outside, target_is_directory=True)
    traversal_error = None
    try:
        root.read_bytes("../outside-sentinel/sentinel.json")
    except Exception as exc:
        traversal_error = {"type": type(exc).__name__, "message": str(exc)}
    symlink_error = None
    try:
        candidate.create_binding(private_root=root, generation_pointer=str(pointer), target_date=DATE, read_formula_generation=read_formula_generation)
    except Exception as exc:
        symlink_error = {"type": type(exc).__name__, "message": str(exc)}
    assert traversal_error and "OWNED_PATH_UNSAFE" in traversal_error["message"]
    assert symlink_error and isinstance(symlink_error["type"], str)
    assert (outside / "sentinel.json").read_text(encoding="utf-8") == "outside"
    assert not (outside / "a_source").exists()
    record("SafeRoot rejects traversal and symlinked binding ancestry", "PASS", {
        "traversal_error": traversal_error,
        "symlink_ancestry_error": symlink_error,
        "outside_sentinel_unchanged": True,
    })


def main():
    base = ACCEPTANCE / "fixtures"
    source_base = base / "sources"
    source_base.mkdir(parents=True, exist_ok=True)
    if base.exists():
        # The acceptance tree is a disposable synthetic fixture directory only.
        import shutil
        shutil.rmtree(base)
        source_base.mkdir(parents=True, exist_ok=True)

    checks = [
        lambda: check_normal_round_trip(source_base / "source-normal", base),
        lambda: reproduce_same_id_different_source(source_base, base),
        lambda: reproduce_corrupt_binding_masking(source_base, base),
        lambda: reproduce_source_drift_masking(source_base, base),
        lambda: reproduce_uninitialized_root(source_base, base),
        lambda: reproduce_overlapping_roots(source_base, base),
        lambda: reproduce_outside_generation_path(source_base, base),
        lambda: reproduce_strict_integer(source_base, base),
        lambda: check_safe_root_rejects_symlink_and_traversal(source_base, base),
    ]
    for check in checks:
        check()
    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "fixture_policy": "synthetic data only; fixed original SafeRoot and read_formula_generation",
        "cases": CASES,
        "pass_count": sum(case["status"] == "PASS" for case in CASES),
        "reproduced_count": sum(case["status"] == "REPRODUCED" for case in CASES),
    }
    OUTPUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"RESULT {payload['pass_count']} PASS; {payload['reproduced_count']} defect reproductions; output={OUTPUT}")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        raise
