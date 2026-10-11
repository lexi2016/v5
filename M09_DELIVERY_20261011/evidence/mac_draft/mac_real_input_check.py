"""Mac-only candidate diagnostic for the unchanged real 20261009 projection.

This creates a NEW isolated evidence directory. It reads the attached original
inputs, copies their bytes unchanged, decodes real parquet through installed
pyarrow, and requires the candidate to reject daily admission. It does not
collect, normalize, schedule, publish a success, or touch active roots.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import stat
import sys
import traceback

T = "20261009"
COLUMNS = ("trade_date", "ts_code", "name", "pct_chg", "amount", "bar_close_pos", "tdx_industry_code", "tdx_industry_name")
EXPECTED = {
    "originals/panel_20261009_required8.parquet": (279209, "7dfa12fa03ad76d5e946088f88993748a3fffd8943281a12eb364c35712f8c47"),
    "originals/membership_20261009.txt": (51260, "b1f561b1d18a5341784c4906b0e3bbbf21d7d092823e4a60c2787fdf004d91fb"),
    "originals/panel_source_receipt.json": (80017050, "de652e8ddc540433bef8d0dd9f13da54eb973cf520156109d9e61794dace2a6e"),
    "originals/CURRENT_SELECTOR_READY_PANEL.txt": (242, "91a52a4f28098a2525ca4c9af9dd96c082e1c028392a55787fc9bcfbcf2f946d"),
    "originals/dispatcher_pointer.txt": (242, "91a52a4f28098a2525ca4c9af9dd96c082e1c028392a55787fc9bcfbcf2f946d"),
    "originals/daily_pointer.txt": (242, "91a52a4f28098a2525ca4c9af9dd96c082e1c028392a55787fc9bcfbcf2f946d"),
}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(data)
    return h.hexdigest()


def checked_path(value):
    path = Path(value)
    if not path.is_absolute() or ".." in path.parts or path == Path("/"):
        raise ValueError("absolute non-root path required")
    for item in (path, *path.parents):
        if item.is_symlink():
            raise ValueError("symlink path rejected: " + str(item))
    return path


def environment():
    versions = {}
    for name in ("pandas", "pyarrow", "numpy", "pytest"):
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    return {"python":sys.version, "executable":sys.executable, "platform":platform.platform(),
            **versions, "dependencies_changed_by_check":False,
            "declared_constraints":"Python>=3.14; pandas>=2.3,<3; pyarrow>=21,<25",
            "acceptance_class":"UNCERTIFIED_RUNTIME_DIAGNOSTIC"}


def save(path, value):
    with path.open("xb") as stream:
        stream.write(canonical(value))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--after", required=True)
    parser.add_argument("--runtime-inputs", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    after, original, out = map(checked_path, (args.after, args.runtime_inputs, args.out))
    for protected in (after, original):
        if out.is_relative_to(protected) or protected.is_relative_to(out):
            raise ValueError("output must be disjoint from candidate and original material")
    if any(part in ("com.lexi.v4.local", "com.lexi.v35.local") for part in out.parts):
        raise ValueError("active application roots are not diagnostic output roots")
    if not out.parent.is_dir():
        raise ValueError("output parent must already exist")
    out.mkdir(mode=0o700)  # Refuse reuse or merge, even after a prior failed check.
    start = datetime.now(timezone.utc)
    report = {"schema_version":"m09.mac_historical_diagnostic.v1", "trade_date":T,
              "execution_kind":"RECORDED_INPUT_REPLAY", "started_at":start.isoformat(),
              "environment":environment(), "real_input_admission":"NOT_RUN", "natural_acceptance":"NOT_RUN"}
    try:
        input_manifest = json.loads((original / "MANIFEST.json").read_bytes())
        if len(input_manifest["files"]) != 40:
            raise ValueError("expected the exact R2 runtime material manifest with 40 files")
        raw_inventory = {}
        for entry in input_manifest["files"]:
            relative = entry["path"]
            parsed = PurePosixPath(relative)
            if parsed.is_absolute() or ".." in parsed.parts or "\\" in relative or relative in raw_inventory:
                raise ValueError("runtime material manifest path invalid")
            path = checked_path(original / relative)
            info = path.stat()
            if not stat.S_ISREG(info.st_mode):
                raise ValueError("runtime material must be a regular file")
            actual = {"bytes":info.st_size,"sha256":digest(path)}
            if actual != {"bytes":entry["bytes"],"sha256":entry["sha256"]}:
                raise ValueError("runtime original identity mismatch: " + relative)
            raw_inventory[relative] = actual
        for relative, (size, expected_sha) in EXPECTED.items():
            if raw_inventory[relative] != {"bytes":size,"sha256":expected_sha}:
                raise ValueError("R3 pinned input mismatch: " + relative)
        save(out / "original_bytes_before.json", raw_inventory)
        source = out / "relocated_source"
        (source / "originals").mkdir(parents=True, mode=0o700)
        for relative in EXPECTED:
            destination = source / relative
            shutil.copyfile(original / relative, destination)
            if digest(destination) != EXPECTED[relative][1]:
                raise ValueError("copied original changed: " + relative)
        # The original Mac pointers are retained as evidence. Only this newly
        # created pointer is supplied to candidate admission and the optional
        # original-producer diagnostic. It is not a source timestamp.
        local_pointer = source / "candidate_panel_pointer.txt"
        local_pointer.write_text(str(source / "originals/panel_20261009_required8.parquet") + "\n", encoding="utf-8")
        save(out / "relocation.json", {
            "original_panel_sha256":"25aaa10f2080a72f0f9266a9456a3c3968dd1370068f31b0fb9106ea34434485",
            "original_panel_bytes":1383142544,
            "projection_path":str(source / "originals/panel_20261009_required8.parquet"),
            "projection_sha256":EXPECTED["originals/panel_20261009_required8.parquet"][1],
            "new_pointer_path":str(local_pointer),"new_pointer_sha256":digest(local_pointer),
            "source_time_inferred_from_copy_or_pointer":False,
            "originals_preserved":list(EXPECTED),
        })
        import pyarrow as pa
        import pyarrow.parquet as pq
        parquet_bytes = (source / "originals/panel_20261009_required8.parquet").read_bytes()
        table = pq.read_table(pa.BufferReader(parquet_bytes))
        if tuple(table.column_names) != COLUMNS:
            raise ValueError("projection must retain the exact eight original columns and their order")
        rows = table.to_pylist()
        members = (source / "originals/membership_20261009.txt").read_text(encoding="utf-8-sig").splitlines()
        missing, empty = {}, {}
        for column in COLUMNS:
            missing[column] = sum(row[column] is None or (isinstance(row[column], float) and math.isnan(row[column])) for row in rows)
            empty[column] = sum(isinstance(row[column],str) and row[column] == "" for row in rows)
        statistics = {"row_count":len(rows),"unique_members":len({r["ts_code"] for r in rows}),
                      "missing_or_nan":missing,"empty_strings":empty,"schema":str(table.schema),
                      "wrong_date_rows":sum(type(r["trade_date"]) is not str or r["trade_date"] != T for r in rows),
                      "bad_suffix_rows":sum(not isinstance(r["ts_code"],str) or re.fullmatch(r"[0-9]{6}\.(SH|SZ|BJ)",r["ts_code"]) is None for r in rows),
                      "declared_member_set_matches":set(members)=={r["ts_code"] for r in rows},
                      "row_order_matches_members":members==[r["ts_code"] for r in rows],
                      "cleaning_applied":False}
        save(out / "decoded_original_statistics.json", statistics)
        expected_statistics = json.loads((original / "panel_evidence.json").read_bytes())
        for key in ("row_count","unique_members","missing_or_nan","empty_strings"):
            if statistics[key] != expected_statistics[key]:
                raise ValueError("original statistics differ from recorded Mac extraction: " + key)
        if statistics["wrong_date_rows"] or statistics["bad_suffix_rows"] or not statistics["declared_member_set_matches"]:
            raise ValueError("unaltered projection has unexpected date/member discrepancy")
        report["real_parquet_decode"] = "OBSERVED_UNCHANGED_INPUT_STATISTICS_MATCH"
        # Preserve missing source metadata as null. In particular, receipt sync
        # timestamps and formula timestamps are not final-panel availability.
        manifest = {
            "schema_version":"v5.m09.input.v1","trade_date":T,"data_kind":"RECORDED_INPUT_REPLAY",
            "panel":{"pointer_path":local_pointer.name,"pointer_sha256":digest(local_pointer),
                     "sha256":EXPECTED["originals/panel_20261009_required8.parquet"][1],"format":"PARQUET","row_count":len(rows)},
            "membership":{"path":"originals/membership_20261009.txt", "sha256":EXPECTED["originals/membership_20261009.txt"][1],
                          "scope":"DECLARED_UNIVERSE","source_id":None,"version":None,"captured_at":None,"available_at":None},
            "provenance":{"source_id":None,"version":None,"status":"PARTIAL","authority_status":"REBUILD_REQUIRED",
                          "coverage_rate":0.8858620689655172,"captured_at":None,"acquired_at":None,"available_at":None,
                          "receipt_path":"originals/panel_source_receipt.json","receipt_sha256":EXPECTED["originals/panel_source_receipt.json"][1],
                          "receipt_fields":{"trade_date":"/target_date"}},
            "evidence":{},
        }
        manifest_path = source / "diagnostic_input.json"
        save(manifest_path, manifest)
        sys.path.insert(0, str(after / "V5/src"))
        from v5_shadow.a_close_daily import diagnose_a_close_input, initialize_a_close_root, read_a_close_daily, run_a_close_daily
        root = out / "rejected_attempts_root"
        initialize_a_close_root(root)
        for slot in ("16:05","17:10"):
            diagnostic = diagnose_a_close_input(source,manifest_path.name,digest(manifest_path),T,slot)
            save(out / ("admission_" + slot.replace(":","") + ".json"), diagnostic)
            if diagnostic.get("admitted") is not False:
                raise ValueError("unexpected admission of known-incomplete historical original")
            issue_codes = {item.get("code") for item in diagnostic.get("issues",[])}
            if not {"SOURCE_AUTHORITY_NOT_READY","SOURCE_TIME_INVALID_OR_UNKNOWN","PANEL_NUMBER_INVALID","PANEL_TEXT_MISSING"} <= issue_codes:
                raise ValueError("expected raw-data defects were not reported: " + repr(issue_codes))
            request = {"schema_version":"v5.m09.daily_request.v1","trade_date":T,"slot":slot,
                       "job_id":"m09_mac_historical_diagnostic_" + slot.replace(":",""),"attempt_id":"original_uncleaned_" + slot.replace(":",""),
                       "execution_kind":"RECORDED_INPUT_REPLAY","triggered_at":datetime.now(timezone.utc).isoformat(),
                       "source_root":str(source),"input_manifest":manifest_path.name,"input_manifest_sha256":digest(manifest_path),
                       "configuration_revision":"mac-original-uncleaned-diagnostic-v1"}
            receipt = run_a_close_daily(root, request)
            save(out / ("attempt_" + slot.replace(":","") + ".json"), receipt)
            if receipt.get("status") != "FAILED" or read_a_close_daily(root,T) is not None:
                raise ValueError("historical rejection unexpectedly created a served result")
        for relative, item in raw_inventory.items():
            if (original / relative).stat().st_size != item["bytes"] or digest(original / relative) != item["sha256"]:
                raise ValueError("original material changed during diagnostic: " + relative)
        for relative, (size, expected_sha) in EXPECTED.items():
            if (source / relative).stat().st_size != size or digest(source / relative) != expected_sha:
                raise ValueError("relocated source changed during diagnostic: " + relative)
        report["original_and_relocated_bytes_unchanged"] = True
        report["real_input_admission"] = "REJECTED_AS_REQUIRED"
        report["real_price_model_success"] = "NOT_RUN_INPUT_NOT_ADMITTED"
        report["status"] = "EXPECTED_REJECTION_CONFIRMED"
    except Exception as exc:
        report["status"] = "FAILED_OR_BLOCKED"
        report["reason"] = type(exc).__name__ + ":" + str(exc)
        (out / "traceback.txt").write_text(traceback.format_exc(), encoding="utf-8")
        raise
    finally:
        end = datetime.now(timezone.utc)
        report["finished_at"] = end.isoformat()
        report["finished_at_shanghai"] = end.astimezone(timezone(timedelta(hours=8))).isoformat()
        save(out / "diagnostic_result.json", report)
        print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
