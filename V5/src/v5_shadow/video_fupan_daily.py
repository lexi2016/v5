"""M12 Video FUPAN V5 private immutable chain."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


class VideoArtifactError(RuntimeError):
    pass


def _sha(value: Any) -> str:
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), ensure_ascii=False, sort_keys=True), encoding="utf-8")


def _bind_review_core():
    from V5.vendor.video_fupan_baseline.review_core.core import run_video
    from V5.vendor.video_fupan_baseline.review_core.config import ProducerConfig
    from V5.vendor.video_fupan_baseline.review_core.producer import AcquisitionTools
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
    root = Path(private_root).absolute()
    if "v5" not in str(root).lower():
        raise VideoArtifactError("M12 requires V5 private root")

    run_video, ProducerConfig, AcquisitionTools = _bind_review_core()
    config = ProducerConfig(data_root=root, network_allowed=allow_network)
    if config.data_root != root:
        raise VideoArtifactError("config root mismatch")
    if not isinstance(tools, AcquisitionTools):
        raise VideoArtifactError("AcquisitionTools required")

    result = run_video(trade_date, mode="acquire", data_root=root, config=config, tools=tools, allow_network=allow_network)
    if not isinstance(result, Mapping):
        raise VideoArtifactError("owner returned non mapping")

    owner_manifest = dict(result.get("manifest") or {})
    if not owner_manifest:
        raise VideoArtifactError("missing owner manifest")

    envelope = {
        "owner_run_id": str(result.get("run_id") or ""),
        "owner_status": result.get("status"),
        "owner_manifest": owner_manifest,
        "m12_identity": {
            "trade_date": str(trade_date),
            "source_sha256": _sha(source_identity),
            "config_sha256": _sha(config_identity),
            "tool_sha256": _sha(tool_identity),
        },
    }
    run_id = str(envelope["owner_run_id"] or _sha(json.dumps(envelope["m12_identity"], sort_keys=True)))
    run_root = root / "video_fupan" / "runs" / str(trade_date) / run_id
    _write_json(run_root / "manifest.json", envelope)
    _write_json(run_root / "receipt.json", {"run_id": run_id, "manifest_sha256": _sha((run_root / 'manifest.json').read_bytes())})
    return {"run_id": run_id, "manifest": envelope}
