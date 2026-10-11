"""M03 cold reader slice.

Incremental addition: keeps existing orchestration outside this slice.
The child process only reads an already admitted snapshot.
"""
import json
import subprocess
import sys


def _reader_child_code():
    return r"""
import json
import sys
from pathlib import Path
try:
    sys.path.insert(0, sys.argv[1])
    from v5_shadow.cloud_us_collector import load_owner, verify, audit_modules, admit_output
    owner = Path(sys.argv[2])
    snapshot = Path(sys.argv[3])
    load_owner(owner)
    admit_output(snapshot, owner)
    from infrastructure.research_peripheral_store import ResearchPeripheralStore
    payload = None
    try:
        payload = ResearchPeripheralStore(snapshot).read_exact(sys.argv[4], "external_finance")
    finally:
        verify(owner)
        audit_modules()
    if payload is not None and not isinstance(payload, dict):
        raise TypeError("M03_READER_PAYLOAD_NOT_DICT")
    print(json.dumps({"payload": payload}, sort_keys=True))
except Exception as exc:
    print(json.dumps({"error": str(exc)}, sort_keys=True))
    raise
"""


def read_cold_snapshot(req, runner=subprocess.run):
    proc = runner(
        [
            sys.executable, "-I", "-B", "-c",
            _reader_child_code(),
            str(req.v5_src),
            str(req.owner_root),
            str(req.snapshot_root),
            req.trade_date,
        ],
        capture_output=True,
        text=True,
        timeout=300,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"M03_READER_FAILED rc={proc.returncode} stdout={proc.stdout} stderr={proc.stderr}"
        )
    try:
        envelope = json.loads(proc.stdout)
    except Exception as exc:
        raise ValueError(
            f"M03_READER_BAD_JSON stdout={proc.stdout} stderr={proc.stderr}"
        ) from exc
    if not isinstance(envelope, dict) or "payload" not in envelope:
        raise ValueError("M03_READER_CONTRACT_ERROR")
    payload = envelope["payload"]
    if payload is not None and not isinstance(payload, dict):
        raise ValueError("M03_READER_PAYLOAD_TYPE_ERROR")
    return payload
