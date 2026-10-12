from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from V5.src.v5_shadow.video_fupan_daily import run_video_fupan
from V5.src.v5_shadow.video_fupan_reader import read_committed_video, VideoReadError
from V5.src.v5_shadow.video_fupan_store import VideoStoreError, publish_latest_success

DATE = "20261011"


class SimulatedOwner:
    """Only discovery/capture/ASR are synthetic; the vendor owner runs unchanged."""

    def __init__(self, bv_id="BV_SIMULATED", asr_status="ASR_REVIEW_REQUIRED"):
        self.bv_id = bv_id
        self.asr_status = asr_status
        self.capture_count = 0
        self.asr_count = 0

    def tools(self):
        from V5.vendor.video_fupan_baseline.review_core.producer import AcquisitionTools

        def discover(_date, _config):
            return [{"bv_id": self.bv_id, "title": "10.11 A股复盘 主线行情思路 SIMULATED", "upload_date": DATE, "uploader": "比巴卜作手", "target_trade_date": DATE}]

        def capture(_selection, work_dir, _config):
            self.capture_count += 1
            p = work_dir / "media" / "simulated.mp4"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b"SIMULATED_MEDIA")
            return {"status": "CAPTURED", "media_path": str(p), "downloaded": True, "access_status": "SIMULATED"}

        def asr(_media, work_dir, _config):
            self.asr_count += 1
            if self.asr_status in {"FAILED", "ASR_FAILED"}:
                return {"status": self.asr_status, "reason": "SIMULATED_ASR_FAILURE"}
            p = work_dir / "asr"
            p.mkdir(parents=True, exist_ok=True)
            raw = p / "a.funasr_raw.txt"
            seg = p / "a.funasr_segments.csv"
            raw.write_text("SIMULATED", encoding="utf-8")
            seg.write_text("start,end,text\n0,1,SIMULATED", encoding="utf-8")
            return {"status": self.asr_status, "raw_path": str(raw), "segments_path": str(seg)}

        return AcquisitionTools(discover=discover, capture=capture, asr=asr)


def _run(tmp_path, owner=None):
    owner = owner or SimulatedOwner()
    # The original owner requires this switch even with all three local adapters.
    # Tests fail on any actual network attempt.
    return owner, run_video_fupan(DATE, private_root=tmp_path / "v5_private", tools=owner.tools(), source_identity="s", tool_identity="t", config_identity="c", allow_network=True)


def _snapshot(path):
    return {str(p.relative_to(path)): p.read_bytes() for p in path.rglob("*") if p.is_file()}


