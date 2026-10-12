"""V5 P0 runtime lifecycle.

This is orchestration only. It does not execute producers from status and does
not replace owner adapters or the existing ledger.
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import time
from pathlib import Path

from .digests import canonical_bytes, sha256_json
from .main_registry import registration_snapshot, validate_registry


MARKER = "v5-main-runtime.v1"


def load_config(path: str) -> dict:
    value = json.loads(Path(path).read_bytes())
    if not isinstance(value, dict):
        raise ValueError("CONFIG_INVALID")
    return value


def validate_config(config: dict) -> dict:
    validate_registry()
    required = ("runtime_root", "composition")
    if any(key not in config for key in required):
        raise ValueError("RUNTIME_CONFIG_REQUIRED")
    return {
        "status": "CONFIGURATION_VALID",
        "registry": registration_snapshot(),
        "config_sha256": sha256_json(config),
        "natural_verified": False,
    }


def _identity(config: dict) -> dict:
    return {
        "marker": MARKER,
        "pid": os.getpid(),
        "config_sha256": sha256_json(config),
        "started_at": time.time(),
    }


def start(config: dict) -> dict:
    root = Path(config["runtime_root"])
    root.mkdir(parents=True, exist_ok=True)
    pid_file = root / "runtime.json"
    if pid_file.exists():
        raise ValueError("RUNTIME_ALREADY_EXISTS")
    identity = _identity(config)
    pid_file.write_bytes(canonical_bytes(identity))
    return {"status": "STARTED", "identity": identity, "natural_verified": False}


def status(config: dict) -> dict:
    path = Path(config["runtime_root"]) / "runtime.json"
    if not path.is_file():
        return {"status": "STOPPED", "natural_verified": False}
    identity = json.loads(path.read_bytes())
    alive = False
    try:
        os.kill(int(identity["pid"]), 0)
        alive = True
    except OSError:
        pass
    return {
        "status": "RUNNING" if alive else "STALE",
        "identity": identity,
        "code_config_sha256": sha256_json(config),
        "natural_verified": False,
    }


def stop(config: dict) -> dict:
    path = Path(config["runtime_root"]) / "runtime.json"
    if not path.is_file():
        return {"status": "ALREADY_STOPPED", "natural_verified": False}
    identity = json.loads(path.read_bytes())
    if identity.get("marker") != MARKER or identity.get("config_sha256") != sha256_json(config):
        raise ValueError("RUNTIME_IDENTITY_MISMATCH")
    try:
        os.kill(int(identity["pid"]), signal.SIGTERM)
    except ProcessLookupError:
        pass
    path.unlink()
    return {"status": "STOPPED", "identity": identity, "natural_verified": False}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("validate", "start", "status", "stop"))
    parser.add_argument("--config", required=True)
    args = parser.parse_args(argv)
    config = load_config(args.config)
    result = {"validate": validate_config, "start": start, "status": status, "stop": stop}[args.command](config)
    print(canonical_bytes(result).decode())


if __name__ == "__main__":
    main()
