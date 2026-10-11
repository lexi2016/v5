from pathlib import Path

from v5_shadow.m11 import IntradayCapsuleStore, M11Slot


def test_m11_roundtrip(tmp_path: Path):
    store = IntradayCapsuleStore(tmp_path)
    slot = M11Slot("2026-10-11", "09:25", "09:33", "explicit", "run-1")
    store.write_success(slot, {"status": "READY"}, "source-sha")
    assert store.read_verified(slot) == {"status": "READY"}


def test_slots_are_fixed():
    assert M11Slot("d", "09:25", "c", "t", "r").slot == "09:25"
