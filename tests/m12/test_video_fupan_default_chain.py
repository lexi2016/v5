from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from V5.src.v5_shadow.video_fupan_daily import run_video_fupan
from V5.src.v5_shadow.video_fupan_reader import read_committed_video, VideoReadError
from V5.src.v5_shadow.video_fupan_store import VideoStoreError, publish_latest_success

DATE = "20261011"


class SimulatedOwner:
    def __init__(self):
        self.capture_count = 0
        self.asr_count = 0

    def tools(self):
        from V5.vendor.video_fupan_baseline.review_core.producer import AcquisitionTools

        def discover(_date, _config):
            return [{"bv_id": "BV_SIMULATED", "title": "10.11 A股复盘 主线行情思路 SIMULATED", "upload_date": DATE, "uploader": "比巴卜作手", "target_trade_date": DATE}]

        def capture(_selection, work_dir, _config):
            self.capture_count += 1
            p = work_dir / "media" / "simulated.mp4"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b"SIMULATED_MEDIA")
            return {"status": "CAPTURED", "media_path": str(p), "downloaded": True, "access_status": "SIMULATED"}

        def asr(_media, work_dir, _config):
            self.asr_count += 1
            p = work_dir / "asr"
            p.mkdir(parents=True, exist_ok=True)
            raw = p / "a.funasr_raw.txt"
            seg = p / "a.funasr_segments.csv"
            raw.write_text("SIMULATED", encoding="utf-8")
            seg.write_text("start,end,text\n0,1,SIMULATED", encoding="utf-8")
            return {"status": "ASR_REVIEW_REQUIRED", "raw_path": str(raw), "segments_path": str(seg)}

        return AcquisitionTools(discover=discover, capture=capture, asr=asr)


def _run(tmp_path, owner=None):
    owner = owner or SimulatedOwner()
    return owner, run_video_fupan(DATE, private_root=tmp_path / "v5_private", tools=owner.tools(), source_identity="s", tool_identity="t", config_identity="c", allow_network=True)


def test_same_input_reuses_committed_run_without_new_capture_asr(tmp_path: Path):
    owner, first = _run(tmp_path)
    _, second = _run(tmp_path, owner)
    assert second["run_id"] == first["run_id"]
    assert owner.capture_count == 1
    assert owner.asr_count == 1
    assert read_committed_video(tmp_path / "v5_private", DATE, second["run_id"])["status"] == "VERIFIED"


def test_failed_publish_keeps_old_success_and_old_run_readable(tmp_path: Path):
    _, result = _run(tmp_path)
    root = tmp_path / "v5_private"
    latest = root / "video_fupan" / DATE / "latest_success.json"
    assert json.loads(latest.read_text())["run_id"] == result["run_id"]
    with pytest.raises(VideoStoreError):
        publish_latest_success(root, DATE, "bad/path")
    assert json.loads(latest.read_text())["run_id"] == result["run_id"]
    assert read_committed_video(root, DATE, result["run_id"])["status"] == "VERIFIED"


def test_existing_valid_run_symlink_artifact_is_rejected(tmp_path: Path):
    _, result = _run(tmp_path)
    root = tmp_path / "v5_private"
    run = root / "video_fupan" / "runs" / DATE / result["run_id"]
    payload = json.loads((run / "manifest.json").read_text())
    ref = payload["owner_manifest"]["artifact_refs"][0]
    artifact = root / ref["path"]
    outside = tmp_path / "outside.bin"
    outside.write_bytes(artifact.read_bytes())
    artifact.unlink()
    try:
        artifact.symlink_to(outside)
    except OSError:
        pytest.skip("symlink unavailable")
    with pytest.raises(VideoReadError):
        read_committed_video(root, DATE, result["run_id"])


def test_path_escape_is_rejected_with_valid_receipt(tmp_path: Path):
    _, result = _run(tmp_path)
    root = tmp_path / "v5_private"
    run = root / "video_fupan" / "runs" / DATE / result["run_id"]
    manifest_path = run / "manifest.json"
    payload = json.loads(manifest_path.read_text())
    payload["owner_manifest"]["artifact_refs"] = [{"kind": "media", "path": "../escape", "sha256": "a" * 64}]
    raw = json.dumps(payload, sort_keys=True).encode("utf-8")
    manifest_path.write_bytes(raw)
    (run / "receipt.json").write_text(json.dumps({"owner_run_id": result["run_id"], "manifest_sha256": hashlib.sha256(raw).hexdigest()}), encoding="utf-8")
    with pytest.raises(VideoReadError):
        read_committed_video(root, DATE, result["run_id"])


# Original four contract tests remain covered by the Mac fixed run history.
# Chat runtime: NOT_RUN (no shell/runtime available).
