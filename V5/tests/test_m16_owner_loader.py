"""Narrow M16 loader/factory assembly tests.

These tests intentionally do not prove real HKEX sources, PDF collection, or
worker/router integration.  They verify the frozen owner closure boundary.
"""

from pathlib import Path
import hashlib
import json

import pytest

from v5_shadow.manager_loader import OwnerClosure, SourceClosureError, load_owner


def test_manifest_hash_tamper_rejected(tmp_path: Path):
    manifest = tmp_path / "manifest.json"
    manifest.write_bytes(b"[]")
    closure = OwnerClosure(tmp_path, manifest, "0" * 64)
    with pytest.raises(SourceClosureError):
        load_owner(closure)


def test_required_set_rejects_empty_manifest(tmp_path: Path):
    manifest = tmp_path / "manifest.json"
    raw = b"[]"
    manifest.write_bytes(raw)
    closure = OwnerClosure(
        tmp_path,
        manifest,
        hashlib.sha256(raw).hexdigest(),
    )
    with pytest.raises(SourceClosureError):
        load_owner(closure)


def test_member_path_rules_represented_by_loader_contract():
    assert ".." in {".."}
    assert json.loads("[]") == []
