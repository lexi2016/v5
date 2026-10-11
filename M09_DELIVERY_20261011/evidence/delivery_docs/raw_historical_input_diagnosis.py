"""Read-only R3 raw-input audit and candidate receipt-size probe; JSON on stdout.

This helper creates no files or directories. It does not relocate pointers,
construct an admission manifest, decode/clean parquet, run the producer,
initialize an output root, publish, or generate a success receipt. A successful
helper exit means only that its read observations completed as described.
"""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import argparse
from datetime import datetime, timezone
import hashlib
import importlib
import json
from pathlib import Path, PurePosixPath
import re
import stat


T = "20261009"
MANIFEST_SHA = "d4df3db803bc6b9c79aaca3a42145eb6f2585f7b4d9e5f5f3263bc549949e53e"
RECEIPT = "originals/panel_source_receipt.json"
MEMBERS = "originals/membership_20261009.txt"


def checked_path(value):
    path = Path(value)
    if not path.is_absolute() or path == Path("/") or ".." in path.parts:
        raise ValueError("ABSOLUTE_NONROOT_PATH_REQUIRED")
    for part in (path, *path.parents):
        if part.is_symlink():
            raise ValueError("SYMLINK_PATH_REJECTED")
    return path


def file_identity(path):
    path = checked_path(path)
    before = path.stat()
    if not stat.S_ISREG(before.st_mode):
        raise ValueError("REGULAR_FILE_REQUIRED")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    after = path.stat()
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
            after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
        raise ValueError("FILE_CHANGED_DURING_OBSERVATION")
    return {"bytes": after.st_size, "raw_sha256": digest.hexdigest()}


def inventory(root):
    manifest_path = root / "MANIFEST.json"
    if file_identity(manifest_path)["raw_sha256"] != MANIFEST_SHA:
        raise ValueError("ORIGINAL_RUNTIME_MANIFEST_CHANGED")
    manifest = json.loads(manifest_path.read_bytes())
    entries = manifest["files"]
    if manifest.get("count") != 40 or len(entries) != 40:
        raise ValueError("ORIGINAL_RUNTIME_MEMBER_COUNT_CHANGED")
    result = {}
    for entry in entries:
        relative = entry["path"]
        parsed = PurePosixPath(relative)
        if (parsed.is_absolute() or ".." in parsed.parts or "\\" in relative
                or relative in result):
            raise ValueError("ORIGINAL_RUNTIME_PATH_INVALID")
        actual = file_identity(root / relative)
        if actual != {"bytes": entry["bytes"], "raw_sha256": entry["sha256"]}:
            raise ValueError("ORIGINAL_RUNTIME_BYTES_CHANGED:" + relative)
        result[relative] = actual
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-inputs", required=True)
    parser.add_argument("--candidate-src", required=True, help="Existing after/V5/src directory")
    args = parser.parse_args()
    root = checked_path(args.runtime_inputs)
    candidate_src = checked_path(args.candidate_src)
    report = {
        "schema_version": "v5.m09.raw_historical_read_diagnosis.v1", "trade_date": T,
        "classification": "READ_ONLY_HISTORICAL_INPUT_OBSERVATION",
        "observed_at_utc": datetime.now(timezone.utc).isoformat(),
        "files_created_by_helper": False, "input_cleaning_applied": False,
        "parquet_decode": "NOT_RUN", "full_candidate_admission": "NOT_RUN_NO_RELOCATED_MANIFEST",
        "original_price_model": "NOT_RUN", "product_publication": "NOT_RUN",
        "natural_acceptance": "NOT_RUN", "strict_1500_pit_verified": False,
    }
    exit_code = 0
    try:
        before = inventory(root)
        report["original_files"] = before
        members = (root / MEMBERS).read_text(encoding="utf-8-sig").splitlines()
        report["observed_membership_text"] = {
            "path": MEMBERS, "line_count": len(members), "unique_count": len(set(members)),
            "duplicate_line_count": len(members) - len(set(members)),
            "invalid_code_line_count": sum(re.fullmatch(r"[0-9]{6}\.(SH|SZ|BJ)", code) is None for code in members),
            "full_market_membership_verified": False,
        }
        panel_report = json.loads((root / "panel_evidence.json").read_bytes())
        report["attached_mac_panel_statistics"] = {
            "evidence_path": "panel_evidence.json", "recomputed_here": False,
            "scope": "SUPPLIED_MAC_EXTRACTION_REPORT_ONLY",
            **{key: panel_report[key] for key in ("row_count", "unique_members", "missing_or_nan", "empty_strings")},
        }
        report["attached_timing_authority"] = json.loads((root / "timing_and_authority.json").read_bytes())
        report["final_panel_available_at"] = None
        report["available_at_note"] = "Unknown; no inference from copy time, mtime, filename, sync records or timezone-free formula timestamps."
        pointer = (root / "originals/CURRENT_SELECTOR_READY_PANEL.txt").read_text(encoding="utf-8-sig").strip()
        report["original_pointer"] = {"text": pointer, "followed": False, "rewritten": False,
                                      "binding_status": "FOREIGN_ABSOLUTE_MAC_PATH_RETAINED_AS_EVIDENCE"}

        # Import only the local candidate and use its actual read-only size
        # guard. This does not call admission, run, initialize or publication.
        sys.path.insert(0, str(candidate_src))
        core_path = candidate_src / "v5_shadow/a_close_daily.py"
        core_before = file_identity(core_path)
        core = importlib.import_module("v5_shadow.a_close_daily")
        if Path(core.__file__).absolute() != core_path:
            raise ValueError("CANDIDATE_MODULE_PATH_MISMATCH")
        limit = core.MAX_JSON_BYTES
        if type(limit) is not int or limit <= 0:
            raise ValueError("CANDIDATE_RECEIPT_LIMIT_INVALID")
        probe = {"limit_bytes": limit, "actual_receipt_bytes": before[RECEIPT]["bytes"],
                 "excess_bytes": before[RECEIPT]["bytes"] - limit,
                 "candidate_module": {"path": str(core_path), **core_before},
                 "called": "frozen.safe_root(runtime_inputs).read_bytes(original_receipt, max_bytes=MAX_JSON_BYTES)",
                 "full_admission_called": False}
        try:
            core.frozen.safe_root(root).read_bytes(RECEIPT, max_bytes=limit)
        except (OSError, ValueError) as error:
            probe.update(status="READ_REJECTED", exception_type=type(error).__name__, exception_text=str(error))
            if str(error) != "OWNED_FILE_TOO_LARGE":
                exit_code = 2
        else:
            probe["status"] = "UNEXPECTED_READ_ACCEPTED_REQUIRES_REVIEW"
            exit_code = 2
        probe["candidate_module_bytes_unchanged"] = file_identity(core_path) == core_before
        if not probe["candidate_module_bytes_unchanged"]:
            exit_code = 2
        report["candidate_receipt_guard_probe"] = probe
        report["original_file_bytes_unchanged"] = inventory(root) == before
        if not report["original_file_bytes_unchanged"]:
            exit_code = 2
        report["observation_status"] = "OBSERVED_REJECTION_NOT_PRODUCT_ACCEPTANCE" if exit_code == 0 else "CANNOT_CONFIRM"
    except Exception as error:
        report["observation_status"] = "CANNOT_CONFIRM"
        report["error"] = {"type": type(error).__name__, "text": str(error)}
        exit_code = 2
    report["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
