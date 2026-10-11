"""M12 Video FUPAN V5 private wrapper.

The Review Core vendor package owns acquisition. This module only binds it,
records an envelope, and requires a later cold reader before exposure.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Mapping


class VideoArtifactError(RuntimeError):
    pass


def _sha_text(value: Any) -> str:
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()


def _sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_json_atomic(path: Path, payload: Mapping[str, Any]) -> str:
    raw = json.dumps(dict(payload), ensure_ascii=False, sort_keys=True).encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as f:
        f.write(raw)
        tmp = Path(f.name)
    os.replace(tmp, path)
    return _sha_bytes(raw)


def _bind_review_core():
    from V5.vendor.video_fupan_baseline.review_core.core import run_video
    from V5.vendor.video_fupan_baseline.review_core.config import ProducerConfig
    from V5.vendor.video_fupan_baseline.review_core.producer import AcquisitionTools
    return run_video, ProducerConfig, AcquisitionTools


def run_video_fupan(trade_date: str, *, private_root: Path | str, tools: Any,
                    source_identity: str, tool_identity: str,
                    config_identity: str, allow_network: bool = False) -> dict[str, Any]:
    root = Path(private_root).absolute()
    if not root.name or "v5" not in str(root).lower():
        raise VideoArtifactError("untrusted V5 root")
    if not re.fullmatch(r"\d{8}", str(trade_date)):
        raise VideoArtifactError("invalid date")
    run_video, ProducerConfig, AcquisitionTools = _bind_review_core()
    config = ProducerConfig(data_root=root, network_allowed=allow_network)
    if config.data_root != root or not isinstance(tools, AcquisitionTools):
        raise VideoArtifactError("invalid owner binding")
    result = run_video(trade_date, mode="acquire", data_root=root, config=config,
                       tools=tools, allow_network=allow_network)
    if not isinstance(result, Mapping):
        raise VideoArtifactError("owner result invalid")
    owner_manifest = dict(result.get("manifest") or {})
    owner_run_id = str(result.get("run_id") or owner_manifest.get("run_id") or "")
    if not owner_run_id:
        raise VideoArtifactError("missing owner run")
    envelope = {
        "owner_run_id": owner_run_id,
        "owner_status": result.get("status"),
        "owner_manifest": owner_manifest,
        "m12_identity": {
            "trade_date": trade_date,
            "source_sha256": _sha_text(source_identity),
            "tool_sha256": _sha_text(tool_identity),
            "config_sha256": _sha_text(config_identity),
        },
    }
    run_root = root / "video_fupan" / "runs" / trade_date / owner_run_id
    manifest_sha = _write_json_atomic(run_root / "manifest.json", envelope)
    _write_json_atomic(run_root / "receipt.json", {
        "owner_run_id": owner_run_id,
        "manifest_sha256": manifest_sha,
    })
    return {"run_id": owner_run_id, "manifest": envelope}
