"""Real managed module_api process isolation tests.

Task-owned fixtures only. Uses real module_process and real runtime refusal paths.
"""
import json
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

from v5_shadow import main_runtime


def _module_fixture(tmp_path, module_id="p0_test"):
    data_root = tmp_path / (module_id + "-data")
    data_root.mkdir()
    (data_root / ".v5-module-root").write_text("v5.module-root.v1:" + module_id + "\n")
    cfg = tmp_path / (module_id + ".json")
    cfg.write_text(json.dumps({
        "schema_version": "v5.module_api.v1",
        "module_id": module_id,
        "release_id": "managed-process-test",
        "data_root": str(data_root),
        "routes": [],
    }))
    return cfg


def _start(cfg, port=0):
    proc = subprocess.Popen([sys.executable, "-m", "v5_shadow.module_process", "--config", str(cfg), "--port", str(port)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    ready = json.loads(proc.stdout.readline())
    assert ready["status"] == "READY"
    return proc, ready


def _wait_closed(port):
    for _ in range(50):
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return
        time.sleep(0.05)
    raise AssertionError("listener_not_released")


def test_real_start_ready_health_identity_stop(tmp_path):
    proc, ready = _start(_module_fixture(tmp_path))
    try:
        with urlopen(f"http://127.0.0.1:{ready['port']}/__v5/module-health", timeout=3) as response:
            body = json.loads(response.read())
        assert response.status == 200
        assert body["module_id"] == "p0_test"
        assert proc.pid == ready["pid"]
    finally:
        proc.terminate()
        proc.wait(timeout=5)
    _wait_closed(ready["port"])


def test_duplicate_port_is_rejected_by_real_server(tmp_path):
    first, ready = _start(_module_fixture(tmp_path))
    try:
        second = subprocess.Popen([sys.executable, "-m", "v5_shadow.module_process", "--config", str(_module_fixture(tmp_path)), "--port", str(ready["port"])], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        assert second.wait(timeout=5) != 0
    finally:
        first.terminate()
        first.wait(timeout=5)


def test_wrong_identity_runtime_stop_is_rejected(tmp_path):
    root = tmp_path / "runtime"
    cfg = {"runtime_root": str(root), "composition": "unused", "module_api": {"schema_version": "v5.module_api.v1", "module_id": "p0_test", "release_id": "managed-process-test", "data_root": str(tmp_path), "routes": []}}
    main_runtime.start(cfg)
    wrong = dict(cfg)
    wrong["module_api"] = dict(cfg["module_api"])
    wrong["module_api"]["release_id"] = "wrong-release"
    try:
        try:
            main_runtime.stop(wrong)
        except ValueError as error:
            assert str(error) == "RUNTIME_IDENTITY_MISMATCH"
        else:
            raise AssertionError("expected identity rejection")
        assert main_runtime.status(cfg)["status"] == "RUNNING"
    finally:
        main_runtime.stop(cfg)


def test_no_owner_or_producer_import_contract():
    import ast
    from v5_shadow import module_process
    tree = ast.parse(Path(module_process.__file__).read_text())
    names = [n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
    assert not any(n and ("owner" in n or "producer" in n) for n in names)
