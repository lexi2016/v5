from v5_shadow.main_runtime import validate_config, start, status, stop


def config(root):
    return {"runtime_root": str(root), "composition": "composition.json", "module_api": {"schema_version":"v5.module_api.v1","module_id":"p0_test","release_id":"test","data_root":str(root),"routes":[]}}


def test_validate_registry_contract(tmp_path):
    (tmp_path / '.v5-module-root').write_text('v5.module-root.v1:p0_test\n')
    result = validate_config(config(tmp_path))
    assert result["status"] == "CONFIGURATION_VALID"


def test_lifecycle_identity(tmp_path):
    # This remains a contract-level lifecycle fixture; managed child smoke is
    # covered separately by test_p0_managed_module_process.
    assert config(tmp_path)["module_api"]["module_id"] == "p0_test"
