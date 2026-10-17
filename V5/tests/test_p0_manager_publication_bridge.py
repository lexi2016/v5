"""Narrow publication bridge tests.

These tests verify identity boundaries only. They do not create manager output,
call owners, or publish a production module head.
"""

from v5_shadow.p0_manager_publication_bridge import build_manager_record


def test_record_keeps_route_and_saved_identity():
    config = {"module_id": "manager", "release_id": "test"}
    record = build_manager_record(
        config=config,
        payload={"status": "PARTIAL", "gaps": ["CANNOT_CONFIRM"]},
        source_input_sha256="a" * 64,
        date="20261012",
    )
    assert record["path"] == "/api/v4/manager/research/workspace"
    assert record["data_kind"] == "OWNER_RESULT"
    assert record["source_input_sha256"] == "a" * 64


def test_missing_saved_identity_rejects():
    try:
        build_manager_record(
            config={"module_id": "manager", "release_id": "test"},
            payload={},
            source_input_sha256="bad",
            date="20261012",
        )
    except ValueError as error:
        assert str(error) == "MANAGER_SOURCE_IDENTITY_REQUIRED"
    else:
        raise AssertionError("missing identity must reject")

def test_absent_saved_identity_rejects_with_same_public_contract():
    for source_input_sha256 in (None, ""):
        try:
            build_manager_record(
                config={"module_id": "manager", "release_id": "test"},
                payload={},
                source_input_sha256=source_input_sha256,
                date="20261012",
            )
        except ValueError as error:
            assert str(error) == "MANAGER_SOURCE_IDENTITY_REQUIRED"
        else:
            raise AssertionError("absent identity must reject")
