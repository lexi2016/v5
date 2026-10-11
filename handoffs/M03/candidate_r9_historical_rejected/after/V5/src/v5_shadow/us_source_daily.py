"""M03 temporary assembly implementation.

Keeps existing owner/transport guards. Provides cold-process adapters and
M03-only binding orchestration helpers.
"""
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os
import subprocess
import tempfile


@dataclass(frozen=True)
class USSourceRequest:
    trade_date: str
    capture_phase: str
    session: str
    cutoff: str
    source_root: Path
    snapshot_root: Path
    binding_root: Path
    owner_root: Path


def parse_utc(value):
    if not isinstance(value, str):
        raise ValueError("M03_TIME_REQUIRED")
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        raise ValueError("M03_TIMEZONE_REQUIRED")
    return dt.astimezone(timezone.utc)


def source_paths(snapshot_root, trade_date):
    root = Path(snapshot_root)
    return {
        "payload": root / "research/peripherals" / trade_date / "external_finance.json",
        "receipt": root / "receipts/research/peripherals" / trade_date / "external_finance.json",
        "manifest": root / "research/peripherals/manifest.json",
    }


def cold_collector_runner(request, runner):
    argv = [
        "--owner-root", str(request.owner_root),
        "--allow-network-capture",
        "--",
        "--data-root", str(request.snapshot_root),
        "--trade-date", request.trade_date,
        "--capture-phase", request.capture_phase,
    ]
    return runner(argv)


def select_capture(payload, request):
    rows = payload.get("us_session_captures", [])
    rows = [
        r for r in rows
        if r.get("us_session_date") == request.session
        and r.get("capture_phase") == request.capture_phase
    ]
    if len(rows) != 1:
        raise ValueError("M03_CAPTURE_AMBIGUOUS")
    return rows[0]


def create_binding(request, payload):
    if not isinstance(payload, dict) or not payload:
        raise ValueError("M03_PAYLOAD_NOT_VALIDATED")
    capture = select_capture(payload, request)
    if payload.get("trade_date") != request.trade_date:
        raise ValueError("M03_DATE_MISMATCH")
    if parse_utc(capture["captured_at"]) > parse_utc(request.cutoff):
        raise ValueError("M03_CAPTURE_AFTER_CUTOFF")

    paths = source_paths(request.snapshot_root, request.trade_date)
    hashes = {k: hashlib.sha256(v.read_bytes()).hexdigest() for k, v in paths.items()}
    return {
        "status": "VALIDATED_SOURCE_BINDING",
        "identity": capture,
        "market_snapshot": payload.get("market_snapshot", {}),
        "source_sha256": hashes,
    }


def persist_binding(binding, root):
    if binding.get("status") != "VALIDATED_SOURCE_BINDING":
        return binding
    version = hashlib.sha256(
        json.dumps(binding, sort_keys=True).encode()
    ).hexdigest()
    target = Path(root) / f"{version}.json"
    if target.exists():
        old = json.loads(target.read_text())
        if old != binding:
            raise ValueError("M03_BINDING_CONFLICT")
        return old
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=target.parent)
    with os.fdopen(fd, "w") as f:
        json.dump(binding, f, sort_keys=True)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, target)
    return json.loads(target.read_text())


def run_us_source(request, store, runner):
    payload = store.read_exact(request.trade_date, "external_finance")
    if payload is None:
        rc = cold_collector_runner(request, runner)
        if rc != 0:
            return {"status": "COLLECTOR_FAILED", "exit_code": rc}
        payload = store.read_exact(request.trade_date, "external_finance")
    if payload is None:
        return {"status": "SOURCE_MISSING"}
    return persist_binding(create_binding(request, payload), request.binding_root)
