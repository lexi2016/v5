"""Narrow P0 manager checkpoint integration tests.

These tests inject only saved owner-reference shaped inputs. They do not fake
owner execution or publication.
"""
from pathlib import Path

from v5_shadow import p0_manager_owner_checkpoint as checkpoint


def test_requires_saved_owner_reference():
    try:
        checkpoint._require_reference({})
    except ValueError as error:
        assert str(error) == "OWNER_REFERENCE_REQUIRED"
    else:
        raise AssertionError("missing owner reference must reject")


def test_slice_keeps_publication_unconnected():
    assert checkpoint.run_saved_owner_checkpoint.__doc__
    assert "original manager" in checkpoint.run_saved_owner_checkpoint.__doc__


def test_no_http_or_refresh_claims():
    source = Path(checkpoint.__file__).read_text()
    assert "publish_generation" not in source
    assert "refresh_owner" not in source
