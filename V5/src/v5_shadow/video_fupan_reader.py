"""Independent M12 cold reader."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class VideoReadError(RuntimeError):
    pass


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise VideoReadError(f"missing file: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise VideoReadError(str(exc)) from exc
    if not isinstance(value, dict):
        raise VideoReadError("object required")
    return value


def _sha_bytes(path: Path) -> str:
    if not path.is_file():
        raise VideoReadError(f"missing artifact: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _safe_relative(path: str) -> Path:
    p = Path(path)
    if p.is_absolute() or ".." in p.parts:
        raise VideoReadError("unsafe artifact path")
    return p


def read_committed_video(root: Path | str, trade_date: str, run_id: str) -> dict[str, Any]:
    base = Path(root).absolute() / "video_fupan" / "runs" / str(trade_date) / run_id
    manifest_path = base / "manifest.json"
    receipt_path = base / "receipt.json"
    manifest = _load(manifest_path)
    receipt = _load(receipt_path)

    if receipt.get("run_id") != run_id or manifest.get("owner_run_id") != run_id:
        raise VideoReadError("run binding mismatch")
    if receipt.get("manifest_sha256") != _sha_bytes(manifest_path):
        raise VideoReadError("manifest bytes mismatch")

    owner = manifest.get("owner_manifest")
    if not isinstance(owner, dict):
        raise VideoReadError("missing owner manifest")

    refs = owner.get("artifact_refs") or []
    if not refs:
        raise VideoReadError("empty artifact refs")

    checked = []
    for ref in refs:
        if not isinstance(ref, dict):
            raise VideoReadError("invalid artifact ref")
        rel = _safe_relative(str(ref.get("path") or ""))
        sha = str(ref.get("sha256") or "")
        if len(sha) != 64:
            raise VideoReadError("invalid artifact sha")
        artifact = Path(root).absolute() / rel
        actual = _sha_bytes(artifact)
        if actual != sha:
            raise VideoReadError("artifact digest mismatch")
        checked.append(str(rel))

    return {"status": "VERIFIED", "run_id": run_id, "artifacts": checked, "manifest": manifest}
