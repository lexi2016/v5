"""Compatibility helpers backed by the original descriptor-safe private store."""
from pathlib import Path
from .intraday_capsule import _date,_root
from .owner_sources import safe_root_class


class M11StorageViolation(ValueError):pass


def validate_target_date(value):
    try:return _date(value)
    except (ValueError,TypeError) as exc:raise M11StorageViolation('M11_TARGET_DATE_INVALID') from exc


def assert_safe_root(root):
    try:
        path=_root(root)
        try:
            with safe_root_class()(path).directory():pass
        except FileNotFoundError:pass
        return path
    except (ValueError,OSError) as exc:raise M11StorageViolation('M11_ROOT_BOUNDARY') from exc


def assert_no_symlink_parents(path,root):
    root=assert_safe_root(root);path=Path(path)
    if root not in path.parents and path!=root:raise M11StorageViolation('M11_PATH_OUTSIDE_ROOT')
    try:
        _root(path)
        try:
            with safe_root_class()(root).directory(str(path.relative_to(root)) if path!=root else None):pass
        except FileNotFoundError:pass
    except (ValueError,OSError) as exc:raise M11StorageViolation('M11_PARENT_SYMLINK') from exc


def atomic_absent_publish(temp_path,final_path,root):
    root=assert_safe_root(root);temp_path=Path(temp_path);final_path=Path(final_path)
    if root not in temp_path.parents or root not in final_path.parents:raise M11StorageViolation('M11_PATH_OUTSIDE_ROOT')
    io=safe_root_class()(root)
    raw=io.read_bytes(str(temp_path.relative_to(root)))
    # Original no-replace hard-link publication, not a check-then-overwrite rename.
    io.write_bytes(str(final_path.relative_to(root)),raw,require_absent=True)
