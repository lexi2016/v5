"""M18 v2 bounded API binding tests.

These tests verify static route binding and read-only configuration contracts.
They do not rebuild bundles, publish data, execute owners, or run managers.
"""

import json
from pathlib import Path

from v5_shadow.module_api import _config


CONFIG_PATH = Path("V5/examples/m18_v2_module_api_config.json")


def _load_config():
    return json.loads(CONFIG_PATH.read_text())


def test_m18_routes_are_explicit_and_read_only():
    config = _load_config()

    assert config["schema_version"] == "v5.module_api.v1"
    assert config["module_id"] == "manager"

    routes = config["routes"]

    assert "/api/v4/manager/m18/v2" in routes
    assert "/api/v4/manager/m18/v2/pages" in routes
    assert len(routes) == len(set(routes))


def test_m18_binding_keeps_v2_identity_separate_from_publication():
    config = _load_config()

    binding = config["m18_v2_binding"]

    assert binding["identity"]["run_id"] == "46596b03c2ab4e29b1219fd2e5eb698f"
    assert len(binding["manifest_sha256"]) == 64
    assert len(binding["profile_sha256"]) == 64


def test_m18_config_rejects_missing_v2_binding():
    config = _load_config()
    config.pop("m18_v2_binding")

    try:
        _config(config)
    except (ValueError, KeyError):
        return

    raise AssertionError("missing M18 binding must not become READY")


def test_m18_config_keeps_pages_route_bounded():
    config = _load_config()

    assert config["routes"] == [
        "/api/v4/manager/m18/v2",
        "/api/v4/manager/m18/v2/pages",
    ]
