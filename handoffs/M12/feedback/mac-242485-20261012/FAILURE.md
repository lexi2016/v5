# M12 Mac fixed-242485 test failure

## Fixed source identity
- Repository: `lexi2016/v5`
- Tested commit: `242485924ed0a8eb7ea9cc11bde6abd7039541a7`
- Store blob: `7300f0c2d8d6201fe3bc6c857767d5f0e3b8e2e1`
- Daily blob: `47ed1493daa90e732cc58a62f5c28cde408f43eb`
- `tests/m12/test_video_fupan_default_chain.py` blob: `e14f6ba05813ddb7d93e1866481d058199180d1e`; bytes identical to c834.
- Identical verified files were reused; all 103 fixed-tree files matched their Git blob identities before and after execution. No product or test edits.

## Execution
Mac, existing isolated Python 3.14.6 and pytest 9.1.1. From the fixed source root; machine-specific interpreter and output paths normalized to relative paths:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
TMPDIR=../m12-242485-evidence/tmp \
python -m pytest tests/m12/test_video_fupan_default_chain.py -vv \
  -p no:cacheprovider \
  --basetemp=../m12-242485-evidence/tmp/pytest \
  --junitxml=../m12-242485-evidence/junit.xml
```

- Start UTC: `2026-10-12T03:08:23.486598+00:00`
- End UTC: `2026-10-12T03:08:23.750174+00:00`
- pytest exit: **1**
- Summary: **1 failed, 3 passed in 0.15s**
- Separate stderr was empty. Full stdout is in `stdout.sanitized.log`; only machine-specific interpreter/source/evidence absolute paths were normalized.

| Test | Result |
| --- | --- |
| `test_simulated_owner_default_chain_contract` | FAIL |
| `test_receipt_manifest_artifact_mutation_rejected` | PASS |
| `test_reader_rejects_empty_refs_and_bad_sha` | PASS |
| `test_simulated_identity_and_path_escape_rejected` | PASS |

## Observed failure and previous blockers
The previous manifest-byte mismatch, invalid-run rejection, and undefined-`parents` NameError do not occur. The three tests invoking `run_video_fupan` now return from it; the default-chain test also passes its reader `VERIFIED` assertion. This run therefore progresses beyond the prior cold-reader, latest-success, and manifest-write blockers.

The sole failure is at `tests/m12/test_video_fupan_default_chain.py:59`:

```text
assert owner.capture_count == 1
assert 0 == 1
```

The observed capture count is **0**, expected **1**. The following ASR-count assertion is not reached, so this receipt makes no runtime claim about that counter. No local fix or additional source review was performed.

## Scope
Only the existing four-test file was executed with simulated tools. No real media acquisition, real ASR, deployment, live V4/trading operation, or credential access was performed. Double full-run counts, failed-run preservation of previous success, ancestor-symlink coverage, and real AcquisitionTools fixtures remain NOT_RUN here. No full M12, lifecycle, or natural media-chain acceptance is claimed.
