"""M10 publication artifact integrity regression tests."""
from __future__ import annotations

import tempfile

import pytest

from v5_shadow.hk_close_daily import HKCloseReviewReader, HKCloseReviewStore


def test_publication_valid_roundtrip():
    with tempfile.TemporaryDirectory() as root:
        store = HKCloseReviewStore(root)
        store.publish("run", {"review": {"top20": ["HK.00001"]}}, {"generation": "g1"})
        assert HKCloseReviewReader(root).read("run")["review"]["top20"] == ["HK.00001"]


@pytest.mark.parametrize("mutation", ["missing", "tampered"])
def test_publication_missing_or_changed_is_rejected(tmp_path, mutation):
    store = HKCloseReviewStore(tmp_path)
    store.publish("run", {"review": {}}, {"generation": "g1"})
    publication = tmp_path / "run" / "publication.json"
    if mutation == "missing":
        publication.unlink()
    else:
        publication.write_text('{"generation":"g2"}', encoding="utf-8")
    with pytest.raises((ValueError, FileNotFoundError)):
        HKCloseReviewReader(tmp_path).read("run")


def test_same_run_same_publication_is_idempotent(tmp_path):
    store = HKCloseReviewStore(tmp_path)
    first = store.publish("run", {"review": {}}, {"generation": "g1"})
    second = store.publish("run", {"review": {}}, {"generation": "g1"})
    assert first == second


def test_same_run_changed_publication_conflicts(tmp_path):
    store = HKCloseReviewStore(tmp_path)
    store.publish("run", {"review": {}}, {"generation": "g1"})
    with pytest.raises(ValueError):
        store.publish("run", {"review": {}}, {"generation": "g2"})
