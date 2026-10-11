from pathlib import Path

from V5.src.v5_shadow.video_fupan_reader import read_committed_video


# Runtime execution remains Mac-owned until shell evidence is available.
# These tests document the real contract: Review Core owner binding is required.


def test_reader_rejects_empty_refs(tmp_path: Path):
    root = tmp_path / "v5_private"
    run = root / "video_fupan" / "runs" / "20261011" / "run1"
    run.mkdir(parents=True)
    (run / "manifest.json").write_text(
        '{"owner_run_id":"run1","owner_manifest":{"artifact_refs":[]}}',
        encoding="utf-8",
    )
    (run / "receipt.json").write_text(
        '{"owner_run_id":"run1","manifest_sha256":"bad"}',
        encoding="utf-8",
    )
    try:
        read_committed_video(root, "20261011", "run1")
    except Exception:
        return
    raise AssertionError("empty refs accepted")


def test_reader_rejects_tampered_manifest(tmp_path: Path):
    root = tmp_path / "v5_private"
    run = root / "video_fupan" / "runs" / "20261011" / "run1"
    run.mkdir(parents=True)
    (run / "manifest.json").write_text('{}', encoding="utf-8")
    (run / "receipt.json").write_text(
        '{"owner_run_id":"run1","manifest_sha256":"0"}',
        encoding="utf-8",
    )
    try:
        read_committed_video(root, "20261011", "run1")
    except Exception:
        return
    raise AssertionError("bad receipt accepted")
