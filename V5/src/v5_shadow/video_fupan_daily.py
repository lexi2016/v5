"""M12 Video FUPAN V5 private wrapper.

Review Core remains the only acquisition owner. This layer records an
immutable envelope and requires cold-reader verification before returning a
committed result.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
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


def _cold_verify(root: Path, date: str, run_id: str) -> None:
    env = dict(os.environ)
    code = (
        "from V5.src.v5_shadow.video_fupan_reader import read_committed_video; "
        "read_committed_video(sys.argv[1], sys.argv[2], sys.argv[3])"
    )
    result = subprocess.run([sys.executable, "-c", "import sys; " + code, str(root), date, run_id],
                            capture_output=True, text=True, env=env)
    if result.returncode != 0:
        raise VideoArtifactError("cold reader rejected committed run: " + result.stderr)


def run_video_fupan(trade_date: str, *, private_root: Path | str, tools: Any,
                    source_identity: str, tool_identity: str,
                    config_identity: str, allow_network: bool = False) -> dict[str, Any]:
    root = Path(private_root).absolute()
    if "v5" not in str(root).lower() or not re.fullmatch(r"\d{8}", str(trade_date)):
        raise VideoArtifactError("invalid M12 root/date")
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
    _write_json_atomic(run_root / "receipt.json", {"owner_run_id": owner_run_id, "manifest_sha256": manifest_sha})
    _cold_verify(root, trade_date, owner_run_id)
    return {"run_id": owner_run_id, "manifest": envelope}
