"""M12 Video FUPAN V5 private wrapper.

Review Core remains the only acquisition owner. This layer records immutable
attempts, promotes only cold-reader verified runs, and reuses committed runs
for identical owner output.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping

from .video_fupan_reader import VideoReadError, _read_owner_evidence
from .video_fupan_store import (
    VideoStoreError,
    ensure_date_run,
    ensure_private_root,
    publish_latest_success,
    safe_replace_json,
    stage_attempt,
)


class VideoArtifactError(RuntimeError):
    pass


def _sha_text(value: Any) -> str:
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()


def _sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _bind_review_core():
    from V5.vendor.video_fupan_baseline.review_core.core import run_video
    from V5.vendor.video_fupan_baseline.review_core.config import ProducerConfig
    from V5.vendor.video_fupan_baseline.review_core.producer import AcquisitionTools
    return run_video, ProducerConfig, AcquisitionTools


def _cold_verify(root: Path, date: str, run_id: str) -> dict[str, Any]:
    code = ("import json; from pathlib import Path; "
            "from V5.src.v5_shadow.video_fupan_reader import read_committed_video; "
            "print(json.dumps(read_committed_video(Path(__import__('sys').argv[1]), __import__('sys').argv[2], __import__('sys').argv[3])))")
    result = subprocess.run([sys.executable, "-c", code, str(root), date, run_id], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise VideoArtifactError("cold reader rejected committed run: " + result.stderr + result.stdout)
    return json.loads(result.stdout)


def _promote_verified(root: Path, date: str, run_id: str, checked: Mapping[str, Any]) -> bool:
    owner = checked["manifest"]["owner_manifest"]
    # Discovery status and current_advanced are not acquisition success. The
    # first failed owner run can have TARGET_BV_LOCKED/current_advanced=True.
    eligible = (checked["owner_receipt"].get("status") == "ACQUIRED"
                and owner.get("discovery_status") == "TARGET_BV_LOCKED"
                and owner.get("capture_status") in {"CAPTURED", "REUSED_CONTENT"}
                and owner.get("asr_status") == "ASR_REVIEW_REQUIRED")
    if eligible:
        publish_latest_success(root, date, run_id)
    return eligible


def _existing_run(root: Path, date: str, run_id: str) -> bool:
    return (root / "video_fupan" / "runs" / date / run_id / "manifest.json").is_file() and (root / "video_fupan" / "runs" / date / run_id / "receipt.json").is_file()


def run_video_fupan(trade_date: str, *, private_root: Path | str, tools: Any,
                    source_identity: str, tool_identity: str,
                    config_identity: str, allow_network: bool = False) -> dict[str, Any]:
    try:
        root = ensure_private_root(private_root)
        run_video, ProducerConfig, AcquisitionTools = _bind_review_core()
        config = ProducerConfig(data_root=root, network_allowed=allow_network)
        ensure_date_run(trade_date, "a")
        if config.data_root != root or not isinstance(tools, AcquisitionTools):
            raise VideoArtifactError("invalid owner binding")

        result = run_video(trade_date, mode="acquire", data_root=root, config=config, tools=tools, allow_network=allow_network)
        if not isinstance(result, Mapping):
            raise VideoArtifactError("owner result invalid")
        owner_manifest = dict(result.get("manifest") or {})
        owner_run_id = str(result.get("run_id") or owner_manifest.get("run_id") or "")
        if not owner_run_id:
            raise VideoArtifactError("missing owner run")
        ensure_date_run(trade_date, owner_run_id)
        _, owner_receipt_sha = _read_owner_evidence(root, trade_date, owner_run_id, owner_manifest)

        if _existing_run(root, trade_date, owner_run_id):
            checked = _cold_verify(root, trade_date, owner_run_id)
            promoted = _promote_verified(root, trade_date, owner_run_id, checked)
            return {"run_id": owner_run_id, "manifest": checked["manifest"], "reused": True, "promoted": promoted}

        attempt_id = hashlib.sha256(json.dumps({"date": trade_date, "owner_run_id": owner_run_id, "source": source_identity, "tool": tool_identity, "config": config_identity}, sort_keys=True).encode("utf-8")).hexdigest()
        attempt = stage_attempt(root, trade_date, attempt_id)
        attempt_id = attempt.name
        envelope = {"owner_run_id": owner_run_id, "owner_status": result.get("status"), "owner_manifest": owner_manifest, "owner_receipt_sha256": owner_receipt_sha, "attempt_id": attempt_id, "m12_identity": {"trade_date": trade_date, "source_sha256": _sha_text(source_identity), "tool_sha256": _sha_text(tool_identity), "config_sha256": _sha_text(config_identity)}}
        safe_replace_json(attempt / "manifest.json", envelope)
        manifest_sha = _sha_file(attempt / "manifest.json")
        safe_replace_json(attempt / "receipt.json", {"owner_run_id": owner_run_id, "attempt_id": attempt_id, "manifest_sha256": manifest_sha})
        committed = root / "video_fupan" / "runs" / trade_date / owner_run_id
        committed.parent.mkdir(parents=True, exist_ok=True)
        if committed.exists():
            raise VideoArtifactError("immutable committed run already exists")
        # The reader layout is unchanged; expose both files together, never a
        # half-committed run that blocks the next same-input retry.
        os.replace(attempt, committed)
        checked = _cold_verify(root, trade_date, owner_run_id)
        promoted = _promote_verified(root, trade_date, owner_run_id, checked)
        return {"run_id": owner_run_id, "manifest": envelope, "attempt_id": attempt_id, "promoted": promoted}
    except (VideoStoreError, VideoReadError) as exc:
        raise VideoArtifactError(str(exc)) from exc

