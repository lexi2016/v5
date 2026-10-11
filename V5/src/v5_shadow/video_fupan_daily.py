"""M12 Video FUPAN V5 private immutable chain.

The Review Core producer remains the owner of discovery/capture/ASR/video
algorithms. This layer only binds the approved owner into a V5 private root and
persists the returned evidence identity.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping


class VideoArtifactError(RuntimeError):
    pass


def _sha(value: Any) -> str:
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_dir = path.parent / ".staging"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp = tmp_dir / (path.name + ".tmp")
    tmp.write_text(json.dumps(dict(payload), ensure_ascii=False, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)


def _require_private_root(root: Path) -> Path:
    root = root.absolute()
    if "v5" not in str(root).lower():
        raise VideoArtifactError("M12 requires explicit V5 private root")
    return root


def _bind_review_core():
    """Import boundary kept in one place for the frozen vendor closure."""
    from .review_core.core import run_video
    from .review_core.config import ProducerConfig
    from .review_core.producer import AcquisitionTools
    return run_video, ProducerConfig, AcquisitionTools


def run_video_fupan(
    trade_date: str,
    *,
    private_root: Path | str,
    tools: Any,
    source_identity: str,
    tool_identity: str,
    config_identity: str,
    allow_network: bool = False,
) -> dict[str, Any]:
    root = _require_private_root(Path(private_root))
    run_video, ProducerConfig, AcquisitionTools = _bind_review_core()

    config = ProducerConfig(data_root=root)
    if Path(config.data_root).absolute() != root:
        raise VideoArtifactError("producer config escaped private root")
    if not isinstance(tools, AcquisitionTools):
        raise VideoArtifactError("explicit AcquisitionTools binding required")

    result = run_video(
        trade_date,
        mode="acquire",
        data_root=root,
        config=config,
        tools=tools,
        allow_network=allow_network,
    )
    if not isinstance(result, Mapping):
        raise VideoArtifactError("review_core returned non mapping")

    manifest = dict(result.get("manifest") or {})
    if not manifest:
        raise VideoArtifactError("missing producer manifest")

    identity = {
        "trade_date": str(trade_date),
        "bv_id": str(manifest.get("bv_id") or ""),
        "source_sha256": _sha(source_identity),
        "config_sha256": _sha(config_identity),
        "tool_sha256": _sha(tool_identity),
    }
    run_id = _sha(json.dumps(identity, sort_keys=True))
    run_root = root / "video_fupan" / "runs" / str(trade_date) / run_id

    persisted = dict(manifest)
    persisted["identity"] = identity
    persisted["run_id"] = run_id
    persisted["technical_state"] = "COMMITTED"
    persisted["business_status"] = manifest.get("status", "UNKNOWN")

    _write_json(run_root / "manifest.json", persisted)
    _write_json(run_root / "receipt.json", {"run_id": run_id, "manifest_sha256": _sha(json.dumps(persisted, sort_keys=True))})
    _write_json(root / "video_fupan" / str(trade_date) / "current.json", {"run_id": run_id})
    return {"run_id": run_id, "manifest": persisted}
