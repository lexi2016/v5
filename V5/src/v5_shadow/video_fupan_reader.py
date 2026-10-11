"""Independent M12 reader.

The reader never imports the producer. It reopens one committed run and checks
receipt, manifest identity and every declared artifact digest before exposing
video evidence.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class VideoReadError(RuntimeError):
    pass


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise VideoReadError(str(exc)) from exc
    if not isinstance(value, dict):
        raise VideoReadError("object required")
    return value


def _sha_file(path: Path) -> str:
    if not path.is_file():
        raise VideoReadError(f"missing artifact: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_committed_video(root: Path | str, trade_date: str, run_id: str) -> dict[str, Any]:
    base = Path(root).absolute() / "video_fupan" / "runs" / str(trade_date) / run_id
    manifest = _load(base / "manifest.json")
    receipt = _load(base / "receipt.json")

    if receipt.get("run_id") != run_id:
        raise VideoReadError("receipt run mismatch")
    if manifest.get("run_id") != run_id:
        raise VideoReadError("manifest run mismatch")

    identity = manifest.get("identity")
    if not isinstance(identity, dict):
        raise VideoReadError("missing identity")
    if hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest() != run_id:
        raise VideoReadError("identity mismatch")

    for artifact in manifest.get("artifact_refs", []) or []:
        if not isinstance(artifact, dict):
            raise VideoReadError("invalid artifact ref")
        path = base / str(artifact.get("path", ""))
        expected = str(artifact.get("sha256", ""))
        if expected and _sha_file(path) != expected:
            raise VideoReadError("artifact digest mismatch")

    return {"status": "VERIFIED", "manifest": manifest, "receipt": receipt}
