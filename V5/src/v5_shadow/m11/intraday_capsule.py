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
_STORE_LOCK = threading.Lock()


def _digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def _safe_date(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("target_date_invalid")
    return date.fromisoformat(value).isoformat()


def _safe_root(root: str | Path) -> Path:
    raw = Path(root)
    if raw.is_absolute() is False:
        raise ValueError("root_must_be_absolute")
    if ".." in raw.parts:
        raise ValueError("root_escape")
    resolved = raw.resolve(strict=False)
    if resolved != raw.absolute().resolve(strict=False):
        raise ValueError("root_resolution_mismatch")
    return resolved


@dataclass(frozen=True)
class M11Slot:
    target_date: str
    slot: str
    cutoff: str
    trigger: str
    run_id: str

    def identity(self) -> str:
        _safe_date(self.target_date)
        if self.slot not in M11_SLOTS:
            raise ValueError("slot_invalid")
        return _digest(self.__dict__)


class IntradayCapsuleStore:
    """M11 producer/store/reader path.

    This is intentionally private storage. A caller cannot replace an existing
    artifact and readers always verify the identity and digest again.
    """

    def __init__(self, root: str | Path):
        self.root = _safe_root(root)

    def _artifact_dir(self, slot: M11Slot) -> Path:
        day = _safe_date(slot.target_date)
        target = self.root / day / slot.slot.replace(":", "") / slot.identity()
        if self.root not in target.parents:
            raise ValueError("artifact_outside_root")
        return target

    def write_success(self, slot: M11Slot, payload: dict, source_sha: str) -> dict:
        target = self._artifact_dir(slot)
        manifest = {
            "identity": slot.identity(),
            "slot": slot.__dict__,
            "source_sha": source_sha,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "payload_sha": _digest(payload),
            "state": "latest_success",
        }
        with _STORE_LOCK:
            if target.exists():
                raise FileExistsError("immutable artifact already exists")
            target.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(dir=str(target.parent)) as tmp:
                tmp_path = Path(tmp)
                (tmp_path / "payload.json").write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
                (tmp_path / "manifest.json").write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
                os.mkdir(target)
                os.replace(tmp_path / "payload.json", target / "payload.json")
                os.replace(tmp_path / "manifest.json", target / "manifest.json")
        return manifest

    def read_verified(self, slot: M11Slot) -> dict:
        target = self._artifact_dir(slot)
        manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
        payload = json.loads((target / "payload.json").read_text(encoding="utf-8"))
        if manifest.get("identity") != slot.identity():
            raise ValueError("artifact_identity_mismatch")
        if manifest.get("payload_sha") != _digest(payload):
            raise ValueError("payload_digest_mismatch")
        return payload