def _cold_read(root, run_id):
    code = """import json, sys
from pathlib import Path
from V5.src.v5_shadow.video_fupan_reader import read_committed_video
result = read_committed_video(Path(sys.argv[1]), sys.argv[2], sys.argv[3])
assert not any(name.endswith('review_core.producer') for name in sys.modules)
print(json.dumps(result))
"""
    result = subprocess.run([sys.executable, "-c", code, str(root), DATE, run_id], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr + result.stdout
    return json.loads(result.stdout)


class VideoFupanDefaultChainTests(unittest.TestCase):
    """Runnable with either stdlib unittest or pytest; no extra cloud dependency."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="m12-v5-test-")
        self.addCleanup(temporary.cleanup)
        self.tmp_path = Path(temporary.name)
        self.root = self.tmp_path / "v5_private"
        self.latest = self.root / "video_fupan" / DATE / "latest_success.json"
        for target in ("socket.socket.connect", "socket.create_connection"):
            blocker = patch(target, side_effect=AssertionError("network forbidden in M12 lifecycle tests"))
            blocker.start()
            self.addCleanup(blocker.stop)

    def test_same_input_reuses_committed_run_without_new_capture_asr(self):
        owner, first = _run(self.tmp_path)
        before = _snapshot(self.root / "video_fupan")
        pointer_stat = self.latest.stat()
        _, second = _run(self.tmp_path, owner)
        assert second["run_id"] == first["run_id"]
        assert second["reused"] is True
        assert owner.capture_count == 1
        assert owner.asr_count == 1
        assert read_committed_video(self.root, DATE, second["run_id"])["status"] == "VERIFIED"
        assert _snapshot(self.root / "video_fupan") == before
        assert self.latest.stat().st_mtime_ns == pointer_stat.st_mtime_ns

    def test_failed_publish_keeps_old_success_and_old_run_readable(self):
        _, result = _run(self.tmp_path)
        assert json.loads(self.latest.read_text())["run_id"] == result["run_id"]
        with self.assertRaises(VideoStoreError):
            publish_latest_success(self.root, DATE, "bad/path")
        assert json.loads(self.latest.read_text())["run_id"] == result["run_id"]
        assert read_committed_video(self.root, DATE, result["run_id"])["status"] == "VERIFIED"

    def test_existing_valid_run_symlink_artifact_is_rejected(self):
        _, result = _run(self.tmp_path)
        run = self.root / "video_fupan" / "runs" / DATE / result["run_id"]
        payload = json.loads((run / "manifest.json").read_text())
        ref = payload["owner_manifest"]["artifact_refs"][0]
        artifact = self.root / ref["path"]
        outside = self.tmp_path / "outside.bin"
        outside.write_bytes(artifact.read_bytes())
        artifact.unlink()
        artifact.symlink_to(outside)
        with self.assertRaises(VideoReadError):
            read_committed_video(self.root, DATE, result["run_id"])

    def test_path_escape_is_rejected_with_valid_receipt(self):
        _, result = _run(self.tmp_path)
        run = self.root / "video_fupan" / "runs" / DATE / result["run_id"]
        manifest_path = run / "manifest.json"
        payload = json.loads(manifest_path.read_text())
        payload["owner_manifest"]["artifact_refs"] = [{"kind": "media", "path": "../escape", "sha256": "a" * 64}]
        raw = json.dumps(payload, sort_keys=True).encode("utf-8")
        manifest_path.write_bytes(raw)
        (run / "receipt.json").write_text(json.dumps({"owner_run_id": result["run_id"], "manifest_sha256": hashlib.sha256(raw).hexdigest()}), encoding="utf-8")
        with self.assertRaises(VideoReadError):
            read_committed_video(self.root, DATE, result["run_id"])

    # Restored 3997cde contract tests, with the original assertions executable.
    def test_simulated_owner_default_chain_contract(self):
        owner, result = _run(self.tmp_path)
        checked = read_committed_video(self.root, DATE, result["run_id"])
        assert checked["status"] == "VERIFIED"
        assert owner.capture_count == 1
        assert owner.asr_count == 1

    def test_receipt_manifest_artifact_mutation_rejected(self):
        _, result = _run(self.tmp_path)
        run = self.root / "video_fupan" / "runs" / DATE / result["run_id"]
        (run / "receipt.json").write_text('{"owner_run_id":"bad"}', encoding="utf-8")
        with self.assertRaises(VideoReadError):
            read_committed_video(self.root, DATE, result["run_id"])

    def test_reader_rejects_empty_refs_and_bad_sha(self):
        for refs in ([], [{"kind": "media", "path": "x", "sha256": ""}]):
            with self.subTest(refs=refs):
                run = self.tmp_path / "video_fupan" / "runs" / DATE / "deadbeef"
                run.mkdir(parents=True, exist_ok=True)
                manifest = {"owner_run_id": "deadbeef", "owner_manifest": {"artifact_refs": refs}}
                raw = json.dumps(manifest, sort_keys=True).encode()
                (run / "manifest.json").write_bytes(raw)
                (run / "receipt.json").write_text(json.dumps({"owner_run_id": "deadbeef", "manifest_sha256": hashlib.sha256(raw).hexdigest()}))
                with self.assertRaises(VideoReadError):
                    read_committed_video(self.tmp_path, DATE, "deadbeef")

    def test_simulated_identity_and_path_escape_rejected(self):
        _, result = _run(self.tmp_path)
        run = self.root / "video_fupan" / "runs" / DATE / result["run_id"]
        payload = json.loads((run / "manifest.json").read_text())
        payload["owner_manifest"]["artifact_refs"] = [{"kind": "media", "path": "../escape", "sha256": "a" * 64}]
        (run / "manifest.json").write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaises(VideoReadError):
            read_committed_video(self.root, DATE, result["run_id"])

    def test_two_valid_different_runs_promote_and_old_run_remains_cold_readable(self):
        _, first = _run(self.tmp_path, SimulatedOwner("BV_FIRST", "OK"))
        old_run = self.root / "video_fupan" / "runs" / DATE / first["run_id"]
        old_bytes = _snapshot(old_run)
        _, second = _run(self.tmp_path, SimulatedOwner("BV_SECOND"))
        assert first["run_id"] != second["run_id"]
        assert json.loads(self.latest.read_text())["run_id"] == second["run_id"]
        assert _snapshot(old_run) == old_bytes
        before = _snapshot(self.root)
        for run in (first, second):
            checked = _cold_read(self.root, run["run_id"])
            assert checked["status"] == "VERIFIED"
            assert checked["manifest"]["owner_manifest"]["asr_status"] == "ASR_REVIEW_REQUIRED"
            assert checked["manifest"]["owner_manifest"]["gap_status"] == "VIDEO_GAP_AUDIT_EMPTY"
        assert _snapshot(self.root) == before

    def test_first_asr_failure_never_creates_latest_success(self):
        for status in ("FAILED", "ASR_FAILED"):
            with self.subTest(status=status):
                root_parent = self.tmp_path / status
                _, result = _run(root_parent, SimulatedOwner("BV_FAILURE", status))
                root = root_parent / "v5_private"
                receipt_path = root / "review" / DATE / "runs" / result["run_id"] / "receipt.json"
                receipt = json.loads(receipt_path.read_text())
                assert receipt["status"] == "ACQUIRE_FAILED"
                assert receipt["current_advanced"] is True
                assert result["manifest"]["owner_status"] == "TARGET_BV_LOCKED"
                assert result["manifest"]["owner_manifest"]["asr_status"] == "ASR_FAILED"
                assert not (root / "video_fupan" / DATE / "latest_success.json").exists()
                assert result["promoted"] is False
                assert _cold_read(root, result["run_id"])["status"] == "VERIFIED"
                # A cached failed first run remains evidence, never a success.
                _, repeated = _run(root_parent, SimulatedOwner("BV_FAILURE", status))
                assert repeated["reused"] is True
                assert repeated["promoted"] is False
                assert not (root / "video_fupan" / DATE / "latest_success.json").exists()

    def test_later_other_bv_asr_failure_preserves_old_success(self):
        _, first = _run(self.tmp_path, SimulatedOwner("BV_GOOD"))
        old_pointer = self.latest.read_bytes()
        old_run = self.root / "video_fupan" / "runs" / DATE / first["run_id"]
        old_bytes = _snapshot(old_run)
        _, failed = _run(self.tmp_path, SimulatedOwner("BV_BAD", "ASR_FAILED"))
        assert failed["run_id"] != first["run_id"]
        assert self.latest.read_bytes() == old_pointer
        assert _snapshot(old_run) == old_bytes
        assert failed["promoted"] is False
        for run in (first, failed):
            assert _cold_read(self.root, run["run_id"])["status"] == "VERIFIED"
        owner_receipt = self.root / "review" / DATE / "runs" / failed["run_id"] / "receipt.json"
        assert json.loads(owner_receipt.read_text())["current_advanced"] is False

    def test_noncurrent_failed_run_reuses_exact_evidence_without_capture_or_asr(self):
        for status in ("FAILED", "ASR_FAILED"):
            with self.subTest(status=status):
                parent = self.tmp_path / status
                root = parent / "v5_private"
                _, first = _run(parent, SimulatedOwner("BV_SUCCESS_A"))
                owner = SimulatedOwner("BV_FAILURE_B", status)
                _, failed = _run(parent, owner)
                current = root / "review" / DATE / "current.json"
                latest = root / "video_fupan" / DATE / "latest_success.json"
                owner_run = root / "review" / DATE / "runs" / failed["run_id"]
                receipt = (owner_run / "receipt.json").read_bytes()
                assert json.loads(receipt)["status"] == "ACQUIRE_FAILED"
                assert json.loads(receipt)["current_advanced"] is False
                before = _snapshot(root)
                pointer_times = (current.stat().st_mtime_ns, latest.stat().st_mtime_ns)
                # A repaired dependency alone does not authorize a new attempt
                # under the same deterministic input/config/tool identity.
                owner.asr_status = "ASR_REVIEW_REQUIRED"
                _, repeated = _run(parent, owner)
                assert repeated["run_id"] == failed["run_id"]
                assert repeated["reused"] is True
                assert repeated["promoted"] is False
                assert owner.capture_count == owner.asr_count == 1
                assert _snapshot(root) == before
                assert (owner_run / "receipt.json").read_bytes() == receipt
                assert json.loads(current.read_text())["run_id"] == first["run_id"]
                assert json.loads(latest.read_text())["run_id"] == first["run_id"]
                assert (current.stat().st_mtime_ns, latest.stat().st_mtime_ns) == pointer_times
                assert _cold_read(root, failed["run_id"])["owner_receipt"]["status"] == "ACQUIRE_FAILED"

    def test_owner_new_config_attempt_recovers_failed_asr_into_new_immutable_run(self):
        from V5.vendor.video_fupan_baseline.review_core.config import ProducerConfig
        from V5.vendor.video_fupan_baseline.review_core.core import run_video, inspect_bundle

        _, first = _run(self.tmp_path, SimulatedOwner("BV_SUCCESS_A"))
        owner = SimulatedOwner("BV_FAILURE_B", "ASR_FAILED")
        _, failed = _run(self.tmp_path, owner)
        failed_dir = self.root / "review" / DATE / "runs" / failed["run_id"]
        old_evidence = _snapshot(failed_dir)
        old_success = self.latest.read_bytes()
        old_media = _snapshot(self.root / "media")
        owner.asr_status = "ASR_REVIEW_REQUIRED"
        config = ProducerConfig(data_root=self.root, network_allowed=True,
                                extra={"recovery_attempt": "explicit-attempt-C"})
        recovered = run_video(DATE, mode="acquire", data_root=self.root,
                              config=config, tools=owner.tools(), allow_network=True)
        assert recovered["run_id"] not in {first["run_id"], failed["run_id"]}
        assert recovered["acquisition_count"] == 0
        assert recovered["asr_execution_count"] == 1
        assert owner.capture_count == 1 and owner.asr_count == 2
        assert _snapshot(failed_dir) == old_evidence
        assert _snapshot(self.root / "media") == old_media
        assert self.latest.read_bytes() == old_success  # raw owner does not publish V5
        assert inspect_bundle(DATE, self.root)["run_id"] == recovered["run_id"]
        receipt = json.loads((Path(recovered["run_dir"]) / "receipt.json").read_text())
        assert receipt["status"] == "ACQUIRED"
        assert recovered["manifest"]["asr_status"] == "ASR_REVIEW_REQUIRED"
        before = _snapshot(self.root)
        repeated = run_video(DATE, mode="acquire", data_root=self.root,
                             config=config, tools=owner.tools(), allow_network=True)
        assert repeated["idempotent"] is True
        assert repeated["run_id"] == recovered["run_id"]
        assert owner.capture_count == 1 and owner.asr_count == 2
        assert _snapshot(self.root) == before

    def test_historical_success_is_not_repromoted_by_failure_reuse_path(self):
        from V5.vendor.video_fupan_baseline.review_core.core import ImmutableRunError

        owner, first = _run(self.tmp_path, SimulatedOwner("BV_SUCCESS_A"))
        _, second = _run(self.tmp_path, SimulatedOwner("BV_SUCCESS_B"))
        before = _snapshot(self.root)
        with self.assertRaises(ImmutableRunError):
            _run(self.tmp_path, owner)
        assert owner.capture_count == owner.asr_count == 1
        assert _snapshot(self.root) == before
        assert json.loads(self.latest.read_text())["run_id"] == second["run_id"]
        assert _cold_read(self.root, first["run_id"])["status"] == "VERIFIED"

    def test_noncurrent_failed_run_tampering_is_rejected_before_capture_or_asr(self):
        from V5.vendor.video_fupan_baseline.review_core.core import EvidenceValidationError

        _, first = _run(self.tmp_path, SimulatedOwner("BV_SUCCESS_A"))
        owner = SimulatedOwner("BV_FAILURE_B", "ASR_FAILED")
        _, failed = _run(self.tmp_path, owner)
        run = self.root / "review" / DATE / "runs" / failed["run_id"]
        receipt_path = run / "receipt.json"
        receipt = json.loads(receipt_path.read_text())
        mutations = [(run / "video_session.json", b"CORRUPTED_ARTIFACT")]
        for field, value in (("input_digest", "0" * 64), ("run_id", "wrong"),
                             ("trade_date", "20261010"), ("manifest_sha256", "0" * 64),
                             ("safety_flags", {"production_allowed": True})):
            mutated = dict(receipt)
            mutated[field] = value
            mutations.append((receipt_path, json.dumps(mutated).encode()))
        for artifact, value in mutations:
            with self.subTest(path=artifact.name, value=value):
                original = artifact.read_bytes()
                artifact.write_bytes(value)
                before = _snapshot(self.root)
                try:
                    with self.assertRaises(EvidenceValidationError):
                        _run(self.tmp_path, owner)
                    assert owner.capture_count == owner.asr_count == 1
                    assert _snapshot(self.root) == before
                    assert json.loads(self.latest.read_text())["run_id"] == first["run_id"]
                finally:
                    artifact.write_bytes(original)

    def test_real_publication_write_or_replace_failure_preserves_old_success(self):
        from V5.src.v5_shadow import video_fupan_store as store
        for failure in ("write", "replace"):
            with self.subTest(failure=failure):
                parent = self.tmp_path / failure
                root = parent / "v5_private"
                latest = root / "video_fupan" / DATE / "latest_success.json"
                _, first = _run(parent, SimulatedOwner("BV_BEFORE"))
                before = latest.read_bytes()
                second_owner = SimulatedOwner("BV_AFTER")
                injected = []
                real_replace = os.replace
                real_fdopen = os.fdopen
                real_write_text = Path.write_text

                def replace(source, destination):
                    if Path(destination) == latest:
                        injected.append("replace")
                        raise OSError("SIMULATED_REPLACE_FAILURE")
                    return real_replace(source, destination)

                def write_text(path, text, *args, **kwargs):
                    if path == latest:
                        real_write_text(path, "{", *args, **kwargs)
                        injected.append("write")
                        raise OSError("SIMULATED_WRITE_FAILURE")
                    return real_write_text(path, text, *args, **kwargs)

                def fdopen(fd, *args, **kwargs):
                    handle = real_fdopen(fd, *args, **kwargs)
                    class PartialWrite:
                        def __enter__(self):
                            handle.__enter__()
                            return self
                        def __exit__(self, *exc):
                            return handle.__exit__(*exc)
                        def write(self, payload):
                            handle.write(payload[:1])
                            injected.append("write")
                            raise OSError("SIMULATED_WRITE_FAILURE")
                    return PartialWrite()

                # Failure injection is at the actual pointer I/O boundary only.
                # For pre-fix write_text it reproduces truncation; for atomic code
                # it interrupts the real temporary write before replacement.
                if failure == "replace":
                    context = patch.object(store.os, "replace", replace)
                else:
                    def publication_only(root_arg, date_arg, run_arg):
                        with patch.object(store.os, "fdopen", fdopen), patch.object(Path, "write_text", write_text):
                            publish_latest_success(root_arg, date_arg, run_arg)
                    context = patch("V5.src.v5_shadow.video_fupan_daily.publish_latest_success", publication_only)
                with context:
                    with self.assertRaises((OSError, VideoStoreError)):
                        _run(parent, second_owner)
                assert injected == [failure]
                assert latest.read_bytes() == before
                assert second_owner.capture_count == second_owner.asr_count == 1
                assert _cold_read(root, first["run_id"])["status"] == "VERIFIED"
                runs = list((root / "video_fupan" / "runs" / DATE).iterdir())
                assert len(runs) == 2
                second_id = next(run.name for run in runs if run.name != first["run_id"])
                assert _cold_read(root, second_id)["status"] == "VERIFIED"
                # Retry can promote the already committed run without re-acquisition.
                _, retried = _run(parent, second_owner)
                assert retried["reused"] is True
                assert json.loads(latest.read_text())["run_id"] == second_id
                assert second_owner.capture_count == second_owner.asr_count == 1

    def test_cold_reader_rejects_owner_receipt_identity_hash_or_status_mutation(self):
        _, result = _run(self.tmp_path)
        owner_receipt = self.root / "review" / DATE / "runs" / result["run_id"] / "receipt.json"
        original = owner_receipt.read_bytes()
        for field, value in (("run_id", "wrong"), ("trade_date", "20261010"), ("manifest_sha256", "0" * 64), ("status", "ACQUIRE_FAILED")):
            with self.subTest(field=field):
                payload = json.loads(original)
                payload[field] = value
                owner_receipt.write_text(json.dumps(payload))
                with self.assertRaises(VideoReadError):
                    read_committed_video(self.root, DATE, result["run_id"])
                owner_receipt.write_bytes(original)

    def test_cold_reader_rejects_owner_receipt_symlink_even_with_same_bytes(self):
        _, result = _run(self.tmp_path)
        receipt = self.root / "review" / DATE / "runs" / result["run_id"] / "receipt.json"
        outside = self.tmp_path / "foreign-receipt.json"
        outside.write_bytes(receipt.read_bytes())
        receipt.unlink()
        receipt.symlink_to(outside)
        with self.assertRaises(VideoReadError):
            read_committed_video(self.root, DATE, result["run_id"])

    def test_legacy_committed_envelope_remains_readable_without_rewriting_history(self):
        owner, result = _run(self.tmp_path)
        run = self.root / "video_fupan" / "runs" / DATE / result["run_id"]
        manifest_path = run / "manifest.json"
        payload = json.loads(manifest_path.read_text())
        payload.pop("owner_receipt_sha256")
        raw = json.dumps(payload, sort_keys=True).encode("utf-8")
        manifest_path.write_bytes(raw)
        receipt_path = run / "receipt.json"
        receipt = json.loads(receipt_path.read_text())
        receipt["manifest_sha256"] = hashlib.sha256(raw).hexdigest()
        receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
        before = _snapshot(run)
        assert _cold_read(self.root, result["run_id"])["status"] == "VERIFIED"
        _, repeated = _run(self.tmp_path, owner)
        assert repeated["reused"] is True
        assert _snapshot(run) == before
        assert owner.capture_count == owner.asr_count == 1

    def test_failed_new_process_verification_preserves_old_success(self):
        from V5.src.v5_shadow import video_fupan_daily as daily
        _, first = _run(self.tmp_path, SimulatedOwner("BV_VERIFIED"))
        before = self.latest.read_bytes()
        cold_verify = daily._cold_verify

        def corrupt_before_real_cold_read(root, date, run_id):
            assert run_id != first["run_id"]
            run = root / "video_fupan" / "runs" / date / run_id
            manifest = json.loads((run / "manifest.json").read_text())
            media = next(ref for ref in manifest["owner_manifest"]["artifact_refs"] if ref["kind"] == "media")
            (root / media["path"]).write_bytes(b"CORRUPTED_BEFORE_COLD_READ")
            return cold_verify(root, date, run_id)

        with patch.object(daily, "_cold_verify", corrupt_before_real_cold_read):
            with self.assertRaisesRegex(daily.VideoArtifactError, "cold reader rejected"):
                _run(self.tmp_path, SimulatedOwner("BV_CORRUPTED"))
        assert self.latest.read_bytes() == before
        assert _cold_read(self.root, first["run_id"])["status"] == "VERIFIED"

    def test_staging_write_or_commit_replace_failure_can_retry_without_overwrite(self):
        from V5.src.v5_shadow import video_fupan_daily as daily
        for failure in ("stage_write", "receipt_write", "commit_replace"):
            with self.subTest(failure=failure):
                parent = self.tmp_path / failure
                root = parent / "v5_private"
                _, first = _run(parent, SimulatedOwner("BV_OLD"))
                latest = root / "video_fupan" / DATE / "latest_success.json"
                before = latest.read_bytes()
                second_owner = SimulatedOwner("BV_NEW")
                write_json = daily.safe_replace_json
                replace = os.replace
                injected = []

                def fail_write(path, payload):
                    target = "manifest.json" if failure == "stage_write" else "receipt.json"
                    if "attempts" in path.parts and path.name == target:
                        injected.append(failure)
                        raise OSError("SIMULATED_STAGING_WRITE_FAILURE")
                    return write_json(path, payload)

                def fail_replace(source, destination):
                    destination = Path(destination)
                    runs = root / "video_fupan" / "runs" / DATE
                    # Old code moved files separately; new code commits a
                    # complete run directory with the same I/O boundary.
                    if destination.parent == runs or (destination.parent.parent == runs and destination.name == "receipt.json"):
                        injected.append("commit_replace")
                        raise OSError("SIMULATED_COMMIT_REPLACE_FAILURE")
                    return replace(source, destination)

                context = patch.object(daily.os, "replace", fail_replace) if failure == "commit_replace" else patch.object(daily, "safe_replace_json", fail_write)
                with context:
                    with self.assertRaises(OSError):
                        _run(parent, second_owner)
                assert injected == [failure]
                assert latest.read_bytes() == before
                assert _cold_read(root, first["run_id"])["status"] == "VERIFIED"
                attempts = root / "video_fupan" / "attempts" / DATE
                failed_evidence = _snapshot(attempts)
                failed_attempts = set(attempts.iterdir())
                try:
                    _, retried = _run(parent, second_owner)
                except daily.VideoArtifactError as exc:
                    self.fail(f"same-input retry must recover without overwriting failed evidence: {exc}")
                assert retried["run_id"] != first["run_id"]
                assert json.loads(latest.read_text())["run_id"] == retried["run_id"]
                assert _cold_read(root, retried["run_id"])["status"] == "VERIFIED"
                assert _snapshot(attempts) == failed_evidence
                assert set(attempts.iterdir()) == failed_attempts
                assert second_owner.capture_count == second_owner.asr_count == 1


if __name__ == "__main__":
    unittest.main()
