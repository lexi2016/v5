# M12 Mac receipt — PASS_READER_ONLY

## Fixed tested source
- Repository: `lexi2016/v5`
- Tested commit: `731814374a94e64557a7c7223e588dfdcc79efc6`
- `V5/src/v5_shadow/video_fupan_daily.py` blob: `66847689651902d107445dc8c3e63c1ff810925a`
- `V5/src/v5_shadow/video_fupan_store.py` blob: `635d3fb081b30d9df4698faf21ecdc47db4fe2f4`
- `tests/m12/test_video_fupan_default_chain.py` blob: `fe5b176a33b3d52a044084d8aa3c037156b33832`
- All 96 fixed-tree files matched their Git blob identities before and after the run. Product and test files were unchanged.
- Superseded candidate `07034d1ff9faacd51a8930f911c12d6057dc9a61`: NOT_RUN; replaced before test execution.

## Command and timing
The command below represents the executed invocation with machine-specific interpreter and output paths normalized to relative paths. Run from the fixed source root; `python` denotes the existing isolated Python 3.14.6 interpreter with pytest 9.1.1. No rerun was performed to publish this receipt.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
TMPDIR=../m12-731814-evidence/tmp \
python -m pytest tests/m12/test_video_fupan_default_chain.py -vv \
  -p no:cacheprovider \
  --basetemp=../m12-731814-evidence/tmp/pytest \
  --junitxml=../m12-731814-evidence/junit.xml
```

- Start UTC: `2026-10-12T02:44:58.773595+00:00`
- End UTC: `2026-10-12T02:44:58.883609+00:00`
- pytest exit code: **0**
- pytest summary: **2 passed in 0.01s**

| Test | Result |
| --- | --- |
| `test_reader_rejects_empty_refs` | PASS |
| `test_reader_checks_artifact_bytes` | PASS |

## Coverage boundary
This result covers only these two reader tests at the tested commit. It does not validate later branch commits or establish complete M12 acceptance.

- daily execution and lifecycle suite: **NOT_RUN**
- store execution and lifecycle suite: **NOT_RUN**
- safety-root suite: **NOT_RUN**
- real AcquisitionTools fixture: **NOT_RUN**
- real media acquisition and ASR: **NOT_RUN**
- deployment and production integration: **NOT_RUN**
