# M12 Mac fixed-c834 test failure

## Source identity
- Repository: `lexi2016/v5`
- Tested fixed commit: `c834ec220406310033a33865bc73b45024bc872b`
- `tests/m12/test_video_fupan_default_chain.py` blob: `e14f6ba05813ddb7d93e1866481d058199180d1e`
- `V5/src/v5_shadow/video_fupan_daily.py` blob: `66847689651902d107445dc8c3e63c1ff810925a`
- `V5/src/v5_shadow/video_fupan_store.py` blob: `635d3fb081b30d9df4698faf21ecdc47db4fe2f4`
- `V5/src/v5_shadow/video_fupan_reader.py` blob: `2b0c226d6eb721ad13804a238c1d73a31914d1f6`
- All 96 fixed-tree files matched Git blob identities before and after execution. No product or test edits.

## Reproduction
Mac; existing isolated Python 3.14.6, pytest 9.1.1, pluggy 1.6.0. From the fixed source root, the executed command with machine-specific interpreter/output paths normalized to relative paths is:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
TMPDIR=../m12-c834-evidence/tmp \
python -m pytest tests/m12/test_video_fupan_default_chain.py -vv \
  -p no:cacheprovider \
  --basetemp=../m12-c834-evidence/tmp/pytest \
  --junitxml=../m12-c834-evidence/junit.xml
```

- Start UTC: `2026-10-12T02:48:05.583987+00:00`
- End UTC: `2026-10-12T02:48:05.854087+00:00`
- pytest exit: **1**
- Summary: **3 failed, 1 passed in 0.17s**
- Separate captured stderr was empty. Tracebacks were in stdout.
- Full stdout is in `stdout.sanitized.log`; only local interpreter/source/evidence absolute paths were normalized.

| Test | Result |
| --- | --- |
| `test_simulated_owner_default_chain_contract` | FAIL |
| `test_receipt_manifest_artifact_mutation_rejected` | FAIL |
| `test_reader_rejects_empty_refs_and_bad_sha` | PASS |
| `test_simulated_identity_and_path_escape_rejected` | FAIL |

## Observed failure
All three failing tests stop during initial `run_video_fupan` at `video_fupan_daily.py:127` → `_cold_verify` → `video_fupan_daily.py:55`:

```text
VideoArtifactError: cold reader rejected committed run:
V5.src.v5_shadow.video_fupan_reader.VideoReadError: manifest bytes mismatch
```

The nested reader raises at `video_fupan_reader.py:46`. The receipt-mutation and path-escape tests fail before their later mutation/rejection assertions. This receipt reports the observed error, without a local fix or additional source review.

## Scope
Only the fixed test file was run, with its simulated owner tools. No real media acquisition, real ASR, deployment, production integration, or live V4/trading operation was run. Double complete-run counters, failed-run preservation of previous success, ancestor-symlink coverage, and real AcquisitionTools fixtures remain NOT_RUN here. No complete-module acceptance is claimed. The independent 731814 reader-only receipt remains valid only for its own tested commit.
