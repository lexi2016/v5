"""Isolation contract tests. Execution on Mac remains NOT_RUN unless logs are attached."""
from v5_shadow import main_runtime


def test_commands_are_separate():
    assert callable(main_runtime.tick)
    assert callable(main_runtime.status)


def test_status_does_not_tick(monkeypatch):
    called=[]
    monkeypatch.setattr(main_runtime,'tick',lambda c: called.append(1))
    assert main_runtime.status({'runtime_root':'/tmp/nonexistent-v5-runtime'})['status']=='STOPPED'
    assert called==[]


def test_validate_requires_module_api():
    try:
        main_runtime.validate_config({'runtime_root':'x','composition':'y'})
    except ValueError as e:
        assert str(e)=='MODULE_API_CONFIG_REQUIRED'
    else:
        raise AssertionError('expected rejection')
