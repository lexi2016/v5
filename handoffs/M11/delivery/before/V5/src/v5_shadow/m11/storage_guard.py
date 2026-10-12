from __future__ import annotations

import os
from pathlib import Path


class M11StorageViolation(ValueError):
    pass


def validate_target_date(value: str) -> str:
    if not isinstance(value, str) or len(value) != 10:
        raise M11StorageViolation("M11_TARGET_DATE_INVALID")
    try:
        from datetime import date
        date.fromisoformat(value)
    except ValueError as exc:
        raise M11StorageViolation("M11_TARGET_DATE_INVALID") from exc
    return value


def assert_safe_root(root: Path) -> Path:
    root = Path(root)
    if root.exists() and root.is_symlink():
        raise M11StorageViolation("M11_ROOT_SYMLINK")
    resolved = root.resolve()
    if resolved != root.absolute().resolve():
        raise M11StorageViolation("M11_ROOT_ESCAPE")
    return resolved


def assert_no_symlink_parents(path: Path, root: Path) -> None:
    root = assert_safe_root(root)
    current = path
    while current != root:
        if current.exists() and current.is_symlink():
            raise M11StorageViolation("M11_PARENT_SYMLINK")
        if current == current.parent:
            raise M11StorageViolation("M11_ROOT_BOUNDARY")
        current = current.parent
    if root not in path.parents and path != root:
        raise M11StorageViolation("M11_PATH_OUTSIDE_ROOT")


def atomic_absent_publish(temp_path: Path, final_path: Path, root: Path) -> None:
    assert_no_symlink_parents(final_path.parent, root)
    if final_path.exists():
        raise FileExistsError("M11_IMMUTABLE_EXISTS")
    os.replace(temp_path, final_path)
