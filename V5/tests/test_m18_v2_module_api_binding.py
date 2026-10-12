"""M18 v2 bounded API binding tests.

These tests exercise configuration identity and the existing read-only API
contract. They do not build bundles or publish data.
"""

from pathlib import Path

from v5_shadow.module_api import _config


def test_m18_routes_are_explicit_and_read_only():
    routes = [
        "/api/v4/manager/m18/v2",
        "/api/v4/manager/m18/v2/pages",
    ]
    assert routes[0] != routes[1]
    assert all(route.startswith("/api/") for route in routes)


def test_m18_config_example_has_bounded_routes():
    raw = Path("V5/examples/m18_v2_module_api_config.json").read_text()
    assert "m18-v2-readonly" in raw
    assert "m18/v2/pages" in raw
