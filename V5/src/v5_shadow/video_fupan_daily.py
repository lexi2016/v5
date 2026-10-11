"""M12 Video FUPAN V5 private immutable default chain.

This module owns orchestration only. The review_core producer remains the
algorithm owner. It materializes a private run, receipt and manifest.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping


@dataclass(frozen=True)
class VideoIdentity:
    trade_date: str
    bv_id: str
    source_sha256: str
    config_sha256: str
    tool_sha256: str


class VideoArtifactError(RuntimeError):
    pass


def _sha(value: Any) -> str:
    if isinstance(value, bytes):
        data = value
    else:
        data = str(value).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)


def run_video_fupan(
    trade_date: str,
    *,
    private_root: Path | str,
    acquire_video: Any,
    config_identity: str,
    tool_identity: str,
    source_identity: str,
) -> dict[str, Any]:
    """Run the first M12 default chain.

    acquire_video is the original Review Core owner callable. It is injected
    only as a binding seam; the caller cannot replace storage or verification.
    """
    root = Path(private_root).absolute()
    if "v5" not in str(root).lower():
        raise VideoArtifactError("M12 requires a V5 private root")

    result = acquire_video(trade_date)
    if not isinstance(result, Mapping):
        raise VideoArtifactError("producer returned non mapping")

    bv_id = str(result.get("bv_id") or "")
    media_sha = str(result.get("media_sha256") or "")
    if not bv_id or not media_sha:
        raise VideoArtifactError("producer evidence missing BV/media identity")

    identity = VideoIdentity(
        trade_date=str(trade_date),
        bv_id=bv_id,
        source_sha256=_sha(source_identity),
        config_sha256=_sha(config_identity),
        tool_sha256=_sha(tool_identity),
    )
    run_id = _sha(json.dumps(asdict(identity), sort_keys=True))
    run_root = root / "video_fupan" / "runs" / str(trade_date) / run_id

    manifest = {
        "identity": asdict(identity),
        "run_id": run_id,
        "status": "COMMITTED",
        "available_at": result.get("available_at"),
        "artifact_sha256": media_sha,
    }
    _write_json(run_root / "manifest.json", manifest)
    _write_json(run_root / "receipt.json", {"run_id": run_id, "status": "COMMITTED"})
    _write_json(root / "video_fupan" / str(trade_date) / "current.json", {"run_id": run_id})
    return {"run_id": run_id, "manifest": manifest}
