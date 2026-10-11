from pathlib import Path

from V5.src.v5_shadow.video_fupan_daily import run_video_fupan
from V5.src.v5_shadow.video_fupan_reader import read_committed_video


def test_default_chain_and_independent_reader(tmp_path: Path):
    def producer(_date):
        return {"bv_id": "BV_TEST", "media_sha256": "media-sha", "available_at": "2026-10-11T20:00:00Z"}

    out = run_video_fupan(
        "20261011",
        private_root=tmp_path / "v5_private",
        acquire_video=producer,
        config_identity="config",
        tool_identity="tool",
        source_identity="source",
    )
    checked = read_committed_video(tmp_path / "v5_private", "20261011", out["run_id"])
    assert checked["status"] == "VERIFIED"


def test_tampered_receipt_rejected(tmp_path: Path):
    def producer(_date):
        return {"bv_id": "BV_TEST", "media_sha256": "media-sha"}

    out = run_video_fupan(
        "20261011",
        private_root=tmp_path / "v5_private",
        acquire_video=producer,
        config_identity="config",
        tool_identity="tool",
        source_identity="source",
    )
    receipt = tmp_path / "v5_private" / "video_fupan" / "runs" / "20261011" / out["run_id"] / "receipt.json"
    receipt.write_text('{"run_id":"bad","status":"COMMITTED"}', encoding="utf-8")
    try:
        read_committed_video(tmp_path / "v5_private", "20261011", out["run_id"])
    except Exception:
        return
    raise AssertionError("tampered receipt accepted")
