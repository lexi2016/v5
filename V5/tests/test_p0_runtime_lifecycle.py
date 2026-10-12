from v5_shadow.main_runtime import validate_config, start, status, stop


def test_validate_registry_contract():
    result = validate_config({"runtime_root": "/tmp/v5-test", "composition": "composition.json"})
    assert result["status"] == "CONFIGURATION_VALID"


def test_lifecycle_identity(tmp_path):
    config = {"runtime_root": str(tmp_path), "composition": "composition.json"}
    started = start(config)
    assert started["status"] == "STARTED"
    current = status(config)
    assert current["identity"]["config_sha256"] == started["identity"]["config_sha256"]
    stopped = stop(config)
    assert stopped["status"] == "STOPPED"
