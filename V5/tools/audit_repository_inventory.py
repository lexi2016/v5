#!/usr/bin/env python3
"""Validate the checked-in source and duplicate inventories against a pinned Git tree.

Standard-library only. This is a source-inventory consistency check, not product
acceptance or a statement about deployed/runtime behavior.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

DEFAULT_COMMIT = "01d93717905813705732161d4d79062ae5af2d99"
SOURCE_MANIFEST = Path("V5/docs/architecture/SOURCE_FILE_MANIFEST.json")
DUPLICATE_MANIFEST = Path("V5/docs/architecture/DUPLICATE_BLOB_INVENTORY.json")


def git(repo: Path, *args: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout


def tracked_blobs(repo: Path, commit: str) -> dict[str, dict]:
    raw = git(repo, "ls-tree", "-r", "-l", "-z", commit)
    files: dict[str, dict] = {}
    for record in raw.split(b"\0"):
        if not record:
            continue
        metadata, path_bytes = record.split(b"\t", 1)
        mode, object_type, sha, size = metadata.decode("ascii").split(" ", 3)
        if object_type != "blob":
            continue
        path = path_bytes.decode("utf-8")
        files[path] = {
            "path": path,
            "mode": mode,
            "type": object_type,
            "git_blob_sha1": sha,
            "size_bytes": int(size),
        }
    return files


def duplicate_groups(files: dict[str, dict]) -> list[dict]:
    by_sha: dict[str, list[dict]] = defaultdict(list)
    for row in files.values():
        by_sha[row["git_blob_sha1"]].append(
            {"path": row["path"], "size_bytes": row["size_bytes"], "mode": row["mode"]}
        )
    groups = []
    for sha, paths in by_sha.items():
        if len(paths) < 2:
            continue
        paths.sort(key=lambda row: row["path"])
        groups.append({"git_blob_sha1": sha, "occurrences": len(paths), "paths": paths})
    groups.sort(key=lambda row: (-row["occurrences"], row["git_blob_sha1"]))
    return groups


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError(f"manifest root must be object: {path}")
    return value


def audit(repo: Path, commit: str) -> list[str]:
    errors: list[str] = []
    source = load_json(repo / SOURCE_MANIFEST)
    duplicate = load_json(repo / DUPLICATE_MANIFEST)

    if source.get("source", {}).get("commit") != commit:
        errors.append("source manifest commit does not match requested commit")
    if duplicate.get("source", {}).get("commit") != commit:
        errors.append("duplicate manifest commit does not match requested commit")

    actual = tracked_blobs(repo, commit)
    listed_rows = source.get("files")
    if not isinstance(listed_rows, list):
        return errors + ["source manifest files must be a list"]

    listed: dict[str, dict] = {}
    for row in listed_rows:
        if not isinstance(row, dict) or not isinstance(row.get("path"), str):
            errors.append("source manifest contains malformed row")
            continue
        path = row["path"]
        if path in listed:
            errors.append(f"duplicate path in source manifest: {path}")
        listed[path] = row

    if set(listed) != set(actual):
        missing = sorted(set(actual) - set(listed))
        extra = sorted(set(listed) - set(actual))
        if missing:
            errors.append(f"source manifest missing {len(missing)} paths; first={missing[:5]}")
        if extra:
            errors.append(f"source manifest has {len(extra)} extra paths; first={extra[:5]}")

    for path in set(listed) & set(actual):
        expected = actual[path]
        row = listed[path]
        for key in ("mode", "type", "git_blob_sha1", "size_bytes"):
            if row.get(key) != expected[key]:
                errors.append(f"source manifest mismatch: {path} field={key}")
                break

    expected_groups = duplicate_groups(actual)
    if duplicate.get("groups") != expected_groups:
        errors.append("duplicate blob groups do not match pinned Git tree")

    summary = duplicate.get("summary", {})
    actual_summary = {
        "file_count": len(actual),
        "unique_blob_count": len({row["git_blob_sha1"] for row in actual.values()}),
        "duplicate_blob_groups": len(expected_groups),
        "files_in_duplicate_groups": sum(group["occurrences"] for group in expected_groups),
        "duplicate_occurrences_beyond_first": sum(group["occurrences"] - 1 for group in expected_groups),
    }
    for key, value in actual_summary.items():
        if summary.get(key) != value:
            errors.append(f"duplicate manifest summary mismatch: {key}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--commit", default=DEFAULT_COMMIT)
    args = parser.parse_args()
    try:
        errors = audit(args.repo.resolve(), args.commit)
    except (OSError, ValueError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        print(f"INVENTORY_AUDIT_ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    if errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print(f"PASS: source inventory and duplicate groups match {args.commit}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
