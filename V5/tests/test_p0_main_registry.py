from v5_shadow.main_registry import MODULE_REGISTRY, registry_by_id, validate_registry


def test_registry_has_eighteen_modules():
    validate_registry()
    assert len(MODULE_REGISTRY) == 18


def test_manager_dependencies_are_explicit():
    manager = registry_by_id()["M18_MANAGER"]
    assert manager.dependencies == (
        "M13_ANNOUNCEMENT",
        "M14_REBOUND",
        "M15_US_MAPPING",
    )


def test_not_ready_is_not_claimed_ready():
    assert registry_by_id()["M12_VIDEO_FUPAN"].status == "NOT_READY"
