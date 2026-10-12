from pathlib import Path

from V5.src.v5_shadow.video_fupan_reader import read_committed_video, VideoReadError


def _make_owner_manifest(root: Path):
    artifact = root / "media.bin"
    artifact.write_bytes(b"video-fixture")
    import hashlib
    return {
        "artifact_refs": [
            {"kind": "media", "path": "media.bin", "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest()}
        ],
        "status": "ASR_REVIEW_REQUIRED",
    }


def test_reader_rejects_empty_refs(tmp_path: Path):
    run = tmp_path / "video_fupan" / "runs" / "20261011" / "run1"
    run.mkdir(parents=True)
    (run / "manifest.json").write_text('{"owner_run_id":"run1","owner_manifest":{"artifact_refs":[]}}')
    (run / "receipt.json").write_text('{"owner_run_id":"run1","manifest_sha256":"bad"}')
    try:
        read_committed_video(tmp_path, "20261011", "run1")
    except VideoReadError:
        return
    raise AssertionError("empty refs accepted")


def test_reader_checks_artifact_bytes(tmp_path: Path):
    owner = _make_owner_manifest(tmp_path)
    run = tmp_path / "video_fupan" / "runs" / "20261011" / "run1"
    run.mkdir(parents=True)
    import hashlib, json
    manifest = {"owner_run_id":"run1", "owner_manifest":owner}
    raw = json.dumps(manifest, sort_keys=True).encode()
    (run / "manifest.json").write_bytes(raw)
    (run / "receipt.json").write_text(json.dumps({"owner_run_id":"run1", "manifest_sha256":hashlib.sha256(raw).hexdigest()}))
    checked = read_committed_video(tmp_path, "20261011", "run1")
    assert checked["status"] == "VERIFIED"
    (tmp_path / "media.bin").write_bytes(b"changed")
    try:
        read_committed_video(tmp_path, "20261011", "run1")
    except VideoReadError:
        return
    raise AssertionError("artifact mutation accepted")
