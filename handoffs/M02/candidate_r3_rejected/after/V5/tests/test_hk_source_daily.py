def test_error_reader_is_rejected():
    from v5_shadow.hk_source_daily import _reader_state
    assert _reader_state(
        "membership", {"error": "BAD_SHA"}
    )["status"] == "REJECTED"


def test_empty_dict_not_valid():
    from v5_shadow.hk_source_daily import _reader_state
    assert _reader_state(
        "native", {}
    )["status"] != "VALID"


def test_external_flag_not_authority():
    from v5_shadow.hk_source_daily import _reader_state
    value = _reader_state(
        "membership",
        {"formal_eligibility_verified": True}
    )
    assert value["status"] == "VALID"
