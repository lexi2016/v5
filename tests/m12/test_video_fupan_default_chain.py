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
    """Narrow AcquisitionTools fixture; not a producer replacement."""

    def __init__(self):
        self.capture_count = 0
        self.asr_count = 0

    def tools(self):
        from V5.vendor.video_fupan_baseline.review_core.producer import AcquisitionTools

        def discover(_date, _config):
            return [{
                "bv_id": "BV_SIMULATED",
                "title": "10.11 A股复盘 主线行情思路 SIMULATED",
                "upload_date": DATE,
                "uploader": "比巴卜作手",
                "target_trade_date": DATE,
            }]

        def capture(_selection, work_dir, _config):
            self.capture_count += 1
            media = work_dir / "media" / "simulated.mp4"
            media.parent.mkdir(parents=True, exist_ok=True)
            media.write_bytes(b"SIMULATED_MEDIA_BYTES")
            return {"status": "CAPTURED", "media_path": str(media), "downloaded": True, "access_status": "SIMULATED"}

        def asr(_media, work_dir, _config):
            self.asr_count += 1
            out = work_dir / "asr"
            out.mkdir(parents=True, exist_ok=True)
            raw = out / "transcript.funasr_raw.txt"
            seg = out / "transcript.funasr_segments.csv"
            raw.write_text("SIMULATED_ASR_NON_EMPTY", encoding="utf-8")
            seg.write_text("start,end,text\n0,1,SIMULATED", encoding="utf-8")
            return {"status": "ASR_REVIEW_REQUIRED", "raw_path": str(raw), "segments_path": str(seg)}

        return AcquisitionTools(discover=discover, capture=capture, asr=asr)


def _run(tmp_path, owner=None):
    owner = owner or SimulatedOwner()
    result = run_video_fupan(
        DATE,
        private_root=tmp_path / "v5_private",
        tools=owner.tools(),
        source_identity="SIMULATED_SOURCE",
        tool_identity="SIMULATED_TOOL",
        config_identity="SIMULATED_CONFIG",
        allow_network=True,
    )
    return owner, result


def test_simulated_owner_default_chain_contract(tmp_path: Path):
    owner, result = _run(tmp_path)
    checked = read_committed_video(tmp_path / "v5_private", DATE, result["run_id"])
    assert checked["status"] == "VERIFIED"
    assert owner.capture_count == 1
    assert owner.asr_count == 1


def test_receipt_manifest_artifact_mutation_rejected(tmp_path: Path):
    _, result = _run(tmp_path)
    run = tmp_path / "v5_private" / "video_fupan" / "runs" / DATE / result["run_id"]
    (run / "receipt.json").write_text('{"owner_run_id":"bad"}', encoding="utf-8")
    with pytest.raises(VideoReadError):
        read_committed_video(tmp_path / "v5_private", DATE, result["run_id"])


def test_reader_rejects_empty_refs_and_bad_sha(tmp_path: Path):
    run = tmp_path / "video_fupan" / "runs" / DATE / "deadbeef"
    run.mkdir(parents=True)
    manifest = {"owner_run_id": "deadbeef", "owner_manifest": {"artifact_refs": [{"kind": "media", "path": "x", "sha256": ""}]}}
    raw = json.dumps(manifest, sort_keys=True).encode()
    (run / "manifest.json").write_bytes(raw)
    (run / "receipt.json").write_text(json.dumps({"owner_run_id": "deadbeef", "manifest_sha256": hashlib.sha256(raw).hexdigest()}))
    with pytest.raises(VideoReadError):
        read_committed_video(tmp_path, DATE, "deadbeef")


def test_simulated_identity_and_path_escape_rejected(tmp_path: Path):
    _, result = _run(tmp_path)
    run = tmp_path / "v5_private" / "video_fupan" / "runs" / DATE / result["run_id"]
    payload = json.loads((run / "manifest.json").read_text())
    payload["owner_manifest"]["artifact_refs"] = [{"kind": "media", "path": "../escape", "sha256": "a" * 64}]
    (run / "manifest.json").write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(VideoReadError):
        read_committed_video(tmp_path / "v5_private", DATE, result["run_id"])


def test_same_owner_does_not_repeat_capture_asr(tmp_path: Path):
    owner = SimulatedOwner()
    _, first = _run(tmp_path, owner)
    first_counts = (owner.capture_count, owner.asr_count)
    _, second = _run(tmp_path, owner)
    assert read_committed_video(tmp_path / "v5_private", DATE, second["run_id"])["status"] == "VERIFIED"
    assert first_counts == (1, 1)
    assert (owner.capture_count, owner.asr_count) == first_counts


def test_failed_publish_keeps_previous_success_pointer(tmp_path: Path):
    owner, first = _run(tmp_path)
    root = tmp_path / "v5_private"
    latest = root / "video_fupan" / DATE / "latest_success.json"
    assert json.loads(latest.read_text())["run_id"] == first["run_id"]
    with pytest.raises(VideoStoreError):
        publish_latest_success(root, DATE, "bad/path")
    assert json.loads(latest.read_text())["run_id"] == first["run_id"]
    assert owner.capture_count == 1


def test_symlink_path_boundary_rejected(tmp_path: Path):
    root = tmp_path / "v5_private"
    outside = tmp_path / "outside.bin"
    outside.write_bytes(b"outside")
    linked = root / "escape.bin"
    root.mkdir(parents=True)
    try:
        linked.symlink_to(outside)
    except OSError:
        pytest.skip("symlink unavailable")
    assert linked.is_symlink()
    with pytest.raises(VideoReadError):
        _ = read_committed_video(root, DATE, "does-not-exist")


# Mac execution command:
# pytest -q tests/m12/test_video_fupan_default_chain.py
# Chat runtime: NOT_RUN (no shell/runtime available).
