"""Narrow M18 publication tests.

These tests assert descriptor/CAS boundaries only. They do not fake bundle
construction or execute owners.
"""

from v5_shadow.m18_v2_publication_bridge import descriptor_from_bundle


def test_descriptor_keeps_v2_generation_separate():
    identity = {"run_id": "a" * 32, "target_date": "20261012"}
    meta = {"identity": identity, "generation_id": "g" * 64, "profile_sha256": "p" * 64}
    descriptor = descriptor_from_bundle(None, identity, meta)
    assert descriptor["generation_id"] == "g" * 64
    assert descriptor["status"] == "READY"


def test_descriptor_rejects_wrong_identity():
    try:
        descriptor_from_bundle(None, {"run_id": "a" * 32}, {"identity": {"run_id": "b" * 32}})
    except ValueError as error:
        assert str(error) == "M18_IDENTITY_MISMATCH"
    else:
        raise AssertionError("wrong identity must reject")
