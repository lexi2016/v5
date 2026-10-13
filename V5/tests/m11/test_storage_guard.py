from pathlib import Path
import pytest

from v5_shadow.m11.storage_guard import (
    M11StorageViolation,
    assert_no_symlink_parents,
    validate_target_date,
)


def test_target_date_validation():
    assert validate_target_date("2026-10-11") == "2026-10-11"
    with pytest.raises(M11StorageViolation):
        validate_target_date("bad")


def test_root_escape_rejected(tmp_path: Path):
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside"
    with pytest.raises(M11StorageViolation):
        assert_no_symlink_parents(outside / "x", root)
