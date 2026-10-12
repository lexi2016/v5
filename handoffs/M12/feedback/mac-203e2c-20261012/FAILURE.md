# M12 Mac fixed-203e2c — 6 PASS / 1 FAIL

## Fixed source identity
- Repository: `lexi2016/v5`
- Tested commit: `203e2cde6d79b5747e3ff0371ba1dcdbb435d2fb`
- Test file: `tests/m12/test_video_fupan_default_chain.py`
- Test blob: `1438ab6989dba09daeaa54994a85769418729e98` (new Chat-supplied test revision).
- Daily blob: `47ed1493daa90e732cc58a62f5c28cde408f43eb`
- Store blob: `7300f0c2d8d6201fe3bc6c857767d5f0e3b8e2e1`
- Reader blob: `2b0c226d6eb721ad13804a238c1d73a31914d1f6`
- Identical verified files were reused; all 107 fixed-tree files matched their Git blob identities before and after execution. No local product or test edits.

## Execution
Mac, existing isolated Python 3.14.6 and pytest 9.1.1. From the fixed source root; machine-specific interpreter/output paths normalized to relative paths:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
TMPDIR=../m12-203e2c-evidence/tmp \
python -m pytest tests/m12/test_video_fupan_default_chain.py -vv \
  -p no:cacheprovider \
  --basetemp=../m12-203e2c-evidence/tmp/pytest \
  --junitxml=../m12-203e2c-evidence/junit.xml
```

- Start UTC: `2026-10-12T03:28:08.360030+00:00`
- End UTC: `2026-10-12T03:28:08.703881+00:00`
- pytest exit: **1**
- Summary: **1 failed, 6 passed in 0.22s**; 7 collected, no skipped cases.
- Separate stderr was empty. Full stdout is in `stdout.sanitized.log`; only machine-specific interpreter/source/evidence absolute paths were normalized.

| Test | Result |
| --- | --- |
| `test_simulated_owner_default_chain_contract` | PASS |
| `test_receipt_manifest_artifact_mutation_rejected` | PASS |
| `test_reader_rejects_empty_refs_and_bad_sha` | PASS |
| `test_simulated_identity_and_path_escape_rejected` | PASS |
| `test_same_owner_does_not_repeat_capture_asr` | FAIL |
| `test_failed_publish_keeps_previous_success_pointer` | PASS |
| `test_symlink_path_boundary_rejected` | PASS |

## Exact failure
The second `_run(tmp_path, owner)` at test line 111 fails through `video_fupan_daily.py:109` → `stage_attempt` → `video_fupan_store.py:70`:

```text
VideoStoreError: attempt already exists
```

It is wrapped at `video_fupan_daily.py:136` as:

```text
V5.src.v5_shadow.video_fupan_daily.VideoArtifactError: attempt already exists
```

The second run does not complete. Its later reader and capture/ASR count assertions are not reached. No claim of successful repeated-run idempotency follows from this run.

## Actual coverage boundaries
- The default-chain case passes its VERIFIED reader and capture_count == 1 / asr_count == 1 assertions using simulated callbacks.
- The failed-publish case rejects `bad/path`, preserves the existing latest_success run_id, and checks capture_count == 1. It does not read back the previous specified run after failure and does not simulate a mid-publication failure.
- The symlink case creates an `escape.bin` file symlink, then asks the reader for the nonexistent run `does-not-exist`. Its PASS does not establish rejection of a symlink in an ancestor directory of a valid run/artifact.
- The path-escape case modifies the manifest without refreshing the receipt hash; its PASS does not isolate path validation from manifest-hash rejection.

These statements describe the supplied test assertions and observed execution, not an additional product source review. No local fix was made. Only this fixed seven-test file ran; real AcquisitionTools fixtures, real media acquisition/ASR, deployment, live V4/trading operations, and complete lifecycle acceptance remain NOT_RUN. No full M12 or natural media-chain acceptance is claimed.
