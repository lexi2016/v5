# M12 Mac fixed-e231 test failure

## Fixed source identity
- Repository: `lexi2016/v5`
- Tested commit: `e231e879dd4c0d3a24c840a46349a6a631b98619`
- `V5/src/v5_shadow/video_fupan_store.py` blob: `96bd0b09d7a1fbb51ccbdaa75f70a502c71e547d`
- `V5/src/v5_shadow/video_fupan_daily.py` blob: `47ed1493daa90e732cc58a62f5c28cde408f43eb`
- `tests/m12/test_video_fupan_default_chain.py` blob: `e14f6ba05813ddb7d93e1866481d058199180d1e`; bytes identical to c834.
- All 101 fixed-tree files matched their Git blob identities before and after testing. No product or test edits.

## Execution
Mac, existing isolated Python 3.14.6 and pytest 9.1.1. From the fixed source root; machine-specific interpreter and output paths normalized to relative paths:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
TMPDIR=../m12-e231-evidence/tmp \
python -m pytest tests/m12/test_video_fupan_default_chain.py -vv \
  -p no:cacheprovider \
  --basetemp=../m12-e231-evidence/tmp/pytest \
  --junitxml=../m12-e231-evidence/junit.xml
```

- Start UTC: `2026-10-12T03:01:31.251033+00:00`
- End UTC: `2026-10-12T03:01:31.461458+00:00`
- pytest exit: **1**
- Summary: **3 failed, 1 passed in 0.07s**
- Separate stderr was empty. Full stdout is in `stdout.sanitized.log`; only machine-specific interpreter/source/evidence absolute paths were normalized.

| Test | Result |
| --- | --- |
| `test_simulated_owner_default_chain_contract` | FAIL |
| `test_receipt_manifest_artifact_mutation_rejected` | FAIL |
| `test_reader_rejects_empty_refs_and_bad_sha` | PASS |
| `test_simulated_identity_and_path_escape_rejected` | FAIL |

## Observed failure and regression status
All three failing tests stop at `video_fupan_daily.py:123` → `safe_replace_json` → `video_fupan_store.py:49`:

```text
path.parent.mkdir(parents, exist_ok=True)
NameError: name 'parents' is not defined
```

The former `manifest bytes mismatch` and `invalid run` exceptions do not appear in this output, but execution now stops earlier, before cold-reader verification or latest-success publication. Their resolution is therefore NOT_VERIFIED by this rerun. The two negative tests also fail before their later mutation assertions. No local fix or additional source review was performed.

## Scope
Only the existing four-test file was executed. No real media acquisition, real ASR, deployment, live V4/trading operation, or credential access was performed. Double full-run counts, failed-run preservation of previous success, ancestor-symlink coverage, and real AcquisitionTools fixtures remain NOT_RUN here. No full M12, lifecycle, or natural media-chain acceptance is claimed.
