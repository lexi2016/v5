"""M12 cold reader. No producer import and no writes."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


class VideoReadError(RuntimeError):
    pass


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise VideoReadError(f"missing {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise VideoReadError(f"cannot read {path}") from exc
    if not isinstance(value, dict):
        raise VideoReadError("object required")
    return value


def _sha_file(path: Path) -> str:
    if not path.is_file():
        raise VideoReadError(f"missing artifact {path}")
    if path.is_symlink():
        raise VideoReadError(f"symlink artifact rejected: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _relative_ref(value: str) -> Path:
    p = Path(value)
    if p.is_absolute() or ".." in p.parts:
        raise VideoReadError("unsafe artifact path")
    return p


def _ensure_no_symlink_path(root: Path, path: Path) -> None:
    try:
        relative = path.relative_to(root)
    except ValueError as exc:
        raise VideoReadError("artifact outside trusted root") from exc
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise VideoReadError(f"symlink path component rejected: {current}")


def _read_owner_evidence(root: Path, trade_date: str, run_id: str,
                         owner: dict[str, Any]) -> tuple[dict[str, Any], str]:
    """Bind the exact immutable owner receipt, never the mutable current pointer."""
    if not re.fullmatch(r"\d{8}", trade_date) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,255}", run_id):
        raise VideoReadError("invalid owner date/run")
    base = root / "review" / trade_date / "runs" / run_id
    for path in (base / "manifest.json", base / "receipt.json"):
        _ensure_no_symlink_path(root, path)
    manifest_path = base / "manifest.json"
    receipt_path = base / "receipt.json"
    persisted = _load(manifest_path)
    receipt = _load(receipt_path)
    if persisted != owner:
        raise VideoReadError("owner manifest does not match persisted evidence")
    if (owner.get("schema_version") != "VideoEvidenceV1"
            or owner.get("run_id") != run_id
            or owner.get("trade_date") != trade_date
            or owner.get("target_trade_date") != trade_date):
        raise VideoReadError("owner manifest identity mismatch")
    if (receipt.get("schema_version") != "ReviewCoreReceiptV1"
            or receipt.get("run_id") != run_id
            or receipt.get("trade_date") != trade_date):
        raise VideoReadError("owner receipt identity mismatch")
    if receipt.get("manifest_sha256") != _sha_file(manifest_path):
        raise VideoReadError("owner receipt manifest bytes mismatch")
    return receipt, _sha_file(receipt_path)


def read_committed_video(root: Path | str, trade_date: str, run_id: str) -> dict[str, Any]:
    root = Path(root).absolute()
    if not re.fullmatch(r"\d{8}", trade_date) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,255}", run_id):
        raise VideoReadError("invalid date/run")
    base = root / "video_fupan" / "runs" / trade_date / run_id
    manifest_path = base / "manifest.json"
    receipt_path = base / "receipt.json"
    _ensure_no_symlink_path(root, manifest_path)
    _ensure_no_symlink_path(root, receipt_path)
    manifest = _load(manifest_path)
    receipt = _load(receipt_path)
    if receipt.get("owner_run_id") != run_id or manifest.get("owner_run_id") != run_id:
        raise VideoReadError("run mismatch")
    if receipt.get("manifest_sha256") != _sha_file(manifest_path):
        raise VideoReadError("manifest bytes mismatch")
    owner = manifest.get("owner_manifest")
    if not isinstance(owner, dict):
        raise VideoReadError("owner manifest missing")
    refs = owner.get("artifact_refs")
    if not isinstance(refs, list) or not refs:
        raise VideoReadError("empty artifact refs")
    checked = []
    for item in refs:
        if not isinstance(item, dict):
            raise VideoReadError("bad ref")
        sha = str(item.get("sha256") or "")
        if len(sha) != 64:
            raise VideoReadError("bad sha")
        rel = _relative_ref(str(item.get("path") or ""))
        artifact = root / rel
        _ensure_no_symlink_path(root, artifact)
        if _sha_file(artifact) != sha:
            raise VideoReadError("artifact mismatch")
        checked.append(str(rel))
    owner_receipt, receipt_sha = _read_owner_evidence(root, trade_date, run_id, owner)
    # Pre-upgrade envelopes did not pin receipt bytes. They still require the
    # exact canonical receipt/date/run/manifest above; never rewrite history.
    if "owner_receipt_sha256" in manifest and manifest["owner_receipt_sha256"] != receipt_sha:
        raise VideoReadError("owner receipt bytes mismatch")
    return {"status": "VERIFIED", "run_id": run_id, "artifacts": checked, "manifest": manifest, "owner_receipt": owner_receipt}

