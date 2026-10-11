from __future__ import annotations

import hashlib
import json
import os
import tempfile
import threading
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

M11_SLOTS = ("09:25", "09:35", "10:00", "11:30", "14:00", "15:00")
_STATES = {"REQUEST_IN_FLIGHT", "REQUEST_ATTEMPTED", "ATTEMPT_UNKNOWN", "FAILED_NO_REQUEST", "SUCCEEDED"}
_LOCK = threading.Lock()


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def _date(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("target_date_invalid")
    return date.fromisoformat(value).isoformat()


def _root(root: str | Path) -> Path:
    p = Path(root)
    if not p.is_absolute() or ".." in p.parts:
        raise ValueError("root_boundary_invalid")
    # Do not use resolved path as authorization. Existing symlink components are rejected.
    current = p
    parts = []
    while current != current.parent:
        parts.append(current)
        current = current.parent
    for item in reversed(parts):
        if item.exists() and item.is_symlink():
            raise ValueError("root_symlink_rejected")
    return p


@dataclass(frozen=True)
class M11Slot:
    target_date: str
    slot: str
    cutoff: str
    trigger: str
    run_id: str

    def identity(self) -> str:
        _date(self.target_date)
        if self.slot not in M11_SLOTS:
            raise ValueError("slot_invalid")
        return _digest(self.__dict__)


class IntradayCapsuleStore:
    """Private M11 artifact writer/reader.

    The business producer is expected to call this only after the original
    intraday owner has produced its evidence/receipt. This class never creates
    a research result itself.
    """

    def __init__(self, root: str | Path):
        self.root = _root(root)

    def _artifact_dir(self, slot: M11Slot) -> Path:
        target = self.root / _date(slot.target_date) / slot.slot.replace(":", "") / slot.identity()
        if self.root not in target.parents:
            raise ValueError("artifact_outside_root")
        return target

    def write_success(self, slot: M11Slot, payload: dict, source_sha: str) -> dict:
        target = self._artifact_dir(slot)
        manifest = {
            "identity": slot.identity(),
            "slot": slot.__dict__,
            "source_sha": source_sha,
            "payload_sha": _digest(payload),
            "created_at": datetime.utcnow().isoformat() + "Z",
            "state": "SUCCEEDED",
        }
        with _LOCK:
            if target.exists():
                raise FileExistsError("artifact_exists")
            target.parent.mkdir(parents=True, exist_ok=True)
            temp_dir = Path(tempfile.mkdtemp(prefix="m11-", dir=str(target.parent)))
            try:
                (temp_dir / "payload.json").write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
                (temp_dir / "manifest.json").write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
                os.link(temp_dir / "manifest.json", temp_dir / "manifest.link")
                os.mkdir(target)
                os.rename(temp_dir / "payload.json", target / "payload.json")
                os.rename(temp_dir / "manifest.json", target / "manifest.json")
            except Exception:
                if target.exists() and not (target / "manifest.json").exists():
                    try:
                        target.rmdir()
                    except OSError:
                        pass
                raise
            finally:
                if temp_dir.exists():
                    for child in temp_dir.iterdir():
                        child.unlink(missing_ok=True)
                    temp_dir.rmdir()
        return manifest

    def write_attempt(self, slot: M11Slot, state: str, error_code: str | None = None) -> dict:
        if state not in _STATES:
            raise ValueError("attempt_state_invalid")
        path = self.root / _date(slot.target_date) / "attempts" / slot.slot.replace(":", "")
        path.mkdir(parents=True, exist_ok=True)
        record = {"slot": slot.__dict__, "state": state, "error_code": error_code}
        (path / "latest_attempt.json").write_text(json.dumps(record, sort_keys=True), encoding="utf-8")
        return record

    def read_verified(self, slot: M11Slot) -> dict:
        target = self._artifact_dir(slot)
        manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
        payload = json.loads((target / "payload.json").read_text(encoding="utf-8"))
        if manifest.get("identity") != slot.identity():
            raise ValueError("artifact_identity_mismatch")
        if manifest.get("payload_sha") != _digest(payload):
            raise ValueError("payload_digest_mismatch")
        return payload
