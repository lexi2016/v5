"""M10 default producer/store/reader regression coverage.

The tests are written as integration seams; runtime execution depends on the
existing V5 test environment and is reported separately when unavailable.
"""
from __future__ import annotations

import tempfile

from v5_shadow.hk_close_daily import HKCloseReviewReader, HKCloseReviewStore


def test_store_reader_roundtrip_and_tamper_detection():
    with tempfile.TemporaryDirectory() as root:
        store = HKCloseReviewStore(root)
        store.publish("20261010-run", {"review": {"top20": ["HK.00001"]}})
        assert HKCloseReviewReader(root).read("20261010-run")["review"]["top20"] == ["HK.00001"]
        with open(f"{root}/20261010-run/payload.json", "w", encoding="utf-8") as handle:
            handle.write('{"review": {"top20": []}}')
        try:
            HKCloseReviewReader(root).read("20261010-run")
        except ValueError as exc:
            assert str(exc) == "M10_PAYLOAD_SHA_INVALID"
        else:
            raise AssertionError("tampered payload accepted")


def test_store_same_run_same_payload_is_idempotent():
    with tempfile.TemporaryDirectory() as root:
        store = HKCloseReviewStore(root)
        first = store.publish("run", {"x": 1})
        second = store.publish("run", {"x": 1})
        assert first == second
