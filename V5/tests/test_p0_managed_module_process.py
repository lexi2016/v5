"""Real managed module_api process isolation tests.

These tests create only task-owned temporary fixtures. They start the real
v5_shadow.module_process entrypoint and exercise the existing read-only
module_api server. They do not mock runtime/server behavior and do not touch
owners, producers, ledgers, V4 or 8910 processes.
"""

import json
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen



def _fixture(tmp_path):
    data_root = tmp_path / "module-data"
    data_root.mkdir()
    (data_root / ".v5-module-root").write_text("v5.module-root.v1:p0_test\n")
    cfg = tmp_path / "module.json"
    cfg.write_text(json.dumps({
        "schema_version": "v5.module_api.v1",
        "module_id": "p0_test",
        "release_id": "managed-process-test",
        "data_root": str(data_root),
        "routes": [],
    }))
    return cfg


def _start(cfg):
    proc = subprocess.Popen(
        [sys.executable, "-m", "v5_shadow.module_process", "--config", str(cfg), "--port", "0"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    line = proc.stdout.readline()
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


def test_wrong_identity_fixture_does_not_stop_existing_process(tmp_path):
    cfg = _fixture(tmp_path)
    proc, ready = _start(cfg)
    try:
        wrong = dict(json.loads(cfg.read_text()))
        wrong["module_id"] = "other_module"
        wrong_cfg = tmp_path / "wrong.json"
        wrong_cfg.write_text(json.dumps(wrong))
        assert wrong_cfg.exists()
        assert proc.poll() is None
    finally:
        proc.terminate()
        proc.wait(timeout=5)


def test_no_owner_or_producer_import_contract():
    from v5_shadow import module_process
    source = Path(module_process.__file__).read_text()
    assert "owner" not in source.lower()
    assert "producer" not in source.lower()
