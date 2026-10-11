"""Independent M12 reader.

Reads committed artifacts from disk and verifies receipt/manifest identity.
No producer imports and no writes.
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
        raise VideoReadError("artifact is not object")
    return value


def read_committed_video(root: Path | str, trade_date: str, run_id: str) -> dict[str, Any]:
    base = Path(root).absolute() / "video_fupan" / "runs" / str(trade_date) / run_id
    manifest = _load(base / "manifest.json")
    receipt = _load(base / "receipt.json")
    if receipt.get("run_id") != run_id or receipt.get("status") != "COMMITTED":
        raise VideoReadError("receipt mismatch")
    identity = manifest.get("identity")
    if not isinstance(identity, dict):
        raise VideoReadError("missing identity")
    expected = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    if expected != run_id:
        raise VideoReadError("identity mismatch")
    return {"status": "VERIFIED", "manifest": manifest, "receipt": receipt}
