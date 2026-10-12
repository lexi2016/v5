# M12 Mac fixed-a158 test failure

## Fixed source identity
- Repository: `lexi2016/v5`
- Tested commit: `a158bca502e77575442467ee1339a238b824690c`
- Daily blob: `47ed1493daa90e732cc58a62f5c28cde408f43eb`
- Store blob: `635d3fb081b30d9df4698faf21ecdc47db4fe2f4`
- Test: `tests/m12/test_video_fupan_default_chain.py`
- Test blob: `e14f6ba05813ddb7d93e1866481d058199180d1e`; bytes identical to the c834 test.
- All 99 fixed-tree files matched their Git blob identities before and after testing. No local product or test changes.

## Execution
Mac, existing isolated Python 3.14.6 and pytest 9.1.1. Executed invocation below has the interpreter/output paths normalized to relative paths; working directory is the fixed source root.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
TMPDIR=../m12-a158-evidence/tmp \
python -m pytest tests/m12/test_video_fupan_default_chain.py -vv \
  -p no:cacheprovider \
  --basetemp=../m12-a158-evidence/tmp/pytest \
  --junitxml=../m12-a158-evidence/junit.xml
```

- Start UTC: `2026-10-12T02:54:35.973098+00:00`
- End UTC: `2026-10-12T02:54:36.232808+00:00`
- pytest exit: **1**
- Summary: **3 failed, 1 passed in 0.15s**
- Separate stderr was empty. Full stdout is in `stdout.sanitized.log`; only machine-specific interpreter/source/evidence absolute paths were normalized.

| Test | Result |
| --- | --- |
| `test_simulated_owner_default_chain_contract` | FAIL |
| `test_receipt_manifest_artifact_mutation_rejected` | FAIL |
| `test_reader_rejects_empty_refs_and_bad_sha` | PASS |
| `test_simulated_identity_and_path_escape_rejected` | FAIL |

## Observed change from c834
The prior `manifest bytes mismatch` error does not occur in this run. All three failing tests pass the cold-reader call and reach `video_fupan_daily.py:133`, calling `publish_latest_success`. They then fail at `video_fupan_store.py:66` → `ensure_date_run` → line 39:

```text
V5.src.v5_shadow.video_fupan_store.VideoStoreError: invalid run
```

The exception is wrapped at `video_fupan_daily.py:136`:

```text
V5.src.v5_shadow.video_fupan_daily.VideoArtifactError: invalid run
```

The first failing run ID in the traceback is `rcv1-20261011-none-32985ce688eb24e0`. The traceback shows the rejecting pattern `[0-9a-fA-F_-]+`. This is observed runtime evidence, not an additional source review or local fix. The same three tests still fail; the two negative tests do not reach their later mutation assertions.

## Scope
Only this four-test file was executed. No real media acquisition, real ASR, deployment, production V4/trading operation, or credential access was performed. Double full-run counts, failed-run preservation of previous success, ancestor symlink coverage, and real AcquisitionTools fixtures remain NOT_RUN here. No complete lifecycle or module acceptance is claimed.
