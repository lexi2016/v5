"""Source-distribution lifecycle from outside the checkout, synthetic input only."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.request import urlopen

BASE = Path(__file__).resolve().parents[1]


def test_source_runtime_without_pythonpath(tmp_path):
    data = tmp_path / "synthetic-data"
    data.mkdir()
    (data / ".v5-module-root").write_text("v5.module-root.v1:p0_test\n")
    runtime = tmp_path / "runtime"
    config = tmp_path / "config.json"
    config.write_text(json.dumps({
        "runtime_root": str(runtime), "composition": "unused-synthetic",
        "module_api": {"schema_version": "v5.module_api.v1",
                       "module_id": "p0_test", "release_id": "SYNTHETIC_CLOUD",
                       "data_root": str(data), "routes": []},
    }))
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)

    def command(action, check=True):
        result = subprocess.run(
            [sys.executable, "-I", "-B", str(BASE / "run_shadow.py"),
             "runtime", action, "--config", str(config)],
            cwd=tmp_path, env=env, capture_output=True, text=True, timeout=20,
        )
        if check:
            assert result.returncode == 0, result.stdout + result.stderr
            return json.loads(result.stdout)
        return result

    assert command("validate")["status"] == "CONFIGURATION_VALID"
    assert command("status")["status"] == "STOPPED"
    assert not runtime.exists()
    try:
        for _ in range(2):
            started = command("start")
            assert started["status"] == "STARTED"
            assert started["natural_verified"] is False
            port = started["identity"]["port"]
            with urlopen(f"http://127.0.0.1:{port}/__v5/module-health", timeout=3) as response:
                health = json.load(response)
            assert health["release_id"] == "SYNTHETIC_CLOUD"
            assert command("status")["status"] == "RUNNING"
            assert "RUNTIME_ALREADY_EXISTS" in command("start", check=False).stderr
            assert command("stop")["status"] == "STOPPED"
            for attempt in range(60):
                with socket.socket() as sock:
                    closed = sock.connect_ex(("127.0.0.1", port)) != 0
                if closed:
                    break
                time.sleep(.05)
            assert closed
            assert command("status")["status"] == "STOPPED"
        assert command("stop")["status"] == "ALREADY_STOPPED"
        assert list(data.iterdir()) == [data / ".v5-module-root"]
    finally:
        command("stop", check=False)
