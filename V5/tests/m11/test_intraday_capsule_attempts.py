from pathlib import Path

from v5_shadow.m11.intraday_capsule import IntradayCapsuleStore, M11Slot


def _slot():
    return M11Slot("2026-10-11", "09:25", "09:25", "capture", "run-1")


def test_attempt_and_cold_reader(tmp_path: Path):
    store = IntradayCapsuleStore(tmp_path)
    slot = _slot()
    store.write_attempt(slot, "ATTEMPT_UNKNOWN", "TIMEOUT")
    store.write_success(slot, {"evidence": "ok"}, "source")
    assert store.read_verified(slot)["evidence"] == "ok"


def test_invalid_attempt_state(tmp_path: Path):
    store = IntradayCapsuleStore(tmp_path)
    try:
        store.write_attempt(_slot(), "READY")
    except ValueError:
        return
    raise AssertionError("invalid state accepted")
