from pathlib import Path
import tempfile

from v5_shadow.m11.intraday_capsule import IntradayCapsuleStore, M11Slot


def slot():
    return M11Slot("2026-10-11", "09:25", "09:25", "manual", "run-1")


def test_default_store_write_and_independent_read():
    with tempfile.TemporaryDirectory() as root:
        store = IntradayCapsuleStore(Path(root).resolve())
        store.write_success(slot(), {"owner": "fixture", "value": 1}, "source-sha")
        assert store.read_verified(slot())["value"] == 1


def test_parent_escape_rejected():
    with tempfile.TemporaryDirectory() as root:
        try:
            IntradayCapsuleStore(Path(root) / ".." / "outside")
        except ValueError:
            return
        assert False


def test_second_publish_does_not_replace_success():
    with tempfile.TemporaryDirectory() as root:
        store = IntradayCapsuleStore(root)
        store.write_success(slot(), {"value": 1}, "sha")
        try:
            store.write_success(slot(), {"value": 2}, "sha")
        except FileExistsError:
            return
        assert False
