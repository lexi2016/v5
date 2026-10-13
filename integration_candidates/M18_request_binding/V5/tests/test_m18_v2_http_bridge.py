from v5_shadow.m18_v2_http_bridge import descriptor_response, PAGES_ROUTE


def test_descriptor_only_small_payload():
    value = {"schema_version": "v5.m18.v2.descriptor.v1", "run_id": "x"}
    assert descriptor_response({"payload": value}) == value


def test_missing_descriptor_not_ready():
    try:
        descriptor_response({"payload": {}})
    except ValueError as error:
        assert str(error) == "M18_DESCRIPTOR_NOT_READY"
    else:
        raise AssertionError("missing descriptor must reject")


def test_pages_route_is_bounded_entry():
    assert PAGES_ROUTE.endswith('/pages')
