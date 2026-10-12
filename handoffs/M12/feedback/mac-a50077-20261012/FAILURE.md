# Mac M12 a50077 targeted lifecycle test — 3 PASS / 1 FAIL

Fixed candidate: `a50077a2a43a7224aaab3637084b9a71fae4ad78`.
Original branch: `dev/m12-github-handoff-20261011`.
Prior comparison: `203e2cde6d79b5747e3ff0371ba1dcdbb435d2fb` had 6 PASS / 1 FAIL; prior feedback `4a45a928`. No earlier a50077 receipt was found in the checked local evidence or remote branch, so this candidate was run once.

Reused the existing Mac M12 Python environment: Python 3.14.6, pytest 9.1.1. New task-isolated source and temporary data directories; old task directories were read-only. All 11 V5/test files matched candidate Git blobs before and after execution. No product modifications or dependency installation.

## Actual command

From isolated fixed candidate root:

```text
<EXISTING_M12_PYTHON> -m pytest tests/m12/test_video_fupan_default_chain.py -vv -p no:cacheprovider --basetemp=<EVIDENCE>/tmp/pytest --junitxml=<EVIDENCE>/junit.xml
```

- Start UTC: **2026-10-12T07:08:49.833328+00:00**
- End UTC: **2026-10-12T07:08:50.164969+00:00**
- Actual pytest exit: **1**
- Summary: **1 failed, 3 passed in 0.22s**
- Synthetic owner fixture only; no real acquisition/ASR, trading, deployment, browser, or P0 tests.

## Results

| Test | Result |
|---|---|
| test_same_input_reuses_committed_run_without_new_capture_asr | PASS |
| test_failed_publish_keeps_old_success_and_old_run_readable | PASS |
| test_existing_valid_run_symlink_artifact_is_rejected | **FAIL** |
| test_path_escape_is_rejected_with_valid_receipt | PASS |

The same-input reuse test now passes; it asserts the same committed run and capture/ASR counts remain one. This addresses the previously observed duplicate owner-attempt failure for this synthetic case.

## First failure

`tests/m12/test_video_fupan_default_chain.py:86`:

```text
with pytest.raises(VideoReadError):
E   Failed: DID NOT RAISE VideoReadError
```

The supplied test creates a valid committed run, copies its first referenced artifact bytes to a sibling file outside the private root, replaces the original artifact with a symlink to that file, and calls the original reader. Symlink creation succeeded (test was not skipped); the expected VideoReadError was not raised.

No product patch, bypass, or expanded audit was attempted. Full sanitized pytest stdout is adjacent; raw logs and JUnit remain local. Natural owner execution, real acquisition, full M12 acceptance and deployment remain NOT_RUN.
