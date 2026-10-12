from v5_shadow.hk_source_daily import _reader_result


def test_membership_error_is_rejected():
    result = _reader_result("membership", {"error": "BAD_SHA"}, ["target_date"])
    assert result["status"] == "REJECTED"


def test_empty_mapping_is_rejected():
    result = _reader_result("native", {}, ["master", "manifest"])
    assert result["status"] == "REJECTED"


def test_fake_qualification_flag_is_not_authority():
    result = _reader_result(
        "membership",
        {"formal_eligibility_verified": True},
        ["target_date", "request_sha256", "source_capsule_sha256", "codes", "source"],
    )
    assert result["status"] == "REJECTED"
