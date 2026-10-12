from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from V5.src.v5_shadow.video_fupan_daily import run_video_fupan
from V5.src.v5_shadow.video_fupan_reader import read_committed_video, VideoReadError


DATE = "20261011"


def _artifact(root: Path, name: str, data: bytes) -> tuple[str, str]:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return name, hashlib.sha256(data).hexdigest()


class SimulatedOwner:
    def __init__(self, root: Path):
        self.root = root
        self.capture_count = 0
        self.asr_count = 0

    def tools(self):
        from V5.vendor.video_fupan_baseline.review_core.producer import AcquisitionTools

        def discover(_date, _config):
            return [{"bv_id": "BV_SIMULATED", "title": "SIMULATED"}]

        def capture(_selection, work_dir, _config):
            self.capture_count += 1
            return _artifact(work_dir, "media/simulated.bin", b"SIMULATED_MEDIA")

        def asr(_media, work_dir, _config):
            self.asr_count += 1
            return _artifact(work_dir, "asr/transcript.txt", "SIMULATED_ASR_NON_EMPTY".encode())

        return AcquisitionTools(discover=discover, capture=capture, asr=asr)


def test_simulated_owner_default_chain_contract(tmp_path: Path):
    owner = SimulatedOwner(tmp_path)
    result = run_video_fupan(
        DATE,
        private_root=tmp_path / "v5_private",
        tools=owner.tools(),
        source_identity="SIMULATED_SOURCE",
        tool_identity="SIMULATED_TOOL",
        config_identity="SIMULATED_CONFIG",
        allow_network=True,
    )
    checked = read_committed_video(tmp_path / "v5_private", DATE, result["run_id"])
    assert checked["status"] == "VERIFIED"
    assert owner.capture_count == 1
    assert owner.asr_count == 1


def test_receipt_manifest_artifact_mutation_rejected(tmp_path: Path):
    owner = SimulatedOwner(tmp_path)
    result = run_video_fupan(DATE, private_root=tmp_path / "v5_private", tools=owner.tools(), source_identity="s", tool_identity="t", config_identity="c", allow_network=True)
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
    owner = SimulatedOwner(tmp_path)
    result = run_video_fupan(DATE, private_root=tmp_path / "v5_private", tools=owner.tools(), source_identity="s", tool_identity="t", config_identity="c", allow_network=True)
    run = tmp_path / "v5_private" / "video_fupan" / "runs" / DATE / result["run_id"]
    payload = json.loads((run / "manifest.json").read_text())
    payload["owner_manifest"]["artifact_refs"] = [{"kind": "media", "path": "../escape", "sha256": "a" * 64}]
    (run / "manifest.json").write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(VideoReadError):
        read_committed_video(tmp_path / "v5_private", DATE, result["run_id"])


# Mac execution command:
# pytest -q tests/m12/test_video_fupan_default_chain.py
# Runtime result: NOT_RUN in Chat environment (no shell/runtime available).
