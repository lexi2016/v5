from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


M11_SLOTS = ("09:25", "09:35", "10:00", "11:30", "14:00", "15:00")


@dataclass(frozen=True)
class M11Slot:
    target_date: str
    slot: str
    cutoff: str
    trigger: str
    run_id: str

    def identity(self) -> str:
        body = json.dumps(self.__dict__, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(body.encode("utf-8")).hexdigest()


class IntradayCapsuleStore:
    """Private immutable M11 artifact store.

    The store deliberately accepts a supplied capsule root only. HTTP/API layers
    must not pass arbitrary filesystem roots into this class.
    """

    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()

    def _artifact_dir(self, slot: M11Slot) -> Path:
        return self.root / slot.target_date / slot.slot.replace(":", "") / slot.identity()

    def write_success(self, slot: M11Slot, payload: dict, source_sha: str) -> dict:
        target = self._artifact_dir(slot)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            raise FileExistsError("immutable artifact already exists")

        manifest = {
            "identity": slot.identity(),
            "slot": slot.__dict__,
            "source_sha": source_sha,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "payload_sha": hashlib.sha256(
                json.dumps(payload, sort_keys=True).encode("utf-8")
            ).hexdigest(),
        }

        with tempfile.TemporaryDirectory(dir=str(target.parent)) as tmp:
            tmp_path = Path(tmp)
            (tmp_path / "payload.json").write_text(
                json.dumps(payload, ensure_ascii=False, sort_keys=True), encoding="utf-8"
            )
            (tmp_path / "manifest.json").write_text(
                json.dumps(manifest, ensure_ascii=False, sort_keys=True), encoding="utf-8"
            )
            os.replace(tmp_path, target)
        return manifest

    def read_verified(self, slot: M11Slot) -> dict:
        target = self._artifact_dir(slot)
        manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
        payload = json.loads((target / "payload.json").read_text(encoding="utf-8"))
        actual = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
        if actual != manifest["payload_sha"]:
            raise ValueError("payload digest mismatch")
        if manifest["identity"] != slot.identity():
            raise ValueError("artifact identity mismatch")
        return payload
