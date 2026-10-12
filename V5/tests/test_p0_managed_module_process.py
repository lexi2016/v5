"""Real managed module_api process isolation tests.

These tests create only task-owned temporary fixtures. They start the real
v5_shadow.module_process entrypoint and exercise the existing read-only
module_api server. They do not mock server behavior and do not touch V4/8910
or unrelated processes.
"""

import ast
import json
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen


def _fixture(tmp_path, module_id="p0_test"):
    data_root = tmp_path / "module-data"
    data_root.mkdir()
    (data_root / ".v5-module-root").write_text(f"v5.module-root.v1:{module_id}\n")
    cfg = tmp_path / f"{module_id}.json"
    cfg.write_text(json.dumps({
        "schema_version": "v5.module_api.v1",
        "module_id": module_id,
        "release_id": "managed-process-test",
        "data_root": str(data_root),
        "routes": [],
    }))
    return cfg


def _start(cfg, port=0):
    proc = subprocess.Popen(
        [sys.executable, "-m", "v5_shadow.module_process", "--config", str(cfg), "--port", str(port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    line = proc.stdout.readline()
    if not line:
        raise AssertionError(proc.stderr.read())
    ready = json.loads(line)
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
    cfg = _fixture(tmp_path)
    proc, ready = _start(cfg)
    try:
        assert proc.pid == ready["pid"]
        with urlopen(f"http://127.0.0.1:{ready['port']}/__v5/module-health", timeout=3) as response:
            body = json.loads(response.read())
        assert response.status == 200
        assert body["module_id"] == "p0_test"
        assert body["release_id"] == "managed-process-test"
    finally:
        proc.terminate()
        proc.wait(timeout=5)
    _wait_closed(ready["port"])


def test_duplicate_port_is_rejected_by_real_server(tmp_path):
    cfg = _fixture(tmp_path)
    first, ready = _start(cfg)
    second = None
    try:
        second = subprocess.Popen(
            [sys.executable, "-m", "v5_shadow.module_process", "--config", str(cfg), "--port", str(ready["port"])],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        assert second.wait(timeout=5) != 0
    finally:
        first.terminate()
        first.wait(timeout=5)
        if second and second.poll() is None:
            second.terminate()
            second.wait(timeout=5)


def test_wrong_identity_is_rejected_by_runtime_stop(tmp_path):
    from v5_shadow import main_runtime

    cfg = _fixture(tmp_path)
    runtime_root = tmp_path / "runtime"
    runtime_cfg = {
        "runtime_root": str(runtime_root),
        "composition": str(tmp_path / "composition.json"),
        "module_api": json.loads(cfg.read_text()),
        "daily": {"enabled": False},
    }
    started = main_runtime.start(runtime_cfg)
    wrong = dict(runtime_cfg)
    wrong["runtime_root"] = str(tmp_path / "other-runtime")
    try:
        assert main_runtime.status(runtime_cfg)["status"] == "RUNNING"
        try:
            main_runtime.stop(wrong)
        except ValueError as exc:
            assert str(exc) == "RUNTIME_ALREADY_STOPPED"
        assert main_runtime.status(runtime_cfg)["status"] == "RUNNING"
    finally:
        main_runtime.stop(runtime_cfg)
        assert started["identity"]["module_pid"]


def test_no_owner_or_producer_execution_contract():
    from v5_shadow import module_process

    tree = ast.parse(Path(module_process.__file__).read_text())
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        if isinstance(node, ast.ImportFrom):
            imported.append(node.module or "")
    assert not any(name.startswith("v5_shadow.owner") for name in imported)
    assert not any(name.startswith("v5_shadow.producer") for name in imported)
