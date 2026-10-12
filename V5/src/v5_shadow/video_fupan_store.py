"""M12 immutable run storage primitives.

No producer logic lives here. The module provides path and lifecycle guards for
wrapper code: staging, attempt separation and latest-success protection.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Mapping


class VideoStoreError(RuntimeError):
    pass


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def ensure_private_root(root: Path | str) -> Path:
    p = Path(root).absolute()
    if "v5" not in str(p).lower():
        raise VideoStoreError("untrusted V5 root")
    for part in p.parts:
        if part == "..":
            raise VideoStoreError("parent escape")
    return p


def ensure_date_run(date: str, run_id: str) -> None:
    if not re.fullmatch(r"\d{8}", str(date)):
        raise VideoStoreError("invalid date")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", str(run_id)):
        raise VideoStoreError("invalid run")
    if len(str(run_id)) > 256:
        raise VideoStoreError("run too long")


def safe_replace_json(path: Path, payload: Mapping[str, Any]) -> str:
    raw = json.dumps(dict(payload), ensure_ascii=False, sort_keys=True).encode("utf-8")
    _ensure_parent(path)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as f:
        f.write(raw)
        tmp = Path(f.name)
    if path.exists():
        raise VideoStoreError("immutable target already exists")
    os.replace(tmp, path)
    return sha_bytes(raw)


def stage_attempt(root: Path | str, date: str, attempt_id: str) -> Path:
    root = ensure_private_root(root)
    ensure_date_run(date, attempt_id)
    p = root / "video_fupan" / "attempts" / date / attempt_id
    if p.exists():
        raise VideoStoreError("attempt already exists")
    p.mkdir(parents=True, exist_ok=False)
    return p


def publish_latest_success(root: Path | str, date: str, run_id: str) -> None:
    root = ensure_private_root(root)
    ensure_date_run(date, run_id)
    current = root / "video_fupan" / date / "latest_success.json"
    _ensure_parent(current)
    if current.exists():
        existing = json.loads(current.read_text(encoding="utf-8"))
        if not isinstance(existing, dict) or not existing.get("run_id"):
            raise VideoStoreError("invalid latest_success pointer")
    current.write_text(json.dumps({"run_id": run_id}), encoding="utf-8")
