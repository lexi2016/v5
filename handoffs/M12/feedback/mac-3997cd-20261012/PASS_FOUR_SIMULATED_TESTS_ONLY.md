# M12 Mac fixed-3997cd — PASS_FOUR_SIMULATED_TESTS_ONLY

## Fixed source identity
- Repository: `lexi2016/v5`
- Tested commit: `3997cdeae2239b2314123e88901919eb8780cd25`
- `tests/m12/test_video_fupan_default_chain.py` blob: `4049beafc54ca41d9703a01f4eb975992637cc77`
- Daily blob: `47ed1493daa90e732cc58a62f5c28cde408f43eb`
- Store blob: `7300f0c2d8d6201fe3bc6c857767d5f0e3b8e2e1`
- Reader blob: `2b0c226d6eb721ad13804a238c1d73a31914d1f6`
- This candidate changes the test fixture supplied by Chat. Its test blob differs from prior runs (`e14f6ba05813ddb7d93e1866481d058199180d1e`). Daily/store/reader remain byte-identical to 242485. This is not a rerun of the previous test bytes.
- Identical verified files were reused. All 105 fixed-tree files matched Git blob identities before and after execution. No local product or test edits.

## Execution
Mac, existing isolated Python 3.14.6 and pytest 9.1.1. From the fixed source root; machine-specific interpreter and output paths normalized to relative paths:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
TMPDIR=../m12-3997cd-evidence/tmp \
python -m pytest tests/m12/test_video_fupan_default_chain.py -vv \
  -p no:cacheprovider \
  --basetemp=../m12-3997cd-evidence/tmp/pytest \
  --junitxml=../m12-3997cd-evidence/junit.xml
```

- Start UTC: `2026-10-12T03:21:23.773332+00:00`
- End UTC: `2026-10-12T03:21:24.018839+00:00`
- pytest exit: **0**
- Summary: **4 passed in 0.14s**
- Separate stderr was empty. Full stdout is in `stdout.sanitized.log`; only machine-specific interpreter/source/evidence absolute paths were normalized.

| Test | Result |
| --- | --- |
| `test_simulated_owner_default_chain_contract` | PASS |
| `test_receipt_manifest_artifact_mutation_rejected` | PASS |
| `test_reader_rejects_empty_refs_and_bad_sha` | PASS |
| `test_simulated_identity_and_path_escape_rejected` | PASS |

## Assertion reach and limits
In the default-chain test, the reader `VERIFIED`, `owner.capture_count == 1`, and `owner.asr_count == 1` assertions were all reached and passed. These counts belong to the supplied simulated callbacks, not real media downloading or a real ASR service. The former manifest mismatch, invalid run, undefined parents, and capture-count failure did not occur in this run.

Only this fixed four-test file was executed. No additional lifecycle or safety-root suite was run. Double full-run counts, failed-run preservation of previous success, ancestor-symlink coverage, and real AcquisitionTools fixtures remain NOT_RUN here. Real media acquisition, real ASR, deployment, live V4/trading operation, and credential access were not performed. This is not full M12, lifecycle, or natural media-chain acceptance.
